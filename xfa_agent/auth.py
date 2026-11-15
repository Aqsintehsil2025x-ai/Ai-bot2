"""XFA account authentication using Google OAuth.

OAuth access tokens are exchanged server-side and discarded. Only provider
subject IDs and minimal profile information are kept in SQLite.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for
from flask.sessions import SessionInterface, SessionMixin
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.datastructures import CallbackDict

auth = Blueprint("xfa_auth", __name__)
PROVIDERS = {"google"}
OAUTH_STATE_TTL = 600


def _db_path() -> Path:
    # Shared with xfa_agent.accounts: one account database for the whole product.
    configured = os.getenv("XFA_DATABASE_PATH", "").strip()
    return Path(configured or (Path("instance") / "xfa.sqlite3")).expanduser().resolve()


@contextmanager
def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


_db_init_lock = threading.Lock()
_initialized_databases: set[str] = set()


def _init_db() -> None:
    path_key = str(_db_path())
    if path_key in _initialized_databases:
        return
    with _db_init_lock:
        if path_key in _initialized_databases:
            return
        # Reuse the existing XFA user, OAuth identity and integration schema.
        from xfa_agent.accounts import init_db as init_accounts_db
        init_accounts_db()
        with _connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS xfa_sessions (
                    sid TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS xfa_sessions_expires_idx ON xfa_sessions(expires);
                """
            )
        _initialized_databases.add(path_key)


class _XFAUserSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=False):
        def on_update(_self):
            _self.modified = True
        super().__init__(initial, on_update)
        self.sid = sid or secrets.token_urlsafe(32)
        self.new = new
        self.modified = False


class _SQLiteSessionInterface(SessionInterface):
    """Store session contents server-side; the browser cookie contains only a signed random ID."""
    salt = "xfa-server-session-v1"

    def _serializer(self, app):
        return URLSafeTimedSerializer(app.secret_key, salt=self.salt)

    def open_session(self, app, req):
        _init_db()
        # Fail closed if the deployment secret is missing or was rotated away.
        # Old cookies must not make an unconfigured app crash.
        if not app.secret_key:
            return _XFAUserSession(new=True)
        cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
        signed_id = req.cookies.get(cookie_name)
        if signed_id:
            try:
                sid = self._serializer(app).loads(
                    signed_id,
                    max_age=int(app.permanent_session_lifetime.total_seconds()),
                )
            except (BadSignature, SignatureExpired, TypeError, ValueError):
                sid = None
            if isinstance(sid, str) and 24 <= len(sid) <= 128:
                with _connect() as db:
                    row = db.execute(
                        "SELECT data, expires FROM xfa_sessions WHERE sid=?", (sid,)
                    ).fetchone()
                if row and int(row["expires"]) > int(time.time()):
                    try:
                        data = json.loads(row["data"])
                        if isinstance(data, dict):
                            return _XFAUserSession(data, sid=sid)
                    except (TypeError, json.JSONDecodeError):
                        pass
        return _XFAUserSession(new=True)

    def save_session(self, app, sess, response):
        name = app.config.get("SESSION_COOKIE_NAME", "session")
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        if not sess:
            with _connect() as db:
                db.execute("DELETE FROM xfa_sessions WHERE sid=?", (sess.sid,))
            if sess.modified:
                response.delete_cookie(
                    name, domain=domain, path=path,
                    secure=self.get_cookie_secure(app),
                    httponly=self.get_cookie_httponly(app),
                    samesite=self.get_cookie_samesite(app),
                )
            return
        now = int(time.time())
        max_age = int(app.permanent_session_lifetime.total_seconds()) if sess.permanent else 43200
        expires_at = now + max_age
        payload = json.dumps(dict(sess), ensure_ascii=False, separators=(",", ":"))
        with _connect() as db:
            db.execute(
                "INSERT INTO xfa_sessions(sid, data, expires) VALUES(?,?,?) "
                "ON CONFLICT(sid) DO UPDATE SET data=excluded.data, expires=excluded.expires",
                (sess.sid, payload, expires_at),
            )
            db.execute("DELETE FROM xfa_sessions WHERE expires <= ?", (now,))
        signed = self._serializer(app).dumps(sess.sid)
        response.set_cookie(
            name, signed, expires=self.get_expiration_time(app, sess),
            httponly=self.get_cookie_httponly(app), secure=self.get_cookie_secure(app),
            samesite=self.get_cookie_samesite(app), path=path, domain=domain,
        )


