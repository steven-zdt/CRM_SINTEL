# Auditoría: apps/tenant/perfil

Resumen de la auditoría ejecutada el 2026-03-26.

Alcance:
- Archivos inspeccionados: `models.py`, templates y sincronización con `workspace.html`.
- Objetivos: cumplimiento Regla 0 (sin emojis ni multibyte), herencia SSoT (`SintelTenantBaseModel`), protección multi-tenant, y creación de partials si faltaban.

Hallazgos:

- Regla 0 ([CRITICAL] 0): No se detectaron emojis ni caracteres multibyte en `apps/tenant/perfil/models.py`.

- Herencia SSoT ([CORE-DB] 14): `TenantProfile` hereda de `SintelTenantBaseModel`.

- Unique constraints / integridad: Existe `unique_together = ('user','empresa')` que garantiza unicidad de perfil por usuario y empresa (no aplica patrón singleton).

- Service Layer y ViewSets: No se encontró `services.py` ni `api/viewsets.py` en la app `perfil`. Si se implementa lógica de negocio en el futuro, debe residir en `services/` siguiendo el patrón SSoT.

- Templates y UI:
  - Se crearon partials en la app bajo `apps/tenant/perfil/templates/perfil/partials/`:
    - `list.html`
    - `modals.html`
    - `assets_perfil.html`
  - Se añadieron wrappers en `apps/tenant/core/templates/tenant/perfil/partials/` para evitar errores en `workspace.html` y mantener la localización SSoT de assets/templates.

- Tests:
  - Antes de esta auditoría no había tests en la app `perfil`.
  - Se añadió una prueba mínima para `TenantProfile` (ver `apps/tenant/perfil/tests/test_models.py`).

Recomendaciones:
- Añadir un `services.py` si se implementa lógica de negocio relevante para perfiles, siempre `@staticmethod` y stateless.
- Mantener la regla de no usar emojis en cualquier archivo del proyecto; integrar `ruff`/pre-commit para detección automática.
- Añadir tests adicionales para endpoints, permisos y flujo de edición de perfil en UI.

Acciones realizadas por el agente:
- Creación de partials en la app `perfil` y wrappers en `core`.
- Creación de `apps/tenant/perfil/tests/test_models.py` con prueba mínima de integridad.

Estado actual:
- Tests de `apps.tenant.perfil` ejecutados: antes no había tests; ahora hay una prueba mínima que será ejecutada en el siguiente paso automatizado.

