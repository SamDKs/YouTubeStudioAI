"""Integridad, respaldo y catálogo del almacenamiento que usa la aplicación actual."""

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app.bootstrap import prepare_storage
from app.config import Settings
from app.storage import Database,restore_backup,MIGRATIONS
from app.domain.package_errors import StorageError


class MigrationTests(unittest.TestCase):
    def setUp(self):
        """Crea un catálogo temporal de los tres canales sin modificar datos del propietario."""
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.settings=Settings(self.root)
        self.catalog=self.root/'config/canales.json';self.catalog.parent.mkdir()
        self.catalog.write_text(json.dumps({'channels':[{'id':code,'name':code,'category':'test','folder':folder} for code,folder in [('MIS','01_misterios'),('TEC','02_tecnologia_ia'),('CIE','03_ciencia_curiosidades')]]}))
        self.database=Database(self.settings.database_path)
        self.latest=len(list(MIGRATIONS.glob('*.sql')))

    def test_create_and_repeat_migrations(self):
        """Una inicialización repetida no duplica migraciones y conserva FK/WAL."""
        self.database.initialize();self.database.initialize()
        with self.database.connection() as c:
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],self.latest)
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0],1)
            self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()[0],'wal')
            self.assertEqual(c.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],self.latest)
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())

    def test_upgrade_preserves_channels_and_backs_up(self):
        """Actualiza una base antigua conservando canales y una copia previa íntegra."""
        self.database.initialize(target_version=1)
        with self.database.connection() as c:
            c.execute('INSERT INTO channels VALUES (?,?,?,?,?,?,?,?,?)',('MIS','MIS','','test','en-US','US','active','now','now'))
        self.database.initialize()
        backups=list((self.root/'data/backups').glob(f'before-schema-{self.latest}-*.sqlite3'))
        self.assertEqual(len(backups),1)
        with sqlite3.connect(backups[0]) as c:
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM channels').fetchone()[0],1)
        with self.database.connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM channels').fetchone()[0],1)

    def test_catalog_import_idempotent_with_correct_record_paths(self):
        """SQLite conserva el catálogo inicial y las rutas de los tres registros reales."""
        prepare_storage(self.settings);prepare_storage(self.settings)
        self.catalog.write_text('{"channels":[]}');prepare_storage(self.settings)
        with self.database.connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM channels').fetchone()[0],3)
            rows=c.execute('SELECT * FROM channel_storage').fetchall()
            self.assertTrue(all(r[2].startswith('canales/') and r[2].endswith('/REGISTRO_MAESTRO.md') for r in rows))

    def test_foreign_keys_rollback_and_duplicates(self):
        """Las relaciones inválidas y claves repetidas no dejan escrituras parciales."""
        self.database.initialize()
        with self.database.connection() as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO channel_storage VALUES ('NO','#ffffff','missing',0,NULL,NULL)")
            c.execute('BEGIN IMMEDIATE');c.execute("INSERT INTO app_metadata VALUES ('test','first')")
            with self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO app_metadata VALUES ('test','duplicate')")
            c.rollback();self.assertIsNone(c.execute("SELECT value FROM app_metadata WHERE key='test'").fetchone())

    def test_backup_restore_preserves_committed_wal(self):
        """Restaura datos confirmados sin sobrescribir destinos ni respaldos existentes."""
        prepare_storage(self.settings)
        with self.database.connection() as live:
            live.execute("INSERT INTO app_metadata VALUES ('persisted','yes')")
            backup=self.database.backup(self.root/'verified.sqlite3');restored=self.root/'restored.sqlite3'
            restore_backup(backup,restored)
            with Database(restored).connection() as c:
                self.assertEqual(c.execute("SELECT value FROM app_metadata WHERE key='persisted'").fetchone()[0],'yes')
                self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
        with self.assertRaises(StorageError):restore_backup(backup,restored)
        with self.assertRaises(StorageError):self.database.backup(backup)

    def test_failed_catalog_import_is_atomic(self):
        """Un ID repetido en el catálogo no deja uno de los canales creado a medias."""
        value=json.loads(self.catalog.read_text());value['channels'][1]['id']='MIS';self.catalog.write_text(json.dumps(value))
        with self.assertRaises(sqlite3.IntegrityError):prepare_storage(self.settings)
        with self.database.connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM channels').fetchone()[0],0)

    def test_tampered_schema_rejected(self):
        """Un checksum modificado bloquea la inicialización sin reinterpretar el historial."""
        self.database.initialize()
        with self.database.connection() as c:c.execute("UPDATE schema_migrations SET checksum='tampered' WHERE version=1")
        with self.assertRaises(StorageError):self.database.initialize()

    def test_schema_not_downgraded(self):
        """Un cliente antiguo no degrada una base ya migrada."""
        self.database.initialize()
        with self.assertRaises(StorageError):self.database.initialize(target_version=1)

    def test_concurrent_initialization_has_one_catalog(self):
        """Dos sesiones concurrentes producen un único catálogo y un historial de esquema."""
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:prepare_storage(self.settings),range(2)))
        with self.database.connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM channels').fetchone()[0],3)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],self.latest)
