from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    trace_id = request.headers.get("x-trace-id", str(uuid4()))
    details = exc.details
    logging.getLogger("curriculumos").warning(
        "domain_error code=%s path=%s course_id=%s document_id=%s job_id=%s trace_id=%s",
        exc.code,
        request.url.path,
        details.get("course_id") or request.path_params.get("course_id"),
        details.get("document_id") or request.path_params.get("document_id"),
        details.get("job_id") or request.path_params.get("job_id"),
        trace_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details, "trace_id": trace_id}},
    )
