CREATE TABLE episodes (
 episode_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(channel_id), idea_id TEXT NOT NULL,
 created_at TEXT NOT NULL, FOREIGN KEY(channel_id,idea_id) REFERENCES ideas(channel_id,idea_id), UNIQUE(channel_id,episode_id)
);
CREATE TABLE pilot_runs (
 job_id TEXT PRIMARY KEY REFERENCES jobs(job_id), episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
 mode TEXT NOT NULL CHECK(mode IN ('ai','local')), config TEXT NOT NULL,
 budget_microusd INTEGER NOT NULL CHECK(budget_microusd>=0), max_calls INTEGER NOT NULL,
 cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),
 content_approved INTEGER NOT NULL DEFAULT 0 CHECK(content_approved IN (0,1)),
 script_version_id TEXT REFERENCES script_versions(script_version_id), progress TEXT,
 created_at TEXT NOT NULL
);
CREATE TABLE artifacts (
 artifact_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, episode_id TEXT NOT NULL, job_id TEXT NOT NULL,
 logical_key TEXT NOT NULL, input_hash TEXT NOT NULL, revision INTEGER NOT NULL,
 relative_path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL CHECK(length(sha256)=64), size_bytes INTEGER NOT NULL CHECK(size_bytes>0),
 metadata TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(channel_id,job_id) REFERENCES jobs(channel_id,job_id),
 FOREIGN KEY(channel_id,episode_id) REFERENCES episodes(channel_id,episode_id), UNIQUE(job_id,logical_key,revision)
);
CREATE INDEX artifacts_lookup ON artifacts(job_id,logical_key,input_hash);
CREATE TABLE pilot_scenes (
 episode_id TEXT NOT NULL REFERENCES episodes(episode_id), job_id TEXT NOT NULL REFERENCES pilot_runs(job_id),
 variant TEXT NOT NULL CHECK(variant IN ('long','short')), scene_id TEXT NOT NULL, sequence INTEGER NOT NULL,
 narration TEXT NOT NULL, visual TEXT NOT NULL, image_prompt TEXT NOT NULL, expected_seconds REAL,
 final_seconds REAL, state TEXT NOT NULL DEFAULT 'pending', audio_artifact_id TEXT REFERENCES artifacts(artifact_id),
 image_artifact_id TEXT REFERENCES artifacts(artifact_id), version INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(job_id,variant,scene_id)
);
CREATE TABLE external_calls (
 call_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES pilot_runs(job_id), operation_key TEXT NOT NULL,
 input_hash TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('sent','received','uncertain','reconciled')),
 estimate_microusd INTEGER NOT NULL CHECK(estimate_microusd>=0), confirmed_microusd INTEGER,
 metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(job_id,operation_key)
);
CREATE INDEX external_calls_budget ON external_calls(created_at,status);
CREATE TABLE network_leases (
 call_id TEXT PRIMARY KEY REFERENCES external_calls(call_id), job_id TEXT NOT NULL REFERENCES jobs(job_id),
 worker_id TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TRIGGER immutable_artifact_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable artifact'); END;
CREATE TRIGGER immutable_artifact_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'immutable artifact'); END;
