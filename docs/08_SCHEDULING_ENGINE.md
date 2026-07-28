# Scheduling and Replanning Engine

## Core principle

The schedule is compiled by OR-Tools CP-SAT.

The LLM does not assign dates.

## Inputs

### Concepts

- duration in minutes;
- prerequisites;
- priority;
- exam weight;
- difficulty;
- required/optional;
- compressibility;
- minimum review spacing.

### Calendar

- available session dates;
- session duration;
- holidays;
- exam dates;
- teacher unavailability;
- locked sessions;
- fixed practicals.

### Feedback

- completed;
- partially completed;
- skipped;
- ran over;
- ran under;
- class mastery;
- remediation requirement.

## Hard constraints

- prerequisite before dependent concept;
- no lesson on unavailable date;
- locked lesson remains fixed;
- fixed exam cannot move;
- required concepts finish before revision;
- one session cannot exceed available minutes;
- a concept cannot be scheduled twice unless marked as review/remediation;
- a lesson cannot be assigned to overlapping sessions.

## Soft constraints

- minimize changes from the published schedule;
- protect revision sessions;
- distribute high-difficulty concepts;
- avoid consecutive overloaded sessions;
- preserve teacher preferred pacing;
- place remediation soon after evidence of failure;
- prefer compressing optional content before required content;
- preserve past-paper weighted concepts;
- maintain spaced review.

## Objective function

Use weighted penalties:

```text
total_penalty =
    moved_locked_like_items * very_high_weight
  + removed_required_concepts * very_high_weight
  + lost_revision_sessions * high_weight
  + moved_existing_lessons * medium_weight
  + compressed_concepts * medium_weight
  + difficult_concept_clustering * low_weight
  + unused_capacity * low_weight
```

Actual weights must be configuration, not hard-coded throughout the solver.

## Infeasibility

Never fabricate a schedule when constraints cannot be satisfied.

Return:

- solver status;
- required minutes;
- available minutes;
- conflicting locks;
- protected concepts preventing compression;
- ranked resolution options.

Example:

```json
{
  "status": "infeasible",
  "required_minutes": 540,
  "available_minutes": 405,
  "options": [
    "Remove 90 minutes of optional enrichment",
    "Reduce revision from 3 sessions to 2",
    "Add one Saturday session",
    "Move the exam date"
  ]
}
```

The teacher chooses the trade-off.

## Replanning triggers

- cancelled session;
- added holiday;
- class ran over;
- class ran under;
- weak mastery;
- teacher lock;
- changed exam date;
- concept manually removed;
- substitute teacher limitation.

## Schedule diff

Every replan must produce:

- moved lessons;
- inserted lessons;
- removed optional content;
- compressed content;
- changed revision sessions;
- reasons;
- affected concepts;
- risk level.

## Tests

At minimum:

- prerequisite order;
- no holiday scheduling;
- lock preservation;
- valid initial compile;
- cancellation repair;
- remediation insertion;
- infeasible case;
- minimum-disruption behavior;
- deterministic result for identical input.
