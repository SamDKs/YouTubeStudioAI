"""Inventario de entradas validadas con Pillow y ffprobe, sin servicios externos."""

from PIL import Image
from app.domain.package_errors import StudioError
from app.engine.domain.serialization import digest
from app.engine.rendering.process import probe_path

IMAGE_FORMATS = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.webp': 'WEBP'}
MEDIA_FORMATS = {'.mp4': {'mov,mp4,m4a,3gp,3g2,mj2'}, '.mov': {'mov,mp4,m4a,3gp,3g2,mj2'},
                 '.wav': {'wav'}, '.mp3': {'mp3'}, '.ogg': {'ogg'}, '.aiff': {'aiff'}}


def inventory(root, ffprobe='ffprobe'):
    """Conserva rutas originales y comprueba tipos reales y metadatos multimedia."""
    result = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        row = {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
               'sha256': digest(path.read_bytes()), 'kind': 'document'}
        if suffix in IMAGE_FORMATS:
            with Image.open(path) as image:
                if image.format != IMAGE_FORMATS[suffix] or image.width * image.height > 30_000_000:
                    raise StudioError('Formato o tamaño de imagen inválido: ' + row['path'])
                row.update(kind='image', width=image.width, height=image.height,
                           aspect=image.width / image.height)
                image.verify()
        elif suffix in MEDIA_FORMATS:
            data = probe_path(path, ffprobe)
            container = data['container']
            if container not in MEDIA_FORMATS[suffix]:
                raise StudioError('Extensión distinta del contenedor: ' + row['path'])
            video = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            if suffix in {'.mp4', '.mov'} and not video:
                raise StudioError('El clip no contiene video: ' + row['path'])
            row.update(kind='video' if video else 'audio', duration=data['duration'],
                       codecs=[s.get('codec_name') for s in data['streams']],
                       has_audio=any(s['codec_type'] == 'audio' for s in data['streams']))
            if video:
                row.update(width=video['width'], height=video['height'], aspect=video['width']/video['height'])
        else:
            text = path.read_text(encoding='utf-8')
            if '\x00' in text or text.startswith(('MZ', '#!', '\x7fELF')):
                raise StudioError('Documento con contenido ejecutable o binario: ' + row['path'])
        result.append(row)
    if not result:
        raise StudioError('El ZIP no contiene archivos.')
    return result
