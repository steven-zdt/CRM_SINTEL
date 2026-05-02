# AUDITORIA_FLUJO_COMPLETO - app `perfil`

**Resumen (FASE 1 — Auditoría inicial)**

- Fecha: 2026-03-27
- App: `perfil`
- Auditor ejecutado: `expert_e2e_auditor`, `validate_module_structure`, `validate_assets_placement` (sintel_agent_unified)

**Resultado general (FASE 1)**: Inicialmente NO conforme; tras intervenciones conservadoras en FASE 2, los issues detectados fueron corregidos o validados.

**Issues detectadas**

1. MODEL_INHERITANCE (resuelto)
   - Observación inicial: La auditoría reportó una clase `Meta` en `models.py` como no conforme. Tras revisión, la clase `Meta` es la metaclase interna del modelo `TenantProfile` y no representa un modelo independiente.
   - Estado actual: `TenantProfile` hereda correctamente de `apps.tenant.core.models.SintelTenantBaseModel`. El auditor AST fue ajustado para ignorar `Meta` y ya no reporta la falsa positiva.

**Checks de estructura**

- `templates/` presente: Sí
- `static/<app>/js/` presente: Sí
- `services/` presente: Sí
- `AUDITORIA_FLUJO_COMPLETO.md` presente: No (este archivo se crea ahora)

**Checks de assets**

- `static/perfil/js/` existe: Sí
- Archivos legacy en `apps/tenant/core/static/core/js/perfil/`: Ninguno detectado

**Recomendaciones (priorizadas)**

1. Migrar los modelos para que hereden de `apps.tenant.core.models.SintelTenantBaseModel` y generar las migraciones correspondientes.
2. Revisar el contenido de `models.py` para confirmar que la clase `Meta` es solo la meta-clase interna; si existe una clase modelo llamada `Meta`, renombrarla para evitar conflictos.
3. Mantener la carpeta `services/` y aplicar la separación de responsabilidades. Acciones aplicadas en FASE 2:
   - `apps/tenant/perfil/services/crud_service.py`: ahora usa `.only()` en queries para minimizar columnas seleccionadas (Zero Waste) y `save(update_fields=...)` para actualizaciones parciales.
   - `apps/tenant/perfil/services/business_service.py`: añadido Double Semantic Verification (anti-IDOR) para rechazar payloads que intenten reasignar `empresa` o `user` a valores externos al tenant/usuario autenticado.
   - `apps/tenant/perfil/services/perfil_service.py`: consultas actualizadas a `.only()` y validaciones anti-IDOR en `update_profile`.
4. Añadir en esta misma auditoría (FASE 1) un registro de acciones planificadas y responsable por cada corrección.

**Estado siguiente**

- Estado: FASE 2 completada (cambios conservadores aplicados). Próxima tarea: FASE 3 — Refactorizar endpoints y frontend.

**FASE 3 (resumen)**

- `api/viewsets.py` simplificado a un enrutador puro delegando en `PerfilServiceMixin`.
- Frontend: plantillas y `tenantprofile_main.js` creados; `tenantprofile_form.js` (DOM Shield) añadido en `static/perfil/js/`.
- Se inspeccionó `apps/tenant/core/static/core/js/perfil/` — no había artefactos activos que dependieran de `perfil` para eliminar.

**FASE 4 — Pruebas y QA**

- `run_sintel_tests('apps/tenant/perfil/tests/')` ejecutado: la ejecución de tests falló por falta de conexión a la base de datos en este entorno (psycopg2: OperationalError). Resultado parcial:
   - `returncode`: 1
   - Error: `psycopg2.OperationalError: could not ...` (DB no accesible desde runner local)

- `verify_db_compliance('perfil_tenantprofile')`: herramienta ejecutada — entono de ejecución actual no realiza chequeos en vivo; retorno: `psycopg2 available but live checks are disabled in this environment`.

**[PASSED]**

- AST E2E Auditor: OK (no issues pendientes tras ajustes).
- Servicios: `services/crud_service.py`, `services/business_service.py`, `services/perfil_service.py` — sintaxis válida y con mejoras aplicadas (Zero Waste y anti-IDOR).

**[ARCH-CHECK]**

- `models.py`: `TenantProfile` ya hereda de `SintelTenantBaseModel`.
- `viewsets.py`: ahora es un enrutador puro que delega responsabilidades al Service Layer.
- `services/`: presente y con separación de CRUD / business logic.

**[COVERAGE]**

- Tests unitarios: ejecución fallida por falta de infraestructura (Postgres no accesible). Para ejecutar los tests en CI/local, levante la base de datos PostgreSQL con las credenciales esperadas o ajuste `pytest.ini` para usar SQLite temporalmente.

**Siguientes pasos recomendados (priorizados)**

1. Ejecutar los tests localmente con la base de datos disponible (docker-compose up -d db) y volver a correr `pytest apps/tenant/perfil/tests/`.
2. Si se desea, puedo crear un patch opcional para adaptar temporalmente `pytest.ini` a SQLite para ejecutar pruebas rápidas sin infra (solo si apruebas esa opción).
3. Revisar y aplicar migraciones si se modifica la estructura de modelos (no fue necesario en esta intervención).

