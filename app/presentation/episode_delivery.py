"""Panel de cuatro piezas, entrega descargable y operación multicanal."""

import json
import streamlit as st
from app.domain.delivery import SLOTS
from app.domain.package_errors import StudioError
from app.presentation.production_monitor import production_monitor

LABELS={'long':'Video largo','short_01':'Short 1','short_02':'Short 2','short_03':'Short 3'}


def launch_delivery(service,delivery_id,launch):
    """Inicia únicamente los jobs en cola de una entrega registrada."""
    delivery=next(d for d in service.repository.list() if d['delivery_id']==delivery_id)
    jobs={j['job_id']:j for j in service.studio.jobs(delivery['project_id'])}
    for piece in delivery['pieces']:
        if piece['job_id'] and jobs[piece['job_id']]['status']=='queued':
            launch(service.studio.settings,piece['job_id'])


@st.fragment(run_every=5)
def render_episode_panel(studio,service,project_id,launch,refresh):
    """Muestra las cuatro posiciones, incluso cuando faltan guiones o archivos."""
    try:deliveries=refresh(project_id)
    except (StudioError,ValueError,OSError) as exc:
        st.error('No se pudo actualizar la entrega: '+str(exc));return
    current=studio.get(project_id)
    deliveries=[d for d in deliveries if d['revision_id']==current.revision_id]
    if not deliveries:
        st.info('Inicia la producción para preparar la entrega de esta revisión.')
        for slot in SLOTS:st.caption(LABELS[slot]+' · pendiente de preparación')
        return
    delivery=deliveries[0];identifier=delivery['delivery_id'];report=delivery['report']
    st.subheader('Entrega del episodio')
    st.write('Estado general: **'+delivery['state']+'**')
    st.caption('RENDER_COMPLETED: archivo generado · QA_PASSED: controles técnicos superados · EDITORIAL_REVIEW_PENDING: revisión humana pendiente · APPROVED_FOR_PUBLICATION: aprobación humana registrada, sin subida.')
    pieces={p['slot']:p for p in report.get('pieces',delivery['pieces'])}
    for start in (0,2):
        columns=st.columns(2)
        for column,slot in zip(columns,SLOTS[start:start+2]):
            with column:
                item=pieces.get(slot,{'state':'NEEDS_SCRIPT'});output=item.get('output')
                st.markdown('**'+LABELS[slot]+'** · '+item['state'])
                if item.get('reason'):st.warning(item['reason'])
                if output:
                    try:
                        content=studio.result_bytes(project_id,output['path'])
                        st.video(content)
                        st.caption(f"Duración: {output['duration']:.3f} s · {output['width']}×{output['height']}")
                        st.download_button('Descargar '+LABELS[slot],content,file_name=slot+'_en-US.mp4',key='piece_download_'+identifier+'_'+slot)
                        st.download_button('Descargar subtítulos',studio.result_bytes(project_id,output['subtitles']),file_name=slot+'_en-US.srt',key='piece_srt_'+identifier+'_'+slot)
                    except (StudioError,OSError) as exc:st.error(str(exc))
                if item.get('deliverable_id') and st.button('Volver a generar '+LABELS[slot],key='regenerate_'+identifier+'_'+slot):
                    try:
                        options={k:v for k,v in delivery['configuration'].items() if k!='regenerate'}
                        new=service.start(project_id,regenerate=slot,**options);launch_delivery(service,new,launch);st.rerun()
                    except (StudioError,OSError) as exc:st.error(str(exc))
    if delivery['bundle_path']:
        text='Descargar paquete completo' if report.get('all_four_rendered_and_qa_passed') else 'Descargar paquete parcial disponible'
        try:st.download_button(text,service.bundle_bytes(project_id,identifier),file_name=current.package.episode_id+'_en-US.zip',mime='application/zip',key='bundle_'+identifier)
        except (StudioError,OSError) as exc:st.error(str(exc))
    with st.expander('Reporte de calidad y faltantes'):
        st.json(report)
        st.download_button('Descargar QA JSON',json.dumps(report,ensure_ascii=False,indent=2),file_name='qa_report.json',key='qa_'+identifier)
    blockers=report.get('approval_blockers',[]) or ([] if report.get('all_four_rendered_and_qa_passed') else ['Faltan piezas o verificaciones.'])
    with st.expander('Revisión editorial y aprobación local'):
        for message in blockers:st.warning(message)
        reviewed=st.checkbox('Revisé los cuatro videos, subtítulos, fuentes y derechos',key='reviewed_'+identifier)
        note=st.text_area('Nota de revisión',key='review_note_'+identifier)
        if st.button('Registrar aprobación para publicación',disabled=bool(blockers) or not reviewed or not note.strip(),key='approve_'+identifier):
            try:service.approve(project_id,identifier,note);refresh(project_id);st.rerun()
            except StudioError as exc:st.error(str(exc))
        st.caption('Esta acción registra una aprobación local; no sube ni publica videos.')


