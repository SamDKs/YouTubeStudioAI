"""One portable location for runtime paths and local tool configuration."""

from dataclasses import dataclass,field
from pathlib import Path
import os


@dataclass(frozen=True,slots=True)
class Settings:
    project_root: Path=field(default_factory=lambda:Path(__file__).resolve().parents[1])
    ffmpeg: str=field(default_factory=lambda:os.environ.get('FFMPEG_PATH','ffmpeg'))
    ffprobe: str=field(default_factory=lambda:os.environ.get('FFPROBE_PATH','ffprobe'))
    fps: int=30

    def __post_init__(self):object.__setattr__(self,'project_root',self.project_root.resolve())

    @property
    def database_path(self):return self.project_root/'data/studio.sqlite3'

    @property
    def work_root(self):return self.project_root/'data/work'

    @property
    def imports_root(self):return self.work_root/'imports'

    @property
    def temporary_root(self):return self.work_root/'temporary'

    @property
    def cache_root(self):return self.work_root/'cache'

    @property
    def exports_root(self):return self.work_root/'exports'

    def safe(self,relative: str) -> Path:
        path=Path(relative)
        if path.is_absolute() or '..' in path.parts:raise ValueError('La ruta debe ser relativa al proyecto.')
        result=(self.project_root/path).resolve()
        if not result.is_relative_to(self.project_root):raise ValueError('La ruta sale del proyecto.')
        return result
