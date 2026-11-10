"""Publicación exclusiva de archivos: jamás reemplaza un recurso del usuario."""

import os
import ctypes
import hashlib
from pathlib import Path
from uuid import uuid4


def atomic_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name('.' + uuid4().hex + '.tmp')
    try:
        with staging.open('xb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.link(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def clone_new(source: Path, target: Path, checksum: str) -> bool:
    """Use macOS copy-on-write when supported, preserving independent immutable files."""
    library=ctypes.CDLL(None,use_errno=True)
    operation=getattr(library,'clonefile',None)
    if operation is None:return False
    operation.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint32]
    operation.restype=ctypes.c_int
    target.parent.mkdir(parents=True,exist_ok=True)
    staging=target.with_name('.'+uuid4().hex+'.clone.tmp')
    try:
        if operation(os.fsencode(source),os.fsencode(staging),0)!=0:return False
        if hashlib.sha256(staging.read_bytes()).hexdigest()!=checksum:raise ValueError('El recurso cambió durante su reutilización.')
        os.link(staging,target)
        return True
    finally:staging.unlink(missing_ok=True)
