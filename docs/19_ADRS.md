# Architecture Decision Records

## ADR-001 — Modular monolith

**Decision:** Use one repository and one application boundary with worker processes.

**Reason:** Faster iteration, shared transactions, simpler testing, adequate for MVP.

## ADR-002 — PostgreSQL for curriculum graph

**Decision:** Store graph edges in PostgreSQL.

**Reason:** Graph data is tightly coupled to schedules, sources, assessments, versions, and permissions.

## ADR-003 — OR-Tools owns scheduling

**Decision:** Use CP-SAT for initial scheduling and replanning.

**Reason:** Dates and constraints require deterministic correctness and infeasibility detection.

## ADR-004 — Prefect for background workflows

**Decision:** Use Prefect instead of an agent framework.

**Reason:** Workflows are predefined, typed, retryable, and observable.

## ADR-005 — Hosted Qwen models

**Decision:** Use Alibaba Model Studio during the hackathon.

**Reason:** Reduces infrastructure risk and aligns with the hackathon technology partner.

## ADR-006 — Hybrid document parsing

**Decision:** Route pages between MinerU, PaddleOCR, and Qwen OCR.

**Reason:** Textbooks, Urdu scans, formulas, diagrams, and past papers fail differently.

## ADR-007 — Human approval for high-impact changes

**Decision:** Require approval for prerequisite edges, removed concepts, and significant schedule compression.

**Reason:** AI uncertainty should not silently alter official curriculum.

## ADR-008 — Offline export is pregenerated

**Decision:** Export static material rather than run a local LLM.

**Reason:** Target machines may be old and connectivity may be unavailable.

## ADR-009 — Immutable schedule versions

**Decision:** Published schedules cannot be modified in place.

**Reason:** Teachers and administrators need auditability and rollback.

## ADR-010 — No AI-proof claim

**Decision:** Describe assessments as resistant to shallow AI answering.

**Reason:** No assignment is categorically immune to capable AI.
