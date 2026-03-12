# 🔍 Auditoría Completa: Flujo y Funcionalidad - App Facturas

**Versión:** 2.61.3  
**Fecha:** 2026-03-12  
**Última actualización:** 2026-03-12  
**Ubicación:** `apps/tenant/facturas/`

---

## 📑 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General](#arquitectura-general)
3. [Estructura de Directorios](#estructura-de-directorios)
4. [Modelos y Relaciones](#modelos-y-relaciones)
5. [Servicios y Lógica de Negocio](#servicios-y-lógica-de-negocio)
6. [APIs y Endpoints](#apis-y-endpoints)
7. [Serializers](#serializers)
8. [Parser UBL](#parser-ubl)
9. [Ingesta por Correo](#ingesta-por-correo)
10. [Permisos y Seguridad](#permisos-y-seguridad)
11. [Flujos Completos](#flujos-completos)
12. [Flujo Completo: Workspace → Core API → Models](#-flujo-completo-workspace--core-api--models)
13. [Dependencias y Aislamiento](#dependencias-y-aislamiento)

---

## 🎯 Resumen Ejecutivo

La app **Facturas** es un módulo completo para la gestión de facturas electrónicas UBL 2.1 (DIAN Colombia). Implementa:

- ✅ **Arquitectura Resiliente**: Funciona incluso si otras apps fallan
- ✅ **Service Layer**: Lógica de negocio centralizada en `services.py`
- ✅ **API-First**: Endpoints REST completos con DRF
- ✅ **Parser UBL Robusto**: Extracción de datos desde XML UBL 2.1 con namespaces dinámicos
- ✅ **Pipeline Universal**: Integración con `document_ingest` para múltiples formatos (XML, PDF, XLS)
- ✅ **Inmutabilidad**: Facturas son documentos históricos (solo lectura, eliminación permitida)
- ✅ **Snapshot Pattern**: Datos de emisor/receptor guardados al momento de emisión
- ✅ **Idempotencia**: Importación por CUFE/CUDE evita duplicados
- ✅ **Ingesta por Correo**: Procesamiento automático de facturas desde buzones IMAP
- ✅ **Notas Crédito**: Gestión completa de notas crédito con relación OneToOne
- ✅ **Pre-validación de Idempotencia (v2.61.2)**: `fast_get_cufe()` extrae CUFE con regex antes del parsing completo
- ✅ **Batch Processing (v2.61.2)**: `upload-ubl` acepta `files[]` con resumen `{creados, duplicados, errores}`
- ✅ **Silent Success (v2.61.2)**: Actualiza `FacturaAnexos` si el XML nuevo es `AttachedDocument` más completo
- ✅ **Core API Facade (v2.61.2)**: `/api/v1/core/v1/facturas/` como punto de entrada unificado
- ✅ **Solo Lectura Frontend (v2.61.2)**: `offcanvas_ver_factura.html` + `ver_detalle_factura.js`
- ✅ **Alineación Backend-Frontend (v2.61.3)**: `persisted:True` en payload + `!data.id` en frontend

### Características Principales

- **Desacoplamiento Radical**: No depende de otras apps excepto SSoT (Empresa)
- **Snapshot Pattern**: Datos históricos de emisor/receptor (resiliencia)
- **Multi-tenant**: Aislamiento completo por esquema (django-tenants)
- **Naturaleza Automática**: Determina VENTA/COMPRA comparando NIT del tenant con emisor
- **Optimización**: QuerySets con `only()` para reducir carga de datos
- **Artefactos Pesados**: XMLs separados en `FacturaAnexos` (optimización)

---

## 🏗️ Arquitectura General

### Principios de Diseño

1. **Resiliencia**: Si el módulo de Clientes falla, las facturas persisten (snapshot)
2. **SSoT (Single Source of Truth)**: Empresa se obtiene del tenant, nunca del payload
3. **Service Layer**: Toda lógica de negocio en `services.py`
4. **Zero Trust**: Validación exhaustiva en serializers y viewsets
5. **API-First**: Backend DRF + Frontend Tabulator
6. **Inmutabilidad**: Facturas son documentos históricos (no edición, solo eliminación)
7. **Idempotencia**: Importación por CUFE/CUDE evita duplicados

### Flujo de Datos

```
Frontend (Tabulator) 
    ↓
API Endpoints (DRF ViewSets)
    ↓
Serializers (Validación)
    ↓
Service Layer (Lógica de Negocio)
    ↓
Parser UBL (Extracción de Datos)
    ↓
Models (Persistencia)
    ↓
Database
```

### Pipeline de Importación (v2.61.3)

```
XML/PDF/XLS Upload (single o batch files[])
    ↓
fast_get_cufe() — regex sobre bytes crudos (⚡ pre-validación idempotencia)
    ├─ CUFE ya existe → 200 OK inmediato (sin parsing)
    └─ CUFE nuevo → continuar
    ↓
upload_ubl (FacturaViewSet) — detecta batch/single/async
    ↓
importar_documento() — pipeline universal
    ├─ status_code >= 400 → propagar error inmediatamente (v2.61.3)
    └─ ok → obtener DTO
    ↓
document_ingest (Pipeline Universal)
    ↓
DTO Canónico (parser.py — fix timezone v2.61.3, fix import re UnboundLocalError v2.61.3)
    ↓
guardar_factura_desde_dto() / guardar_nota_credito_desde_dto()
    ├─ transaction.atomic solo envuelve BD (no parsing) (v2.61.2)
    ├─ Silent Success: actualiza FacturaAnexos si AttachedDocument más completo (v2.61.2)
    └─ Retorna {id, persisted:True} (v2.61.3)
    ↓
Factura/NotaCredito (Persistencia)
    ↓
FacturaAnexos (XML almacenado)
    ↓
Frontend: detecta data.id (no data.persisted) para evitar re-persistencia (v2.61.3)
```

---

## 📁 Estructura de Directorios

```
apps/tenant/facturas/
├── __init__.py                    # Inicialización del módulo
├── admin.py                      # Configuración Django Admin
├── apps.py                       # Configuración de la app Django
├── models.py                     # ⚠️ Modelos principales (Factura, ItemFactura, NotaCredito, FacturaAnexos, MailIngestionRun, MailInboxState)
├── services.py                   # ⚠️ Service Layer - Lógica de negocio (SSoT)
├── ubl_parser.py                 # ⚠️ Parser UBL 2.1 (extracción de datos desde XML)
├── services_mail_ingestion.py    # ⚠️ Servicio de ingesta por correo
├── inbox_state.py                # ⚠️ Gestión de estado IMAP (procesamiento incremental)
├── views_ui.py                   # Vistas UI (DEPRECADO - movido a Core)
├── urls_ui.py                    # URLs UI (DEPRECADO)
│
├── api/                          # Módulo de APIs REST
│   ├── __init__.py
│   ├── viewsets.py               # ⚠️ ViewSets DRF (FacturaViewSet, ItemFacturaViewSet, NotaCreditoViewSet)
│   ├── serializers.py            # ⚠️ Serializers DRF (FacturaListSerializer, FacturaDetailSerializer, etc.)
│   ├── urls.py                   # URLs de API
│   ├── pagination.py             # Paginación personalizada
│   ├── permissions.py            # Permisos personalizados
│   ├── filters.py                # Filtros personalizados
│   └── views_mail_ingestion.py  # Vistas para ingesta por correo
│
├── management/                   # Comandos de gestión
│   └── commands/
│       ├── backfill_facturas_anexos.py
│       ├── audit_facturas_anexos.py
│       ├── fix_naturaleza_inconsistent.py
│       ├── audit_naturaleza_mismatches.py
│       └── backfill_naturaleza_facturas.py
│
├── templates/                    # Templates HTML
│   └── tenant/facturas/partials/
│       ├── list.html
│       ├── modals.html
│       └── assets_facturas.html
│
├── tests/                        # Tests unitarios
│   ├── test_api_facturas.py
│   ├── test_import_ubl_service.py
│   ├── test_naturaleza_unit.py
│   ├── test_nota_credito_pipeline.py
│   └── ... (más tests)
│
└── xml/                          # XMLs de ejemplo/referencia
    └── (archivos XML de prueba)
```

---

## 📊 Modelos y Relaciones

### Factura

**Ubicación:** `apps/tenant/facturas/models.py`

**Descripción:** Modelo principal para facturas electrónicas UBL 2.1.

**Campos Principales:**

- **Identificación:**
  - `numero`: Número de factura (único)
  - `prefijo`: Prefijo de numeración (ej: "FST")
  - `consecutivo`: Número consecutivo
  - `cufe`: Código Único de Facturación Electrónica (clave de idempotencia)

- **Clasificación:**
  - `tipo`: FE (Factura Electrónica), NC (Nota Crédito), ND (Nota Débito)
  - `estado`: BORRADOR, ENVIADA, ACEPTADA, RECHAZADA, ANULADA
  - `naturaleza`: VENTA (tenant es emisor), COMPRA (tenant es receptor)
  - `categoria`: PRODUCTO, SERVICIO, MIXTO

- **Snapshot Emisor (SSoT):**
  - `emisor_nit`, `emisor_razon_social`, `emisor_direccion`, `emisor_email`, `emisor_telefono`
  - ⚠️ **CRÍTICO**: Datos guardados al momento de emisión (resiliencia histórica)

- **Snapshot Receptor:**
  - `receptor_nit`, `receptor_razon_social`, `receptor_direccion`, `receptor_email`, `receptor_telefono`
  - ⚠️ **CRÍTICO**: Datos guardados al momento de emisión (resiliencia histórica)

- **Totales:**
  - `subtotal`, `impuestos`, `total`
  - `moneda`: Código de moneda (default: "COP")

- **DIAN:**
  - `qr_code`, `qr_url`: Código QR y URL de validación DIAN
  - `autorizacion_numero`, `autorizacion_prefijo`: Datos de autorización DIAN
  - `dian_validation_code`, `dian_validation_desc`: Estado de validación DIAN

- **Relaciones:**
  - `empresa`: FK a `Empresa` (SSoT, requerido v2.40)
  - `items`: Relación OneToMany con `ItemFactura`
  - `anexos`: Relación OneToOne con `FacturaAnexos` (XMLs)
  - `nota_credito`: Relación OneToOne con `NotaCredito` (opcional)

**Índices:**
- `numero`, `fecha_emision`, `estado`, `naturaleza`, `cufe`, `empresa`

**Reglas de Negocio:**
- ⚠️ **INMUTABILIDAD**: No se pueden editar después de creadas (solo eliminación)
- ⚠️ **IDEMPOTENCIA**: Importación por CUFE evita duplicados
- ⚠️ **NATURALEZA**: Se calcula automáticamente comparando NIT del tenant con emisor

### ItemFactura

**Ubicación:** `apps/tenant/facturas/models.py`

**Descripción:** Ítems de línea de una factura.

**Campos Principales:**

- `factura`: FK a `Factura` (CASCADE)
- `empresa`: FK a `Empresa` (SSoT, requerido v2.40)
- `linea_id`: ID de línea UBL
- `codigo`: Código del ítem
- `descripcion`: Descripción del ítem
- `cantidad`, `unidad_medida`: Cantidad y unidad (ej: "UND", "ZZ")
- `valor_unitario`: Precio unitario
- `porcentaje_iva`: Porcentaje de IVA
- `valor_iva`: IVA calculado
- `subtotal`: Subtotal (cantidad × valor_unitario)
- `total`: Total (subtotal + valor_iva)
- `es_servicio`: Heurística (True si unidad_medida == "ZZ")
- `orden`: Orden de visualización

**Cálculos Automáticos:**
- `subtotal = cantidad × valor_unitario`
- `valor_iva = subtotal × (porcentaje_iva / 100)`
- `total = subtotal + valor_iva`

### NotaCredito

**Ubicación:** `apps/tenant/facturas/models.py`

**Descripción:** Nota Crédito UBL 2.1 (corrección de factura).

**Campos Principales:**

- `factura`: OneToOne con `Factura` (PROTECT - evita borrado accidental)
- `empresa`: FK a `Empresa` (SSoT, requerido v2.40)
- `numero`: Número de nota crédito (único)
- `cude`: Código Único de Documento Electrónico (clave de idempotencia)
- `fecha_emision`: Fecha/hora de emisión
- `moneda`: Código de moneda
- `subtotal`, `impuestos`, `total`: Totales
- `motivo`: Motivo de la nota crédito
- `ref_factura_numero`, `ref_factura_cufe`: Referencia a factura original
- `xml_content`: XML UBL completo

**Reglas de Negocio:**
- ⚠️ **ONE-TO-ONE**: Una factura solo puede tener UNA nota crédito
- ⚠️ **IDEMPOTENCIA**: Importación por CUDE evita duplicados
- ⚠️ **INMUTABILIDAD**: No se pueden editar después de creadas

### FacturaAnexos

**Ubicación:** `apps/tenant/facturas/models.py`

**Descripción:** Anexos de factura (XMLs grandes separados de la fila principal).

**Campos Principales:**

- `factura`: OneToOne con `Factura` (CASCADE)
- `ubl_xml`: XML UBL completo (TextField)
- `application_response_xml`: XML de respuesta DIAN (ApplicationResponse)

**Optimización:**
- ⚠️ **ARQUITECTURA**: Evita cargar blobs en listados (optimización)
- ⚠️ **ENDPOINT DEDICADO**: `/api/v1/facturas/{id}/xml/` para acceso a XML

### MailIngestionRun

**Ubicación:** `apps/tenant/facturas/models.py`

**Descripción:** Registro de ejecución de ingesta de facturas desde correo.

**Campos Principales:**

- `started_by`: FK a `User` (quien inició la ingesta)
- `started_at`, `finished_at`: Timestamps de ejecución
- `task_id`: ID de tarea Celery (único, indexado)
- `naturaleza`: VENTA o COMPRA (determinado desde XML)
- `status`: PENDING, RUNNING, SUCCESS, FAILED, CANCEL_REQUESTED, CANCELED, ABORTED
- `counts`: JSON con métricas (xml_detected, imported, duplicates, errors)
- `summary`: JSON con detalles de ejecución

**Reglas:**
- ⚠️ **CERO SIGNALS**: Actualizado directamente por tarea Celery
- ⚠️ **MULTI-TENANT**: Aislado por esquema

### MailInboxState

**Ubicación:** `apps/tenant/facturas/models.py`

**Descripción:** Estado del procesamiento IMAP de un buzón de correo.

**Campos Principales:**

- `mailbox_config`: FK a `MailInboxConfig` (SSoT en empresa)
- `last_seen_uid`: Último UID IMAP procesado (NULL = primera ejecución)
- `last_run_at`: Fecha/hora de última ejecución exitosa
- `total_processed`: Total acumulado de mensajes procesados

**Reglas:**
- ⚠️ **PROCESAMIENTO INCREMENTAL**: Solo procesa UIDs > last_seen_uid
- ⚠️ **UNIQUE_TOGETHER**: Un estado por configuración
- ⚠️ **UID IMAP**: Los UIDs son únicos y persistentes por buzón

---

## 🔧 Servicios y Lógica de Negocio

### services.py

**Ubicación:** `apps/tenant/facturas/services.py`

**Descripción:** Service Layer - Toda la lógica de negocio centralizada.

#### Funciones Principales

##### `guardar_factura_desde_dto(dto, xml_text, file_bytes, file_type)`

**Propósito:** Persiste factura desde DTO canónico del pipeline XML (SSoT).

**Parámetros:**
- `dto`: DTO canónico de factura (formato: `apps/services/xml_ingest/dto.InvoiceDTO`)
- `xml_text`: Texto XML original (para anexos)
- `file_bytes`: Bytes del archivo (v2.61.2: para Silent Success en FacturaAnexos)
- `file_type`: Tipo de archivo (`'xml'` o `'pdf'`)

**Retorna:**
- `Tuple[Dict, int]`: (payload, status_code)
  - `201 Created`: Si se crea nueva factura → `{"id", "numero", "naturaleza", "created": True, "persisted": True}`
  - `200 OK`: Si factura ya existe (idempotente) → `{"id", "numero", "naturaleza", "created": False, "persisted": True}`
  - `409 Conflict`: Si hay conflicto de integridad
  - `422 Unprocessable Entity`: Si faltan campos obligatorios

**Lógica (v2.61.2 + v2.61.3):**
1. Valida configuración de empresa (SSoT)
2. Normaliza números y NITs usando `normalize_document_number()`
3. Resuelve naturaleza (VENTA/COMPRA) usando `_resolver_naturaleza()`
4. Extrae prefijo y consecutivo desde número
5. Parsea fecha de emisión (timezone-aware)
6. `transaction.atomic` envuelve SOLO la escritura en BD (no el parsing)
7. Busca factura existente por CUFE (idempotencia)
8. Si no existe, crea nueva factura
9. **Silent Success**: actualiza `FacturaAnexos.ubl_xml` si el nuevo XML es `AttachedDocument` (más completo)
10. Retorna `persisted: True` siempre en el payload

**Reglas:**
- ⚠️ **IDEMPOTENCIA**: Por CUFE (clave legal) o número (fallback)
- ⚠️ **TRANSACCIONAL OPTIMIZADO** (v2.61.2): `transaction.atomic` solo en escritura BD
- ⚠️ **SILENT SUCCESS** (v2.61.2): Actualiza FacturaAnexos si AttachedDocument > Invoice simple
- ⚠️ **PERSISTED FLAG** (v2.61.3): Retorna `"persisted": True` para señalizar al frontend
- ⚠️ **SSoT**: Usa `get_empresa_emisor_data()` para resolver naturaleza

##### `guardar_nota_credito_desde_dto(dto, xml_text)`

**Propósito:** Persiste Nota Crédito. Idempotencia por CUDE.

**Parámetros:**
- `dto`: DTO canónico de nota crédito
- `xml_text`: Texto XML original (keyword-only)

**Retorna:**
- `NotaCredito`: Instancia creada

**Lógica:**
1. Extrae CUDE (clave de idempotencia)
2. Verifica si ya existe por CUDE (idempotencia)
3. Busca factura referenciada por número o CUFE (normalizado)
4. Valida que la factura no tenga ya una NC (OneToOne)
5. Crea la NotaCredito

**Reglas:**
- ⚠️ **IDEMPOTENCIA**: Por CUDE (clave legal)
- ⚠️ **TRANSACCIONAL**: `@transaction.atomic`
- ⚠️ **ONE-TO-ONE**: Una factura solo puede tener UNA nota crédito

##### `importar_documento(file_bytes, filename, preview, async_mode)`

**Propósito:** Importa documento usando el pipeline universal de documentos (FASE 2).

**Parámetros:**
- `file_bytes`: Bytes del documento a importar
- `filename`: Nombre del archivo (default: "ubl.xml")
- `preview`: Si True, solo retorna DTO sin persistir
- `async_mode`: Si True, procesa de forma asíncrona

**Retorna:**
- Si `async_mode=False`: `Tuple[Dict, int]` (payload, status_code)
- Si `async_mode=True`: `Dict` con task_id (pendiente implementación)

**Lógica (v2.61.3):**
1. Verifica si el pipeline universal está disponible (`FEATURE_DOCUMENT_PIPELINE`)
2. Detecta tipo de documento (hint para XML/UBL)
3. Llama a `ingest_document()` del pipeline universal
4. **v2.61.3**: Si `status_code >= 400`, propaga el error inmediatamente (sin intentar materializar)
5. Si `preview=False`, materializa usando `guardar_factura_desde_dto()` o `guardar_nota_credito_desde_dto()`
6. **v2.61.3**: Retorna `"persisted": True` también para `NotaCredito` (201)

**Reglas:**
- ⚠️ **PIPELINE UNIVERSAL**: Usa `apps.services.document_ingest.ingest_document`
- ⚠️ **FAIL FAST** (v2.61.3): Errores del pipeline (400, 415, etc.) se propagan sin intento de materialización
- ⚠️ **PERSISTED FLAG** (v2.61.3): Payload de éxito incluye `"persisted": True` para Factura y NotaCredito
- ⚠️ **COMPATIBILIDAD**: Mantiene compatibilidad con pipeline legacy

##### `get_facturacion_summary(empresa_id)`

**Propósito:** Calcula resumen de facturación neta excluyendo facturas con Nota de Crédito.

**Parámetros:**
- `empresa_id`: ID de la empresa (opcional, filtra por empresa si se proporciona)

**Retorna:**
- `Dict` con desglose por naturaleza (VENTA/COMPRA):
  ```python
  {
      "ventas": {
          "subtotal_neto": Decimal,
          "impuestos_neto": Decimal,
          "total_neto": Decimal,
          "cantidad": int
      },
      "compras": {
          "subtotal_neto": Decimal,
          "impuestos_neto": Decimal,
          "total_neto": Decimal,
          "cantidad": int
      }
  }
  ```

**Reglas:**
- ⚠️ **REGLA CRÍTICA**: Facturas con `nota_credito_id IS NOT NULL` => Valor 0
- ⚠️ **INTEGRIDAD FISCAL**: Solo suma facturas sin NC asociada

##### `eliminar_factura(factura)`

**Propósito:** Elimina una factura y todos sus registros relacionados.

**Parámetros:**
- `factura`: Instancia de Factura a eliminar

**Lógica:**
1. Elimina nota de crédito asociada primero (si existe)
2. Elimina anexos (OneToOne, se elimina automáticamente)
3. Elimina factura (esto elimina automáticamente los items por CASCADE)

**Reglas:**
- ⚠️ **NUEVA POLÍTICA v2.95**: Se permite eliminar facturas sin restricciones
- ⚠️ **CASCADA**: Items se eliminan automáticamente

##### `normalize_document_number(value)`

**Propósito:** Normaliza números de documento (factura, NIT, etc.) eliminando espacios y caracteres no imprimibles.

**Parámetros:**
- `value`: String con número de documento

**Retorna:**
- `str`: String normalizado sin espacios iniciales/finales ni caracteres no imprimibles

**Reglas:**
- ⚠️ **CRÍTICO**: Evita errores de "Factura no encontrada" por formato
- ⚠️ **BASADO EN XML REAL**: Estructura real de XML en `apps/tenant/facturas/xml/`

##### `qs_list(search)`

**Propósito:** QuerySet optimizado para listado (Tabulator v2.40).

**Parámetros:**
- `search`: String de búsqueda (opcional)

**Retorna:**
- `QuerySet`: QuerySet con `only(*LIST_FIELDS)` y `select_related("nota_credito")`

**Optimización:**
- ⚠️ **ONLY**: Solo carga campos necesarios para la tabla
- ⚠️ **SELECT_RELATED**: Carga nota_credito en una sola query
- ⚠️ **ESCALABLE**: Millones de facturas

##### `qs_detail()`

**Propósito:** QuerySet optimizado para detalle (retrieve).

**Retorna:**
- `QuerySet`: QuerySet con `only(*DETAIL_FIELDS)` y `select_related("nota_credito")`

**Optimización:**
- ⚠️ **ONLY**: Solo carga campos necesarios para el detalle

##### `emitir_factura_desde_cotizacion(cotizacion_id, empresa_id)`

**Propósito:** Emite una factura desde una cotización aceptada.

**Parámetros:**
- `cotizacion_id`: ID de la cotización a convertir
- `empresa_id`: ID de la empresa del tenant (Zero Trust)

**Retorna:**
- `Tuple[Dict, int]`: (payload, status_code)
  - `201 Created`: Si se crea nueva factura
  - `400 Bad Request`: Si la cotización no está en estado válido
  - `404 Not Found`: Si la cotización no existe o no pertenece al tenant
  - `422 Unprocessable Entity`: Si el cliente no está activo o faltan datos

**Lógica:**
1. Valida que la cotización pertenece al tenant (Zero Trust)
2. Valida que la cotización está en estado ACEPTADA
3. Valida que el cliente existe y está activo
4. Obtiene datos del emisor (SSoT)
5. Genera número de factura (prefijo + consecutivo)
6. Crea factura con snapshot de emisor/receptor
7. Crea items de factura desde items de cotización

**Reglas:**
- ⚠️ **ZERO TRUST**: Valida que la factura pertenezca al Tenant
- ⚠️ **TRANSACCIONAL**: `@transaction.atomic`

---

## 🌐 APIs y Endpoints

### FacturaViewSet

**Ubicación:** `apps/tenant/facturas/api/viewsets.py`

**Descripción:** ViewSet para gestión de facturas (ReadOnlyModelViewSet).

**Endpoints Principales:**

#### `GET /api/v1/facturas/`

**Propósito:** Lista de facturas (paginada).

**Query Params:**
- `naturaleza`: VENTA|COMPRA
- `nit`: Busca en emisor_nit o receptor_nit
- `estado`: Filtro exacto
- `fecha_emision__date__gte` / `fecha_emision__date__lte`: Rango de fechas
- `search`: Búsqueda general (numero, cufe, receptor_razon_social, emisor_razon_social)
- `ordering`: Ordenamiento (default: `-fecha_emision, -consecutivo`)

**Retorna:**
- `200 OK`: Lista paginada con `FacturaListSerializer`

**Optimización:**
- ⚠️ **ONLY**: Usa `qs_list()` con `only(*LIST_FIELDS)`
- ⚠️ **SELECT_RELATED**: Carga nota_credito en una sola query

#### `GET /api/v1/facturas/{id}/`

**Propósito:** Detalle de factura (read-only).

**Retorna:**
- `200 OK`: Detalle con `FacturaDetailSerializer`
- `404 Not Found`: Si la factura no existe

**Optimización:**
- ⚠️ **ONLY**: Usa `qs_detail()` con `only(*DETAIL_FIELDS)`
- ⚠️ **SELECT_RELATED**: Carga anexos en una sola query

#### `DELETE /api/v1/facturas/{id}/`

**Propósito:** Eliminación directa de facturas (sin restricciones de inmutabilidad).

**Retorna:**
- `204 No Content`: Si se elimina exitosamente
- `409 Conflict`: Si hay restricciones de integridad a nivel de BD
- `500 Internal Server Error`: Solo para errores inesperados

**Lógica:**
1. Obtiene instancia de factura
2. Llama a `services.eliminar_factura(instance)`
3. Retorna 204 si exitoso

**Reglas:**
- ⚠️ **NUEVA POLÍTICA v2.95**: Se habilita eliminación directa sin restricciones
- ⚠️ **SERVICE LAYER**: Usa `services.eliminar_factura()`

#### `POST /api/v1/facturas/upload-ubl/`

**Propósito:** ⚠️ DEPRECATED - Sube un archivo XML UBL 2.1 y lo importa.

**Body (multipart/form-data):**
- `file`: Archivo XML UBL 2.1

**Query Params:**
- `async=true` (default): Encola tarea Celery y retorna 202 + task_id
- `async=false`: Parsea y materializa en la misma request (201/200)
- `preview=true`: Solo retorna DTO sin persistir

**Retorna:**
- `async=true`: `202 Accepted` con `{"task_id": str, "status": "queued"}`
- `async=false`: `201/200` con datos de factura materializada
- `400 Bad Request`: Si falta archivo XML
- `409 Conflict`: Si es duplicado
- `422 Unprocessable Entity`: Si hay error de validación

**Nota:** ⚠️ **DEPRECATED** - Usar `POST /api/v1/core/documentos/upload/` en su lugar.

#### `POST /api/v1/facturas/create-from-dto/`

**Propósito:** Crea una factura o nota crédito desde DTO parseado por document_ingest.

**Body (JSON):**
```json
{
    "dto": {...DTO_UNIFICADO...},
    "persist_anexos": true|false  // Opcional, default: true
}
```

**Retorna:**
- `201 Created`: Factura/NC creada
- `200 OK`: Factura/NC actualizada (idempotencia)
- `400 Bad Request`: Falta 'dto' en el cuerpo
- `422 Unprocessable Entity`: Falta SSoT empresa o DTO inválido
- `409 Conflict`: Duplicado o restricción violada

**Lógica:**
1. Extrae DTO del cuerpo
2. Llama a `materializar_factura_desde_result(dto, persist_anexos)`
3. Retorna payload con status_code

#### `GET /api/v1/facturas/{id}/xml/`

**Propósito:** Retorna el UBL XML completo de la factura.

**Retorna:**
- `200 OK`: XML completo con `Content-Type: application/xml`
- `204 No Content`: Si no hay XML disponible
- `404 Not Found`: Si la factura no existe

**Optimización:**
- ⚠️ **ENDPOINT DEDICADO**: Artefactos pesados solo en endpoints `/xml/`
- ⚠️ **INLINE/DOWNLOAD**: Inline si <= 2MB, descarga forzada si mayor

#### `GET /api/v1/facturas/{id}/app-response/`

**Propósito:** Retorna el ApplicationResponse DIAN XML completo.

**Retorna:**
- `200 OK`: XML completo con `Content-Type: application/xml`
- `204 No Content`: Si no hay ApplicationResponse disponible
- `404 Not Found`: Si la factura no existe

#### `GET /api/v1/facturas/summary/`

**Propósito:** Endpoint para obtener resumen de facturación neta.

**Retorna:**
- `200 OK`: JSON con desglose por naturaleza (VENTA/COMPRA)
  ```json
  {
      "ventas": {
          "subtotal_neto": "100000.00",
          "impuestos_neto": "19000.00",
          "total_neto": "119000.00",
          "cantidad": 5
      },
      "compras": {
          "subtotal_neto": "50000.00",
          "impuestos_neto": "9500.00",
          "total_neto": "59500.00",
          "cantidad": 2
      }
  }
  ```

**Reglas:**
- ⚠️ **EXCLUYE NC**: Excluye facturas con Nota de Crédito asociada

#### `GET /api/v1/facturas/gestor-offcanvas/`

**Propósito:** ⚠️ v2.60 - Devuelve el HTML del formulario de factura para HTMX Offcanvas.

**Query Params:**
- `id`: ID de factura (opcional)

**Retorna:**
- `200 OK`: HTML template con formulario Offcanvas

**Lógica:**
- Si recibe `id`, devuelve factura en modo lectura (ReadOnly) si ya está emitida, o permite edición si es borrador
- Si no recibe `id`, devuelve formulario vacío para nueva factura

**Reglas:**
- ⚠️ **ZERO TRUST**: Valida que la factura pertenezca al tenant del usuario

### NotaCreditoViewSet

**Ubicación:** `apps/tenant/facturas/api/viewsets.py`

**Descripción:** ViewSet para gestión de notas crédito (ListModelMixin, RetrieveModelMixin, DestroyModelMixin).

**Endpoints Principales:**

#### `GET /api/v1/facturas/notas-credito/`

**Propósito:** Lista de notas crédito (paginada).

**Retorna:**
- `200 OK`: Lista paginada con `NotaCreditoListSerializer`

**Optimización:**
- ⚠️ **ONLY**: Solo campos esenciales (sin xml_content)

#### `GET /api/v1/facturas/notas-credito/{id}/`

**Propósito:** Detalle de nota crédito (read-only).

**Retorna:**
- `200 OK`: Detalle con `NotaCreditoDetailSerializer`
- `404 Not Found`: Si la nota crédito no existe

#### `GET /api/v1/facturas/notas-credito/{id}/xml/`

**Propósito:** Endpoint dedicado para XML completo (artefacto pesado).

**Retorna:**
- `200 OK`: XML completo con `Content-Type: application/xml`
- `404 Not Found`: Si no hay XML disponible

#### `DELETE /api/v1/facturas/notas-credito/{id}/`

**Propósito:** Eliminar nota crédito (rollback técnico).

**Retorna:**
- `204 No Content`: Si se elimina exitosamente
- `409 Conflict`: Si está protegida (ProtectedError)

**Reglas:**
- ⚠️ **ROLLBACK TÉCNICO**: Solo para corregir errores de carga
- ⚠️ **PROTECCIÓN**: OneToOneField con PROTECT evita borrado accidental de factura

---

## 📝 Serializers

### FacturaListSerializer

**Ubicación:** `apps/tenant/facturas/api/serializers.py`

**Descripción:** Serializer optimizado para listado de facturas (Tabulator v2.60).

**Campos:**
- `id`, `numero`, `naturaleza`, `fecha_emision`, `fecha_vencimiento`
- `cliente_nombre`: Campo aplanado desde `receptor_razon_social` (snapshot)
- `receptor_razon_social`: Snapshot histórico (mantenido por compatibilidad)
- `moneda`, `subtotal`, `impuestos`, `total`
- `total_formateado`: Campo calculado formateado para visualización
- `estado`
- `nota_credito_id`, `nota_credito_numero`: Detección de Nota de Crédito asociada

**Optimización:**
- ⚠️ **CAMPOS APLANADOS**: `cliente_nombre` para mejor legibilidad en frontend
- ⚠️ **CAMPOS CALCULADOS**: `total_formateado` para visualización

### FacturaDetailSerializer

**Ubicación:** `apps/tenant/facturas/api/serializers.py`

**Descripción:** Serializer de detalle para factura (uno a uno).

**Campos:**
- Todos los campos de `DETAIL_FIELDS`
- `has_ubl_xml`: Indica si existe UBL XML en anexos
- `has_application_response_xml`: Indica si existe ApplicationResponse XML
- `anexos_meta`: Metadatos de anexos (tamaños, timestamps) sin el contenido

**Optimización:**
- ⚠️ **METADATOS**: Solo metadatos de anexos, no el contenido XML
- ⚠️ **ENDPOINT DEDICADO**: XML se expone en `/xml/`

### ItemFacturaSerializer

**Ubicación:** `apps/tenant/facturas/api/serializers.py`

**Descripción:** Serializer para ItemFactura (nested read-only en FacturaDetailSerializer).

**Campos:**
- `id`, `linea_id`, `codigo`, `descripcion`, `cantidad`, `unidad_medida`
- `valor_unitario`, `porcentaje_iva`, `valor_iva`, `subtotal`, `total`
- `es_servicio`, `orden`

**Read-Only:**
- `id`, `valor_iva`, `subtotal`, `total`, `es_servicio`

### NotaCreditoListSerializer

**Ubicación:** `apps/tenant/facturas/api/serializers.py`

**Descripción:** Serializer mínimo para listado de notas crédito.

**Campos:**
- `id`, `numero`, `cude`, `fecha_emision`, `moneda`
- `subtotal`, `impuestos`, `total`, `motivo`
- `ref_factura_numero`, `ref_factura_cufe`
- `factura_numero`, `factura_cufe`: Campos relacionados
- `created_at`

**Optimización:**
- ⚠️ **SIN XML**: Sin xml_content (artefacto pesado)

### NotaCreditoDetailSerializer

**Ubicación:** `apps/tenant/facturas/api/serializers.py`

**Descripción:** Serializer de detalle para nota crédito.

**Campos:**
- Todos los campos de `NotaCreditoListSerializer`
- `factura_id`: ID de factura relacionada
- `updated_at`: Timestamp de actualización

**Optimización:**
- ⚠️ **SIN XML**: NO incluye xml_content (artefacto pesado)
- ⚠️ **ENDPOINT DEDICADO**: XML se expone en `/xml/`

---

## 🔍 Parser UBL

### ubl_parser.py

**Ubicación:** `apps/tenant/facturas/ubl_parser.py`

**Descripción:** Parser UBL 2.1 para importación de facturas electrónicas DIAN.

#### Funciones Principales

##### `importar_factura_desde_ubl(xml_text)`

**Propósito:** Importa una factura UBL 2.1 desde XML (legacy).

**Parámetros:**
- `xml_text`: Contenido XML UBL 2.1 (string)

**Retorna:**
- `Factura`: Instancia de Factura creada

**Lógica:**
1. Parsea XML con parser robusto
2. Detecta si es AttachedDocument y extrae Invoice interno
3. Obtiene namespaces dinámicos del documento
4. Extrae información básica (número, fecha, CUFE)
5. Extrae emisor y receptor (snapshot)
6. Extrae totales y moneda
7. Extrae items de línea
8. Determina naturaleza (VENTA/COMPRA)
9. Determina categoría (PRODUCTO/SERVICIO/MIXTO)
10. Crea factura usando `facturas_services.crear_factura()`

**Reglas:**
- ⚠️ **SOPORTE AttachedDocument**: Si el root es AttachedDocument, extrae el Invoice interno desde CDATA
- ⚠️ **NAMESPACES DINÁMICOS**: Usa nsmap del documento + fallbacks UBL comunes
- ⚠️ **LOCAL-NAME**: Usa `local-name()` para evitar fallos por prefijos no declarados

##### `parse_ubl_to_dict(root, xml_bytes, naturaleza)`

**Propósito:** Mapea UBL 2.1 (root ya parseado) a DTO (dict) sin crear Factura.

**Parámetros:**
- `root`: Elemento raíz del XML ya parseado (etree._Element)
- `xml_bytes`: Bytes originales del XML (opcional, para incluir en DTO)
- `naturaleza`: "VENTA" | "COMPRA" (opcional, se determina automáticamente si no se proporciona)

**Retorna:**
- `Dict`: DTO con datos de la factura (sin persistir)

**Lógica:**
1. Detecta si es AttachedDocument y extrae Invoice interno
2. Obtiene namespaces dinámicos
3. Extrae información básica (número, fecha, CUFE)
4. Extrae emisor y receptor
5. Extrae totales y moneda
6. Construye DTO con datos extraídos

**Reglas:**
- ⚠️ **NO PARSEA BYTES**: Acepta root ya parseado (etree._Element)
- ⚠️ **TIMEZONE-AWARE**: Retorna fecha_emision como datetime timezone-aware

#### Utilidades de Parsing

##### `_parse_xml(xml_input)`

**Propósito:** Parser robusto: acepta bytes o str, detecta encoding desde declaración XML.

**Parámetros:**
- `xml_input`: XML como string o bytes

**Retorna:**
- `etree._Element`: Elemento raíz del XML parseado

**Reglas:**
- ⚠️ **FORÉNSICA**: Respeta encoding declarado en XML
- ⚠️ **HUGE_TREE**: Soporta XML grandes

##### `_ns(root)`

**Propósito:** Mapa de namespaces dinámico desde el documento + fallbacks UBL comunes.

**Parámetros:**
- `root`: Elemento raíz del XML

**Retorna:**
- `dict`: Diccionario de namespaces

**Reglas:**
- ⚠️ **FALLBACKS**: Incluye fallbacks UBL comunes (cbc, cac, ext)
- ⚠️ **NO HARDCODE**: No hardcodea prefijos que no existan en el documento

##### `_extraer_invoice_desde_attached_document(root)`

**Propósito:** Si root es AttachedDocument, extrae el Invoice interno desde CDATA o ExternalReference.

**Parámetros:**
- `root`: Elemento raíz del XML

**Retorna:**
- `Optional[etree._Element]`: Elemento Invoice interno o None

**Lógica:**
1. Verifica si root es Invoice directamente
2. Si es AttachedDocument, busca Invoice en múltiples ubicaciones:
   - `//cac:Attachment//cbc:Description` (CDATA)
   - `//cac:Attachment//cac:ExternalReference//cbc:Description` (texto)
3. Limpia CDATA markers si existen
4. Parsea Invoice interno y lo retorna

**Reglas:**
- ⚠️ **FORÉNSICA**: Busca Invoice en múltiples ubicaciones
- ⚠️ **CDATA**: Limpia CDATA markers automáticamente

##### `normalize_document_number(value)`

**Propósito:** Normaliza números de documento (factura, NIT, etc.) eliminando espacios y caracteres no imprimibles.

**Parámetros:**
- `value`: String con número de documento

**Retorna:**
- `str`: String normalizado

**Reglas:**
- ⚠️ **CRÍTICO**: Evita errores de "Factura no encontrada" por formato
- ⚠️ **BASADO EN XML REAL**: Estructura real de XML en `apps/tenant/facturas/xml/`

---

## 📧 Ingesta por Correo

### services_mail_ingestion.py

**Ubicación:** `apps/tenant/facturas/services_mail_ingestion.py`

**Descripción:** Servicio de orquestación de ingesta de facturas desde correo.

#### Funciones Principales

##### `enqueue_mail_ingestion(config_id, limit_messages, started_by)`

**Propósito:** Encola la tarea de ingesta de correo para facturas XML.

**Parámetros:**
- `config_id`: ID de MailInboxConfig de empresa (debe estar activa)
- `limit_messages`: Número máximo de mensajes a procesar (default: 50)
- `started_by`: Usuario que inició la ingesta (opcional)

**Retorna:**
- `MailIngestionRun`: Registro creado con task_id asignado

**Lógica:**
1. Crea registro `MailIngestionRun` en estado PENDING
2. Obtiene esquema del tenant actual
3. Encola tarea Celery `fetch_and_process_billing_mail` (import lazy)
4. Actualiza registro con task_id real

**Reglas:**
- ⚠️ **SSoT**: Consume configuraciones desde `apps.tenant.empresa.services.mailbox_provider`
- ⚠️ **SEGURIDAD**: NO envía credenciales en payload (solo config_id)
- ⚠️ **IMPORT LAZY**: Importa Celery tasks solo cuando se necesitan

##### `persist_run_result(tenant_schema, task_id, result, status_label)`

**Propósito:** Persiste el resultado de una ejecución de ingesta en MailIngestionRun.

**Parámetros:**
- `tenant_schema`: Nombre del esquema del tenant
- `task_id`: ID de la tarea Celery
- `result`: Dict con resultado de la ejecución (MailDigesterResult)
- `status_label`: Estado final (SUCCESS|FAILURE)

**Lógica:**
1. Busca `MailIngestionRun` por task_id
2. Actualiza status, finished_at, counts, summary

**Reglas:**
- ⚠️ **CERO SIGNALS**: Esta función se invoca explícitamente desde la tarea Celery
- ⚠️ **MULTI-TENANT**: Debe ejecutarse dentro de schema_context del tenant correcto

### inbox_state.py

**Ubicación:** `apps/tenant/facturas/inbox_state.py`

**Descripción:** Gestión del estado del buzón IMAP para procesamiento incremental.

#### Funciones Principales

##### `get_or_create_inbox_state(config_id)`

**Propósito:** Obtiene o crea el estado del buzón para una configuración.

**Parámetros:**
- `config_id`: ID de MailInboxConfig

**Retorna:**
- `MailInboxState`: Estado existente o nuevo (con last_seen_uid=None)

**Reglas:**
- ⚠️ **SSoT**: Un estado por configuración (unique_together)
- ⚠️ **PRIMERA EJECUCIÓN**: Si last_seen_uid es NULL, procesa histórico completo

##### `update_inbox_state(config_id, last_uid, messages_processed)`

**Propósito:** Actualiza el estado del buzón después de procesar un lote.

**Parámetros:**
- `config_id`: ID de MailInboxConfig
- `last_uid`: Último UID procesado (None si no se procesó ningún mensaje)
- `messages_processed`: Número de mensajes procesados en este lote

**Lógica:**
1. Obtiene o crea estado del buzón
2. Si last_uid es mayor que last_seen_uid, actualiza
3. Incrementa total_processed

**Reglas:**
- ⚠️ **ATOMICIDAD**: Usa `transaction.atomic()` para evitar condiciones de carrera
- ⚠️ **INCREMENTAL**: Solo actualiza si el nuevo UID es mayor

##### `get_inbox_state(config_id)`

**Propósito:** Obtiene el estado del buzón para una configuración.

**Parámetros:**
- `config_id`: ID de MailInboxConfig

**Retorna:**
- `Optional[MailInboxState]`: Estado o None si no existe

---

## 🔐 Permisos y Seguridad

### Permisos

**Ubicación:** `apps/tenant/facturas/api/permissions.py`

**Permisos Utilizados:**
- `IsAuthenticated`: Usuario autenticado
- `IsTenantAdminOrReadOnly`: Admin del tenant puede escribir, otros solo leer

### Autenticación

**ViewSets:**
- `authentication_classes = [SessionAuthentication]`: Compatible con workspace (cookies de sesión)

### Zero Trust

**Validaciones:**
- ⚠️ **TENANT ISOLATION**: django-tenants maneja automáticamente el aislamiento por esquema
- ⚠️ **EMPRESA VALIDATION**: Valida que la empresa pertenezca al tenant
- ⚠️ **FACTURA VALIDATION**: Valida que la factura pertenezca al tenant del usuario

---

## 🔄 Flujos Completos

### Flujo 1: Importación de Factura desde XML UBL

```
1. Usuario sube archivo XML UBL 2.1
   ↓
2. POST /api/v1/facturas/upload-ubl/ (o /api/v1/core/documentos/upload/)
   ↓
3. importar_documento() (services.py)
   ↓
4. ingest_document() (pipeline universal)
   ↓
5. DTO canónico generado
   ↓
6. guardar_factura_desde_dto() (services.py)
   ↓
7. Normalización de números y NITs
   ↓
8. Resolución de naturaleza (VENTA/COMPRA)
   ↓
9. Búsqueda por CUFE (idempotencia)
   ↓
10. Si no existe, crea Factura
   ↓
11. Guarda XML en FacturaAnexos
   ↓
12. Retorna 201 Created o 200 OK (idempotente)
```

### Flujo 2: Importación de Nota Crédito desde XML UBL

```
1. Usuario sube archivo XML UBL 2.1 (CreditNote)
   ↓
2. POST /api/v1/facturas/upload-ubl/ (o /api/v1/core/documentos/upload/)
   ↓
3. importar_documento() (services.py)
   ↓
4. ingest_document() (pipeline universal)
   ↓
5. DTO canónico generado (tipo: creditnote)
   ↓
6. guardar_nota_credito_desde_dto() (services.py)
   ↓
7. Extrae CUDE (clave de idempotencia)
   ↓
8. Verifica si ya existe por CUDE (idempotencia)
   ↓
9. Busca factura referenciada por número o CUFE (normalizado)
   ↓
10. Valida que la factura no tenga ya una NC (OneToOne)
   ↓
11. Crea NotaCredito
   ↓
12. Retorna NotaCredito creada
```

### Flujo 3: Ingesta Automática desde Correo

```
1. Usuario inicia ingesta desde UI
   ↓
2. POST /api/v1/facturas/mail-ingestion/run/
   ↓
3. enqueue_mail_ingestion() (services_mail_ingestion.py)
   ↓
4. Crea MailIngestionRun en estado PENDING
   ↓
5. Encola tarea Celery fetch_and_process_billing_mail
   ↓
6. Tarea Celery ejecuta:
   a. Obtiene configuración de buzón (SSoT)
   b. Obtiene estado del buzón (inbox_state.py)
   c. Conecta a IMAP (solo UIDs > last_seen_uid)
   d. Procesa mensajes (busca XMLs adjuntos)
   e. Para cada XML:
      - Parsea usando pipeline universal
      - Materializa usando guardar_factura_desde_dto()
   f. Actualiza estado del buzón (last_seen_uid)
   g. Actualiza MailIngestionRun (status, counts, summary)
   ↓
7. Usuario consulta estado: GET /api/v1/facturas/mail-ingestion/{task_id}/status/
   ↓
8. Retorna estado de ejecución (PENDING, RUNNING, SUCCESS, FAILED)
```

### Flujo 4: Eliminación de Factura

```
1. Usuario solicita eliminar factura
   ↓
2. DELETE /api/v1/facturas/{id}/
   ↓
3. FacturaViewSet.destroy()
   ↓
4. services.eliminar_factura(factura)
   ↓
5. Elimina NotaCredito asociada (si existe)
   ↓
6. Elimina FacturaAnexos (OneToOne, se elimina automáticamente)
   ↓
7. Elimina Factura (esto elimina automáticamente los items por CASCADE)
   ↓
8. Retorna 204 No Content
```

### Flujo 5: Emisión de Factura desde Cotización

```
1. Usuario acepta cotización
   ↓
2. POST /api/v1/facturas/emitir-desde-cotizacion/
   ↓
3. emitir_factura_desde_cotizacion() (services.py)
   ↓
4. Valida que la cotización pertenece al tenant (Zero Trust)
   ↓
5. Valida que la cotización está en estado ACEPTADA
   ↓
6. Valida que el cliente existe y está activo
   ↓
7. Obtiene datos del emisor (SSoT)
   ↓
8. Genera número de factura (prefijo + consecutivo)
   ↓
9. Crea Factura con snapshot de emisor/receptor
   ↓
10. Crea ItemFactura desde CotizacionItem
   ↓
11. Retorna 201 Created con datos de factura
```

---

## 🌐 Flujo Completo: Workspace → Core API → Models

### Resumen del Flujo Arquitectónico

El flujo completo de la app Facturas se inicia desde el template principal `workspace.html`, pasa por el Core API (`core/api/urls.py`), y finalmente llega a los modelos en `facturas/models.py`. Este flujo garantiza una arquitectura desacoplada y modular, alineada con el patrón de cotizaciones y contabilidad.

### Diagrama de Flujo Completo

```
1. Usuario accede a /workspace/
   ↓
2. Django: WorkspaceView.render() (apps/tenant/core/views_ui.py)
   ↓
3. Template: tenant/core/workspace.html
   ├── Incluye: tenant/core/partials/facturas/list.html
   ├── Incluye: tenant/facturas/partials/assets_facturas.html
   └── Carga JavaScript modular (facturas.page.js)
   ↓
4. JavaScript: facturas.page.js se inicializa
   ├── Detecta tab #tab-facturas visible
   ├── Inicializa Tabulator con API endpoint
   └── Configura listeners HTMX
   ↓
5. Frontend: Usuario interactúa (upload XML, ver detalle, eliminar, etc.)
   ↓
6. HTMX/API: Request a Core API facade
   ├── GET /api/v1/core/v1/facturas/facturas/ (list)
   ├── GET /api/v1/core/v1/facturas/facturas/{id}/ (retrieve)
   ├── POST /api/v1/core/v1/facturas/facturas/upload-ubl/ (upload UBL)
   ├── GET /api/v1/core/v1/facturas/facturas/gestor-offcanvas/ (offcanvas)
   └── DELETE /api/v1/core/v1/facturas/facturas/{id}/ (delete)
   ↓
7. Core API: apps/tenant/core/api/urls.py
   ├── Router dedicado: path("v1/facturas/", include("apps.tenant.core.api.v1.facturas.urls"))
   └── Gateway directo: path("_apps/facturas/", include("apps.tenant.facturas.api.urls"))
   ↓
8. Core API Facade: apps/tenant/core/api/v1/facturas/viewsets.py
   ├── FacturaCoreViewSet (hereda de FacturaViewSet)
   ├── ItemFacturaCoreViewSet (hereda de ItemFacturaViewSet)
   └── NotaCreditoCoreViewSet (hereda de NotaCreditoViewSet)
   ↓
9. App API: apps/tenant/facturas/api/viewsets.py
   ├── FacturaViewSet (ReadOnlyModelViewSet)
   ├── ItemFacturaViewSet (CRUD)
   └── NotaCreditoViewSet (List, Retrieve, Destroy)
   ↓
10. Serializers: apps/tenant/facturas/api/serializers.py
    ├── FacturaListSerializer (validación)
    ├── FacturaDetailSerializer (validación)
    └── ItemFacturaSerializer (validación)
    ↓
11. Service Layer: apps/tenant/facturas/services.py
    ├── guardar_factura_desde_dto()
    ├── guardar_nota_credito_desde_dto()
    ├── importar_documento()
    └── eliminar_factura()
    ↓
12. Parser UBL: apps/tenant/facturas/ubl_parser.py
    ├── parse_ubl_to_dict()
    └── importar_factura_desde_ubl()
    ↓
13. Models: apps/tenant/facturas/models.py
    ├── Factura.save()
    ├── ItemFactura.save()
    └── NotaCredito.save()
    ↓
14. Database: PostgreSQL (multi-tenant)
```

### 1. Punto de Entrada: `workspace.html`

**Ubicación:** `apps/tenant/core/templates/tenant/core/workspace.html`

#### Estructura del Módulo Facturas

```html
{# Módulo Facturas v2.60 - HTML Centralizado en Core #}
<section id="tab-facturas" class="workspace-tab" style="display: none;">
  {# ⚠️ v2.60: Toolbar y contenido centralizados en Core #}
  {% include 'tenant/core/partials/facturas/list.html' %}
  {# ⚠️ v2.60: modals.html eliminado - Todo funciona con HTMX + Offcanvas #}
  {# El contenedor del offcanvas está en list.html: #offcanvas-container-facturas #}
</section>
```

#### Carga de Assets JavaScript

```html
{# En bloque extra_js de workspace.html #}
{% include 'tenant/facturas/partials/assets_facturas.html' %}
```

**Orden de Carga Crítico:**
1. `assets_core.html` (DOMUtils, TabulatorFactory, UIManager)
2. `facturas.api.js` (API wrapper)
3. `facturas.page.js` (módulo principal)
4. `facturas.editor.js` (editor de facturas, si aplica)

#### Configuración HTMX

```html
{# HTMX cargado globalmente en workspace.html #}
<script src="https://unpkg.com/htmx.org@1.9.10"></script>

{# Setup global de CSRF para HTMX #}
<script>
  document.body.addEventListener('htmx:configRequest', function(event) {
    const method = (event.detail.verb || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const token = getCSRFToken();
      if (token) {
        event.detail.headers['X-CSRFToken'] = token;
      }
    }
  });
</script>
```

### 2. Core API: `core/api/urls.py`

**Ubicación:** `apps/tenant/core/api/urls.py`

#### Router Dedicado para Facturas

```python
# ⚠️ v2.61.1: Routers dedicados por módulo (patrón de contabilidad y cotizaciones)
# ⚠️ FACTURAS: Router dedicado con todas las funcionalidades CRUD
path("v1/facturas/", include("apps.tenant.core.api.v1.facturas.urls")),
```

**Endpoints Disponibles:**
- `/api/v1/core/v1/facturas/facturas/` (CRUD principal - ReadOnly)
- `/api/v1/core/v1/facturas/items-factura/` (CRUD items)
- `/api/v1/core/v1/facturas/notas-credito/` (CRUD notas crédito)
- Todas las acciones `@action` se heredan automáticamente:
  - `upload-ubl/` (POST)
  - `upload-document/` (POST)
  - `summary/` (GET)
  - `ingest/{task_id}/status/` (GET)
  - `create-from-dto/` (POST)
  - `materialize/` (POST)
  - `{id}/xml/` (GET)
  - `{id}/app-response/` (GET)
  - `update-inbox-state/` (POST)
  - `gestor-offcanvas/` (GET - TemplateHTMLRenderer)

#### Gateway Directo

```python
# Gateway a APIs de apps (acceso directo a las apps sin facades)
path("_apps/facturas/", include("apps.tenant.facturas.api.urls")),
```

**Endpoints Disponibles:**
- `/api/v1/core/_apps/facturas/` (CRUD directo)
- `/api/v1/core/_apps/facturas/upload-ubl/`
- `/api/v1/core/_apps/facturas/upload-document/`
- `/api/v1/core/_apps/facturas/summary/`
- `/api/v1/core/_apps/facturas/ingest/{task_id}/status/`
- `/api/v1/core/_apps/facturas/create-from-dto/`
- `/api/v1/core/_apps/facturas/materialize/`
- `/api/v1/core/_apps/facturas/{id}/xml/`
- `/api/v1/core/_apps/facturas/{id}/app-response/`
- `/api/v1/core/_apps/facturas/update-inbox-state/`
- `/api/v1/core/_apps/facturas/gestor-offcanvas/`
- `/api/v1/core/_apps/facturas/items-factura/` (CRUD items)
- `/api/v1/core/_apps/facturas/notas-credito/` (CRUD notas crédito)

### 3. Core API Facade: `core/api/v1/facturas/`

**Ubicación:** `apps/tenant/core/api/v1/facturas/`

#### Estructura de Archivos

```
apps/tenant/core/api/v1/facturas/
├── __init__.py
├── urls.py                    # Router dedicado
├── viewsets.py                # Facade ViewSets
└── serializers.py             # Facade Serializers
```

#### ViewSets Facade

**Archivo:** `apps/tenant/core/api/v1/facturas/viewsets.py`

```python
class FacturaCoreViewSet(FacturaViewSet):
    """
    ⚠️ v2.61.1: Facade ViewSet para Facturas en Core API.
    
    Hereda todas las acciones @action de FacturaViewSet:
    - importar-ubl: POST
    - summary: GET
    - upload-ubl: POST
    - upload-document: POST
    - ingest/{task_id}/status: GET
    - create-from-dto: POST
    - materialize: POST
    - xml: GET (detail)
    - app-response: GET (detail)
    - update-inbox-state: POST
    - gestor-offcanvas: GET (TemplateHTMLRenderer)
    """
    authentication_classes = [SessionAuthentication]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.FacturaWorkspaceListSerializer
        elif self.action == 'retrieve':
            return ws_serializers.FacturaWorkspaceDetailSerializer
        return ws_serializers.FacturaWorkspaceSerializer
```

**Características:**
- ✅ **Herencia Completa**: Todas las acciones `@action` se heredan automáticamente
- ✅ **SessionAuthentication**: Autenticación por sesión (workspace)
- ✅ **Serializers Especializados**: Serializers optimizados para workspace

#### Router Dedicado

**Archivo:** `apps/tenant/core/api/v1/facturas/urls.py`

```python
from rest_framework.routers import DefaultRouter
from .viewsets import (
    FacturaCoreViewSet,
    ItemFacturaCoreViewSet,
    NotaCreditoCoreViewSet,
)

router = DefaultRouter(trailing_slash=True)
# ⚠️ CRÍTICO: Orden de registro importa - rutas específicas ANTES de ruta vacía ""
router.register(r'notas-credito', NotaCreditoCoreViewSet, basename='core-factura-nota-credito')
router.register(r'items-factura', ItemFacturaCoreViewSet, basename='core-factura-item')
router.register(r'facturas', FacturaCoreViewSet, basename='core-factura')  # ⚠️ AL FINAL para evitar greedy matching

urlpatterns = router.urls
```

### 4. App API: `facturas/api/`

**Ubicación:** `apps/tenant/facturas/api/`

#### ViewSets Principales

**Archivo:** `apps/tenant/facturas/api/viewsets.py`

##### `FacturaViewSet`

```python
class FacturaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gestión de facturas (ReadOnly).
    Expone CRUD limitado y acciones personalizadas.
    """
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
    lookup_field = 'id'
    pagination_class = StandardResultsSetPagination
    
    @action(detail=False, methods=['post'], url_path='upload-ubl')
    def upload_ubl(self, request):
        """Sube un archivo XML UBL 2.1 y lo importa."""
        # ...
    
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Retorna resumen de facturación neta."""
        # ...
    
    @action(detail=True, methods=['get'], url_path='xml')
    def xml(self, request, id=None):
        """Retorna el UBL XML completo de la factura."""
        # ...
    
    @action(detail=False, methods=['get'], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """Devuelve el HTML del formulario de factura para HTMX Offcanvas."""
        # ...
```

### 5. Service Layer: `facturas/services.py`

**Ubicación:** `apps/tenant/facturas/services.py`

#### Métodos Principales

```python
# v2.61.2: transaction.atomic envuelve SOLO la escritura en BD (no el parsing)
def guardar_factura_desde_dto(dto, xml_text=None, file_bytes=None, file_type='xml'):
    """
    Persiste factura desde DTO canónico del pipeline XML (SSoT).
    
    Lógica (v2.61.3):
    1. Valida configuración de empresa (SSoT)
    2. Normaliza números y NITs
    3. Resuelve naturaleza (VENTA/COMPRA)
    4. Extrae prefijo y consecutivo
    5. Parsea fecha de emisión (timezone-aware)
    6. TRANSACCIONAL (solo BD): busca por CUFE → crea o actualiza
    7. Silent Success: actualiza FacturaAnexos si AttachedDocument > Invoice
    8. Retorna {"id", "numero", "naturaleza", "created", "persisted": True}
    """
    # ...

def importar_documento(file_bytes, filename, preview, async_mode):
    """
    Importa documento usando el pipeline universal de documentos.
    
    Lógica (v2.61.3):
    1. Verifica si el pipeline universal está disponible
    2. Detecta tipo de documento (hint para XML/UBL)
    3. Llama a ingest_document() del pipeline universal
    4. ⚠️ v2.61.3: Si status_code >= 400 → propaga error inmediatamente
    5. Si preview=False, materializa usando guardar_factura_desde_dto()
       o guardar_nota_credito_desde_dto()
    6. ⚠️ v2.61.3: Retorna "persisted": True en respuesta exitosa (Factura y NC)
    """
    # ...

def eliminar_factura(factura):
    """
    Elimina una factura y todos sus registros relacionados.
    
    Lógica:
    1. Elimina nota de crédito asociada primero (si existe)
    2. Elimina anexos (OneToOne, se elimina automáticamente)
    3. Elimina factura (esto elimina automáticamente los items por CASCADE)
    """
    # ...
```

### 6. Parser UBL: `facturas/ubl_parser.py`

**Ubicación:** `apps/tenant/facturas/ubl_parser.py`

#### Funciones Principales

```python
def fast_get_cufe(xml_bytes: bytes) -> Optional[str]:
    """
    ⚡ v2.61.2: Pre-validación de Idempotencia — extrae CUFE/CUDE con regex pura.
    
    Ejecuta en milisegundos sobre los bytes crudos SIN parsear todo el XML.
    Busca contenido dentro de <cbc:UUID> o variantes con namespace.
    
    Patrón:
      r'<[^>]*:UUID[^>]*>([A-Za-z0-9\\-]{20,})</[^>]*:UUID[^>]*>'
    
    Retorna: CUFE (str) o None si no se encuentra
    """

def _limpiar_cdata_eficiente(xml_content: str) -> str:
    """
    v2.61.2: Limpia marcadores CDATA de forma eficiente mediante regex.
    Reemplaza <![CDATA[ ... ]]> preservando el contenido interno.
    """

def _extraer_invoice_desde_attached_document(root, xml_bytes):
    """
    v2.61.2: Extrae el Invoice/CreditNote embebido en AttachedDocument.
    
    Optimizaciones:
    - Si xml_bytes > 2MB: usa lxml.etree.iterparse (streaming, bajo consumo RAM)
    - Si < 2MB: parsing estándar (más rápido para archivos pequeños)
    - Limpieza CDATA con _limpiar_cdata_eficiente() (regex)
    - Buffer de memoria limitado a 10MB
    - Libera elementos procesados inmediatamente (elem.clear())
    """

def parse_ubl_to_dict(root, xml_bytes=None, naturaleza=None):
    """
    Mapea UBL 2.1 (root ya parseado) a DTO (dict) sin crear Factura.
    
    Lógica:
    1. Detecta si es AttachedDocument y extrae Invoice interno
       (usa _extraer_invoice_desde_attached_document con iterparse si >2MB)
    2. Obtiene namespaces dinámicos
    3. Extrae información básica (número, fecha, CUFE)
    4. Extrae emisor y receptor
    5. Extrae totales y moneda
    6. Construye DTO con datos extraídos
    """
```

### 6b. Parser Genérico: `apps/services/document_parser/xml_parser/parser.py`

**Ubicación:** `apps/services/document_parser/xml_parser/parser.py`

#### Correcciones v2.61.3

```python
# FIX: UnboundLocalError 'cannot access local variable re' (v2.61.3)
# Causa: import re dentro de _parse_invoice_ubl21() hacía que Python tratara
#        're' como variable local en todo el scope de la función.
# Solución: eliminados los 'import re' dentro de la función (líneas 270 y 316).
#           El módulo re ya está importado al inicio del archivo (línea 12).

# FIX: Doble timezone en fecha_emision (v2.61.3 / v2.61.2)
# Causa: issue_time puede incluir offset "-05:00" ya que la DIAN lo incluye.
# Solución: solo agrega "-05:00" si la cadena datetime NO tiene timezone ya.
if fecha_emision and "T" in fecha_emision:
    time_part = fecha_emision.split("T", 1)[1]
    has_tz = bool(re.search(r'[+-]\d{2}:\d{2}$', time_part)) or time_part.endswith('Z')
    if not has_tz:
        fecha_emision = f"{fecha_emision}-05:00"  # UTC-5 (Colombia)
```

### 7. Models: `facturas/models.py`

**Ubicación:** `apps/tenant/facturas/models.py`

#### Modelos Principales

```python
class Factura(models.Model):
    """
    Modelo principal de Facturas.
    Representa una factura electrónica UBL 2.1.
    """
    numero = models.CharField(max_length=50, unique=True)
    cufe = models.CharField(max_length=128, unique=True, db_index=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    naturaleza = models.CharField(max_length=10, choices=Naturaleza.choices)
    # Snapshot Emisor
    emisor_nit = models.CharField(max_length=20)
    emisor_razon_social = models.CharField(max_length=255)
    # Snapshot Receptor
    receptor_nit = models.CharField(max_length=20)
    receptor_razon_social = models.CharField(max_length=255)
    # Totales
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # ...
    
    class Meta:
        indexes = [
            models.Index(fields=['numero', 'fecha_emision']),
            models.Index(fields=['estado', 'naturaleza']),
            models.Index(fields=['cufe']),
            models.Index(fields=['empresa']),
        ]

class ItemFactura(models.Model):
    """
    Items de línea de una factura.
    """
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    linea_id = models.CharField(max_length=50)
    descripcion = models.TextField()
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # ...
    
    def save(self, *args, **kwargs):
        """Calcula subtotales automáticamente."""
        self.subtotal = self.cantidad * self.valor_unitario
        self.valor_iva = self.subtotal * (self.porcentaje_iva / Decimal('100.00'))
        self.total = self.subtotal + self.valor_iva
        super().save(*args, **kwargs)
```

### 8. Flujo de Datos Completo (v2.61.3)

#### Ejemplo: Importar Factura desde XML UBL

```
1. Usuario: Sube archivo XML UBL 2.1 en workspace.html
   → Botón "Importar XML / PDF" (data-action="subir-factura", sin onclick inline)
   ↓
2. HTMX: POST /api/v1/core/v1/facturas/facturas/upload-ubl/?preview=false&async=false
   (batch: acepta files[] con múltiples archivos)
   ↓
3. Core API Facade: FacturaCoreViewSet.upload_ubl()
   → Hereda de FacturaViewSet.upload_ubl() (todas las acciones heredan)
   ↓
4. App API: FacturaViewSet.upload_ubl()
   → ⚡ fast_get_cufe(xml_bytes): regex sobre bytes crudos
   │   ├─ CUFE ya existe → return 200 OK inmediato
   │   └─ CUFE nuevo → continuar
   → Detecta batch (files[]) → procesa cada archivo
   → Si >10 archivos → delega a Celery (202 + task_id)
   → Llama a services.importar_documento()
   ↓
5. Service Layer: importar_documento()
   → Llama a ingest_document() del pipeline universal
   → ⚠️ Si status_code >= 400 → propaga error inmediatamente (v2.61.3)
   → Obtiene DTO canónico
   ↓
6. Document Parser: parser.py (_parse_invoice_ubl21)
   → Extrae número, CUFE, emisor, receptor, totales
   → Timezone fix: agrega -05:00 solo si no hay tz en fecha_emision (v2.61.3)
   → Sin import re locales (fix UnboundLocalError v2.61.3)
   ↓
7. Service Layer: guardar_factura_desde_dto()
   → Valida empresa (SSoT)
   → Normaliza NITs y números
   → Resuelve naturaleza (VENTA/COMPRA)
   → transaction.atomic solo envuelve escritura BD (v2.61.2)
   → Busca por CUFE (idempotencia)
   → Crea o actualiza Factura
   → Silent Success: actualiza FacturaAnexos si AttachedDocument (v2.61.2)
   → Retorna {"id", "numero", "created", "persisted": True} (v2.61.3)
   ↓
8. Models: Factura.save() → ItemFactura.save() × N
   → Calcula subtotales automáticamente
   ↓
9. Response: {id, numero, naturaleza, created, persisted: true} (201 o 200)
   ↓
10. Frontend: facturas_ui.js — manejarSubidaArchivo()
    → Detecta data.id (no data.persisted) para saber si ya fue persistido (v2.61.3)
    │   ├─ data.id existe → ya persistido → cerrar offcanvas + recargar tabla
    │   ├─ data.id ausente + missingFields → mostrarFormularioCamposFaltantes()
    │   └─ data.id ausente + DTO completo → persistir vía create-from-dto
    ↓
11. Frontend: facturas_list.js — Tabulator recarga datos
    → _eliminandoFactura en scope módulo (fix ReferenceError v2.61.3)
    → rowClick ignorado durante eliminación
```

### 9. Ventajas de la Arquitectura

#### ✅ Desacoplamiento
- **Core API Facade**: Expone funcionalidades de apps individuales de forma unificada
- **Gateway Directo**: Permite acceso directo a APIs de apps sin facades
- **Service Layer**: Lógica de negocio centralizada e independiente

#### ✅ Modularidad
- **Templates Separados**: `list.html`, `offcanvas_factura.html`
- **JavaScript Modular**: `facturas.api.js`, `facturas.page.js`, `facturas.editor.js`
- **ViewSets Especializados**: Serializers optimizados para workspace

#### ✅ Resiliencia
- **SSoT (Single Source of Truth)**: Empresa siempre del tenant
- **Snapshot Pattern**: Datos de emisor/receptor guardados al momento de emisión
- **Idempotencia**: Importación por CUFE/CUDE evita duplicados

#### ✅ Escalabilidad
- **Router Dedicado**: Fácil agregar nuevas funcionalidades
- **Herencia de Acciones**: Todas las acciones `@action` se heredan automáticamente
- **Gateway Directo**: Acceso directo para casos especiales
- **Pipeline Universal**: Soporte para múltiples formatos (XML, PDF, XLS)

#### ✅ Inmutabilidad
- **Documentos Históricos**: Facturas son documentos históricos (no edición, solo eliminación)
- **Integridad Fiscal**: Snapshot garantiza integridad histórica

---

## 🔗 Dependencias y Aislamiento

### Dependencias Externas

**SSoT (Single Source of Truth):**
- `apps.tenant.empresa.models.Empresa`: Datos de empresa del tenant
- `apps.tenant.empresa.services.get_empresa_emisor_data()`: Obtiene datos del emisor
- `apps.tenant.empresa.models.MailInboxConfig`: Configuración de buzones de correo

**Pipeline Universal:**
- `apps.services.document_ingest.ingest_service.ingest_document()`: Parser universal de documentos
- `apps.services.document_parser.xml_parser.core`: Helpers genéricos de parsing XML

**Celery:**
- `apps.services.maildigester.tasks.fetch_and_process_billing_mail`: Tarea de ingesta por correo

### Aislamiento

**Multi-tenant:**
- ⚠️ **DJANGO-TENANTS**: Aislamiento completo por esquema
- ⚠️ **NO FILTRO MANUAL**: django-tenants maneja automáticamente el aislamiento

**Resiliencia:**
- ⚠️ **SNAPSHOT PATTERN**: Datos de emisor/receptor guardados al momento de emisión
- ⚠️ **SIN DEPENDENCIAS**: No depende de otras apps excepto SSoT (Empresa)

---

## 📝 Notas de Versión

### v2.61.3 — Alineación Backend-Frontend (2026-03-12)

**Backend (`services.py`):**
- ✅ `guardar_factura_desde_dto()`: retorna `"persisted": True` en el payload (201 y 200)
- ✅ `importar_documento()`: verifica `status_code >= 400` antes de intentar materializar el DTO
- ✅ `importar_documento()`: retorna `"persisted": True` también para `NotaCredito` (201)

**Backend (`parser.py`):**
- ✅ Fix `UnboundLocalError: cannot access local variable 're'`: eliminados dos `import re` locales dentro de `_parse_invoice_ubl21()` (líneas 270 y 316); el módulo `re` ya está importado globalmente (línea 12)
- ✅ Fix doble timezone en `fecha_emision`: `issue_time` de la DIAN puede incluir `-05:00`; ahora solo se agrega si no hay timezone ya presente

**Frontend (`facturas_ui.js`):**
- ✅ Fix `manejarSubidaArchivo`: condición cambiada de `!data.persisted` a `!data.id` para detectar de forma fiable si el backend ya persistió la factura
- ✅ Comentario en línea 1519 actualizado: refleja que `upload-ubl` puede retornar `{id, persisted:true}` (no siempre es parse-only)

**Frontend (`facturas_list.js`):**
- ✅ Fix `ReferenceError: _eliminandoFactura is not defined`: variable movida de scope local de `initTable()` al scope del módulo (línea 25), compartida correctamente con `initListEvents()`

**Cascade de versión (7 archivos a v2.61.3):**
- `services.py` docstring, `facturas_ui.js` comentario, `facturas_list.js` header, `ver_detalle_factura.js` header, `assets_facturas.html`, `list.html`, `workspace.html`

---

### v2.61.2 — Optimización Pipeline + Core API Facade + Solo Lectura

**Pre-validación de Idempotencia:**
- ✅ `fast_get_cufe(xml_bytes)` en `ubl_parser.py`: extrae CUFE con regex antes del parsing completo
- ✅ `upload_ubl` llama a `fast_get_cufe()` primero; si CUFE existe → `200 OK` inmediato

**Optimización del Pipeline (`ubl_parser.py`):**
- ✅ `_extraer_invoice_desde_attached_document`: usa `lxml.etree.iterparse` si `>2MB`
- ✅ `_limpiar_cdata_eficiente()`: limpieza CDATA por regex (no reemplazo manual de strings)
- ✅ `transaction.atomic` en `guardar_factura_desde_dto()` solo envuelve escritura BD

**Silent Success (`services.py`):**
- ✅ Si la factura ya existe, actualiza `FacturaAnexos.ubl_xml` si el nuevo XML es `AttachedDocument` (más completo que `Invoice` simple)

**Batch Processing (`viewsets.py`):**
- ✅ `upload_ubl` acepta `files[]` (múltiples archivos)
- ✅ Retorna resumen `{"creados": X, "duplicados": Y, "errores": Z, "resultados": [...]}`
- ✅ Si `>10` archivos → delega a Celery (`batch_upload_facturas_task`) → `202 + task_id`

**Core API Facade:**
- ✅ Router dedicado: `apps/tenant/core/api/v1/facturas/urls.py`
- ✅ `FacturaCoreViewSet`, `ItemFacturaCoreViewSet`, `NotaCreditoCoreViewSet`
- ✅ Serializers workspace: `WorkspaceListSerializer`, `WorkspaceDetailSerializer`
- ✅ `get_serializer_class()` retorna `None` para acciones que manejan datos directamente

**Frontend Solo Lectura:**
- ✅ `offcanvas_ver_factura.html`: todos los inputs → `<p class='form-control-plaintext'>`, sin botón Guardar
- ✅ `ver_detalle_factura.js`: solo GET, cierra offcanvas con warning si recibe 404
- ✅ `facturas_list.js`: botón "Ver" carga `gestor-offcanvas?readonly=true`
- ✅ Eliminación: cierra offcanvas, hash → `#facturas`, flag `_eliminandoFactura`
- ✅ Botones: eliminados `onclick` inline, solo `data-action` (event delegation)
- ✅ `facturas_editor.js` deshabilitado (comentado en `assets_facturas.html`)

**Frontend `facturas_ui.js`:**
- ✅ Validación preventiva en `manejarSubidaArchivo`: chequea `emisor` y `naturaleza` antes de persistir
- ✅ Búsqueda NIT en rutas alternativas para `AttachedDocument` (`sender_party_nit`, `sender_company_id`)
- ✅ `naturaleza` asignada automáticamente como `'COMPRA'` para `AttachedDocument`
- ✅ `limpiarNIT()`: elimina caracteres especiales del NIT
- ✅ `mostrarFormularioCamposFaltantes`: `<select>` para naturaleza, reconstrucción correcta de objetos anidados
- ✅ Protección doble click en botones de toolbar

---

### v2.60
- ✅ Emisión de facturas desde cotizaciones
- ✅ Validación de numeración DIAN
- ✅ Endpoint gestor-offcanvas para HTMX

### v2.40
- ✅ FK a Empresa requerida (ENFORCED MODE)
- ✅ Normalización de números de documento
- ✅ Resumen de facturación neta (excluye NC)
- ✅ Optimización de QuerySets con only()

### v2.37
- ✅ LIST_FIELDS y DETAIL_FIELDS para alineación Serializers ↔ Services ↔ UI
- ✅ QuerySets optimizados para listado y detalle

### v2.36
- ✅ Pipeline universal de documentos (FASE 2)
- ✅ Import seguro para Document Ingest Pipeline Universal (FASE 0)
- ✅ Endpoint universal upload-document (FASE 3)

### v2.35
- ✅ Pipeline XML Canónico (SSoT)
- ✅ guardar_factura_desde_dto() con idempotencia por CUFE
- ✅ guardar_nota_credito_desde_dto() con idempotencia por CUDE

### v2.30
- ✅ Service Layer Pattern
- ✅ API-First (DRF JSON-only)
- ✅ Parser UBL robusto con namespaces dinámicos

---

---

## 🐛 Registro de Bugs Corregidos

| Versión | Bug | Causa | Fix |
|---------|-----|-------|-----|
| v2.61.3 | `UnboundLocalError: cannot access local variable 're'` | `import re` dentro de `_parse_invoice_ubl21()` marcaba `re` como local → `re.search()` anterior fallaba | Eliminados `import re` locales (líneas 270 y 316); usa `re` global del módulo |
| v2.61.3 | `ReferenceError: _eliminandoFactura is not defined` | Declarado con `let` dentro de `initTable()` (scope local), usado en `initListEvents()` (scope hermano) | Movido al scope del módulo IIFE (junto a `let table`) |
| v2.61.3 | Doble timezone en `fecha_emision` | `issue_time` de DIAN ya incluye `-05:00`; se añadía un segundo offset | Fix: solo agrega `-05:00` si no hay timezone en la cadena |
| v2.61.3 | Frontend intentaba re-persistir factura ya guardada | Condición usaba `!data.persisted` (flag semántico a veces ausente) | Cambiado a `!data.id` (indicador concreto: si hay id, ya fue guardado) |
| v2.61.2 | `POST /upload-document/ → 403 Forbidden` | Endpoint incorrecto en frontend | Cambiado a `/upload-ubl/` en `facturas.api.js`, `maildigester.xml.modal.js`, templates |
| v2.61.2 | `POST /create-from-dto/ → 422` | DRF intentaba crear serializer para acciones que no lo usan | `get_serializer_class()` retorna `None` para acciones directas; `get_serializer()` maneja el caso |
| v2.61.2 | `GET /facturas/{id}/ → 404` tras eliminación | Frontend intentaba ver la factura recién eliminada | `ver_detalle_factura.js` cierra offcanvas y muestra warning en 404; hash → `#facturas` |
| v2.61.2 | Botón "Importar" disparaba múltiples eventos | `onclick` inline + listener duplicaban invocaciones | Eliminados `onclick` inline; solo `data-action` + flag `_subirNuevaEnProceso` |
| v2.61.2 | `422` por `emisor.nit` / `naturaleza` faltantes | `AttachedDocument` expone NIT en `SenderParty`, no en la ruta estándar | `manejarSubidaArchivo` busca NIT en rutas alternativas; `naturaleza='COMPRA'` auto-asignado |

---

**Documento actualizado manualmente**  
**Última actualización**: 2026-03-12  
**Versión del Sistema**: 2.61.3  
**Estado**: ✅ Sincronizado con todos los cambios aplicados hasta 2026-03-12  
**Módulos cubiertos**: `services.py`, `ubl_parser.py`, `parser.py`, `viewsets.py`, `facturas_ui.js`, `facturas_list.js`, `ver_detalle_factura.js`, `assets_facturas.html`, `list.html`, `workspace.html`
