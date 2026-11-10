"""Control real de cola y vínculo de importación, sin servicios remotos."""

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from app.bootstrap import create_studio
from app.config import Settings
from app.application.package_preparation import PreparePackages
from app.application.package_production import ProducePackages
from app.infrastructure.package_inventory import inventory
from app.infrastructure.sqlite.package_imports import PackageImports
from app.infrastructure.sqlite.package_production import ProductionLinks
from app.domain.package_errors import Paused, StudioError
from app.engine.ingestion.zip_reader import ZipReader
from tools.build_example import build


class PackageProductionTests(unittest.TestCase):
    def setUp(self):
        """Construye dos canales reales y un paquete canónico en disco temporal."""
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.settings=Settings(Path(self.temp.name));self.studio=create_studio(self.settings)
        self.db=self.studio.repository.database
        with self.db.connection() as c:
            for channel in ('MIS','TEC'):
                c.execute('INSERT INTO channels VALUES (?,?,?,?,?,?,?,?,?)',(channel,channel,'','test','en-US','US','active','now','now'))
        folder=self.settings.project_root/'fixture';manifest=build(folder)
        manifest['deliverables'][0]['kind']='long';(folder/'manifest.json').write_text(json.dumps(manifest))
        self.path=self.settings.project_root/'input.zip'
        with zipfile.ZipFile(self.path,'w') as archive:
            for path in folder.rglob('*'):
                if path.is_file():archive.write(path,path.relative_to(folder))
        self.imports=PackageImports(self.db)
        self.preparation=PreparePackages(self.settings,self.imports,ZipReader(require_manifest=False),inventory)
        self.producer=ProducePackages(self.imports,self.studio,ProductionLinks(self.db))

    def activate(self):
        """Pasa por la importación de fase 1 y su puente persistente al motor."""
        identifier=self.preparation.import_zip(self.path,'MIS','test.zip')
        return identifier,self.producer.activate(identifier,'MIS')

    def test_import_bridge_and_long_plan_excludes_shorts(self):
        """Usa un solo paquete del motor, con perfil real de largo y control de canal."""
        identifier,project=self.activate()
        self.assertEqual(self.producer.activate(identifier,'MIS'),project)
        with self.assertRaises(StudioError):self.producer.activate(identifier,'TEC')
        self.studio.voices=lambda _:('am_michael',)
        job=self.studio.produce_long(project)
        steps=self.studio.queue.steps(job)
        self.assertIn('preview:explainer',[s['step_type'] for s in steps])
        self.assertIn('quality',[s['step_type'] for s in steps])
        self.assertFalse(any('short' in s['step_type'] for s in steps))
        lease=self.studio.queue.claim('first',job)
        self.assertIsNotNone(lease)
        context=self.studio.queue.run_context(lease)
        self.assertEqual(context['configuration']['fps'],30)
        self.assertTrue(context['configuration']['review_only'])
        self.assertIsNone(self.studio.queue.claim('second',job))

    def test_safe_pause_checkpoint_resume_and_cancel(self):
        """Persiste pausas y recuperación; la cancelación de una pausa es terminal."""
        _,project=self.activate();self.studio.voices=lambda _:('am_michael',)
        job=self.studio.produce_long(project);store=self.studio.queue
        lease=store.claim('worker',job);store.pause(job)
        # El guard normal permite terminar la etapa antes de atender pausa.
        store.guard(lease)
        with self.assertRaises(Paused):store.pause_boundary(lease)
        store.finish(lease,'paused',{},'Pausa verificada')
        store.resume(job)
        lease=store.claim('resumed',job)
        self.assertGreater(lease.token,1)
        store.pause(job);store.finish(lease,'paused',{},'Pausa')
        store.cancel(job)
        self.assertEqual(self.studio.jobs(project)[0]['status'],'canceled')
        self.assertIsNone(store.claim('late',job))

    def test_no_tts_blocks_instead_of_silent_narration(self):
        """No encola producción si el proveedor no tiene voces locales."""
        _,project=self.activate()
        self.studio.voices=lambda _:()
        with self.assertRaisesRegex(StudioError,'Bloqueado'):self.studio.produce_long(project)
        self.assertFalse(self.studio.jobs(project))

    def test_expired_lease_preserves_requested_pause(self):
        """Recupera un worker vencido sin perder una solicitud durable de pausa."""
        _,project=self.activate();self.studio.voices=lambda _:('am_michael',)
        job=self.studio.produce_long(project);store=self.studio.queue
        store.claim('expired',job);store.pause(job)
        with self.db.connection() as c:
            c.execute("UPDATE jobs SET lease_expires_at='2000-01-01T00:00:00+00:00' WHERE job_id=?",(job,))
        self.assertIsNone(store.claim('recovery',job))
        self.assertEqual(self.studio.jobs(project)[0]['status'],'paused')
        store.resume(job)
        self.assertIsNotNone(store.claim('resumed',job))

    def test_real_ffmpeg_music_mix(self):
        """Verifica ducking y AAC con medios sintéticos de prueba, separados del episodio real."""
        import subprocess
        from types import SimpleNamespace
        from app.engine.rendering.composer import PackageRenderer
        from app.engine.domain.serialization import digest
        root=self.settings.project_root;video=root/'test.mp4';music=root/'music.wav'
        subprocess.run([self.settings.ffmpeg,'-v','error','-f','lavfi','-i','color=c=navy:s=320x180:r=30:d=0.4',
                        '-f','lavfi','-i','sine=frequency=440:duration=0.4','-c:v','libx264','-threads','2','-c:a','aac','-shortest',str(video)],check=True,capture_output=True)
        subprocess.run([self.settings.ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=220:duration=0.3',str(music)],check=True,capture_output=True)
        asset=SimpleNamespace(path='music.wav',rights_status='allowed',sha256=digest(music.read_bytes()))
        package=SimpleNamespace(audio_mix=({'asset_id':'bed','deliverable_id':'long','start_seconds':0.,'gain':.1},),asset=lambda _:asset)
        renderer=PackageRenderer(self.settings,root/'working',root/'render.lock')
        output,metadata=renderer.mix_audio(video,package,SimpleNamespace(deliverable_id='long'),root,.4,lambda:None,lambda _:None)
        self.assertTrue(output.is_file())
        self.assertTrue(any(s['codec_name']=='aac' for s in metadata['streams']))
        self.assertLess(abs(metadata['duration']-.4),.1)

    def test_streamlit_production_controls_render_for_channel(self):
        """Comprueba formularios y contexto sin iniciar procesamiento desde la prueba UI."""
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        self.activate();self.studio.voices=lambda _:('am_michael',)
        with patch('app.workbench.create_studio',return_value=self.studio):
            app=AppTest.from_string('from app.workbench import main;main()').run()
            app.selectbox(key='phase1_context').set_value('MIS').run()
            self.assertFalse(app.exception)
            self.assertTrue(any(b.label=='Iniciar producción' for b in app.button))
            self.assertTrue(any(s.label=='Voz estadounidense' for s in app.selectbox))
            app.selectbox(key='phase1_context').set_value('TEC').run()
            self.assertFalse(app.exception)
            self.assertFalse(any(b.label=='Iniciar producción' for b in app.button))
