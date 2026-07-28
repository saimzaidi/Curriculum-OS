"""Concept graph generation, approval, and editing operations."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from ..db import connect
from ..errors import DomainError
from ..schemas import ConceptEdit
from .common import PROMPT_VERSION, dump, load, new_id, now, require_course, row, rows
from .documents import list_source_blocks


def _title_for_block(text: str, index: int) -> str:
    first = re.sub(r"^\s*(chapter|unit|topic)?\s*\d*\s*[:.-]?\s*", "", text.split(".")[0].split("\n")[0], flags=re.I).strip()
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", first)
    return " ".join(words[:7]).title() or f"Source Concept {index + 1}"


def _concept_out(item: dict[str, Any]) -> dict[str, Any]:
    item["required"] = bool(item["required"])
    item["locked"] = bool(item["locked"])
    item["source_block_ids"] = load(item.pop("source_block_ids_json"))
    item["learning_objectives"] = load(item.pop("learning_objectives_json"))
    return item


def _check_graph_cycle(course_id: str, candidate: tuple[str, str] | None = None) -> None:
    graph = defaultdict(list)
    with connect() as conn:
        edges = conn.execute("SELECT source_concept_id,target_concept_id FROM concept_edges WHERE course_id = ? AND relation_type = 'prerequisite' AND rejected = 0", (course_id,)).fetchall()
    for edge in edges:
        graph[edge[0]].append(edge[1])
    if candidate:
        graph[candidate[0]].append(candidate[1])
    visiting, visited = set(), set()
    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        cyclic = any(visit(child) for child in graph[node])
        visiting.remove(node)
        visited.add(node)
        return cyclic
    if any(visit(node) for node in list(graph)):
        raise DomainError("GRAPH_CYCLE", "Prerequisite edges must not contain a cycle.", status_code=422)


def generate_concept_graph(course_id: str) -> dict[str, Any]:
    course = require_course(course_id)
    blocks = list_source_blocks(course_id)
    useful = [block for block in blocks if block["normalized_text"]][:12]
    if not useful:
        raise DomainError("NO_SOURCE_BLOCKS", "Upload a document with extractable text first.", status_code=422)
    created: list[dict[str, Any]] = []
    seen: set[str] = set()
    with connect() as conn:
        for index, block in enumerate(useful):
            title = _title_for_block(block["normalized_text"], index)
            normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
            if normalized in seen or conn.execute("SELECT 1 FROM concepts WHERE course_id = ? AND normalized_title = ?", (course_id, normalized)).fetchone():
                continue
            seen.add(normalized)
            concept = {
                "id": new_id(), "course_id": course_id, "title": title, "normalized_title": normalized,
                "description": block["normalized_text"][:500], "difficulty": min(5, 1 + index // 3),
                "estimated_minutes": 30, "required": 1, "exam_weight": round(0.4 + min(index, 5) * 0.1, 2),
                "source_block_ids": [block["id"]], "learning_objectives": [f"Explain {title}."], "confidence": 0.75,
                "status": "proposed", "locked": 0, "created_at": now(),
            }
            conn.execute(
                """INSERT INTO concepts VALUES(:id,:course_id,:title,:normalized_title,:description,:difficulty,:estimated_minutes,:required,:exam_weight,:source_block_ids,:learning_objectives,:confidence,:status,:locked,:created_at)""",
                {**concept, "source_block_ids": dump(concept["source_block_ids"]), "learning_objectives": dump(concept["learning_objectives"])},
            )
            created.append(concept)
        for source, target in zip(created, created[1:]):
            conn.execute("INSERT INTO concept_edges VALUES(?,?,?,?,?,?,?,?,?)", (new_id(), course_id, source["id"], target["id"], "prerequisite", 0.65, "Sequential source order proposal.", 0, 0))
        record_id = new_id()
        conn.execute("INSERT INTO generation_records VALUES(?,?,?,?,?,?,?,?,?)", (record_id, course_id, "concept_extraction", PROMPT_VERSION, "deterministic-local", dump({"block_ids": [block["id"] for block in useful], "subject": course["subject"]}), dump({"concept_ids": [item["id"] for item in created]}), 1, now()))
    return get_graph(course_id)


def get_graph(course_id: str) -> dict[str, Any]:
    require_course(course_id)
    with connect() as conn:
        concepts = [_concept_out(item) for item in rows(conn.execute("SELECT *, source_block_ids_json, learning_objectives_json FROM concepts WHERE course_id = ? ORDER BY created_at", (course_id,)).fetchall())]
        edges = rows(conn.execute("SELECT * FROM concept_edges WHERE course_id = ? AND rejected = 0 ORDER BY id", (course_id,)).fetchall())
    for edge in edges:
        edge["teacher_approved"] = bool(edge["teacher_approved"])
        edge["rejected"] = bool(edge["rejected"])
    return {"concepts": concepts, "edges": edges}


def approve_edge(course_id: str, edge_id: str, approved: bool) -> dict[str, Any]:
    require_course(course_id)
    with connect() as conn:
        edge = row(conn.execute("SELECT * FROM concept_edges WHERE id = ? AND course_id = ?", (edge_id, course_id)).fetchone())
        if not edge:
            raise DomainError("EDGE_NOT_FOUND", "Concept edge was not found.", status_code=404)
        if approved:
            _check_graph_cycle(course_id)
        conn.execute("UPDATE concept_edges SET teacher_approved = ?, rejected = ? WHERE id = ?", (int(approved), int(not approved), edge_id))
        updated = row(conn.execute("SELECT * FROM concept_edges WHERE id = ?", (edge_id,)).fetchone())
    updated["teacher_approved"] = bool(updated["teacher_approved"])
    updated["rejected"] = bool(updated["rejected"])
    return updated


def edit_concept(course_id: str, concept_id: str, data: ConceptEdit) -> dict[str, Any]:
    require_course(course_id)
    source_ids = set(item["id"] for item in list_source_blocks(course_id))
    if not set(data.source_block_ids) <= source_ids:
        raise DomainError("INVALID_SOURCE_REFERENCE", "Every source reference must belong to this course.", status_code=422)
    normalized = re.sub(r"[^a-z0-9]+", " ", data.title.lower()).strip()
    with connect() as conn:
        existing = row(conn.execute("SELECT * FROM concepts WHERE id = ? AND course_id = ?", (concept_id, course_id)).fetchone())
        if not existing:
            raise DomainError("CONCEPT_NOT_FOUND", "Concept was not found.", status_code=404)
        conn.execute(
            """UPDATE concepts SET title=?,normalized_title=?,description=?,difficulty=?,estimated_minutes=?,required=?,exam_weight=?,source_block_ids_json=?,learning_objectives_json=?,confidence=?,locked=?,status='approved' WHERE id=?""",
            (data.title, normalized, data.description, data.difficulty, data.estimated_minutes, int(data.required), data.exam_weight, dump(data.source_block_ids), dump(data.learning_objectives), data.confidence, int(data.locked), concept_id),
        )
        result = row(conn.execute("SELECT *, source_block_ids_json, learning_objectives_json FROM concepts WHERE id = ?", (concept_id,)).fetchone())
    return _concept_out(result)
