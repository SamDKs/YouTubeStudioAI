CREATE TABLE studio_settings (
 key TEXT PRIMARY KEY, value TEXT NOT NULL CHECK(json_valid(value))
);
INSERT INTO studio_settings VALUES ('paid_apis_enabled','false');
INSERT INTO studio_settings VALUES ('cost_profile','"local_free"');

-- También protege workers antiguos: no se reserva una llamada antes de HTTP.
CREATE TRIGGER zero_paid_api_calls BEFORE INSERT ON external_calls
WHEN COALESCE((SELECT value FROM studio_settings WHERE key='paid_apis_enabled'),'false')!='true'
BEGIN SELECT RAISE(ABORT,'ZERO PAID API CALLS: paid providers disabled'); END;

CREATE TABLE provider_selections (
 channel_id TEXT NOT NULL REFERENCES channels(channel_id), capability TEXT NOT NULL,
 primary_provider TEXT NOT NULL, alternative_provider TEXT, configuration TEXT NOT NULL CHECK(json_valid(configuration)),
 PRIMARY KEY(channel_id,capability)
);
CREATE TABLE resource_assets (
 asset_id TEXT PRIMARY KEY, channel_id TEXT REFERENCES channels(channel_id), kind TEXT NOT NULL,
 title TEXT NOT NULL, relative_path TEXT NOT NULL, sha256 TEXT NOT NULL,
 provenance TEXT NOT NULL CHECK(json_valid(provenance)), metadata TEXT NOT NULL CHECK(json_valid(metadata)),
 rights_status TEXT NOT NULL CHECK(rights_status IN ('unknown','allowed','restricted')),
 created_at TEXT NOT NULL
);
CREATE INDEX assets_channel_kind ON resource_assets(channel_id,kind);
CREATE TABLE edit_revisions (
 revision_id TEXT PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
 channel_id TEXT NOT NULL REFERENCES channels(channel_id), version INTEGER NOT NULL,
 content TEXT NOT NULL CHECK(json_valid(content)), content_hash TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(episode_id,version)
);
CREATE TRIGGER edit_revisions_immutable BEFORE UPDATE ON edit_revisions
BEGIN SELECT RAISE(ABORT,'Edit revisions are immutable'); END;
CREATE TABLE edit_approvals (
 revision_id TEXT PRIMARY KEY REFERENCES edit_revisions(revision_id), approved_at TEXT NOT NULL
);
CREATE TABLE scheduled_items (
 schedule_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(channel_id),
 idea_id TEXT NOT NULL REFERENCES ideas(idea_id), episode_id TEXT REFERENCES episodes(episode_id),
 title TEXT NOT NULL, deliverable TEXT NOT NULL, scheduled_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('planned','ready','queued','completed','canceled')),
 job_id TEXT REFERENCES jobs(job_id), version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE INDEX schedule_due ON scheduled_items(status,scheduled_at);
CREATE TABLE youtube_accounts (
 channel_id TEXT PRIMARY KEY REFERENCES channels(channel_id), youtube_channel_id TEXT NOT NULL,
 credential_reference TEXT NOT NULL, verified_at TEXT
);
CREATE TABLE metric_snapshots (
 snapshot_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(channel_id),
 recorded_at TEXT NOT NULL, source TEXT NOT NULL, metrics TEXT NOT NULL CHECK(json_valid(metrics))
);
