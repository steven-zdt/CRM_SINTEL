# N8N_OPERATIONS — operacion, backup, observabilidad

Mision N8N-SINTEL-01 (Fase 18/19).

## Observabilidad (Fase 18)

Cada evento saliente (`apps.services.integration_events`) loggea, nunca
persiste en un dashboard dedicado (no se construyo uno en esta pasada):
`event_id`, `event_type`, `tenant` (schema_name), `aggregate_type`,
`aggregate_uuid`. **Nunca loggea**: el payload completo con datos de
negocio sensibles mas alla de los campos minimos (`numero`/`naturaleza`/
`cufe`/`created` para facturas -- nunca el XML completo, nunca datos de
cliente/proveedor mas alla de lo estrictamente necesario), tokens,
contraseñas, secretos.

`correlation_id`/`workflow_execution_id` (Fase 18) no se implementan en
esta pasada del lado SINTEL -- `event_id` cumple el mismo proposito de
trazabilidad para el tramo SINTEL->n8n; el tramo interno de ejecucion
de un workflow de n8n (workflow_execution_id) es responsabilidad de
n8n, visible en su propia UI de ejecuciones.

## Backup y recuperacion (Fase 19)

**No implementado en esta pasada** (DEFERRED) -- diseño real a seguir
cuando se decida:

| Elemento | Donde vive | Estrategia recomendada |
|---|---|---|
| Workflows + credenciales cifradas | Base de datos Postgres `n8n` (volumen nativo Docker, servidor `db` compartido) | Mismo mecanismo de backup ya usado para `sintel` (`pg_dump -Fc`, ver `docs/production/BACKUP_RESTORE_RUNBOOK.md`) -- agregar `-n n8n` o dump completo del servidor, NUNCA mezclar con el dump de `sintel` (son bases distintas, dumps distintos) |
| `N8N_ENCRYPTION_KEY` | `.env` (no versionado) | **CRITICO**: sin esta key, las credenciales cifradas en la base de datos de n8n son irrecuperables aunque el backup de la DB exista. Debe respaldarse por separado, con el mismo cuidado que `DATABASE_PASSWORD` |
| `n8n_data` (named volume, `/home/node/.n8n`) | Docker volume `crm_sintel_n8n_data` | Incluir en la rutina de backup de volumenes Docker si existe una (no auditada en esta pasada) |

**No asumir que reconstruir el contenedor n8n desde cero equivale a
recuperar el estado** (Fase 19, regla explicita) -- sin el backup de la
base de datos `n8n` Y el `N8N_ENCRYPTION_KEY`, un `docker compose up -d
n8n` desde cero arranca una instancia vacia, sin workflows ni
credenciales.

## Seguridad — `n8n audit` (Fase 21)

**No ejecutado en esta pasada.** n8n expone un comando real
`n8n audit` (CLI dentro del contenedor) que revisa credenciales,
filesystem, base de datos, nodes riesgosos y configuracion de la
instancia. Pendiente de ejecutar:

```bash
docker compose exec n8n n8n audit
```

DEFERRED porque la instancia recien desplegada aun no tiene workflows
ni credenciales configuradas (setup inicial de n8n via su UI, paso que
requiere que el usuario complete la creacion de la cuenta owner de n8n
-- esta sesion no completo el login/setup inicial de n8n en nombre del
usuario). Ejecutar despues de que el usuario complete el setup inicial
y antes de conectar cualquier credencial real (email/WhatsApp).

## Como completar el setup pendiente (para el usuario)

1. Abrir `http://localhost:5678` en el navegador -- n8n pedira crear la
   cuenta owner (email/password reales del usuario, nunca completado
   por esta sesion).
2. Crear la credencial "Header Auth" con `Authorization: Bearer
   <access_token>` usando el token impreso por
   `crear_identidad_tecnica_n8n --schema <tenant>` (rotar antes de 7
   dias, o programar el workflow `N8N-SYSTEM: rotar credenciales`).
3. Construir el workflow receptor del webhook (`N8N-SYSTEM: webhook
   inbound`) -- nodo Webhook, validar `X-Sintel-Signature` con
   `N8N_WEBHOOK_SECRET`, copiar la URL real a `N8N_WEBHOOK_URL` en
   `.env` de SINTEL y reiniciar `celery`/`web`.
4. Ejecutar `docker compose exec n8n n8n audit` y resolver los
   findings.
5. Solo entonces conectar credenciales de correo/WhatsApp reales.
