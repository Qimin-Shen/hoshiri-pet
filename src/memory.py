"""Local, user-controlled persistent memories; never stores raw chat history."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

import config
from store import DB_FILE

MAX_RECALL_ITEMS = 4
MAX_RECALL_CHARS = 1200
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)\b(?:password|passwd|api[_ -]?key|secret|token)\b|密码|口令|API\s*Key|密钥|验证码"),
    re.compile(r"(?i)\b\d{13,19}\b|\b\d{6,}\b"),
    re.compile(r"(?i)\b\d{1,5}\s+[^\n,，]{1,30}(?:street|road|avenue|街|路|号)\b"),
    re.compile(r"(?:我有|我患有|诊断为|病史|身高|体重|身份证|银行卡|账户余额|工资)"),
]
CANDIDATE_PREFIXES = ("记住", "我喜欢", "我不喜欢", "我偏好", "我通常", "我正在", "我在做", "我的目标是", "我叫")
STOPWORDS = {"今天", "现在", "可以", "怎么", "什么", "这个", "那个", "星璃", "记住"}


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'preference', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS memory_ignored (fingerprint TEXT PRIMARY KEY, ignored_at TEXT NOT NULL)")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_sensitive(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def candidate_from_user_message(text: str) -> str | None:
    value = " ".join(text.split()).strip()
    if not value or len(value) > 180 or is_sensitive(value) or not value.startswith(CANDIDATE_PREFIXES):
        return None
    if value.startswith("记住"):
        value = re.sub(r"^记住[：:，, ]*", "", value)
    return value[:180] or None


def _fingerprint(text: str) -> str:
    return hashlib.sha256(" ".join(text.casefold().split()).encode("utf-8")).hexdigest()


def is_ignored(text: str) -> bool:
    with _conn() as conn:
        return conn.execute("SELECT 1 FROM memory_ignored WHERE fingerprint=?", (_fingerprint(text),)).fetchone() is not None


def ignore_candidate(text: str) -> None:
    with _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO memory_ignored VALUES (?,?)", (_fingerprint(text), datetime.now().isoformat(timespec="seconds")))


def add(text: str, category: str = "preference") -> int:
    content = " ".join(text.split()).strip()
    if not content or len(content) > 500 or is_sensitive(content):
        raise ValueError("记忆为空、过长或可能包含敏感信息，未保存。")
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        cur = conn.execute("INSERT INTO memories(content,category,created_at,updated_at) VALUES(?,?,?,?)", (content, category[:40], now, now))
        return int(cur.lastrowid)


def list_memories(query: str = "") -> list[dict]:
    with _conn() as conn:
        if query.strip():
            rows = conn.execute("SELECT * FROM memories WHERE content LIKE ? ORDER BY updated_at DESC", (f"%{query.strip()}%",)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]


def update(memory_id: int, text: str) -> None:
    content = " ".join(text.split()).strip()
    if not content or len(content) > 500 or is_sensitive(content):
        raise ValueError("记忆为空、过长或可能包含敏感信息，未保存。")
    with _conn() as conn:
        conn.execute("UPDATE memories SET content=?, updated_at=? WHERE id=?", (content, datetime.now().isoformat(timespec="seconds"), memory_id))


def delete(memory_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))


def clear_all() -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM memories")


def _terms(text: str) -> set[str]:
    result = set(re.findall(r"[a-z0-9_]{2,}", text.casefold()))
    chinese = "".join(ch for ch in text if 0x4e00 <= ord(ch) <= 0x9fff)
    result.update(chinese[i:i + 2] for i in range(len(chinese) - 1))
    return {term for term in result if term not in STOPWORDS}


def retrieve(query: str, limit: int = MAX_RECALL_ITEMS, max_chars: int = MAX_RECALL_CHARS) -> list[str]:
    if not config.load().get("memory_enabled", True):
        return []
    query_terms = _terms(query)
    if not query_terms:
        return []
    ranked: list[tuple[int, str]] = []
    for row in list_memories():
        content = row["content"]
        memory_terms = _terms(content)
        overlap = query_terms & memory_terms
        if len(overlap) >= 2:
            ranked.append((len(overlap), content))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    out, used = [], 0
    for _, content in ranked[:max(0, limit)]:
        if used + len(content) > max_chars:
            continue
        out.append(content)
        used += len(content)
    return out
