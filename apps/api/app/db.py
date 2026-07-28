from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = ROOT / os.getenv("DATABASE_PATH", "data/curriculumos.db")
MIGRATIONS = ROOT / "migrations"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate() -> None:
    with connect() as conn:
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            marker = f"migration:{migration.name}"
            conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
            if conn.execute("SELECT 1 FROM _migrations WHERE name = ?", (marker,)).fetchone():
                continue
            conn.executescript(migration.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO _migrations(name) VALUES (?)", (marker,))
