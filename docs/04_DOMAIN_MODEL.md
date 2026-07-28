# Domain Model

## Main entities

### Organization

A school, academy, or independent teacher workspace.

### User

A teacher, coordinator, administrator, or owner.

### Course

A teaching instance for one subject, grade, section, and term.

### SourceDocument

A textbook, supplementary reader, past paper, calendar, or teacher-created resource.

### SourceBlock

A normalized unit extracted from a document.

Fields include:

- document;
- page;
- bounding box;
- block type;
- raw text;
- normalized text;
- image reference;
- parser;
- confidence;
- content hash.

### Concept

A teachable knowledge unit.

Fields include:

- title;
- description;
- difficulty;
- estimated minutes;
- exam weight;
- required or optional;
- source links;
- status;
- teacher approval.

### ConceptEdge

A relation between concepts.

Supported relations:

- prerequisite;
- part_of;
- reinforces;
- commonly_confused_with;
- assessed_by.

Only `prerequisite` participates in topological scheduling.

### LearningObjective

A measurable outcome linked to concepts and source material.

### Session

A calendar slot where teaching can occur.

### Lesson

The planned teaching content assigned to a session.

### Material

Notes, activities, homework, slides, worksheets, or teacher scripts.

### Assessment

A quiz, test, warm-up, assignment, or exam.

### AssessmentItem

A question with rubric, difficulty, source links, and concept links.

### Student

A learner in a course section.

### Attempt

A student's response or score for an assessment item.

### MasteryRecord

Computed mastery for a student or class on a concept.

### RemediationAction

A proposed or approved response to low mastery.

### ScheduleVersion

An immutable schedule snapshot.

### ScheduleDiff

A human-readable and machine-readable comparison between schedule versions.

### GenerationRecord

Stores model, prompt, schema, source blocks, output, validation result, and teacher status.

### TeacherLock

Prevents automatic changes to a concept, lesson, material, assessment, or date.

## Important invariants

- Every generated lesson must link to at least one source block.
- Every assessment item must link to at least one concept.
- Every scheduled concept must have a positive duration.
- A prerequisite must be scheduled before its dependent concept.
- Locked items cannot move during automatic replanning.
- Published schedule versions are immutable.
- Teacher edits are never overwritten automatically.
- A removed concept is archived, not hard deleted.
