"""Work projects reuse the existing jobs, steps, events, checkpoints and SQLite."""

from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import json
import sqlite3
from uuid import uuid4

from app.storage import Database,utc_now
from app.domain.package_errors import Canceled,LeaseLost,StorageError,StudioError,Paused
from app.engine.domain.package import Lease,Task
from app.engine.domain.serialization import digest,encoded


class SqliteWorkStore:
    def __init__(self,database: Database):self.database=database

    @contextmanager
    def write(self):
        with self.database.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            try:yield c;c.commit()
            except BaseException:c.rollback();raise

    def channels(self) -> tuple[dict,...]:
        with self.database.connection(read_only=True) as c:
            return tuple(dict(r) for r in c.execute("SELECT channel_id,name,primary_language,status FROM channels ORDER BY channel_id"))

    def add_package(self,project_id: str,manifest: dict,relative: str,checksum: str,warnings: tuple[str,...],voice: dict) -> None:
        content=encoded({'manifest':manifest,'voice':voice}).decode();revision=str(uuid4());now=utc_now()
        with self.write() as c:
            if not c.execute("SELECT 1 FROM channels WHERE channel_id=? AND status='active'",(manifest['channel_id'],)).fetchone():raise StudioError('El canal del paquete no existe o está archivado. Configura el canal antes de importar.')
            if c.execute('SELECT 1 FROM work_packages WHERE channel_id=? AND episode_id=? AND language=?',(manifest['channel_id'],manifest['episode_id'],manifest['language'])).fetchone():raise StudioError('Ese episodio/idioma ya está importado. No se sobrescribió; usa sus revisiones o asigna otro identificador en Work.')
            c.execute('INSERT INTO work_packages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(project_id,manifest['channel_id'],manifest['episode_id'],manifest['language'],manifest['title'],relative,checksum,encoded(manifest).decode(),encoded(warnings).decode(),None,'imported',now))
            c.execute('INSERT INTO work_revisions VALUES (?,?,?,?,?,?)',(revision,project_id,1,content,digest(content.encode()),now))
            c.execute("UPDATE work_packages SET current_revision_id=?,stage='validated' WHERE project_id=?",(revision,project_id))
            for stage in ('imported','validated'):
                c.execute('INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)',(str(uuid4()),manifest['channel_id'],project_id,'work_'+stage,'local_owner',encoded({'project_id':project_id,'input_sha256':checksum}).decode(),now))

    def projects(self) -> tuple[dict,...]:
        with self.database.connection(read_only=True) as c:
            return tuple(dict(r) for r in c.execute('SELECT project_id,channel_id,episode_id,title,language,stage,imported_at FROM work_packages ORDER BY imported_at DESC'))

    def project(self,project_id: str) -> dict:
        with self.database.connection(read_only=True) as c:
            row=c.execute('SELECT * FROM work_packages WHERE project_id=?',(project_id,)).fetchone()
            if not row:raise StudioError('El proyecto no existe.')
            revision=c.execute('SELECT * FROM work_revisions WHERE revision_id=?',(row['current_revision_id'],)).fetchone()
        if digest(revision['content'].encode())!=revision['content_hash']:raise StorageError('La revisión no supera la comprobación de integridad.')
        return dict(row)|{'revision':dict(revision)|json.loads(revision['content']),'warnings':json.loads(row['warnings'])}

    def save_revision(self,project_id: str,manifest: dict,voice: dict,expected: int,timing_overrides: dict | None = None) -> dict:
        content=encoded({'manifest':manifest,'voice':voice,'timing_overrides':timing_overrides or {}}).decode()
        with self.write() as c:
            old=c.execute('SELECT r.* FROM work_packages p JOIN work_revisions r ON p.current_revision_id=r.revision_id WHERE p.project_id=?',(project_id,)).fetchone()
            if not old or old['version']!=expected:raise StudioError('El proyecto cambió en otra sesión. Recarga antes de guardar.')
            if old['content']==content:return self.project(project_id)['revision']
            revision=str(uuid4());now=utc_now()
            c.execute('INSERT INTO work_revisions VALUES (?,?,?,?,?,?)',(revision,project_id,expected+1,content,digest(content.encode()),now))
            c.execute("UPDATE work_packages SET current_revision_id=?,stage='validated' WHERE project_id=?",(revision,project_id))
        return self.project(project_id)['revision']

    def enqueue(self,project_id: str,revision_id: str,task: Task,selection: dict,steps: tuple[str,...],configuration: dict) -> str:
        snapshot={'project_id':project_id,'revision_id':revision_id,'task':task.value,'selection':selection,'configuration':configuration}
        key=digest(encoded(snapshot));pipeline='work-1-'+digest(encoded(steps))[:20]
        with self.write() as c:
            old=c.execute('SELECT job_id FROM jobs WHERE idempotency_key=?',(key,)).fetchone()
            if old:return old[0]
            project=c.execute('SELECT * FROM work_packages WHERE project_id=?',(project_id,)).fetchone()
            if not project or project['current_revision_id']!=revision_id:raise StudioError('La revisión cambió; revisa otra vez antes de producir.')
            job=str(uuid4());now=utc_now()
            spec=encoded({'steps':steps}).decode()
            c.execute('INSERT OR IGNORE INTO pipeline_versions VALUES (?,?,?,?)',(pipeline,spec,digest(spec.encode()),now))
            c.execute('INSERT INTO jobs (job_id,channel_id,job_type,status,idempotency_key,created_at,updated_at,configuration_snapshot,pipeline_version) VALUES (?,?,?,?,?,?,?,?,?)',(job,project['channel_id'],'work_package','queued',key,now,now,encoded(snapshot).decode(),pipeline))
            for index,stage in enumerate(steps):
                c.execute('INSERT INTO job_steps (step_id,job_id,step_type,sequence,status,dependencies,capability,retry_policy,cancel_policy) VALUES (?,?,?,?,?,?,?,?,?)',(str(uuid4()),job,stage,index,'pending','[]' if index==0 else encoded([steps[index-1]]).decode(),'implemented','verified_checkpoint_only','cooperative'))
            c.execute('INSERT INTO work_runs (job_id,project_id,revision_id,task,selection) VALUES (?,?,?,?,?)',(job,project_id,revision_id,task.value,encoded(selection).decode()))
            self._event(c,job,'queued','Trabajo local de paquete en cola. No consume APIs.',{})
        return job

    @staticmethod
    def _event(c,job: str,kind: str,message: str,payload: dict):
        sequence=c.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM job_events WHERE job_id=?',(job,)).fetchone()[0]
        c.execute('INSERT INTO job_events VALUES (?,?,?,?,?,?,?,?)',(str(uuid4()),job,None,sequence,kind,message,encoded(payload).decode(),utc_now()))

    @staticmethod
    def _guard(c,lease: Lease,allow_cancel: bool=False):
        row=c.execute('SELECT j.*,w.cancel_requested FROM jobs j JOIN work_runs w USING(job_id) WHERE job_id=?',(lease.job_id,)).fetchone()
        if not row or row['status']!='running' or row['worker_id']!=lease.owner or row['fencing_token']!=lease.token or not row['lease_expires_at'] or row['lease_expires_at']<=utc_now():raise LeaseLost('El worker perdió su lease.')
        if row['cancel_requested'] and not allow_cancel:raise Canceled('Cancelación solicitada.')

    # Recupera leases vencidos y toma un único trabajo permitido.
    def claim(self,owner: str,job_id: str | None=None) -> Lease | None:
        with self.write() as c:
            abandoned=c.execute("SELECT j.job_id FROM jobs j JOIN work_runs w USING(job_id) WHERE j.status='running' AND j.lease_expires_at<=?",(utc_now(),)).fetchall()
            for row in abandoned:
                c.execute("UPDATE jobs SET status=CASE WHEN (SELECT cancel_requested FROM work_runs WHERE work_runs.job_id=jobs.job_id)=1 THEN 'canceled' WHEN (SELECT pause_requested FROM work_runs WHERE work_runs.job_id=jobs.job_id)=1 THEN 'paused' ELSE 'queued' END,worker_id=NULL,lease_expires_at=NULL,version=version+1 WHERE job_id=?",(row['job_id'],))
                self._event(c,row['job_id'],'recovered','Lease vencido; se verificarán cachés antes de reanudar.',{})
            if c.execute("SELECT 1 FROM jobs j JOIN work_runs w USING(job_id) WHERE j.status='running' LIMIT 1").fetchone():
                return None
            row=c.execute("SELECT j.* FROM jobs j JOIN work_runs w USING(job_id) WHERE j.status='queued' AND w.cancel_requested=0 AND w.pause_requested=0 AND (? IS NULL OR j.job_id=?) ORDER BY j.created_at LIMIT 1",(job_id,job_id)).fetchone()
            if not row:return None
            lease=Lease(row['job_id'],'work:'+owner,row['fencing_token']+1)
            expiry=(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat()
            c.execute("UPDATE jobs SET status='running',worker_id=?,fencing_token=?,heartbeat_at=?,lease_expires_at=?,attempt_count=attempt_count+1,started_at=COALESCE(started_at,?),updated_at=?,version=version+1 WHERE job_id=?",(lease.owner,lease.token,utc_now(),expiry,utc_now(),utc_now(),lease.job_id))
            self._event(c,lease.job_id,'claimed','Worker tomó el paquete editorial.',{})
            return lease

    def guard(self,lease: Lease):
        with self.database.connection(read_only=True) as c:self._guard(c,lease)

    def heartbeat(self,lease: Lease):
        with self.write() as c:
            self._guard(c,lease,True)
            c.execute('UPDATE jobs SET heartbeat_at=?,lease_expires_at=? WHERE job_id=?',(utc_now(),(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat(),lease.job_id))

    def run_context(self,lease: Lease) -> dict:
        with self.database.connection(read_only=True) as c:
            self._guard(c,lease)
            row=c.execute('SELECT j.configuration_snapshot,r.content,r.content_hash,p.import_relative_path FROM jobs j JOIN work_runs w USING(job_id) JOIN work_revisions r ON r.revision_id=w.revision_id JOIN work_packages p ON p.project_id=w.project_id WHERE j.job_id=?',(lease.job_id,)).fetchone()
        if digest(row['content'].encode())!=row['content_hash']:raise StorageError('La revisión del trabajo cambió.')
        return json.loads(row['configuration_snapshot'])|json.loads(row['content'])|{'import_relative_path':row['import_relative_path']}

    def start(self,lease: Lease,stage: str):
        with self.write() as c:
            self._guard(c,lease)
            step=c.execute('SELECT * FROM job_steps WHERE job_id=? AND step_type=?',(lease.job_id,stage)).fetchone()
            if not step:raise StudioError('Etapa ajena al pipeline.')
            c.execute("UPDATE job_steps SET status='running',attempt_count=attempt_count+1,started_at=?,error_details=NULL WHERE step_id=?",(utc_now(),step['step_id']))
            c.execute('UPDATE jobs SET current_step_id=?,updated_at=? WHERE job_id=?',(step['step_id'],utc_now(),lease.job_id))
            self._event(c,lease.job_id,'stage',stage,{})

    def checkpoint(self,lease: Lease,stage: str,relative: str,sha256: str):
        with self.write() as c:
            self._guard(c,lease)
            step=c.execute('SELECT * FROM job_steps WHERE job_id=? AND step_type=?',(lease.job_id,stage)).fetchone()
            reference='work-file:'+relative
            c.execute("UPDATE job_steps SET status='completed',result_reference=?,finished_at=? WHERE step_id=?",(reference,utc_now(),step['step_id']))
            version=c.execute('SELECT COALESCE(MAX(checkpoint_version),0)+1 FROM job_checkpoints WHERE step_id=?',(step['step_id'],)).fetchone()[0]
            c.execute('INSERT INTO job_checkpoints VALUES (?,?,?,?,?,?,?)',(str(uuid4()),lease.job_id,step['step_id'],version,reference,sha256,utc_now()))
            self._event(c,lease.job_id,'checkpoint','Resultado real verificado y conservado.',{'stage':stage,'sha256':sha256})

    # Confirma el estado del trabajo y conserva resultados y diagnóstico.
    def finish(self,lease: Lease,status: str,result: dict,message: str):
        if status not in {'completed','failed','canceled','waiting_review','queued','paused'}:raise StudioError('Estado de terminación inválido.')
        with self.write() as c:
            self._guard(c,lease,True)
            c.execute('UPDATE jobs SET status=?,last_error=?,finished_at=?,worker_id=NULL,lease_expires_at=NULL,updated_at=?,version=version+1 WHERE job_id=?',(status,message if status in {'failed','waiting_review'} else None,utc_now() if status not in {'queued','paused'} else None,utc_now(),lease.job_id))
            c.execute('UPDATE work_runs SET result=? WHERE job_id=?',(encoded(result).decode(),lease.job_id))
            if status!='completed':c.execute("UPDATE job_steps SET status=?,error_details=? WHERE job_id=? AND status='running'",('interrupted' if status=='queued' else status,message,lease.job_id))
            if status=='completed':
                row=c.execute('SELECT * FROM work_runs WHERE job_id=?',(lease.job_id,)).fetchone()
                stage={'narrate':'narration','synchronize':'synchronization','preview':'preview','export':'export','produce_long':'export'}[row['task']]
                c.execute('UPDATE work_packages SET stage=? WHERE project_id=? AND current_revision_id=?',(stage,row['project_id'],row['revision_id']))
            self._event(c,lease.job_id,status,message,result)

    def progress(self,lease: Lease,payload: dict):
        with self.write() as c:self._guard(c,lease);self._event(c,lease.job_id,'progress','FFmpeg informó progreso real.',payload)

    def jobs(self,project_id: str) -> tuple[dict,...]:
        with self.database.connection(read_only=True) as c:
            return tuple(dict(r)|{'result':json.loads(r['result'])} for r in c.execute("SELECT j.job_id,j.status,j.created_at,j.last_error,j.attempt_count,w.task,w.revision_id,w.result FROM jobs j JOIN work_runs w USING(job_id) WHERE w.project_id=? AND COALESCE(json_extract(w.result,'$.retired_by_cleanup'),0)=0 ORDER BY j.created_at DESC",(project_id,)))

    def run_project_id(self,job_id: str) -> str:
        with self.database.connection(read_only=True) as c:
            row=c.execute('SELECT project_id FROM work_runs WHERE job_id=?',(job_id,)).fetchone()
        if not row:raise StudioError('Trabajo no perteneciente al motor de paquetes.')
        return row[0]

    def events(self,job_id: str) -> tuple[dict,...]:
        with self.database.connection(read_only=True) as c:
            return tuple(dict(r) for r in c.execute('SELECT event_type,human_readable_message,event_payload,created_at FROM job_events WHERE job_id=? ORDER BY sequence',(job_id,)))

    def checkpoints(self,job_id: str) -> tuple[dict,...]:
        with self.database.connection(read_only=True) as c:
            return tuple(dict(r) for r in c.execute('SELECT s.step_type,k.result_reference,k.integrity_hash FROM job_checkpoints k JOIN job_steps s USING(step_id) WHERE k.job_id=? ORDER BY k.created_at',(job_id,)))


    def cancel(self,job_id: str):
        with self.write() as c:
            row=c.execute('SELECT j.status FROM jobs j JOIN work_runs w USING(job_id) WHERE job_id=?',(job_id,)).fetchone()
            if not row or row['status'] not in {'queued','running','paused'}:raise StudioError('El trabajo ya terminó.')
            c.execute('UPDATE work_runs SET cancel_requested=1 WHERE job_id=?',(job_id,))
            if row['status'] in {'queued','paused'}:c.execute("UPDATE jobs SET status='canceled',finished_at=? WHERE job_id=?",(utc_now(),job_id))
            self._event(c,job_id,'cancel_requested','Cancelación solicitada; se conservan resultados verificados.',{})

    # Reencola un trabajo detenido sin eliminar sus checkpoints.
    def retry(self,job_id: str):
        with self.write() as c:
            row=c.execute('SELECT j.* FROM jobs j JOIN work_runs w USING(job_id) WHERE job_id=?',(job_id,)).fetchone()
            if not row or row['status'] not in {'failed','waiting_review','interrupted','canceled'}:raise StudioError('Solo se reintentan trabajos detenidos.')
            if row['attempt_count']>=5:raise StudioError('Cinco intentos agotados; revisa las entradas antes de otra producción.')
            c.execute('UPDATE work_runs SET cancel_requested=0,pause_requested=0 WHERE job_id=?',(job_id,))
            c.execute("UPDATE jobs SET status='queued',last_error=NULL,version=version+1 WHERE job_id=?",(job_id,))
            self._event(c,job_id,'retry','Reintento explícito; se verificará cada resultado reutilizado.',{})


    def pause(self, job_id: str):
        """Solicita pausa al acabar la etapa actual; una cola se pausa inmediatamente."""
        with self.write() as c:
            row=c.execute('SELECT j.status FROM jobs j JOIN work_runs w USING(job_id) WHERE job_id=?',(job_id,)).fetchone()
            if not row or row['status'] not in {'running','queued'}:raise StudioError('El trabajo no permite pausa ahora.')
            c.execute('UPDATE work_runs SET pause_requested=1 WHERE job_id=?',(job_id,))
            if row['status']=='queued':c.execute("UPDATE jobs SET status='paused' WHERE job_id=?",(job_id,))
            self._event(c,job_id,'pause_requested','Pausa solicitada para el siguiente checkpoint seguro.',{})

    def pause_boundary(self, lease):
        """Interrumpe solo después de publicar un checkpoint íntegro."""
        with self.database.connection(read_only=True) as c:
            self._guard(c,lease)
            row=c.execute('SELECT pause_requested FROM work_runs WHERE job_id=?',(lease.job_id,)).fetchone()
            if row[0]:raise Paused('Pausado en checkpoint; las etapas verificadas se conservan.')

    def resume(self, job_id):
        """Reencola explícitamente una pausa conservando los hashes y la revisión."""
        with self.write() as c:
            row=c.execute('SELECT j.status FROM jobs j JOIN work_runs w USING(job_id) WHERE job_id=?',(job_id,)).fetchone()
            if not row or row[0]!='paused':raise StudioError('El trabajo no está pausado.')
            c.execute('UPDATE work_runs SET pause_requested=0 WHERE job_id=?',(job_id,))
            c.execute("UPDATE jobs SET status='queued',finished_at=NULL WHERE job_id=?",(job_id,))
            self._event(c,job_id,'resumed','Reanudación desde resultados verificados por hash.',{})

    def steps(self, job_id):
        """Expone estados de etapas persistidos para seguimiento real."""
        with self.database.connection(read_only=True) as c:
            return tuple(dict(r) for r in c.execute('SELECT step_type,status,attempt_count,error_details FROM job_steps WHERE job_id=? ORDER BY sequence',(job_id,)))


    def channel_voice(self,channel_id):
        """Recupera la preferencia explícita de voz del canal, sin cambiar revisiones."""
        with self.database.connection(read_only=True) as c:
            row=c.execute('SELECT value FROM app_metadata WHERE key=?',('voice:'+channel_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def set_channel_voice(self,channel_id,voice):
        """Guarda una preferencia para nuevos paquetes del canal real."""
        with self.write() as c:
            if not c.execute('SELECT 1 FROM channels WHERE channel_id=?',(channel_id,)).fetchone():raise StudioError('Canal inexistente.')
            c.execute('INSERT INTO app_metadata(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('voice:'+channel_id,encoded(voice).decode()))

    def llm_config(self,channel):
        """Devuelve únicamente un LLM local elegido explícitamente, sin leer secretos."""
        with self.database.connection(read_only=True) as c:
            row=c.execute("SELECT configuration FROM provider_selections WHERE channel_id=? AND capability='script' AND primary_provider='llama_cpp'",(channel,)).fetchone()
            value=json.loads(row[0]) if row else {}
            return {k:value[k] for k in ('model','base_url') if k in value} if value.get('model') else None
