# Document Intake Service — Arquitectura (FASE 32)

**Fecha:** 2026-08-25. Documento canónico de la misión "Mail Hub ->
Document Intake Service". Complementa `MAIL_HUB_BASELINE.md` (auditoría +
bitácora de bugs encontrados/corregidos) — este documento describe el
sistema **resultante**, no la investigación.

---

## 1. Principio arquitectónico

El Document Intake Service **no conoce** Factura/Venta/Compra/Cliente/
Proveedor/Inventario/Banco/Contabilidad/Nómina. Conoce únicamente:
mensaje/correo/adjunto/archivo/XML/metadatos/tipo documental/origen/
contexto tenant/evento de documento. Las aplicaciones de dominio deciden
qué hacer con el documento, implementando un `DocumentHandler` propio.

```
                    DOCUMENT INTAKE
                          |
        +-----------------+-----------------+
        |                 |                 |
       MAIL              API              UPLOAD
        |                 |                 |
        +-----------------+-----------------+
                          v
                 ReceivedDocument (FASE 6)
                          v
                 DocumentDispatcher (FASE 10)
                          |
            +-------------+-------------+
            v             v             v
        FACTURAS       COMPRAS        OTROS
     (InvoiceHandler) (PurchaseDocumentHandler)
            v
     FacturaBusinessService
   (SSoT ya existente, reutilizado)
```

## 2. Capas y ubicación en el repo

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Contratos transversales | `apps/services/document_intake/contracts.py` | `ReceivedDocument`, `ProcessingResult`, `ProcessingStatus`, `DocumentSource`, `DocumentHandler` (Protocol) |
| Dispatcher | `apps/services/document_intake/dispatcher.py` | `DocumentDispatcher` (registro handler por tipo + ejecución + logging) |
| Detección/normalización (reutilizado, no duplicado) | `apps/services/document_ingest/ingest_service.py::ingest_document()` | Parsea XML -> DTO canónico. Ya existía; el Document Intake Service lo consume, no lo reimplementa |
| Canal MAIL (reutilizado) | `apps/services/maildigester/` | IMAP, extracción de adjuntos, ZIP, detección de tipo. Sin cambios de arquitectura en esta misión, solo corrección de bugs (ver Baseline §5, §8, §12, §15) |
| Handler Facturas | `apps/tenant/facturas/document_intake/invoice_handler.py` | `InvoiceHandler` — traduce `ReceivedDocument` -> `FacturaBusinessService.guardar_desde_dto()` |
| Handler Compras | `apps/tenant/compras/document_intake/purchase_handler.py` | `PurchaseDocumentHandler` — registrado, retorna `REQUIRES_REVIEW` (ver §7) |

## 3. Contratos (FASE 6-9)

### `ReceivedDocument` (frozen dataclass)

```python
tenant_schema: str
source: DocumentSource            # EMAIL | UPLOAD | API | IMPORT
content: bytes
filename: str | None
mime_type: str | None
document_type: str | None         # "invoice" | "creditnote" | "purchase_document" | ...
message_id: str | None            # canal EMAIL
attachment_id: str | None         # canal EMAIL
sender: str | None
received_at: datetime | None
metadata: dict[str, Any]          # via de escape (ej: empresa_id resuelto por el canal)
document_id: str                  # uuid4 autogenerado
```

Deliberadamente **no** incluye `factura_id`/`compra_id`/`cliente_id`/
`proveedor_id` ni CUFE obligatorio: esos son conceptos de dominio.

### `ProcessingResult` (dataclass)

```python
status: ProcessingStatus   # SUCCESS | DUPLICATE | INVALID | REQUIRES_REVIEW | FAILED | PARTIAL
document_id: str
source: DocumentSource
handler: str | None        # nombre de la clase que proceso
domain: str | None         # "facturas" | "compras" | ...
errors: list[str]
warnings: list[str]
metadata: dict[str, Any]   # ej: {"numero":..., "naturaleza":..., "cufe":...}
```

`ProcessingResult.ok` es `True` solo para `SUCCESS`/`DUPLICATE` — un
`PARTIAL`/`FAILED`/`REQUIRES_REVIEW` nunca se reporta como éxito (mismo
principio de FASE 2 aplicado al contrato transversal).

### `DocumentHandler` (Protocol)

```python
def can_handle(self, document: ReceivedDocument) -> bool: ...
def handle(self, document: ReceivedDocument) -> ProcessingResult: ...
```

Sin fábrica gigantesca: cada handler es una clase autocontenida en el
paquete de su propio dominio, registrada explícitamente (sin signals) vía
una función `register()` en `apps/tenant/<dominio>/document_intake/__init__.py`.

### `DocumentDispatcher`

