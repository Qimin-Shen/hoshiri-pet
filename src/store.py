"""本地用量记录：SQLite。额度仪表盘的数据都从这里来。"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import config

DB_FILE = config.CONFIG_DIR / "usage.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    model     TEXT NOT NULL,
    prompt    INTEGER DEFAULT 0,
    completion INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS balance (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    total  REAL NOT NULL,
    currency TEXT DEFAULT 'CNY'
);
CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage(ts);
CREATE INDEX IF NOT EXISTS idx_balance_ts ON balance(ts);
"""


def _conn() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.executescript(_SCHEMA)
    return conn


def add_usage(model: str, prompt: int, completion: int) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO usage (ts, model, prompt, completion) VALUES (?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), model, int(prompt), int(completion)),
        )


def add_balance(total: float, currency: str = "CNY") -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO balance (ts, total, currency) VALUES (?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), float(total), currency),
        )


def last_balance() -> tuple[float, str] | None:
    with _conn() as c:
        row = c.execute(
            "SELECT total, ts FROM balance ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return (row[0], row[1]) if row else None


def _sum_tokens(where: str = "", args: tuple = ()) -> int:
    with _conn() as c:
        row = c.execute(
            f"SELECT COALESCE(SUM(prompt + completion), 0) FROM usage {where}", args
        ).fetchone()
    return int(row[0]) if row else 0


def today_tokens() -> int:
    start = date.today().isoformat() + "T00:00:00"
    return _sum_tokens("WHERE ts >= ?", (start,))


def total_tokens() -> int:
    return _sum_tokens()


def today_spend() -> float:
    """用当天余额差推算实际花费，比按单价估算准。"""
    start = date.today().isoformat() + "T00:00:00"
    with _conn() as c:
        rows = c.execute(
            "SELECT total FROM balance WHERE ts >= ? ORDER BY id ASC", (start,)
        ).fetchall()
    if len(rows) < 2:
        return 0.0
    return max(0.0, float(rows[0][0]) - float(rows[-1][0]))


def total_spend() -> float:
    with _conn() as c:
        rows = c.execute("SELECT total FROM balance ORDER BY id ASC").fetchall()
    if len(rows) < 2:
        return 0.0
    return max(0.0, float(rows[0][0]) - float(rows[-1][0]))


def history(days: int = 7) -> list[tuple[str, int]]:
    """最近 N 天每天的 token 数，用于小柱状图。"""
    start = (date.today() - timedelta(days=days - 1)).isoformat() + "T00:00:00"
    with _conn() as c:
        rows = c.execute(
            "SELECT substr(ts,1,10) d, SUM(prompt + completion) "
            "FROM usage WHERE ts >= ? GROUP BY d ORDER BY d",
            (start,),
        ).fetchall()
    return [(r[0], int(r[1] or 0)) for r in rows]
