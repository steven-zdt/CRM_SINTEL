"""
Jerarquia de Permisos Organizacionales (Fase 4, proyecto OCF).

Ver docs/ADR-004-organizational-context-framework-diseno.md ("OrganizationalPermission")
y documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md para el estado del
proyecto. Nueva infraestructura, aditiva - no modifica RolTenant.rol ni
AlcanceOrganizacional.alcance (SSoT sin cambios, ADR-003), ni ninguna de las
clases de apps/tenant/api/permissions.py ya existentes.

Mapeo de los niveles pedidos a lo que YA existe (sin campo nuevo):

    ADMIN_GLOBAL   -> is_staff / is_superuser (Django, esquema publico)
    ADMIN_EMPRESA  -> rol=ADMIN    + alcance=EMPRESA
    ADMIN_SEDE     -> rol=ADMIN    + alcance=SEDE
    JEFE_AREA      -> rol=ADMIN    + alcance=AREA
    OPERADOR       -> rol=OPERADOR (cualquier alcance)
    CONSULTA       -> rol=VISOR    (cualquier alcance)

GAP CONOCIDO Y DOCUMENTADO (no resuelto en silencio): el pedido original
incluye un nivel "Supervisor" entre JEFE_AREA y OPERADOR. El modelo actual
(rol: ADMIN/OPERADOR/VISOR x alcance: EMPRESA/SEDE/AREA) no tiene ningun eje
libre para representarlo sin inventar una distincion de capacidad que Fase 0
no encontro en ningun modulo real (mismo criterio ya aplicado a JEFE_AREA en
ADR-004, riesgo de diseno D-3). Por eso "Supervisor" se trata aqui como
sinonimo de OPERADOR (misma funcion de resolucion, mismo nivel) hasta que una
fase futura con un caso de uso real justifique separar una nueva capacidad
(ej. "puede aprobar" vs "solo puede operar"). No se fabrica una jerarquia
rol/alcance que no tiene respaldo en ningun modulo existente.
"""
from __future__ import annotations

ADMIN_GLOBAL = "ADMIN_GLOBAL"
ADMIN_EMPRESA = "ADMIN_EMPRESA"
ADMIN_SEDE = "ADMIN_SEDE"
JEFE_AREA = "JEFE_AREA"
OPERADOR = "OPERADOR"  # incluye "Supervisor" - ver GAP CONOCIDO arriba
CONSULTA = "CONSULTA"

# Orden de mayor a menor privilegio - usado por OrganizationalPermission para
# aceptar "este nivel o superior" sin que cada ViewSet enumere combinaciones.
ORGANIZATIONAL_PERMISSION_LEVELS = (
    ADMIN_GLOBAL,
    ADMIN_EMPRESA,
    ADMIN_SEDE,
    JEFE_AREA,
    OPERADOR,
    CONSULTA,
)

_LEVEL_RANK = {level: idx for idx, level in enumerate(ORGANIZATIONAL_PERMISSION_LEVELS)}


def resolve_organizational_permission_level(*, rol: str, alcance: str, is_staff: bool = False) -> str:
    """Resuelve el nivel jerarquico (Fase 4) a partir de datos ya existentes
    (RolTenant.rol, AlcanceOrganizacional.alcance, Django is_staff) - no
    requiere ningun campo nuevo en TenantProfile."""
    if is_staff:
        return ADMIN_GLOBAL
    if rol == "ADMIN":
        if alcance == "SEDE":
            return ADMIN_SEDE
        if alcance == "AREA":
            return JEFE_AREA
        return ADMIN_EMPRESA  # alcance == "EMPRESA" o desconocido: el mas amplio de los ADMIN
    if rol == "VISOR":
        return CONSULTA
    return OPERADOR  # rol == "OPERADOR" (o cualquier otro valor no reconocido: el mas restrictivo no-VISOR)


def level_meets_minimum(level: str, minimum: str) -> bool:
    """True si `level` es igual o mas privilegiado que `minimum`, segun el
    orden de ORGANIZATIONAL_PERMISSION_LEVELS. Niveles desconocidos nunca
    cumplen (fail-closed)."""
    if level not in _LEVEL_RANK or minimum not in _LEVEL_RANK:
        return False
    return _LEVEL_RANK[level] <= _LEVEL_RANK[minimum]
