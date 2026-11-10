"""Single recoverable production engine for all imported channels and deliverables."""

from dataclasses import asdict,replace
import json
from pathlib import Path
import re
from uuid import uuid4

from app.files import atomic_new
from app.engine.audio.processing import AudioProcessor
from app.domain.package_errors import NeedsReview,StudioError
from app.engine.domain.package import Task,measure_timeline
from app.engine.domain.serialization import digest,encoded
from app.engine.ingestion.contract import validate_manifest
from app.engine.pipeline.plan import ENGINE_VERSION
from app.engine.rendering.composer import PackageRenderer
from app.engine.timing.alignment import WordTiming,validate_words,AlignmentReview
from app.engine.timing.subtitles import export_srt


def publish_result(path, content):
    """Reutiliza publicación idéntica tras reinicio; nunca sobrescribe otra versión."""
    if path.exists():
        if digest(path.read_bytes())!=digest(content):raise StudioError("El resultado existente difiere; se conservó para revisión.")
        return
    atomic_new(path,content)


class ProductionExecutor:
    def __init__(self,settings,repository,cache,speech,alignment):
        self.settings,self.repository,self.cache,self.speech,self.alignment=settings,repository,cache,speech,alignment

    # Publica el resultado durable antes de atender una pausa.
    def _checkpoint(self,lease,stage,entry):
        self.repository.checkpoint(lease,stage,str(entry.path.relative_to(self.settings.project_root)),entry.sha256)
        self.repository.pause_boundary(lease)

    def _audio(self,lease,scene,package,voice,processor,guard):
        key=digest(encoded({'text':scene.narration,'language':package.language,'voice':voice,'pause':scene.pause_after_seconds,
            'model':self.speech.model_fingerprint(),'normalization':'pcm24k-loudnorm-1','engine':ENGINE_VERSION}))
        entry=self.cache.get('audio',key,'.wav')
        if entry:return entry
        guard()
        content,model=self.speech.speech(scene.narration,voice['voice'],voice['speed'],voice.get('pronunciation'),language=package.language)
        guard();pcm,measurement=processor.normalize(content,scene.pause_after_seconds,guard)
        return self.cache.put('audio',key,pcm,'.wav',measurement|{'provider':model,'narration':scene.narration,'language':package.language,'synthetic':True})

    def _timing(self,scene,package,audio,override,guard):
        model=self.alignment.fingerprint(package.language) if self.alignment.available(package.language) else 'unavailable'
        key=digest(encoded({'audio':audio.sha256,'text':scene.narration,'model':model,'override':override}))
        entry=self.cache.get('timing',key,'.json')
        if entry:return entry
        data={key:audio.metadata[key] for key in ('narration_seconds','pause_seconds','scene_seconds')}
        data.update(audio_sha256=audio.sha256,words=[],status='requires_review',method='measured scene audio; words unverified',language=package.language)
        try:
            if override:
                if override['audio_sha256']!=audio.sha256:raise NeedsReview('La corrección manual corresponde a otro audio; no se aplicó.')
                words=validate_words([WordTiming(**w) for w in override['words']],scene.narration,data['narration_seconds'])
                data['method']='manual reviewed intervals'
            elif self.alignment.available(package.language):
                guard();words=self.alignment.align(audio.path.read_bytes(),scene.narration,data['narration_seconds'],scene.scene_id,language=package.language)
                data['method']='whisper.cpp observed timestamps; listening review required'
            else:raise NeedsReview('No hay modelo local de alineación compatible; los tiempos de palabras no existen.')
            data.update(words=[asdict(w) for w in words],status='text_and_time_validated')
        except AlignmentReview as exc:data.update(reason=str(exc),candidate_words=[asdict(w) for w in exc.candidates])
        except NeedsReview as exc:data['reason']=str(exc)
        guard();return self.cache.put('timing',key,encoded(data),'.json',{'status':data['status'],'audio_sha256':audio.sha256})

    def _asset(self,package,scene,input_root):
        asset=package.asset(scene.asset_id)
        if asset.status!='available':raise NeedsReview('El recurso '+asset.asset_id+' está pendiente o no disponible; no se sustituyó por relleno.')
        source=input_root/asset.path
        if not source.resolve().is_relative_to(input_root.resolve()) or not source.is_file() or digest(source.read_bytes())!=asset.sha256:raise NeedsReview('El recurso '+asset.asset_id+' falta o cambió respecto del paquete original.')
        return asset,source

    # Compone escenas a partir de audio medido y reutiliza renders verificados.
    def _render(self,lease,package,deliverable,scenes,audios,timings,input_root,working,configuration,guard):
        preview=configuration['preview'];width,height=deliverable.width,deliverable.height
        if preview:
            factor=min(1.,640/max(width,height));width=max(128,round(width*factor/2)*2);height=max(128,round(height*factor/2)*2)
        renderer=PackageRenderer(replace(self.settings,fps=deliverable.fps),working,self.settings.work_root/'render.lock')
        clips=[];provisional=False
        with renderer.render_slot(guard):
            for scene,audio,timing in zip(scenes,audios,timings):
                guard();asset,source=self._asset(package,scene,input_root)
                if asset.rights_status=='prohibited':raise NeedsReview('El recurso '+asset.asset_id+' tiene uso prohibido.')
                if not preview and not configuration.get('review_only') and asset.rights_status!='allowed':raise NeedsReview('Falta confirmar derechos del recurso '+asset.asset_id+'.')
                if deliverable.captions_mode=='word' and not timing['words']:
                    if deliverable.alignment_failure=='block' or (not preview and not configuration.get('allow_provisional')):raise NeedsReview('La escena '+scene.scene_id+' necesita alineación/corrección. No se declaró definitiva una temporización aproximada.')
                    provisional=True
                key=digest(encoded({'scene':asdict(scene),'asset':asset.sha256,'audio':audio.sha256,'timing':timing,'size':[width,height],'renderer':'phase3-mobile-1' if height>width else 'phase2-2','fps':deliverable.fps,'captions':deliverable.captions_mode,'engine':ENGINE_VERSION}))
                cached=self.cache.get('render',key,'.mp4')
                if not cached:
                    path=renderer.render_scene(scene,asset,source,audio.path,timing,deliverable,(width,height),key,guard,lambda p:self.repository.progress(lease,p))
                    cached=self.cache.put('render',key,path.read_bytes(),'.mp4',{'scene_id':scene.scene_id,'duration':timing['scene_seconds'],'size':[width,height]})
                clips.append(cached.path)
                self.repository.pause_boundary(lease)
            duration=sum(t['scene_seconds'] for t in timings)
            target=working/(uuid4().hex+'.mp4')
            metadata=renderer.assemble(tuple(clips),duration,target,guard,lambda p:self.repository.progress(lease,p))
            if package.audio_mix:
                target,metadata=renderer.mix_audio(target,package,deliverable,input_root,duration,guard,lambda p:self.repository.progress(lease,p))
        return target,metadata,provisional

    # Ejecuta el snapshot del job, guarda entregas y comprueba su calidad.
    def run(self,lease,guard) -> dict:
        context=self.repository.run_context(lease);task=Task(context['task'])
        if task==Task.SHORT_SCRIPTS:
            from app.engine.pipeline.short_scripts import generate_short_drafts
            return generate_short_drafts(self,lease,context,guard)
        package=validate_manifest(context['manifest']);voice=context['voice']
        if context['configuration'].get('horizontal_profile'):
            package=replace(package,deliverables=tuple(replace(d,width=1920,height=1080,fps=context['configuration']['fps']) if d.kind=='long' else d for d in package.deliverables))
        if context['configuration'].get('episode_piece'):
            package=replace(package,deliverables=tuple(replace(d,width=1080 if d.kind=='short' else 1920,height=1920 if d.kind=='short' else 1080,fps=context['configuration']['fps']) for d in package.deliverables))
        input_root=self.settings.safe(context['import_relative_path'])/'input'
        working=self.settings.temporary_root/'jobs'/lease.job_id;working.mkdir(parents=True,exist_ok=True)
        processor=AudioProcessor(self.settings,working,self.settings.work_root/'render.lock')
        result={'project_id':context['project_id'],'task':task.value,'preview':task==Task.PREVIEW,'editorial_review':'pending','outputs':[],'scenes':[],'paid_api_calls':0,'warnings':[]}
        result['logs_directory']=str(working.relative_to(self.settings.project_root))
        result['music']='explicit licensed tracks' if package.audio_mix else 'none: no authorized audio_mix supplied'
        result['rights_review_pending']=[a.asset_id for a in package.assets if a.rights_status!='allowed']
        if result['rights_review_pending']:
            result['warnings'].append('Derechos pendientes de revisión; esta entrega local no autoriza publicación.')
        for deliverable in package.deliverables:
            selected=context['selection'].get(deliverable.deliverable_id,[])
            if not selected:continue
            scenes=tuple(s for s in deliverable.scenes if s.scene_id in selected);audios=[];timings=[]
            for scene in scenes:
                guard();stage=f'audio:{deliverable.deliverable_id}:{scene.scene_id}';self.repository.start(lease,stage)
                audio=self._audio(lease,scene,package,voice,processor,guard);self._checkpoint(lease,stage,audio);audios.append(audio)
                item={'deliverable_id':deliverable.deliverable_id,'scene_id':scene.scene_id,'audio_path':str(audio.path.relative_to(self.settings.project_root)),**{k:audio.metadata[k] for k in ('narration_seconds','scene_seconds')}}
                if task!=Task.NARRATE:
                    stage=f'timing:{deliverable.deliverable_id}:{scene.scene_id}';self.repository.start(lease,stage)
                    entry=self._timing(scene,package,audio,context.get('timing_overrides',{}).get(scene.scene_id),guard);self._checkpoint(lease,stage,entry)
                    timing=json.loads(entry.path.read_text());timings.append(timing)
                    item.update(timing_path=str(entry.path.relative_to(self.settings.project_root)),alignment_status=timing['status'])
                    if timing['status']=='requires_review':result['warnings'].append(scene.scene_id+': '+timing.get('reason','alineación pendiente'))
                result['scenes'].append(item)
            if deliverable.kind=='short' and timings:
                total_audio=sum(t['scene_seconds'] for t in timings)
                if total_audio>context['configuration'].get('short_max_seconds',180):raise NeedsReview('El Short supera la duración configurada. Edita su guion o amplía el límite permitido; no se cortó la narración.')
                if total_audio<30:result['warnings'].append(deliverable.deliverable_id+': duración inferior a los 30 s preferidos; no se agregó relleno.')
            if task in {Task.PREVIEW,Task.EXPORT,Task.PRODUCE}:
                if task==Task.PRODUCE:
                    stage='preview:'+deliverable.deliverable_id
                    self.repository.start(lease,stage)
                    preview_path,preview_meta,_=self._render(lease,package,deliverable,scenes,audios,timings,input_root,working,context['configuration']|{'preview':True},guard)
                    preview_entry=self.cache.put('render',digest(preview_path.read_bytes()),preview_path.read_bytes(),'.mp4',{'preview':True,'duration':preview_meta['duration']})
                    self._checkpoint(lease,stage,preview_entry)
                    result['outputs'].append({'deliverable_id':deliverable.deliverable_id,'path':str(preview_entry.path.relative_to(self.settings.project_root)),'preview':True,'duration':preview_meta['duration']})
                stage='render:'+deliverable.deliverable_id;self.repository.start(lease,stage)
                path,metadata,provisional=self._render(lease,package,deliverable,scenes,audios,timings,input_root,working,context['configuration'],guard)
                stem=re.sub(r'[^A-Za-z0-9_-]+','_',package.title)[:70]+'__'+package.episode_id+'__'+deliverable.deliverable_id+'__'+package.language+('__PREVIEW' if task==Task.PREVIEW else '__REVIEW_PENDING')
                folder=self.settings.exports_root/(package.episode_id+'_'+package.language)/lease.job_id;folder.mkdir(parents=True,exist_ok=True)
                video=folder/(stem+'.mp4');publish_result(video,path.read_bytes())
                srt,approximate=export_srt(scenes,tuple(timings));subtitle=folder/(stem+('_PROVISIONAL' if approximate else '_ALIGNED')+'.srt');publish_result(subtitle,srt)
                measured=measure_timeline(scenes,tuple(t['narration_seconds'] for t in timings))
                timeline={'language':package.language,'timing_status':'provisional_words' if approximate else 'word_alignment_checked_listening_pending','scenes':[asdict(m) for m in measured],'words_by_scene':{s.scene_id:t['words'] for s,t in zip(scenes,timings)}}
                publish_result(folder/(stem+'_timing.json'),encoded(timeline))
                self.repository.checkpoint(lease,stage,str(video.relative_to(self.settings.project_root)),digest(video.read_bytes()))
                self.repository.pause_boundary(lease)
                total=metadata['duration'];subset=len(scenes)!=len(deliverable.scenes)
                if not subset and not deliverable.target_min_seconds<=total<=deliverable.target_max_seconds:result['warnings'].append(f'{deliverable.deliverable_id}: audio real {total:.2f} s fuera del objetivo {deliverable.target_min_seconds}–{deliverable.target_max_seconds}; no se recortaron palabras.')
                result['outputs'].append({'deliverable_id':deliverable.deliverable_id,'path':str(video.relative_to(self.settings.project_root)),'subtitles':str(subtitle.relative_to(self.settings.project_root)),'duration':total,'preview':task==Task.PREVIEW,'width':next(s['width'] for s in metadata['streams'] if s['codec_type']=='video'),'height':next(s['height'] for s in metadata['streams'] if s['codec_type']=='video'),'provisional_subtitles':approximate,'subset':subset,'streams':metadata['streams']})
        if task==Task.PRODUCE:
            self.repository.start(lease,'quality')
            from app.engine.pipeline.quality import inspect_output
            for output in result['outputs']:
                deliverable=next(d for d in package.deliverables if d.deliverable_id==output['deliverable_id'])
                scene_ids={s.scene_id for s in deliverable.scenes}
                measured=[json.loads(self.settings.safe(item['timing_path']).read_text()) for item in result['scenes'] if item['scene_id'] in scene_ids]
                if len(measured)!=len(deliverable.scenes):raise StudioError('QA: faltan escenas obligatorias.')
                size=(output.get('width',640),output.get('height',360)) if output['preview'] else (deliverable.width,deliverable.height)
                if output['preview']:
                    factor=min(1.,640/max(deliverable.width,deliverable.height))
                    size=(max(128,round(deliverable.width*factor/2)*2),max(128,round(deliverable.height*factor/2)*2))
                output['quality']=inspect_output(self.settings,working,output,size,deliverable.fps,measured,guard,lambda p:self.repository.progress(lease,p))
                output['render_state']='RENDER_COMPLETED'
                output['editorial_state']='EDITORIAL_REVIEW_PENDING'
            quality=self.cache.put('report',digest(encoded(result['outputs'])),encoded(result['outputs']),'.json',{'kind':'quality'})
            self._checkpoint(lease,'quality',quality)
        self.repository.start(lease,'delivery')
        key=digest(encoded(result));entry=self.cache.put('report',key,encoded(result),'.json',{'task':task.value})
        self._checkpoint(lease,'delivery',entry)
        state='waiting_review' if task==Task.SYNCHRONIZE and result['warnings'] else 'completed'
        self.repository.finish(lease,state,result,'Producción local verificada; revisión humana pendiente.' if state=='completed' else 'Hay discrepancias de alineación; se conservan audio y candidatos.')
        return result
