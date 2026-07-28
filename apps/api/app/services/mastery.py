"""Mastery calculation, remediation proposal, and approval."""
from __future__ import annotations

from typing import Any

from ..db import connect
from ..errors import DomainError
from .common import dump, load, new_id, now, require_course, row, rows
from .concepts import get_graph
from .scheduling import replan_schedule


def recompute_mastery(course_id: str) -> list[dict[str, Any]]:
    require_course(course_id)
    with connect() as conn:
        raw = conn.execute("SELECT concept_id, SUM(earned_points) AS earned, SUM(max_points) AS possible, COUNT(*) AS count FROM attempts WHERE course_id=? GROUP BY concept_id", (course_id,)).fetchall()
        timestamp = now()
        for item in raw:
            score, count = item["earned"] / item["possible"], item["count"]
            confidence = min(1.0, count / 5)
            conn.execute("INSERT OR REPLACE INTO mastery_records VALUES(?,?,?,?,?,?,?)", (new_id(), course_id, item["concept_id"], score, count, confidence, timestamp))
        records = rows(conn.execute("""SELECT m.*,c.title AS concept_title FROM mastery_records m JOIN concepts c ON c.id=m.concept_id WHERE m.course_id=? ORDER BY m.weighted_score,c.title""", (course_id,)).fetchall())
    return records


def propose_remediation(course_id: str) -> dict[str, Any]:
    records = recompute_mastery(course_id)
    if not records:
        raise DomainError("NO_MASTERY_EVIDENCE", "Import quiz results before proposing remediation.", status_code=422)
    weakest = records[0]
    action = {"id": new_id(), "course_id": course_id, "concept_id": weakest["concept_id"], "duration_minutes": 20, "evidence": {"mastery": weakest["weighted_score"], "item_count": weakest["item_count"], "confidence": weakest["confidence"]}, "status": "proposed", "created_at": now(), "approved_at": None}
    with connect() as conn:
        conn.execute("INSERT INTO remediation_actions VALUES(?,?,?,?,?,?,?,?)", (action["id"], course_id, action["concept_id"], action["duration_minutes"], dump(action["evidence"]), action["status"], action["created_at"], None))
    return action


def approve_remediation(course_id: str, action_id: str, base_version_id: str, cancelled_entry_ids: list[str]) -> dict[str, Any]:
    with connect() as conn:
        action = row(conn.execute("SELECT * FROM remediation_actions WHERE id=? AND course_id=?", (action_id, course_id)).fetchone())
        if not action:
            raise DomainError("REMEDIATION_NOT_FOUND", "Remediation proposal was not found.", status_code=404)
        if action["status"] == "approved":
            raise DomainError("REMEDIATION_ALREADY_APPROVED", "This remediation has already been approved.", status_code=409)
        conn.execute("UPDATE remediation_actions SET status='approved',approved_at=? WHERE id=?", (now(), action_id))
    schedule = replan_schedule(course_id, base_version_id, cancelled_entry_ids, remediation_concept_id=action["concept_id"])
    return {"action_id": action_id, "schedule": schedule}
