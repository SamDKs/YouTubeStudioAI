"""Orquesta cuatro piezas sobre la cola existente, sin acoplarse a FFmpeg o Streamlit."""

from uuid import uuid4
from hashlib import sha256
from app.domain.delivery import piece_plan
from app.domain.package_errors import StudioError


class EpisodeDelivery:
    def __init__(self,studio,repository):
        """Inyecta la producción existente y persistencia de entregas."""
        self.studio,self.repository=studio,repository

    def start(self,project_id,*,fps=30,short_max_seconds=60,review_only=True,allow_provisional=True,regenerate=None):
        """Encola piezas disponibles; conserva faltantes y fallos como estados individuales."""
        view=self.studio.get(project_id)
        if not 30<=short_max_seconds<=180 or fps not in {24,25,30}:raise StudioError('Perfil de entrega inválido.')
        options={'fps':fps,'short_max_seconds':short_max_seconds,'review_only':review_only,'allow_provisional':allow_provisional}
        if regenerate:options['regenerate']={regenerate:str(uuid4())}
        identifier=self.repository.create(project_id,view.revision_id,options)
        for piece in piece_plan(view.package):
            slot=piece['slot'];job=None;reason=piece['reason'];state='NEEDS_SCRIPT' if reason else 'PREPARED'
            if not reason:
                try:
                    job=self.studio.produce_piece(project_id,piece['deliverable_id'],fps=fps,short_max_seconds=short_max_seconds,
                          review_only=review_only,allow_provisional=allow_provisional,regeneration=options.get('regenerate',{}).get(slot))
                    state=next(j['status'] for j in self.studio.jobs(project_id) if j['job_id']==job)
                except StudioError as exc:state='BLOCKED';reason=str(exc)
            self.repository.piece(identifier,slot,piece['deliverable_id'],job,state,reason)
        return identifier

    def approve_short(self,project_id,deliverable,*,actor='local_owner',source='owner_approved'):
        """Asocia un timeline revisado al episodio mediante una nueva revisión sin tocar el ZIP."""
        view=self.studio.get(project_id);data=self.studio.editable(project_id)
        if deliverable.get('kind')!='short':raise StudioError('Solo se admite un timeline Short independiente.')
        if sum(d.kind=='short' for d in view.package.deliverables)>=3:raise StudioError('El episodio ya contiene tres Shorts.')
        data['manifest']['deliverables'].append(deliverable)
        proposed=self.studio.validate_edit(data['manifest'])
        if any(p['deliverable_id']==deliverable['deliverable_id'] and p['reason'] for p in piece_plan(proposed)):
            raise StudioError('El Short duplica otra narración o un recorte del largo.')
        # save ejecuta el contrato y conserva identidad, recursos, fuentes y rótulos obligatorios.
        self.studio.save(project_id,data['manifest'],data['voice'],view.revision_version)
        new=self.studio.get(project_id)
        return self.repository.candidate(project_id,source,deliverable,'approved',actor,new.revision_id)

    def start_all(self,**options):
        """Inicia episodios por canal y devuelve errores aislados; no detiene otros canales."""
        results=[]
        for project in self.studio.projects():
            try:results.append({'project_id':project['project_id'],'channel_id':project['channel_id'],'delivery_id':self.start(project['project_id'],**options)})
            except StudioError as exc:results.append({'project_id':project['project_id'],'channel_id':project['channel_id'],'error':str(exc)})
        return results

    def bundle_bytes(self,project_id,delivery_id):
        """Restringe la descarga al paquete registrado para el episodio seleccionado."""
        row=next((d for d in self.repository.list(project_id) if d['delivery_id']==delivery_id),None)
        if not row or not row['bundle_path']:raise StudioError('El paquete todavía no está disponible.')
        content=self.studio.settings.safe(row['bundle_path']).read_bytes()
        if sha256(content).hexdigest()!=row['report'].get('bundle_sha256'):raise StudioError('El ZIP cambió desde su verificación. Regenera la entrega.')
        return content

    def approve(self,project_id,delivery_id,note):
        """Permite aprobación explícita solo con las cuatro piezas y verificaciones completas."""
        if not any(d['delivery_id']==delivery_id for d in self.repository.list(project_id)):raise StudioError('La entrega no pertenece al episodio.')
        self.bundle_bytes(project_id,delivery_id)
        if not note.strip():raise StudioError('Registra una nota de revisión humana.')
        try:self.repository.approve(delivery_id,'local_owner',note)
        except ValueError as exc:raise StudioError(str(exc)) from exc
