CREATE TABLE package_imports (
 import_id TEXT PRIMARY KEY,
 channel_id TEXT NOT NULL REFERENCES channels(channel_id),
 episode_id TEXT NOT NULL,
 zip_sha256 TEXT NOT NULL,
 original_name TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('IMPORTED','VALIDATING','NEEDS_SCRIPT','NEEDS_ASSETS','READY_FOR_PRODUCTION','FAILED')),
 report TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(channel_id, zip_sha256)
);
CREATE TABLE package_import_events (
 event_id INTEGER PRIMARY KEY,
 import_id TEXT NOT NULL REFERENCES package_imports(import_id),
 state TEXT NOT NULL,
 detail TEXT NOT NULL,
 created_at TEXT NOT NULL
);
