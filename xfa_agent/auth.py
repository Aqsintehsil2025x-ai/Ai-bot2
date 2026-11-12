"""XFA account authentication and consent-based Discord notifications.

OAuth access tokens are exchanged server-side and discarded. Only provider
subject IDs and minimal profile information are kept in SQLite.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, redirect, request, session, url_for

auth = Blueprint("xfa_auth", __name__)
PROVIDERS = {"google", "discord"}
OAUTH_STATE_TTL = 600


def _data_dir() -> Path:
    return Path(os.getenv("XFA_DATA_DIR", "data/xfa")).expanduser().resolve()


def _db_path() -> Path:
    return Path(os.getenv("XFA_AUTH_DB", str(_data_dir() / "auth.sqlite3"))).expanduser().resolve()


@contextmanager
def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA journal_mode = WAL")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _init_db() -> None:
    with _connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                email TEXT,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identities (
                provider TEXT NOT NULL,
                subject TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                provider_email TEXT,
                linked_at INTEGER NOT NULL,
                PRIMARY KEY (provider, subject)
            );
            CREATE INDEX IF NOT EXISTS identities_user_id_idx ON identities(user_id);
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                discord_enabled INTEGER NOT NULL DEFAULT 0
            );
            """
        )


def _auth_ready() -> bool:
    return bool(current_app.secret_key and os.getenv("FLASK_SECRET_KEY", "").strip())


def _provider_credentials(provider: str):
    if provider == "google":
        return os.getenv("GOOGLE_CLIENT_ID", "").strip(), os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if provider == "discord":
        return os.getenv("DISCORD_CLIENT_ID", "").strip(), os.getenv("DISCORD_CLIENT_SECRET", "").strip()
    raise ValueError("Unsupported login provider")


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
    client_id, client_secret = _provider_credentials(provider)
    token_url = (
        "https://oauth2.googleapis.com/token"
        if provider == "google"
        else "https://discord.com/api/oauth2/token"
    )
    token = _http_json(
        token_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _callback_uri(provider),
            "code_verifier": verifier,
        },
    )
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Giriş sağlayıcısı erişim izni vermedi.")
    user_url = (
        "https://openidconnect.googleapis.com/v1/userinfo"
        if provider == "google"
        else "https://discord.com/api/users/@me"
    )
    profile = _http_json(user_url, headers={"Authorization": "Bearer " + access_token})
    if provider == "google":
        subject = str(profile.get("sub") or "").strip()
        verified = profile.get("email_verified") is True
        email = str(profile.get("email") or "").strip().lower() if verified else ""
        name = str(profile.get("name") or profile.get("given_name") or "Google kullanıcısı").strip()
    else:
        subject = str(profile.get("id") or "").strip()
        verified = profile.get("verified") is True
        email = str(profile.get("email") or "").strip().lower() if verified else ""
        name = str(profile.get("global_name") or profile.get("username") or "Discord kullanıcısı").strip()
    if not subject:
        raise RuntimeError("Kimlik sağlayıcısı hesap kimliğini döndürmedi.")
    return {"subject": subject, "email": email or None, "name": name[:100]}


def _csrf_valid(value: str | None) -> bool:
    expected = session.get("xfa_csrf")
    return bool(expected and value and hmac.compare_digest(str(expected), str(value)))


def _redirect_error(code: str):
    return redirect("/xfa?auth_error=" + urllib.parse.quote(code, safe=""))


def _set_user_session(user_id: str, profile: dict, provider: str) -> None:
    session.clear()
    session.permanent = True
    session["xfa_user_id"] = user_id
    session["xfa_display_name"] = profile["name"]
    session["xfa_email"] = profile.get("email")
    session["xfa_login_provider"] = provider
    session["xfa_csrf"] = secrets.token_urlsafe(32)


@auth.get("/auth/login/<provider>")
def login(provider: str):
    return _start_oauth(provider, "login")


@auth.post("/auth/link/<provider>")
def link(provider: str):
    if provider not in PROVIDERS:
        return jsonify({"error": "Desteklenmeyen sağlayıcı."}), 404
    if not _auth_ready() or not session.get("xfa_user_id"):
        return jsonify({"error": "Önce hesabına giriş yap."}), 401
    if not _csrf_valid(request.form.get("csrf_token")):
        return jsonify({"error": "Güvenlik doğrulaması başarısız."}), 403
    return _start_oauth(provider, "link")


