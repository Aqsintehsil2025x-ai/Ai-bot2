"""Restricted project-workspace tools for XFA.

Reads are bounded and confined to the configured project root. Writes are
new-file-only and require a short-lived, explicit approval from the dashboard.
"""
from __future__ import annotations

import os
import hashlib
import secrets
import threading
import time
from collections import deque
from pathlib import Path

DATA_ROOT = Path(os.getenv("XFA_USER_DATA_DIR", str(Path(os.getenv("XFA_DATA_DIR", "data/xfa")) / "workspaces"))).expanduser().resolve()
BLOCKED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache"}
BLOCKED_NAMES = {".env", ".env.local", ".env.production", "cookies.txt", "secrets.json"}
READ_LIMIT = 64 * 1024
WRITE_LIMIT = 32 * 1024
WRITE_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".css", ".html"}
_pending: dict[str, dict] = {}
_lock = threading.Lock()
_audit = deque(maxlen=100)


def _user_root(user_id: str | None) -> Path:
    uid = str(user_id or "").strip()
    if not uid or len(uid) > 64 or any(not (ch.isalnum() or ch in "-_") for ch in uid):
        raise ValueError("A valid authenticated user workspace is required")
    root = (DATA_ROOT / uid).resolve()
    if root != DATA_ROOT and DATA_ROOT not in root.parents:
        raise ValueError("Invalid user workspace")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _record(user_id: str, action: str, path: str, status: str) -> None:
    with _lock:
        _audit.append({"time": int(time.time()), "user_id": user_id, "action": action, "path": path[:180], "status": status})


def audit_log(user_id: str | None = None) -> list[dict]:
    uid = str(user_id or "")
    with _lock:
        return [{k: v for k, v in item.items() if k != "user_id"} for item in _audit if item.get("user_id") == uid]


def _safe_path(relative: str, user_id: str | None = None) -> Path:
    root = _user_root(user_id)
    raw = str(relative or "").strip()
    if not raw or len(raw) > 300 or "\x00" in raw or Path(raw).is_absolute() or ".." in Path(raw).parts:
        raise ValueError("A valid relative workspace path without parent traversal is required")
    candidate = (root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Path is outside the user's XFA workspace")
    parts = Path(raw).parts
    if any(part in BLOCKED_PARTS or part.startswith(".") for part in parts):
        raise ValueError("Hidden, dependency, and internal paths are blocked")
    if candidate.name.lower() in BLOCKED_NAMES or candidate.name.lower().endswith((".pem", ".key", ".p12")):
        raise ValueError("Sensitive files are blocked")
    return candidate


def list_files(relative: str = "", limit: int = 100, user_id: str | None = None) -> list[dict]:
    root = _user_root(user_id)
    folder = root if not relative or relative == "." else _safe_path(relative, user_id)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Directory does not exist")
    found = []
    for item in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if item.name.startswith(".") or item.name in BLOCKED_PARTS or item.name.lower() in BLOCKED_NAMES:
            continue
        if item.is_symlink():
            continue
        found.append({"name": item.name, "path": item.relative_to(root).as_posix(), "type": "directory" if item.is_dir() else "file"})
        if len(found) >= max(1, min(int(limit), 100)):
            break
    _record(str(user_id), "list", str(relative or "."), "ok")
    return found


def read_file(relative: str, user_id: str | None = None) -> dict:
    root = _user_root(user_id)
    path = _safe_path(relative, user_id)
    if not path.is_file() or path.is_symlink():
        raise ValueError("File does not exist or is not a regular file")
    if path.stat().st_size > READ_LIMIT:
        raise ValueError("File is larger than the 64 KiB read limit")
    data = path.read_text(encoding="utf-8")
    _record(str(user_id), "read", relative, "ok")
    return {"path": path.relative_to(root).as_posix(), "content": data}


def propose_new_file(relative: str, content: str, user_id: str | None = None) -> str:
    root = _user_root(user_id)
    path = _safe_path(relative, user_id)
    text = str(content)
    if path.suffix.lower() not in WRITE_SUFFIXES:
        raise ValueError("This file type is not enabled for approved writes")
    if len(text.encode("utf-8")) > WRITE_LIMIT:
        raise ValueError("New file content exceeds 32 KiB")
    if path.exists():
        raise ValueError("XFA can currently create new files only; existing files are never overwritten")
    approval_id = secrets.token_urlsafe(18)
    with _lock:
        _pending[approval_id] = {"path": path, "content": text, "user_id": str(user_id), "expires": time.monotonic() + 600}
    _record(str(user_id), "propose_create", relative, "awaiting_approval")
    return approval_id


def propose_update_file(relative: str, content: str, user_id: str | None = None) -> str:
    root = _user_root(user_id)
    path = _safe_path(relative, user_id)
    text = str(content)
    if path.suffix.lower() not in WRITE_SUFFIXES:
        raise ValueError("This file type is not enabled for approved updates")
    if not path.is_file() or path.is_symlink():
        raise ValueError("Only existing regular files can be updated")
    current = path.read_bytes()
    if len(current) > READ_LIMIT:
        raise ValueError("Existing file is larger than the 64 KiB update limit")
    if len(text.encode("utf-8")) > WRITE_LIMIT:
        raise ValueError("Updated content exceeds 32 KiB")
    approval_id = secrets.token_urlsafe(18)
    with _lock:
        _pending[approval_id] = {
            "path": path,
            "content": text,
            "user_id": str(user_id),
            "expires": time.monotonic() + 600,
            "operation": "update",
            "original_sha256": hashlib.sha256(current).hexdigest(),
        }
    _record(str(user_id), "propose_update", relative, "awaiting_approval")
    return approval_id


def approve_new_file(approval_id: str, user_id: str | None = None) -> dict:
    with _lock:
        item = _pending.pop(str(approval_id), None)
    if not item or item["expires"] < time.monotonic() or item.get("user_id") != str(user_id):
        raise ValueError("Approval is missing, expired, or belongs to another account")
    root = _user_root(user_id)
    path: Path = item["path"]
    if path != root and root not in path.resolve().parents:
        raise ValueError("Path is outside the user's XFA workspace")
    if item.get("operation") == "update":
        if not path.is_file() or path.is_symlink():
            raise ValueError("Target is no longer a regular file")
        current = path.read_bytes()
        if hashlib.sha256(current).hexdigest() != item["original_sha256"]:
            raise ValueError("File changed after the proposal; refusing a stale update")
        temporary = path.with_name(path.name + ".xfa-tmp-" + secrets.token_hex(4))
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                stream.write(item["content"])
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        _record(str(user_id), "update_file", path.relative_to(root).as_posix(), "approved")
        return {"path": path.relative_to(root).as_posix(), "operation": "updated",
                "bytes": len(item["content"].encode("utf-8"))}
    if path.exists():
        raise ValueError("The target now exists; refusing to overwrite it")
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_parent = path.parent.resolve()
    if resolved_parent != root and root not in resolved_parent.parents:
        raise ValueError("Path is outside the user's XFA workspace")
    with path.open("x", encoding="utf-8") as stream:
        stream.write(item["content"])
    _record(str(user_id), "create_file", path.relative_to(root).as_posix(), "approved")
    return {"path": path.relative_to(root).as_posix(), "operation": "created",
            "bytes": len(item["content"].encode("utf-8"))}
