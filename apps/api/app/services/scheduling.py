"""Schedule compilation, replanning, and version management using OR-Tools."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ortools.sat.python import cp_model

from ..db import connect
from ..errors import DomainError
from ..schemas import CalendarInput
from .common import dump, load, new_id, now, require_course, row, rows
from .concepts import get_graph

WEEKDAYS = {"MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4, "SATURDAY": 5, "SUNDAY": 6}


def session_dates(calendar: CalendarInput) -> list[date]:
    wanted = {WEEKDAYS[day] for day in calendar.session_days}
    holidays = set(calendar.holidays)
    current, dates = calendar.start_date, []
    while current <= calendar.end_date:
        if current.weekday() in wanted and current not in holidays and current < calendar.exam_date:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _approved_prerequisites(course_id: str) -> list[tuple[str, str]]:
    with connect() as conn:
        return [(row[0], row[1]) for row in conn.execute("SELECT source_concept_id,target_concept_id FROM concept_edges WHERE course_id=? AND relation_type='prerequisite' AND teacher_approved=1 AND rejected=0", (course_id,)).fetchall()]


def _solve_positions(concepts: list[dict[str, Any]], slots: int, prerequisites: list[tuple[str, str]], fixed_positions: dict[str, int] | None = None) -> dict[str, int] | None:
    if len(concepts) > slots:
        return None
    model = cp_model.CpModel()
    positions = {concept["id"]: model.NewIntVar(0, slots - 1, f"p_{index}") for index, concept in enumerate(concepts)}
    model.AddAllDifferent(positions.values())
    for concept_id, position in (fixed_positions or {}).items():
        if concept_id in positions:
            model.Add(positions[concept_id] == position)
    for prerequisite, dependent in prerequisites:
        if prerequisite in positions and dependent in positions:
            model.Add(positions[prerequisite] < positions[dependent])
    model.Minimize(sum(positions[item["id"]] * (6 - item["difficulty"]) for item in concepts))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = 3
    if solver.Solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    return {concept_id: solver.Value(position) for concept_id, position in positions.items()}


def compile_schedule(course_id: str, calendar: CalendarInput, trigger_type: str = "initial", parent_version_id: str | None = None, extra_concept_ids: list[str] | None = None) -> dict[str, Any]:
    require_course(course_id)
    graph = get_graph(course_id)
    concepts = [item for item in graph["concepts"] if item["status"] in {"approved", "proposed"}]
    if extra_concept_ids:
        needed = set(extra_concept_ids)
        concepts = [item for item in concepts if item["required"] or item["id"] in needed]
    if not concepts:
        raise DomainError("NO_CONCEPTS", "Approve or create at least one source-grounded concept first.", status_code=422)
    available = session_dates(calendar)
    teaching_dates = available[:-calendar.revision_sessions] if calendar.revision_sessions else available
    overflow = [item for item in concepts if item["estimated_minutes"] > calendar.session_minutes]
    if overflow or len(concepts) > len(teaching_dates):
        raise DomainError("SCHEDULE_INFEASIBLE", "The required curriculum cannot fit in the available teaching sessions.", {"concept_count": len(concepts), "teaching_sessions": len(teaching_dates), "oversized_concept_ids": [item["id"] for item in overflow], "options": ["Remove optional enrichment", "Add class sessions", "Increase session duration", "Split the large concept manually"]}, 422)
    positions = _solve_positions(concepts, len(teaching_dates), _approved_prerequisites(course_id))
    if positions is None:
        raise DomainError("SCHEDULE_INFEASIBLE", "The prerequisite constraints cannot be satisfied.", status_code=422)
    version_id, created = new_id(), now()
    entries = []
    by_position = {position: concept_id for concept_id, position in positions.items()}
    for position, session_date in enumerate(available):
        if position >= len(teaching_dates):
            entries.append((new_id(), version_id, session_date.isoformat(), calendar.session_minutes, None, "revision", 0, "planned", "Protected revision session."))
        else:
            concept_id = by_position.get(position)
            if concept_id:
                entries.append((new_id(), version_id, session_date.isoformat(), calendar.session_minutes, concept_id, "lesson", 0, "planned", ""))
    with connect() as conn:
        version_number = conn.execute("SELECT COALESCE(MAX(version_number),0)+1 FROM schedule_versions WHERE course_id=?", (course_id,)).fetchone()[0]
        conn.execute("INSERT INTO schedule_versions VALUES(?,?,?,?,?,?,?,?,?,?)", (version_id, course_id, version_number, parent_version_id, trigger_type, dump(calendar.model_dump(mode="json")), "feasible", "Prerequisites and protected revision sessions were compiled deterministically.", None, created))
        conn.executemany("INSERT INTO schedule_entries VALUES(?,?,?,?,?,?,?,?,?)", entries)
    return get_schedule(course_id, version_id)


def get_schedule(course_id: str, version_id: str | None = None) -> dict[str, Any]:
    require_course(course_id)
    with connect() as conn:
        if version_id is None:
            version = row(conn.execute("SELECT * FROM schedule_versions WHERE course_id=? ORDER BY version_number DESC LIMIT 1", (course_id,)).fetchone())
        else:
            version = row(conn.execute("SELECT * FROM schedule_versions WHERE course_id=? AND id=?", (course_id, version_id)).fetchone())
        if not version:
            raise DomainError("SCHEDULE_NOT_FOUND", "No schedule version was found.", status_code=404)
        entries = rows(conn.execute("""SELECT e.*,c.title AS concept_title FROM schedule_entries e LEFT JOIN concepts c ON c.id=e.concept_id WHERE e.version_id=? ORDER BY e.session_date,e.id""", (version["id"],)).fetchall())
    version["trigger_payload"] = load(version.pop("trigger_payload_json"))
    for entry in entries:
        entry["locked"] = bool(entry["locked"])
    return {"version": version, "entries": entries}


def lock_schedule_entry(course_id: str, entry_id: str, locked: bool = True) -> dict[str, Any]:
    require_course(course_id)
    with connect() as conn:
        entry = row(conn.execute("""SELECT e.* FROM schedule_entries e JOIN schedule_versions v ON v.id=e.version_id WHERE e.id=? AND v.course_id=?""", (entry_id, course_id)).fetchone())
        if not entry:
            raise DomainError("SCHEDULE_ENTRY_NOT_FOUND", "Schedule entry was not found.", status_code=404)
        conn.execute("UPDATE schedule_entries SET locked=? WHERE id=?", (int(locked), entry_id))
        entry["locked"] = locked
    return entry


def replan_schedule(course_id: str, base_version_id: str, cancelled_entry_ids: list[str], preserve_locked_items: bool = True, remediation_concept_id: str | None = None) -> dict[str, Any]:
    base = get_schedule(course_id, base_version_id)
    cancelled = set(cancelled_entry_ids)
    known = {item["id"] for item in base["entries"]}
    if not cancelled <= known:
        raise DomainError("SCHEDULE_ENTRY_NOT_FOUND", "One or more cancelled sessions do not belong to the base schedule.", status_code=422)
    if preserve_locked_items and any(entry["id"] in cancelled and entry["locked"] for entry in base["entries"]):
        raise DomainError("LOCKED_ITEM", "A locked lesson cannot be cancelled automatically.", status_code=422)
    settings = CalendarInput.model_validate(base["version"]["trigger_payload"])
    cancelled_dates = {entry["session_date"] for entry in base["entries"] if entry["id"] in cancelled}
    available_dates = [item for item in session_dates(settings) if item.isoformat() not in cancelled_dates]
    revision_dates = available_dates[-settings.revision_sessions:] if settings.revision_sessions else []
    teaching_dates = available_dates[:-settings.revision_sessions] if settings.revision_sessions else available_dates
    planned_lessons = [entry for entry in base["entries"] if entry["kind"] == "lesson"]
    retained_lessons = [entry for entry in planned_lessons if entry["id"] not in cancelled]
    concept_ids = [entry["concept_id"] for entry in planned_lessons if entry["concept_id"]]
    unique_ids = list(dict.fromkeys(concept_ids))
    graph = get_graph(course_id)
    by_id = {concept["id"]: concept for concept in graph["concepts"]}
    concepts = [by_id[concept_id] for concept_id in unique_ids if concept_id in by_id]
    required_slots = len(concepts) + int(remediation_concept_id is not None)
    if required_slots > len(teaching_dates):
        raise DomainError("SCHEDULE_INFEASIBLE", "The remaining content cannot fit after the cancelled sessions.", {"concept_count": required_slots, "remaining_sessions": len(teaching_dates), "options": ["Remove optional content", "Add a recovery class", "Reduce revision sessions"]}, 422)
    fixed_positions = {
        entry["concept_id"]: position
        for position, session_date in enumerate(teaching_dates)
        for entry in retained_lessons
        if entry["locked"] and entry["concept_id"] and entry["session_date"] == session_date.isoformat()
    } if preserve_locked_items else {}
    positions = _solve_positions(concepts, len(teaching_dates), _approved_prerequisites(course_id), fixed_positions)
    if positions is None:
        raise DomainError("SCHEDULE_INFEASIBLE", "The revised prerequisite constraints cannot be satisfied.", status_code=422)
    version_id, created = new_id(), now()
    original_dates = {entry["concept_id"]: entry["session_date"] for entry in planned_lessons if entry["concept_id"]}
    entries, diff = [], []
    by_position = {position: concept_id for concept_id, position in positions.items()}
    for position, session_date in enumerate(teaching_dates):
        concept_id = by_position.get(position)
        if not concept_id:
            continue
        original = original_dates.get(concept_id)
        entry_id = new_id()
        entries.append((entry_id, version_id, session_date.isoformat(), settings.session_minutes, concept_id, "lesson", int(concept_id in fixed_positions), "planned", ""))
        if original != session_date.isoformat():
            diff.append({"concept_id": concept_id, "from": original, "to": session_date.isoformat(), "reason": "cancelled sessions"})
    if remediation_concept_id:
        remediation_position = next((position for position in range(len(teaching_dates)) if position not in by_position), None)
        if remediation_position is None:
            raise DomainError("SCHEDULE_INFEASIBLE", "No free session remains for approved remediation.", status_code=422)
        remediation_date = teaching_dates[remediation_position]
        entries.append((new_id(), version_id, remediation_date.isoformat(), settings.session_minutes, remediation_concept_id, "remediation", 0, "planned", "Inserted after mastery evidence."))
        diff.append({"concept_id": remediation_concept_id, "from": None, "to": remediation_date.isoformat(), "reason": "approved remediation"})
    for revision_date in revision_dates:
        entries.append((new_id(), version_id, revision_date.isoformat(), settings.session_minutes, None, "revision", 0, "planned", "Protected revision session."))
    with connect() as conn:
        version_number = conn.execute("SELECT COALESCE(MAX(version_number),0)+1 FROM schedule_versions WHERE course_id=?", (course_id,)).fetchone()[0]
        payload = {**settings.model_dump(mode="json"), "cancelled_entry_ids": cancelled_entry_ids, "schedule_diff": diff}
        conn.execute("INSERT INTO schedule_versions VALUES(?,?,?,?,?,?,?,?,?,?)", (version_id, course_id, version_number, base_version_id, "remediation" if remediation_concept_id else "cancelled_sessions", dump(payload), "feasible", f"Replanned after {len(cancelled)} cancelled sessions; {len(diff)} entries changed.", None, created))
        conn.executemany("INSERT INTO schedule_entries VALUES(?,?,?,?,?,?,?,?,?)", entries)
    return {**get_schedule(course_id, version_id), "diff": diff}


def publish_schedule(course_id: str, version_id: str) -> dict[str, Any]:
    schedule = get_schedule(course_id, version_id)
    if schedule["version"]["published_at"]:
        return schedule["version"]
    with connect() as conn:
        conn.execute("UPDATE schedule_versions SET published_at=? WHERE id=?", (now(), version_id))
    return get_schedule(course_id, version_id)["version"]