def _start_oauth(provider: str, intent: str):
    if provider not in PROVIDERS:
        return jsonify({"error": "Desteklenmeyen giriş yöntemi."}), 404
    if not _auth_ready():
        return _redirect_error("server_not_configured")
    client_id, client_secret = _provider_credentials(provider)
    if not client_id or not client_secret:
        return _redirect_error(provider + "_not_configured")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = __import__("base64").urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    session["xfa_oauth_" + provider] = {
        "state": state,
        "verifier": verifier,
        "intent": intent,
        "user_id": session.get("xfa_user_id") if intent == "link" else None,
        "expires": int(time.time()) + OAUTH_STATE_TTL,
    }
    session.permanent = True
    if provider == "google":
        endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        scope = "openid email profile"
    else:
        endpoint = "https://discord.com/oauth2/authorize"
        scope = "identify email"
    params = {
        "client_id": client_id,
        "redirect_uri": _callback_uri(provider),
        "response_type": "code",
        "scope": scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if provider == "google":
        params["prompt"] = "select_account"
    return redirect(endpoint + "?" + urllib.parse.urlencode(params))


@auth.get("/auth/callback/<provider>")
def callback(provider: str):
    if provider not in PROVIDERS:
        return _redirect_error("unsupported_provider")
    if not _auth_ready():
        return _redirect_error("server_not_configured")
    pending = session.get("xfa_oauth_" + provider)
    supplied_state = request.args.get("state", "")
    if (
        not isinstance(pending, dict)
        or not supplied_state
        or not hmac.compare_digest(str(pending.get("state", "")), supplied_state)
        or int(pending.get("expires", 0)) < int(time.time())
    ):
        session.pop("xfa_oauth_" + provider, None)
        return _redirect_error("state_invalid")
    session.pop("xfa_oauth_" + provider, None)
    if request.args.get("error"):
        return _redirect_error("permission_denied")
    code = request.args.get("code", "")
    if not code or len(code) > 4096:
        return _redirect_error("code_missing")
    try:
        profile = _provider_profile(provider, code, str(pending.get("verifier", "")))
        _init_db()
        intent = pending.get("intent", "login")
        if intent == "link":
            user_id = str(pending.get("user_id") or "")
            if not user_id or session.get("xfa_user_id") != user_id:
                return _redirect_error("link_session_expired")
            with _connect() as db:
                existing = db.execute(
                    "SELECT user_id FROM identities WHERE provider=? AND subject=?",
                    (provider, profile["subject"]),
                ).fetchone()
                if existing and existing["user_id"] != user_id:
                    return _redirect_error("identity_already_used")
                db.execute(
                    "INSERT OR IGNORE INTO identities(provider, subject, user_id, provider_email, linked_at) VALUES(?,?,?,?,?)",
                    (provider, profile["subject"], user_id, profile.get("email"), int(time.time())),
                )
                if profile.get("email"):
                    db.execute("UPDATE users SET email=COALESCE(email, ?) WHERE id=?", (profile["email"], user_id))
            session["xfa_csrf"] = secrets.token_urlsafe(32)
            return redirect("/xfa?auth_success=linked")
        with _connect() as db:
            identity = db.execute(
                "SELECT user_id FROM identities WHERE provider=? AND subject=?",
                (provider, profile["subject"]),
            ).fetchone()
            if identity:
                user_id = identity["user_id"]
                db.execute(
                    "UPDATE users SET display_name=?, email=COALESCE(?, email) WHERE id=?",
                    (profile["name"], profile.get("email"), user_id),
                )
                db.execute(
                    "UPDATE identities SET provider_email=? WHERE provider=? AND subject=?",
                    (profile.get("email"), provider, profile["subject"]),
                )
            else:
                user_id = str(uuid.uuid4())
                db.execute(
                    "INSERT INTO users(id, display_name, email, created_at) VALUES(?,?,?,?)",
                    (user_id, profile["name"], profile.get("email"), int(time.time())),
                )
                db.execute(
                    "INSERT INTO identities(provider, subject, user_id, provider_email, linked_at) VALUES(?,?,?,?,?)",
                    (provider, profile["subject"], user_id, profile.get("email"), int(time.time())),
                )
        _set_user_session(user_id, profile, provider)
        return redirect("/xfa?auth_success=1")
    except Exception:
        current_app.logger.exception("XFA OAuth callback failed for provider %s", provider)
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
            "SELECT id, display_name, email FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not user:
            session.clear()
            return jsonify({"authenticated": False}), 401
        providers = [
            row["provider"] for row in db.execute(
                "SELECT provider FROM identities WHERE user_id=? ORDER BY provider", (user_id,)
            ).fetchall()
        ]
        pref = db.execute(
            "SELECT discord_enabled FROM notification_preferences WHERE user_id=?", (user_id,)
        ).fetchone()
    return jsonify({
        "authenticated": True,
        "user": {"id": user["id"], "name": user["display_name"], "email": user["email"]},
        "providers": providers,
        "discord_notifications": bool(pref["discord_enabled"]) if pref else False,
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


@auth.post("/auth/discord-notifications")
def discord_notifications():
    if not _auth_ready() or not session.get("xfa_user_id"):
        return jsonify({"error": "Önce giriş yap."}), 401
    if not _csrf_valid(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Güvenlik doğrulaması başarısız."}), 403
    body = request.get_json(silent=True) or {}
    enabled = body.get("enabled") is True
    user_id = session["xfa_user_id"]
    _init_db()
    with _connect() as db:
        linked = db.execute(
            "SELECT 1 FROM identities WHERE provider='discord' AND user_id=?", (user_id,)
        ).fetchone()
        if enabled and not linked:
            return jsonify({"error": "Önce Discord hesabını bağlamalısın."}), 409
        db.execute(
            "INSERT INTO notification_preferences(user_id, discord_enabled) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET discord_enabled=excluded.discord_enabled",
            (user_id, 1 if enabled else 0),
        )
    return jsonify({"ok": True, "enabled": enabled})


def send_discord_notification(app, user_id: str, message: str) -> bool:
    """Send a DM only after the account owner has explicitly opted in."""
    clean = str(message or "").strip()
    if not clean or len(clean) > 1800:
        raise ValueError("Bildirim metni 1-1800 karakter olmalı.")
    _init_db()
    with _connect() as db:
        row = db.execute(
            "SELECT i.subject, p.discord_enabled FROM identities i "
            "JOIN notification_preferences p ON p.user_id=i.user_id "
            "WHERE i.user_id=? AND i.provider='discord'",
            (user_id,),
        ).fetchone()
    if not row or not row["discord_enabled"]:
        return False
    bot = app.config.get("XFA_DISCORD_BOT")
    if not bot or not bot.is_ready():
        raise RuntimeError("Discord botu şu anda çevrimiçi değil.")
    async def _deliver():
        user = await bot.fetch_user(int(row["subject"]))
        await user.send(clean)
    future = asyncio.run_coroutine_threadsafe(_deliver(), bot.loop)
    try:
        future.result(timeout=15)
    except Exception as exc:
        future.cancel()
        raise RuntimeError("Discord DM gönderilemedi. Kullanıcının DM ayarlarını ve bot erişimini kontrol edin.") from exc
    return True


@auth.post("/auth/discord-notifications/test")
def test_discord_notifications():
    if not _auth_ready() or not session.get("xfa_user_id"):
        return jsonify({"error": "Önce giriş yap."}), 401
    if not _csrf_valid(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Güvenlik doğrulaması başarısız."}), 403
    try:
        sent = send_discord_notification(
            current_app._get_current_object(),
            session["xfa_user_id"],
            "XFA bağlantı testi başarılı. Discord bildirimlerini etkinleştirdin.",
        )
        if not sent:
            return jsonify({"error": "Discord bildirimlerini önce etkinleştir."}), 409
        return jsonify({"ok": True})
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 503


def register_auth(app) -> None:
    secret = os.getenv("FLASK_SECRET_KEY", "").strip()
    app.secret_key = secret or None
    app.config.update(
        SESSION_COOKIE_NAME="xfa_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.getenv("XFA_COOKIE_SECURE", "true").strip().lower() not in {"0", "false", "no"},
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_PATH="/",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
    )
    _init_db()
    if "xfa_auth" not in app.blueprints:
        app.register_blueprint(auth)
