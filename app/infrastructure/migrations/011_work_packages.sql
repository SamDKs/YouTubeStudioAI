CREATE TABLE work_packages (
 project_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL REFERENCES channels(channel_id),
 episode_id TEXT NOT NULL, language TEXT NOT NULL, title TEXT NOT NULL,
 import_relative_path TEXT NOT NULL UNIQUE, input_sha256 TEXT NOT NULL,
 canonical_manifest TEXT NOT NULL, warnings TEXT NOT NULL, current_revision_id TEXT,
 stage TEXT NOT NULL, imported_at TEXT NOT NULL,
 UNIQUE(channel_id,episode_id,language)
);
CREATE TABLE work_revisions (
 revision_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES work_packages(project_id),
 version INTEGER NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(project_id,version), UNIQUE(project_id,revision_id)
);
CREATE TABLE work_runs (
 job_id TEXT PRIMARY KEY REFERENCES jobs(job_id), project_id TEXT NOT NULL REFERENCES work_packages(project_id),
 revision_id TEXT NOT NULL, task TEXT NOT NULL, selection TEXT NOT NULL,
 cancel_requested INTEGER NOT NULL DEFAULT 0, result TEXT NOT NULL DEFAULT '{}',
 FOREIGN KEY(project_id,revision_id) REFERENCES work_revisions(project_id,revision_id)
);
CREATE TRIGGER work_revision_immutable_update BEFORE UPDATE ON work_revisions
BEGIN SELECT RAISE(ABORT,'immutable Work revision'); END;
CREATE TRIGGER work_revision_immutable_delete BEFORE DELETE ON work_revisions
BEGIN SELECT RAISE(ABORT,'immutable Work revision'); END;
CREATE TRIGGER work_revision_owner BEFORE UPDATE OF current_revision_id ON work_packages
WHEN NEW.current_revision_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM work_revisions WHERE project_id=NEW.project_id AND revision_id=NEW.current_revision_id)
BEGIN SELECT RAISE(ABORT,'Work revision belongs to another project'); END;
CREATE TRIGGER work_run_channel BEFORE INSERT ON work_runs
WHEN NOT EXISTS(SELECT 1 FROM jobs j JOIN work_packages p ON p.channel_id=j.channel_id WHERE j.job_id=NEW.job_id AND p.project_id=NEW.project_id)
BEGIN SELECT RAISE(ABORT,'Work job belongs to another channel'); END;
