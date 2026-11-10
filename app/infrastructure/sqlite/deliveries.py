"""Entregas, piezas y guiones revisados en la misma SQLite del estudio."""

import json
from uuid import uuid4
from app.storage import utc_now
from app.engine.domain.serialization import encoded,digest


class DeliveryStore:
    def __init__(self,database):
        """Comparte conexiones cortas y migraciones existentes."""
        self.database=database

    def create(self,project,revision,configuration):
        """Deduplica solicitudes de entrega por revisión y configuración."""
        key=digest(encoded([project,revision,configuration]));identifier=str(uuid4());now=utc_now()
        with self.database.connection() as c:
            c.execute('INSERT OR IGNORE INTO episode_deliveries VALUES (?,?,?,?,?,?,?,?,?,?)',
                      (identifier,project,revision,encoded(configuration).decode(),key,'PREPARING',None,'{}',now,now))
            row=c.execute('SELECT delivery_id FROM episode_deliveries WHERE request_hash=?',(key,)).fetchone()
            return row[0]

    def piece(self,delivery,slot,deliverable,job,state,reason=None):
        """Actualiza solo la pieza afectada sin tocar los otros canales."""
        with self.database.connection() as c:
            c.execute('INSERT INTO delivery_pieces VALUES (?,?,?,?,?,?) ON CONFLICT(delivery_id,slot) DO UPDATE SET deliverable_id=excluded.deliverable_id,job_id=excluded.job_id,state=excluded.state,reason=excluded.reason',
                      (delivery,slot,deliverable,job,state,reason))

    def list(self,project=None):
        """Recupera entregas y piezas para paneles, workers y recuperación."""
        with self.database.connection(read_only=True) as c:
            rows=[dict(r) for r in c.execute('SELECT * FROM episode_deliveries WHERE (? IS NULL OR project_id=?) ORDER BY created_at DESC',(project,project))]
            for row in rows:
                row['pieces']=[dict(r) for r in c.execute('SELECT * FROM delivery_pieces WHERE delivery_id=? ORDER BY slot',(row['delivery_id'],))]
                row['configuration']=json.loads(row['configuration']);row['report']=json.loads(row['report'])
            return rows

    def save_report(self,delivery,state,report,bundle=None):
        """Publica estado agregado y ruta del paquete sin afirmar aprobación editorial."""
        with self.database.connection() as c:
            c.execute('UPDATE episode_deliveries SET state=?,report=?,bundle_path=?,updated_at=? WHERE delivery_id=?',
                      (state,encoded(report).decode(),bundle,utc_now(),delivery))

    def candidate(self,project,source,content,state='draft',actor=None,revision=None):
        """Conserva autoría y aprobación explícita del guion/timeline adicional."""
        identifier=str(uuid4());text=encoded(content).decode()
        with self.database.connection() as c:
            old=c.execute('SELECT candidate_id FROM short_candidates WHERE project_id=? AND source=? AND content_hash=? AND state=?',(project,source,digest(text.encode()),state)).fetchone()
            if old:return old[0]
            c.execute('INSERT INTO short_candidates VALUES (?,?,?,?,?,?,?,?,?)',(identifier,project,source,text,digest(text.encode()),state,actor,revision,utc_now()))
        return identifier

    def candidates(self,project):
        """Lista borradores generados o aprobados únicamente del episodio actual."""
        with self.database.connection(read_only=True) as c:
            return [dict(r)|{'content':json.loads(r['content'])} for r in c.execute('SELECT * FROM short_candidates WHERE project_id=? ORDER BY created_at DESC',(project,))]

    def approval(self,delivery):
        """Lee una aprobación local vinculada al contenido exacto de la entrega."""
        with self.database.connection(read_only=True) as c:
            row=c.execute('SELECT value FROM app_metadata WHERE key=?',('delivery_approval:'+delivery,)).fetchone()
            return json.loads(row[0]) if row else None

    def approve(self,delivery,actor,note):
        """Registra una decisión humana; no inicia subida ni programación."""
        with self.database.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT report FROM episode_deliveries WHERE delivery_id=?',(delivery,)).fetchone()
            report=json.loads(row[0]) if row else {}
            if not report.get('all_four_rendered_and_qa_passed') or report.get('approval_blockers') or not report.get('bundle_path_verified'):
                raise ValueError('Hay verificaciones o piezas pendientes; no se puede aprobar.')
            value={'actor':actor,'note':note,'approved_at':utc_now(),'fingerprint':report['base_fingerprint']}
            c.execute('INSERT INTO app_metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('delivery_approval:'+delivery,encoded(value).decode()))
            c.commit()

    def mark_candidate_approved(self,candidate_id,project,revision):
        """Cierra el borrador original después de guardar su revisión aprobada."""
        with self.database.connection() as c:
            c.execute("UPDATE short_candidates SET state='approved',actor='local_owner',revision_id=? WHERE candidate_id=? AND project_id=?",(revision,candidate_id,project))

    def auto_enabled(self,channel):
        """Lee la preferencia explícita de automatización del canal."""
        with self.database.connection(read_only=True) as c:
            row=c.execute('SELECT value FROM app_metadata WHERE key=?',('auto_production:'+channel,)).fetchone()
            return bool(row and row[0]=='true')

    def set_auto(self,channel,enabled):
        """Persiste la opción por canal sin modificar sus episodios o voces."""
        with self.database.connection() as c:
            if not c.execute('SELECT 1 FROM channels WHERE channel_id=?',(channel,)).fetchone():raise ValueError('Canal inexistente.')
            c.execute('INSERT INTO app_metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('auto_production:'+channel,'true' if enabled else 'false'))