Registro `dict[document_type_base -> DocumentHandler]` + `dispatch()`:
normaliza `document_type` (`"invoice.ubl21"` -> `"invoice"`), busca
handler, ejecuta, envuelve cualquier excepción del handler en
`ProcessingResult(status=FAILED)` (nunca deja que un handler roto tumbe el
dispatcher), loggea cada paso (`document_intake.dispatching` /
`.dispatched` / `.no_handler` / `.handler_exception`) sin loggear jamás
contenido del documento ni credenciales.

Instancia compartida a nivel de módulo:
`apps.services.document_intake.dispatcher.dispatcher` — un solo registro
para todo el proyecto, poblado por cada dominio consumidor.

## 4. Integración Facturas (FASE 11, primer consumidor real)

`InvoiceHandler.handle()`:

1. `ingest_document(content, filename, mime_type, kind_hint="xml", preview=True, async_mode=False)` — reutiliza el pipeline universal existente (**no** un segundo parser UBL).
2. `FacturaBusinessService.guardar_desde_dto(dto, xml_text, file_bytes, file_type="xml", empresa_id=...)` — reutiliza el SSoT real: `_resolver_naturaleza()`, vinculación cliente/proveedor, idempotencia por CUFE, distinción factura/nota-crédito vía `is_credit_note` interno. **Un solo handler cubre `invoice`, `creditnote` y `debitnote`** porque `guardar_desde_dto()` ya distingue internamente — no se crean tres handlers duplicados.
3. Mapea `status_code` real -> `ProcessingStatus`: `201` -> `SUCCESS`, `200 + created=False` -> `DUPLICATE`, cualquier otro -> `FAILED`.

`empresa_id` viaja en `ReceivedDocument.metadata["empresa_id"]` — nunca se infiere del contenido del documento ni de una fuente de configuración distinta a la del canal de entrada (ver Baseline §12 sobre la fuente-de-verdad-divergente que existía antes).

Verificado con persistencia real (test `apps/tenant/facturas/tests/test_document_intake_invoice_handler.py`, 4 tests, todos contra BD real vía `SintelTenantTestCase`): creación real, idempotencia real (mismo CUFE no duplica), tipo no soportado no crashea (`REQUIRES_REVIEW`), `empresa_id` ausente no crashea (`INVALID`).

## 5. Integración Compras (FASE 23/24 — preparado, no operativo)

`PurchaseDocumentHandler` está registrado (`document_type="purchase_document"`)
y responde `REQUIRES_REVIEW` con un `warning` explícito. Decisión
deliberada, no un olvido: la misión prohíbe expresamente crear Inventario
automáticamente "sin regla explícita", y esa regla (¿cuándo un documento de
compra genera una `OrdenCompra`/`RecepcionCompra` real? ¿dispara
Inventario o no?) no existe todavía en el dominio Compras. Inventarla aquí
excedería el alcance mínimo y el principio de "no fusionar dominios".
Implementarla es la extensión natural de una fase futura, una vez el dueño
de Compras defina esa regla.

**Prueba de extensibilidad (FASE 24):** registrar `PurchaseDocumentHandler`
no requirió tocar `InvoiceHandler`, `DocumentDispatcher`,
`apps/services/maildigester/` (IMAP/ZIP/detector/pipeline), ni
`tasks.py` (Celery). Verificado: ambos handlers coexisten en el mismo
`dispatcher` compartido sin colisión.

## 6. Multi-canal (FASE 25)

El contrato `ReceivedDocument` es agnóstico del canal por diseño (campo
`source: DocumentSource`). El canal **EMAIL** es el único con un productor
real conectado hoy (ver §8, nota de alcance). **UPLOAD/API/IMPORT** no
tienen un productor conectado todavía — la prueba de FASE 25 en esta misión
es de **contrato**, no de productor: los tests de `InvoiceHandler`
construyen `ReceivedDocument` con `source=DocumentSource.EMAIL` y
`source=DocumentSource.UPLOAD` indistintamente y ambos convergen en el
mismo `DocumentDispatcher.dispatch()` sin ninguna rama condicional por
canal — el dispatcher y los handlers son literalmente ciegos al canal de
origen. Conectar un productor real para UPLOAD/API (ej: un endpoint DRF que
construya `ReceivedDocument` desde un archivo subido) es directo pero
deliberadamente fuera del alcance mínimo de esta misión (no hay un
requisito de negocio concreto para UPLOAD/API todavía).

## 7. `tasks.py` rewireado al dispatcher (MAIL-16, cerrado)

