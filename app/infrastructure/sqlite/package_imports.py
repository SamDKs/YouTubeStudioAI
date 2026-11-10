"""Persistencia aditiva del inventario e historial en SQLite existente."""

import json
from app.storage import utc_now


class PackageImports:
    def __init__(self, database):
        """Comparte la conexión/migraciones del estudio."""
        self.database = database

    def channels(self):
        """Devuelve identidades reales de canales activos."""
        with self.database.connection(read_only=True) as c:
            return [dict(r) for r in c.execute("SELECT channel_id,name FROM channels WHERE status='active' ORDER BY channel_id")]

    def list(self, channel=None):
        """Recupera importaciones, opcionalmente aisladas por canal."""
        with self.database.connection(read_only=True) as c:
            rows = c.execute('SELECT * FROM package_imports WHERE (? IS NULL OR channel_id=?) ORDER BY created_at DESC', (channel, channel))
            return [dict(r) | {'report': json.loads(r['report'])} for r in rows]

    def create(self, identifier, channel, episode, checksum, name):
        """Deduplica por canal/hash sin reemplazar entradas anteriores."""
        with self.database.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO package_imports VALUES (?,?,?,?,?,?,?,?,?)',
                      (identifier, channel, episode, checksum, name, 'IMPORTED', '{}', utc_now(), utc_now()))
            row = c.execute('SELECT import_id FROM package_imports WHERE channel_id=? AND zip_sha256=?', (channel, checksum)).fetchone()
            c.commit()
            return row[0]

    def update(self, identifier, state, report):
        """Guarda estado y evento juntos para recuperación e historial."""
        with self.database.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('UPDATE package_imports SET state=?,report=?,updated_at=?,episode_id=COALESCE(?,episode_id) WHERE import_id=?',
                      (state, json.dumps(report, ensure_ascii=False), utc_now(), report.get('episode_id'), identifier))
            c.execute('INSERT INTO package_import_events(import_id,state,detail,created_at) VALUES (?,?,?,?)',
                      (identifier, state, json.dumps(report, ensure_ascii=False), utc_now()))
            c.commit()

    def scripts(self, channel):
        """Ofrece únicamente versiones aprobadas en inglés del canal activo."""
        with self.database.connection(read_only=True) as c:
            return [dict(r) for r in c.execute("SELECT s.script_id,s.current_version_id,v.content FROM scripts s JOIN script_versions v ON v.script_version_id=s.current_version_id JOIN script_approvals a ON a.script_version_id=v.script_version_id AND a.content_hash=v.content_hash WHERE s.channel_id=? AND s.status='approved' AND s.language='en-US'", (channel,))]

    def events(self, identifier):
        """Lee transiciones en orden estable sin alterar el historial."""
        with self.database.connection(read_only=True) as c:
            return [dict(r) for r in c.execute('SELECT state,detail,created_at FROM package_import_events WHERE import_id=? ORDER BY event_id', (identifier,))]

    def jobs(self, channel=None):
        """Consulta trabajos vigentes del motor, excluyendo pilotos y derivados retirados."""
        with self.database.connection(read_only=True) as c:
            return [dict(r) for r in c.execute("SELECT j.job_id,j.channel_id,j.job_type,j.status,j.created_at,j.updated_at FROM jobs j JOIN work_runs w USING(job_id) WHERE (? IS NULL OR j.channel_id=?) AND COALESCE(json_extract(w.result,'$.retired_by_cleanup'),0)=0 ORDER BY j.created_at DESC LIMIT 100", (channel, channel))]