def render_short_sources(studio,service,project_id,launch):
    """Permite asociar timelines aprobados o solicitar borradores a un LLM real configurado."""
    view=studio.get(project_id);count=sum(d.kind=='short' for d in view.package.deliverables)
    if count>=3:return
    with st.expander(f'Completar guiones pendientes · {3-count} Short(s)'):
        st.write('Prioridad: guiones del ZIP → timelines aprobados del episodio → borradores de un LLM local configurado.')
        configuration=studio.repository.llm_config(view.package.channel_id)
        if not configuration:st.info('No hay LLM local configurado. Agrega un guion con su timeline y recursos explícitos; no se generará contenido de muestra.')
        if st.button('Solicitar borradores al LLM local',disabled=not bool(configuration),key='draft_shorts_'+project_id):
            try:
                job=studio.request_short_scripts(project_id);launch(studio.settings,job);st.success('Solicitud en cola. Los borradores requieren revisión editorial.')
            except (StudioError,OSError) as exc:st.error(str(exc))
        candidates=[c for c in service.repository.candidates(project_id) if c['state']=='draft']
        choices={c['candidate_id']:c for c in candidates}
        selected=st.selectbox('Origen del timeline', [None,*choices],format_func=lambda key:'Timeline aprobado aportado por mí' if key is None else choices[key]['source']+' · '+key[:8],key='short_origin_'+project_id)
        initial=json.dumps(choices[selected]['content'],indent=2,ensure_ascii=False) if selected else ''
        content=st.text_area('Timeline Short en formato JSON del contrato',value=initial,height=220,key='short_json_'+project_id+'_'+str(selected))
        st.caption('Incluye título, narración propia, escenas, IDs de recursos existentes, rótulos y cierre. El contrato y el ejemplo están documentados en docs/phase3-delivery.md.')
        approved=st.checkbox('Revisé la narración, las fuentes y las asociaciones de recursos de este Short',key='short_approved_'+project_id)
        if st.button('Guardar Short aprobado en el episodio',disabled=not approved or not content.strip(),key='save_short_'+project_id):
            try:
                value=json.loads(content)
                if not isinstance(value,dict):raise ValueError('El timeline debe ser un objeto JSON.')
                service.approve_short(project_id,value,source=choices[selected]['source'] if selected else 'owner_approved')
                if selected:service.repository.mark_candidate_approved(selected,project_id,studio.get(project_id).revision_id)
                st.rerun()
            except (StudioError,ValueError,KeyError,TypeError) as exc:st.error(str(exc))


def render_publication_metadata(studio,project_id):
    """Guarda metadatos proporcionados por el propietario sin atribuirlos a generación automática."""
    data=studio.editable(project_id);meta=data['manifest'].get('publication_metadata',{})
    with st.expander('Metadatos del paquete de entrega'):
        with st.form('metadata_'+project_id):
            description=st.text_area('Descripción en inglés',meta.get('description',''))
            keywords=st.text_input('Keywords en inglés, separadas por comas',', '.join(meta.get('keywords',[])))
            if st.form_submit_button('Guardar metadatos'):
                data['manifest']['publication_metadata']={'description':description,'keywords':[s.strip() for s in keywords.split(',') if s.strip()]}
                try:
                    studio.save(project_id,data['manifest'],data['voice'],data['version']);st.rerun()
                except StudioError as exc:st.error(str(exc))


def render_global(studio,service,channels,launch,refresh,producer=None,imports=None):
    """Ofrece un ciclo multicanal con diagnósticos y controles independientes."""
    def activate_prepared(channel=None):
        """Asocia importaciones válidas antes de iniciar sus trabajos."""
        if not producer or not imports:return
        for item in imports.list(channel):
            if item['state'] in {'FAILED','IMPORTED','VALIDATING'} or not item['report'].get('manifest'):continue
            try:producer.activate(item['import_id'],item['channel_id'])
            except (StudioError,OSError) as exc:st.warning(item['channel_id']+': '+str(exc))
    st.subheader('Producción de todos los canales')
    st.caption('Los trabajos se conservan por canal y se procesan de uno en uno en esta Mac.')
    if st.button('Iniciar ciclo para todos los canales',key='start_all_channels'):
        activate_prepared()
        results=service.start_all()
        for result in results:
            if result.get('error'):st.warning(result['channel_id']+': '+result['error'])
            else:launch_delivery(service,result['delivery_id'],launch)
        if not results:st.info('Todavía no hay episodios activados. Importa y activa un ZIP para comenzar.')
    for channel in channels:
        projects=[p for p in studio.projects() if p['channel_id']==channel['channel_id']]
        with st.expander(channel['name']+' · '+str(len(projects))+' episodio(s)',expanded=bool(projects)):
            if not projects:
                st.info('Sin paquetes activados.')
                if st.button('Iniciar paquetes validados de este canal',key='start_prepared_channel_'+channel['channel_id']):
                    activate_prepared(channel['channel_id'])
                    for project in studio.projects():
                        if project['channel_id']==channel['channel_id']:
                            try:launch_delivery(service,service.start(project['project_id']),launch)
                            except (StudioError,OSError) as exc:st.error(str(exc))
                    st.rerun()
            for project in projects:
                st.write(project['episode_id']+' · '+project['title'])
                if st.button('Iniciar piezas preparadas',key='start_global_'+project['project_id']):
                    try:
                        identifier=service.start(project['project_id']);launch_delivery(service,identifier,launch)
                    except (StudioError,OSError) as exc:st.error(str(exc))
                try:
                    deliveries=refresh(project['project_id'])
                    if deliveries:st.dataframe([{'pieza':p['slot'],'estado':p['state'],'motivo':p.get('reason')} for p in deliveries[0]['report'].get('pieces',[])],hide_index=True)
                except (StudioError,OSError,ValueError) as exc:st.error(str(exc))
                production_monitor(studio,project['project_id'],launch,show_outputs=False)
