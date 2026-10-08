import json
import sqlite3
import threading
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    sender TEXT, subject TEXT,
    scam_type TEXT, confidence REAL, reasons TEXT,
    persona_id TEXT,
    status TEXT NOT NULL,          -- engaged | needs_review | ignored | stopped
    mode TEXT NOT NULL             -- manual | sim | imap
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES threads(id),
    role TEXT NOT NULL,            -- scammer | bot
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    effort_min REAL DEFAULT 0      -- estimated scammer minutes spent on this message
);
CREATE TABLE IF NOT EXISTS intel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES threads(id),
    kind TEXT NOT NULL, value TEXT NOT NULL, first_seen TEXT NOT NULL,
    UNIQUE(thread_id, kind, value)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def reset_connection():
    """Used by tests to point at a fresh DB."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None


def create_thread(sender, subject, classification, persona_id, status, mode) -> int:
    with _lock:
        cur = conn().execute(
            "INSERT INTO threads (created_at, sender, subject, scam_type, confidence, reasons, persona_id, status, mode) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now(), sender, subject, classification["scam_type"], classification["confidence"],
             json.dumps(classification["reasons"]), persona_id, status, mode),
        )
        conn().commit()
        return cur.lastrowid


def set_status(thread_id: int, status: str):
    with _lock:
        conn().execute("UPDATE threads SET status=? WHERE id=?", (status, thread_id))
        conn().commit()


def add_message(thread_id: int, role: str, body: str, effort_min: float = 0) -> int:
    with _lock:
        cur = conn().execute(
            "INSERT INTO messages (thread_id, role, body, created_at, effort_min) VALUES (?,?,?,?,?)",
            (thread_id, role, body, now(), effort_min),
        )
        conn().commit()
        return cur.lastrowid


def add_intel(thread_id: int, items: list[tuple[str, str]]):
    with _lock:
        conn().executemany(
            "INSERT OR IGNORE INTO intel (thread_id, kind, value, first_seen) VALUES (?,?,?,?)",
            [(thread_id, k, v, now()) for k, v in items],
        )
        conn().commit()


def _thread_dict(row) -> dict:
    d = dict(row)
    d["reasons"] = json.loads(d["reasons"] or "[]")
    return d


def get_thread(thread_id: int) -> dict | None:
    row = conn().execute("SELECT * FROM threads WHERE id=?", (thread_id,)).fetchone()
    if not row:
        return None
    t = _thread_dict(row)
    t["messages"] = [dict(r) for r in conn().execute(
        "SELECT * FROM messages WHERE thread_id=? ORDER BY id", (thread_id,))]
    t["intel"] = [dict(r) for r in conn().execute(
        "SELECT kind, value, first_seen FROM intel WHERE thread_id=? ORDER BY id", (thread_id,))]
    t["minutes_wasted"] = round(sum(m["effort_min"] for m in t["messages"]), 1)
    return t


def find_thread_by_sender(sender: str) -> int | None:
    row = conn().execute(
        "SELECT id FROM threads WHERE sender=? AND status IN ('engaged','needs_review') ORDER BY id DESC LIMIT 1",
        (sender,)).fetchone()
    return row["id"] if row else None


def list_threads() -> list[dict]:
    rows = conn().execute("""
        SELECT t.*, COUNT(m.id) AS message_count, COALESCE(SUM(m.effort_min), 0) AS minutes_wasted,
               (SELECT COUNT(*) FROM intel i WHERE i.thread_id = t.id) AS intel_count
        FROM threads t LEFT JOIN messages m ON m.thread_id = t.id
        GROUP BY t.id ORDER BY t.id DESC""").fetchall()
    return [_thread_dict(r) for r in rows]


def stats() -> dict:
    c = conn()
    q = lambda sql: c.execute(sql).fetchone()[0]
    return {
        "minutes_wasted": round(q("SELECT COALESCE(SUM(effort_min),0) FROM messages"), 1),
        "threads_engaged": q("SELECT COUNT(*) FROM threads WHERE status IN ('engaged','stopped')"),
        "scammer_messages": q("SELECT COUNT(*) FROM messages WHERE role='scammer'"),
        "intel_items": q("SELECT COUNT(*) FROM intel"),
        "payment_destinations": q("SELECT COUNT(*) FROM intel WHERE kind IN "
                                  "('btc_wallet','eth_wallet','tron_wallet','iban','bank_account','cashtag')"),
    }
