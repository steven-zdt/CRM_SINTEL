# N8N_WORKFLOWS — catalogo de workflows

Mision N8N-SINTEL-01 (Fase 15/16). Solo el piloto minimo (Fase 15: "no
crear 50 workflows en la primera mision").

**N8N-SINTEL-02 (2026-09-10):** proveedores confirmados por el usuario --
**Gmail/Google Workspace** para el correo entrante (Fase 5) y
**WhatsApp Business Cloud API (Meta oficial)** para las alertas
salientes (Fase 9). Ver diseño de nodos concreto en cada workflow abajo.
**Bloqueo real encontrado al intentar construirlos:** `http://127.0.0.1:5678`
(n8n, ya corriendo y healthy -- ver `N8N_RELEASE_GATE.md`) **no tiene
cuenta owner creada** -- pantalla "Set up owner account" al abrir la UI.
El asistente de Claude Code tiene prohibido escribir contraseñas en
cualquier campo (incluida esta), asi que el diseño de abajo queda listo
para importar pero la construccion real en la UI de n8n (y la conexion
de credenciales Gmail OAuth2 / WhatsApp) requiere que el usuario cree
esa cuenta owner primero.

## Workflow A — Email -> XML -> SINTEL Facturas

```
Trigger: Gmail Trigger (n8n, nodo oficial, credencial OAuth2 -- el
         usuario autoriza su cuenta Google directamente en la UI de
         n8n, nunca en codigo SINTEL, Fase 16)
  |
  v
Detectar adjuntos .xml (filtrar por extension/mimetype)
  |
  v
Rechazar archivos peligrosos/no validos (tamaño, extension real vs
declarada -- responsabilidad del workflow de n8n, no de SINTEL)
  |
  v
POST /api/v1/core/_apps/facturas/upload-document/
  (Authorization: Bearer <access_token de la identidad tecnica>,
   multipart/form-data, campo "file")
  |
  v
SINTEL: FacturaUBLMixin.upload_document() -> service_importar_documento()
  -> pipeline universal (parser oficial, guardar_desde_dto()) -- n8n
  NUNCA parsea el XML por su cuenta
  |
  v
Respuesta 200/201/40x/422/500 (ver "Casos de uso" abajo)
```

**Diseño de nodos concreto (Gmail, N8N-SINTEL-02, listo para importar):**

| # | Nodo n8n | Configuracion |
|---|---|---|
| 1 | Gmail Trigger | Credencial OAuth2 (usuario la crea en n8n), poll cada 1-5 min, filtro `hasAttachment:true` |
| 2 | IF (filtrar relevante) | `$json.subject` o remitente coincide con la regla de negocio del buzon de facturas (a definir con el usuario -- no inventado aqui) |
| 3 | Loop Over Items (adjuntos) | Itera los adjuntos del correo |
| 4 | IF (es XML) | `$binary.data.fileExtension === 'xml'` -- descarta PDF/otros adjuntos del mismo correo sin bloquear el XML |
| 5 | Set (correlation_id) | `{{$json.id}}-{{$binary.data.fileName}}` -- generado por n8n, nunca reusa el `event_id` de SINTEL (son namespaces distintos, Fase 11) |
| 6 | HTTP Request | `POST /api/v1/core/_apps/facturas/upload-document/`, credencial "HTTP Header Auth" (`Authorization: Bearer <token de crear_identidad_tecnica_n8n>`), body multipart con el binario del XML |
| 7 | Switch (por status code) | `200/201` -> continuar (log exito); `409` -> log duplicado, sin alerta; `400/415/422` -> notificar "Documento rechazado" (Fase 10); `401/403` -> alerta TI (token expirado/identidad invalida, distinto de "documento rechazado"); `5xx` -> retry (n8n `Retry On Fail`, backoff) |
| 8 | Error Trigger (workflow-level) | Captura fallos no manejados (ej. token de Gmail revocado) -> notificacion TI/Administracion |

**Estado:** endpoint real habilitado y verificado con `manage.py check`
limpio, mas 13 tests nuevos de `integration_events` y 4 de seguridad
multi-tenant del endpoint (N8N-SINTEL-02, FASE 3/7). **No se ejecuto un
envio de correo real de punta a punta** (requiere la cuenta owner de
n8n + la credencial OAuth2 de Gmail, ambas pendientes del usuario) — el
endpoint SINTEL en si esta operativo y probado por el propio test suite
existente de `upload-document`
(`apps/tenant/core/tests/test_documentos_upload_api.py`,
`test_n8n_upload_document_security.py`).
**COMPLETED_WITH_DEFERRED** para el tramo email->n8n especificamente;
**BLOCKED_EXTERNAL_CREDENTIALS** para el tramo n8n->Gmail real (cuenta
owner + OAuth2, ambos pendientes del usuario).

## Workflow B/C/D — SINTEL Event -> Email / WhatsApp / Error

```
FacturaUBLMixin.upload_document() (u otro punto de dominio futuro)
  |
  v
apps.services.integration_events.publish_event(event_type=..., ...)
  |
  v
Celery: send_webhook_event (retry en errores transitorios, firmado HMAC)
  |
  v
POST <N8N_WEBHOOK_URL> (X-Sintel-Signature, X-Sintel-Event-Id, X-Sintel-Event-Type)
  |
  v
n8n: nodo Webhook -> [DISEÑADO, DEFERRED] valida firma -> switch por
     event_type -> Email/WhatsApp/registro de incidente segun status
```

**Estado del lado SINTEL:** implementado y conectado (Workflow A publica
`invoice.processed`/`invoice.duplicate` de verdad). **Estado del lado
n8n:** DEFERRED -- el workflow receptor (nodo Webhook + validacion HMAC
+ switch + nodos de Email/WhatsApp) no esta creado, requiere trabajo en
la UI de n8n que esta sesion no ejecuto (bloqueado por la cuenta owner
de n8n sin crear, ver banner arriba -- no por falta de diseño).

**Diseño de nodos concreto (N8N-SINTEL-02, WhatsApp = Business Cloud API
oficial de Meta, listo para importar en cuanto exista cuenta owner):**

| # | Nodo n8n | Configuracion |
|---|---|---|
| 1 | Webhook | `POST`, path dedicado (ej. `/sintel/events`), `Respond` inmediato 200 para no bloquear el retry de SINTEL |
| 2 | Code/Function (verificar HMAC) | Recalcula `HMAC-SHA256(body, N8N_WEBHOOK_SECRET)` y compara contra el header `X-Sintel-Signature` -- **rechaza (no procesa) si no coincide**, mismo criterio que `tasks.py::_firmar()` del lado SINTEL |
| 3 | Code/Function (idempotencia) | Verifica `event_id` contra almacenamiento propio de n8n (ej. `NoOp` + n8n data store, o Redis si n8n lo tiene disponible) -- si ya se proceso, `NoOp` y salir (Fase 11) |
| 4 | Switch (por `event_type`) | `invoice.processed` -> rama Email; `invoice.duplicate` -> rama log silencioso (`NoOp`); ninguna rama WhatsApp/urgente todavia (`invoice.failed` sigue sin publicarse, ver mas abajo) |
| 5a | Set (resolver destinatario) | Lee la matriz departamento->destinatarios->canales desde configuracion existente de n8n (variables de entorno o credencial, NO hardcodeada en el nodo -- Fase 10) |
| 5b | Gmail/SMTP (nodo oficial de envio) | Email al departamento resuelto en 5a |
| 5c | WhatsApp Business Cloud API (nodo oficial) | Credencial: Phone Number ID + WABA ID + token de acceso (el usuario los carga en la credencial de n8n, nunca en este workflow en texto plano); plantilla de mensaje pre-aprobada por Meta (WhatsApp Cloud API exige plantillas aprobadas para el primer mensaje de una conversacion, no texto libre arbitrario) |
| 6 | Error Trigger (workflow-level) | Fallo de envio (credencial invalida, destinatario rechazado, timeout) -> log + reintento manual, nunca reintento infinito silencioso |

Mapeo de reglas ya definido (Fase 8/17, para cuando el workflow del
lado n8n se construya):

| Evento SINTEL | Accion n8n (diseñada, no implementada) |
|---|---|
| `invoice.processed` (created=true) | Email al departamento (Contabilidad) |
| `invoice.duplicate` (created=false) | Log silencioso, sin notificacion (no es un error) |
| `invoice.failed` (DEFERRED, no publicado aun -- no hay punto de fallo claro cableado) | Email urgente + WhatsApp + registro de incidente |

**`invoice.failed` no se publica todavia (decision explicita, re-evaluada
en N8N-SINTEL-02 FASE 7, no un olvido):** `upload_document()` solo
publica en el camino `code in (200, 201)` (exito o duplicado). El
camino de error (400/415/422/500) no crea ninguna `Factura`, por lo que
no existe ningun `aggregate_uuid` real que el contrato `DomainEvent`
pueda referenciar sin inventarlo -- y n8n ya recibe el fallo
directamente en el codigo de respuesta HTTP del paso 6 del Workflow A
(sin necesidad de un evento adicional para ESE tramo). Publicar
`invoice.failed` solo tendria sentido para un fallo asincrono
*posterior* a la persistencia (hoy no existe ese caso en el pipeline
sincrono actual) -- si aparece, se cablea entonces, con un
`aggregate_uuid` real.

## Workflows exportados, listos para importar (N8N-SINTEL-02, 2026-09-10)

`docs/n8n/workflows/` -- JSON real (formato de exportacion de n8n) para
los 2 workflows de arriba, mas `README.md` con la checklist completa de
importacion (variables de entorno, credenciales, correccion de
`N8N_WEBHOOK_URL` para apuntar al servicio Docker `n8n`, no a
`127.0.0.1`). Construidos como archivo (no en vivo en la UI de n8n)
porque la cuenta owner de n8n existe pero Claude Code no tiene ni puede
tener la contraseña. Ningun secreto real esta embebido en los JSON.

## Catalogo N8N-* (Fase 16) — diseño, no implementado mas alla del piloto

```
N8N-INVOICES   -- Workflow A (piloto, parcialmente real -- ver arriba)
N8N-SALES      -- no iniciado
N8N-PURCHASES  -- no iniciado
N8N-INVENTORY  -- no iniciado
N8N-FINANCE    -- no iniciado
N8N-CUSTOMER   -- no iniciado
N8N-SYSTEM     -- solo diseñado: "rotar credenciales" (cada <7 dias, re-ejecutar
                  `manage.py crear_identidad_tecnica_n8n`), "webhook inbound"
                  (recibir eventos SINTEL, DEFERRED del lado n8n)
```

Cada workflow del catalogo, cuando se construya, debe declarar
(Fase 16): nombre, proposito, trigger, entradas, llamadas SINTEL,
outputs, retries, timeout, idempotencia, alertas, owner -- ninguno mas
alla de Workflow A tiene esta ficha completa todavia porque no se
construyo.

## Idempotencia (Fase 11, verificado en el diseño)

`DomainEvent.event_id` (UUID) es el identificador real. n8n, al recibir
un webhook, debe verificar `event_id` contra su propio almacenamiento
(nodo n8n "NoOp"/base de datos propia/Redis -- decision de
implementacion de n8n, no de SINTEL) antes de ejecutar la notificacion.
**No implementado del lado n8n** (mismo motivo que el resto de
Workflow B/C/D: requiere el workflow receptor real).

Del lado SINTEL, `event_id` nunca se reutiliza (generado con `uuid4()`
por evento, nunca derivado de asunto de correo/timestamp/filename, tal
como exige la Fase 11).
