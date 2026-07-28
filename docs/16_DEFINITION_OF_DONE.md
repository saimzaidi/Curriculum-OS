# Definition of Done

## Product-level completion

The MVP is complete when the following scenario works:

1. A teacher creates a course.
2. The teacher uploads a textbook and past paper.
3. The system extracts page-grounded source blocks.
4. The system proposes a concept graph.
5. The teacher approves and edits the graph.
6. The solver generates an eight-week schedule.
7. The system generates a source-grounded lesson.
8. The system generates an authentic assessment.
9. Quiz results are imported.
10. The weakest concept is identified.
11. A remediation block is proposed.
12. Two sessions are cancelled.
13. The system replans while preserving a locked lesson.
14. A schedule diff is shown.
15. The teacher publishes the new version.
16. An offline pack is exported and opened without internet.

## Engineering completion

- migrations are reproducible;
- automated tests pass;
- no secrets are committed;
- errors use the standard envelope;
- model output is schema-validated;
- jobs are idempotent;
- schedule versions are immutable;
- teacher edits survive regeneration;
- source links open the correct page;
- logs include trace and job IDs;
- README contains exact run commands.

## Quality gates

### Ingestion

- no missing pages in demo source;
- repeated headers do not dominate chunks;
- difficult page can be manually corrected.

### Curriculum graph

- no cycles;
- no dangling edges;
- every concept has source evidence.

### Schedule

- no unavailable dates;
- prerequisites respected;
- no session over capacity;
- infeasibility reported honestly.

### Generation

- no unsupported citations;
- session duration respected;
- material linked to taught concepts.

### Recall

- score calculation reproducible;
- low evidence reduces confidence;
- remediation is not inserted without approval.

### Offline export

- no remote dependency;
- no broken asset links;
- print-safe;
- contains version and checksum manifest.
