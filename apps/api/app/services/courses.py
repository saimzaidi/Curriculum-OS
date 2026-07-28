"""Course management operations."""
from __future__ import annotations

from typing import Any

from ..db import connect
from ..errors import DomainError
from ..schemas import CourseCreate
from .common import new_id, now, row, rows, require_course


def create_course(data: CourseCreate, user_id: str) -> dict[str, Any]:
    course = {"id": new_id(), **data.model_dump(), "created_at": now()}
    with connect() as conn:
        conn.execute(
            """INSERT INTO courses(id,name,grade,subject,section,language,localization_region,created_at)
               VALUES(:id,:name,:grade,:subject,:section,:language,:localization_region,:created_at)""",
            course,
        )
        conn.execute("INSERT INTO course_memberships VALUES(?,?,?,?)", (course["id"], user_id, "owner", course["created_at"]))
    return course


def list_courses(user_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return rows(conn.execute("""SELECT c.*,m.role AS membership_role FROM courses c JOIN course_memberships m ON m.course_id=c.id WHERE m.user_id=? ORDER BY c.created_at DESC""", (user_id,)).fetchall())
