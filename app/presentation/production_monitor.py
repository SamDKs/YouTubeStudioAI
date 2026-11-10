"""Seguimiento de jobs persistentes compartido por vistas de episodio y canales."""

import json
import streamlit as st

@st.fragment(run_every=5)
def production_monitor(studio,project_id,launch,show_outputs=True):
    """Consulta etapas y progreso real sin ejecutar FFmpeg en Streamlit."""
    for job in studio.jobs(project_id):
        identifier=job['job_id']
        with st.expander(job['task']+' · '+job['status']+' · '+identifier,expanded=True):
            if job['last_error']:st.warning(job['last_error'])
            st.dataframe(studio.queue.steps(identifier),hide_index=True)
            events=studio.events(identifier)
            latest=None
            for event in reversed(events):
                if event['event_type']=='stage':break
                if event['event_type']=='progress':
                    latest=json.loads(event['event_payload']);break
            if latest and job['status']=='running':
                st.progress(min(1.,latest['encoded_seconds']/max(.001,latest['total_seconds'])),text='Última operación informada por FFmpeg')
            if job['status'] in {'running','queued'} and st.button('Pausar en checkpoint',key='pause_'+identifier):
                studio.queue.pause(identifier);st.rerun()
            if job['status']=='paused' and st.button('Reanudar',key='resume_'+identifier):
                studio.queue.resume(identifier);launch(studio.settings,identifier);st.rerun()
            if job['status'] in {'running','queued','paused'} and st.button('Cancelar proceso',key='cancel_'+identifier):
                studio.cancel(identifier);st.rerun()
            if job['status']=='queued' and st.button('Iniciar worker pendiente',key='worker_'+identifier):
                launch(studio.settings,identifier);st.info('Worker iniciado; esperará su turno si otro trabajo está activo.')
            if job['status'] in {'failed','waiting_review','interrupted','canceled'} and st.button('Reintentar desde caché verificada',key='retry_'+identifier):
                studio.retry(identifier);launch(studio.settings,identifier);st.rerun()
            if show_outputs and not job['result'].get('outputs'):
                previews=[p for p in studio.queue.checkpoints(identifier) if p['step_type'].startswith('preview:')]
                if previews and st.checkbox('Ver vista previa ya terminada',key='checkpoint_preview_'+identifier):
                    st.video(studio.result_bytes(project_id,previews[-1]['result_reference'].removeprefix('work-file:')))
            for warning in job['result'].get('warnings',[]):st.warning(warning)
            for index,output in enumerate(job['result'].get('outputs',[]) if show_outputs else []):
                st.caption(('Vista previa' if output['preview'] else 'MP4 para revisión humana')+f" · {output['duration']:.3f} s")
                if output.get('provisional_subtitles'):st.warning('Subtítulos aproximados; revisar sincronización antes de publicar.')
                if st.checkbox('Mostrar video',key=f'watch_{identifier}_{index}'):
                    st.video(studio.result_bytes(project_id,output['path']))
                st.download_button('Descargar MP4',studio.result_bytes(project_id,output['path']),file_name=output['path'].split('/')[-1],key=f'mp4_{identifier}_{index}')
                if output.get('subtitles'):
                    st.download_button('Descargar SRT',studio.result_bytes(project_id,output['subtitles']),file_name=output['subtitles'].split('/')[-1],key=f'srt_{identifier}_{index}')
            with st.expander('Historial de etapas y diagnósticos'):
                st.dataframe(events,hide_index=True)

