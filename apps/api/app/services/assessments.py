"""Assessment generation, approval, and results import."""
from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

from ..db import connect
from ..errors import DomainError
from .common import PROMPT_VERSION, dump, load, new_id, now, require_course, row, rows
from .concepts import get_graph


def generate_assessment(course_id: str, concept_ids: list[str], title: str) -> dict[str, Any]:
    require_course(course_id)
    graph = get_graph(course_id)
    concepts = [item for item in graph["concepts"] if item["id"] in concept_ids]
    if len(concepts) != len(set(concept_ids)):
        raise DomainError("CONCEPT_NOT_FOUND", "Every assessment concept must belong to this course.", status_code=422)
    items = []
    for index, concept in enumerate(concepts, 1):
        items.append({"id": f"Q{index}", "concept_ids": [concept["id"]], "source_block_ids": concept["source_block_ids"], "question": f"Using the course source, explain and apply {concept['title']} to a specific classroom scenario.", "rubric": ["Accurately states the source-grounded idea.", "Applies it to the scenario with reasoning."], "max_points": 4, "shallow_answer_resistance": "Requires cited course-specific evidence."})
    content = {"title": title, "items": items, "status": "pending_teacher_approval"}
    fingerprint = hashlib.sha256(dump({"concept_ids": sorted(concept_ids), "title": title}).encode()).hexdigest()
    with connect() as conn:
        duplicate = conn.execute("SELECT id FROM assessments WHERE course_id=? AND fingerprint=?", (course_id, fingerprint)).fetchone()
        if duplicate:
            raise DomainError("DUPLICATE_ASSESSMENT", "An assessment with this concept coverage already exists.", {"assessment_id": duplicate[0]}, 409)
        assessment_id = new_id()
        conn.execute("INSERT INTO assessments VALUES(?,?,?,?,?,?,?)", (assessment_id, course_id, title, dump(content), fingerprint, 0, now()))
        conn.execute("INSERT INTO generation_records VALUES(?,?,?,?,?,?,?,?,?)", (new_id(), course_id, "assessment", PROMPT_VERSION, "deterministic-local", dump({"concept_ids": concept_ids}), dump(content), 1, now()))
    return {"id": assessment_id, **content}


def approve_assessment(course_id: str, assessment_id: str) -> dict[str, Any]:
    with connect() as conn:
        assessment = row(conn.execute("SELECT * FROM assessments WHERE id=? AND course_id=?", (assessment_id, course_id)).fetchone())
        if not assessment:
            raise DomainError("ASSESSMENT_NOT_FOUND", "Assessment was not found.", status_code=404)
        conn.execute("UPDATE assessments SET approved=1 WHERE id=?", (assessment_id,))
    return {"id": assessment_id, "approved": True}


def import_results(course_id: str, assessment_id: str, contents: bytes) -> dict[str, Any]:
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM assessments WHERE id=? AND course_id=?", (assessment_id, course_id)).fetchone():
            raise DomainError("ASSESSMENT_NOT_FOUND", "Assessment was not found.", status_code=404)
    try:
        reader = csv.DictReader(io.StringIO(contents.decode("utf-8-sig")))
        required = {"student_id", "assessment_item_id", "concept_id", "earned_points", "max_points"}
        if set(reader.fieldnames or []) != required:
            raise ValueError("CSV headers must be student_id,assessment_item_id,concept_id,earned_points,max_points")
        attempts = []
        concept_ids = {item["id"] for item in get_graph(course_id)["concepts"]}
        for line, item in enumerate(reader, 2):
            if item["concept_id"] not in concept_ids:
                raise ValueError(f"line {line}: unknown concept_id")
            earned, maximum = float(item["earned_points"]), float(item["max_points"])
            if maximum <= 0 or earned < 0 or earned > maximum:
                raise ValueError(f"line {line}: invalid score")
            attempts.append((new_id(), course_id, assessment_id, item["student_id"], item["assessment_item_id"], item["concept_id"], earned, maximum, now()))
    except (UnicodeDecodeError, ValueError) as exc:
        raise DomainError("INVALID_RESULTS_CSV", str(exc), status_code=422) from exc
    with connect() as conn:
        conn.executemany("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)", attempts)
    return {"imported_attempts": len(attempts)}
