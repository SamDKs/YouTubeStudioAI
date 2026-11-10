"""Content/configuration cache with exclusive publication, hashes and no input writes."""

from dataclasses import dataclass
import fcntl
import json
from pathlib import Path

from app.files import atomic_new
from app.domain.package_errors import StorageError
from app.engine.domain.serialization import digest,encoded


@dataclass(frozen=True,slots=True)
class CacheEntry:
    path: Path
    sha256: str
    metadata: dict


class ContentCache:
    def __init__(self,root: Path):self.root=root

    def _path(self,kind: str,key: str,suffix: str) -> Path:
        if kind not in {'audio','timing','render','report'} or len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise StorageError('Identidad de caché inválida.')
        if suffix not in {'.wav','.json','.mp4','.srt'}:raise StorageError('Tipo de caché no permitido.')
        return self.root/kind/key[:2]/(key+suffix)

    def get(self,kind: str,key: str,suffix: str) -> CacheEntry | None:
        path=self._path(kind,key,suffix);receipt=path.with_suffix(path.suffix+'.json')
        if not path.exists() and not receipt.exists():return None
        if not path.is_file() or not receipt.is_file():return None
        try:
            data=json.loads(receipt.read_text());checksum=digest(path.read_bytes())
            if checksum!=data['sha256']:raise StorageError('Caché corrupta: '+path.name+'. No se sobrescribió.')
            return CacheEntry(path,checksum,data['metadata'])
        except (ValueError,KeyError,OSError) as exc:
            if isinstance(exc,StorageError):raise
            raise StorageError('Recibo de caché inválido: '+path.name) from exc

    def put(self,kind: str,key: str,content: bytes,suffix: str,metadata: dict) -> CacheEntry:
        path=self._path(kind,key,suffix);path.parent.mkdir(parents=True,exist_ok=True)
        with path.with_suffix(path.suffix+'.lock').open('a') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
            existing=self.get(kind,key,suffix)
            if existing:return existing
            checksum=digest(content)
            if path.exists():
                if digest(path.read_bytes())!=checksum:raise StorageError('Existe un resultado distinto en esta identidad de caché; requiere revisión.')
            else:atomic_new(path,content)
            atomic_new(path.with_suffix(path.suffix+'.json'),encoded({'sha256':checksum,'metadata':metadata}))
            return CacheEntry(path,checksum,metadata)
