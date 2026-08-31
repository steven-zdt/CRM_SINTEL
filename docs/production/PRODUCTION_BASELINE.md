# PRODUCTION_BASELINE — Fase 0

Auditoría de código/configuración real (sin modificar nada en esta
fase). Fuente: `AGENTS.md`, `MEMORY.md`, `docker-compose.yaml`,
`config/settings.py`, `.env`, comandos de gestión existentes, y el
trabajo ya verificado en esta misma sesión (auditoría de onboarding,
remediación P0, lifecycle de tenants).

**Fecha:** 2026-08-31

## Estado declarado de partida

`DEVELOPMENT MODE` — confirmado: no existe ningún ambiente de
`staging`/`production` real desplegado; todo lo verificable en esta
auditoría corre contra el `docker-compose.yaml` local de desarrollo.

## Inventario de contenedores (`docker-compose.yaml`)

| Servicio | Imagen | Rol | Notas de producción |
|---|---|---|---|
| `db` | `postgres:16-alpine` | Base de datos multi-tenant | `POSTGRES_PASSWORD` requerido explícitamente (`${DATABASE_PASSWORD:?...}` — sin fallback débil, buena práctica DEVOPS-M1 ya aplicada) |
| `redis` | `redis:7.2-alpine` | Cache + broker de Celery | — |
| `neo4j` | `neo4j:5.24-community` | Grafo de conocimiento (EKG, `tools.ekg`) | `NEO4J_AUTH` requerido explícitamente |
| `web` | build local | Django (Gunicorn/runserver según entrypoint) | — |
| `nginx` | build local | Reverse proxy | Volumen `nginx_certs` dedicado — sugiere gestión de certificados TLS ya contemplada en el diseño, no verificado si hay certificados reales cargados |
| `celery` | build local | Worker (`celery -A config worker -l info -Q high_priority,default`) | **Sin `celery beat`** — confirmado en la misión de lifecycle de tenants anterior: cero tareas periódicas automáticas en ningún entorno |
| `cloudflared` | `cloudflare/cloudflared:2025.5.0` | Túnel Cloudflare | Sugiere que la exposición pública planeada es vía Cloudflare Tunnel, no un balanceador/IP pública directa — relevante para Fase 9 (TLS) y 10 (DNS) |

**Volúmenes con nombre explícito** (sobreviven `docker compose down`):
`crm_sintel_postgres_data`, `crm_sintel_nginx_certs`,
`crm_sintel_neo4j_data`.

## Secretos — dónde viven (Fase 5, preliminar)

Todos los secretos viven en un único archivo `.env` (vía `env_file:
- .env` en cada servicio), inyectados como variables de entorno — sin
un secret manager dedicado (Vault, AWS Secrets Manager, etc.). Esto es
**normal y aceptable para desarrollo**, pero es un ítem real de la
Fase 5 para producción (ver `docs/production/PRODUCTION_CHECKLIST.md`).

Variables `${VAR:?mensaje}` (fallan explícito si faltan, sin default
inseguro) ya confirmadas: `DATABASE_PASSWORD`, `NEO4J_PASSWORD`. Patrón
correcto — se audita en Fase 4-6 si se aplica consistentemente a TODAS
las variables sensibles.

## Comandos de backup/restore YA EXISTENTES (Fase 16-17)

Confirmado por inspección directa de código —
`apps/public/tenants/management/commands/`:

- `backup_tenant.py` — backup de UN schema vía `pg_dump` (formato
  custom), con soporte de detección de "último backup" (aunque el
  propio código anota que `pg_dump` no soporta incremental nativo).
- `backup_all_tenants.py` — backup de todos los tenants.
- `restore_tenant.py` — restauración desde un backup de `pg_dump`.

**Esto ya es una base real** — no hay que construir el mecanismo desde
cero. Lo que falta (ver Fase 16-17 del checklist) es: programación
automática (cron/Celery Beat — inexistente hoy), retención definida,
cifrado en reposo, ubicación fuera del propio host, y **una prueba de
restauración end-to-end ejecutada y documentada** (tener el comando no
es lo mismo que haber demostrado que funciona).

## Observabilidad existente (Fase 21-22)

- `GET /health` — confirmado funcional (usado como evidencia en la
  misión de onboarding E2E: `HTTP 200`, respuesta corta). Es un único
  endpoint, sin distinción explícita `liveness` vs `readiness`.
- `apps/public/core/management/commands/status_public.py` — comando de
  diagnóstico del schema público (ya existente).
- `ConsoleActionLog` — auditoría de acciones administrativas (parcial,
  ver misión de lifecycle de tenants: 3 de 8 acciones de `ClientViewSet`
  auditadas al cierre de esa misión).
- `FailedTenantTask` — dead-letter-queue de Celery ya en uso.

## Multi-tenancy / aislamiento — YA VERIFICADO EN VIVO en esta sesión

No se repite el trabajo — evidencia ya real y documentada:

- `documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md` — auditoría
  completa del flujo de creación de tenant.
- `docs/e2e/ONBOARDING_E2E_REPORT.md` — creación real de 2 tenants QA,
  aislamiento cross-tenant confirmado (401 + invalidación forzada de
  cookie de sesión al cruzar de tenant), y **una fuga de privilegios
  crítica encontrada y corregida** (owner de tenant nuevo obtenía
  `is_staff=True` global).
- `docs/console/CONSOLE_TENANTS_FINAL_REPORT.md` — período de prueba
  con bloqueo real verificado sin depender de Celery.

## Dependencias externas ya clasificadas (Fase 38-39) — no se re-audita, se referencia

- `docs/remediation/REM-EXT-01.md` — transmisión real DIAN: **BLOCKED**,
  sin credenciales/certificado/WSDL de producción.
- `docs/remediation/REM-EXT-02.md` — transmisión real DSPNE (nómina):
  **BLOCKED**, mismo motivo.
- `apps/tenant/core/dian/adapters.py` — `NullTransportAdapter` por
  defecto (honesto, no simula éxito); `MockTransportAdapter` solo
  activable con `settings.FISCAL_ALLOW_MOCK_TRANSPORT=True` explícito Y
  parámetro de request explícito — **nunca implícito**. Esto es
  exactamente el guardrail que la Fase 45 pide auditar — ya existe y ya
  es correcto (verificado, no asumido — ver Fase 45 más abajo para la
  verificación puntual repetida en esta misión).

## Governance y EKG ya existentes

- `tools/ekg` — grafo de dependencias/impacto (Neo4j), ya usado en
  sesiones previas (`tools.ekg.impact --name FacturaBusinessService`,
  referenciado en `MEMORY.md`).
- Hooks de gobernanza: `py_compile` post-edición, `SSoT Guard` en
  pre-commit (confirmado activo en cada commit de esta sesión).
- `make audit` — ruff + bandit + pip-audit + django check + static check
  (`CLAUDE.md`).

## Alcance de esta misión, dado el estado real de la infraestructura

**No existe ambiente de staging ni de producción real** — todas las
fases que requieren infraestructura real (TLS con certificados reales,
DNS público, balanceo blue/green, prueba de carga contra staging,
ventana de monitoreo post-deploy) **no pueden ejecutarse ni verificarse
de forma real** en este entorno. Se documentan como `NOT_APPLICABLE_LOCAL_DEV`
o `BLOCKED` según corresponda, con el procedimiento REAL a seguir el día
que exista esa infraestructura — nunca simulados como si ya hubieran
ocurrido.

Ningún código fue modificado en esta fase — solo lectura.
