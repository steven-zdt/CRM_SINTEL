# Workflows N8N-SINTEL-02 — listos para importar

**Por que estos archivos existen en vez de estar ya en la UI de n8n:**
n8n ya tiene cuenta owner creada (2026-09-10), pero Claude Code no tiene
ni puede tener la contrasena (regla del asistente: nunca entra
contrasenas/API keys en ningun campo, con o sin autorizacion). Por eso
los workflows se construyeron como JSON real (formato de exportacion de
n8n) en vez de en la UI en vivo -- se importan con un click y solo
falta conectar credenciales.

## Que hace cada archivo

| Archivo | Workflow | Fases de la mision |
|---|---|---|
| `N8N-INVOICES_workflow_A_email_to_sintel.json` | Gmail -> filtra XML -> `POST upload-document` -> switch por status -> notifica rechazos/errores de identidad | FASE 5, 6, 10, 12 |
| `N8N-EVENTS_workflow_receptor_sintel.json` | Webhook de SINTEL -> verifica firma HMAC -> idempotencia -> switch por `event_type` -> Email + WhatsApp | FASE 7 (lado n8n), 8, 9, 10, 11 |

Ningun archivo contiene una credencial, token o secreto real -- todo
sensible se referencia via `$env.<VARIABLE>` (variables de entorno del
contenedor n8n) o via credenciales de n8n marcadas `"id": "PENDIENTE"`
(el usuario las crea/selecciona al importar).

## Pasos para dejarlos operativos (todos del lado del usuario)

### 1. Importar

En la UI de n8n: **Workflows -> Import from File** -> seleccionar cada
`.json` de esta carpeta. Se importan inactivos (`"active": false`) a
proposito -- activarlos es la ultima accion, despues de revisar cada
nodo marcado `REVISAR` en sus notas.

### 2. Variables de entorno del contenedor n8n

**Correccion 2026-09-10:** el servicio `n8n` de `docker-compose.yaml`
usa la imagen oficial (`n8nio/n8n`), no el `x-app-base` con `env_file:
.env` que si usan `web`/`celery`/etc -- por eso NO heredaba el `.env`
completo (el README original decia lo contrario, corregido). Ya se
agregaron las variables de abajo, explicitas, al bloque `environment:`
del servicio `n8n` en `docker-compose.yaml` (referenciando el mismo
`.env` de la raiz via `${VARIABLE}`) -- **solo falta llenar sus
valores reales en ese mismo `.env` de la raiz**, no crear uno nuevo:

**Nota de seguridad (tradeoff deliberado, no un descuido):** la
decision original de N8N-SINTEL-01 fue que el JWT de la identidad
tecnica NUNCA viviera en un `.env`, solo como credencial cifrada
DENTRO de n8n. El REFRESH token es la excepcion: el nodo "Refrescar
token SINTEL" lo necesita dentro de un body JSON
(`POST /api/token/refresh/`), y los Code nodes de n8n no tienen acceso
a credenciales por diseño propio de n8n (solo nodos nativos como HTTP
Request pueden inyectar una credencial, y solo como header/query/basic
auth -- nunca dentro de un body arbitrario). Si esto no es aceptable,
la alternativa es guardar el ACCESS token (no el refresh) como
credencial "Header Auth" real en el nodo `Subir a SINTEL
(upload-document)` y aceptar rotarlo manualmente cada <15 min -- mucho
mas operativo/tedioso. Se opto por la variable de entorno.

