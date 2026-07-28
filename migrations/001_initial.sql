PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS courses (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  grade TEXT NOT NULL,
  subject TEXT NOT NULL,
  section TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'English',
  localization_region TEXT NOT NULL DEFAULT 'Karachi, Pakistan',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  title TEXT NOT NULL,
  document_type TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  file_path TEXT NOT NULL,
  parser_name TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  page_count INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(course_id, content_hash)
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  document_id TEXT REFERENCES documents(id),
  job_type TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  stage TEXT NOT NULL,
  progress REAL NOT NULL,
  message TEXT NOT NULL,
  error TEXT,
  trace_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_blocks (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  document_id TEXT NOT NULL REFERENCES documents(id),
  page_number INTEGER NOT NULL,
  block_index INTEGER NOT NULL,
  block_type TEXT NOT NULL,
  bbox_json TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  normalized_text TEXT NOT NULL,
  parser_name TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  confidence REAL NOT NULL,
  content_hash TEXT NOT NULL,
  quality_flags_json TEXT NOT NULL DEFAULT '[]',
  UNIQUE(document_id, page_number, block_index, content_hash)
);

CREATE TABLE IF NOT EXISTS concepts (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  title TEXT NOT NULL,
  normalized_title TEXT NOT NULL,
  description TEXT NOT NULL,
  difficulty INTEGER NOT NULL CHECK(difficulty BETWEEN 1 AND 5),
  estimated_minutes INTEGER NOT NULL CHECK(estimated_minutes > 0),
  required INTEGER NOT NULL,
  exam_weight REAL NOT NULL,
  source_block_ids_json TEXT NOT NULL,
  learning_objectives_json TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  locked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  UNIQUE(course_id, normalized_title)
);

CREATE TABLE IF NOT EXISTS concept_edges (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  source_concept_id TEXT NOT NULL REFERENCES concepts(id),
  target_concept_id TEXT NOT NULL REFERENCES concepts(id),
  relation_type TEXT NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT NOT NULL,
  teacher_approved INTEGER NOT NULL DEFAULT 0,
  rejected INTEGER NOT NULL DEFAULT 0,
  CHECK(source_concept_id <> target_concept_id),
  UNIQUE(course_id, source_concept_id, target_concept_id, relation_type)
);

CREATE TABLE IF NOT EXISTS schedule_versions (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  version_number INTEGER NOT NULL,
  parent_version_id TEXT,
  trigger_type TEXT NOT NULL,
  trigger_payload_json TEXT NOT NULL,
  solver_status TEXT NOT NULL,
  explanation TEXT NOT NULL,
  published_at TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(course_id, version_number)
);

CREATE TABLE IF NOT EXISTS schedule_entries (
  id TEXT PRIMARY KEY,
  version_id TEXT NOT NULL REFERENCES schedule_versions(id),
  session_date TEXT NOT NULL,
  session_minutes INTEGER NOT NULL,
  concept_id TEXT REFERENCES concepts(id),
  kind TEXT NOT NULL,
  locked INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'planned',
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS lessons (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  schedule_entry_id TEXT NOT NULL REFERENCES schedule_entries(id),
  content_json TEXT NOT NULL,
  source_block_ids_json TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model_name TEXT NOT NULL,
  teacher_edited INTEGER NOT NULL DEFAULT 0,
  locked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(course_id, schedule_entry_id)
);

CREATE TABLE IF NOT EXISTS assessments (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  title TEXT NOT NULL,
  content_json TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  approved INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  UNIQUE(course_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS attempts (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  assessment_id TEXT NOT NULL REFERENCES assessments(id),
  student_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  concept_id TEXT NOT NULL REFERENCES concepts(id),
  earned_points REAL NOT NULL,
  max_points REAL NOT NULL CHECK(max_points > 0),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mastery_records (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  concept_id TEXT NOT NULL REFERENCES concepts(id),
  weighted_score REAL NOT NULL,
  item_count INTEGER NOT NULL,
  confidence REAL NOT NULL,
  computed_at TEXT NOT NULL,
  UNIQUE(course_id, concept_id)
);

CREATE TABLE IF NOT EXISTS remediation_actions (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  concept_id TEXT NOT NULL REFERENCES concepts(id),
  duration_minutes INTEGER NOT NULL,
  evidence_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  approved_at TEXT
);

CREATE TABLE IF NOT EXISTS generation_records (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  purpose TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model_name TEXT NOT NULL,
  input_json TEXT NOT NULL,
  output_json TEXT NOT NULL,
  valid INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exports (
  id TEXT PRIMARY KEY,
  course_id TEXT NOT NULL REFERENCES courses(id),
  version_id TEXT REFERENCES schedule_versions(id),
  file_path TEXT NOT NULL,
  manifest_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
