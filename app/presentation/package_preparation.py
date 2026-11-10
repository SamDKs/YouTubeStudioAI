"""Carga y revisión de paquetes bajo un único contexto de canal."""

from uuid import uuid4
import streamlit as st
from app.domain.package_errors import StudioError


def render_packages(service, channel, producer=None,episode_service=None,launch=None):
    """Muestra importaciones globales o permite importar y preparar en un canal."""
    st.subheader('Producción audiovisual')
    st.caption('Importa el guion largo, hasta tres guiones Short independientes y sus recursos. Los faltantes se muestran por pieza.')
    repository = service.repository
    if channel:
        automatic=False
        if episode_service:
            key='auto_zip_'+channel
            if key not in st.session_state:st.session_state[key]=episode_service.repository.auto_enabled(channel)
            automatic=st.checkbox('Producir automáticamente después de validar el ZIP',key=key,
                on_change=lambda:episode_service.repository.set_auto(channel,st.session_state[key]))
            if automatic:st.caption('Solo se encolan las piezas con guion, recursos y derechos resueltos; los demás faltantes quedan visibles.')
        uploaded = st.file_uploader('Cargar paquete ZIP', type=['zip'], key='package_zip_'+channel)
        if uploaded and st.button('Validar e importar', key='phase1_import'):
            if uploaded.size > service.reader.limits.compressed_bytes:
                st.error('El ZIP supera el límite configurado.')
            else:
                temporary = service.settings.temporary_root
                temporary.mkdir(parents=True, exist_ok=True)
                path = temporary / (str(uuid4())+'.zip')
                try:
                    path.write_bytes(uploaded.getvalue())
                    with st.spinner('Validando contenido y metadatos…'):
                        import_id=service.import_zip(path, channel, uploaded.name)
                    if automatic and producer and episode_service:
                        from app.presentation.episode_delivery import launch_delivery
                        project=producer.activate(import_id,channel)
                        delivery=episode_service.start(project,review_only=False)
                        launch_delivery(episode_service,delivery,launch)
                        st.success('Validación terminada; consulta el estado real de cada pieza en la entrega.')
                except (StudioError, OSError, ValueError) as exc:
                    st.error(str(exc))
                finally:
                    path.unlink(missing_ok=True)
    else:
        st.info('Selecciona un canal en Contexto para cargar un paquete. Aquí puedes consultar todos.')
    jobs = repository.jobs(channel)
    if jobs:
        with st.expander('Trabajos existentes por canal (consulta)'):
            st.dataframe(jobs, hide_index=True)
    rows = repository.list(channel)
    if not rows:
        st.info('Todavía no hay importaciones en este contexto.')
        return
    for row in rows:
        report = row['report']
        with st.expander(row['channel_id']+' · '+report.get('title', row['original_name'])+' · '+row['state']):
            st.caption(report.get('episode_id', row['episode_id'])+' · '+report.get('language', 'en-US')+' · '+row['import_id'])
            st.write('SHA-256: '+row['zip_sha256'])
            if report.get('files'):
                st.dataframe(report['files'], hide_index=True)
            for message in report.get('errors', []):
                st.error(message)
            for message in report.get('warnings', []) + report.get('missing', []):
                st.warning(message)
            if channel and row['state'] not in {'FAILED', 'VALIDATING', 'IMPORTED'}:
                scripts = repository.scripts(channel)
                script = st.selectbox('Asociar guion aprobado (opcional)', [None]+[s['script_id'] for s in scripts], key='script_'+row['import_id'])
                if st.button('Preparar producción', key='prepare_'+row['import_id']):
                    try:
                        service.prepare(row['import_id'], channel, script)
                        st.rerun()
                    except StudioError as exc:
                        st.error(str(exc))
            if channel and producer and report.get('manifest') and row['state'] not in {'FAILED','VALIDATING','IMPORTED'}:
                if st.button('Activar timeline en el motor audiovisual',key='activate_'+row['import_id']):
                    try:
                        producer.activate(row['import_id'],channel);st.rerun()
                    except (StudioError,OSError) as exc:st.error(str(exc))
            st.dataframe(repository.events(row['import_id']), hide_index=True)
    st.caption('La importación conserva los originales. El motor produce las piezas disponibles y conserva sus faltantes; no publica.')
