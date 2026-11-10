"""Casos de uso de fase 1; reutiliza contratos y extracción del motor actual."""

from pathlib import Path
import shutil
from uuid import uuid4

from app.domain.package_preparation import preparation_state
from app.domain.package_errors import StudioError
from hashlib import sha256


class PreparePackages:
    def __init__(self, settings, repository, reader, inspect_files):
        """Inyecta persistencia, extracción e inspección sin acoplarlos a la UI."""
        self.settings = settings
        self.repository = repository
        self.reader = reader
        self.inspect_files = inspect_files

    def import_zip(self, source: Path, channel: str, original_name: str):
        """Aísla por canal/importación y conserva fallos y reintentos por hash."""
        if channel not in {c['channel_id'] for c in self.repository.channels()}:
            raise StudioError('Selecciona un canal activo real.')
        if source.stat().st_size > self.reader.limits.compressed_bytes:
            raise StudioError('ZIP demasiado grande.')
        checksum = sha256(source.read_bytes()).hexdigest()
        identifier = str(uuid4())
        identifier = self.repository.create(identifier, channel, channel+'-'+identifier, checksum, Path(original_name).name)
        old = next(r for r in self.repository.list(channel) if r['import_id'] == identifier)
        if old['state'] not in {'FAILED', 'IMPORTED', 'VALIDATING'}:
            return identifier
        report = {'warnings': [], 'missing': [], 'files': []}
        self.repository.update(identifier, 'VALIDATING', report)
        base = self.settings.safe(str((self.settings.imports_root / channel / identifier).relative_to(self.settings.project_root)))
        try:
            with self.reader.inspect(source, self.settings.temporary_root) as value:
                manifest = value.manifest
                if manifest and manifest['channel_id'] != channel:
                    raise StudioError('El canal del manifiesto no coincide con el contexto seleccionado.')
                if manifest and manifest['language'] != 'en-US':
                    raise StudioError('El paquete principal de esta fase requiere en-US; el historial se conserva.')
                report['files'] = self.inspect_files(value.root, self.settings.ffprobe)
                report.update(mode='structured' if manifest else 'resources', manifest=manifest,
                              episode_id=manifest.get('episode_id', old['episode_id']),
                              title=manifest.get('title', Path(original_name).stem), language='en-US',
                              has_script=bool(manifest), warnings=list(value.warnings))
                if manifest:
                    report['missing'] = [a['asset_id'] for a in manifest['assets'] if a['status'] != 'available']
                    kinds = [d['kind'] for d in manifest['deliverables']]
                    if kinds.count('long') != 1 or kinds.count('short') != 3:
                        report['missing'].append('Se requiere un largo y tres Shorts independientes.')
                    if any(a['provenance']['rights_status'] != 'allowed' for a in manifest['assets']):
                        report['missing'].append('Derechos de recursos pendientes de revisión.')
                else:
                    report['missing'] = ['Timeline largo y tres timelines de Shorts con narración y asociaciones explícitas',
                                         'Procedencia y licencias de los recursos por revisar']
                    report['warnings'].append('No se infieren escenas ni hechos de nombres de archivo. Los guiones sueltos requieren revisión y asociación explícita.')
                base.mkdir(parents=True, exist_ok=True)
                # Solo se publica una entrada completa. No se toca una carpeta ya publicada.
                if not (base / 'input').exists():
                    staging = base / ('staging-'+str(uuid4()))
                    shutil.copytree(value.root, staging)
                    staging.rename(base / 'input')
                if not (base / 'original.zip').exists():
                    shutil.copyfile(source, base / 'original.zip')
                if sha256((base / 'original.zip').read_bytes()).hexdigest() != checksum:
                    raise StudioError('El ZIP original cambió durante la copia.')
                report['input_path'] = str(base.relative_to(self.settings.project_root) / 'input')
            self.repository.update(identifier, preparation_state(report), report)
        except Exception as exc:
            report['errors'] = [str(exc)]
            self.repository.update(identifier, 'FAILED', report)
        return identifier

    def prepare(self, identifier, channel, script_id=None):
        """Asocia aprobación real del canal y recalcula faltantes sin renderizar."""
        row = next((r for r in self.repository.list(channel) if r['import_id'] == identifier), None)
        if not row or row['state'] in {'FAILED', 'VALIDATING', 'IMPORTED'}:
            raise StudioError('Primero importa y valida el paquete en este canal.')
        report = row['report']
        if script_id:
            script = next((s for s in self.repository.scripts(channel) if s['script_id'] == script_id), None)
            if not script:
                raise StudioError('El guion no está aprobado en inglés para este canal.')
            report.update(has_script=True, script_id=script_id, script_version_id=script['current_version_id'])
        self.repository.update(identifier, preparation_state(report), report)
