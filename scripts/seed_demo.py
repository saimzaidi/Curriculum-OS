"""Create a repeatable local CurriculumOS demo without external services."""
from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app import auth, db, services
from app.errors import DomainError
from app.schemas import CalendarInput, CourseCreate, LessonGenerateRequest


SOURCE = b"""Force is a push or pull that can change an object's motion.

Momentum describes how mass and velocity combine in moving objects.

The conservation of energy explains how energy changes form without being lost.

Newton's second law connects force, mass, and acceleration in measurable situations."""

PAST_PAPER = b"""Past paper prompt: A bus changes speed while carrying passengers. Use Newton's second law to explain the relationship between force, mass, and acceleration. Cite the relevant principle and show your reasoning."""


def build_course(user_id: str, fresh: bool) -> dict:
    base_name = "Grade XI Physics - Mechanics Demo"
    if fresh:
        # A fresh named course avoids deleting a teacher's prior rehearsal work.
        return services.create_course(CourseCreate(name=f"{base_name} | Rehearsal {date.today().isoformat()}", grade="XI", subject="Physics", section="A"), user_id)
    return next((course for course in services.list_courses(user_id) if course["name"] == base_name), None) or services.create_course(CourseCreate(name=base_name, grade="XI", subject="Physics", section="A"), user_id)


def run_full_rehearsal(course_id: str, graph: dict, schedule: dict) -> tuple[dict, dict]:
    lessons = [entry for entry in schedule["entries"] if entry["kind"] == "lesson"]
    services.generate_lesson(course_id, lessons[0]["id"], LessonGenerateRequest())
    concepts = graph["concepts"][:2]
    assessment = services.generate_assessment(course_id, [concept["id"] for concept in concepts], "Mechanics evidence check")
    services.approve_assessment(course_id, assessment["id"])
    results = (
        "student_id,assessment_item_id,concept_id,earned_points,max_points\n"
        f"S1,Q1,{concepts[0]['id']},4,4\nS1,Q2,{concepts[1]['id']},0,4\n"
        f"S2,Q1,{concepts[0]['id']},4,4\nS2,Q2,{concepts[1]['id']},1,4\n"
    )
    services.import_results(course_id, assessment["id"], results.encode())
    action = services.propose_remediation(course_id)
    revised = services.approve_remediation(course_id, action["id"], schedule["version"]["id"], [entry["id"] for entry in lessons[1:]])["schedule"]
    services.publish_schedule(course_id, revised["version"]["id"])
    return revised, services.create_offline_export(course_id, revised["version"]["id"])


def seed(fresh: bool = False) -> dict:
    db.migrate()
    try:
        account = auth.authenticate("demo@curriculumos.local", "curriculumos-demo-password")
    except DomainError:
        account = auth.create_account("demo@curriculumos.local", "curriculumos-demo-password", "Ayesha Khan")
    user_id = account["user"]["id"]
    course = build_course(user_id, fresh)
    course_id = course["id"]
    if not services.list_source_blocks(course_id):
        services.upload_document(course_id, "mechanics-demo.txt", SOURCE, "textbook", "Mechanics demo source")
    services.upload_document(course_id, "mechanics-past-paper.txt", PAST_PAPER, "past_paper", "Mechanics past paper")
    graph = services.get_graph(course_id)
    if not graph["concepts"]:
        graph = services.generate_concept_graph(course_id)
    for edge in graph["edges"]:
        if not edge["teacher_approved"]:
            services.approve_edge(course_id, edge["id"], True)
    try:
        schedule = services.get_schedule(course_id)
    except Exception:
        schedule = services.compile_schedule(course_id, CalendarInput(start_date=date(2026, 8, 3), end_date=date(2026, 9, 25), exam_date=date(2026, 9, 29), session_days=["MONDAY", "WEDNESDAY", "FRIDAY"], session_minutes=45, revision_sessions=2))
    if not any(entry["locked"] for entry in schedule["entries"] if entry["kind"] == "lesson"):
        first_lesson = next(entry for entry in schedule["entries"] if entry["kind"] == "lesson")
        services.lock_schedule_entry(course_id, first_lesson["id"])
        schedule = services.get_schedule(course_id)
    export = None
    if fresh:
        schedule, export = run_full_rehearsal(course_id, graph, schedule)
    return {"course_id": course_id, "schedule_version_id": schedule["version"]["id"], "offline_export": export["file_path"] if export else None, "email": "demo@curriculumos.local", "password": "curriculumos-demo-password", "url": "http://127.0.0.1:8000"}


def main() -> None:
    parser = ArgumentParser(description="Create a local CurriculumOS demo course.")
    parser.add_argument("--fresh", action="store_true", help="Create a new, fully exercised rehearsal course without changing an earlier demo.")
    args = parser.parse_args()
    print(json.dumps(seed(args.fresh), indent=2))


if __name__ == "__main__":
    main()
