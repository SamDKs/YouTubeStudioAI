"""Seguridad y persistencia reales con SQLite temporal; sin proveedores."""

from pathlib import Path
import tempfile
import unittest
import zipfile

from app.bootstrap import prepare_storage
from app.config import Settings
from app.application.package_preparation import PreparePackages
from app.infrastructure.package_inventory import inventory
from app.infrastructure.sqlite.package_imports import PackageImports
from app.engine.ingestion.zip_reader import ZipReader
from app.domain.package_errors import StudioError


class PackagePreparationTests(unittest.TestCase):
    def setUp(self):
        """Construye un catálogo mínimo con migraciones reales sin tocar los pilotos."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(project_root=self.root)
        self.database = prepare_storage(self.settings)
        with self.database.connection() as c:
            for channel in ('MIS', 'TEC'):
                c.execute('INSERT INTO channels VALUES (?,?,?,?,?,?,?,?,?)', (channel,channel,'','test','en-US','US','active','now','now'))
        self.repo = PackageImports(self.database)
        self.service = PreparePackages(self.settings, self.repo, ZipReader(require_manifest=False), inventory)

    def archive(self, files):
        """Escribe un ZIP real para ejercitar extracción, CRC e inventario."""
        path = self.root / 'package.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return path

    def test_resources_persist_recover_and_deduplicate_by_channel(self):
        """Comprueba recuperación por nueva conexión y aislamiento de identidad."""
        path = self.archive({'guiones/en.md': 'A reviewed story needs an explicit timeline.'})
        identifier = self.service.import_zip(path, 'MIS', 'resources.zip')
        self.assertEqual(self.repo.list('MIS')[0]['state'], 'NEEDS_SCRIPT')
        self.assertEqual(self.service.import_zip(path, 'MIS', 'again.zip'), identifier)
        self.service.import_zip(path, 'TEC', 'resources.zip')
        recovered = PackageImports(self.database)
        self.assertEqual(len(recovered.list()), 2)
        self.assertEqual(len(recovered.list('MIS')), 1)
        self.service.prepare(identifier, 'MIS')
        self.assertEqual(len(recovered.events(identifier)), 3)
        self.assertTrue((self.settings.imports_root / 'MIS' / identifier / 'input/guiones/en.md').is_file())

    def test_corrupt_and_unsafe_are_recorded(self):
        """Conserva errores y rechaza traversal, ejecutables y binarios disfrazados."""
        for files in ({'../outside.txt':'bad'}, {'run.py':'print(1)'}, {'fake.png':'not an image'}, {'fake.txt':'MZbinary'}):
            with self.subTest(files=files):
                self.service.import_zip(self.archive(files), 'MIS', 'bad.zip')
                self.assertEqual(self.repo.list('MIS')[0]['state'], 'FAILED')
        path = self.root / 'corrupt.zip'
        path.write_bytes(b'not a zip')
        self.service.import_zip(path, 'MIS', 'corrupt.zip')
        self.assertEqual(self.repo.list('MIS')[0]['state'], 'FAILED')
        self.assertFalse((self.root / 'outside.txt').exists())

    def test_unknown_channel_and_cross_channel_prepare(self):
        """Impide importar y asociar estados fuera del canal seleccionado."""
        path = self.archive({'notes.md':'No inferred facts.'})
        with self.assertRaises(StudioError):
            self.service.import_zip(path, 'UNKNOWN', 'test.zip')
        identifier = self.service.import_zip(path, 'MIS', 'test.zip')
        with self.assertRaises(StudioError):
            self.service.prepare(identifier, 'TEC')

    def test_structured_contract_and_channel_mismatch(self):
        """Reutiliza el contrato canónico y bloquea asociación a otro canal."""
        from tools.build_example import build
        folder = self.root / 'structured'
        build(folder)
        path = self.root / 'structured.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for file in folder.rglob('*'):
                if file.is_file():
                    archive.write(file, file.relative_to(folder))
        self.service.import_zip(path, 'MIS', 'structured.zip')
        row = self.repo.list('MIS')[0]
        self.assertEqual(row['report']['episode_id'], 'EXAMPLE-001')
        self.assertEqual(row['state'], 'NEEDS_ASSETS')
        self.service.import_zip(path, 'TEC', 'structured.zip')
        self.assertEqual(self.repo.list('TEC')[0]['state'], 'FAILED')

    def test_streamlit_context_and_upload_are_available(self):
        """Arranca la UI real con almacenamiento temporal e intercambia contexto."""
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        from app.bootstrap import create_studio
        studio = create_studio(self.settings)
        with patch('app.workbench.create_studio', return_value=studio):
            app = AppTest.from_string('from app.workbench import main; main()').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get('file_uploader')), 0)
            app.selectbox(key='phase1_context').set_value('MIS').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get('file_uploader')), 1)
            app.selectbox(key='phase1_context').set_value('TEC').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key='phase1_context').value, 'TEC')
            self.assertEqual(len(app.get('file_uploader')), 1)

    def test_upgrade_preserves_historical_work_package(self):
        """Migra una base de versión 11 sin alterar el manifiesto histórico."""
        from app.storage import Database
        db = Database(self.root / 'old.sqlite3')
        db.initialize(target_version=11)
        with db.connection() as c:
            c.execute('INSERT INTO channels VALUES (?,?,?,?,?,?,?,?,?)', ('MIS','MIS','','test','en-US','US','active','now','now'))
            c.execute('INSERT INTO work_packages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                      ('historic','MIS','WOW-001','en-US','Wow!','old/path','abc','{}','[]',None,'imported','now'))
        db.initialize()
        with db.connection(read_only=True) as c:
            self.assertEqual(c.execute('SELECT title FROM work_packages WHERE project_id=?', ('historic',)).fetchone()[0], 'Wow!')
            self.assertFalse(c.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], 14)

    def test_audio_metadata_uses_real_ffprobe(self):
        """Lee duración, codec y audio de un WAV de prueba real."""
        import wave
        audio = self.root / 'sample.wav'
        with wave.open(str(audio), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(8000)
            writer.writeframes(b'\x00\x00' * 800)
        path = self.archive({'assets/audio/sample.wav': audio.read_bytes()})
        self.service.import_zip(path, 'MIS', 'audio.zip')
        row = self.repo.list('MIS')[0]
        self.assertEqual(row['state'], 'NEEDS_SCRIPT')
        media = row['report']['files'][0]
        self.assertAlmostEqual(media['duration'], .1, places=2)
        self.assertTrue(media['has_audio'])
        self.assertIn('pcm_s16le', media['codecs'])

    def test_symlink_and_configurable_limits(self):
        """Rechaza enlaces simbólicos y límites reducidos sin extraer fuera."""
        import stat
        from app.engine.ingestion.zip_reader import ZipLimits
        path = self.root / 'link.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            entry = zipfile.ZipInfo('link.txt')
            entry.create_system = 3
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(entry, '/tmp/outside')
        self.service.import_zip(path, 'MIS', 'link.zip')
        self.assertEqual(self.repo.list('MIS')[0]['state'], 'FAILED')
        self.service.reader = ZipReader(ZipLimits(file_bytes=4), require_manifest=False)
        self.service.import_zip(self.archive({'notes.md': 'too large'}), 'MIS', 'limit.zip')
        self.assertEqual(self.repo.list('MIS')[0]['state'], 'FAILED')

    def test_complete_structured_package_is_ready(self):
        """Exige un largo y tres Shorts explícitos para declarar preparación completa."""
        import copy
        import json
        from tools.build_example import build
        folder = self.root / 'complete'
        manifest = build(folder)
        original = manifest['deliverables'][0]
        manifest['deliverables'] = []
        for index, kind in enumerate(['long', 'short', 'short', 'short']):
            deliverable = copy.deepcopy(original)
            deliverable.update(deliverable_id='piece-'+str(index), kind=kind)
            deliverable['scenes'][0]['scene_id'] = 'scene-'+str(index)
            manifest['deliverables'].append(deliverable)
        (folder / 'manifest.json').write_text(json.dumps(manifest))
        path = self.root / 'complete.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for file in folder.rglob('*'):
                if file.is_file():
                    archive.write(file, file.relative_to(folder))
        identifier = self.service.import_zip(path, 'MIS', 'complete.zip')
        self.assertEqual(self.repo.list('MIS')[0]['state'], 'READY_FOR_PRODUCTION')
        self.service.prepare(identifier, 'MIS')
        self.assertEqual(self.repo.list('MIS')[0]['state'], 'READY_FOR_PRODUCTION')
