"""User-scoped account and encrypted integration storage for public XFA.

This module intentionally contains no HTTP routes. Authentication/session routes
are added only after the storage primitives and ownership boundaries are tested.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PASSWORD_N = 2**14
PASSWORD_R = 8
PASSWORD_P = 1
PASSWORD_DKLEN = 64
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 1024


def _database_path() -> Path:
    configured = os.getenv("XFA_DATABASE_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path("instance") / "xfa.sqlite3"


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    """Create the initial schema. Safe to call at every application startup."""
    with _connection() as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS xfa_users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS xfa_oauth_accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES xfa_users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                provider_subject TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(provider, provider_subject)
            );

            CREATE TABLE IF NOT EXISTS xfa_integrations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES xfa_users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                provider_account_id TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                scopes_json TEXT NOT NULL DEFAULT '[]',
                token_ciphertext BLOB NOT NULL,
                token_nonce BLOB NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(user_id, provider, provider_account_id)
            );

            CREATE TABLE IF NOT EXISTS xfa_resources (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES xfa_users(id) ON DELETE CASCADE,
                provider TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                external_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL,
                UNIQUE(user_id, provider, resource_type, external_id)
            );

            CREATE TABLE IF NOT EXISTS xfa_devices (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES xfa_users(id) ON DELETE CASCADE,
                device_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                paired_at INTEGER NOT NULL,
                revoked_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS xfa_audit_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES xfa_users(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                target_type TEXT NOT NULL DEFAULT '',
                target_id TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_xfa_integrations_user
                ON xfa_integrations(user_id, provider);
            CREATE INDEX IF NOT EXISTS idx_xfa_resources_user
                ON xfa_resources(user_id, provider);
            CREATE INDEX IF NOT EXISTS idx_xfa_devices_user
                ON xfa_devices(user_id, revoked_at);
            CREATE INDEX IF NOT EXISTS idx_xfa_audit_user
                ON xfa_audit_events(user_id, created_at);
            """
        )


def _normalize_email(email: str) -> str:
    value = str(email or "").strip().lower()
    if len(value) > 254 or value.count("@") != 1:
        raise ValueError("A valid email address is required")
    local, domain = value.rsplit("@", 1)
    if not local or not domain or "." not in domain or any(ch.isspace() for ch in value):
        raise ValueError("A valid email address is required")
    return value


def _password_bytes(password: str) -> bytes:
    value = str(password or "")
    if not PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} characters")
    return value.encode("utf-8")


def _derive_password(password: bytes, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password, salt=salt, n=PASSWORD_N, r=PASSWORD_R, p=PASSWORD_P,
        dklen=PASSWORD_DKLEN, maxmem=128 * 1024 * 1024,
    )


