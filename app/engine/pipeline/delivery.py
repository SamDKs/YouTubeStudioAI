"""Empaqueta resultados reales por episodio; conserva faltantes y revisiones."""

import fcntl
import json
import shutil
from uuid import uuid4
import zipfile

from PIL import Image
from app.infrastructure.sqlite.deliveries import DeliveryStore
from app.engine.domain.serialization import digest,encoded
from app.engine.pipeline.quality import check_subtitles
from app.domain.package_errors import StudioError


class DeliveryAssembler:
    def __init__(self,settings,queue):
        """Comparte cola y SQLite; no crea renders ni aprueba contenidos."""
        self.settings,self.queue=settings,queue
        self.repository=DeliveryStore(queue.database)

    def refresh(self,project_id):
        """Recalcula entregas a partir de jobs reales; solo empaqueta estados terminales."""
        for delivery in self.repository.list(project_id):
            folder=self.settings.exports_root/'deliveries'/delivery['delivery_id'];folder.mkdir(parents=True,exist_ok=True)
            with (folder/'.delivery.lock').open('a') as lock:
                try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:continue
                self._refresh(delivery,folder)
        return self.repository.list(project_id)

    def _refresh(self,delivery,folder):
        """Conserva cada pieza como entidad independiente y nunca simula cuatro éxitos."""
        if delivery['report'].get('integrity_failure'):return
        jobs={j['job_id']:j for j in self.queue.jobs(delivery['project_id'])};pieces=[];ready=[];active=False
        for piece in delivery['pieces']:
            item=dict(piece);job=jobs.get(piece['job_id'])
            if job:
                output=next((o for o in job['result'].get('outputs',[]) if not o.get('preview') and o['deliverable_id']==piece['deliverable_id']),None)
                item['job_status']=job['status']
                item['state']=job['status'].upper();item['reason']=job['last_error']
                if job['status'] in {'queued','running','paused','interrupted'}:active=True
                if job['status']=='completed' and output:
                    path=self.settings.safe(output['path'])
                    checkpoint=next((c for c in reversed(self.queue.checkpoints(job['job_id'])) if c['result_reference']=='work-file:'+output['path']),None)
                    if not path.is_file() or not checkpoint or digest(path.read_bytes())!=checkpoint['integrity_hash']:
                        item.update(state='QA_FAILED',reason='El archivo final falta o cambió desde su checkpoint.')
                    elif output.get('quality',{}).get('technical_state')=='QA_PASSED':
                        try:
                            subtitle=self.settings.safe(output['subtitles'])
                            check_subtitles(subtitle,output['duration'])
                            item.update(state='EDITORIAL_REVIEW_PENDING',render_state='RENDER_COMPLETED',technical_state='QA_PASSED',output=output,subtitle_sha256=digest(subtitle.read_bytes()))
                            ready.append(item)
                        except (OSError,ValueError,StudioError) as exc:
                            item.update(state='QA_FAILED',reason='Subtítulos no válidos: '+str(exc))
                    else:item.update(state='QA_REVIEW_REQUIRED',reason='Revisa el diagnóstico técnico antes de entregar la pieza.',output=output)
            pieces.append(item)
        complete=len(ready)==4 and len(pieces)==4
        state='PRODUCING' if active else ('EDITORIAL_REVIEW_PENDING' if complete else 'PARTIAL_DELIVERY' if ready else 'BLOCKED')
        report={'state':state,'all_four_rendered_and_qa_passed':complete,'approved_for_publication':False,
                'pieces':pieces,'missing_slots':[p['slot'] for p in pieces if p.get('technical_state')!='QA_PASSED']}
        report['base_fingerprint']=digest(encoded(report))
        approval=self.repository.approval(delivery['delivery_id'])
        if approval and approval['fingerprint']==report['base_fingerprint']:
            report.update(state='APPROVED_FOR_PUBLICATION',approved_for_publication=True,approval=approval)
            state='APPROVED_FOR_PUBLICATION'
        bundle=None
        if not active and ready:
            fingerprint=digest(encoded(report))
            previous=delivery['bundle_path']
            if delivery['report'].get('content_fingerprint')==fingerprint and previous:
                archive=self.settings.safe(previous)
                if archive.is_file() and digest(archive.read_bytes())==delivery['report'].get('bundle_sha256'):
                    return
                # Un ZIP alterado no conserva aprobación ni se ofrece como verificado.
                report.update(integrity_failure=True,state='BLOCKED',approved_for_publication=False,bundle_path_verified=False,approval_blockers=['El ZIP cambió o falta; vuelve a generar la entrega.'])
                self.repository.save_report(delivery['delivery_id'],'BLOCKED',report,None)
                return
            bundle=self._bundle(delivery,ready,report,folder,fingerprint)
            report['content_fingerprint']=fingerprint
            report['bundle_sha256']=digest(self.settings.safe(bundle).read_bytes())
        self.repository.save_report(delivery['delivery_id'],state,report,bundle)

    def _bundle(self,delivery,ready,report,folder,fingerprint):
        """Crea nombres estables, manifiestos y ZIP a partir de archivos verificados."""
        project=self.queue.project(delivery['project_id'])
        with self.queue.database.connection(read_only=True) as c:
            revision=c.execute('SELECT content FROM work_revisions WHERE revision_id=?',(delivery['revision_id'],)).fetchone()
        snapshot=json.loads(revision[0]);manifest=snapshot['manifest'];input_root=self.settings.safe(project['import_relative_path'])/'input'
        destination=folder/fingerprint;staging=folder/('staging-'+uuid4().hex);staging.mkdir()
        metadata={'title':manifest['title'],'language':manifest['language'],'channel_id':manifest['channel_id'],'episode_id':manifest['episode_id'],
                  'description':manifest.get('publication_metadata',{}).get('description',''),
                  'keywords':manifest.get('publication_metadata',{}).get('keywords',[]),
                  'sources':manifest['editorial_references'],'attributions':[a['provenance']|{'asset_id':a['asset_id']} for a in manifest['assets']],
                  'review_state':report['state'],'editorial_warnings':[], 'videos':[]}
        if not metadata['description']:metadata['editorial_warnings'].append('Falta descripción estructurada: revisar documentos editoriales del ZIP.')
        for item in ready:
            output=item['output'];name=item['slot']+'_en-US';source=self.settings.safe(output['path'])
            shutil.copyfile(source,staging/(name+'.mp4'))
            subtitle=self.settings.safe(output['subtitles']);check_subtitles(subtitle,output['duration'])
            (staging/'subtitles').mkdir(exist_ok=True);shutil.copyfile(subtitle,staging/'subtitles'/(name+'.srt'))
            deliverable=next(d for d in manifest['deliverables'] if d['deliverable_id']==item['deliverable_id'])
            metadata['videos'].append({'slot':item['slot'],'title':deliverable['title'],'duration':output['duration'],'format':'9:16' if deliverable['kind']=='short' else '16:9',
                  'language':'en-US','file':name+'.mp4','sha256':digest(source.read_bytes()),'subtitles':'subtitles/'+name+'.srt','provisional_subtitles':output.get('provisional_subtitles',False)})
            metadata['editorial_warnings']+=output['quality'].get('warnings',[])
        thumb=next((a for a in manifest['assets'] if a['role']=='thumbnail' and a['status']=='available' and a['kind']=='image'),None)
        if thumb:
            source=input_root/thumb['path']
            if digest(source.read_bytes())!=thumb['sha256']:raise ValueError('La miniatura original cambió.')
            with Image.open(source) as image:image.convert('RGB').save(staging/'thumbnail.png')
            metadata['thumbnail']={'file':'thumbnail.png','asset_id':thumb['asset_id'],'source_sha256':thumb['sha256'],'provenance':thumb['provenance']}
        else:metadata['editorial_warnings'].append('NEEDS_THUMBNAIL: falta miniatura proporcionada; no se simuló.')
        rights=[a['asset_id'] for a in manifest['assets'] if a['provenance']['rights_status']!='allowed']
        if rights:metadata['editorial_warnings'].append('Derechos pendientes: '+', '.join(rights))
        report['rights_review_pending']=rights
        blockers=[]
        if not report['all_four_rendered_and_qa_passed']:blockers.append('Faltan piezas o controles técnicos.')
        if rights:blockers.append('Derechos pendientes de revisión.')
        if any(i['output'].get('provisional_subtitles') for i in ready):blockers.append('Hay subtítulos aproximados pendientes de corrección.')
        if not thumb:blockers.append('Falta miniatura real.')
        if not metadata['description']:blockers.append('Falta descripción estructurada.')
        report['approval_blockers']=blockers
        report['bundle_path_verified']=True
        for name,value in [('metadata.json',metadata),('qa_report.json',report),('project_manifest.json',{'contract':manifest,'voice':snapshot['voice'],'configuration':delivery['configuration'],
                'project_id':delivery['project_id'],'revision_id':delivery['revision_id'],'original_zip_sha256':project['input_sha256'],'original_input_path':project['import_relative_path']})]:
            (staging/name).write_bytes(encoded(value))
        if not destination.exists():staging.rename(destination)
        else:shutil.rmtree(staging)  # Solo temporal creado por esta invocación.
        # Los temporales propios que pierden una carrera no sustituyen archivos previos.
        archive=folder/(fingerprint+'.zip')
        if not archive.exists():
            temporary=folder/(uuid4().hex+'.zip')
            with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED) as z:
                for path in sorted(destination.rglob('*')):
                    if path.is_file():z.write(path,path.relative_to(destination))
            temporary.rename(archive)
        report['output_directory']=str(destination.relative_to(self.settings.project_root))
        return str(archive.relative_to(self.settings.project_root))
