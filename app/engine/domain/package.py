"""Internal immutable models. Renderers consume these, never scattered JSON files."""

from dataclasses import dataclass
from enum import StrEnum


class Stage(StrEnum):
    IMPORTED = 'imported'
    VALIDATED = 'validated'
    NARRATION = 'narration'
    SYNCHRONIZATION = 'synchronization'
    PREVIEW = 'preview'
    EXPORT = 'export'


class Task(StrEnum):
    NARRATE = 'narrate'
    SYNCHRONIZE = 'synchronize'
    PREVIEW = 'preview'
    EXPORT = 'export'
    PRODUCE = 'produce_long'
    SHORT_SCRIPTS = 'short_scripts'


@dataclass(frozen=True, slots=True)
class Crop:
    left: float = 0.
    top: float = 0.
    right: float = 1.
    bottom: float = 1.


@dataclass(frozen=True, slots=True)
class Asset:
    asset_id: str
    kind: str
    role: str
    path: str | None
    sha256: str | None
    status: str
    width: int | None
    height: int | None
    origin: str
    generation_status: str
    rights_status: str
    author: str
    license: str
    source_url: str | None
    required_crop: Crop | None


@dataclass(frozen=True, slots=True)
class ScreenText:
    text: str
    kind: str
    position: str
    required: bool


@dataclass(frozen=True, slots=True)
class Motion:
    kind: str
    start_zoom: float
    end_zoom: float


@dataclass(frozen=True, slots=True)
class Scene:
    scene_id: str
    narration: str
    asset_id: str
    estimated_duration_seconds: float
    pause_after_seconds: float
    crop: Crop
    fit: str
    anchor_x: float
    anchor_y: float
    motion: Motion
    transition: str
    transition_seconds: float
    texts: tuple[ScreenText, ...]
    editorial_references: tuple[str, ...]
    video_start_seconds: float = 0.


@dataclass(frozen=True, slots=True)
class Deliverable:
    deliverable_id: str
    title: str
    kind: str
    width: int
    height: int
    fps: int
    target_min_seconds: float
    target_max_seconds: float
    captions_mode: str
    alignment_failure: str
    scenes: tuple[Scene, ...]


@dataclass(frozen=True, slots=True)
class EditorialPackage:
    contract_version: str
    package_version: str
    episode_id: str
    channel_id: str
    title: str
    language: str
    target_market: str
    assets: tuple[Asset, ...]
    deliverables: tuple[Deliverable, ...]
    audio_mix: tuple[dict, ...] = ()

    def asset(self, identifier: str) -> Asset:
        return next(asset for asset in self.assets if asset.asset_id == identifier)


@dataclass(frozen=True, slots=True)
class VoiceConfiguration:
    voice: str
    speed: float = .95
    pronunciation: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Lease:
    job_id: str
    owner: str
    token: int


@dataclass(frozen=True, slots=True)
class MeasuredScene:
    scene_id: str
    narration_seconds: float
    pause_seconds: float
    start_seconds: float
    end_seconds: float


def measure_timeline(scenes: tuple[Scene,...], narration_durations: tuple[float,...]) -> tuple[MeasuredScene,...]:
    import math
    from app.domain.package_errors import StudioError
    if len(scenes) != len(narration_durations): raise StudioError('Faltan duraciones de audio de las escenas.')
    cursor=0.;result=[]
    for scene,duration in zip(scenes,narration_durations):
        if not math.isfinite(duration) or duration<=0:raise StudioError('El audio debe tener una duración real positiva.')
        end=cursor+duration+scene.pause_after_seconds
        result.append(MeasuredScene(scene.scene_id,duration,scene.pause_after_seconds,cursor,end));cursor=end
    return tuple(result)
