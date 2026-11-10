-- Un worker 2B ya cargado en memoria no debe ejecutar el perfil editorial 2C.
CREATE TRIGGER editorial_worker_capability
BEFORE UPDATE OF status,worker_id ON jobs
WHEN NEW.status='running'
 AND EXISTS(SELECT 1 FROM pilot_runs p WHERE p.job_id=NEW.job_id
            AND json_extract(p.config,'$.profile') IN ('editorial-2c-1','voice-preview-2c-1'))
 AND (NEW.worker_id IS NULL OR NEW.worker_id NOT LIKE '2c:%')
BEGIN
 SELECT RAISE(ABORT,'Editorial 2C requires restarting the worker with the current application');
END;