def _auth_ready() -> bool:
    return bool(current_app.secret_key and os.getenv("FLASK_SECRET_KEY", "").strip())


def _provider_credentials(provider: str):
    if provider != "google":
        raise ValueError("Unsupported login provider")
    return os.getenv("GOOGLE_CLIENT_ID", "").strip(), os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

def _callback_uri(provider: str) -> str:
    explicit = os.getenv(provider.upper() + "_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    base = os.getenv("XFA_PUBLIC_BASE_URL", "").strip().rstrip("/")
    path = url_for("xfa_auth.callback", provider=provider)
    return base + path if base else url_for("xfa_auth.callback", provider=provider, _external=True)


def _http_json(url: str, *, data=None, headers=None) -> dict:
    payload = None
    request_headers = {"Accept": "application/json", "User-Agent": "XFA-Auth/1.0"}
    if headers:
        request_headers.update(headers)
    if data is not None:
        payload = urllib.parse.urlencode(data).encode("utf-8")
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=payload, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = response.read(1024 * 1024)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Kimlik sağlayıcısına bağlanılamadı.") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Kimlik sağlayıcısından geçersiz yanıt alındı.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Kimlik sağlayıcısından geçersiz yanıt alındı.")
    return value


def _provider_profile(provider: str, code: str, verifier: str) -> dict:
    if provider != "google":
        raise ValueError("Unsupported login provider")
    client_id, client_secret = _provider_credentials("google")
    token = _http_json("https://oauth2.googleapis.com/token", data={
        "client_id": client_id, "client_secret": client_secret,
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": _callback_uri("google"), "code_verifier": verifier,
    })
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Google giriş izni vermedi.")
    profile = _http_json("https://openidconnect.googleapis.com/v1/userinfo",
                         headers={"Authorization": "Bearer " + access_token})
    subject = str(profile.get("sub") or "").strip()
    verified = profile.get("email_verified") is True
    email = str(profile.get("email") or "").strip().lower() if verified else ""
    name = str(profile.get("name") or profile.get("given_name") or "Google kullanıcısı").strip()
    if not subject:
        raise RuntimeError("Google hesap kimliğini döndürmedi.")
    return {"subject": subject, "email": email or None, "name": name[:100]}

def _csrf_valid(value: str | None) -> bool:
    expected = session.get("xfa_csrf")
    return bool(expected and value and hmac.compare_digest(str(expected), str(value)))


def _redirect_error(code: str):
    return redirect("/xfa?auth_error=" + urllib.parse.quote(code, safe=""))


def _set_user_session(user_id: str, profile: dict, provider: str) -> None:
    old_sid = getattr(session, "sid", None)
    session.clear()
    if old_sid:
        with _connect() as db:
            db.execute("DELETE FROM xfa_sessions WHERE sid=?", (old_sid,))
        session.sid = secrets.token_urlsafe(32)
    session.permanent = True
    session["xfa_user_id"] = user_id
    session["xfa_display_name"] = profile["name"]
    session["xfa_email"] = profile.get("email")
    session["xfa_login_provider"] = provider
    session["xfa_csrf"] = secrets.token_urlsafe(32)


@auth.get("/auth/providers")
def available_providers():
    google_id, google_secret = _provider_credentials("google")
    return jsonify({"session_ready": _auth_ready(), "google": bool(google_id and google_secret and _auth_ready())})


@auth.get("/auth/login/<provider>")
def login(provider: str):
    if provider != "google":
        return jsonify({"error": "Desteklenmeyen giriş yöntemi."}), 404
    return _start_oauth()


def _start_oauth():
    if not _auth_ready():
        return _redirect_error("server_not_configured")
    client_id, client_secret = _provider_credentials("google")
    if not client_id or not client_secret:
        return _redirect_error("google_not_configured")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = __import__("base64").urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    session["xfa_oauth_google"] = {"state": state, "verifier": verifier, "expires": int(time.time()) + OAUTH_STATE_TTL}
    session.permanent = True
    params = {
        "client_id": client_id, "redirect_uri": _callback_uri("google"),
        "response_type": "code", "scope": "openid email profile",
        "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256", "prompt": "select_account",
    }
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params))