def create_user(email: str, password: str) -> dict:
    """Create a local account; return only non-secret account fields."""
    normalized = _normalize_email(email)
    raw_password = _password_bytes(password)
    salt = secrets.token_bytes(16)
    password_hash = _derive_password(raw_password, salt)
    user_id = str(uuid.uuid4())
    import time
    with _connection() as db:
        try:
            db.execute(
                "INSERT INTO xfa_users(id,email,password_salt,password_hash,created_at) VALUES(?,?,?,?,?)",
                (user_id, normalized, salt, password_hash, int(time.time())),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email already exists") from exc
    return {"id": user_id, "email": normalized}


def verify_user(email: str, password: str) -> dict | None:
    """Verify credentials without revealing whether an email exists."""
    try:
        normalized = _normalize_email(email)
        raw_password = _password_bytes(password)
    except ValueError:
        return None
    with _connection() as db:
        row = db.execute(
            "SELECT id,email,password_salt,password_hash FROM xfa_users WHERE email = ?",
            (normalized,),
        ).fetchone()
    if row is None:
        # Perform a dummy derivation to reduce account-enumeration timing differences.
        _derive_password(raw_password, b"\x00" * 16)
        return None
    candidate = _derive_password(raw_password, bytes(row["password_salt"]))
    if not hmac.compare_digest(candidate, bytes(row["password_hash"])):
        return None
    return {"id": row["id"], "email": row["email"]}


def _encryption_key() -> bytes:
    encoded = os.getenv("XFA_TOKEN_ENCRYPTION_KEY", "").strip()
    if not encoded:
        raise RuntimeError("XFA_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except Exception as exc:
        raise RuntimeError("XFA_TOKEN_ENCRYPTION_KEY must be URL-safe base64") from exc
    if len(key) != 32:
        raise RuntimeError("XFA_TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def _aad(user_id: str, provider: str, provider_account_id: str) -> bytes:
    return json.dumps(
        [str(user_id), str(provider).lower(), str(provider_account_id)],
        separators=(",", ":"),
    ).encode("utf-8")


def save_integration(
    user_id: str,
    provider: str,
    provider_account_id: str,
    access_token: str,
    refresh_token: str = "",
    scopes: list[str] | None = None,
    display_name: str = "",
) -> dict:
    """Encrypt provider credentials and upsert them under exactly one user."""
    provider = str(provider or "").strip().lower()
    account_id = str(provider_account_id or "").strip()
    access = str(access_token or "")
    if not provider or not account_id or not access or len(access) > 20000:
        raise ValueError("Provider, account ID, and a valid access token are required")
    if len(str(refresh_token)) > 20000:
        raise ValueError("Refresh token is too long")
    import time
    user_id = str(user_id)
    payload = json.dumps(
        {"access_token": access, "refresh_token": str(refresh_token)},
        separators=(",", ":"),
    ).encode("utf-8")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(
        nonce, payload, _aad(user_id, provider, account_id)
    )
    integration_id = str(uuid.uuid4())
    safe_scopes = sorted({str(scope)[:120] for scope in (scopes or []) if str(scope).strip()})[:100]
    with _connection() as db:
        owner = db.execute("SELECT 1 FROM xfa_users WHERE id = ?", (user_id,)).fetchone()
        if owner is None:
            raise ValueError("Account does not exist")
        db.execute(
            """
            INSERT INTO xfa_integrations
                (id,user_id,provider,provider_account_id,display_name,scopes_json,
                 token_ciphertext,token_nonce,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id,provider,provider_account_id) DO UPDATE SET
                display_name=excluded.display_name,
                scopes_json=excluded.scopes_json,
                token_ciphertext=excluded.token_ciphertext,
                token_nonce=excluded.token_nonce,
                updated_at=excluded.updated_at
            """,
            (integration_id, user_id, provider, account_id, str(display_name)[:200],
             json.dumps(safe_scopes), ciphertext, nonce, int(time.time())),
        )
        row = db.execute(
            "SELECT id FROM xfa_integrations WHERE user_id=? AND provider=? AND provider_account_id=?",
            (user_id, provider, account_id),
        ).fetchone()
    return {"id": row["id"], "provider": provider, "account_id": account_id,
            "display_name": str(display_name)[:200], "scopes": safe_scopes}


def list_integrations(user_id: str) -> list[dict]:
    """Return connection metadata only; never return credential ciphertext or tokens."""
    with _connection() as db:
        rows = db.execute(
            """SELECT id,provider,provider_account_id,display_name,scopes_json,updated_at
               FROM xfa_integrations WHERE user_id=? ORDER BY provider,display_name""",
            (str(user_id),),
        ).fetchall()
    return [
        {"id": row["id"], "provider": row["provider"],
         "account_id": row["provider_account_id"], "display_name": row["display_name"],
         "scopes": json.loads(row["scopes_json"]), "updated_at": row["updated_at"]}
        for row in rows
    ]


def get_integration_tokens(user_id: str, integration_id: str) -> dict | None:
    """Internal provider adapter helper; ownership is enforced in the SQL query."""
    with _connection() as db:
        row = db.execute(
            """SELECT provider,provider_account_id,token_ciphertext,token_nonce
               FROM xfa_integrations WHERE user_id=? AND id=?""",
            (str(user_id), str(integration_id)),
        ).fetchone()
    if row is None:
        return None
    plaintext = AESGCM(_encryption_key()).decrypt(
        bytes(row["token_nonce"]), bytes(row["token_ciphertext"]),
        _aad(str(user_id), row["provider"], row["provider_account_id"]),
    )
    return json.loads(plaintext.decode("utf-8"))


def disconnect_integration(user_id: str, integration_id: str) -> bool:
    """Delete only a connection owned by the authenticated user."""
    with _connection() as db:
        cursor = db.execute(
            "DELETE FROM xfa_integrations WHERE user_id=? AND id=?",
            (str(user_id), str(integration_id)),
        )
    return cursor.rowcount == 1