**Actualizado — ya NO es una nota de alcance diferido.** En la ronda
MAIL-16, `apps/services/maildigester/tasks.py::fetch_and_process_billing_mail()`
se rewireó para llamar `dispatcher.dispatch(ReceivedDocument(...))` en vez
de `FacturaBusinessService.guardar_desde_dto()` directo. `tasks.py` **ya no
importa ningún dominio consumidor** (`apps.tenant.facturas`,
`apps.tenant.compras`, etc.) -- el único símbolo transversal que conoce es
`apps.services.document_intake`. `FacturaBusinessService.guardar_desde_dto()`
sigue siendo el SSoT real de persistencia; lo que cambió es **cómo** se le
llama (a través de `InvoiceHandler`), no que se le llama.

Cada dominio se auto-registra como consumidor desde su propio
`AppConfig.ready()`:
`apps/tenant/facturas/apps.py::FacturasConfig.ready()` y
`apps/tenant/compras/apps.py::ComprasConfig.ready()` llaman
`document_intake.register()` de su propio paquete. Esto significa que
agregar un tercer dominio consumidor (empleados/gastos/proyectos/bancos)
**nunca requiere modificar `tasks.py`, el dispatcher, ni ningún handler
existente** -- solo crear el paquete `document_intake/` del nuevo dominio
y su propio `ready()`. Precedente en el propio código base:
`apps/tenant/core/apps.py::TenantCoreConfig.ready()` ya usaba este patrón
para registro de admin/signals antes de esta misión.

Verificado end-to-end contra BD real (rollback vía `transaction.atomic()`):
creación real de `Factura` a través del camino completo
`fetch_and_process_billing_mail` -> `dispatcher.dispatch()` ->
`InvoiceHandler` -> `FacturaBusinessService.guardar_desde_dto()`, más
idempotencia (segunda ejecución del mismo documento -> `DUPLICATE`, sin
segunda `Factura`). Confirmado también con el test committeado
`tests/services/maildigester/test_tasks.py`.

## 8. Seguridad

- **Credenciales** (FASE 15): `MailInboxConfig.password`/`imap_password`/
  `smtp_password` se cifran en reposo con Fernet
  (`apps/services/security/crypto.py`, dependencia `cryptography` ya
  existente). `get_mailbox_config()` (el único punto real de resolución de
  credenciales para conectar) descifra con graceful degradation (clave
  rotada o fila legacy en texto plano -> usa el valor crudo, nunca crashea,
  nunca loggea el valor). Nunca se serializan (`write_only=True`), nunca se
  envían al payload de Celery (solo viaja `config_id`), nunca se muestran
  en Django admin (`PasswordInput(render_value=False)` + cifrado en
  `clean()` si el operador escribe uno nuevo).
- **Observabilidad** (FASE 26): todo log usa `extra={...}` estructurado
  (`tenant_schema`, `task_id`/`document_id`, `handler`, `status`, `error`/
  `error_type`, nunca el contenido del documento ni credenciales).
- **Clasificación de errores** (FASE 3): `_clasificar_excepcion()` en
  `tasks.py` distingue `transient/programming/domain/validation/security/
  unknown`; `programming`/`security` se loggean con `logger.error` +
  `exc_info=True` (nunca bajo un `except Exception` silencioso genérico).

## 9. Tenant isolation (FASE 14)

- Celery payload lleva únicamente `config_id` (nunca credenciales) —
  resolución real dentro de `schema_context(tenant_schema)`.
- `empresa_id` se resuelve explícitamente desde `MailInboxConfig.empresa_id`
  dentro del schema del tenant, nunca se infiere del contenido del
  documento (evita que un XML manipulado spoofee la empresa destino).
- `MailInboxConfig`/`MailIngestionRun`/`MailInboxState`/`Factura` heredan
  todos de `SintelTenantBaseModel` (aislamiento por schema de PostgreSQL,
  el mecanismo existente del proyecto — sin cambios en esta misión).

## 10. Idempotencia en dos niveles (FASE 13)

- **Nivel dominio (verificado, real):** `FacturaBusinessService.guardar_desde_dto()`
  deduplica por CUFE/CUDE (y por `numero` como fallback si el documento no
  trae CUFE) — un reintento del mismo documento nunca crea una segunda
  `Factura`. Verificado end-to-end tanto vía `tasks.py` como vía
  `InvoiceHandler`/`DocumentDispatcher` (dos caminos independientes, mismo
  resultado).
- **Nivel mail (preexistente, sin cambios en esta misión):**
  `MailInboxState.last_seen_uid` evita reprocesar el mismo UID IMAP en
  ejecuciones sucesivas. Coexiste con la idempotencia de dominio — ninguna
  sustituye a la otra, tal como exige la misión.

## 11. Estados

`MailIngestionRun.status`: `PENDING -> RUNNING -> {SUCCESS | PARTIAL_SUCCESS
| FAILED | CANCELED}` (mas `CANCEL_REQUESTED`/`ABORTED`). `PARTIAL_SUCCESS`
es un valor nuevo de esta misión (migración `0038_partial_success_status`).
Regla real (FASE 2): `SUCCESS` solo si `errors==0`; `PARTIAL_SUCCESS` si
`errors>0` pero `imported>0 or duplicates>0`; `FAILED` si `errors>0` y nada
se importó ni deduplicó.

