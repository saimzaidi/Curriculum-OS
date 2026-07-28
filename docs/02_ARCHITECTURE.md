# System Architecture

## Architecture style

Use a modular monolith with background workers.

The web application, API, scheduling engine, graph logic, and AI adapters live in one repository with explicit package boundaries.

Do not split into microservices before load or team size justifies it.

## High-level components

```mermaid
flowchart LR
    U[Teacher or Coordinator] --> W[Next.js Web App]
    W --> A[FastAPI Application]
    A --> DB[(PostgreSQL + pgvector)]
    A --> OSS[Object Storage]
    A --> PF[Prefect API / Job Submission]

    PF --> IW[Ingestion Worker]
    PF --> GW[Generation Worker]
    PF --> EW[Export Worker]

    IW --> MP[MinerU]
    IW --> OCR[Qwen OCR / PaddleOCR]
    IW --> DB
    IW --> OSS

    GW --> QW[Qwen Model Adapter]
    GW --> RR[Embedding + Reranking]
    GW --> DB

    A --> CG[Curriculum Graph Service]
    A --> SE[OR-Tools Scheduling Service]
    CG --> NX[NetworkX Validation]
    SE --> DB

    EW --> PG[Paged.js / Static Pack Compiler]
    EW --> OSS
```

## Separation of responsibilities

### Next.js

- forms;
- dashboards;
- graph review;
- schedule editing;
- progress input;
- export initiation;
- offline cache.

### FastAPI

- authentication;
- authorization;
- CRUD;
- job submission;
- curriculum state transitions;
- orchestration between deterministic services;
- signed download URLs.

### Prefect

- long-running ingestion;
- extraction;
- embedding;
- generation;
- export;
- retries;
- progress state.

### PostgreSQL

- all authoritative product state;
- relationships;
- versions;
- audit records;
- embeddings;
- job records.

### Object storage

- original uploads;
- normalized files;
- page images;
- generated assets;
- offline packs.

### Qwen

- semantic extraction;
- concept proposals;
- localization;
- lesson generation;
- question generation;
- rubric generation;
- explanation.

### OR-Tools

- timetable creation;
- timetable repair;
- constrained compression;
- remediation placement;
- buffer preservation.

### NetworkX

- cycle detection;
- topological order;
- dependency validation;
- impact traversal;
- graph metrics.

## Core event flow

```mermaid
sequenceDiagram
    participant T as Teacher
    participant API as FastAPI
    participant PF as Prefect
    participant ING as Ingestion
    participant DB as PostgreSQL
    participant AI as Qwen
    participant SCH as OR-Tools

    T->>API: Upload documents and course settings
    API->>PF: Start ingestion job
    PF->>ING: Parse and normalize
    ING->>DB: Store source blocks
    PF->>AI: Extract concept proposals
    AI->>DB: Store proposed graph
    T->>API: Approve or edit graph
    API->>SCH: Compile schedule
    SCH->>DB: Save schedule version
    T->>API: Import quiz results
    API->>SCH: Insert remediation and recompile
    SCH->>DB: Save new schedule version + diff
```

## State rule

All important state must be reconstructable from PostgreSQL and object storage.

Do not depend on:

- in-memory agent state;
- chat history;
- browser-only data;
- Prefect internal state as the source of truth.
