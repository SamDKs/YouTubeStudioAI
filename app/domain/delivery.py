"""Reglas editoriales estructurales de las cuatro piezas; no escriben guiones."""

import re

SLOTS=('long','short_01','short_02','short_03')


def normalized_narration(deliverable):
    """Normaliza una narración para detectar duplicados completos."""
    return re.sub(r'\W+',' ', ' '.join(s.narration for s in deliverable.scenes).casefold()).strip()


def piece_plan(package):
    """Asigna hasta tres Shorts con guion propio, sin extraer fragmentos del largo."""
    longs=[d for d in package.deliverables if d.kind=='long']
    shorts=[d for d in package.deliverables if d.kind=='short']
    long_text=' '.join(normalized_narration(d) for d in longs);seen=set();rows=[]
    rows.append({'slot':'long','deliverable_id':longs[0].deliverable_id if len(longs)==1 else None,
                 'reason':None if len(longs)==1 else 'Se requiere un único timeline largo.'})
    for index in range(3):
        item=shorts[index] if index<len(shorts) else None
        text=normalized_narration(item) if item else ''
        reason=None
        if not item:reason='NEEDS_SCRIPT: falta guion y timeline independiente.'
        elif not text or text in seen or text in long_text:reason='NEEDS_SCRIPT: guion duplicado o recorte textual del largo; revisar enfoque propio.'
        seen.add(text)
        rows.append({'slot':SLOTS[index+1],'deliverable_id':item.deliverable_id if item else None,'reason':reason})
    return rows
