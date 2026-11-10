"""Controles audiovisuales locales; ninguna acción publica contenido."""

import json
import streamlit as st
from app.domain.package_errors import StudioError


from app.presentation.production_monitor import production_monitor


def render_production(studio,project_id,launch,episode_service=None,refresh=None):
    """Configura voz, ritmo y pronunciación como revisión editable por episodio."""
    view=studio.get(project_id);data=studio.editable(project_id)
    st.markdown('**Producción del episodio · largo y hasta tres Shorts · en-US**' if episode_service else '**Motor del video largo · en-US**')
    if view.package.language!='en-US':
        st.info('El original de esta fase requiere en-US.');return
    voices=studio.voices('en-US')
    if not voices:
        st.warning('Bloqueado para nuevas narraciones: Kokoro no tiene voces estadounidenses locales. Las entregas existentes siguen disponibles.')
    with st.form('voice_'+project_id):
        chosen=st.selectbox('Voz estadounidense',voices or ('Sin voz local disponible',),disabled=not bool(voices),index=voices.index(data['voice']['voice']) if data['voice']['voice'] in voices else 0)
        speed=st.slider('Velocidad narrativa',.7,1.2,float(data['voice']['speed']),.01)
        pronunciation=st.text_area('Pronunciaciones (JSON)',json.dumps(data['voice']['pronunciation'],ensure_ascii=False))
        channel_default=st.checkbox('Usar también como voz predeterminada de este canal para nuevos paquetes')
        if st.form_submit_button('Guardar configuración de voz del episodio',disabled=not bool(voices)):
            try:
                studio.save(project_id,data['manifest'],{'voice':chosen,'speed':speed,'pronunciation':json.loads(pronunciation)},view.revision_version)
                if channel_default:studio.repository.set_channel_voice(view.package.channel_id,{'voice':chosen,'speed':speed,'pronunciation':json.loads(pronunciation)})
                st.rerun()
            except (StudioError,ValueError) as exc:st.error(str(exc))
    fps=st.selectbox('FPS de producción',[30,24,25],key='fps_'+project_id)
    provisional=st.checkbox('Permitir subtítulos aproximados identificados cuando falle la alineación',value=True,key='approx_'+project_id)
    short_max=st.number_input('Duración máxima del Short (segundos)',30,180,60,step=5,key='short_max_'+project_id) if episode_service else 60
    confirmed=True if episode_service else st.checkbox('Autorizo producción local para revisión; derechos y publicación permanecen pendientes',key='confirm_'+project_id)
    st.caption('Se produce localmente para revisión editorial. La aprobación de publicación es una acción separada.')
    if st.button('Iniciar producción',disabled=not confirmed or not bool(voices),key='produce_'+project_id):
        try:
            if episode_service:
                from app.presentation.episode_delivery import launch_delivery
                identifier=episode_service.start(project_id,fps=fps,short_max_seconds=short_max,allow_provisional=provisional)
                launch_delivery(episode_service,identifier,launch);st.rerun()
            identifier=studio.produce_long(project_id,fps=fps,allow_provisional=provisional)
            state=next(j['status'] for j in studio.jobs(project_id) if j['job_id']==identifier)
            if state=='queued':
                launch(studio.settings,identifier);st.success('Trabajo encolado; el proceso continúa fuera de Streamlit.')
            else:
                st.info('Esta configuración ya tiene un trabajo en estado '+state+'. Consulta su resultado o los controles de recuperación.')
        except (StudioError,OSError) as exc:st.error(str(exc))
    if episode_service:
        from app.presentation.episode_delivery import render_episode_panel,render_short_sources,render_publication_metadata
        render_short_sources(studio,episode_service,project_id,launch)
        render_publication_metadata(studio,project_id)
        render_episode_panel(studio,episode_service,project_id,launch,refresh)
        if st.checkbox('Ver trabajos y controles por etapa',key='show_jobs_'+project_id):
            production_monitor(studio,project_id,launch,show_outputs=False)
    else:production_monitor(studio,project_id,launch)
