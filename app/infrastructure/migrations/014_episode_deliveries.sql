CREATE TABLE episode_deliveries (
 delivery_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES work_packages(project_id),
 revision_id TEXT NOT NULL REFERENCES work_revisions(revision_id), configuration TEXT NOT NULL,
 request_hash TEXT NOT NULL UNIQUE, state TEXT NOT NULL, bundle_path TEXT, report TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE delivery_pieces (
 delivery_id TEXT NOT NULL REFERENCES episode_deliveries(delivery_id), slot TEXT NOT NULL,
 deliverable_id TEXT, job_id TEXT REFERENCES jobs(job_id), state TEXT NOT NULL, reason TEXT,
 PRIMARY KEY(delivery_id,slot)
);
CREATE TABLE short_candidates (
 candidate_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES work_packages(project_id),
 source TEXT NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('draft','approved')), actor TEXT, revision_id TEXT,
 created_at TEXT NOT NULL
);
