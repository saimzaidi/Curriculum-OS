# AI Pipelines

## Rule

Every LLM call must have:

- a defined purpose;
- strict input schema;
- strict output schema;
- source context;
- model configuration;
- prompt version;
- validation;
- retry limit;
- stored generation record.

## Model routing

### Qwen3.7 Plus

Use for:

- concept extraction from difficult material;
- prerequisite proposals;
- learning-objective mapping;
- semantic preservation checks;
- dead-weight analysis;
- high-quality localized rewriting;
- schedule-change explanation.

### Qwen3.6 Flash

Use for:

- routine lesson generation;
- notes;
- homework;
- differentiated versions;
- assessment variations;
- adversarial shallow-answer attempts;
- weekly summaries.

### Qwen OCR

Use for:

- difficult scans;
- formula-heavy pages;
- diagram labels;
- tables;
- handwritten teacher notes;
- exam papers.

## Pipeline A — concept extraction

Input:

- source blocks from one chapter;
- subject;
- grade;
- language;
- neighboring chapter summaries.

Output:

- concepts;
- estimated minutes;
- difficulty;
- learning objectives;
- source block IDs;
- proposed prerequisite edges;
- confidence and rationale.

Validation:

- every concept has source blocks;
- no duplicate normalized names;
- duration is positive;
- edge endpoints exist;
- graph is cycle-checked;
- low-confidence edges require teacher approval.

## Pipeline B — lesson generation

Input:

- scheduled concepts;
- source blocks;
- objectives;
- session duration;
- student level;
- language;
- local context;
- teacher preferences.

Output:

- objectives;
- prior knowledge;
- timed lesson sequence;
- explanation;
- examples;
- activity;
- checks for understanding;
- differentiated variants;
- homework;
- source citations.

Validation:

- total minutes fit session;
- all objectives map to concepts;
- all factual content has source links;
- no untaught prerequisite is assumed;
- localized examples preserve the original learning objective.

## Pipeline C — authentic assessment

1. Select taught concepts.
2. Retrieve exact source blocks.
3. Generate question and rubric.
4. Ask a separate model call to answer using only general knowledge.
5. Score whether the question can be answered shallowly.
6. Rewrite when required.
7. Verify concept, difficulty, source grounding, and rubric.
8. Store question fingerprint to prevent repetition.
9. Require teacher approval before publishing.

Do not claim “AI-proof.”

Use:

“Resistant to shallow copy-paste AI answers.”

## Pipeline D — localization

Localization input must include:

- region;
- age;
- language;
- concept;
- original example;
- constraints that must remain unchanged.

Output includes:

- localized example;
- mapping explaining equivalence;
- vocabulary notes;
- risks or cultural assumptions.

A validator checks:

- same concept;
- similar difficulty;
- numerically valid values;
- no stereotyping;
- no unnecessary political or religious assumptions.

## Pipeline E — dead-weight analysis

The LLM may classify concepts as:

- protected prerequisite;
- exam-critical;
- compressible;
- optional enrichment;
- unsafe to remove.

OR-Tools decides whether and how to fit them.

The LLM never directly deletes content.

## Prompt storage

Prompts live under `packages/prompts/`.

Each prompt has:

- name;
- semantic version;
- input schema;
- output schema;
- owner;
- change log;
- evaluation dataset.
