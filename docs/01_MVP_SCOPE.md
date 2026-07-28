# MVP Scope

## MVP objective

Prove that CurriculumOS is an adaptive curriculum compiler, not a PDF chatbot.

## Required input

- one PDF textbook;
- optional supplementary PDF or past paper;
- grade/class level;
- subject;
- course start and end dates;
- class days or sessions per week;
- fixed holidays;
- exam date;
- language preference;
- one CSV of quiz results.

## Required output

- extracted source blocks with page references;
- chapter/topic structure;
- concept dependency graph;
- eight-week schedule;
- one generated lesson;
- one localized example set;
- one differentiated activity at three levels;
- one authentic assessment;
- one friction heatmap;
- one remediation block;
- a recompiled schedule after two cancelled classes;
- an offline course ZIP containing HTML and printable PDFs.

## MVP features

### Must have

- Upload and parse a textbook.
- Detect chapters and source blocks.
- Build and review a concept graph.
- Generate a valid schedule using OR-Tools.
- Lock lessons or concepts.
- Generate grounded lesson content.
- Import quiz CSV.
- Calculate concept mastery.
- Insert remediation.
- Replan after lost classes.
- Explain schedule changes.
- Export offline package.
- Preserve full version history.

### Should have

- Local example replacement.
- Three-level lesson differentiation.
- Past-paper concept weighting.
- Print-safe black-and-white output.
- One-click “ran over / ran under” update.
- Spaced review insertion.

### Explicitly out of scope

- student mobile application;
- full LMS;
- attendance integration;
- plagiarism detection;
- AI-writing detection;
- voice-first interface;
- education-department reporting;
- multi-school billing;
- autonomous grading of high-stakes work;
- full Urdu speech recognition;
- self-hosted large generation models;
- agent swarms;
- Neo4j.

## Demo dataset limit

For the hackathon demo:

- 1–3 documents;
- 2–4 chapters;
- 20–60 concepts;
- 20–40 sessions;
- 1 class section;
- 10–40 students;
- 1 quiz import.

The architecture may support more, but the demo must remain reliable.
