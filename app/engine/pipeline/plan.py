"""One pipeline definition for any imported deliverable, channel or episode."""

from app.domain.package_errors import StudioError
from app.engine.domain.package import EditorialPackage,Task

ENGINE_VERSION='work-engine-1.0.0'


def select_scenes(package: EditorialPackage,deliverable_ids: tuple[str,...],scene_ids: tuple[str,...]=()) -> dict[str,list[str]]:
    available={d.deliverable_id:d for d in package.deliverables}
    if not deliverable_ids or set(deliverable_ids)-set(available):raise StudioError('Selecciona entregables existentes del paquete.')
    ids={s.scene_id for identifier in deliverable_ids for s in available[identifier].scenes}
    if scene_ids and set(scene_ids)-ids:raise StudioError('La escena no pertenece a los entregables seleccionados.')
    return {identifier:[s.scene_id for s in available[identifier].scenes if not scene_ids or s.scene_id in scene_ids]
        for identifier in deliverable_ids if not scene_ids or any(s.scene_id in scene_ids for s in available[identifier].scenes)}


def production_steps(task: Task,selection: dict[str,list[str]]) -> tuple[str,...]:
    result=[]
    for deliverable,scenes in selection.items():
        for scene in scenes:
            result.append(f'audio:{deliverable}:{scene}')
            if task!=Task.NARRATE:result.append(f'timing:{deliverable}:{scene}')
        if task==Task.PRODUCE:result.append('preview:'+deliverable)
        if task in {Task.PREVIEW,Task.EXPORT,Task.PRODUCE}:result.append('render:'+deliverable)
    if task==Task.PRODUCE:result.append('quality')
    result.append('delivery')
    return tuple(result)