@auth.get("/auth/callback/<provider>")
def callback(provider: str):
    if provider != "google":
        return _redirect_error("unsupported_provider")
    if not _auth_ready():
        return _redirect_error("server_not_configured")
    pending = session.get("xfa_oauth_google")
    supplied_state = request.args.get("state", "")
    if (not isinstance(pending, dict) or not supplied_state
        or not hmac.compare_digest(str(pending.get("state", "")), supplied_state)
        or int(pending.get("expires", 0)) < int(time.time())):
        session.pop("xfa_oauth_google", None)
        return _redirect_error("state_invalid")
    session.pop("xfa_oauth_google", None)
    if request.args.get("error"):
        return _redirect_error("permission_denied")
    code = request.args.get("code", "")
    if not code or len(code) > 4096:
        return _redirect_error("code_missing")
    try:
        profile = _provider_profile("google", code, str(pending.get("verifier", "")))
        _init_db()
        with _connect() as db:
            identity = db.execute(
                "SELECT user_id FROM xfa_oauth_accounts WHERE provider='google' AND provider_subject=?",
                (profile["subject"],)).fetchone()
            email_taken = bool(profile.get("email") and db.execute(
                "SELECT 1 FROM xfa_users WHERE email=? COLLATE NOCASE", (profile["email"],)).fetchone())
        if identity:
            user_id = identity["user_id"]
        else:
            from xfa_agent.accounts import create_user
            account_email = profile.get("email")
            if not account_email or email_taken:
                opaque = hashlib.sha256(("google:" + profile["subject"]).encode()).hexdigest()[:24]
                account_email = f"google-{opaque}@oauth.xfa.invalid"
            try:
                created = create_user(account_email, secrets.token_urlsafe(48))
            except ValueError:
                opaque = hashlib.sha256(("google:" + profile["subject"]).encode()).hexdigest()[:24]
                created = create_user(f"google-{opaque}@oauth.xfa.invalid", secrets.token_urlsafe(48))
            user_id = created["id"]
            try:
                with _connect() as db:
                    concurrent = db.execute(
                        "SELECT user_id FROM xfa_oauth_accounts WHERE provider='google' AND provider_subject=?",
                        (profile["subject"],)).fetchone()
                    if concurrent:
                        db.execute("DELETE FROM xfa_users WHERE id=?", (user_id,))
                        user_id = concurrent["user_id"]
                    else:
                        db.execute(
                            "INSERT INTO xfa_oauth_accounts(id, user_id, provider, provider_subject, created_at) VALUES(?,?,?,?,?)",
                            (str(uuid.uuid4()), user_id, "google", profile["subject"], int(time.time())))
            except Exception:
                with _connect() as db:
                    db.execute("DELETE FROM xfa_users WHERE id=?", (user_id,))
                raise
        _set_user_session(user_id, profile, "google")
        return redirect("/xfa?auth_success=1")
    except Exception:
        current_app.logger.exception("XFA Google OAuth callback failed")
        return _redirect_error("provider_error")

@auth.get("/auth/me")
def me():
    if not _auth_ready():
        return jsonify({"authenticated": False, "error": "server_not_configured"}), 503
    user_id = session.get("xfa_user_id")
    if not user_id:
        return jsonify({"authenticated": False})
    _init_db()
    with _connect() as db:
        user = db.execute(
            "SELECT id, email FROM xfa_users WHERE id=?", (user_id,)
        ).fetchone()
        if not user:
            session.clear()
            return jsonify({"authenticated": False}), 401
        providers = [
        row["provider"] for row in db.execute(
            "SELECT provider FROM xfa_oauth_accounts WHERE user_id=? AND provider='google' ORDER BY provider", (user_id,)
        ).fetchall()
    ]
    return jsonify({
        "authenticated": True,
        "user": {"id": user["id"], "name": session.get("xfa_display_name") or "XFA kullanıcısı", "email": session.get("xfa_email")},
        "providers": providers,
        "csrf_token": session.get("xfa_csrf"),
    })


@auth.post("/auth/logout")
def logout():
    if not _auth_ready():
        return jsonify({"error": "Sunucu oturum anahtarı yapılandırılmamış."}), 503
    if not _csrf_valid(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Güvenlik doğrulaması başarısız."}), 403
    session.clear()
    return jsonify({"ok": True})



def register_auth(app) -> None:
    secret = os.getenv("FLASK_SECRET_KEY", "").strip()
    app.secret_key = secret or None
    app.config.update(
        SESSION_COOKIE_NAME="xfa_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.getenv("XFA_COOKIE_SECURE", "true").strip().lower() not in {"0", "false", "no"},
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_PATH="/",
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    )
    app.session_interface = _SQLiteSessionInterface()
    _init_db()
    if "xfa_auth" not in app.blueprints:
        app.register_blueprint(auth)
