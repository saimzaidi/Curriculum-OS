# Testing and Evaluation

## Testing pyramid

### Unit tests

- schema validation;
- graph cycle detection;
- topological sorting;
- mastery calculation;
- schedule constraints;
- diff calculation;
- source citation formatting;
- export manifest generation.

### Integration tests

- upload to source blocks;
- source blocks to concepts;
- concepts to schedule;
- quiz CSV to mastery;
- mastery to remediation;
- remediation to replanned schedule;
- course data to offline ZIP.

### End-to-end tests

Use Playwright for:

1. create course;
2. upload sample textbook;
3. approve graph;
4. compile schedule;
5. generate lesson;
6. import quiz results;
7. approve remediation;
8. cancel sessions;
9. replan;
10. export pack.

## Golden documents

Maintain a small fixed set:

- clean digital PDF;
- scanned English page;
- Urdu page;
- table-heavy page;
- formula-heavy page;
- past paper.

Expected artifacts:

- page count;
- headings;
- source blocks;
- concept set;
- source references.

## AI output evaluation

### Hard validation

- valid schema;
- source IDs exist;
- no unsupported citations;
- duration total fits;
- concepts exist;
- language requested;
- forbidden claims absent.

### Semantic evaluation

Use human-reviewed golden examples for:

- concept extraction;
- prerequisite quality;
- lesson grounding;
- localization equivalence;
- question difficulty;
- rubric correctness.

### Metrics

- source citation precision;
- unsupported claim rate;
- concept extraction recall;
- duplicate concept rate;
- prerequisite approval rate;
- schedule feasibility rate;
- schedule disruption score;
- OCR character error rate on sampled pages;
- teacher edit rate;
- export success rate.

## Mastery calculation test

The mastery formula must be explicit and tested.

Suggested MVP:

```text
item_score = earned_points / max_points

concept_mastery =
    weighted_mean(item_score, item_concept_weight)
```

Apply confidence reduction when item count is small.

Do not pretend one quiz gives a precise diagnosis.

## Authentic assessment test

A generated question passes when:

- linked concepts were taught;
- sources support the expected answer;
- rubric is complete;
- it is not a duplicate;
- a general-context answer is insufficient or materially weaker;
- teacher approves it.

## Performance targets

For the demo dataset:

- API CRUD p95 under 500 ms;
- schedule compile under 5 seconds;
- replan under 5 seconds;
- lesson generation progress visible;
- export under 60 seconds;
- failed model call recoverable through retry.
