CREATE TABLE pipeline_versions (
 pipeline_version TEXT PRIMARY KEY, specification TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE production_batches (
 batch_id TEXT PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('prepared','running','waiting_review','completed','partial','attention','canceled')),
 requested_at TEXT NOT NULL, requested_by TEXT NOT NULL, execution_policy TEXT NOT NULL,
 configuration_snapshot_version TEXT NOT NULL
);
CREATE TABLE operation_requests (
 request_key TEXT PRIMARY KEY, request_hash TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE jobs (
 job_id TEXT PRIMARY KEY, batch_id TEXT REFERENCES production_batches(batch_id),
 channel_id TEXT NOT NULL REFERENCES channels(channel_id), idea_id TEXT, script_id TEXT,
 job_type TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('prepared','queued','running','waiting_review','completed','failed','canceled','paused','interrupted')),
 current_step_id TEXT, idempotency_key TEXT NOT NULL UNIQUE, attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count>=0),
 created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, updated_at TEXT NOT NULL, last_error TEXT,
 configuration_snapshot TEXT NOT NULL, pipeline_version TEXT NOT NULL REFERENCES pipeline_versions(pipeline_version),
 heartbeat_at TEXT, lease_expires_at TEXT, worker_id TEXT, fencing_token INTEGER NOT NULL DEFAULT 0,
 version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
 UNIQUE(batch_id,channel_id), UNIQUE(channel_id,job_id),
 FOREIGN KEY(channel_id,idea_id) REFERENCES ideas(channel_id,idea_id),
 FOREIGN KEY(channel_id,script_id) REFERENCES scripts(channel_id,script_id),
 FOREIGN KEY(job_id,current_step_id) REFERENCES job_steps(job_id,step_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE job_steps (
 step_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(job_id), step_type TEXT NOT NULL,
 sequence INTEGER NOT NULL CHECK(sequence>=0), status TEXT NOT NULL CHECK(status IN ('pending','running','waiting_review','completed','failed','canceled','paused','interrupted')),
 attempt_count INTEGER NOT NULL DEFAULT 0 CHECK(attempt_count>=0), started_at TEXT, finished_at TEXT,
 result_reference TEXT, error_details TEXT, dependencies TEXT NOT NULL, capability TEXT NOT NULL,
 retry_policy TEXT NOT NULL, cancel_policy TEXT NOT NULL,
 UNIQUE(job_id,sequence), UNIQUE(job_id,step_type), UNIQUE(job_id,step_id)
);
CREATE TABLE job_events (
 event_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(job_id), step_id TEXT,
 sequence INTEGER NOT NULL, event_type TEXT NOT NULL, human_readable_message TEXT NOT NULL,
 event_payload TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(job_id,sequence),
 FOREIGN KEY(job_id,step_id) REFERENCES job_steps(job_id,step_id)
);
CREATE TABLE job_checkpoints (
 checkpoint_id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(job_id), step_id TEXT NOT NULL,
 checkpoint_version INTEGER NOT NULL CHECK(checkpoint_version>0), result_reference TEXT NOT NULL,
 integrity_hash TEXT NOT NULL CHECK(length(integrity_hash)=64), created_at TEXT NOT NULL,
 UNIQUE(step_id,checkpoint_version), FOREIGN KEY(job_id,step_id) REFERENCES job_steps(job_id,step_id)
);
CREATE INDEX jobs_channel_status ON jobs(channel_id,status,created_at);
CREATE INDEX jobs_batch ON jobs(batch_id);
CREATE INDEX events_job ON job_events(job_id,sequence);
CREATE INDEX checkpoints_job ON job_checkpoints(job_id,step_id);
CREATE TRIGGER checkpoint_completed BEFORE INSERT ON job_checkpoints
 WHEN NOT EXISTS(SELECT 1 FROM job_steps WHERE step_id=NEW.step_id AND job_id=NEW.job_id AND status='completed' AND result_reference=NEW.result_reference)
 BEGIN SELECT RAISE(ABORT,'checkpoint requires completed result'); END;
CREATE TRIGGER job_script_idea_insert BEFORE INSERT ON jobs
 WHEN NEW.script_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM scripts WHERE script_id=NEW.script_id AND channel_id=NEW.channel_id AND idea_id=NEW.idea_id)
 BEGIN SELECT RAISE(ABORT,'script must belong to selected idea'); END;
CREATE TRIGGER job_script_idea_update BEFORE UPDATE OF script_id,idea_id,channel_id ON jobs
 WHEN NEW.script_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM scripts WHERE script_id=NEW.script_id AND channel_id=NEW.channel_id AND idea_id=NEW.idea_id)
 BEGIN SELECT RAISE(ABORT,'script must belong to selected idea'); END;
CREATE TRIGGER immutable_job_event_update BEFORE UPDATE ON job_events BEGIN SELECT RAISE(ABORT,'immutable job event'); END;
CREATE TRIGGER immutable_job_event_delete BEFORE DELETE ON job_events BEGIN SELECT RAISE(ABORT,'immutable job event'); END;
CREATE TRIGGER immutable_checkpoint_update BEFORE UPDATE ON job_checkpoints BEGIN SELECT RAISE(ABORT,'immutable checkpoint'); END;
CREATE TRIGGER immutable_checkpoint_delete BEFORE DELETE ON job_checkpoints BEGIN SELECT RAISE(ABORT,'immutable checkpoint'); END;
CREATE TRIGGER immutable_pipeline_update BEFORE UPDATE ON pipeline_versions BEGIN SELECT RAISE(ABORT,'immutable pipeline'); END;
CREATE TRIGGER immutable_pipeline_delete BEFORE DELETE ON pipeline_versions BEGIN SELECT RAISE(ABORT,'immutable pipeline'); END;
