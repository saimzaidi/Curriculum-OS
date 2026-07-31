"""Lesson generation, editing, and teacher lock management."""
from __future__ import annotations

from typing import Any

from ..db import connect
from ..errors import DomainError
from ..schemas import GeneratedLessonSchema, LessonGenerateRequest
from .common import PROMPT_VERSION, dump, load, new_id, now, require_course, row
from .documents import list_source_blocks


def _entry_and_concept(course_id: str, entry_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    with connect() as conn:
        entry = row(conn.execute("""SELECT e.* FROM schedule_entries e JOIN schedule_versions v ON v.id=e.version_id WHERE e.id=? AND v.course_id=?""", (entry_id, course_id)).fetchone())
        if not entry or not entry["concept_id"]:
            raise DomainError("LESSON_NOT_SCHEDULABLE", "Select a scheduled concept lesson.", status_code=422)
        concept = row(conn.execute("SELECT *,source_block_ids_json,learning_objectives_json FROM concepts WHERE id=?", (entry["concept_id"],)).fetchone())
    from .concepts import _concept_out
    return entry, _concept_out(concept)


def generate_lesson(course_id: str, entry_id: str, request: LessonGenerateRequest) -> dict[str, Any]:
    course = require_course(course_id)
    entry, concept = _entry_and_concept(course_id, entry_id)
    with connect() as conn:
        existing = row(conn.execute("SELECT * FROM lessons WHERE course_id=? AND schedule_entry_id=?", (course_id, entry_id)).fetchone())
        if existing and (existing["teacher_edited"] or existing["locked"]):
            return {"id": existing["id"], "content": load(existing["content_json"]), "preserved_teacher_work": True}
        source = row(conn.execute("SELECT * FROM source_blocks WHERE id=?", (concept["source_block_ids"][0],)).fetchone())
    if not source:
        raise DomainError("INVALID_SOURCE_REFERENCE", "Scheduled concept has no available source block.", status_code=422)
    minutes = entry["session_minutes"]
    content = {
        "title": concept["title"],
        "objectives": concept["learning_objectives"],
        "timed_segments": [
            {"minutes": 5, "name": "Retrieval", "teacher_actions": ["Ask students to recall the prerequisite."], "student_actions": ["Write one prior idea."], "source_block_ids": concept["source_block_ids"]},
            {"minutes": max(10, minutes - 15), "name": "Source-grounded explanation", "teacher_actions": [source["normalized_text"][:220]], "student_actions": [f"Annotate the key idea: {concept['title']}."], "source_block_ids": concept["source_block_ids"]},
            {"minutes": 10, "name": "Karachi context activity", "teacher_actions": [f"Model {concept['title']} using a familiar Karachi classroom or commute example."], "student_actions": ["Work through a paired example."], "source_block_ids": concept["source_block_ids"]},
        ],
        "checks_for_understanding": [f"Explain {concept['title']} using one cited source idea."],
        "differentiation": {"below": ["Use a labelled worked example."], "on": ["Solve the core application."], "advanced": ["Justify the method and compare an alternative."]},
        "homework": [f"Write a short source-cited explanation of {concept['title']}."],
        "source_block_ids": concept["source_block_ids"],
        "localization_region": request.localization_region,
    }
    # Validate against our strict GeneratedLessonSchema (corresponding to generated-lesson.schema.json)
    try:
        GeneratedLessonSchema.model_validate(content)
    except Exception as exc:
        raise DomainError("SCHEMA_VALIDATION_FAILED", "Generated lesson schema validation failed.", {"errors": str(exc)}, 500) from exc

    if sum(part["minutes"] for part in content["timed_segments"]) > minutes:
        raise DomainError("LESSON_DURATION_INVALID", "Generated lesson exceeds the scheduled session duration.", status_code=422)
    lesson_id, timestamp = existing["id"] if existing else new_id(), now()
    with connect() as conn:
        if existing:
            conn.execute("UPDATE lessons SET content_json=?,source_block_ids_json=?,prompt_version=?,model_name=?,updated_at=? WHERE id=?", (dump(content), dump(concept["source_block_ids"]), PROMPT_VERSION, "deterministic-local", timestamp, lesson_id))
        else:
            conn.execute("INSERT INTO lessons VALUES(?,?,?,?,?,?,?,?,?,?,?)", (lesson_id, course_id, entry_id, dump(content), dump(concept["source_block_ids"]), PROMPT_VERSION, "deterministic-local", 0, 0, timestamp, timestamp))
        conn.execute("INSERT INTO generation_records VALUES(?,?,?,?,?,?,?,?,?)", (new_id(), course_id, "lesson", PROMPT_VERSION, "deterministic-local", dump({"entry_id": entry_id, "source_block_ids": concept["source_block_ids"]}), dump(content), 1, timestamp))
    return {"id": lesson_id, "content": content, "preserved_teacher_work": False}


def edit_lesson(course_id: str, lesson_id: str, content: dict[str, Any], locked: bool) -> dict[str, Any]:
    source_ids = set(item["id"] for item in list_source_blocks(course_id))
    cited = set(content.get("source_block_ids", []))
    if not cited or not cited <= source_ids:
        raise DomainError("INVALID_SOURCE_REFERENCE", "Lesson must cite source blocks from this course.", status_code=422)
    with connect() as conn:
        lesson = row(conn.execute("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course_id)).fetchone())
        if not lesson:
            raise DomainError("LESSON_NOT_FOUND", "Lesson was not found.", status_code=404)
        conn.execute("UPDATE lessons SET content_json=?,source_block_ids_json=?,teacher_edited=1,locked=?,updated_at=? WHERE id=?", (dump(content), dump(sorted(cited)), int(locked), now(), lesson_id))
    return {"id": lesson_id, "content": content, "teacher_edited": True, "locked": locked}
