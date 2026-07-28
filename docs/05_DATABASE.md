# Database Design

Use PostgreSQL as the authoritative data store.

## Core tables

```text
organizations
users
organization_memberships
courses
course_settings
source_documents
source_pages
source_blocks
source_block_embeddings
concepts
concept_edges
concept_source_links
learning_objectives
objective_concept_links
sessions
lessons
lesson_concept_links
materials
material_source_links
assessments
assessment_items
assessment_item_concepts
assessment_item_sources
students
course_enrollments
attempts
mastery_records
remediation_actions
schedule_versions
schedule_entries
schedule_diffs
teacher_locks
generation_records
jobs
audit_events
exports
```

## Required columns on most domain tables

- `id UUID PRIMARY KEY`
- `organization_id UUID`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`
- `created_by UUID`
- `version INTEGER`
- `archived_at TIMESTAMPTZ NULL`

## Source block example

```sql
CREATE TABLE source_blocks (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    document_id UUID NOT NULL REFERENCES source_documents(id),
    page_number INTEGER NOT NULL,
    block_index INTEGER NOT NULL,
    block_type TEXT NOT NULL,
    bbox JSONB,
    raw_text TEXT,
    normalized_text TEXT,
    image_object_key TEXT,
    parser_name TEXT NOT NULL,
    parser_version TEXT,
    confidence REAL,
    content_hash TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(document_id, page_number, block_index, content_hash)
);
```

## Concept edge example

```sql
CREATE TABLE concept_edges (
    id UUID PRIMARY KEY,
    course_id UUID NOT NULL REFERENCES courses(id),
    source_concept_id UUID NOT NULL REFERENCES concepts(id),
    target_concept_id UUID NOT NULL REFERENCES concepts(id),
    relation_type TEXT NOT NULL,
    confidence REAL,
    teacher_approved BOOLEAN NOT NULL DEFAULT FALSE,
    rationale TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (source_concept_id <> target_concept_id)
);
```

For `prerequisite`:

`source_concept_id` must be learned before `target_concept_id`.

## Schedule versioning

A schedule version is immutable after publication.

```text
schedule_versions
- id
- course_id
- version_number
- parent_version_id
- trigger_type
- trigger_payload
- solver_status
- objective_score
- explanation
- created_at
- published_at
```

Every entry belongs to one version.

## Mastery storage

Store both raw and derived values:

- number of items;
- weighted score;
- confidence;
- last assessed date;
- decay-adjusted mastery;
- source assessment IDs.

Never store only a dashboard percentage with no derivation.

## Vector storage

Use pgvector on source blocks.

Keep the original normalized text and metadata beside the vector.

Retrieval must combine:

- course/document filtering;
- concept filtering;
- PostgreSQL full-text search;
- vector similarity;
- reranking.
