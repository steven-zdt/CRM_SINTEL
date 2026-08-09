# F16 — Modelo Organizacional Colombiano — Empresa/Sede/Área

**Fecha:** 2026-08-09
**Estado:** 🟢 F16 COMPLETED

## F16.0 — Empresa

`apps/tenant/empresa/models.py:Empresa` — singleton por schema tenant (verificado, `singleton_key`
usado en `get_or_create`, ver `apps/services/onboarding/empresa_service.py`). Campos fiscales
reales: `razon_social`, `nit`, `dv` (verificar nombre exacto de campo — no se re-audita aquí, ya
cubierto por el resto de la arquitectura), régimen tributario, dirección — sin duplicar contra
`apps/public/impuestos` (catálogo DIAN compartido, consumido por selección, no copiado).

## F16.1/F16.2 — Sede / Área

`Sede(SintelTenantBaseModel)`: `empresa` FK (`CASCADE`, excepción documentada `[ARQ-A2]` a
`SintelTenantBaseModel` que normalmente usa `PROTECT` — Sede debe desaparecer con su Empresa).
`Area(SintelTenantBaseModel)`: `empresa` FK **propia** + `sede` FK — ambas relaciones existen
independientemente (`Area.empresa_id` no se deriva de `Area.sede.empresa_id` a nivel de esquema).

## F16.3 — Integridad jerárquica (verificado, no asumido)

**`Area.empresa_id == Area.sede.empresa_id` SÍ se aplica, a nivel de Service Layer (no de
constraint de base de datos):**

```python
# apps/tenant/empresa/services/crud_service.py:187-192 (crear_area_db)
sede = Sede.objects.filter(empresa_id=empresa_id, pk=sede_id).first()
if not sede:
    raise ValueError("La sede especificada no existe o no pertenece a la empresa.")
```

Mismo patrón en `actualizar_area_db` (línea 214-220). **Enforcement real, verificado leyendo el
código — no una constraint `CHECK` de PostgreSQL**, lo que significa: protegido contra cualquier
escritura que pase por `AreaBusinessService`/el ViewSet (el camino real de la aplicación), pero no
contra un script/shell que haga `Area.objects.create(empresa=A, sede=sede_de_B)` directamente vía
ORM crudo. Riesgo residual bajo (ningún camino de la aplicación real hace esto), documentado para
que quede explícito, no oculto.

## F16.4/F16.5/F16.6 — Contexto, Scope, Context

Ya formalizado y verificado con código real en `documentacion/ORGANIZATIONAL_CONTRACT.md` (FASE 3
de la consolidación OCF/OSF) — no se re-deriva aquí. Resumen: `OrganizationalContext` (posición
activa) ≠ `OrganizationalScope` (límite de autorización, conjunto completo), ambos resuelven desde
`TenantProfile` (`rol`/`alcance`/`sedes_asignadas`/`areas_asignadas`), nunca desde `sede_id` del
frontend — verificado además por la regla `ORG-001` del motor de gobernanza (0 findings, los dos
conceptos siguen separados).

## F16.7 — Null-safe

`filter_by_scope_null_safe()` ya implementado y en uso real en 6 apps — ver
`OSF_TECHNICAL_AUDIT.md` §4. Este documento no introduce ningún cambio a ese patrón.

## F16.8 — Matriz de obligatoriedad organizacional

Ver `documentacion/ORGANIZATIONAL_FIELD_MATRIX.md` (nuevo, este documento) — reconstruida a partir
del análisis real ya hecho en FASE 5 (`ORGANIZATIONAL_SCOPE_MATRIX.md` §1), no re-derivada desde
cero.

**Estado: 🟢 F16 COMPLETED.**
