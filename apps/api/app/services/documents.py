"""Document upload, parsing, and source block management."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from ..db import connect
from ..errors import DomainError
from . import common
from .common import dump, load, new_id, now, require_course, row, rows


def _document_blocks(path: Path, suffix: str) -> list[tuple[int, str, tuple[float, float, float, float], float]]:
    if suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise DomainError("DOCUMENT_ENCRYPTED", "Encrypted PDFs cannot be processed.", status_code=422)
            pages = []
            for index, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                pages.append((index, text, (0, 0, width, height), 0.95 if text.strip() else 0.1))
            return pages
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError("DOCUMENT_PARSE_FAILED", "The PDF could not be read.", {"reason": str(exc)}, 422) from exc
    return [(1, path.read_text(encoding="utf-8", errors="replace"), (0, 0, 0, 0), 1.0)]


def _source_block_rows(course_id: str, document_id: str, stored: Path, pages: list[tuple[int, str, tuple[float, float, float, float], float]]) -> list[tuple[Any, ...]]:
    blocks: list[tuple[Any, ...]] = []
    for page_number, text, bbox, confidence in pages:
        fragments = [fragment.strip() for fragment in re.split(r"\n\s*\n+", text) if fragment.strip()] or [""]
        for block_index, raw_text in enumerate(fragments):
            normalized = re.sub(r"\s+", " ", raw_text).strip()
            flags = ["blank_page"] if not normalized else []
            blocks.append((new_id(), course_id, document_id, page_number, block_index, "heading" if block_index == 0 else "paragraph", dump(bbox), raw_text, normalized, "pypdf" if stored.suffix == ".pdf" else "plain_text", "1", confidence, hashlib.sha256(normalized.encode()).hexdigest(), dump(flags)))
    return blocks


def _insert_job(conn: sqlite3.Connection, job_id: str, course_id: str, document_id: str, idempotency_key: str, status: str, stage: str, progress: float, message: str, error: str | None, timestamp: str) -> None:
    conn.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (job_id, course_id, document_id, "ingestion", idempotency_key, status, stage, progress, message, error, new_id(), timestamp, timestamp))


def upload_document(course_id: str, filename: str, content: bytes, document_type: str, title: str) -> dict[str, Any]:
    require_course(course_id)
    if not filename or Path(filename).suffix.lower() not in {".pdf", ".txt", ".md"}:
        raise DomainError("INVALID_DOCUMENT", "Upload a PDF, TXT, or Markdown document.", status_code=422)
    if not content:
        raise DomainError("INVALID_DOCUMENT", "The uploaded file is empty.", status_code=422)
    digest = hashlib.sha256(content).hexdigest()
    with connect() as conn:
        duplicate = row(conn.execute("SELECT * FROM documents WHERE course_id = ? AND content_hash = ?", (course_id, digest)).fetchone())
        if duplicate:
            existing_job = row(conn.execute("SELECT * FROM jobs WHERE document_id = ? ORDER BY created_at DESC LIMIT 1", (duplicate["id"],)).fetchone())
            return {"document_id": duplicate["id"], "job_id": existing_job["id"], "status": existing_job["status"], "duplicate": True}

    document_id, job_id, timestamp = new_id(), new_id(), now()
    stored = common.UPLOAD_DIR / course_id / f"{document_id}{Path(filename).suffix.lower()}"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_bytes(content)
    parser_name = "pypdf" if stored.suffix == ".pdf" else "plain_text"
    idempotency_key = f"{course_id}:{digest}:pypdf:1"
    try:
        pages = _document_blocks(stored, stored.suffix)
    except DomainError as exc:
        with connect() as conn:
            conn.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)", (document_id, course_id, title or Path(filename).stem, document_type, digest, str(stored), parser_name, "1", 0, timestamp))
            _insert_job(conn, job_id, course_id, document_id, idempotency_key, "failed", "parsing", 0.0, "Source parsing failed. Retry after correcting the document.", dump({"code": exc.code, "details": exc.details}), timestamp)
        raise DomainError(exc.code, exc.message, {**exc.details, "document_id": document_id, "job_id": job_id}, exc.status_code) from exc
    blocks = _source_block_rows(course_id, document_id, stored, pages)
    with connect() as conn:
        conn.execute(
            """INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (document_id, course_id, title or Path(filename).stem, document_type, digest, str(stored), parser_name, "1", len(pages), timestamp),
        )
        _insert_job(conn, job_id, course_id, document_id, idempotency_key, "completed", "persisted", 1.0, f"Extracted {len(blocks)} page-grounded blocks.", None, timestamp)
        conn.executemany("INSERT INTO source_blocks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", blocks)
    return {"document_id": document_id, "job_id": job_id, "status": "completed", "duplicate": False}


