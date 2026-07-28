# Implementation Plan

## Phase 0 — Repository and contracts

Deliver:

- monorepo;
- Docker Compose;
- schemas;
- database connection;
- migrations;
- logging;
- error envelope;
- CI.

Exit criteria:

- web and API boot;
- migration passes;
- test command passes;
- health endpoint works.

## Phase 1 — Course setup and document upload

Deliver:

- organization/user/course;
- upload UI;
- OSS/MinIO storage;
- document job;
- job status UI.

Exit criteria:

- upload persists;
- duplicate hash detected;
- failed upload visible.

## Phase 2 — Ingestion

Deliver:

- PyMuPDF preflight;
- MinerU adapter;
- OCR adapter interface;
- source blocks;
- source review page.

Exit criteria:

- sample textbook produces page-grounded blocks;
- page references are clickable;
- parser failures are recoverable.

## Phase 3 — Concept graph

Deliver:

- concept extraction prompt;
- strict schema;
- concept and edge storage;
- NetworkX validation;
- React Flow review UI.

Exit criteria:

- teacher can approve/reject edges;
- cycles are blocked;
- concepts open source evidence.

## Phase 4 — Initial scheduling

Deliver:

- session calendar;
- OR-Tools compiler;
- constraints;
- schedule version;
- calendar UI.

Exit criteria:

- valid eight-week schedule;
- prerequisites respected;
- holidays avoided;
- locks preserved.

## Phase 5 — Lesson generation

Deliver:

- grounded lesson generation;
- three levels;
- local examples;
- activity;
- homework;
- source citations;
- teacher edit and lock.

Exit criteria:

- one lesson passes hard validation;
- teacher edit survives regeneration.

## Phase 6 — Assessment

Deliver:

- question generation;
- rubric;
- source links;
- duplicate fingerprint;
- shallow-answer adversarial pass;
- approval UI.

Exit criteria:

- one assessment is generated and approved;
- duplicate generation is prevented.

## Phase 7 — Recall loop

Deliver:

- quiz CSV import;
- assessment item mapping;
- mastery calculation;
- friction heatmap;
- remediation proposal.

Exit criteria:

- weak concept is correctly identified;
- evidence is visible;
- teacher can approve remediation.

## Phase 8 — Replanning

Deliver:

- cancelled-session trigger;
- remediation trigger;
- minimum-disruption objective;
- schedule diff;
- approval.

Exit criteria:

- two classes are cancelled;
- remediation is inserted;
- schedule recompiles;
- locked lesson remains;
- diff explains changes.

## Phase 9 — Offline export

Deliver:

- static pack compiler;
- print templates;
- ZIP;
- download.

Exit criteria:

- pack opens with network disabled;
- lesson and quiz search works;
- PDFs print correctly.

## Phase 10 — Demo hardening

Deliver:

- seed data;
- scripted demo;
- loading states;
- retry controls;
- observability;
- backup demo video;
- final test run.

Exit criteria:

- full demo repeated three times without manual database changes.

## Rule

Do not begin Phase N+1 until the exit criteria for Phase N pass.
