"""Common utilities shared across service modules."""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..db import ROOT, connect
from ..errors import DomainError

UPLOAD_DIR = ROOT / "uploads"
EXPORT_DIR = ROOT / "exports"
PROMPT_VERSION = "local-deterministic-v1"


def now() -> str:
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    return str(uuid4())


def dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)


def load(value: str) -> Any:
    return json.loads(value)


def row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def rows(result: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(item) for item in result]


def require_course(course_id: str) -> dict[str, Any]:
    with connect() as conn:
        course = row(conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone())
    if not course:
        raise DomainError("COURSE_NOT_FOUND", "Course was not found.", {"course_id": course_id}, 404)
    return course


def require_course_access(course_id: str, user_id: str, write: bool = False) -> dict[str, Any]:
    course = require_course(course_id)
    with connect() as conn:
        membership = row(conn.execute("SELECT role FROM course_memberships WHERE course_id=? AND user_id=?", (course_id, user_id)).fetchone())
    if not membership or (write and membership["role"] == "viewer"):
        raise DomainError("FORBIDDEN", "You do not have access to this course.", {"course_id": course_id}, 403)
    return {**course, "membership_role": membership["role"]}


def audit(course_id: str | None, user_id: str, action: str, entity_type: str, entity_id: str | None, trace_id: str, details: dict[str, Any] | None = None) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?,?)", (new_id(), course_id, user_id, action, entity_type, entity_id, dump(details or {}), trace_id, now()))