def get_job(job_id: str) -> dict[str, Any]:
    with connect() as conn:
        job = row(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())
    if not job:
        raise DomainError("JOB_NOT_FOUND", "Job was not found.", {"job_id": job_id}, 404)
    return {key: job[key] for key in ("id", "course_id", "status", "stage", "progress", "message", "error", "trace_id")}


def retry_document(course_id: str, document_id: str) -> dict[str, Any]:
    with connect() as conn:
        document = row(conn.execute("SELECT * FROM documents WHERE id=? AND course_id=?", (document_id, course_id)).fetchone())
    if not document:
        raise DomainError("DOCUMENT_NOT_FOUND", "Source document was not found.", status_code=404)
    path = Path(document["file_path"])
    if not path.is_file():
        raise DomainError("SOURCE_FILE_MISSING", "The stored source file is unavailable; upload it again.", status_code=422)
    job_id, timestamp = new_id(), now()
    with connect() as conn:
        _insert_job(conn, job_id, course_id, document_id, f"{course_id}:{document['content_hash']}:retry:{job_id}", "running", "parsing", 0.1, "Retrying source parsing.", None, timestamp)
    try:
        pages = _document_blocks(path, path.suffix)
        blocks = _source_block_rows(course_id, document_id, path, pages)
    except DomainError as exc:
        with connect() as conn:
            conn.execute("UPDATE jobs SET status='failed',stage='parsing',progress=0,message=?,error=?,updated_at=? WHERE id=?", ("Source parsing failed. Retry after correcting the document.", dump({"code": exc.code, "details": exc.details}), now(), job_id))
        raise DomainError(exc.code, exc.message, {**exc.details, "document_id": document_id, "job_id": job_id}, exc.status_code) from exc
    with connect() as conn:
        conn.execute("DELETE FROM source_blocks WHERE document_id=?", (document_id,))
        conn.executemany("INSERT INTO source_blocks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", blocks)
        conn.execute("UPDATE documents SET page_count=?,parser_name=?,parser_version=? WHERE id=?", (len(pages), "pypdf" if path.suffix == ".pdf" else "plain_text", "1", document_id))
        conn.execute("UPDATE jobs SET status='completed',stage='persisted',progress=1,message=?,error=NULL,updated_at=? WHERE id=?", (f"Extracted {len(blocks)} page-grounded blocks.", now(), job_id))
    return get_job(job_id)


def document_path(course_id: str, document_id: str) -> Path:
    with connect() as conn:
        document = row(conn.execute("SELECT file_path FROM documents WHERE id=? AND course_id=?", (document_id, course_id)).fetchone())
    if not document or not Path(document["file_path"]).is_file():
        raise DomainError("DOCUMENT_NOT_FOUND", "Source document was not found.", status_code=404)
    return Path(document["file_path"])


def list_source_blocks(course_id: str) -> list[dict[str, Any]]:
    require_course(course_id)
    with connect() as conn:
        result = rows(conn.execute("SELECT * FROM source_blocks WHERE course_id = ? ORDER BY document_id, page_number, block_index", (course_id,)).fetchall())
    for item in result:
        item["bbox"] = load(item.pop("bbox_json"))
        item["quality_flags"] = load(item.pop("quality_flags_json"))
    return result


def edit_source_block(course_id: str, block_id: str, text: str) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        raise DomainError("INVALID_SOURCE_BLOCK", "Source block text cannot be blank.", status_code=422)
    with connect() as conn:
        block = row(conn.execute("SELECT quality_flags_json FROM source_blocks WHERE id=? AND course_id=?", (block_id, course_id)).fetchone())
        if not block:
            raise DomainError("SOURCE_BLOCK_NOT_FOUND", "Source block was not found.", status_code=404)
        flags = sorted(set(load(block["quality_flags_json"]) + ["teacher_corrected"]))
        conn.execute("UPDATE source_blocks SET raw_text=?,normalized_text=?,content_hash=?,quality_flags_json=? WHERE id=?", (text.strip(), normalized, hashlib.sha256(normalized.encode()).hexdigest(), dump(flags), block_id))
    return next(item for item in list_source_blocks(course_id) if item["id"] == block_id)
