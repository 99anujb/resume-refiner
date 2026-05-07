"""SQLite-backed application tracker."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"

STATUSES = [
    "draft", "applied", "phone_screen", "technical", "onsite",
    "offer", "rejected", "ghosted", "withdrawn",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role_title TEXT NOT NULL,
    role_category TEXT,
    seniority TEXT,
    location TEXT,
    source TEXT,
    jd_url TEXT,
    fit_score REAL,
    verdict TEXT,
    visa_verdict TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    applied_date TEXT,
    last_update TEXT NOT NULL,
    resume_pdf_path TEXT,
    cover_pdf_path TEXT,
    notes TEXT,
    jd_text TEXT,
    analysis_json TEXT,
    fit_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_last_update ON applications(last_update);
"""


@contextmanager
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(SCHEMA)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_application(**fields) -> int:
    init_db()
    fields.setdefault("status", "draft")
    fields.setdefault("last_update", now())
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    with _conn() as c:
        cur = c.execute(
            f"INSERT INTO applications ({cols}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        return int(cur.lastrowid)


def update_application(app_id: int, **fields) -> None:
    init_db()
    fields["last_update"] = now()
    sets = ", ".join(f"{k} = ?" for k in fields)
    with _conn() as c:
        c.execute(
            f"UPDATE applications SET {sets} WHERE id = ?",
            (*fields.values(), app_id),
        )


def list_applications(status: str | None = None) -> list[dict[str, Any]]:
    init_db()
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY last_update DESC",
                (status,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM applications ORDER BY last_update DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def get_application(app_id: int) -> dict[str, Any] | None:
    init_db()
    with _conn() as c:
        r = c.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return dict(r) if r else None


def delete_application(app_id: int) -> None:
    init_db()
    with _conn() as c:
        c.execute("DELETE FROM applications WHERE id = ?", (app_id,))


def stats() -> dict[str, int]:
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT status, COUNT(*) AS n FROM applications GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}
