# Master Instructions for the Coding Agent

You are implementing CurriculumOS.

Treat the files in this repository as the product contract. Do not silently change the architecture, scope, schemas, or core workflow.

## Your mission

Build a working vertical slice that demonstrates:

`source ingestion → concept graph → schedule → generated material → classroom feedback → automatic replanning → offline export`

## Priorities

1. Correctness and traceability.
2. A complete end-to-end demo.
3. Deterministic scheduling and validation.
4. Teacher control.
5. Source-grounded generation.
6. Clean interfaces between components.
7. Reliability over unnecessary sophistication.

## Forbidden shortcuts

Do not:

- use one giant prompt to produce the entire course;
- let an LLM calculate the timetable;
- store only unstructured generated text;
- generate assessments without source references;
- overwrite teacher-edited or locked content;
- claim assignments are “AI-proof”;
- rely on vector search alone;
- add Neo4j, CrewAI, AutoGen, or agent swarms;
- add microservices before the modular monolith works;
- build unrelated features from the backlog before MVP completion;
- use synthetic success screenshots in place of working behavior.

## Required engineering behavior

- Use strict typed schemas.
- Validate every model response.
- Store prompt and model versions.
- Make all long jobs idempotent.
- Cache by source hash and prompt version.
- Preserve page number and bounding-box provenance.
- Write migrations, not ad-hoc database mutations.
- Add unit tests before marking a module complete.
- Add integration tests for every stage boundary.
- Log failures with job, document, course, and trace identifiers.
- Keep human approval for prerequisite edges and high-impact schedule cuts.
- Never delete teacher content automatically.

## Repository target

```text
curriculum-os/
├── apps/
│   ├── web/                  # Next.js
│   └── api/                  # FastAPI
├── workers/
│   ├── ingestion/
│   ├── generation/
│   └── export/
├── packages/
│   ├── schemas/
│   ├── prompts/
│   ├── scheduling/
│   ├── curriculum_graph/
│   └── evaluation/
├── prefect_flows/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── golden_documents/
│   └── golden_outputs/
├── infra/
├── scripts/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Build order

Follow `docs/15_IMPLEMENTATION_PLAN.md`.

Do not start with UI polish. Start with schemas, database, ingestion, graph validation, and scheduling.

## Definition of “done”

A feature is done only when:

- schema exists;
- API or function contract exists;
- happy path works;
- invalid input is handled;
- tests exist;
- persistence works;
- logs are meaningful;
- UI exposes failure clearly;
- documentation is updated.

## Decision rule

When two implementation choices are possible, choose the one that:

1. reduces hidden state;
2. preserves deterministic replay;
3. improves source traceability;
4. is simpler to test;
5. can be replaced later behind an interface.

## Work reporting

At the end of each implementation phase, produce:

- files changed;
- database changes;
- API changes;
- tests added;
- known limitations;
- next phase;
- exact commands to run.
