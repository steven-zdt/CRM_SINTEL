# PRODUCTION_BLOCKERS

Generado a partir de una corrida real de `python manage.py
production_readiness` (2026-08-31T15:48:37Z). Severidad per Fase 57:
`P0` bloquea, `P1` bloquea normalmente, `P2` warning, `P3` mejora.

## P0 — bloquean el release

| ID | Categoría | Hallazgo | Corrección requerida | Owner |
|---|---|---|---|---|
| `APP-01-debug` | APPLICATION | `settings.DEBUG=True` actualmente | Definir `DEBUG=False` en el `.env` del entorno de destino antes de desplegar (correcto y esperado que sea `True` en desarrollo local — este blocker es "no despliegues así", no "el código está mal") | DevOps/release |
| `APP-02-secret-key` | APPLICATION | `SECRET_KEY` usa el fallback `'django-insecure-change-me-in-production'` — confirmado real, `DJANGO_SECRET_KEY` no está definida en `.env` | Generar una clave real (`get_random_secret_key()`) y definir `DJANGO_SECRET_KEY` en el entorno de destino. **No cambiar el `.env` de desarrollo local** — invalidaría sesiones/tokens activos sin necesidad real; esto es una acción específica del entorno de destino | DevOps/release |
| `BAK-02-restore-tested` | BACKUP | Sin evidencia de una prueba de restauración end-to-end ejecutada | Ejecutar el drill descrito en `BACKUP_RESTORE_RUNBOOK.md` y documentar el resultado con evidencia | DevOps |

## EXTERNAL_DEPENDENCY — no bloquean por sí solos, pero deben quedar clasificados explícitamente (nunca fingidos como resueltos)

| ID | Hallazgo |
|---|---|
| `FISCAL-01-dian-transmission` | Transmisión real DIAN sin credenciales/certificado/WSDL de producción |
| `FISCAL-02-dspne-transmission` | Transmisión real DSPNE sin credenciales/certificado/URL de producción |

## P1/P2 — no bloquean, documentados

- `APP-04-check-deploy` (P1, WARN): 6 security warnings de
  `manage.py check --deploy` — esperadas mientras `DEBUG=True`;
  re-verificar tras resolver `APP-01`.
- `BAK-03-schedule` (P2, WARN): sin backup automático programado (no
  hay `celery beat` en ningún entorno de este proyecto).
- `INFRA-01-services-up` (P1, WARN): este check debe ejecutarse desde
  el host (no dentro del contenedor `web`) — limitación de la
  herramienta, no del sistema.
- `INFRA-02-celery-beat` (P2, WARN): sin scheduler — no bloqueante
  porque el enforcement real de trial vive en el middleware, no en
  Celery (ver `docs/console/TRIAL_PERIOD.md`).
- `OBS-02-liveness-readiness-split` (P2, WARN): un solo endpoint
  `/health`, sin distinción explícita liveness/readiness — irrelevante
  sin orquestador que la consuma.
- `SEC-04-localhost-leaks` (P2, WARN): 65 ocurrencias de
  `localhost`/`127.0.0.1` en código no-test — no clasificadas
  individualmente en esta pasada (Fase 44 pide clasificar cada una;
  requiere una revisión dedicada, no una corrección apresurada masiva).

## PASS confirmados (no listados aquí en detalle — ver output completo de `production_readiness`)

`APP-03` (ALLOWED_HOSTS), `DB-01` (sin migraciones pendientes),
`DOC-01` (docs core presentes), `SEC-01` (sin secretos hardcodeados —
tras corregir un falso positivo de la propia herramienta),
`SEC-02` (CORS/CSRF acotados), `SEC-03` (mock de DIAN deshabilitado por
defecto), `OBS-01` (`/health` responde 200), `TEN-01/02/03` (aislamiento
cross-tenant, fix de escalación de privilegios, y enforcement de trial —
los 3 verificados en vivo en misiones previas de esta sesión).
