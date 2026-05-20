# Auditoría Flujo Completo — Módulo Facturas

**Versión auditada:** v3.10.0  
**Fecha:** 2026-05-20  
**Estado:** ✅ OPERATIVO (0 CRÍTICOS)  
**Auditor:** Claude Code (claude-sonnet-4-6)  
**Ubicación:** `apps/tenant/facturas/`

---

## 1. Responsabilidades del Módulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **Pipeline UBL 2.1** — Extracción de datos maestros desde XMLs estándar (Parser especializado) | ✅ |
| 2 | **Idempotencia Legal** — Prevención de duplicados por CUFE/CUDE: `fast_get_cufe()` pre-valida antes del parsing | ✅ |
| 3 | **Snapshot de Identidad** — Emisor y receptor persistidos al momento de emisión (SSoT histórico) | ✅ |
| 4 | **Ingesta Multi-Canal** — Drag & Drop, batch ZIP, ingesta IMAP automática (Celery) | ✅ |
| 5 | **Resolución de Naturaleza** — `VENTA` (tenant es emisor) / `COMPRA` (tenant es receptor) por comparación NIT | ✅ |
| 6 | **Gestión de Anexos** — XMLs en `FacturaAnexos` (campo separado, optimiza queries principales) | ✅ |
| 7 | **Rastreo de Pagos** — Campo `estado_pago`: `NO_PAGADA / PAGO_PARCIAL / PAGADA` | ✅ (v2.97) |
| 8 | **Edición Controlada** — Modal centralizado para los 8 `MANUAL_EDITABLE_FIELDS`; campos XML siempre readonly | ✅ (v2.98) |
| 9 | **Pull Model Retenciones** — `@property` lee desde `Contabilidad.Retencion`; Factura no almacena retenciones | ✅ (v3.7.1) |
| 10 | **UUID Lookup** — `lookup_field = 'uuid'` via `BaseTenantViewSet` | ✅ (mig 0011/0015) |
| 11 | **Inter-App API** — `FacturaInterAppAPI` abierto para lectura sin empresa_id (Contabilidad, Proyectos, Gastos, etc.) | ✅ (v3.10.0) |

---

## 2. Modelos

### 2.1 `Factura`
**Herencia:** `SintelTenantBaseModel` ✅  
**Tabla:** default Django (`tenant_facturas_factura`)  
**Ordering:** `['-fecha_emision', '-consecutivo']`

#### Constantes de Dominio SSoT (nivel módulo)

```python
MANUAL_EDITABLE_FIELDS = frozenset({
    'estado', 'estado_pago', 'fecha_vencimiento', 'categoria',
    'forma_pago', 'medio_pago_codigo', 'payment_due_date', 'cuenta_contable_uuid',
})

XML_IMMUTABLE_FIELDS = frozenset({
    'numero', 'prefijo', 'consecutivo', 'tipo', 'fecha_emision',
    'emisor_nit', 'emisor_razon_social', 'emisor_direccion', 'emisor_email',
    'emisor_telefono', 'emisor_actividad_ciiu',
    'receptor_nit', 'receptor_razon_social', 'receptor_direccion',
    'receptor_email', 'receptor_telefono',
    'moneda', 'subtotal', 'impuestos', 'total',
    'cufe', 'qr_code', 'qr_url',
    'autorizacion_*', 'dian_validation_*', 'dian_response_xml',
    'naturaleza', 'ubl_version', 'customization_id', 'profile_id',
    'profile_execution_id', 'invoice_type_code',
})
```

#### Choices (TextChoices)

| Clase | Valores |
|-------|---------|
| `TipoFactura` | `FE` (Factura Electrónica), `NC` (Nota Crédito), `ND` (Nota Débito) |
| `Estado` | `BORRADOR / ENVIADA / ACEPTADA / RECHAZADA / ANULADA` |
| `EstadoPago` | `NO_PAGADA / PAGO_PARCIAL / PAGADA` |
| `Naturaleza` | `VENTA` (tenant es emisor) / `COMPRA` (tenant es receptor) |
| `Categoria` | `PRODUCTO / SERVICIO / MIXTO` |

