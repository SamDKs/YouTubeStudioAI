"""Borradores mediante el conector local existente; aprobación humana posterior."""

import copy
import json
from app.infrastructure.media.local_language import LocalLanguageModel
from app.infrastructure.sqlite.deliveries import DeliveryStore
from app.engine.domain.serialization import digest,encoded
from app.domain.package_errors import NeedsReview
from app.engine.ingestion.contract import validate_manifest
from app.domain.delivery import piece_plan


def generate_short_drafts(executor,lease,context,guard):
    """Usa investigación suministrada y recursos reales; valida la respuesta estructural."""
    manifest=context['manifest'];existing=sum(d['kind']=='short' for d in manifest['deliverables']);count=3-existing
    if count<=0:raise NeedsReview('No faltan guiones Short.')
    root=executor.settings.safe(context['import_relative_path'])/'input';research=[]
    for ref in manifest['editorial_references']:
        path=ref.get('document_path')
        if path and path in manifest['checksums']:
            source=root/path
            if digest(source.read_bytes())!=manifest['checksums'][path]:raise NeedsReview('La investigación cambió desde la importación.')
            research.append(source.read_text()[:20000])
    if not research:raise NeedsReview('Falta investigación trazable para generar nuevos guiones.')
    config=context['configuration']['local_llm'];executor.repository.start(lease,'short_scripts');guard()
    editorial=''
    with executor.repository.database.connection(read_only=True) as c:
        row=c.execute('SELECT * FROM channel_storage WHERE channel_id=?',(manifest['channel_id'],)).fetchone()
        if row:
            path=executor.settings.safe(row[2])
            if path.is_file():editorial=path.read_text()[:20000]
    prompt=('Return ONLY JSON {"shorts": [canonical deliverable objects]}. Write '+str(count)+' distinct standalone US-English Shorts, each with a sourced hook, development and conclusion. '
            'Use kind short, unique deliverable and scene IDs, narration_file null, 1080x1920, 30 fps, target 30–60 seconds. Do not copy excerpts of the long. '
            'Use only supplied asset IDs and references; preserve required disclosures/crops. This is an unapproved draft. Canonical example and constraints: '+encoded(manifest).decode())
    try:
        response=LocalLanguageModel(config.get('base_url','http://127.0.0.1:8080')).draft(config['model'],manifest['title'],'\n\n'.join(research),editorial+'\n'+prompt,language='en-US')
    except Exception as exc:
        raise NeedsReview('El LLM local no produjo borradores: '+str(exc)) from exc
    guard();text=response['text'].strip()
    if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
    try:shorts=json.loads(text)['shorts']
    except (ValueError,KeyError,TypeError):raise NeedsReview('El LLM respondió sin timelines JSON utilizables; no se declararon generados.') from None
    if not isinstance(shorts,list) or len(shorts)!=count:raise NeedsReview('El LLM no devolvió la cantidad pendiente de guiones.')
    candidate=copy.deepcopy(manifest);candidate['deliverables']+=shorts;package=validate_manifest(candidate)
    if any(p['reason'] for p in piece_plan(package)):raise NeedsReview('Los borradores contienen narraciones repetidas o faltantes; revisa el enfoque editorial.')
    if any(d.get('kind')!='short' for d in shorts):raise NeedsReview('El modelo no devolvió Shorts independientes.')
    store=DeliveryStore(executor.repository.database)
    ids=[store.candidate(context['project_id'],'llama_cpp:'+config['model'],d) for d in shorts]
    result={'project_id':context['project_id'],'draft_candidates':ids,'editorial_review':'pending','paid_api_calls':0,'provider':'llama_cpp','model':config['model']}
    entry=executor.cache.put('report',digest(encoded(result)),encoded(result),'.json',{'kind':'short_drafts'})
    executor._checkpoint(lease,'short_scripts',entry);executor.repository.start(lease,'delivery');executor._checkpoint(lease,'delivery',entry)
    executor.repository.finish(lease,'waiting_review',result,'Borradores reales guardados; verifica fuentes y aprueba sus timelines antes de producir.')
    return result
