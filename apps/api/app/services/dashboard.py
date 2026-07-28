"""Dashboard aggregation for the course overview."""
from __future__ import annotations

from typing import Any

from ..db import connect
from ..errors import DomainError
from .common import load, require_course, rows
from .concepts import get_graph
from .documents import list_source_blocks
from .scheduling import get_schedule


def dashboard(course_id: str) -> dict[str, Any]:
    course = require_course(course_id)
    graph = get_graph(course_id)
    try:
        schedule = get_schedule(course_id)
    except DomainError:
        schedule = None
    with connect() as conn:
        source_count = conn.execute("SELECT COUNT(*) FROM source_blocks WHERE course_id=?", (course_id,)).fetchone()[0]
        lessons = rows(conn.execute("SELECT id,schedule_entry_id,content_json,teacher_edited,locked,updated_at FROM lessons WHERE course_id=? ORDER BY updated_at DESC", (course_id,)).fetchall())
        assessments = rows(conn.execute("SELECT id,title,content_json,approved,created_at FROM assessments WHERE course_id=? ORDER BY created_at DESC", (course_id,)).fetchall())
        mastery = rows(conn.execute("SELECT m.*,c.title AS concept_title FROM mastery_records m JOIN concepts c ON c.id=m.concept_id WHERE m.course_id=? ORDER BY m.weighted_score,c.title", (course_id,)).fetchall())
        remediation = rows(conn.execute("SELECT r.*,c.title AS concept_title FROM remediation_actions r JOIN concepts c ON c.id=r.concept_id WHERE r.course_id=? ORDER BY r.created_at DESC", (course_id,)).fetchall())
        audit_events = rows(conn.execute("SELECT action,entity_type,entity_id,details_json,trace_id,created_at FROM audit_events WHERE course_id=? ORDER BY created_at DESC LIMIT 12", (course_id,)).fetchall())
        jobs = rows(conn.execute("SELECT id,document_id,status,stage,progress,message,error,created_at,updated_at FROM jobs WHERE course_id=? ORDER BY created_at DESC LIMIT 8", (course_id,)).fetchall())
    for lesson in lessons:
        lesson["content"] = load(lesson.pop("content_json"))
        lesson["teacher_edited"] = bool(lesson["teacher_edited"])
        lesson["locked"] = bool(lesson["locked"])
    for assessment in assessments:
        assessment["content"] = load(assessment.pop("content_json"))
        assessment["approved"] = bool(assessment["approved"])
    for action in remediation:
        action["evidence"] = load(action.pop("evidence_json"))
    for event in audit_events:
        event["details"] = load(event.pop("details_json"))
    return {"course": course, "source_count": source_count, "source_blocks": list_source_blocks(course_id), "graph": graph, "schedule": schedule, "lessons": lessons, "assessments": assessments, "mastery": mastery, "remediation": remediation, "jobs": jobs, "audit_events": audit_events}
