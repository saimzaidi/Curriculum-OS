# API Contracts

All APIs use JSON unless uploading or downloading files.

Base path:

`/api/v1`

## Authentication

Use bearer access tokens.

Every request must resolve:

- user;
- organization;
- role;
- course access.

## Documents

### Upload document

`POST /courses/{course_id}/documents`

Multipart fields:

- `file`
- `document_type`
- `title`
- `language_hint`

Response:

```json
{
  "document_id": "uuid",
  "job_id": "uuid",
  "status": "queued"
}
```

### Get ingestion status

`GET /jobs/{job_id}`

```json
{
  "status": "running",
  "stage": "ocr",
  "progress": 0.62,
  "message": "Processing page 18 of 29",
  "error": null
}
```

## Concepts

### Generate concept graph

`POST /courses/{course_id}/concept-graph/generate`

### Get graph

`GET /courses/{course_id}/concept-graph`

### Approve edge

`POST /courses/{course_id}/concept-edges/{edge_id}/approve`

### Reject edge

`POST /courses/{course_id}/concept-edges/{edge_id}/reject`

### Create or edit concept

`PUT /courses/{course_id}/concepts/{concept_id}`

## Scheduling

### Compile initial schedule

`POST /courses/{course_id}/schedules/compile`

```json
{
  "start_date": "2026-08-22",
  "end_date": "2026-10-17",
  "exam_date": "2026-10-20",
  "session_days": ["MONDAY", "WEDNESDAY", "FRIDAY"],
  "session_minutes": 45,
  "revision_sessions": 2
}
```

### Replan schedule

`POST /courses/{course_id}/schedules/replan`

```json
{
  "base_version_id": "uuid",
  "trigger": {
    "type": "cancelled_sessions",
    "session_ids": ["uuid", "uuid"]
  },
  "preserve_locked_items": true,
  "minimize_disruption": true
}
```

### Publish schedule

`POST /courses/{course_id}/schedules/{version_id}/publish`

## Lesson generation

`POST /courses/{course_id}/lessons/{lesson_id}/generate`

```json
{
  "language": "en",
  "localization_region": "Karachi, Pakistan",
  "levels": ["below", "on", "advanced"],
  "include_activity": true,
  "include_homework": true
}
```

## Assessment

### Generate authentic assessment

`POST /courses/{course_id}/assessments/generate`

### Import results

`POST /courses/{course_id}/assessments/{assessment_id}/results/import`

CSV format is specified in `examples/quiz-results.csv`.

### Compute mastery

`POST /courses/{course_id}/mastery/recompute`

## Remediation

### Propose remediation

`POST /courses/{course_id}/remediation/propose`

### Approve remediation and replan

`POST /courses/{course_id}/remediation/{action_id}/approve`

## Export

### Create offline pack

`POST /courses/{course_id}/exports/offline-pack`

### Download export

`GET /exports/{export_id}/download`

## Errors

Use a consistent error envelope:

```json
{
  "error": {
    "code": "SCHEDULE_INFEASIBLE",
    "message": "The remaining required concepts cannot fit before the exam.",
    "details": {
      "required_minutes": 540,
      "available_minutes": 405,
      "locked_session_ids": []
    },
    "trace_id": "uuid"
  }
}
```
