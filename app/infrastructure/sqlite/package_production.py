"""Relaciones persistentes entre importaciones de fase 1 y paquetes del motor."""


class ProductionLinks:
    def __init__(self,database):
        """Comparte la base migrada del estudio."""
        self.database=database

    def find(self,import_id):
        """Recupera la vinculación sin crear revisiones ni jobs."""
        with self.database.connection(read_only=True) as c:
            row=c.execute('SELECT project_id FROM package_production_links WHERE import_id=?',(import_id,)).fetchone()
            return row[0] if row else None

    def save(self,import_id,project_id):
        """Publica una asociación idempotente manteniendo la identidad del canal."""
        with self.database.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            valid=c.execute('SELECT 1 FROM package_imports i JOIN work_packages p ON p.channel_id=i.channel_id AND p.input_sha256=i.zip_sha256 WHERE i.import_id=? AND p.project_id=?',(import_id,project_id)).fetchone()
            if not valid:raise ValueError('El paquete no corresponde a esta importación.')
            c.execute('INSERT OR IGNORE INTO package_production_links VALUES (?,?)',(import_id,project_id))
            c.commit()
