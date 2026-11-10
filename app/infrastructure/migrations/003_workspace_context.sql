CREATE TABLE workspace_preferences (
 preference_key TEXT PRIMARY KEY, channel_id TEXT REFERENCES channels(channel_id), updated_at TEXT NOT NULL
);
CREATE TABLE channel_creation_intents (
 token TEXT PRIMARY KEY, channel_id TEXT NOT NULL UNIQUE, folder TEXT NOT NULL UNIQUE,
 registration TEXT NOT NULL, record_content TEXT NOT NULL, record_hash TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('prepared','published')), created_at TEXT NOT NULL
);
