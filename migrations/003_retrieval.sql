CREATE TABLE IF NOT EXISTS retrieval_indexes (
  course_id TEXT PRIMARY KEY REFERENCES courses(id),
  engine TEXT NOT NULL,
  source_snapshot_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  details_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
