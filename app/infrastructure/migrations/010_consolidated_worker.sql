-- Older in-memory workers must not interpret new multilingual/profile snapshots.
CREATE TRIGGER consolidated_worker_capability
BEFORE UPDATE OF status,worker_id ON jobs
WHEN NEW.status='running'
AND EXISTS(SELECT 1 FROM pilot_runs p WHERE p.job_id=NEW.job_id
 AND json_extract(p.config,'$.profile')='local-studio-1'
 AND json_extract(p.config,'$.production_profile') IS NOT NULL)
AND (NEW.worker_id IS NULL OR NEW.worker_id NOT LIKE 'studio:v2:%')
BEGIN SELECT RAISE(ABORT,'Restart worker: consolidated production requires studio:v2 capability'); END;
