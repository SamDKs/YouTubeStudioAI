"""Explicit input migration for the actual legacy ZIP, not a story-specific engine."""

import json
from pathlib import Path
import re

from app.domain.package_errors import ContractError
from app.engine.domain.serialization import digest
from app.engine.ingestion.contract import relative_path

RULES_PATH=Path(__file__).resolve().parents[3]/'schemas/adapters/editorial-production-1.json'


def adapt_manifest(source: dict, root: Path) -> tuple[dict, tuple[str,...]]:
    if 'contract_version' in source:return source,()
    rules=json.loads(RULES_PATH.read_text())
    if source.get('schema')!=rules['source_schema']:raise ContractError('manifest.json','schema','formato desconocido; se necesita el contrato canónico 1.0.0 o un adaptador explícito')
    allowed={'schema','episode_id','title','language','status','fact_check_date','audio_status','video_status','compatibility','assets','formats','supplemental_assets','thumbnail_asset_id'}
    if set(source)-allowed:raise ContractError('manifest.json','$','campos heredados no soportados: '+', '.join(sorted(set(source)-allowed)))
    checksums={p.relative_to(root).as_posix():digest(p.read_bytes()) for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix()!='manifest.json'}
    assets=[];constraints=rules['asset_constraints']
    for a in source['assets']:
        path=relative_path(a['file'],field='assets.file')
        if path not in checksums:raise ContractError(path,'assets.file','recurso declarado que no está en el ZIP')
        if checksums[path]!=a['sha256']:raise ContractError(path,'sha256','checksum original incorrecto')
        if a['status']!='generated_and_present' or a['authentic_archive'] is not False:raise ContractError(path,'status','este adaptador solo admite ilustraciones presentes y declaradas')
        assets.append({'asset_id':a['id'],'kind':'image','role':'thumbnail' if a['role']=='thumbnail' else 'visual',
            'path':path,'sha256':a['sha256'],'status':'available','dimensions':{'width':a['width_px'],'height':a['height_px']},
            'provenance':{'origin':'generated','generation_status':'generated','rights_status':'review_required','author':'Provided by ChatGPT Work','license':a['rights_note'],'source_url':None},
            'constraints':{'required_crop':constraints.get(a['id'],{}).get('required_crop')}})
    reference_ids={ref for f in source['formats'] for s in f['scenes'] for ref in s['sources']}
    research_path='editorial/research_and_sources.md'
    research=(root/research_path).read_text() if (root/research_path).is_file() else ''
    if any(not re.search(r'^- '+re.escape(ref)+r'\b',research,re.M) for ref in reference_ids):raise ContractError(research_path,'references','faltan referencias utilizadas por las escenas')
    deliverables=[]
    for f in source['formats']:
        scenes=[];cursor=0.
        for s in f['scenes']:
            if set(s)-{'id','start_s_estimate','end_s_estimate','asset_id','narration','overlay_disclosure','motion','crop','overlay_text','sources'}:raise ContractError('manifest.json',s['id'],'instrucción heredada no soportada')
            if s['motion'] not in rules['motion_map']:raise ContractError('manifest.json',s['id']+'.motion','movimiento sin traducción explícita')
            if s['start_s_estimate']!=cursor or s['end_s_estimate']<=cursor:raise ContractError('manifest.json',s['id']+'.estimate','tiempos estimados incoherentes')
            duration=s['end_s_estimate']-cursor;cursor=s['end_s_estimate']
            if s['crop'].get('fallback')!='contain_with_blurred_background':raise ContractError('manifest.json',s['id']+'.crop','fallback no soportado')
            texts=[{'text':s['overlay_disclosure'],'kind':'hypothesis' if 'HYPOTHESIS' in s['overlay_disclosure'] else 'disclosure','position':'top','required':True}]
            if s.get('overlay_text'):texts.append({'text':s['overlay_text'],'kind':'explanatory','position':'center','required':True})
            scenes.append({'scene_id':s['id'],'narration':s['narration'],'asset_id':s['asset_id'],'estimated_duration_seconds':duration,'pause_after_seconds':0.,
                'crop':constraints.get(s['asset_id'],{}).get('required_crop',[0.,0.,1.,1.]),'fit':'contain_blur','anchor':{'x':s['crop']['anchor_x'],'y':s['crop']['anchor_y']},
                'motion':rules['motion_map'][s['motion']],'transition':{'kind':'fade','duration_seconds':.3},'texts':texts,'editorial_references':s['sources']})
        deliverables.append({'deliverable_id':f['id'],'kind':f['id'] if f['id'] in {'long','short'} else 'custom','title':source['title'],
            'resolution':{'width':f['width'],'height':f['height']},'fps':f['fps'],'target_duration_seconds':{'min':f['target_duration_s']*.85,'max':f['target_duration_s']*1.15},
            'captions':{'mode':'word','on_alignment_failure':'scene_estimates'},'narration_file':f['narration_file'],'scenes':scenes})
    result={'contract_version':'1.0.0','package_version':'1.0.0','episode_id':source['episode_id'],'channel_id':source['episode_id'].split('-',1)[0],
        'title':source['title'],'language':source['language'],'target_market':'US','assets':assets,'deliverables':deliverables,
        'editorial_references':[{'reference_id':ref,'document_path':research_path,'url':None} for ref in sorted(reference_ids)],'checksums':checksums}
    warnings=['Adaptador editorial-production/1.0 aplicado; las estimaciones no son tiempos finales.',
        'Solo las imágenes tenían hashes originales; los hashes del resto se calcularon localmente, sin afirmar autenticidad del remitente.',
        'No se incluyeron assets_manifest.json, long_timeline.json, short_timeline.json ni CODEX_IMPORT.md.',
        'Recorte obligatorio de sala incorporado desde la decisión explícita del propietario; no se atribuye a un Markdown ausente.',
        'La alineación fallida permite subtítulos provisionales identificados; revisión humana antes de una exportación final.']
    return result,tuple(warnings)
