# Frontend and Teacher UX

## Design principle

The product should feel like curriculum control software, not a chat application.

## Main screens

### 1. Workspace dashboard

Shows:

- active courses;
- syllabus risk;
- upcoming classes;
- weak concepts;
- pending approvals;
- recent schedule changes.

### 2. Course setup

Wizard:

1. upload source material;
2. define class and subject;
3. set term dates;
4. set session days and duration;
5. set holidays and exam dates;
6. choose language and regional context.

### 3. Source review

- document list;
- processing state;
- page viewer;
- extracted block overlays;
- flagged OCR pages;
- reprocess option.

### 4. Curriculum graph

React Flow interface:

- concept nodes;
- prerequisite edges;
- source count;
- difficulty;
- estimated time;
- confidence;
- approval controls.

Teacher can:

- edit concept;
- approve/reject edge;
- add edge;
- lock concept;
- open source pages.

### 5. Schedule

Calendar plus list view.

Each lesson shows:

- concept;
- duration;
- status;
- difficulty;
- source references;
- lock state.

Actions:

- completed;
- partially completed;
- skipped;
- ran over;
- ran under;
- lock;
- move manually;
- request replan.

### 6. Lesson workspace

Tabs:

- teacher plan;
- explanation;
- local examples;
- activities;
- differentiated versions;
- homework;
- sources.

Teacher can edit and lock any section.

### 7. Assessment workspace

- concept coverage;
- question;
- rubric;
- difficulty;
- source evidence;
- shallow-answer resistance score;
- regenerate;
- approve.

### 8. Recall dashboard

Show:

- concept mastery heatmap;
- most-missed concept;
- prerequisite chain;
- proposed remediation;
- schedule impact.

Avoid a dashboard that only reports failure. Always show the action.

### 9. Replanning review

Show before/after diff:

- moved;
- added;
- compressed;
- removed;
- protected;
- risk.

Teacher must approve high-impact changes.

### 10. Export

Options:

- offline HTML;
- print-safe teacher pack;
- student notes;
- quizzes and answer keys;
- selected date range.

## Offline behavior

Cache:

- latest published schedule;
- lesson content;
- teacher edits pending sync;
- source snippets needed for active lessons.

Use a visible synchronization state:

- synced;
- offline;
- changes pending;
- conflict;
- failed.

## Accessibility

- keyboard navigation;
- high contrast;
- no color-only status meaning;
- readable print mode;
- Urdu right-to-left support;
- minimum touch target sizes.
