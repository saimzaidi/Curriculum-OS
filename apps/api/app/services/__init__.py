"""Services package — re-exports the public API for backward compatibility.

This module re-exports every public symbol from the domain modules
so that ``from app.services import ...`` keeps working unchanged.
"""

# ── common utilities (re-exported for external callers) ──────────────
from .common import (  # noqa: F401
    EXPORT_DIR,
    PROMPT_VERSION,
    UPLOAD_DIR,
    audit,
    dump,
    load,
    new_id,
    now,
    require_course,
    require_course_access,
    row,
    rows,
)

# ── courses ─────────────────────────────────────────────────────────
from .courses import create_course, list_courses  # noqa: F401

# ── documents ───────────────────────────────────────────────────────
from .documents import (  # noqa: F401
    document_path,
    edit_source_block,
    get_job,
    list_source_blocks,
    retry_document,
    upload_document,
)

# ── concepts ────────────────────────────────────────────────────────
from .concepts import (  # noqa: F401
    approve_edge,
    edit_concept,
    generate_concept_graph,
    get_graph,
)

# ── scheduling ──────────────────────────────────────────────────────
from .scheduling import (  # noqa: F401
    _solve_positions,
    compile_schedule,
    get_schedule,
    lock_schedule_entry,
    publish_schedule,
    replan_schedule,
    session_dates,
)

# ── lessons ─────────────────────────────────────────────────────────
from .lessons import edit_lesson, generate_lesson  # noqa: F401

# ── assessments ─────────────────────────────────────────────────────
from .assessments import (  # noqa: F401
    approve_assessment,
    generate_assessment,
    import_results,
)

# ── mastery / remediation ───────────────────────────────────────────
from .mastery import (  # noqa: F401
    approve_remediation,
    propose_remediation,
    recompute_mastery,
)

# ── export ──────────────────────────────────────────────────────────
from .export import (  # noqa: F401
    create_offline_export,
    export_course_id,
    export_path,
)

# ── dashboard ───────────────────────────────────────────────────────
from .dashboard import dashboard  # noqa: F401
