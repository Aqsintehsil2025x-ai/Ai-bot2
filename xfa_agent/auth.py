"""Simple email/password authentication for XFA.

Sessions use Flask's signed, HttpOnly cookie implementation. Account records and
password hashes remain in SQLite; HTTP requests do not open SQLite just to load
a session.
"""
from __future__ import annotations

import hmac
import os
import secrets
from datetime import timedelta

from flask import Blueprint, current_app, jsonify, request, session

auth = Blueprint("xfa_auth", __name__)


def _auth_ready() -> bool:
    return bool(current_app.secret_key and os.getenv("FLASK_SECRET_KEY", "").strip())


def _csrf_valid(value: str | None) -> bool:
    expected = session.get("xfa_csrf")
    return bool(expected and value and hmac.compare_digest(str(expected), str(value)))


def _set_user_session(user: dict) -> None:
    # Clear any anonymous or stale session data before establishing the account.
    session.clear()
    session.permanent = True
    session["xfa_user_id"] = user["id"]
    session["xfa_display_name"] = user["email"].split("@", 1)[0][:100] or "XFA istifadəçisi"
    session["xfa_email"] = user["email"]
    session["xfa_login_provider"] = "email"
    session["xfa_csrf"] = secrets.token_urlsafe(32)


@auth.get("/auth/providers")
def available_providers():
    # Google OAuth is intentionally disabled until it is explicitly configured.
    return jsonify({"session_ready": _auth_ready(), "google": False})


@auth.post("/auth/register")
def register_password():
    if not _auth_ready():
        return jsonify({"error": "Sunucu oturum anahtarı yapılandırılmamış."}), 503
    if not _csrf_valid(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Güvenlik doğrulaması başarısız. Sayfayı yenileyip tekrar dene."}), 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Geçerli kayıt bilgileri gönderilmelidir."}), 400
    email, password = payload.get("email"), payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "E-posta ve parola zorunludur."}), 400
    try:
        from xfa_agent.accounts import create_user
        user = create_user(email, password)
    except ValueError as exc:
        message = str(exc)
        if "already exists" in message:
            return jsonify({"error": "Bu e-posta ile hesap açılamadı. E-posta daha önce kullanılmış olabilir."}), 409
        if "Password must" in message:
            return jsonify({"error": "Parola 12 ile 1024 karakter arasında olmalıdır."}), 400
        return jsonify({"error": "Geçerli bir e-posta adresi gir."}), 400
    _set_user_session(user)
    return jsonify({"ok": True})


@auth.post("/auth/login/password")
def login_password():
    if not _auth_ready():
        return jsonify({"error": "Sunucu oturum anahtarı yapılandırılmamış."}), 503
    if not _csrf_valid(request.headers.get("X-CSRF-Token")):
        return jsonify({"error": "Güvenlik doğrulaması başarısız. Sayfayı yenileyip tekrar dene."}), 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Geçerli giriş bilgileri gönderilmelidir."}), 400
    email, password = payload.get("email"), payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "E-posta ve parola zorunludur."}), 400
    from xfa_agent.accounts import verify_user
    user = verify_user(email, password)
    if not user:
        return jsonify({"error": "E-posta veya parola hatalı."}), 401
    _set_user_session(user)
    return jsonify({"ok": True})


@auth.get("/auth/me")
def me():
    if not _auth_ready():
        return jsonify({"authenticated": False, "error": "server_not_configured"}), 503
    user_id = session.get("xfa_user_id")
    if not user_id:
        csrf_token = session.get("xfa_csrf")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["xfa_csrf"] = csrf_token
        return jsonify({"authenticated": False, "csrf_token": csrf_token})

    email = session.get("xfa_email")
    if not isinstance(email, str) or not email:
        session.clear()
        return jsonify({"authenticated": False}), 401
    return jsonify({
        "authenticated": True,
        "user": {
            "id": user_id,
            "name": session.get("xfa_display_name") or "XFA istifadəçisi",
            "email": email,
        },
        "providers": [],
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
    """Register auth routes and initialize account storage once at startup."""
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
    # Flask's built-in secure-cookie session interface is intentionally retained.
    # No database read/write is needed when opening or saving an HTTP session.
    from xfa_agent.accounts import init_db
    init_db()
    if "xfa_auth" not in app.blueprints:
        app.register_blueprint(auth)
