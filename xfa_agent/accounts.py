"""User-scoped account storage for public XFA.

This module intentionally contains no HTTP routes. Authentication/session routes
are added only after the storage primitives and ownership boundaries are tested.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

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
        # Remove legacy per-user provider credentials from existing installations.
        db.execute("DROP TABLE IF EXISTS xfa_integrations")
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


