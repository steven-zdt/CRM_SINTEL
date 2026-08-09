"""
Algoritmo de resolucion de "sede activa" (ADR-003), compartido por
SintelDSVMixin.get_sede_id() (apps/tenant/api/mixins.py, usado por los
ViewSets DRF) y por el context processor de UI
(apps/tenant/core/context_processors.py, usado por el header compartido) -
un solo lugar para no duplicar el orden de resolucion en dos capas que
podrian desincronizarse.
"""
from __future__ import annotations


def resolve_sede_activa_id(request, empresa_id: int, perfil) -> int | None:
    """Resuelve el id de la Sede activa. Orden:
      1. request.session['sede_activa_id'], si sigue perteneciendo a
         `empresa_id` (si no, se descarta de la sesion por obsoleta).
      2. La primera (por nombre) de perfil.sedes_asignadas.
      3. La Sede "Principal" (primera por nombre) de la empresa.
    Retorna None solo si la empresa aun no tiene ninguna Sede.
    """
    from apps.tenant.empresa.models import Sede

    session = getattr(request, 'session', None)
    sesion_sede_id = session.get('sede_activa_id') if session is not None else None
    if sesion_sede_id:
        if Sede.objects.filter(id=sesion_sede_id, empresa_id=empresa_id).exists():
            return sesion_sede_id
        del session['sede_activa_id']

    if perfil is not None:
        primera_asignada = perfil.sedes_asignadas.order_by('nombre').first()
        if primera_asignada:
            return primera_asignada.id

    principal = Sede.objects.filter(empresa_id=empresa_id).order_by('nombre').first()
    return principal.id if principal else None