#### Campos Principales

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ (mig 0011) |
| `numero` | CharField(50) | `unique=True` — identificador legal |
| `prefijo` | CharField(10) | nullable |
| `consecutivo` | IntegerField | — |
| `tipo` | CharField(2) | `TipoFactura` choices |
| `estado` | CharField(20) | `Estado` choices, default `BORRADOR` |
| `estado_pago` | CharField(20) | `EstadoPago` choices, default `NO_PAGADA` |
| `naturaleza` | CharField(10) | `Naturaleza` choices, calculado en importación |
| `categoria` | CharField(10) | `Categoria` choices, default `SERVICIO` |
| `ubl_version` / `customization_id` / `profile_id` / `profile_execution_id` / `invoice_type_code` | CharField | Metadatos UBL — nullable |
| `fecha_emision` | DateTimeField | del XML |
| `fecha_vencimiento` | DateField | nullable, editable |
| `emisor_nit` | CharField(20) | **snapshot** (inmutable post-import) |
| `emisor_razon_social` | CharField(200) | **snapshot** |
| `emisor_direccion` / `emisor_email` / `emisor_telefono` / `emisor_actividad_ciiu` | CharField | **snapshot**, nullable |
| `receptor_nit` | CharField(20) | **snapshot** |
| `receptor_razon_social` | CharField(200) | **snapshot** |
| `receptor_direccion` / `receptor_email` / `receptor_telefono` | CharField | **snapshot**, nullable |
| `moneda` | CharField(3) | default `'COP'` |
| `subtotal` / `impuestos` / `total` | DecimalField(15,2) | del XML, `MinValueValidator(0)` |
| `forma_pago` / `medio_pago_codigo` / `payment_due_date` | varios | formas de pago, editables |
| `cuenta_contable_uuid` | UUIDField | nullable, vinculación contable (v3.7) |
| `cufe` | CharField(128) | `unique=True, db_index=True` — clave DIAN |
| `qr_code` / `qr_url` | TextField/URLField | del XML |
| `autorizacion_numero` / `autorizacion_prefijo` / `autorizacion_rango_*` / `autorizacion_vigencia_*` | varios | resolución DIAN |
| `dian_validation_code` / `dian_validation_desc` / `dian_validation_fecha` / `dian_validation_hora` | varios | respuesta validación DIAN |
| `dian_response_xml` | TextField | ApplicationResponse inline (<2MB) |
| `xml_content` | TextField | **DEPRECATED** — usar `FacturaAnexos.ubl_xml` |
| `xml_file_path` | CharField(500) | **DEPRECATED** |

#### Propiedades (Pull Model v3.7.1)

```python
@property total_retencion_fuente → lee Contabilidad.Retencion(tipo='RETEFUENTE')
@property total_reteica          → lee Contabilidad.Retencion(tipo='RETEICA')
@property total_reteiva          → lee Contabilidad.Retencion(tipo='RETEIVA')
@property tiene_nota_credito     → bool (hasattr nota_credito)
```

**Regla:** Estos `@property` leen de `apps.tenant.contabilidad.models.Retencion` con filtros `(documento_origen_app='facturas', documento_origen_modelo='Factura', documento_origen_id=self.id, reversada=False)`. Nunca almacenados en Factura.

#### Índices BD

```
Index(fields=['numero'])
Index(fields=['fecha_emision'], condition=Q(estado='ACEPTADA'), name='idx_fact_aceptadas_fecha')
Index(fields=['fecha_emision'])
Index(fields=['estado'])
Index(fields=['naturaleza'])
cufe: unique=True + db_index=True
```

#### `save()` override

- Fallback `empresa_id` por singleton `Empresa.objects.first()` (legacy/tests)
- Auto-calcula `total = subtotal + impuestos` si `total == 0`

---

