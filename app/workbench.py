"""Entrada visual de importación y producción local; componentes organizados en app/presentation."""

import streamlit as st
from app.bootstrap import create_studio
from app.config import Settings
from app.domain.package_errors import StudioError

def main():
    """Abre importación, producción y entrega con un único contexto de canal."""
    from app.application.package_preparation import PreparePackages
    from app.infrastructure.package_inventory import inventory
    from app.infrastructure.sqlite.package_imports import PackageImports
    from app.presentation.package_preparation import render_packages
    from app.engine.ingestion.zip_reader import ZipReader
    from app.application.package_production import ProducePackages
    from app.infrastructure.sqlite.package_production import ProductionLinks
    from app.infrastructure.local_worker import launch_worker
    from app.presentation.package_production import render_production
    from app.application.episode_delivery import EpisodeDelivery
    from app.infrastructure.sqlite.deliveries import DeliveryStore
    from app.engine.pipeline.delivery import DeliveryAssembler
    from app.presentation.episode_delivery import render_global

    st.set_page_config(page_title='YouTube Studio AI', page_icon='◫', layout='wide')
    st.title('YouTube Studio AI')
    try:
        studio = create_studio(Settings())
        repository = PackageImports(studio.repository.database)
        channels = repository.channels()
        names = {c['channel_id']: c['name'] for c in channels}
        channel = st.sidebar.selectbox('Contexto', [None, *names],
            format_func=lambda value: 'Todos los canales' if value is None else names[value], key='phase1_context')
        service = PreparePackages(studio.settings, repository, ZipReader(require_manifest=False), inventory)
        producer=ProducePackages(repository,studio,ProductionLinks(repository.database))
        delivery_service=EpisodeDelivery(studio,DeliveryStore(repository.database))
        assembler=DeliveryAssembler(studio.settings,studio.repository)
        render_packages(service, channel, producer,delivery_service,launch_worker)
        if channel:
            projects=[p for p in studio.projects() if p['channel_id']==channel]
            if projects:
                by_id={p['project_id']:p for p in projects}
                selected=st.selectbox('Episodio con timeline para producir',list(by_id),format_func=lambda key:by_id[key]['episode_id']+' · '+by_id[key]['title'],key='production_project_'+channel)
                render_production(studio,selected,launch_worker,delivery_service,assembler.refresh)
        else:
            render_global(studio,delivery_service,channels,launch_worker,assembler.refresh,producer,repository)
    except (StudioError, OSError, ValueError, TypeError) as exc:
        st.error(str(exc))
