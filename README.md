# CurriculumOS

CurriculumOS is a local, source-grounded curriculum planner for teachers and schools. This repository now contains a working offline-capable vertical slice rather than only the product contract.

It converts textbooks, supplementary material, past papers, academic calendars, and classroom feedback into a source-grounded curriculum that can:

- build a term plan;
- generate lessons, notes, activities, homework, and assessments;
- track planned versus actual coverage;
- detect weak concepts;
- insert remediation automatically;
- recompile the remaining timetable after delays;
- protect prerequisite and exam-critical concepts;
- localize examples for Pakistani classrooms;
- export a complete offline course pack.

## What works locally

- PDF, TXT, and Markdown ingestion with SHA-256 duplicate detection, page number, bounding box, parser, and confidence provenance; failed parses are retained as retryable jobs and teachers can correct a source block without losing provenance.
- Source-grounded concept proposals and teacher approval of prerequisite edges with cycle protection.
- OR-Tools deterministic schedule compilation, revision protection, infeasibility reporting, immutable versions, and locked-lesson preservation during replanning.
- Validated local lesson and assessment generation with stored prompt/model versions and source citations.
- Quiz CSV import, reproducible mastery calculation, remediation proposal, teacher approval, and schedule diff.
- Self-contained HTML offline course ZIP with no remote assets or API dependency.
- Account-based access controls, course-level roles, audit events, trace IDs, upload limits, and a production-mode secret guard.
- Hybrid source retrieval using TurboVec plus a RAG-Anything multimodal adapter that activates only when its model provider is configured.

Cloud hosting, managed PostgreSQL/pgvector, object storage, and hosted model adapters are intentionally deferred. The local demo uses SQLite, filesystem storage, deterministic generation, and local background-free jobs so it can run without cloud credentials.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps\api --reload
```

For a clean, end-to-end rehearsal course (lesson, assessment, classroom results, approved remediation, revised plan, and offline export), run:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo.py --fresh
```

Open `http://127.0.0.1:8000`. The local teacher shell handles course creation, source ingestion, graph proposal and approval, schedule compilation, lesson/assessment generation, feedback, remediation, replanning, and offline export. API documentation is available at `http://127.0.0.1:8000/docs`.

Run all checks with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Verify the full rehearsal loop three times in isolated local storage:

```powershell
.\.venv\Scripts\python.exe scripts\verify_demo.py
```

## Demo inputs

- `examples/course-config.json` contains an eight-week calendar shape.
- `examples/quiz-results.csv` shows the accepted CSV headers. Replace `concept_id` values with IDs returned by the concept graph for a live course.
- `scripts/seed_demo.py` creates an idempotent mechanics demo course. `--fresh` creates a separate completed rehearsal course and never deletes earlier teacher work.

## TurboVec and RAG-Anything

TurboVec is the active local vector index for source-block retrieval. RAG-Anything is integrated as the optional multimodal indexer because it requires a model provider and heavier parsing dependencies. To enable it, install its full runtime with `pip install -r requirements-rag-anything.txt`, set `RAG_ANYTHING_ENABLED=true` and `RAG_ANYTHING_API_KEY`, then rebuild retrieval for a course. If it is not configured, the app remains fully functional with deterministic hybrid lexical + TurboVec search; the retrieval response exposes that state rather than claiming multimodal indexing occurred.

## Local architecture

`apps/api` is the FastAPI modular monolith, `apps/web/public` is the local teacher shell, `migrations` holds the reproducible SQLite schema, and `tests` verifies the stage boundaries. The original product documents remain the product contract and planned cloud evolution.

## Product contract

Read these files in order:

1. `AGENTS.md`
2. `docs/00_PRODUCT_BRIEF.md`
3. `docs/01_MVP_SCOPE.md`
4. `docs/02_ARCHITECTURE.md`
5. `docs/03_TECH_STACK.md`
6. `docs/04_DOMAIN_MODEL.md`
7. `docs/05_DATABASE.md`
8. `docs/06_API_CONTRACTS.md`
9. `docs/07_AI_PIPELINES.md`
10. `docs/08_SCHEDULING_ENGINE.md`
11. `docs/09_DOCUMENT_INGESTION.md`
12. `docs/10_FRONTEND_UX.md`
13. `docs/11_OFFLINE_EXPORT.md`
14. `docs/12_TESTING_EVALUATION.md`
15. `docs/13_SECURITY_PRIVACY.md`
16. `docs/14_DEPLOYMENT.md`
17. `docs/15_IMPLEMENTATION_PLAN.md`
18. `docs/16_DEFINITION_OF_DONE.md`
19. `docs/17_DEMO_SCRIPT.md`
20. `docs/18_BACKLOG.md`
21. `docs/19_ADRS.md`
22. `docs/20_REFERENCES.md`

## Non-negotiable product principle

The LLM performs semantic extraction and content generation.

Deterministic software owns:

- dates;
- schedules;
- prerequisites;
- source links;
- versions;
- teacher locks;
- validation;
- database writes;
- optimization;
- authorization.

Do not build CurriculumOS as an autonomous agent swarm.

## End-to-end acceptance story

A teacher uploads:

- one textbook;
- one past paper;
- an eight-week calendar;
- class frequency;
- an exam date.

CurriculumOS:

1. extracts chapters and source blocks;
2. proposes a concept dependency graph;
3. creates a valid teaching schedule;
4. generates one grounded lesson and assessment;
5. accepts quiz results;
6. identifies the weakest concept;
7. inserts remediation;
8. cancels two future classes;
9. recompiles the timetable without moving locked lessons;
10. exports the revised course as an offline HTML/PDF package.

If this complete loop works reliably, the local product workflow is ready for rehearsal and demonstration.
