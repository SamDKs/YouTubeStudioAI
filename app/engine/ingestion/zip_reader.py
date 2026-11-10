"""Bounded, independent extraction. Archive entries are data, never programs."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import stat
import tempfile
import unicodedata
import zipfile

from app.domain.package_errors import ContractError
from app.engine.ingestion.adapters import adapt_manifest
from app.engine.ingestion.contract import load_json, relative_path, validate_manifest


@dataclass(frozen=True, slots=True)
class ZipLimits:
    files: int = 500
    compressed_bytes: int = 128*1024*1024
    uncompressed_bytes: int = 512*1024*1024
    file_bytes: int = 128*1024*1024
    expansion_ratio: int = 200


@dataclass(frozen=True, slots=True)
class ValidatedInput:
    root: Path
    manifest: dict
    warnings: tuple[str,...]


class ZipReader:
    def __init__(self, limits: ZipLimits | None = None, *, require_manifest: bool = True):
        """Configura límites comunes y permite inventariar ZIP sin manifiesto."""
        self.limits = limits or ZipLimits()
        self.require_manifest = require_manifest

    def _entries(self, archive):
        """Rechaza rutas ambiguas, enlaces, bombas y extensiones no admitidas."""
        entries=archive.infolist();seen=set();total=0;files=set()
        if len(entries)>self.limits.files:raise ContractError('ZIP','$','demasiados archivos')
        allowed={'.json','.md','.txt','.csv','.srt','.vtt','.png','.jpg','.jpeg','.webp','.mp4','.mov','.wav','.mp3','.aiff','.ogg'}
        for entry in entries:
            name=entry.orig_filename.rstrip('/')
            relative_path(name,'ZIP',entry.orig_filename)
            normalized=unicodedata.normalize('NFC',name).casefold()
            if normalized in seen:raise ContractError('ZIP',name,'ruta duplicada o ambigua por mayúsculas/Unicode')
            seen.add(normalized)
            kind=stat.S_IFMT(entry.external_attr>>16)
            if kind not in {0,stat.S_IFREG,stat.S_IFDIR}:raise ContractError('ZIP',name,'enlace o tipo de entrada peligroso')
            if entry.flag_bits & 1:raise ContractError('ZIP',name,'no se admiten archivos cifrados')
            if not entry.is_dir():
                files.add(name)
                if Path(name).suffix.lower() not in allowed:raise ContractError('ZIP',name,'tipo de archivo no admitido; no se ejecutan scripts del paquete')
            total+=entry.file_size
            if entry.file_size>self.limits.file_bytes or total>self.limits.uncompressed_bytes:raise ContractError('ZIP',name,'límite de tamaño descomprimido superado')
            if entry.file_size>max(1,entry.compress_size)*self.limits.expansion_ratio:raise ContractError('ZIP',name,'expansión de compresión excesiva')
        for name in files:
            if any(parent.as_posix() in files for parent in Path(name).parents if parent.as_posix()!='.'):raise ContractError('ZIP',name,'colisión entre archivo y directorio')
        manifests=[name for name in files if name.split('/')[-1]=='manifest.json' and len(name.split('/'))<=2]
        if not manifests and not self.require_manifest:return entries,''
        if len(manifests)!=1:raise ContractError('ZIP','manifest.json','se necesita un manifiesto en raíz o en una única carpeta contenedora')
        prefix=manifests[0].removesuffix('manifest.json')
        if prefix and any(not name.startswith(prefix) for name in files):raise ContractError('ZIP','$','hay archivos fuera de la carpeta contenedora')
        return entries,prefix

    @contextmanager
    def inspect(self, source: Path, temporary_parent: Path | None = None):
        """Extrae en aislamiento temporal y valida el contrato cuando existe."""
        if source.stat().st_size>self.limits.compressed_bytes:raise ContractError('ZIP','$','archivo comprimido demasiado grande')
        if temporary_parent:temporary_parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='work-import-',dir=temporary_parent) as temporary:
            destination=Path(temporary)
            try:
                with zipfile.ZipFile(source) as archive:
                    entries,prefix=self._entries(archive)
                    for entry in entries:
                        if entry.is_dir():continue
                        target=destination/entry.filename
                        if not target.resolve().is_relative_to(destination.resolve()):raise ContractError('ZIP',entry.filename,'extracción fuera del destino')
                        target.parent.mkdir(parents=True,exist_ok=True)
                        written=0
                        with archive.open(entry) as reader,target.open('xb') as writer:
                            while chunk:=reader.read(1024*1024):
                                written+=len(chunk)
                                if written>entry.file_size or written>self.limits.file_bytes:raise ContractError('ZIP',entry.filename,'tamaño real distinto o excesivo')
                                writer.write(chunk)
                root=destination/prefix
                canonical,warnings=({},())
                if (root/'manifest.json').is_file():
                    canonical,warnings=adapt_manifest(load_json(root/'manifest.json'),root)
                    validate_manifest(canonical,root)
                yield ValidatedInput(root,canonical,warnings)
            except (zipfile.BadZipFile,RuntimeError,OSError,NotImplementedError,EOFError) as exc:
                raise ContractError('ZIP','$','archivo corrupto o extracción imposible; solo se limpió esta importación temporal') from exc
