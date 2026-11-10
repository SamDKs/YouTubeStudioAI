"""Entrega multipieza con SQLite real y fixtures; no atribuye renders ficticios a episodios."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests.integration import test_package_production as fixtures
from app.application.episode_delivery import EpisodeDelivery
from app.infrastructure.sqlite.deliveries import DeliveryStore
from app.domain.delivery import piece_plan
from app.domain.package_errors import StudioError
from app.engine.pipeline.delivery import DeliveryAssembler
from app.engine.pipeline.quality import check_subtitles


class EpisodeDeliveryTests(unittest.TestCase):
    def setUp(self):
        """Reutiliza la preparación real de un ZIP aislado y su base migrada."""
        self.fixture=fixtures.PackageProductionTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        _,self.project=self.fixture.activate();self.studio=self.fixture.studio
        self.studio.voices=lambda _:('am_michael',)
        self.store=DeliveryStore(self.fixture.db);self.service=EpisodeDelivery(self.studio,self.store)

    def short(self,text='A separate question leads to a different explanation.'):
        """Construye un timeline explícito con recursos de prueba existentes."""
        value=deepcopy(self.studio.editable(self.project)['manifest']['deliverables'][0])
        value.update(deliverable_id='short-test',kind='short',title='Independent fixture')
        value['scenes'][0].update(scene_id='short-scene',narration=text)
        return value

    def test_missing_scripts_and_idempotent_jobs(self):
        """Conserva tres faltantes, un solo job y una entrega al repetir la solicitud."""
        first=self.service.start(self.project);second=self.service.start(self.project)
        self.assertEqual(first,second);self.assertEqual(len(self.studio.jobs(self.project)),1)
        row=self.store.list(self.project)[0]
        self.assertEqual(sum(p['state']=='NEEDS_SCRIPT' for p in row['pieces']),3)
        self.assertFalse(row['bundle_path'])

    def test_approved_short_and_selective_regeneration(self):
        """Una regeneración del Short conserva el job largo y crea solo otro Short."""
        self.service.approve_short(self.project,self.short())
        first=self.service.start(self.project)
        before={p['slot']:p['job_id'] for p in self.store.list(self.project)[0]['pieces']}
        second=self.service.start(self.project,regenerate='short_01')
        after={p['slot']:p['job_id'] for p in self.store.list(self.project)[0]['pieces']}
        self.assertNotEqual(first,second);self.assertEqual(before['long'],after['long'])
        self.assertNotEqual(before['short_01'],after['short_01'])
        self.assertEqual(len(self.studio.jobs(self.project)),3)

    def test_duplicate_short_rejected_before_save(self):
        """Un recorte textual no altera la revisión ni persiste un guion aprobado."""
        old=self.studio.get(self.project).revision_id
        with self.assertRaises(StudioError):self.service.approve_short(self.project,self.short('Evidence needs context.'))
        self.assertEqual(old,self.studio.get(self.project).revision_id)
        self.assertFalse(self.store.candidates(self.project))

    def test_missing_llm_does_not_enqueue(self):
        """No presenta generación simulada cuando no existe proveedor configurado."""
        with self.assertRaises(StudioError):self.studio.request_short_scripts(self.project)
        self.assertFalse(self.studio.jobs(self.project))

    def test_auto_preference_isolated_and_approval_blocked(self):
        """La preferencia se limita al canal y una entrega incompleta no se aprueba."""
        self.store.set_auto('MIS',True)
        self.assertTrue(self.store.auto_enabled('MIS'));self.assertFalse(self.store.auto_enabled('TEC'))
        delivery=self.service.start(self.project)
        DeliveryAssembler(self.studio.settings,self.studio.queue).refresh(self.project)
        with self.assertRaises(ValueError):self.store.approve(delivery,'owner','Reviewed')
        with self.assertRaises(StudioError):self.service.bundle_bytes(self.project,delivery)

    def test_all_channels_error_isolation(self):
        """Un error en un canal no impide iniciar el siguiente proyecto."""
        from unittest.mock import patch
        with patch.object(self.studio,'projects',return_value=[{'project_id':'absent','channel_id':'TEC'},{'project_id':self.project,'channel_id':'MIS'}]):
            results=self.service.start_all()
        self.assertIn('error',results[0]);self.assertIn('delivery_id',results[1])

    def test_subtitle_temporal_validation(self):
        """Rechaza texto sin timestamps, solapamientos y tiempos fuera del video."""
        path=self.fixture.settings.project_root/'subtitles.srt'
        path.write_text('1\n00:00:00,000 --> 00:00:01,000\nTest\n')
        self.assertEqual(check_subtitles(path,2),1)
        for content in ('invalid','1\n00:00:00,000 --> 00:00:03,000\nTest','1\n00:00:00,000 --> 00:00:01,000\nTest\n\n2\n00:00:00,500 --> 00:00:02,000\nOverlap'):
            path.write_text(content)
            with self.assertRaises(StudioError):check_subtitles(path,2)

    def test_four_piece_bundle_approval_and_tamper(self):
        """Prueba empaquetado y aprobación con resultados simulados, sin afirmar renders reales."""
        from unittest.mock import patch
        from app.engine.domain.serialization import digest
        import zipfile
        for index in range(3):
            short=self.short(f'Independent fixture number {index} has its own question and conclusion.')
            short['deliverable_id']=f'short-{index}';short['scenes'][0]['scene_id']=f'scene-short-{index}'
            self.service.approve_short(self.project,short)
        data=self.studio.editable(self.project)
        data['manifest']['publication_metadata']={'description':'Test fixture description.','keywords':['fixture']}
        # Thumbnail se usa únicamente en este snapshot temporal de prueba.
        data['manifest']['assets'][0]['role']='thumbnail'
        self.studio.save(self.project,data['manifest'],data['voice'],data['version'])
        delivery=self.service.start(self.project);row=self.store.list(self.project)[0]
        root=self.fixture.settings.project_root;video=root/'fixture.mp4';video.write_bytes(b'not a real render: assembler fixture')
        subtitle=root/'fixture.srt';subtitle.write_text('1\n00:00:00,000 --> 00:00:01,000\nFixture\n')
        jobs=[{'job_id':p['job_id'],'status':'completed','last_error':None,'result':{'outputs':[{'path':'fixture.mp4','subtitles':'fixture.srt','deliverable_id':p['deliverable_id'],'duration':1.,'provisional_subtitles':False,'quality':{'technical_state':'QA_PASSED','warnings':[]}}]}} for p in row['pieces']]
        assembler=DeliveryAssembler(self.studio.settings,self.studio.queue)
        with patch.object(self.studio.queue,'jobs',return_value=jobs),patch.object(self.studio.queue,'checkpoints',return_value=[{'result_reference':'work-file:fixture.mp4','integrity_hash':digest(video.read_bytes())}]):
            result=assembler.refresh(self.project)[0]
            self.assertTrue(result['report']['all_four_rendered_and_qa_passed'])
            with zipfile.ZipFile(root/result['bundle_path']) as archive:
                self.assertEqual(len([n for n in archive.namelist() if n.endswith('.mp4')]),4)
                self.assertIsNone(archive.testzip())
            self.service.approve(self.project,delivery,'Fixture human decision')
            approved=assembler.refresh(self.project)[0]
            self.assertEqual(approved['state'],'APPROVED_FOR_PUBLICATION')
            (root/approved['bundle_path']).write_bytes(b'corrupted archive')
            with self.assertRaises(StudioError):self.service.bundle_bytes(self.project,delivery)
            blocked=assembler.refresh(self.project)[0]
            self.assertEqual(blocked['state'],'BLOCKED');self.assertFalse(blocked['bundle_path'])
            self.assertEqual(assembler.refresh(self.project)[0]['state'],'BLOCKED')

    def test_real_qa_detects_black_video(self):
        """Detecta negro en un MP4 sintético decodificable con voz sustituida por un tono de prueba."""
        import subprocess
        from app.engine.pipeline.quality import inspect_output
        root=self.fixture.settings.project_root
        subprocess.run([self.studio.settings.ffmpeg,'-nostdin','-v','error','-f','lavfi','-i','color=c=black:s=320x180:r=30:d=1.5','-f','lavfi','-i','sine=frequency=440:duration=1.5','-c:v','libx264','-threads','2','-c:a','aac','-shortest',str(root/'black.mp4')],check=True,capture_output=True)
        (root/'black.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nTest fixture\n')
        result=inspect_output(self.studio.settings,root,{'path':'black.mp4','subtitles':'black.srt'},(320,180),30,[{'scene_seconds':1.5}],lambda:None,lambda _:None)
        self.assertEqual(result['technical_state'],'QA_REVIEW_REQUIRED')
        self.assertTrue(result['black_segments_seconds'])