`ProcessingResult.status`: `SUCCESS | DUPLICATE | INVALID |
REQUIRES_REVIEW | FAILED | PARTIAL` — vocabulario del contrato transversal,
deliberadamente más granular que el de `MailIngestionRun` (ese vive a nivel
de ejecución completa del buzón; `ProcessingResult` vive a nivel de un
documento individual).

## 12. Futuros consumidores

Agregar un dominio nuevo (empleados/gastos/proyectos/bancos) requiere
únicamente: una clase con `can_handle()`/`handle()` en
`apps/tenant/<dominio>/document_intake/`, un `register()` en ese mismo
paquete, y una llamada a ese `register()` desde el `ready()` del
`AppConfig` del dominio. No requiere tocar `apps/services/maildigester/`,
`apps/services/document_ingest/`, `apps/services/document_intake/dispatcher.py`,
ni ningún handler existente — demostrado en la práctica al agregar Compras
(§5) sin tocar Facturas, y reafirmado por el rewiring de `tasks.py` (§7):
el productor de documentos (`tasks.py`) tampoco necesita saber qué
dominios están registrados.

## 13. Detalle por documento -- `DocumentProcessing` (MAIL-17/18)

`MailIngestionRun.counts`/`summary` dan el agregado de una ejecución
completa, pero no una fila consultable por documento individual.
`DocumentProcessing` (modelo nuevo, `apps/tenant/facturas/models.py`,
migración `0039_document_processing`) resuelve esto: una fila por cada
`ReceivedDocument` que pasó por el dispatcher, con
`run` (FK a `MailIngestionRun`, `CASCADE`), `document_id`, `source`,
`filename`, `document_type`, `handler`, `domain`, `status` (mismo
vocabulario que `ProcessingStatus`), `numero`, `error_message`,
`created_at`. Se crea desde `tasks.py` en los 3 puntos donde un documento
puede terminar su procesamiento: error de parsing, DTO vacío, y el
resultado real de `dispatcher.dispatch()` (incluyendo `SUCCESS`, no solo
los casos de error -- el detalle debe existir para todo documento, no solo
para los que fallan).

**Bug real corregido en el camino** (hallado verificando este mismo
escenario, no antes): el log de `maildigester.parse_error` usaba
`extra={"message": error_msg}` -- `"message"` es un atributo reservado de
`logging.LogRecord`, así que esa llamada lanzaba
`KeyError("Attempt to overwrite 'message' in LogRecord")` **cada vez** que
se ejecutaba, es decir, en cada documento con error de parsing real. El
error real quedaba enmascarado bajo ese `KeyError` distinto (contado dos
veces en `counts["errors"]`: una vez por el flujo normal, otra por la
excepción de logging escapando al handler exterior). Corregido (`error_detail`
en vez de `message`) y verificado con un XML inválido real: ahora un solo
`DocumentProcessing(status=INVALID, error_message=<mensaje real y legible>)`.

**API**: `GET /api/v1/facturas/ingesta-correo/runs/<run_id>/documents/`
(`MailIngestionRunDocumentsAPIView`, filtra por `run_id` + `empresa_id` del
usuario autenticado). **Frontend** (`list_factura.html` +
`facturas_main.js`): botón "Historial de Ingestas" abre un offcanvas con
los runs recientes (fecha, badges de `imported`/`duplicates`/`errors`
reales -- nunca "Ejecución exitosa" si `imported=0` y hay errores, mismo
principio de FASE 2 aplicado a la UI), cada uno expandible a un segundo
offcanvas con el detalle por documento (número/estado/handler/error). Todo
contenido proveniente del documento (filename, error_message) se escapa
antes de insertarse en el DOM (`_escapeHtml`) -- viene de correos
externos, no es confiable.

**Bug preexistente encontrado y corregido al mismo tiempo, sin relación
con MAIL-17/18 en sí**: `facturas.api.js::syncMailbox()`/`listMailRuns()`
apuntaban a `/api/v1/core/maildigester/run|runs/`, endpoints que **nunca
llegaron a implementarse** (comentados explícitamente "No existe" en
`apps/tenant/core/api/urls.py`) -- cualquier llamada real habría devuelto
404. Redirigidos a los endpoints reales y ya funcionales de `facturas`
(`/api/v1/facturas/ingesta-correo/run|runs/`).

---

Ver `MAIL_HUB_BASELINE.md` §12 en adelante para el detalle completo de
bugs encontrados y corregidos, y `MAIL_HUB_RELEASE_GATE.md` para el
checklist formal de cierre de esta misión.
