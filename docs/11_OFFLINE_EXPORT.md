# Zero-Fi Offline Export

## Goal

Produce a self-contained course package that works without internet or server access.

## Export contents

```text
course-pack/
├── index.html
├── assets/
├── app/
│   ├── app.js
│   ├── styles.css
│   └── service-worker.js
├── data/
│   ├── course.json
│   ├── lessons.json
│   ├── assessments.json
│   ├── sources.json
│   └── search-index.json
├── lessons/
├── notes/
├── quizzes/
├── answer-keys/
├── printable/
└── MANIFEST.json
```

## Requirements

- no CDN;
- no remote fonts;
- no API calls;
- no online authentication;
- all assets use relative paths;
- static full-text search;
- print-safe black-and-white layouts;
- Urdu RTL support;
- checksums in manifest;
- export version and creation timestamp.

## HTML pack

The offline interface should provide:

- schedule;
- lesson navigation;
- concept search;
- notes;
- quiz viewing;
- source references;
- print buttons.

## PDF generation

Use HTML/CSS templates rendered through Paged.js or a headless browser.

Templates:

- lesson plan;
- teacher script;
- notes;
- worksheet;
- quiz paper;
- answer key;
- weekly summary.

## Low-toner mode

- no large backgrounds;
- no color-dependent charts;
- thin borders;
- grayscale-safe;
- configurable image exclusion;
- compact spacing.

## Security

Offline packs may contain student data.

Default export must exclude personally identifiable student records unless explicitly selected by an authorized user.
