CREATE TABLE episode_projects (
 episode_id TEXT PRIMARY KEY REFERENCES episodes(episode_id), channel_id TEXT NOT NULL REFERENCES channels(channel_id),
 code TEXT NOT NULL UNIQUE, title TEXT NOT NULL, slug TEXT NOT NULL,
 relative_root TEXT NOT NULL UNIQUE, archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
 created_at TEXT NOT NULL, UNIQUE(channel_id,episode_id)
);
CREATE TABLE artifact_locations (
 artifact_id TEXT PRIMARY KEY REFERENCES artifacts(artifact_id), relative_path TEXT NOT NULL UNIQUE,
 migrated_at TEXT NOT NULL
);
CREATE TABLE project_file_moves (
 episode_id TEXT PRIMARY KEY REFERENCES episodes(episode_id), manifest TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('prepared','committed')), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE archived_jobs (
 job_id TEXT PRIMARY KEY REFERENCES jobs(job_id), reason TEXT NOT NULL, archived_at TEXT NOT NULL
);
CREATE TABLE editorial_approvals (
 job_id TEXT PRIMARY KEY REFERENCES pilot_runs(job_id), preview_job_id TEXT REFERENCES jobs(job_id),
 script_version_id TEXT NOT NULL REFERENCES script_versions(script_version_id), voice_config_hash TEXT NOT NULL,
 budget_microusd INTEGER NOT NULL, approved_at TEXT NOT NULL
);
