from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import auth, services
from . import retrieval
from .config import settings, validate_settings
from .db import ROOT, migrate
from .errors import DomainError, domain_error_handler
from .schemas import AssessmentGenerateRequest, CalendarInput, ConceptEdit, CourseCreate, LessonGenerateRequest, ReplanRequest, SignIn, SignUp, SourceBlockEdit


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=settings.environment == "production" and logging.INFO or logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    validate_settings()
    migrate()
    yield


tags_metadata = [
    {"name": "health", "description": "Service health and readiness checks."},
    {"name": "auth", "description": "Account creation, sign-in, and current-user identity."},
    {"name": "courses", "description": "Course lifecycle: create, list, and manage teaching courses."},
    {"name": "documents", "description": "Source document upload, parsing, retry, and retrieval indexing."},
    {"name": "source-blocks", "description": "Page-grounded source blocks extracted from documents."},
    {"name": "concept-graph", "description": "Concept proposals, prerequisite edges, and teacher approval."},
    {"name": "schedules", "description": "OR-Tools schedule compilation, replanning, locking, and publishing."},
    {"name": "lessons", "description": "Source-grounded lesson generation and teacher editing."},
    {"name": "assessments", "description": "Assessment generation, approval, and results import."},
    {"name": "mastery", "description": "Mastery computation and remediation proposals."},
    {"name": "exports", "description": "Offline course-pack export and download."},
    {"name": "dashboard", "description": "Aggregated course dashboard with all planning state."},
]

app = FastAPI(
    title="CurriculumOS",
    description="Local, source-grounded curriculum planner for teachers and schools.",
    version="0.2.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_exception_handler(DomainError, domain_error_handler)
security = HTTPBearer(auto_error=False)


@app.middleware("http")
async def trace_request(request: Request, call_next):
    request.state.trace_id = request.headers.get("x-trace-id", str(uuid4()))
    response = await call_next(request)
    response.headers["x-trace-id"] = request.state.trace_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request is invalid.", "details": {"errors": exc.errors()}, "trace_id": getattr(request.state, "trace_id", "request-validation")}})


def signed_in(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise DomainError("AUTHENTICATION_REQUIRED", "Sign in to continue.", status_code=401)
    return auth.current_user(credentials.credentials)


def access(course_id: str, user: dict, write: bool = False) -> None:
    services.require_course_access(course_id, user["id"], write=write)


def audit(request: Request, user: dict, course_id: str | None, action: str, entity_type: str, entity_id: str | None, details: dict | None = None) -> None:
    services.audit(course_id, user["id"], action, entity_type, entity_id, request.state.trace_id, details)


# ──────────────────────────────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["health"],
    summary="Service health check",
    description="Returns service status, operating mode, and version.",
)
def health() -> dict:
    return {"status": "ok", "mode": "local-production-path", "version": app.version}


# ──────────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/auth/sign-up",
    status_code=201,
    tags=["auth"],
    summary="Create a new account",
    description="Register a teacher account with email, password, and display name. Returns a JWT access token.",
)
def sign_up(payload: SignUp) -> dict:
    return auth.create_account(payload.email, payload.password, payload.display_name)


@app.post(
    "/api/v1/auth/sign-in",
    tags=["auth"],
    summary="Sign in",
    description="Authenticate with email and password. Returns a JWT access token.",
)
def sign_in(payload: SignIn) -> dict:
    return auth.authenticate(payload.email, payload.password)


@app.get(
    "/api/v1/auth/me",
    tags=["auth"],
    summary="Get current user",
    description="Return the authenticated user's profile (id, email, display_name).",
)
def me(user: dict = Depends(signed_in)) -> dict:
    return {key: user[key] for key in ("id", "email", "display_name")}


# ──────────────────────────────────────────────────────────────────────
# Courses
# ──────────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/courses",
    tags=["courses"],
    summary="List courses",
    description="Return all courses the authenticated user has access to, ordered by creation date.",
)
def courses(user: dict = Depends(signed_in)) -> list[dict]:
    return services.list_courses(user["id"])