### 2.2 `ItemFactura`
**Herencia:** `SintelTenantBaseModel` ✅  
**FK:** `Factura` (CASCADE, `related_name='items'`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ (mig 0015) |
| `linea_id` / `codigo` | CharField | del XML, nullable |
| `descripcion` | CharField(500) | |
| `cantidad` | DecimalField(10,2) | `MinValueValidator(0.01)` |
| `unidad_medida` | CharField(10) | default `'UND'` |
| `valor_unitario` | DecimalField(15,2) | |
| `porcentaje_iva` / `valor_iva` | DecimalField | |
| `subtotal` / `total` | DecimalField | calculados |
| `es_servicio` | BooleanField | |
| `porcentaje_retefuente` / `valor_retefuente` / `porcentaje_reteica` / `valor_reteica` / `porcentaje_reteiva` / `valor_reteiva` | DecimalField | **DEPRECATED v3.7.1** — `editable=False` |

---

### 2.3 `FacturaAnexos`
**Herencia:** `SintelTenantBaseModel` ✅  
**Relación:** `OneToOneField(Factura, related_name='anexos')`

| Campo | Tipo | Notas |
|-------|------|-------|
| `ubl_xml` | TextField | XML UBL original completo |
| `application_response_xml` | TextField | ApplicationResponse DIAN |
| `pdf_file` | FileField | PDF del documento |

---

### 2.4 `NotaCredito`
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ (mig 0015) |
| `factura` | OneToOneField(Factura) | `PROTECT` — NC no puede existir sin factura |
| `numero` | CharField | `unique=True` |
| `cude` | CharField(128) | `unique=True` — equivalente a CUFE para NC |
| `fecha_emision` | DateTimeField | |
| `motivo` | TextField | |
| `subtotal` / `impuestos` / `total` | DecimalField(15,2) | |
| `moneda` | CharField(3) | default `'COP'` |
| `retefuente` / `reteica` / `reteiva` | DecimalField | **Nota:** NC puede llevar retenciones propias (en XML) |
| `ref_factura_numero` / `ref_factura_cufe` | CharField | referencia redundante (snapshot) |
| `xml_content` | TextField | XML de la NC |

---

### 2.5 `MailIngestionRun`
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `task_id` | CharField | Celery task ID |
| `naturaleza` | CharField | `VENTA / COMPRA / MIXTO` |
| `status` | CharField | `PENDING / RUNNING / SUCCESS / FAILED / CANCEL_REQUESTED / CANCELED / ABORTED` |
| `counts` | JSONField | `{total, created, duplicated, errors}` |
| `summary` | JSONField | detalles de ejecución |

---

### 2.6 `MailInboxState`
Gestión de estado IMAP incremental.

| Campo | Tipo | Notas |
|-------|------|-------|
| `last_seen_uid` | IntegerField | nullable — si `NULL` → procesar histórico completo |
| `last_run_at` | DateTimeField | |
| `total_processed` | IntegerField | |

---

### 2.7 `MailIngestionConfig` (DEPRECATED)
Migrado a `empresa.MailInboxConfig`. Mantener hasta cleanup v3.9.

---

### 2.8 Migraciones

| # | Archivo | Cambio Principal |
|---|---------|-----------------|
| 0001 | `0001_initial.py` | Creación inicial (Factura, ItemFactura, MailIngestionConfig, MailIngestionRun, MailInboxState) |
| 0002 | `..._idx_fact_aceptadas_fecha.py` | Índice parcial en `fecha_emision` para estado=ACEPTADA |
| 0003 | `..._mailinboxstate_empresa_...` | FK empresa en MailInboxState y MailIngestionConfig |
| 0004 | `..._remove_factura_..._idx.py` | Elimina índice duplicado |
| 0005 | `..._retefuente_reteica_reteiva.py` | ⚠️ Agregar campos retenciones (DEPRECATED v3.7.1) |
| 0006 | `..._factura_estado_pago.py` | Campo `estado_pago` |
| 0007 | `..._cuenta_contable_uuid.py` | Campo `cuenta_contable_uuid` (vinculación contable) |
| 0008 | `..._add_reteiva_fields.py` | Retenciones en ItemFactura |
| 0009 | `..._deprecate_retention_fields.py` | **v3.7.1 CRÍTICA** — `editable=False` en campos retenciones |
| 0010 | `..._alter_factura_retefuente_...` | Alter deprecación |
| 0011 | `..._factura_uuid.py` | UUID field en Factura |
| 0012 | `..._remove_factura_retefuente_...` | Eliminar campos retenciones de Factura |
| 0013 | `..._alter_factura_uuid.py` | Constraint uuid en Factura |
| 0014 | `..._migrate_mail_ingestion_to_mail_inbox.py` | Migrar MailIngestion → empresa.MailInboxConfig |
| 0015 | `..._add_uuid_itemfactura_notacredito.py` | UUID fields en ItemFactura y NotaCredito |

---

## 3. Service Layer (FSD)

### 3.1 `services/selectors.py` — Lectura Zero-Waste

**Clase:** `FacturaSelectors` (todos `@staticmethod`)

| Método | Descripción |
|--------|-------------|
| `qs_list(empresa_id, search)` | `.only(LIST_FIELDS)` + `select_related("nota_credito")` + filtro empresa + búsqueda Q |
| `qs_detail(empresa_id)` | `.only(DETAIL_FIELDS)` + `select_related("nota_credito", "anexos")` + filtro empresa |
| `qs_centros_costo(empresa_id)` | Solo `id/uuid/numero/receptor_razon_social` para dropdowns |
| `get_summary(empresa_id)` | Agrega ventas y compras netas descontando NCs: `{ventas: {subtotal_neto, impuestos_neto, total_neto, cantidad}, compras: {...}}` |
| `obtener_anexo_xml(factura, tipo)` | Retorna XML desde `FacturaAnexos` — `tipo='ubl'` o `'app'`; streaming si `>2MB` |

**Constantes SSoT:**
- `LIST_FIELDS` — 23 campos optimizados para tabla Tabulator
- `DETAIL_FIELDS` — 31 campos para vista completa
- `ANEXO_KEYS = {"ubl_xml", "application_response_xml"}`
- `MAX_INLINE_BYTES = 2_000_000` (2MB — threshold streaming)

---

### 3.2 `services/crud_service.py` — Escritura Atómica

**Clase:** `FacturaCRUDService`

| Método | Descripción |
|--------|-------------|
| `crear(dto, empresa_id)` | `@transaction.atomic` — crea Factura desde DTO |
| `actualizar(instance, data)` | `@transaction.atomic` — actualiza solo `MANUAL_EDITABLE_FIELDS` |
| `eliminar(instance)` | Elimina factura (cascade items/anexos) |
| `qs_list(empresa_id, search)` | Delega a `FacturaSelectors.qs_list()` |
| `qs_detail(empresa_id)` | Delega a `FacturaSelectors.qs_detail()` |

---

### 3.3 `services/business_service.py` — Reglas de Negocio (~563 líneas)

**Clase principal:** `FacturaBusinessService`

| Método | Descripción |
|--------|-------------|
| `normalize_document_number(nit)` | Normaliza NITs: elimina guiones, puntos, espacios, dígito verificación |
| `_resolver_naturaleza(emisor_nit, empresa_nit)` | SSoT: `VENTA` si emisor==tenant, `COMPRA` si receptor==tenant |
| `importar_documento(file_bytes, **kwargs)` | Orquesta pipeline: UBLParser → DTO → `guardar_factura_desde_dto()` |
| `guardar_factura_desde_dto(dto, empresa_id)` | `@transaction.atomic` — CUFE pre-check → `FacturaCRUDService.crear()` |
| `materializar_desde_result(result, empresa_id)` | Materializa desde resultado de pipeline anterior |
| `obtener_xml(factura, tipo)` | Delega a `FacturaSelectors.obtener_anexo_xml()` |
| `obtener_retenciones_desde_cliente(cliente_nit, empresa_id)` | **Pull Model v3.7.1** — Bridge API a `RetencionesService` de Contabilidad |
| `obtener_retenciones_desde_proveedor(proveedor_nit, empresa_id)` | **Pull Model v3.7.1** — Bridge API (COMPRA: retenciones vienen en XML, no se extraen de proveedor) |

**Facade:** `FacturaService` — alias estable que re-exporta `FacturaBusinessService`.

---

### 3.4 `services/api_mixins.py` — Inyección en ViewSet

**Clase:** `FacturaServiceMixin`

| Método | Delegado a |
|--------|-----------|
| `get_qs_list(empresa_id, search)` | `FacturaSelectors.qs_list()` |
| `get_qs_detail(empresa_id)` | `FacturaSelectors.qs_detail()` |
| `get_summary(empresa_id)` | `FacturaSelectors.get_summary()` |
| `service_eliminar(instance)` | `FacturaCRUDService.eliminar()` |
| `service_importar_documento(file_bytes, **kwargs)` | `FacturaBusinessService.importar_documento()` |
| `service_materializar(result, empresa_id)` | `FacturaBusinessService.materializar_desde_result()` |
| `service_obtener_xml(factura, tipo)` | `FacturaBusinessService.obtener_xml()` |
| `service_obtener_retenciones_cliente(cliente_nit, empresa_id)` | Bridge Pull Model |
| `service_obtener_retenciones_proveedor(proveedor_nit, empresa_id)` | Bridge Pull Model |

---

### 3.5 `services/services_mail_ingestion.py` (~432 líneas)

| Función | Descripción |
|---------|-------------|
| `enqueue_mail_ingestion(empresa_id, config, naturaleza)` | Encola tarea Celery de ingesta |
| `process_mail_ingestion_sync(empresa_id, config, naturaleza)` | Ingesta síncrona (preview/testing) |
| `persist_run_result(run, counts, summary)` | Persiste resultado en `MailIngestionRun` |
| `preview_mail_ingestion(empresa_id, config)` | Preview sin persistir — retorna estadísticas |

---

## 4. API Layer

### 4.1 ViewSets

| ViewSet | Líneas | Herencia | lookup_field |
|---------|--------|----------|-------------|
| `FacturaViewSet` | ~1513 | `FacturaServiceMixin, BaseTenantViewSet` | `uuid` |
| `ItemFacturaViewSet` | ~25 | `BaseTenantViewSet` | `uuid` (heredado) |
| `NotaCreditoViewSet` | ~50 | `BaseTenantViewSet` | `uuid` (heredado) |

**Acciones de `FacturaViewSet`:**

| Acción | Método | URL |
|--------|--------|-----|
| `list` | GET | `/api/v1/facturas/` |
| `retrieve` | GET | `/api/v1/facturas/{uuid}/` |
| `destroy` | DELETE | `/api/v1/facturas/{uuid}/` |
| `partial_update` | PATCH | `/api/v1/facturas/{uuid}/` |
| `upload_ubl` | POST | `/api/v1/facturas/upload-ubl/` |
| `importar_ubl` | POST | `/api/v1/facturas/importar-ubl/` |
| `upload_document` | POST | `/api/v1/facturas/upload-document/` |
| `summary` | GET | `/api/v1/facturas/summary/` |
| `ingest_status` | GET | `/api/v1/facturas/ingest/{task_id}/status/` |
| `materialize` | POST | `/api/v1/facturas/materialize/` |
| `create_from_dto` | POST | `/api/v1/facturas/create-from-dto/` |
| `gestor_offcanvas` | GET | `/api/v1/facturas/gestor-offcanvas/` |
| `xml` | GET | `/api/v1/facturas/{uuid}/xml/` |
| `app_response` | GET | `/api/v1/facturas/{uuid}/app-response/` |
| `update_inbox_state` | POST | `/api/v1/facturas/update-inbox-state/` |

---

### 4.2 Serializers (`api/serializers.py`)

| Serializer | Propósito |
|------------|-----------|
| `ItemFacturaSerializer` | CRUD de ítems |
| `FacturaListDTSerializer` | **DEPRECATED** — legacy DataTable |
| `FacturaListSerializer` | List endpoint — usa `LIST_FIELDS` |
| `FacturaDetailSerializer` | Detalle completo + `@property` retenciones |
| `FacturaWriteSerializer` | PATCH/PUT — solo `MANUAL_EDITABLE_FIELDS` |
| `FacturaReadDTOSerializer` | DTO canónico (para pipeline interno) |
| `ImportUBLSerializer` | POST importar-ubl (texto XML) |
| `UploadUBLFileSerializer` | POST upload-ubl (`file` o `files[]`) |
| `MailIngestionRunCreateSerializer` | POST ingesta-correo/run |
| `MailIngestionRunListSerializer` | GET ingesta-correo/runs |
| `NotaCreditoListSerializer` | NC list |
| `NotaCreditoDetailSerializer` | NC detalle completo |

---

### 4.3 Endpoints Completos

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/v1/facturas/` | Lista paginada (Tabulator) |
| GET | `/api/v1/facturas/{uuid}/` | Detalle completo |
| PATCH | `/api/v1/facturas/{uuid}/` | Actualiza `MANUAL_EDITABLE_FIELDS` |
| DELETE | `/api/v1/facturas/{uuid}/` | Elimina (cascade ítems + anexos) |
| POST | `/api/v1/facturas/upload-ubl/` | Subir XML único o batch (`files[]`) |
| POST | `/api/v1/facturas/importar-ubl/` | Importar desde texto XML |
| POST | `/api/v1/facturas/upload-document/` | Upload universal (XML/PDF/XLS/CSV/TXT) |
| GET | `/api/v1/facturas/summary/` | Resumen financiero neto (ventas/compras − NCs) |
| GET | `/api/v1/facturas/ingest/{task_id}/status/` | Estado de tarea Celery |
| POST | `/api/v1/facturas/materialize/` | Materializar desde resultado de pipeline |
| POST | `/api/v1/facturas/create-from-dto/` | Crear desde DTO canónico |
| GET | `/api/v1/facturas/gestor-offcanvas/` | Render HTML offcanvas gestor |
| GET | `/api/v1/facturas/{uuid}/xml/` | Descargar XML UBL |
| GET | `/api/v1/facturas/{uuid}/app-response/` | Descargar ApplicationResponse |
| POST | `/api/v1/facturas/update-inbox-state/` | Actualizar estado IMAP |
| GET | `/api/v1/facturas/notas-credito/` | Lista NCs |
| GET | `/api/v1/facturas/notas-credito/{id}/` | Detalle NC |
| GET | `/api/v1/facturas/items-factura/` | Lista ítems |
| POST | `/api/v1/facturas/ingesta-correo/run/` | Ejecutar ingesta IMAP |
| GET | `/api/v1/facturas/ingesta-correo/runs/` | Listar ejecuciones |
| POST | `/api/v1/facturas/ingesta-correo/preview/` | Preview sin persistir |

**Orden de registro en Router** (anti-greedy):
```
router.register(r'notas-credito', ...)  # PRIMERO
router.register(r'items-factura', ...)  # ANTES de r''
router.register(r'', FacturaViewSet)    # AL FINAL
```

---

### 4.4 Vistas de Ingesta (`api/views_mail_ingestion.py`)

| Vista | Tipo | URL |
|-------|------|-----|
| `MailIngestionRunCreateAPIView` | `APIView` | POST `/ingesta-correo/run/` |
| `MailIngestionRunsListAPIView` | `ListAPIView` | GET `/ingesta-correo/runs/` |
| `MailIngestionPreviewAPIView` | `APIView` | POST `/ingesta-correo/preview/` |

---

## 5. Frontend

### 5.1 JavaScript (`static/js/facturas/`)

| Archivo | Líneas | Namespace / Responsabilidad |
|---------|--------|----------------------------|
| `facturas_main.js` | ~2000 | Orquestador central: enrutador de features, estado global, inicialización |
| `facturas.api.js` | ~280 | **SSoT de URLs**: todos los métodos HTTP mapeados con URLs parametrizadas |
| `facturas.components.js` | ~125 | Componentes reutilizables: modales, botones, badges |
| `features/facturas_list.js` | ~935 | Tabulator grid: columnas, filtrado, paginación, acciones por fila |
| `features/facturas_editor.js` | ~479 | Modal de edición: carga datos, validación, PATCH payload |
| `features/ver_detalle_factura.js` | ~236 | Vista detalle offcanvas: carga XML, ApplicationResponse, PDF |

**Flujo edición (modal):**
```
usuario → btn "Editar" en tabla
  → facturas_list.js abre modal
  → facturas_editor.js carga datos via GET /api/v1/facturas/{uuid}/
  → usuario modifica MANUAL_EDITABLE_FIELDS
  → sanitiza: fecha vacía → null, uuid vacío → null
  → PATCH /api/v1/facturas/{uuid}/ con solo campos editables
  → on success: cierra modal, recarga tabla Tabulator
```

---

### 5.2 Templates HTML (`templates/tenant/facturas/`)

| Template | Líneas | Propósito |
|----------|--------|-----------|
| `list.html` | 108 | Listado principal con Tabulator |
| `list_factura.html` | 110 | Listado legacy |
| `offcanvas_crear_factura.html` | 212 | Formulario creación manual |
| `offcanvas_editar_factura.html` | 299 | Modal edición controlada (XML vs Manual) |
| `offcanvas_detalle_factura.html` | 136 | Vista detalle en offcanvas |
| `offcanvas_importar_factura.html` | 44 | Drag & Drop importador UBL |
| `offcanvas_pendientes_factura.html` | 31 | Facturas pendientes de contabilización |
| `partials/assets_facturas.html` | — | Include CSS/JS del módulo |

**Separación XML / Manual en `offcanvas_editar_factura.html`:**
- Sección XML: siempre `readonly`, badge `bg-secondary` con ícono 🔒
- Sección Manual: siempre editable, badge `bg-primary` con ícono ✏️

---

### 5.3 Tarea Celery (`tasks.py`)

```python
@shared_task(max_retries=3, default_retry_delay=60)
def procesar_factura_xml_task(xml_content, empresa_id, usuario_id):
    """Procesa XML UBL asincronamente con aislamiento multi-tenant."""
```

---

## 6. Utilidades y Pipeline UBL

### `utils/ubl_parser.py`

| Función/Clase | Descripción |
|---------------|-------------|
| `fast_get_cufe(xml_bytes)` | Extrae CUFE con regex antes del parsing completo — pre-validación de idempotencia en milisegundos |
| `UBLParser` | Parser completo: `parse(xml_bytes)` → `FacturaDTO` con todos los campos |

**Batch Processing Pattern:**
```
POST /upload-ubl/ con files[]
  → Para cada archivo:
      1. fast_get_cufe() con regex rápida (~ms)
      2. Si CUFE existe → 200 OK inmediato (sin parsing)
      3. Si CUFE nuevo → UBLParser.parse() completo
      4. → guardar_factura_desde_dto() @transaction.atomic
  → Response: {creados, duplicados, errores, resultados[]}
```

---

## 7. Management Commands (`management/commands/`)

| Comando | Propósito |
|---------|-----------|
| `audit_facturas_anexos` | Audita qué facturas no tienen `FacturaAnexos` |
| `audit_naturaleza_mismatches` | Detecta facturas con naturaleza inconsistente |
| `backfill_facturas_anexos` | Migra `xml_content` → `FacturaAnexos` para facturas legacy |
| `backfill_naturaleza_facturas` | Recalcula `naturaleza` para facturas importadas antes del resolver |
| `fix_naturaleza_inconsistent` | Corrige facturas con naturaleza incoherente |

---

## 8. Tests (`tests/` — 23 archivos)

| Archivo | Bytes | Propósito |
|---------|-------|-----------|
| `test_api_facturas.py` | 7,789 | CRUD API endpoints |
| `test_nota_credito_pipeline.py` | 13,169 | **CRÍTICO** — Pipeline NC completo |
| `test_retenciones_backward_compat.py` | 11,974 | **CRÍTICO v3.7.1** — Pull Model backward compat |
| `test_xml_pipeline_canonical.py` | 5,707 | Pipeline XML canónico |
| `test_naturaleza_rule_ssot.py` | — | Regla naturaleza VENTA/COMPRA |
| `test_importar_ubl_service.py` | — | Servicio importación UBL |
| `test_create_with_anexos.py` | — | Creación + FacturaAnexos |
| `test_facturas_delete_api.py` | — | Eliminación sin restricciones |
| `test_import_ubl_heavy_payload.py` | — | Import con XML >2MB |
| `test_upload_async_flow.py` | — | Flujo async Celery |
| `test_templates.py` | — | Rendering de templates |
| + 12 más | — | Cobertura naturaleza, payload, ingesta, pipeline |

---

## 9. Checklist AGENTS.md — Estado de Cumplimiento

| Regla | Estado | Detalle |
|-------|--------|---------|
| `SintelTenantBaseModel` | ✅ | Todos los modelos |
| `empresa_id` en queries | ✅ | `FacturaSelectors` aplica filtro en todos los métodos |
| `.only()` en querysets | ✅ | `LIST_FIELDS` / `DETAIL_FIELDS` SSoT en `selectors.py` |
| `lookup_field = 'uuid'` | ✅ | Todos los ViewSets (heredado) |
| UUID en modelos | ✅ | Factura (mig 0011), ItemFactura/NotaCredito (mig 0015) |
| No signals para negocio | ✅ | Service Layer exclusivo |
| `@transaction.atomic` en CRUD | ✅ | `crear()`, `guardar_factura_desde_dto()`, `materializar_desde_result()` |
| `BaseTenantViewSet` sin override auth | ✅ | `FacturaViewSet` no sobreescribe `authentication_classes` |
| Imports de `apps.public.*` bloqueados | ✅ | No hay imports directos |
| Permisos de `apps.tenant.api.permissions` | ✅ | `IsTenantMember`, `IsTenantAdminOrReadOnly` |
| Pull Model retenciones | ✅ | `@property` lee desde `Contabilidad.Retencion`, Factura no almacena |
| Router anti-greedy | ✅ | `r'notas-credito'` y `r'items-factura'` ANTES de `r''` |
| Imports globales (no dentro de `def`) | ⚠️ | `models.py` tiene imports locales en `@property` (excepción justificada: evitar circular import con contabilidad) |

---

## 10. Deuda Técnica

| ID | Archivo | Severidad | Descripción |
|----|---------|-----------|-------------|
| DEUDA-01 | `api/viewsets.py` | ALTA | 1513 líneas — monolito. Debería fragmentarse en: `FacturaBaseViewSet` + mixins por feature (`FacturaUBLMixin`, `FacturaMailIngestionMixin`, `FacturaXMLMixin`) |
| DEUDA-02 | `facturas_main.js` | ALTA | ~2000 líneas. El orquestador principal debería fragmentarse en módulos de feature |
| DEUDA-03 | `features/facturas_list.js` | MEDIA | 935 líneas — podría separarse en `facturas_list_columns.js` + `facturas_list_actions.js` |
| DEUDA-04 | `facturas_xml/` | MEDIA | 650+ archivos XML de prueba dentro del código de producción — mover a `fixtures/` o excluir en `.gitignore` |
| DEUDA-05 | `Factura.xml_content` / `xml_file_path` | MEDIA | Campos DEPRECATED (migrar a `FacturaAnexos`) — eliminar en v3.9 junto al cleanup de retenciones |
| DEUDA-06 | `MailIngestionConfig` | MEDIA | Modelo DEPRECATED (migrado a `empresa.MailInboxConfig`) — eliminar en v3.9 |
| DEUDA-07 | `FacturaListDTSerializer` | BAJA | Serializer legacy DataTable — verificar si tiene consumidores; eliminar si no |
| DEUDA-08 | `services/__init__.py` | BAJA | `LIST_FIELDS` se importa dos veces (líneas 6 y 13) — limpiar duplicado |
| DEUDA-09 | `list_factura.html` | BAJA | Dos templates de listado (`list.html` + `list_factura.html`) — verificar cuál está activo |
| DEUDA-10 | `utils/ubl_parser.py` | BAJA | Sin tests unitarios directos del parser — dependen de tests de integración |

---

## 11. Patrones Clave

### 11.1 Pull Model (ADR-001 v3.7.1)

```
Factura.total_retencion_fuente [@property]
  → Contabilidad.Retencion.objects.filter(
      tipo='RETEFUENTE',
      documento_origen_app='facturas',
      documento_origen_id=self.id,
      reversada=False
    ).aggregate(Sum('monto'))
```

- **Facturas NUNCA almacena retenciones** — solo las lee via `@property`
- **Backward compat**: `FacturaDetailSerializer` expone los `@property` transparentemente
- **COMPRA**: retenciones vienen en XML, no se extraen de proveedores
- **VENTA**: retenciones se aplican desde Clientes (bridge a `RetencionesService`)

### 11.2 Snapshot Pattern

Emisor y receptor capturados al momento de importación UBL. Los campos `emisor_*` y `receptor_*` son `XML_IMMUTABLE_FIELDS` — nunca editables post-import. Garantiza SSoT histórico fiscal.

### 11.3 Naturaleza Resolver (SSoT)

```python
_resolver_naturaleza(emisor_nit, empresa_nit):
    emisor_norm = normalize_document_number(emisor_nit)
    empresa_norm = normalize_document_number(empresa_nit)
    if emisor_norm == empresa_norm: return Naturaleza.VENTA
    return Naturaleza.COMPRA
```

Calculada automáticamente en importación — **nunca asignable manualmente**.

### 11.4 Pre-validación Idempotencia (CUFE)

```
fast_get_cufe(xml_bytes)  → regex ~ms
  → Si cufe existe en BD → 200 OK (sin parsing completo)
  → Si cufe nuevo → UBLParser.parse() → guardar_factura_desde_dto()
```

### 11.5 Zero Waste Queries

```python
LIST_FIELDS = (23 campos)   # Para Tabulator grid
DETAIL_FIELDS = (31 campos) # Para offcanvas detalle
# Nunca .all() sin .only()
```

---

## 12. Flujo Completo: Importación UBL

```
[Frontend offcanvas_importar_factura.html]
  ↓ usuario arrastra XML(s) y confirma
[facturas_list.js] → POST /api/v1/facturas/upload-ubl/
  Body: FormData con files[] (múltiples) o file (único)
    ↓
[FacturaViewSet.upload_ubl()]
  Para cada archivo:
    1. fast_get_cufe(xml_bytes) → regex CUFE
    2. Si CUFE existe → return {status: 200, duplicado: true}
    3. Si CUFE nuevo → service_importar_documento(file_bytes, empresa_id=...)
         ↓
    [FacturaBusinessService.importar_documento()]
      → UBLParser.parse(xml_bytes) → FacturaDTO
      → _resolver_naturaleza(emisor_nit, empresa_nit)
      → obtener_retenciones_desde_cliente() [si VENTA]
      → guardar_factura_desde_dto(dto, empresa_id) @transaction.atomic
           → FacturaCRUDService.crear(dto, empresa_id)
           → FacturaAnexos.objects.create(ubl_xml=xml_content)
           → ItemFactura.objects.bulk_create(items)
         ↓ return Factura instance
  Response batch: {creados: X, duplicados: Y, errores: Z, resultados: [...]}
    ↓
[facturas_list.js] → table.replaceData() → tabla se refresca
```

---

## 13. Flujo Completo: Edición Controlada (PATCH)

```
[facturas_list.js] → usuario clic en btn "Editar" (Tabulator row)
  → composedPath() detecta botón (anti-rowClick bug v2.98)
  → abre modal offcanvas_editar_factura.html
    ↓
[facturas_editor.js] → GET /api/v1/facturas/{uuid}/
  → Carga datos en modal:
    - Sección XML: readonly (numero, emisor, receptor, totales)
    - Sección Manual: editable (estado, estado_pago, vencimiento, etc.)
  → usuario edita MANUAL_EDITABLE_FIELDS
  → sanitiza fechas vacías → null, uuid vacío → null
  → PATCH /api/v1/facturas/{uuid}/ con payload limpio
    ↓
[FacturaViewSet.partial_update()]
  → empresa_id resuelto desde tenant_profile o fallback singleton
  → FacturaWriteSerializer.is_valid() → valida MANUAL_EDITABLE_FIELDS
  → FacturaCRUDService.actualizar(instance, validated_data)
  → Response 200 + datos actualizados
    ↓
[facturas_editor.js] → cierra modal → table.replaceData()
```

---

## 14. Inter-App API (v3.10.0) — Acceso sin empresa_id

**[NEW v3.10.0]** Apps de negocio (Contabilidad, Proyectos, Gastos, Empleados, Proveedores, Clientes) pueden acceder a **TODOS** los datos de Facturas sin restricción empresa_id.

### API Abierto

```python
from apps.tenant.facturas.services import FacturaInterAppAPI

# Lectura sin restricción empresa_id
qs = FacturaInterAppAPI.list_all()                  # QuerySet de TODAS las facturas
qs = FacturaInterAppAPI.list_all(search='123')      # Con búsqueda
factura = FacturaInterAppAPI.get_by_id(factura_id=123)
factura = FacturaInterAppAPI.get_by_id(factura_uuid='550e8400-e29b-...')
factura = FacturaInterAppAPI.get_by_cufe('430078...')
factura = FacturaInterAppAPI.get_by_numero('PV001-00000001')
summary = FacturaInterAppAPI.summary_all()          # {ventas: {...}, compras: {...}}
```

### Casos de Uso

| App | Caso de Uso | Método |
|-----|------------|--------|
| **Contabilidad** | Extraer facturas para contabilizar (Pull Model) | `list_all()` + `.filter(naturaleza='COMPRA')` |
| **Proyectos** | Vincular facturas a proyectos (sin restricción empresa) | `get_by_id(factura_uuid=...)` |
| **Dashboard** | Resumen consolidado multi-empresa | `summary_all()` |
| **Gastos** | Buscar facturas asociadas por CUFE | `get_by_cufe(...)` |
| **Core (Orchestration)** | Integraciones internas | `list_all()` |

### Reglas de Seguridad

**✅ Permitido:**
- Lectura desde servicios internos (Service Layer)
- Pasar QuerySet a otras funciones de servicios
- `.only()` / `.defer()` para optimización
- `.filter()`, `.aggregate()`, `.count()` en servicios

**❌ Prohibido:**
- **NUNCA desde API HTTP ViewSet** — usar `FacturaSelectors.qs_list(empresa_id=<user's>)` en su lugar
- **NUNCA en serializers** — mantener DSV a nivel ViewSet
- **Exposición directa a cliente sin filtro** — riesgo de fuga de datos

### Flujo HTTP vs Inter-App

```
┌─────────────────────────────────────────────────────────────────┐
│ HTTP Request (Frontend → Backend) — RESTRICCIÓN OBLIGATORIA    │
├─────────────────────────────────────────────────────────────────┤
│ GET /api/v1/facturas/                                           │
│   ↓ [FacturaViewSet.list()]                                     │
│   empresa_id = request.user.tenant_profile.empresa_id            │
│   qs = FacturaSelectors.qs_list(empresa_id=empresa_id)           │
│   ↓ Filtra por empresa_id del usuario (protección IDOR)         │
│   Response: Solo facturas de su empresa                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Inter-App Service Call — SIN RESTRICCIÓN (legítimo)            │
├─────────────────────────────────────────────────────────────────┤
│ from apps.tenant.facturas.services import FacturaInterAppAPI    │
│   ↓                                                              │
│ qs = FacturaInterAppAPI.list_all()  # empresa_id=None           │
│   ↓ Sin filtro — acceso a TODAS las facturas                    │
│   Resultado: Datos consolidados (contabilidad, dashboards)      │
└─────────────────────────────────────────────────────────────────┘
```

### Escrituras — DSV Obligatorio

FacturaInterAppAPI es **SOLO lectura**. Para crear/actualizar:

```python
# ❌ INCORRECTO — FacturaInterAppAPI no tiene write methods
FacturaInterAppAPI.crear(...)  # NO EXISTE

# ✅ CORRECTO — Usar FacturaBusinessService con DSV
from apps.tenant.facturas.services import FacturaBusinessService

FacturaBusinessService.actualizar_factura_limitado(
    factura=factura_instance,
    data={...},
    empresa_id=empresa_id  # DSV obligatorio — valida propiedad
)
```

### Backward Compatibility

✅ Métodos anteriores siguen funcionando:
- `FacturaSelectors.qs_list(empresa_id=None)` — sigue abierto, pero menos explícito
- Imports directo desde `models.py` — permitidos pero deprecated
- Todas las propiedades `@property` funcionan igual

**Recomendación:** Refactorizar imports antiguos a usar `FacturaInterAppAPI` para mayor claridad de intención.

### Referencias Documentales

- Documentación completa: [INTER_APP_API_v3100.md](./INTER_APP_API_v3100.md)
- Implementación: `apps/tenant/facturas/services/business_service.py:§FacturaInterAppAPI`
- Exports: `apps/tenant/facturas/services/__init__.py`
