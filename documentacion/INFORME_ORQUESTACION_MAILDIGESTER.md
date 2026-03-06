# 📧 INFORME DETALLADO — Orquestación del Servicio MailDigester

**Fecha:** 2026-02-10  
**Versión:** v2.36  
**Objetivo:** Documentar el flujo completo de orquestación del servicio `maildigester` desde su inicio hasta su consumo en las apps.

---

## 📋 TABLA DE CONTENIDOS

1. [Arquitectura General](#arquitectura-general)
2. [Componentes del Servicio](#componentes-del-servicio)
3. [Flujo de Orquestación Completo](#flujo-de-orquestación-completo)
4. [Integración con Apps](#integración-con-apps)
5. [Endpoints API](#endpoints-api)
6. [Consumo desde UI](#consumo-desde-ui)
7. [Diagramas de Flujo](#diagramas-de-flujo)

---

## 🏗️ ARQUITECTURA GENERAL

### Principios de Diseño

- **Service Layer Pattern**: Lógica de negocio separada de modelos y vistas
- **SSoT (Single Source of Truth)**: 
  - Configuraciones de buzón: `apps.tenant.empresa.services.mailbox_provider`
  - Parsing UBL: `apps.tenant.facturas.services`
  - Pipeline universal: `apps.services.document_ingest`
- **Multi-tenant**: Aislamiento por esquema usando `schema_context`
- **API-First**: Todos los endpoints son JSON-only
- **Cero Signals**: Toda la lógica es explícita (sin Django signals)
- **Idempotencia**: Delegada a `upsert_factura_desde_ubl` (por CUFE)
- **Procesamiento Incremental**: Usa UIDs IMAP para evitar reprocesar correos

### Ubicación de Componentes

```
apps/services/maildigester/
├── __init__.py              # Exports principales
├── pipeline.py              # Orquestación principal
├── tasks.py                 # Tareas Celery
├── schemas.py               # DTOs (TypedDict)
├── inbox_client.py          # Cliente IMAP (RealIMAPClient, StubInboxClient)
├── extractors.py            # Extracción de adjuntos
├── detectors.py             # Detección de XML UBL
├── archives.py              # Descompresión (ZIP/RAR/7z)
├── exceptions.py            # Excepciones específicas
└── mail_service.py          # Servicio legacy (en migración)

apps/tenant/facturas/
├── services_mail_ingestion.py  # Orquestación de ingesta (enqueue_mail_ingestion)
├── inbox_state.py              # Estado del buzón (UIDs procesados)
├── models.py                   # MailIngestionRun, MailInboxState
└── api/views_mail_ingestion.py # Endpoints DRF

apps/tenant/core/
├── services/facturas_maildigester_adapter.py  # Adapter Core API → Facturas
└── api/views.py                               # Endpoints Core API
```

---

## 🔧 COMPONENTES DEL SERVICIO

### 1. Pipeline Principal (`pipeline.py`)

**Función principal:** `collect_invoice_xml_from_mailbox()`

**Responsabilidades:**
- Conectar a buzón de correo (IMAP)
- Obtener mensajes (hasta `limit_messages`)
- Extraer adjuntos de cada mensaje
- Descomprimir archivos (ZIP/RAR/7z) si es necesario
- Detectar XML UBL (o AttachedDocument) y extraer Invoice(s)
- Retornar lista de `InvoiceXMLDTO` (sin persistir)

**Función alternativa:** `collect_invoice_xml_from_mailbox_by_uid()`

**Características:**
- Procesamiento por UIDs IMAP (histórico completo + incremental)
- Soporte para cancelación cooperativa (`should_abort` callback)
- Retorna tupla `(lista de InvoiceXMLDTO, último_uid_procesado)`

**Flujo interno:**
```
1. Conectar → inbox_client.connect(config)
2. Obtener mensajes → client.fetch_messages_by_uid(start_uid, batch_size)
3. Para cada mensaje:
   a. Extraer adjuntos → client.get_attachments(message)
   b. Para cada adjunto:
      - Validar tamaño (max_attachment_mb)
      - Adivinar tipo → guess_file_kind()
      - Si es ZIP/RAR/7z → expand_archive()
      - Si es XML → detectar UBL → is_ubl_invoice()
      - Extraer Invoice(s) → extract_xml_from_attacheddocument()
   c. Finalizar mensaje → client.finalize() (marcar leído, mover)
4. Desconectar → client.disconnect()
```

### 2. Cliente de Buzón (`inbox_client.py`)

**Interfaz:** `InboxClient` (Protocol)

**Implementaciones:**

#### `RealIMAPClient`
- Implementación real usando `imaplib`
- Soporta:
  - IMAPS (993, TLS implícito)
  - IMAP (143) + STARTTLS
  - Autenticación, selección de carpeta
  - Búsqueda y fetch de mensajes por UID
  - Extracción de adjuntos
  - Finalización (marcar leído, mover)

**Métodos clave:**
- `connect(config: MailboxConfigDTO)`: Conecta y autentica
- `fetch_messages(limit: int)`: Obtiene mensajes (LEGACY, usa índices)
- `fetch_messages_by_uid(start_uid, batch_size)`: Obtiene mensajes por UID (recomendado)
- `get_attachments(message)`: Extrae adjuntos
- `finalize(message, mark_as_seen, move_to)`: Finaliza procesamiento
- `disconnect()`: Cierra conexión

#### `StubInboxClient`
- Implementación stub para pruebas/desarrollo
- No se conecta a servidor real
- Simula respuestas válidas

### 3. Extractores (`extractors.py`)

**Función:** `extract_attachments(message, max_mb=50)`

**Responsabilidades:**
- Extraer adjuntos de mensajes MIME
- Validar tamaños (prevenir DoS)
- Filtrar tipos relevantes (XML, ZIP, etc.)

**Estado:** ⚠️ FASE 1 (STUB) - Solo estructura, sin parsing real de MIME

### 4. Detectores (`detectors.py`)

**Funciones:**

#### `guess_file_kind(filename, content_type, content)`
- Adivina tipo de archivo por:
  - Extensión (`.xml`, `.zip`, `.rar`, `.7z`)
  - Magic bytes (primeros bytes del archivo)
  - Content-Type MIME

#### `extract_xml_from_attacheddocument(xml_text)`
- Extrae XMLs internos desde AttachedDocument UBL
- Si el XML es AttachedDocument con Invoice(s) en base64/CDATA, los decodifica
- **Estado:** ⚠️ FASE 1 (STUB) - Solo estructura

#### `is_ubl_invoice(xml_text)`
- Heurística mínima para detectar si un XML es factura UBL 2.1
- Verifica:
  - Presencia de elemento `<Invoice>`
  - Namespace UBL 2.1 (`urn:oasis:names:specification:ubl:schema:xsd:Invoice-2`)

### 5. Archivos Comprimidos (`archives.py`)

**Funciones:**

#### `is_supported_archive(filename, content_type)`
- Detecta si un archivo es formato soportado (ZIP, RAR, 7z)

#### `expand_archive(file: ExtractedFileDTO)`
- Descomprime archivo y retorna lista de archivos extraídos
- **Seguridad crítica:**
  - Rechaza path traversal (`..`)
  - Rechaza rutas absolutas
  - Normaliza rutas relativas
  - Limita número máximo de archivos (p. ej., 100)
  - Valida tamaños individuales

**Estado:** ⚠️ FASE 1 (STUB) - Solo validaciones de seguridad, sin descompresión real

### 6. Tareas Celery (`tasks.py`)

**Tarea principal:** `fetch_and_process_billing_mail`

**Decorador:**
```python
@shared_task(
    bind=True,
    name="apps.services.maildigester.tasks.fetch_and_process_billing_mail",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
```

**Parámetros:**
- `tenant_schema: str` - Esquema del tenant
- `config_id: int` - ID de MailInboxConfig (NO credenciales en payload)
- `limit_messages: int = 50` - Límite de mensajes
- `naturaleza: Optional[str] = None` - Naturaleza (se determina desde XML)

**Flujo de la tarea:**
```
1. Actualizar run → status="RUNNING"
2. Verificar cancelación cooperativa → _should_abort()
3. Resolver config desde BD (dentro de schema_context)
4. Obtener estado del buzón → get_or_create_inbox_state(config_id)
   - last_seen_uid: None = histórico completo, int = incremental
5. Procesar por lotes (UIDs):
   a. Obtener lote → collect_invoice_xml_from_mailbox_by_uid()
   b. Para cada XML:
      - Importar → facturas_services.upsert_factura_desde_ubl()
      - Contar: imported, duplicates, errors
   c. Actualizar estado → update_inbox_state(config_id, last_uid)
   d. Verificar cancelación antes de cada lote
6. Actualizar run → status="SUCCESS" o "FAILED"
```

**Funciones auxiliares:**

#### `_should_abort(tenant_schema, task_id)`
- Verifica cancelación cooperativa
- Lee estado `CANCEL_REQUESTED` desde BD (`MailIngestionRun`)

#### `_update_run(tenant_schema, task_id, **fields)`
- Actualiza `MailIngestionRun` de forma atómica
- Usa `select_for_update` para evitar condiciones de carrera

### 7. DTOs (`schemas.py`)

#### `MailboxConfigDTO`
```python
{
    "provider": "gmail" | "custom",
    "host": str,
    "port": int,
    "protocol": "imap" | "pop3",
    "ssl": bool,
    "starttls": bool,
    "username": str,
    "password": str,
    "mailbox": str,
    "max_attachment_mb": int,
    "move_processed_to": Optional[str],
    "mark_as_seen": bool,
    "smtp": Optional[Dict]
}
```

#### `InvoiceXMLDTO`
```python
{
    "source_email_id": str,
    "source_filename": Optional[str],
    "xml_text": str,
    "naturaleza": "VENTA" | "COMPRA",
    "metadata": Dict[str, Any]
}
```

#### `AttachmentDTO`
```python
{
    "filename": str,
    "content_type": str,
    "size_bytes": int,
    "content": bytes
}
```

#### `ExtractedFileDTO`
```python
{
    "filename": str,
    "guessed_type": "xml" | "zip" | "rar" | "7z" | "other",
    "size_bytes": int,
    "content": bytes
}
```

### 8. Excepciones (`exceptions.py`)

- `MailDigesterError`: Base exception
- `MailboxConnectionError`: Error de conexión/autenticación
- `AttachmentTooLarge`: Adjunto excede límite
- `ArchiveExpansionError`: Error al descomprimir
- `InvalidXMLDocument`: XML no válido
- `PathTraversalError`: Intento de path traversal
- `MimeTypeMismatch`: Content-Type no coincide

---

## 🔄 FLUJO DE ORQUESTACIÓN COMPLETO

### Fase 1: Inicio desde UI (Workspace)

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

**Trigger:** Usuario hace click en "Iniciar ingesta" (`#btn-run-mail-ingestion`)

**JavaScript:**
```javascript
// apps/tenant/core/templates/tenant/core/workspace.html (línea ~1409)
on("btn-run-mail-ingestion", "click", async () => {
  const configId = $("#mail-config-select")?.value;
  const limit = parseInt($("#mail-limit-input")?.value || "50");
  
  const res = await http("POST", "/api/v1/core/maildigester/run/", {
    config_id: parseInt(configId),
    limit_messages: limit,
  });
  
  // Iniciar polling para actualizar estado
  startMailRunsPolling();
});
```

### Fase 2: Core API Endpoint

**Endpoint:** `POST /api/v1/core/maildigester/run/`

**Ubicación:** `apps/tenant/core/api/views.py` → `CoreMailIngestionRunAPIView`

**Flujo:**
```python
# 1. Importar adapter (lazy import)
from apps.tenant.core.services.facturas_maildigester_adapter import core_run_mail_ingestion

# 2. Llamar adapter
data = core_run_mail_ingestion(
    config_id=request.data["config_id"],
    limit_messages=request.data.get("limit_messages", 50),
    started_by=request.user
)

# 3. Retornar 202 Accepted con run_id y task_id
return Response({
    "run_id": data["run_id"],
    "task_id": data["task_id"],
    "status": "PENDING"
}, status=202)
```

### Fase 3: Adapter Core → Facturas

**Ubicación:** `apps/tenant/core/services/facturas_maildigester_adapter.py`

**Función:** `core_run_mail_ingestion()`

**Responsabilidades:**
- Validar que la configuración existe y está activa
- Llamar a `apps.tenant.facturas.services_mail_ingestion.enqueue_mail_ingestion()`
- Retornar `run_id` y `task_id`

### Fase 4: Service Layer de Facturas

**Ubicación:** `apps/tenant/facturas/services_mail_ingestion.py`

**Función:** `enqueue_mail_ingestion()`

**Flujo:**
```python
# 1. Crear registro MailIngestionRun en estado PENDING
run = MailIngestionRun.objects.create(
    started_by=started_by,
    task_id="PENDING",
    status="PENDING",
    naturaleza="VENTA",  # Valor por defecto
    counts={"processed": 0, "xml_detected": 0, "imported": 0, "duplicates": 0, "errors": 0}
)

# 2. Obtener esquema del tenant
tenant_schema = connection.schema_name

# 3. Encolar tarea Celery (SIN credenciales en payload)
from apps.services.maildigester.tasks import fetch_and_process_billing_mail

async_res = fetch_and_process_billing_mail.apply_async(
    kwargs={
        "tenant_schema": tenant_schema,
        "config_id": config_id,  # Solo ID, NO credenciales
        "limit_messages": limit_messages,
    },
    queue="high_priority"
)

# 4. Actualizar run con task_id real
run.task_id = async_res.id
run.save()
```

### Fase 5: Tarea Celery

**Ubicación:** `apps/services/maildigester/tasks.py`

**Tarea:** `fetch_and_process_billing_mail`

**Flujo detallado:**

#### 5.1. Inicialización
```python
# 1. Actualizar run → status="RUNNING"
_update_run(tenant_schema, task_id, status="RUNNING")

# 2. Verificar cancelación
if _should_abort(tenant_schema, task_id):
    _update_run(tenant_schema, task_id, status="CANCELED")
    return {"ok": False, "canceled": True}
```

#### 5.2. Resolver Configuración
```python
# Dentro de schema_context
with schema_context(tenant_schema):
    # Leer configuración desde BD (SSoT)
    from apps.tenant.empresa.services.mailbox_provider import get_mailbox_config
    mailbox_config = get_mailbox_config(config_id)
    
    # Obtener estado del buzón (último UID procesado)
    from apps.tenant.facturas.inbox_state import get_or_create_inbox_state
    inbox_state = get_or_create_inbox_state(config_id)
    start_uid = inbox_state.last_seen_uid  # None = histórico completo
```

#### 5.3. Procesamiento por Lotes
```python
current_uid = start_uid
while True:
    # Verificar cancelación antes de cada lote
    if _should_abort(tenant_schema, task_id):
        # Actualizar estado con último UID antes de cancelar
        update_inbox_state(config_id, current_uid, total_messages_processed)
        _update_run(tenant_schema, task_id, status="CANCELED")
        return {"ok": False, "canceled": True}
    
    # Obtener lote de mensajes por UID
    xml_items, last_uid = pipeline.collect_invoice_xml_from_mailbox_by_uid(
        mailbox_config,
        start_uid=current_uid,
        batch_size=batch_size,
        naturaleza=naturaleza,
        should_abort=lambda: _should_abort(tenant_schema, task_id)
    )
    
    # Si no hay mensajes nuevos, terminar
    if not xml_items:
        break
    
    # Procesar XMLs del lote
    for item in xml_items:
        # Verificar cancelación durante el loop
        if _should_abort(tenant_schema, task_id):
            update_inbox_state(config_id, current_uid, total_messages_processed)
            _update_run(tenant_schema, task_id, status="CANCELED")
            return {"ok": False, "canceled": True}
        
        try:
            # SSoT: Importar usando servicio de facturas
            from apps.tenant.facturas import services as facturas_services
            facturas_services.upsert_factura_desde_ubl(
                file_or_text=item["xml_text"],
                naturaleza=naturaleza
            )
            counts["imported"] += 1
        except facturas_services.DuplicateNumero:
            counts["duplicates"] += 1
        except Exception as e:
            counts["errors"] += 1
            logger.warning("maildigester.import_error", extra={"error": str(e)})
    
    # Actualizar estado después de cada lote
    if last_uid is not None and last_uid != current_uid:
        update_inbox_state(config_id, last_uid, batch_messages)
        current_uid = last_uid
    
    # Si el lote está incompleto, no hay más mensajes
    if batch_messages < batch_size:
        break
```

#### 5.4. Finalización
```python
# Actualizar run → status="SUCCESS"
_update_run(tenant_schema, task_id, status="SUCCESS", counts=counts, finished_at=timezone.now())

return {"ok": True, "counts": counts, "last_uid": current_uid}
```

### Fase 6: Pipeline de Extracción

**Ubicación:** `apps/services/maildigester/pipeline.py`

**Función:** `collect_invoice_xml_from_mailbox_by_uid()`

**Flujo detallado:**

#### 6.1. Conexión
```python
# Crear cliente IMAP
client = RealIMAPClient()

# Conectar
client.connect(config)
```

#### 6.2. Obtención de Mensajes
```python
# Obtener mensajes por UID
messages = client.fetch_messages_by_uid(
    start_uid=start_uid,  # None = histórico completo, int = incremental
    batch_size=batch_size
)
```

#### 6.3. Procesamiento de Mensajes
```python
for message in messages:
    # Verificar cancelación cooperativa
    if should_abort and should_abort():
        break
    
    # Extraer adjuntos
    attachments = client.get_attachments(message)
    
    for attachment in attachments:
        # Validar tamaño
        if size_bytes > max_bytes:
            continue
        
        # Adivinar tipo
        file_kind = guess_file_kind(filename, content_type, content)
        
        # Si es archivo comprimido, expandirlo
        if file_kind in ("zip", "rar", "7z"):
            extracted_files = expand_archive(archive_file)
            for extracted in extracted_files:
                _process_file_for_invoice(...)
        
        # Si es XML directo, procesarlo
        elif file_kind == "xml":
            _process_file_for_invoice(...)
    
    # Finalizar mensaje (marcar leído, mover)
    if config.get("mark_as_seen") or config.get("move_processed_to"):
        client.finalize(message, mark_as_seen=..., move_to=...)
```

#### 6.4. Detección de Invoice UBL
```python
def _process_file_for_invoice(file, source_email_id, ...):
    # Decodificar a texto
    xml_text = content.decode("utf-8")
    
    # Verificar si es AttachedDocument
    attached_xmls = extract_xml_from_attacheddocument(xml_text)
    
    if attached_xmls:
        # Procesar cada Invoice extraído
        for invoice_xml in attached_xmls:
            if is_ubl_invoice(invoice_xml):
                invoice_xmls.append(InvoiceXMLDTO(...))
    else:
        # XML directo
        if is_ubl_invoice(xml_text):
            invoice_xmls.append(InvoiceXMLDTO(...))
```

### Fase 7: Importación de Facturas

**Ubicación:** `apps/tenant/facturas/services.py`

**Función:** `upsert_factura_desde_ubl()`

**Flujo:**
```python
# 1. Parsear XML UBL
# 2. Extraer DTO
# 3. Buscar factura existente por CUFE (idempotencia)
# 4. Si existe → retornar (idempotente)
# 5. Si no existe → crear nueva factura
# 6. Guardar anexos XML
```

**Nota:** Esta función está en proceso de migración al pipeline universal (`document_ingest`).

---

## 🔌 INTEGRACIÓN CON APPS

### 1. App Facturas

#### Modelos

**`MailIngestionRun`** (`apps/tenant/facturas/models.py`)
```python
class MailIngestionRun(models.Model):
    started_by = ForeignKey(User)
    started_at = DateTimeField(auto_now_add=True)
    finished_at = DateTimeField(null=True)
    task_id = CharField(max_length=128, unique=True, db_index=True)
    naturaleza = CharField(max_length=10, default="VENTA")
    status = CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    counts = JSONField(default=dict)  # {xml_detected, imported, duplicates, errors}
    summary = JSONField(default=dict)  # Detalles de ejecución
```

**Estados:**
- `PENDING`: Tarea encolada, esperando ejecución
- `RUNNING`: Tarea en ejecución
- `SUCCESS`: Tarea completada exitosamente
- `FAILED`: Tarea falló
- `CANCEL_REQUESTED`: Cancelación solicitada (cooperativa)
- `CANCELED`: Tarea cancelada

**`MailInboxState`** (`apps/tenant/facturas/models.py`)
```python
class MailInboxState(models.Model):
    mailbox_config = OneToOneField(MailInboxConfig)
    last_seen_uid = IntegerField(null=True)  # Último UID procesado
    total_processed = IntegerField(default=0)
    last_run_at = DateTimeField(null=True)
```

**Propósito:** Mantener estado del procesamiento incremental por buzón.

#### Servicios

**`enqueue_mail_ingestion()`** (`apps/tenant/facturas/services_mail_ingestion.py`)
- Crea `MailIngestionRun` en estado `PENDING`
- Encola tarea Celery
- Actualiza `task_id` con ID real de Celery

**`upsert_factura_desde_ubl()`** (`apps/tenant/facturas/services.py`)
- Parsear XML UBL
- Buscar factura existente por CUFE (idempotencia)
- Crear o actualizar factura
- Guardar anexos XML

#### Estado del Buzón

**`get_or_create_inbox_state(config_id)`** (`apps/tenant/facturas/inbox_state.py`)
- Obtiene o crea estado del buzón
- `last_seen_uid=None` → primera ejecución (histórico completo)
- `last_seen_uid=int` → ejecución incremental (solo UIDs > last_seen_uid)

**`update_inbox_state(config_id, last_uid, messages_processed)`**
- Actualiza estado después de procesar un lote
- Usa `transaction.atomic()` para evitar condiciones de carrera
- Solo actualiza si `last_uid > state.last_seen_uid`

### 2. App Empresa

#### Configuración de Buzón

**`MailInboxConfig`** (`apps/tenant/empresa/models.py`)
- Almacena configuración de buzón de correo
- Campos: `host`, `port`, `username`, `password`, `mailbox`, `is_active`, etc.

**`get_mailbox_config(config_id)`** (`apps/tenant/empresa/services/mailbox_provider.py`)
- Lee configuración desde BD
- Retorna `MailboxConfigDTO` (sin exponer credenciales en logs)

### 3. App Core (Tenant)

#### Adapter

**`facturas_maildigester_adapter.py`** (`apps/tenant/core/services/`)

**Funciones:**
- `core_run_mail_ingestion()`: Inicia ingesta
- `core_list_mail_runs()`: Lista ejecuciones
- `core_list_mail_configs()`: Lista configuraciones
- `core_test_mailbox_connection()`: Prueba conexión
- `core_stop_mail_ingestion_run()`: Detiene ejecución
- `core_get_mail_ingestion_run_details()`: Obtiene detalles
- `core_delete_mail_ingestion_run()`: Elimina ejecución

**Propósito:** Adaptar Core API a servicios de facturas (capa de abstracción).

---

## 🌐 ENDPOINTS API

### Core API (`/api/v1/core/maildigester/`)

#### 1. `POST /api/v1/core/maildigester/run/`
**View:** `CoreMailIngestionRunAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Request:**
```json
{
  "config_id": 1,
  "limit_messages": 50
}
```

**Response (202 Accepted):**
```json
{
  "run_id": 123,
  "task_id": "abc123-def456-...",
  "status": "PENDING"
}
```

**Flujo:**
1. Validar `config_id` existe y está activa
2. Llamar `core_run_mail_ingestion()`
3. Retornar `run_id` y `task_id`

#### 2. `GET /api/v1/core/maildigester/runs/`
**View:** `CoreMailIngestionRunsListAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Response:**
```json
{
  "results": [
    {
      "id": 123,
      "task_id": "abc123-...",
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:30:00Z",
      "finished_at": "2024-01-15T10:35:00Z",
      "counts": {
        "xml_detected": 10,
        "imported": 8,
        "duplicates": 2,
        "errors": 0
      }
    }
  ]
}
```

#### 3. `GET /api/v1/core/maildigester/configs/`
**View:** `CoreMailIngestionConfigsListAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "name": "Buzón Principal",
      "host": "imap.gmail.com",
      "mailbox": "INBOX",
      "is_active": true
    }
  ]
}
```

#### 4. `POST /api/v1/core/maildigester/configs/test/`
**View:** `CoreMailIngestionConfigTestAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Request:**
```json
{
  "config_id": 1
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Conexión exitosa"
}
```

#### 5. `POST /api/v1/core/maildigester/run/{run_id}/stop/`
**View:** `CoreMailIngestionRunStopAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Request:**
```json
{
  "force": false
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Cancelación solicitada"
}
```

**Flujo:**
1. Actualizar `MailIngestionRun` → `status="CANCEL_REQUESTED"`
2. La tarea Celery verifica `_should_abort()` y se cancela cooperativamente

#### 6. `GET /api/v1/core/maildigester/run/{run_id}/details/`
**View:** `CoreMailIngestionRunDetailsAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Response:**
```json
{
  "id": 123,
  "task_id": "abc123-...",
  "status": "SUCCESS",
  "counts": {...},
  "summary": {
    "details": [...]
  }
}
```

#### 7. `DELETE /api/v1/core/maildigester/run/{run_id}/`
**View:** `CoreMailIngestionRunDeleteAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated`

**Response (204 No Content):**

### Facturas API (`/api/v1/facturas/ingesta-correo/`)

#### 1. `POST /api/v1/facturas/ingesta-correo/run/`
**View:** `MailIngestionRunCreateAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated, IsTenantAdminOrReadOnly`

**Request/Response:** Similar a Core API

#### 2. `GET /api/v1/facturas/ingesta-correo/runs/`
**View:** `MailIngestionRunsListAPIView`  
**Autenticación:** `SessionAuthentication`  
**Permisos:** `IsAuthenticated, IsTenantAdminOrReadOnly`

**Response:** Lista de ejecuciones (paginada)

---

## 🖥️ CONSUMO DESDE UI

### Workspace HTML

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

**Sección:** `#mail-ingestion-panel` (línea ~371)

**Elementos:**
- Selector de configuración: `#mail-config-select`
- Input de límite: `#mail-limit-input`
- Botón iniciar: `#btn-run-mail-ingestion`
- Botón detener: `#btn-stop-mail-ingestion`
- Botón refrescar: `#btn-refresh-mail-runs`
- Tabla de ejecuciones: `#tbl-mail-runs`

### JavaScript

**Ubicación:** Inline en `workspace.html` (línea ~1336)

**Funciones principales:**

#### `loadMailIngestionPanel()`
```javascript
// 1. Cargar configuraciones desde empresa (SSoT)
const configsRes = await http("GET", "/api/v1/core/maildigester/configs/");

// 2. Cargar ejecuciones
const runsRes = await http("GET", "/api/v1/core/maildigester/runs/");

// 3. Renderizar tabla de ejecuciones
```

#### `startMailRunsPolling()`
```javascript
// Polling cada 5 segundos para actualizar estado de ejecuciones
setInterval(async () => {
  const runningRows = tbody.querySelectorAll('tr');
  let hasRunning = false;
  // Verificar si hay ejecuciones en curso
  if (hasRunning) {
    await loadMailIngestionPanel();
  } else {
    clearInterval(mailRunsPollingInterval);
  }
}, 5000);
```

#### Handler "Iniciar ingesta"
```javascript
on("btn-run-mail-ingestion", "click", async () => {
  const res = await http("POST", "/api/v1/core/maildigester/run/", {
    config_id: parseInt(configId),
    limit_messages: limit,
  });
  
  // Iniciar polling
  startMailRunsPolling();
});
```

#### Handler "Detener ingesta"
```javascript
on("btn-stop-mail-ingestion", "click", async () => {
  const res = await http("POST", `/api/v1/core/maildigester/run/${runId}/stop/`, {
    force: false
  });
  
  // Recargar panel
  await loadMailIngestionPanel();
});
```

### Assets

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/assets_maildigester.html`

**Contenido:**
- Scripts JavaScript para maildigester
- Estilos CSS (si aplica)

---

## 📊 DIAGRAMAS DE FLUJO

### Flujo Completo (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUARIO (Workspace UI)                       │
│  Click "Iniciar ingesta" → POST /api/v1/core/maildigester/run/  │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Core API (CoreMailIngestionRunAPIView)              │
│  1. Validar request                                             │
│  2. Llamar adapter → core_run_mail_ingestion()                 │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│         Adapter (facturas_maildigester_adapter.py)              │
│  1. Validar config_id existe y está activa                     │
│  2. Llamar → enqueue_mail_ingestion()                          │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│    Service Layer (services_mail_ingestion.py)                   │
│  1. Crear MailIngestionRun (status="PENDING")                  │
│  2. Encolar tarea Celery → fetch_and_process_billing_mail     │
│  3. Actualizar run.task_id                                     │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Celery Worker (cola: high_priority)                 │
│  Tarea: fetch_and_process_billing_mail                         │
│  1. Actualizar run → status="RUNNING"                          │
│  2. Resolver config desde BD (schema_context)                  │
│  3. Obtener estado buzón (last_seen_uid)                      │
│  4. Procesar por lotes (UIDs):                                 │
│     a. collect_invoice_xml_from_mailbox_by_uid()                │
│     b. Para cada XML → upsert_factura_desde_ubl()               │
│     c. Actualizar estado (last_seen_uid)                        │
│  5. Actualizar run → status="SUCCESS"                          │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Pipeline (pipeline.py)                             │
│  1. Conectar IMAP → RealIMAPClient.connect()                   │
│  2. Obtener mensajes → fetch_messages_by_uid()                 │
│  3. Para cada mensaje:                                          │
│     a. Extraer adjuntos → get_attachments()                     │
│     b. Adivinar tipo → guess_file_kind()                       │
│     c. Si ZIP/RAR/7z → expand_archive()                        │
│     d. Si XML → detectar UBL → is_ubl_invoice()                │
│     e. Extraer Invoice(s) → extract_xml_from_attacheddocument()│
│  4. Retornar lista de InvoiceXMLDTO                            │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│         Service Facturas (services.py)                           │
│  upsert_factura_desde_ubl(xml_text):                            │
│  1. Parsear XML UBL                                             │
│  2. Buscar por CUFE (idempotencia)                              │
│  3. Crear o actualizar Factura                                  │
│  4. Guardar anexos XML                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Cancelación Cooperativa

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUARIO (Workspace UI)                       │
│  Click "Detener ingesta" → POST /api/v1/core/maildigester/     │
│                                run/{run_id}/stop/               │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│         Core API (CoreMailIngestionRunStopAPIView)              │
│  1. Actualizar MailIngestionRun → status="CANCEL_REQUESTED"    │
└──────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Celery Worker (tarea en ejecución)                 │
│  Loop de procesamiento:                                         │
│  1. Antes de cada lote:                                         │
│     → _should_abort() → Lee BD → status="CANCEL_REQUESTED"?    │
│     → Si True: Actualizar estado, retornar CANCELED             │
│  2. Durante procesamiento de XMLs:                               │
│     → _should_abort() → Si True: Cancelar inmediatamente        │
│  3. Actualizar run → status="CANCELED"                          │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Procesamiento Incremental (UIDs)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Primera Ejecución                            │
│  last_seen_uid = None                                            │
│  → Procesar desde UID 1 (histórico completo)                   │
│  → Procesar lotes de 100 mensajes                               │
│  → Actualizar last_seen_uid = último UID procesado              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Ejecuciones Subsecuentes                      │
│  last_seen_uid = 500 (ejemplo)                                   │
│  → Procesar solo UIDs > 500 (incremental)                      │
│  → Procesar lotes de 100 mensajes                               │
│  → Actualizar last_seen_uid = nuevo último UID                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 SEGURIDAD Y MULTI-TENANCY

### Aislamiento por Esquema

**Todas las operaciones se ejecutan dentro de `schema_context`:**

```python
with schema_context(tenant_schema):
    # Leer configuración
    mailbox_config = get_mailbox_config(config_id)
    
    # Leer estado del buzón
    inbox_state = get_or_create_inbox_state(config_id)
    
    # Importar facturas (persistencia en esquema correcto)
    facturas_services.upsert_factura_desde_ubl(xml_text)
```

### Seguridad de Credenciales

**⚠️ CRÍTICO:** Las credenciales NO se envían en el payload de Celery.

**Flujo seguro:**
1. UI envía solo `config_id` al endpoint
2. Endpoint valida que `config_id` existe
3. Tarea Celery lee configuración desde BD dentro de `schema_context`
4. Credenciales nunca aparecen en logs ni en cola de Celery

### Validaciones de Seguridad

**Archivos comprimidos:**
- Rechaza path traversal (`..`)
- Rechaza rutas absolutas
- Limita número máximo de archivos (100)
- Valida tamaños individuales

**Adjuntos:**
- Valida tamaño máximo (`max_attachment_mb`)
- Filtra tipos relevantes (XML, ZIP, etc.)

---

## 📈 MÉTRICAS Y LOGGING

### Logging Estructurado

**Logger:** `maildigester`

**Eventos principales:**
- `maildigester.start`: Inicio de tarea
- `maildigester.mode`: Modo (histórico/incremental)
- `maildigester.end`: Finalización exitosa
- `maildigester.task_failure`: Error en tarea
- `maildigester.import_error`: Error al importar XML
- `maildigester.abort_check_error`: Error al verificar cancelación
- `maildigester.update_run_error`: Error al actualizar run

**Formato:**
```python
logger.info("maildigester.start", extra={
    "tenant_schema": tenant_schema,
    "task_id": task_id,
    "config_id": config_id
})
```

### Métricas en `MailIngestionRun`

**Campo `counts` (JSON):**
```json
{
  "processed": 10,      // Mensajes procesados
  "xml_detected": 12,   // XMLs detectados
  "imported": 10,       // Facturas importadas
  "duplicates": 2,      // Duplicados (idempotencia)
  "errors": 0           // Errores
}
```

**Campo `summary` (JSON):**
```json
{
  "details": [
    {"status": "imported", "numero": "FAC-123"},
    {"status": "duplicate", "message": "La factura ya existe."}
  ]
}
```

---

## 🔄 REINTENTOS Y MANEJO DE ERRORES

### Reintentos Automáticos (Celery)

**Solo para errores transitorios:**
- `ConnectionError`: Error de conexión a servidor IMAP
- `TimeoutError`: Timeout de conexión
- `OSError`: Error de sistema operativo

**Configuración:**
```python
@shared_task(
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
```

**NO reintenta:**
- `AttributeError`: Errores de programación
- `ValidationError`: Errores de validación
- `DuplicateNumero`: Duplicados (idempotencia)

### Manejo de Errores en Pipeline

**Estrategia:** Continuar con otros mensajes si uno falla

```python
try:
    # Procesar mensaje
    ...
except Exception:
    # Log error pero continuar
    continue
```

**Errores críticos:**
- `MailboxConnectionError`: No se puede conectar → falla toda la tarea
- `PathTraversalError`: Intento de path traversal → rechazar archivo
- `ArchiveExpansionError`: Error al descomprimir → saltar archivo

---

## 🎯 INTEGRACIÓN CON PIPELINE UNIVERSAL

### Estado Actual

**`mail_service.py` (legacy):**
- ⚠️ En proceso de migración
- Usa `ingest_document` del pipeline universal (condicional)
- Fallback a procesamiento legacy si no está disponible

**Migración futura:**
- `pipeline.py` → usar `document_ingest.ingest_document()` para parsear XMLs
- Eliminar dependencia de `xml_parser` legacy
- Usar DTOs del pipeline universal

### Flujo Propuesto (Futuro)

```
Pipeline MailDigester:
  1. Extraer XMLs desde correo
  2. Para cada XML:
     → ingest_document(content=xml_bytes, preview=False)
     → Retorna DTO
     → Materializar → guardar_factura_desde_dto(dto)
```

---

## 📝 RESUMEN EJECUTIVO

### Puntos Clave

1. **Orquestación Multi-Capa:**
   - UI → Core API → Adapter → Service Layer → Celery → Pipeline → Facturas

2. **Procesamiento Incremental:**
   - Usa UIDs IMAP para evitar reprocesar correos
   - Estado persistido en `MailInboxState`

3. **Cancelación Cooperativa:**
   - UI marca `CANCEL_REQUESTED` en BD
   - Tarea verifica periódicamente y se cancela

4. **Seguridad:**
   - Credenciales nunca en payload de Celery
   - Aislamiento por esquema (`schema_context`)
   - Validaciones de path traversal

5. **Idempotencia:**
   - Delegada a `upsert_factura_desde_ubl` (por CUFE)
   - Duplicados contados pero no fallan

6. **Observabilidad:**
   - Logging estructurado
   - Métricas en `MailIngestionRun.counts`
   - Estado persistido en BD

### Flujo Simplificado

```
Usuario → UI → Core API → Adapter → Service → Celery → Pipeline → IMAP
                                                                    ↓
                                                              XMLs extraídos
                                                                    ↓
                                                              Pipeline Universal
                                                                    ↓
                                                              DTOs generados
                                                                    ↓
                                                              Service Facturas
                                                                    ↓
                                                              Facturas persistidas
```

---

**Última actualización:** 2026-02-10  
**Autor:** Sistema de Documentación Automática
