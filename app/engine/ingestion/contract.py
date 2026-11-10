"""One canonical schema plus cross-file semantics; no executable editorial instructions."""

import json
from pathlib import Path, PurePosixPath
import re
import unicodedata

from jsonschema import Draft202012Validator
from PIL import Image

from app.domain.package_errors import ContractError
from app.engine.domain.package import Asset, Crop, Deliverable, EditorialPackage, Motion, Scene, ScreenText
from app.engine.domain.serialization import digest

SCHEMA_PATH=Path(__file__).resolve().parents[3]/'schemas/editorial-package-1.0.0.schema.json'
CONTRACT_VERSION='1.0.0'


def relative_path(value: str, file: str='manifest.json', field: str='path') -> str:
    if not isinstance(value,str) or not value or '\\' in value or ':' in value or '\x00' in value:
        raise ContractError(file,field,'usa una ruta POSIX relativa, sin barras inversas ni unidades')
    path=PurePosixPath(value)
    if path.is_absolute() or any(part in {'','..','.'} for part in value.split('/')):
        raise ContractError(file,field,'ruta absoluta o traversal no permitido')
    if any(part.endswith(('.', ' ')) for part in path.parts):raise ContractError(file,field,'nombre de archivo no portable')
    return str(path)


def load_json(path: Path) -> dict:
    if path.stat().st_size>2*1024*1024:raise ContractError(path.name,'$','JSON demasiado grande')
    try:
        def reject(value):raise ValueError(value)
        return json.loads(path.read_text(encoding='utf-8'),parse_constant=reject,object_pairs_hook=_unique_keys)
    except (ValueError,UnicodeError,RecursionError) as exc:raise ContractError(path.name,'$','JSON inválido, claves repetidas o números no finitos') from exc


