"""Conecta la fase de importación con las revisiones y jobs del motor existente."""

from app.domain.package_errors import StudioError


class ProducePackages:
    def __init__(self, imports, studio, links):
        """Inyecta los servicios existentes sin crear otra cola ni otro renderer."""
        self.imports, self.studio, self.links = imports, studio, links

    def activate(self, import_id, channel):
        """Vincula por hash un paquete validado; nunca reutiliza otro contenido."""
        row=next((r for r in self.imports.list(channel) if r['import_id']==import_id),None)
        if not row or row['state'] in {'FAILED','IMPORTED','VALIDATING'}:
            raise StudioError('Primero valida el paquete en este canal.')
        manifest=row['report'].get('manifest')
        if not manifest:raise StudioError('Bloqueado: el ZIP de recursos necesita un timeline narrativo explícito.')
        linked=self.links.find(import_id)
        if linked:return linked
        project=next((p for p in self.studio.projects() if p['channel_id']==channel and p['episode_id']==manifest['episode_id'] and p['language']==manifest['language']),None)
        if project:
            raw=self.studio.repository.project(project['project_id'])
            if raw['input_sha256']!=row['zip_sha256']:
                raise StudioError('Existe otro paquete para este episodio. No se sobrescribió; utiliza un ID de variante explícito.')
            identifier=project['project_id']
        else:
            input_path=self.studio.settings.safe(row['report']['input_path'])
            identifier=self.studio.import_zip(input_path.parent/'original.zip')
        self.links.save(import_id,identifier)
        return identifier
