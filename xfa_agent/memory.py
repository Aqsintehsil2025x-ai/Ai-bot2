"""Explicit, user-controlled, account-scoped memory for XFA.

Nothing is automatically remembered. The user must create a memory item explicitly,
and every read/update/delete is scoped to the authenticated account.
"""
from __future__ import annotations

import json
import time
import uuid

from xfa_agent.accounts import _connection

MAX_ITEMS = 100
MAX_TITLE = 120
MAX_CONTENT = 6000
MAX_TAGS = 12


def _ensure_table() -> None:
    with _connection() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS xfa_memory_items (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES xfa_users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_xfa_memory_user_updated "
            "ON xfa_memory_items(user_id, updated_at DESC)"
        )


def _serialize(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": json.loads(row["tags_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_memories(user_id: str, query: str = "") -> list[dict]:
    _ensure_table()
    query = str(query or "").strip()[:120]
    with _connection() as db:
        if query:
            pattern = "%" + query.replace("%", "\\%").replace("_", "\\_") + "%"
            rows = db.execute(
                """SELECT * FROM xfa_memory_items
                   WHERE user_id=? AND (title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\')
                   ORDER BY updated_at DESC LIMIT ?""",
                (str(user_id), pattern, pattern, MAX_ITEMS),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT * FROM xfa_memory_items WHERE user_id=?
                   ORDER BY updated_at DESC LIMIT ?""",
                (str(user_id), MAX_ITEMS),
            ).fetchall()
    return [_serialize(row) for row in rows]


def create_memory(user_id: str, title: str, content: str, tags=None) -> dict:
    _ensure_table()
    title = str(title or "").strip()
    content = str(content or "").strip()
    if not title or len(title) > MAX_TITLE:
        raise ValueError("Başlıq 1-120 simvol olmalıdır.")
    if not content or len(content) > MAX_CONTENT:
        raise ValueError("Yaddaş mətni 1-6000 simvol olmalıdır.")
    safe_tags = sorted({str(tag).strip()[:32] for tag in (tags or [])
                        if str(tag).strip()})[:MAX_TAGS]
    now = int(time.time())
    item_id = str(uuid.uuid4())
    with _connection() as db:
        count = db.execute(
            "SELECT COUNT(*) AS n FROM xfa_memory_items WHERE user_id=?",
            (str(user_id),),
        ).fetchone()["n"]
        if count >= MAX_ITEMS:
            raise ValueError("Hesab başına maksimum 100 yaddaş qeydinə icazə verilir.")
        db.execute(
            """INSERT INTO xfa_memory_items
               (id,user_id,title,content,tags_json,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?)""",
            (item_id, str(user_id), title, content, json.dumps(safe_tags), now, now),
        )
        row = db.execute(
            "SELECT * FROM xfa_memory_items WHERE id=? AND user_id=?",
            (item_id, str(user_id)),
        ).fetchone()
    return _serialize(row)


def update_memory(user_id: str, item_id: str, title: str, content: str, tags=None) -> dict | None:
    _ensure_table()
    title = str(title or "").strip()
    content = str(content or "").strip()
    if not title or len(title) > MAX_TITLE:
        raise ValueError("Başlıq 1-120 simvol olmalıdır.")
    if not content or len(content) > MAX_CONTENT:
        raise ValueError("Yaddaş mətni 1-6000 simvol olmalıdır.")
    safe_tags = sorted({str(tag).strip()[:32] for tag in (tags or [])
                        if str(tag).strip()})[:MAX_TAGS]
    with _connection() as db:
        cursor = db.execute(
            """UPDATE xfa_memory_items SET title=?,content=?,tags_json=?,updated_at=?
               WHERE id=? AND user_id=?""",
            (title, content, json.dumps(safe_tags), int(time.time()),
             str(item_id), str(user_id)),
        )
        if cursor.rowcount != 1:
            return None
        row = db.execute(
            "SELECT * FROM xfa_memory_items WHERE id=? AND user_id=?",
            (str(item_id), str(user_id)),
        ).fetchone()
    return _serialize(row)


def delete_memory(user_id: str, item_id: str) -> bool:
    _ensure_table()
    with _connection() as db:
        cursor = db.execute(
            "DELETE FROM xfa_memory_items WHERE id=? AND user_id=?",
            (str(item_id), str(user_id)),
        )
    return cursor.rowcount == 1