def _unique_keys(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate key')
        result[key]=value
    return result


def _crop(value,field):
    if value is None:return None
    crop=Crop(*value)
    if crop.left>=crop.right or crop.top>=crop.bottom:raise ContractError('manifest.json',field,'rectángulo sin área positiva')
    return crop


def validate_manifest(value: dict, root: Path | None=None) -> EditorialPackage:
    version=value.get('contract_version','') if isinstance(value,dict) else ''
    if version!=CONTRACT_VERSION:raise ContractError('manifest.json','contract_version',f'versión {version!r} incompatible; se admite {CONTRACT_VERSION}; no se degrada silenciosamente')
    validator=Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    errors=sorted(validator.iter_errors(value),key=lambda error:str(list(error.absolute_path)))
    if errors:
        error=errors[0];field='.'.join(map(str,error.absolute_path)) or '$'
        raise ContractError('manifest.json',field,error.message)
    asset_ids=[a['asset_id'] for a in value['assets']];reference_ids=[r['reference_id'] for r in value['editorial_references']]
    deliverable_ids=[d['deliverable_id'] for d in value['deliverables']]
    for field,ids in (('assets',asset_ids),('editorial_references',reference_ids),('deliverables',deliverable_ids)):
        if len(set(ids))!=len(ids):raise ContractError('manifest.json',field,'identificadores duplicados')
    assets=[];scene_ids=set()
    for index,a in enumerate(value['assets']):
        field=f'assets.{index}';region=_crop(a['constraints']['required_crop'],field+'.constraints.required_crop')
        if a['status']=='available':
            if not a['path'] or not a['sha256']:raise ContractError('manifest.json',field,'un recurso disponible requiere ruta y checksum')
            path=relative_path(a['path'],field=field+'.path')
            if value['checksums'].get(path)!=a['sha256']:raise ContractError('manifest.json',field+'.sha256','no coincide con checksums')
            if a['kind'] in {'image','video'} and a['dimensions'] is None:raise ContractError('manifest.json',field+'.dimensions','faltan dimensiones visuales')
        elif a['path'] is not None or a['sha256'] is not None:raise ContractError('manifest.json',field,'un recurso pendiente/no disponible debe tener path y sha256 nulos')
        p=a['provenance'];dims=a['dimensions'] or {}
        assets.append(Asset(a['asset_id'],a['kind'],a['role'],a['path'],a['sha256'],a['status'],dims.get('width'),dims.get('height'),p['origin'],p['generation_status'],p['rights_status'],p['author'],p['license'],p['source_url'],region))
    by_id={a.asset_id:a for a in assets};deliverables=[]
    for index,d in enumerate(value['deliverables']):
        if d['target_duration_seconds']['min']>d['target_duration_seconds']['max']:raise ContractError('manifest.json',f'deliverables.{index}.target_duration_seconds','rango invertido')
        scenes=[]
        for number,s in enumerate(d['scenes']):
            field=f'deliverables.{index}.scenes.{number}'
            if s['scene_id'] in scene_ids:raise ContractError('manifest.json',field+'.scene_id','el ID debe ser único en todo el paquete')
            scene_ids.add(s['scene_id'])
            if s['asset_id'] not in by_id:raise ContractError('manifest.json',field+'.asset_id','recurso inexistente')
            asset=by_id[s['asset_id']]
            if asset.kind not in {'image','video'}:raise ContractError('manifest.json',field+'.asset_id','la escena requiere un recurso visual')
            if set(s['editorial_references'])-set(reference_ids):raise ContractError('manifest.json',field+'.editorial_references','referencia editorial inexistente')
            crop=_crop(s['crop'],field+'.crop');required=asset.required_crop
            if required and not (crop.left>=required.left and crop.top>=required.top and crop.right<=required.right and crop.bottom<=required.bottom):raise ContractError('manifest.json',field+'.crop','debe respetar el recorte obligatorio del recurso')
            disclosures=[t for t in s['texts'] if t['kind'] in {'disclosure','hypothesis'} and t['required']]
            if asset.origin=='generated' and not disclosures:raise ContractError('manifest.json',field+'.texts','un visual generado requiere un rótulo editorial visible y obligatorio')
            if s['transition']['kind']=='cut' and s['transition']['duration_seconds']!=0:raise ContractError('manifest.json',field+'.transition','un corte tiene duración cero')
            scenes.append(Scene(s['scene_id'],s['narration'],s['asset_id'],s['estimated_duration_seconds'],s['pause_after_seconds'],crop,s['fit'],s['anchor']['x'],s['anchor']['y'],Motion(**s['motion']),s['transition']['kind'],s['transition']['duration_seconds'],tuple(ScreenText(**t) for t in s['texts']),tuple(s['editorial_references']),s.get('video_start_seconds',0.)))
        deliverables.append(Deliverable(d['deliverable_id'],d['title'],d['kind'],d['resolution']['width'],d['resolution']['height'],d['fps'],d['target_duration_seconds']['min'],d['target_duration_seconds']['max'],d['captions']['mode'],d['captions']['on_alignment_failure'],tuple(scenes)))
    for path in value['checksums']:relative_path(path,field='checksums')
    for ref in value['editorial_references']:
        if ref['document_path'] and ref['document_path'] not in value['checksums']:raise ContractError('manifest.json','editorial_references','documento sin checksum')
    for track in value.get('audio_mix',[]):
        asset=by_id.get(track['asset_id'])
        if not asset or asset.kind!='audio' or asset.status!='available':raise ContractError('manifest.json','audio_mix','requiere un recurso de audio disponible')
        if track['deliverable_id'] not in deliverable_ids:raise ContractError('manifest.json','audio_mix','entregable desconocido')
        if asset.rights_status!='allowed':raise ContractError('manifest.json','audio_mix','música/efectos requieren derechos permitidos explícitos')
    if root is not None:validate_files(value,root)
    return EditorialPackage(value['contract_version'],value['package_version'],value['episode_id'],value['channel_id'],value['title'],value['language'],value['target_market'],tuple(assets),tuple(deliverables),tuple(value.get('audio_mix',[])))


def validate_files(value: dict, root: Path) -> None:
    present={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='manifest.json'}
    expected=set(value['checksums'])
    if present!=expected:raise ContractError('manifest.json','checksums',f'archivos sin declarar {sorted(present-expected)}; archivos faltantes {sorted(expected-present)}')
    for relative,checksum in value['checksums'].items():
        path=root/relative
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():raise ContractError(relative,'path','archivo fuera del paquete o enlace peligroso')
        if digest(path.read_bytes())!=checksum:raise ContractError(relative,'sha256','checksum incorrecto')
    for asset in value['assets']:
        if asset['status']!='available':continue
        path=root/asset['path']
        if asset['kind']=='image':
            try:
                with Image.open(path) as image:
                    if image.width*image.height>30_000_000:raise ContractError(asset['path'],'dimensions','imagen demasiado grande')
                    image.verify()
                    if (image.width,image.height)!=(asset['dimensions']['width'],asset['dimensions']['height']):raise ContractError(asset['path'],'dimensions','dimensiones distintas de las declaradas')
                    if image.format not in {'PNG','JPEG','WEBP'}:raise ContractError(asset['path'],'format','formato de imagen no admitido')
            except (OSError,ValueError) as exc:
                if isinstance(exc,ContractError):raise
                raise ContractError(asset['path'],'format','imagen no válida') from exc
        elif asset['kind']=='video':
            from app.engine.rendering.process import probe_path
            probe=probe_path(path);stream=next((s for s in probe['streams'] if s['codec_type']=='video'),None)
            if not stream or (stream['width'],stream['height'])!=(asset['dimensions']['width'],asset['dimensions']['height']):raise ContractError(asset['path'],'dimensions','video o dimensiones no válidos')
    for d in value['deliverables']:
        if d['narration_file']:
            path=relative_path(d['narration_file'],field='narration_file')
            if path not in value['checksums']:raise ContractError(path,'narration_file','guion no declarado')
            supplied=' '.join((root/path).read_text().split());scenes=' '.join(' '.join(s['narration'].split()) for s in d['scenes'])
            if supplied!=scenes:raise ContractError(path,'narration','el guion no corresponde a la narración estructurada por escenas')
