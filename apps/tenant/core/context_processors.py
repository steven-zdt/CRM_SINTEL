"""
Context processors globales del workspace tenant (ver config/settings.py's
TEMPLATES['OPTIONS']['context_processors']).
"""
from apps.tenant.core.services.sede_context import resolve_sede_activa_id


def contexto_organizacional(request):
    """Inyecta `sede_activa` y `sedes_disponibles` en todo template
    renderizado dentro del tenant (ADR-003), para el selector de "Sede
    activa" del header compartido
    (apps/tenant/core/templates/tenant/partials/_header.html).

    Vacio (sin llaves) para requests anonimos o sin tenant_profile - no
    rompe ningun template existente que no las use.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}

    perfil = getattr(user, 'tenant_profile', None)
    if perfil is None:
        return {}

    from apps.tenant.empresa.models import Sede

    if perfil.alcance == 'EMPRESA':
        sedes_disponibles = list(Sede.objects.filter(empresa_id=perfil.empresa_id).order_by('nombre'))
    else:
        sedes_disponibles = list(perfil.sedes_asignadas.order_by('nombre'))

    sede_activa_id = resolve_sede_activa_id(request, perfil.empresa_id, perfil)
    sede_activa = next((s for s in sedes_disponibles if s.id == sede_activa_id), None)
    if sede_activa is None and sede_activa_id is not None:
        sede_activa = Sede.objects.filter(id=sede_activa_id).first()

    return {
        'sede_activa': sede_activa,
        'sedes_disponibles': sedes_disponibles,
    }