```bash
# Identidad tecnica SINTEL (rotar cada <7 dias -- ver
# manage.py crear_identidad_tecnica_n8n --schema home)
SINTEL_N8N_REFRESH_TOKEN=<refresh token real, generado por el comando>

# N8N_WEBHOOK_SECRET ya tiene un valor real en el .env de la raiz
# (variable existente, usada tambien por config/settings.py) -- NO
# hace falta agregarla ni duplicarla, ya se pasa automaticamente al
# contenedor n8n con el fix de docker-compose.yaml.

# WhatsApp Business Cloud API
SINTEL_WHATSAPP_PHONE_NUMBER_ID=<Phone Number ID real de Meta>

# Matriz de departamentos (FASE 10) -- agregar mas variables si se
# agregan mas ramas al Switch de cualquiera de los 2 workflows
SINTEL_DEPT_CONTABILIDAD_EMAIL=<email real>
SINTEL_DEPT_CONTABILIDAD_WHATSAPP=<telefono real, formato E.164>
SINTEL_DEPT_ADMINISTRACION_EMAIL=<email real>
SINTEL_DEPT_ADMINISTRACION_WHATSAPP=<telefono real, formato E.164>
SINTEL_DEPT_TI_EMAIL=<email real>
```

Despues de editarlas: `docker compose up -d n8n` (recrea el contenedor
con las variables nuevas -- no alcanza con solo guardar el archivo).

### 3. Credenciales de n8n (UI, nunca en estos archivos)

- **Gmail OAuth2**: Credentials -> New -> Gmail OAuth2 API -> autorizar
  la cuenta Google del buzon de facturas. Nombrarla igual que aparece
  en los nodos (`Gmail -- buzon facturas SINTEL...`) para que el import
  la enlace sola, o reasignarla manualmente nodo por nodo si el nombre
  no calza exacto.
- **WhatsApp Business Cloud API**: Credentials -> New -> WhatsApp API ->
  cargar el token de acceso de Meta. Mismo criterio de nombre.

### 4. Conectar el webhook de salida en SINTEL (`N8N_WEBHOOK_URL`)

Una vez importado y activado `N8N-EVENTS...json`, n8n expone su URL de
webhook real (nodo "Webhook: eventos SINTEL" -> pestana "Webhook URLs").
**Importante:** el que llama a esa URL es el contenedor `celery` de
SINTEL (via `apps/services/integration_events/tasks.py`), no el host
-- por eso debe usarse el nombre de servicio Docker, no `127.0.0.1`:

```bash
# .env de SINTEL (raiz del proyecto, el que ya lee config/settings.py)
N8N_WEBHOOK_URL=http://n8n:5678/webhook/sintel-events
```

`127.0.0.1:5678` (el puerto publicado del contenedor n8n) solo es
alcanzable desde la maquina host, no desde otro contenedor de la misma
red de Docker Compose -- usar el nombre de servicio (`n8n`) evita ese
error comun.

### 5. Antes de activar en produccion — revisar los nodos WhatsApp

Ambos workflows tienen un nodo WhatsApp con texto libre (`textBody`).
**WhatsApp Business Cloud API exige una plantilla pre-aprobada por Meta
para el primer mensaje de cualquier conversacion** -- texto libre solo
funciona dentro de una ventana de 24h tras un mensaje previo del
destinatario. Cambiar la operacion del nodo a "Send Template" con el
nombre real de una plantilla aprobada antes de activar, o el envio
fallara en producción real la primera vez.

### 6. Validar (FASE 13, E2E real)

1. Enviar un correo de prueba con un XML valido al buzon conectado.
2. Confirmar en n8n (pestana Executions) que Workflow A corrio y que
   `Subir a SINTEL` devolvio 200/201.
3. Confirmar en SINTEL que la Factura se creo (`docker compose exec web
   python manage.py shell` o la UI).
4. Confirmar que Workflow B/C/D recibio el evento (Executions), la
   firma paso, y llegaron el email + WhatsApp de prueba.
5. Repetir el mismo correo (mismo adjunto) -> confirmar que NO se crea
   una segunda Factura ni se envia una segunda notificacion (FASE 11).

Ninguno de estos 5 pasos se puede completar sin las credenciales
reales del usuario -- una vez hechos, actualizar
`docs/n8n/N8N_MCP_E2E_EXECUTION.md`/`N8N_MCP_RELEASE_GATE.md` (FASE 17)
con la evidencia real.
