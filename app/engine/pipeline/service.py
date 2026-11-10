"""Interface use cases; editing changes revisions, never the imported package."""

import copy
from dataclasses import dataclass
import json
import math
from pathlib import Path

from app.domain.package_errors import StudioError
from app.engine.domain.package import EditorialPackage,Task
from app.engine.domain.serialization import digest
from app.engine.ingestion.contract import validate_manifest
from app.engine.pipeline.plan import ENGINE_VERSION,production_steps,select_scenes


@dataclass(frozen=True,slots=True)
class ProjectView:
    project_id: str
    revision_id: str
    revision_version: int
    stage: str
    package: EditorialPackage
    voice: dict
    warnings: tuple[str,...]


class WorkStudio:
    def __init__(self,settings,repository,queue,importer,speech):
        self.settings,self.repository,self.queue,self.importer,self.speech=settings,repository,queue,importer,speech

    def import_zip(self,path: Path) -> str:return self.importer.import_zip(path)

    def projects(self) -> tuple[dict,...]:return self.repository.projects()

    def get(self,project_id: str) -> ProjectView:
        value=self.repository.project(project_id);revision=value['revision']
        return ProjectView(project_id,revision['revision_id'],revision['version'],value['stage'],validate_manifest(revision['manifest']),revision['voice'],tuple(value['warnings']))

    def editable(self,project_id: str) -> dict:return copy.deepcopy(self.repository.project(project_id)['revision'])

    def voices(self,language: str) -> tuple[str,...]:return self.speech.voices(language)

    def save(self,project_id: str,manifest: dict,voice: dict,expected: int,timing_overrides: dict | None=None) -> None:
        package=validate_manifest(manifest);current=self.repository.project(project_id)
        original=json.loads(current['canonical_manifest']);prior=current['revision']
        for key in ('episode_id','channel_id','language','checksums','editorial_references'):
            if manifest[key]!=original[key]:raise StudioError('La identidad, idioma y referencias del paquete original no se reescriben; importa otra variante.')
        assets={a['asset_id']:a for a in original['assets']}
        if set(assets)!={a['asset_id'] for a in manifest['assets']}:raise StudioError('Los recursos de entrada son inmutables; puedes seleccionar los ya incluidos.')
        for asset in manifest['assets']:
            for key in ('path','sha256','constraints','status','dimensions'):
                if asset[key]!=assets[asset['asset_id']][key]:raise StudioError('No se puede relajar el recorte obligatorio ni modificar un archivo de entrada.')
        required={s['scene_id']:{(t['text'],t['kind']) for t in s['texts'] if t['required']} for d in original['deliverables'] for s in d['scenes']}
        for d in manifest['deliverables']:
            for s in d['scenes']:
                if required.get(s['scene_id'],set())-{(t['text'],t['kind']) for t in s['texts'] if t['required']}:raise StudioError('Los rótulos editoriales obligatorios deben permanecer visibles.')
        if set(voice)!={'voice','speed','pronunciation'} or voice['voice'] not in self.voices(package.language):raise StudioError('Selecciona una voz local instalada y compatible con el idioma.')
        if not isinstance(voice['speed'],(int,float)) or not math.isfinite(voice['speed']) or not .7<=voice['speed']<=1.2:raise StudioError('Velocidad de voz fuera de rango.')
        if not isinstance(voice['pronunciation'],dict) or len(voice['pronunciation'])>100 or any(not isinstance(k,str) or not isinstance(v,str) or not k or not v or len(v)>200 for k,v in voice['pronunciation'].items()):raise StudioError('Diccionario de pronunciación inválido.')
        overrides=copy.deepcopy(timing_overrides if timing_overrides is not None else prior.get('timing_overrides',{}))
        old_scenes={s['scene_id']:s for d in prior['manifest']['deliverables'] for s in d['scenes']}
        for deliverable in manifest['deliverables']:
            for scene in deliverable['scenes']:
                old=old_scenes.get(scene['scene_id'],{})
                if voice!=prior['voice'] or any(scene.get(key)!=old.get(key) for key in ('narration','pause_after_seconds')):overrides.pop(scene['scene_id'],None)
        self.repository.save_revision(project_id,manifest,voice,expected,overrides)

    # Congela la selección y deriva la producción automática al perfil del largo.
    def enqueue(self,project_id: str,task: Task,deliverables: tuple[str,...],scene_ids: tuple[str,...]=(),*,confirmed: bool,allow_provisional: bool=False) -> str:
        if not confirmed:raise StudioError('Confirma los entregables y la ejecución local.')
        project=self.get(project_id)
        if task==Task.PRODUCE:
            longs=tuple(d.deliverable_id for d in project.package.deliverables if d.kind=='long')
            if tuple(deliverables)!=longs or scene_ids:raise StudioError('La producción automática admite solo el largo completo.')
            return self.produce_long(project_id,allow_provisional=allow_provisional)
        selection=select_scenes(project.package,deliverables,scene_ids)
        if task!=Task.PREVIEW and scene_ids:raise StudioError('La selección parcial se utiliza en previsualización; la exportación produce entregables completos.')
        for d in project.package.deliverables:
            for scene in d.scenes:
                if scene.scene_id not in selection.get(d.deliverable_id,[]):continue
                asset=project.package.asset(scene.asset_id)
                if task in {Task.PREVIEW,Task.EXPORT} and asset.status!='available':raise StudioError('El recurso '+asset.asset_id+' está pendiente; no existe para producir esta escena.')
        return self.queue.enqueue(project_id,project.revision_id,task,selection,production_steps(task,selection),
            {'engine_version':ENGINE_VERSION,'preview':task==Task.PREVIEW,'allow_provisional':allow_provisional,'paid_api_calls':0})

    def jobs(self,project_id: str) -> tuple[dict,...]:return self.queue.jobs(project_id)

    def events(self,job_id: str) -> tuple[dict,...]:return self.queue.events(job_id)

    def cancel(self,job_id: str):self.queue.cancel(job_id)

    def retry(self,job_id: str):self.queue.retry(job_id)

    def asset_bytes(self,project_id: str,asset_id: str) -> bytes:
        project=self.get(project_id);asset=project.package.asset(asset_id)
        if asset.status!='available':raise StudioError('El recurso no está disponible.')
        root=self.settings.safe(self.repository.project(project_id)['import_relative_path'])/'input'
        path=(root/asset.path).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():raise StudioError('El recurso falta o sale del paquete.')
        data=path.read_bytes()
        if digest(data)!=asset.sha256:raise StudioError('El recurso cambió respecto al paquete importado.')
        return data

    # Restringe las lecturas a entregas o checkpoints del propio proyecto.
    def result_bytes(self,project_id: str,path: str) -> bytes:
        allowed=set()
        for job in self.jobs(project_id):
            for output in job['result'].get('outputs',[]):allowed.add(output['path']);allowed.update([output['subtitles']] if output.get('subtitles') else [])
            for scene in job['result'].get('scenes',[]):allowed.update(scene.get(key) for key in ('audio_path','timing_path') if scene.get(key))
            allowed.update(c['result_reference'].removeprefix('work-file:') for c in self.queue.checkpoints(job['job_id']))
        if path not in allowed:raise StudioError('El resultado no pertenece a este proyecto.')
        return self.settings.safe(path).read_bytes()

    def scene_results(self,project_id: str) -> dict:
        current=self.get(project_id);result={}
        for job in self.jobs(project_id):
            if job['revision_id']!=current.revision_id:continue
            for item in self.queue.checkpoints(job['job_id']):
                parts=item['step_type'].split(':')
                if len(parts)!=3 or parts[0] not in {'audio','timing'}:continue
                kind,_,scene=parts;entry=result.setdefault(scene,{})
                if kind in entry:continue
                path=item['result_reference'].removeprefix('work-file:')
                content=self.settings.safe(path).read_bytes()
                if digest(content)!=item['integrity_hash']:raise StudioError('Un resultado de escena cambió; no se reutilizó.')
                entry[kind]={'path':path,'sha256':item['integrity_hash']}
                if kind=='timing':entry[kind]['data']=json.loads(content)
        return result




    def produce_long(self,project_id,*,fps=30,allow_provisional=True,review_only=True):
        """Encola un largo completo con preview y perfil 1080p; no produce Shorts."""
        project=self.get(project_id)
        if project.package.language!='en-US':raise StudioError('Esta fase produce el original en-US.')
        longs=tuple(d for d in project.package.deliverables if d.kind=='long')
        if len(longs)!=1:raise StudioError('Se requiere exactamente un timeline largo explícito.')
        if fps not in {24,25,30}:raise StudioError('Selecciona 24, 25 o 30 FPS.')
        for scene in longs[0].scenes:
            asset=project.package.asset(scene.asset_id)
            if asset.status!='available' or asset.rights_status=='prohibited':raise StudioError('Falta un recurso permitido de la escena '+scene.scene_id)
        if not self.voices('en-US'):raise StudioError('Bloqueado: no hay voz estadounidense local instalada.')
        selection=select_scenes(project.package,(longs[0].deliverable_id,))
        configuration={'engine_version':'phase2-long-3-cfr','preview':False,'allow_provisional':allow_provisional,'review_only':review_only,'horizontal_profile':True,'fps':fps,'paid_api_calls':0}
        return self.queue.enqueue(project_id,project.revision_id,Task.PRODUCE,selection,production_steps(Task.PRODUCE,selection),configuration)

    def produce_piece(self,project_id,deliverable_id,*,fps=30,short_max_seconds=60,review_only=True,allow_provisional=True,regeneration=None):
        """Encola una pieza autónoma con voz, captions y QA propios; aísla los fallos."""
        project=self.get(project_id)
        if project.package.language!='en-US':raise StudioError('Se requiere narración en-US.')
        if fps not in {24,25,30} or not 30<=short_max_seconds<=180:raise StudioError('Perfil inválido: 24/25/30 FPS y límite Short entre 30 y 180 s.')
        d=next((d for d in project.package.deliverables if d.deliverable_id==deliverable_id),None)
        if not d or d.kind not in {'long','short'}:raise StudioError('Falta el timeline de la pieza.')
        for scene in d.scenes:
            asset=project.package.asset(scene.asset_id)
            if asset.status!='available' or asset.rights_status=='prohibited':raise StudioError('NEEDS_ASSETS: recurso no utilizable en '+scene.scene_id)
            if not review_only and asset.rights_status!='allowed':raise StudioError('NEEDS_RIGHTS: revisar derechos de '+asset.asset_id)
        if not self.voices('en-US'):raise StudioError('BLOCKED_TTS: no hay voces estadounidenses locales.')
        selection=select_scenes(project.package,(deliverable_id,))
        configuration={'engine_version':'phase3-pieces-1','preview':False,'episode_piece':True,'fps':fps,
                       'short_max_seconds':short_max_seconds,'review_only':review_only,'allow_provisional':allow_provisional,
                       'regeneration':regeneration,'paid_api_calls':0}
        return self.queue.enqueue(project_id,project.revision_id,Task.PRODUCE,selection,production_steps(Task.PRODUCE,selection),configuration)


    def validate_edit(self,manifest):
        """Permite comprobar un plan propuesto antes de guardar una revisión."""
        return validate_manifest(manifest)

    def request_short_scripts(self,project_id):
        """Solicita borradores a llama.cpp solo si está configurado; nunca sustituye por API paga."""
        project=self.get(project_id);configuration=self.repository.llm_config(project.package.channel_id)
        if not configuration:raise StudioError('NEEDS_SCRIPT: no hay LLM local configurado. Importa guiones Short o agrega timelines aprobados.')
        if sum(d.kind=='short' for d in project.package.deliverables)>=3:raise StudioError('Ya existen tres Shorts.')
        return self.queue.enqueue(project_id,project.revision_id,Task.SHORT_SCRIPTS,{},('short_scripts','delivery'),{'local_llm':configuration,'paid_api_calls':0})