@app.post(
    "/api/v1/courses",
    status_code=201,
    tags=["courses"],
    summary="Create a course",
    description="Create a new teaching course. The creating user becomes the owner.",
)
def create_course(payload: CourseCreate, request: Request, user: dict = Depends(signed_in)) -> dict:
    course = services.create_course(payload, user["id"])
    audit(request, user, course["id"], "course.created", "course", course["id"])
    return course


# ──────────────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/documents",
    status_code=201,
    tags=["documents"],
    summary="Upload a source document",
    description="Upload a PDF, TXT, or Markdown document. Parses the file into page-grounded source blocks. Duplicate content is detected by SHA-256 hash.",
)
async def upload_document(course_id: str, request: Request, file: UploadFile = File(...), document_type: str = Form("textbook"), title: str = Form(""), user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise DomainError("FILE_TOO_LARGE", f"Uploads are limited to {settings.max_upload_mb} MB.", status_code=413)
    result = services.upload_document(course_id, file.filename or "upload", content, document_type, title)
    audit(request, user, course_id, "document.uploaded", "document", result["document_id"], {"job_id": result["job_id"]})
    return result


@app.get(
    "/api/v1/jobs/{job_id}",
    tags=["documents"],
    summary="Get job status",
    description="Return the status, progress, and message for an ingestion job.",
)
def job(job_id: str, user: dict = Depends(signed_in)) -> dict:
    result = services.get_job(job_id)
    access(result["course_id"], user)
    return result


@app.get(
    "/api/v1/courses/{course_id}/documents/{document_id}/source",
    tags=["documents"],
    summary="Download source document",
    description="Return the original uploaded document file.",
)
def source_document(course_id: str, document_id: str, user: dict = Depends(signed_in)) -> FileResponse:
    access(course_id, user)
    path = services.document_path(course_id, document_id)
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


@app.post(
    "/api/v1/courses/{course_id}/documents/{document_id}/retry",
    tags=["documents"],
    summary="Retry failed document parsing",
    description="Re-attempt parsing for a document whose ingestion job previously failed.",
)
def retry_document(course_id: str, document_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.retry_document(course_id, document_id)
    audit(request, user, course_id, "document.retry", "document", document_id, {"job_id": result["id"]})
    return result


# ──────────────────────────────────────────────────────────────────────
# Source Blocks
# ──────────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/courses/{course_id}/source-blocks",
    tags=["source-blocks"],
    summary="List source blocks",
    description="Return all extracted page-grounded source blocks for a course.",
)
def source_blocks(course_id: str, user: dict = Depends(signed_in)) -> list[dict]:
    access(course_id, user)
    return services.list_source_blocks(course_id)


@app.put(
    "/api/v1/courses/{course_id}/source-blocks/{block_id}",
    tags=["source-blocks"],
    summary="Correct a source block",
    description="Teacher correction of an extracted source block. The block is marked as teacher-corrected.",
)
def update_source_block(course_id: str, block_id: str, payload: SourceBlockEdit, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.edit_source_block(course_id, block_id, payload.text)
    audit(request, user, course_id, "source_block.corrected", "source_block", block_id)
    return result


# ──────────────────────────────────────────────────────────────────────
# Retrieval
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/retrieval/rebuild",
    tags=["documents"],
    summary="Rebuild retrieval index",
    description="Rebuild the hybrid lexical + TurboVec vector index for source retrieval.",
)
def rebuild_retrieval(course_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = retrieval.rebuild(course_id)
    audit(request, user, course_id, "retrieval.rebuilt", "course", course_id, result)
    return result


@app.get(
    "/api/v1/courses/{course_id}/retrieval/search",
    tags=["documents"],
    summary="Search source evidence",
    description="Hybrid search across source blocks using lexical matching and TurboVec vector similarity.",
)
def search_sources(course_id: str, q: str = Query(..., description="Search query text"), limit: int = Query(8, ge=1, le=50, description="Max results"), user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    return retrieval.search(course_id, q, limit)


# ──────────────────────────────────────────────────────────────────────
# Concept Graph
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/concept-graph/generate",
    tags=["concept-graph"],
    summary="Generate concept proposals",
    description="Extract source-grounded concept proposals and prerequisite edges from uploaded source blocks.",
)
def generate_graph(course_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.generate_concept_graph(course_id)
    audit(request, user, course_id, "concept_graph.generated", "course", course_id)
    return result


@app.get(
    "/api/v1/courses/{course_id}/concept-graph",
    tags=["concept-graph"],
    summary="Get concept graph",
    description="Return all concepts and approved prerequisite edges for a course.",
)
def graph(course_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    return services.get_graph(course_id)


@app.post(
    "/api/v1/courses/{course_id}/concept-edges/{edge_id}/approve",
    tags=["concept-graph"],
    summary="Approve a prerequisite edge",
    description="Teacher approval of a prerequisite edge. Cycles are rejected automatically.",
)
def approve_edge(course_id: str, edge_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.approve_edge(course_id, edge_id, True)
    audit(request, user, course_id, "concept_edge.approved", "concept_edge", edge_id)
    return result


@app.post(
    "/api/v1/courses/{course_id}/concept-edges/{edge_id}/reject",
    tags=["concept-graph"],
    summary="Reject a prerequisite edge",
    description="Teacher rejection of a proposed prerequisite edge.",
)
def reject_edge(course_id: str, edge_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.approve_edge(course_id, edge_id, False)
    audit(request, user, course_id, "concept_edge.rejected", "concept_edge", edge_id)
    return result


@app.put(
    "/api/v1/courses/{course_id}/concepts/{concept_id}",
    tags=["concept-graph"],
    summary="Edit a concept",
    description="Update concept metadata (title, description, difficulty, source references). The concept status is set to approved.",
)
def update_concept(course_id: str, concept_id: str, payload: ConceptEdit, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.edit_concept(course_id, concept_id, payload)
    audit(request, user, course_id, "concept.updated", "concept", concept_id)
    return result


@app.get(
    "/api/v1/courses/{course_id}/concept-graph/topological-order",
    tags=["concept-graph"],
    summary="Get topological order",
    description="Return concepts in prerequisite-safe (topological) order using NetworkX.",
)
def topological_order(course_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    order = services.graph_topological_order(course_id)
    return {"course_id": course_id, "topological_order": order, "count": len(order)}


@app.get(
    "/api/v1/courses/{course_id}/concept-graph/metrics",
    tags=["concept-graph"],
    summary="Get graph metrics",
    description="Return NetworkX graph metrics: node/edge count, depth, density, roots, leaves, isolated concepts.",
)
def concept_graph_metrics(course_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    return services.graph_metrics(course_id)


@app.get(
    "/api/v1/courses/{course_id}/concepts/{concept_id}/impact",
    tags=["concept-graph"],
    summary="Get concept impact",
    description="Return all downstream concepts affected by changes to this concept (NetworkX descendants).",
)
def concept_impact(course_id: str, concept_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    impacted = services.graph_impact(course_id, concept_id)
    return {"concept_id": concept_id, "impacted_concept_ids": impacted, "count": len(impacted)}


@app.get(
    "/api/v1/courses/{course_id}/concepts/{concept_id}/prerequisites",
    tags=["concept-graph"],
    summary="Get transitive prerequisites",
    description="Return all transitive prerequisites of a concept (NetworkX ancestors).",
)
def concept_prerequisites(course_id: str, concept_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    prereqs = services.graph_prerequisites(course_id, concept_id)
    return {"concept_id": concept_id, "prerequisite_ids": prereqs, "count": len(prereqs)}


# ──────────────────────────────────────────────────────────────────────
# Schedules
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/schedules/compile",
    tags=["schedules"],
    summary="Compile a teaching schedule",
    description="Use OR-Tools to deterministically compile a teaching schedule respecting prerequisites, holidays, and session constraints.",
)
def compile_schedule(course_id: str, payload: CalendarInput, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.compile_schedule(course_id, payload)
    audit(request, user, course_id, "schedule.compiled", "schedule_version", result["version"]["id"])
    return result


@app.get(
    "/api/v1/courses/{course_id}/schedules/{version_id}",
    tags=["schedules"],
    summary="Get a schedule version",
    description="Return a specific schedule version with all its entries.",
)
def schedule(course_id: str, version_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    return services.get_schedule(course_id, version_id)


@app.get(
    "/api/v1/courses/{course_id}/schedules",
    tags=["schedules"],
    summary="Get latest schedule",
    description="Return the most recent schedule version for a course.",
)
def latest_schedule(course_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    return services.get_schedule(course_id)


@app.post(
    "/api/v1/courses/{course_id}/schedule-entries/{entry_id}/lock",
    tags=["schedules"],
    summary="Lock a schedule entry",
    description="Lock a schedule entry to prevent it from being moved during replanning.",
)
def lock_entry(course_id: str, entry_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.lock_schedule_entry(course_id, entry_id)
    audit(request, user, course_id, "schedule_entry.locked", "schedule_entry", entry_id)
    return result


@app.post(
    "/api/v1/courses/{course_id}/schedules/replan",
    tags=["schedules"],
    summary="Replan after cancellations",
    description="Recompile the schedule after cancelling sessions. Locked entries are preserved.",
)
def replan(course_id: str, payload: ReplanRequest, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.replan_schedule(course_id, payload.base_version_id, payload.cancelled_session_ids, payload.preserve_locked_items)
    audit(request, user, course_id, "schedule.replanned", "schedule_version", result["version"]["id"])
    return result


@app.post(
    "/api/v1/courses/{course_id}/schedules/{version_id}/publish",
    tags=["schedules"],
    summary="Publish a schedule",
    description="Mark a schedule version as published.",
)
def publish(course_id: str, version_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.publish_schedule(course_id, version_id)
    audit(request, user, course_id, "schedule.published", "schedule_version", version_id)
    return result


# ──────────────────────────────────────────────────────────────────────
# Lessons
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/schedule-entries/{entry_id}/lesson/generate",
    tags=["lessons"],
    summary="Generate a lesson",
    description="Generate a source-grounded, differentiated lesson plan for a scheduled concept entry.",
)
def generate_lesson(course_id: str, entry_id: str, payload: LessonGenerateRequest, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.generate_lesson(course_id, entry_id, payload)
    audit(request, user, course_id, "lesson.generated", "lesson", result["id"])
    return result


@app.put(
    "/api/v1/courses/{course_id}/lessons/{lesson_id}",
    tags=["lessons"],
    summary="Edit a lesson",
    description="Teacher edit of a lesson's content. Teacher-edited lessons are preserved during regeneration.",
)
def edit_lesson(course_id: str, lesson_id: str, request: Request, content: dict, locked: bool = False, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.edit_lesson(course_id, lesson_id, content, locked)
    audit(request, user, course_id, "lesson.edited", "lesson", lesson_id, {"locked": locked})
    return result


# ──────────────────────────────────────────────────────────────────────
# Assessments
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/assessments/generate",
    tags=["assessments"],
    summary="Generate an assessment",
    description="Generate a source-grounded assessment with items tied to specific concepts and source blocks.",
)
def generate_assessment(course_id: str, payload: AssessmentGenerateRequest, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.generate_assessment(course_id, payload.concept_ids, payload.title)
    audit(request, user, course_id, "assessment.generated", "assessment", result["id"])
    return result


@app.post(
    "/api/v1/courses/{course_id}/assessments/{assessment_id}/approve",
    tags=["assessments"],
    summary="Approve an assessment",
    description="Teacher approval of a generated assessment.",
)
def approve_assessment(course_id: str, assessment_id: str, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.approve_assessment(course_id, assessment_id)
    audit(request, user, course_id, "assessment.approved", "assessment", assessment_id)
    return result


@app.post(
    "/api/v1/courses/{course_id}/assessments/{assessment_id}/results/import",
    tags=["assessments"],
    summary="Import quiz results",
    description="Import quiz results from a CSV file with columns: student_id, assessment_item_id, concept_id, earned_points, max_points.",
)
async def import_results(course_id: str, assessment_id: str, request: Request, file: UploadFile = File(...), user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.import_results(course_id, assessment_id, await file.read())
    audit(request, user, course_id, "results.imported", "assessment", assessment_id, result)
    return result


# ──────────────────────────────────────────────────────────────────────
# Mastery & Remediation
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/mastery/recompute",
    tags=["mastery"],
    summary="Recompute mastery",
    description="Recompute weighted mastery scores from imported quiz attempts.",
)
def mastery(course_id: str, user: dict = Depends(signed_in)) -> list[dict]:
    access(course_id, user, write=True)
    return services.recompute_mastery(course_id)


@app.post(
    "/api/v1/courses/{course_id}/remediation/propose",
    tags=["mastery"],
    summary="Propose remediation",
    description="Identify the weakest concept and propose a remediation block based on mastery evidence.",
)
def propose_remediation(course_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    return services.propose_remediation(course_id)


@app.post(
    "/api/v1/courses/{course_id}/remediation/{action_id}/approve",
    tags=["mastery"],
    summary="Approve remediation",
    description="Approve a remediation proposal and recompile the schedule to insert the remediation block.",
)
def approve_remediation(course_id: str, action_id: str, payload: ReplanRequest, request: Request, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user, write=True)
    result = services.approve_remediation(course_id, action_id, payload.base_version_id, payload.cancelled_session_ids)
    audit(request, user, course_id, "remediation.approved", "remediation", action_id, {"version_id": result["schedule"]["version"]["id"]})
    return result


# ──────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────

@app.get(
    "/api/v1/courses/{course_id}/dashboard",
    tags=["dashboard"],
    summary="Course dashboard",
    description="Aggregated view of all planning state: sources, graph, schedule, lessons, assessments, mastery, and audit events.",
)
def course_dashboard(course_id: str, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    return services.dashboard(course_id)


# ──────────────────────────────────────────────────────────────────────
# Exports
# ──────────────────────────────────────────────────────────────────────

@app.post(
    "/api/v1/courses/{course_id}/exports/offline-pack",
    tags=["exports"],
    summary="Create offline export",
    description="Generate a self-contained HTML/ZIP offline course pack with no remote dependencies.",
)
def offline_export(course_id: str, request: Request, version_id: str | None = None, user: dict = Depends(signed_in)) -> dict:
    access(course_id, user)
    result = services.create_offline_export(course_id, version_id)
    audit(request, user, course_id, "export.created", "export", result["id"])
    return {"id": result["id"], "download_url": f"/api/v1/exports/{result['id']}/download", "manifest": result["manifest"]}


@app.get(
    "/api/v1/exports/{export_id}/download",
    tags=["exports"],
    summary="Download offline pack",
    description="Download a previously generated offline course pack ZIP file.",
)
def download_export(export_id: str, request: Request, user: dict = Depends(signed_in)) -> FileResponse:
    course_id = services.export_course_id(export_id)
    access(course_id, user)
    audit(request, user, course_id, "export.downloaded", "export", export_id)
    path = services.export_path(export_id)
    return FileResponse(path, media_type="application/zip", filename="curriculumos-offline-pack.zip")


WEB = ROOT / "apps" / "web" / "public"
if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
