# [MT] Arquitectura de Microtareas: Módulo Facturas

**Namespace:** `MT-FAC`
**Versión:** 3.5.0
**Estado:** ✅ STANDARDIZED
**SSoT Portal:** [AUDITORIA_FLUJO_FACTURAS.md](file:///c:/Users/Administrator/Documents/crm_sintel/apps/tenant/facturas/AUDITORIA_FLUJO_FACTURAS.md)

---

## 0. Resumen Ejecutivo

La app `facturas` gestiona facturas electronicas UBL 2.1, notas credito y la ingesta automatizada de documentos DIAN. Sus caracteristicas clave:

- **Inmutabilidad**: facturas de solo lectura post-creacion; correcciones via Nota Credito 1:1
- **Idempotencia por CUFE**: pre-validacion regex `fast_get_cufe()` antes del parsing completo (ms vs segundos)
- **Snapshot Pattern**: emisor/receptor congelados al momento de emision (resiliencia historica)
- **Naturaleza automatica**: VENTA si `emisor_nit == tenant_nit`, COMPRA en caso contrario
- **Pipeline universal**: `apps.services.document_ingest` como orquestador de parseo
- **Ingesta email**: `maildigester` → IMAP → adjuntos XML → pipeline → DB
- **Batch async**: archivos > 10 → Celery task con tracking via `MailIngestionRun`
- **Pull Model contabilidad**: `ExtractorFacturas` lee Factura/NotaCredito sin que facturas importe de contabilidad
- **Blob separation**: `FacturaAnexos` separa XMLs grandes de la fila principal (evita N+1 en listados)

---

## 1. Modelos

### 1.1 Mapa de Modelos

```
Empresa (FK SSoT desde empresa app)
    |
    +--- Factura (documento principal, lookup por PK)
              |
              +--- ItemFactura (CASCADE, N:1)
              |
              +--- FacturaAnexos (OneToOne CASCADE, blob storage)
              |
              +--- NotaCredito (OneToOne PROTECT, correcciones)

TenantProfile
    |
    +--- MailIngestionRun (tracking de ejecuciones email)

empresa.MailInboxConfig
    |
    +--- MailInboxState (cursor IMAP incremental, unique_together)

// DEPRECADO:
MailIngestionConfig (migracion pendiente a empresa.MailInboxConfig)
```

### 1.2 `Factura` (hereda `SintelTenantBaseModel`)

Documento inmutable post-creacion. Lookup por PK (sin UUID).

**Choices:**
- `TipoFactura`: FE / NC / ND
- `Estado`: BORRADOR / ENVIADA / ACEPTADA / RECHAZADA / ANULADA
- `Naturaleza`: VENTA / COMPRA (calculada automaticamente)
- `Categoria`: PRODUCTO / SERVICIO / MIXTO

| Campo | Tipo | Restriccion | Notas |
|---|---|---|---|
| `numero` | CharField(50, unique) | required | Ej: FST354 |
| `prefijo` | CharField(10, null) | — | Prefijo DIAN |
| `consecutivo` | IntegerField | required | Para ordering |
| `tipo` | CharField(2, choices) | default=FE | FE/NC/ND |
| `estado` | CharField(20, choices) | default=BORRADOR | |
| `naturaleza` | CharField(10, null, blank) | calculada | VENTA/COMPRA |
| `categoria` | CharField(10, choices) | default=SERVICIO | |
| `cufe` | CharField(128, unique, db_index, null) | CRITICO | Idempotencia DIAN |
| `fecha_emision` | DateTimeField | required | |
| `fecha_vencimiento` | DateField(null) | — | |
| `emisor_nit` | CharField(20) | required | Snapshot |
| `emisor_razon_social` | CharField(200) | required | Snapshot |
| `emisor_direccion/email/telefono/actividad_ciiu` | CharField(null) | — | Snapshot |
| `receptor_nit` | CharField(20) | required | Snapshot |
| `receptor_razon_social` | CharField(200) | required | Snapshot |
| `receptor_direccion/email/telefono` | CharField(null) | — | Snapshot |
| `moneda` | CharField(3) | default='COP' | |
| `subtotal/impuestos/total` | Decimal(15,2) | MinValue(0) | |
| `retefuente/reteica/reteiva` | Decimal(15,2) | MinValue(0) | v2.62, integracion contable |
| `forma_pago/medio_pago_codigo` | CharField(null) | — | |
| `payment_due_date` | DateField(null) | — | |
| `qr_code/qr_url` | TextField/URLField(null) | — | |
| `autorizacion_*` | varios (null) | — | Rango DIAN |
| `dian_validation_*` | varios (null) | — | ApplicationResponse |
| `dian_response_xml` | TextField(null) | — | |
| `xml_content` | TextField(null) | DEPRECADO | Usar FacturaAnexos |
| `xml_file_path` | CharField(null) | DEPRECADO | |

**Indexes:** `numero`, `fecha_emision` (condicional: estado=ACEPTADA), `fecha_emision` (general), `estado`, `naturaleza`. `cufe` tiene `unique=True` + `db_index=True` (no necesita indice adicional).

**Ordering:** `['-fecha_emision', '-consecutivo']`

**`save()`:**
- Auto-asigna `empresa` desde `Empresa.objects.first()` si `empresa_id` es None (fallback legacy)
- Calcula `total = subtotal + impuestos` si `total` es 0 o None

**`tiene_nota_credito` property:** `hasattr(self, 'nota_credito')` — usa related_name del OneToOne

### 1.3 `ItemFactura` (hereda `SintelTenantBaseModel`)

Lineas de la factura. Eliminacion via CASCADE en Factura.

| Campo | Tipo | Restriccion |
|---|---|---|
| `factura` | FK → Factura (CASCADE, related_name='items') | required |
| `linea_id` | CharField(10, null) | ID linea UBL |
| `codigo` | CharField(50, null) | Codigo de producto/servicio |
| `descripcion` | CharField(500) | required |
| `cantidad` | Decimal(10,2) | MinValue(0.01) |
| `unidad_medida` | CharField(10) | default='UND' |
| `valor_unitario` | Decimal(15,2) | MinValue(0) |
| `porcentaje_iva/valor_iva` | Decimal(5,2)/(15,2) | MinValue(0) |
| `porcentaje_retefuente/valor_retefuente` | Decimal(5,2)/(15,2) | v2.62 |
| `porcentaje_reteica/valor_reteica` | Decimal(5,2)/(15,2) | v2.62 |
| `subtotal/total` | Decimal(15,2) | MinValue(0), calculados en save() |
| `es_servicio` | BooleanField | heuristica por unidad_medida |
| `orden` | IntegerField | default=1 |

**Ordering:** `['factura', 'orden']`

**`save()`:**
- Auto-asigna `empresa` desde `factura.empresa`
- Calcula `subtotal = cantidad * valor_unitario`
- Calcula `valor_iva = subtotal * (porcentaje_iva / 100)`
- Calcula `total = subtotal + valor_iva`
- Heuristica: si `unidad_medida.upper() in {'ZZ'}` → `es_servicio = True`

### 1.4 `FacturaAnexos` (hereda `SintelTenantBaseModel`)

Blob storage separado para evitar cargar XMLs en listados.

| Campo | Tipo | Notas |
|---|---|---|
| `factura` | OneToOneField → Factura (CASCADE, related_name='anexos') | required |
| `ubl_xml` | TextField(null) | XML UBL completo |
| `application_response_xml` | TextField(null) | ApplicationResponse DIAN |
| `pdf_file` | FileField(upload_to='facturas/pdfs/', null) | PDF representacion grafica |

`db_table = 'facturas_factura_anexos'`

**`save()`:** Auto-asigna `empresa` desde `factura.empresa`

### 1.5 `NotaCredito` (hereda `SintelTenantBaseModel`)

Documento de correccion 1:1 con Factura. Inmutable post-creacion.

| Campo | Tipo | Restriccion | Notas |
|---|---|---|---|
| `factura` | OneToOneField → Factura (PROTECT, related_name='nota_credito') | required | PROTECT evita cascade accidental |
| `numero` | CharField(50, unique) | required | Ej: NC135 |
| `cude` | CharField(128, unique) | required | CUDE DIAN (idempotencia) |
| `fecha_emision` | DateTimeField | default=now | |
| `moneda` | CharField(8) | default='COP' | |
| `subtotal/impuestos/total` | Decimal(18,2) | MinValue(0) | |
| `retefuente/reteica/reteiva` | Decimal(15,2) | MinValue(0) | v2.62 |
| `motivo` | TextField(blank) | — | |
| `ref_factura_numero` | CharField(50, blank) | — | Redundancia para consultas |
| `ref_factura_cufe` | CharField(128, blank) | — | CUFE de factura original |
| `xml_content` | TextField(blank) | — | XML UBL de la NC |

**Indexes:** `cude`, `numero`, `fecha_emision`, `factura`

**Ordering:** `['-fecha_emision', '-created_at']`

**`save()`:** Auto-asigna `empresa` desde `factura.empresa`. Calcula `total = subtotal + impuestos` si es 0.

### 1.6 `MailIngestionRun` (hereda `SintelTenantBaseModel`)

Tracking de ejecuciones de ingesta por email.

| Campo | Tipo | Notas |
|---|---|---|
| `started_by` | FK → TenantProfile (SET_NULL, null) | Quien inicio la ingesta |
| `started_at` | DateTimeField(auto_now_add) | |
| `finished_at` | DateTimeField(null) | |
| `task_id` | CharField(128, db_index, unique) | ID Celery |
| `naturaleza` | CharField(10, choices, default='VENTA') | |
| `status` | CharField(20, choices, db_index) | PENDING/RUNNING/SUCCESS/FAILED/CANCEL_REQUESTED/CANCELED/ABORTED |
| `counts` | JSONField(default=dict) | xml_detected, imported, duplicates, errors |
| `summary` | JSONField(default=dict) | Detalles de ejecucion |

**Indexes:** `task_id`, `status`, `started_at`

### 1.7 `MailInboxState` (hereda `SintelTenantBaseModel`)

Cursor IMAP para procesamiento incremental.

| Campo | Tipo | Notas |
|---|---|---|
| `mailbox_config` | FK → empresa.MailInboxConfig (CASCADE) | SSoT |
| `last_seen_uid` | BigIntegerField(null, db_index) | NULL = primera ejecucion (historico completo) |
| `last_run_at` | DateTimeField(null) | |
| `total_processed` | PositiveIntegerField(default=0) | |

`unique_together = [['mailbox_config']]` — un estado por config

**Regla de negocio:** si `last_seen_uid is None` → procesar todos los UIDs desde 1; si existe → solo UIDs > last_seen_uid (incremental).

### 1.8 `MailIngestionConfig` — DEPRECADO

Mantener por migracion de datos. Usar `apps.tenant.empresa.models.MailInboxConfig` en codigo nuevo.

### 1.9 Invariantes Criticos

| Invariante | Mecanismo |
|---|---|
| Unicidad de factura | `numero unique=True` + `cufe unique=True` (ambos con db_index) |
| Idempotencia CUFE | `fast_get_cufe()` (regex, ms) antes del parsing + check DB por cufe |
| Naturaleza automatica | `_resolver_naturaleza()` compara NITs normalizados |
| Cascading Security para COMPRA | Valida `receptor_nit == tenant_nit` antes de persistir |
| NC 1:1 con Factura | `OneToOneField PROTECT` en NotaCredito |
| Empresa en todos los modelos | `save()` auto-asigna empresa desde relacion padre si esta None |
| XML en FacturaAnexos | `update_or_create` — nunca duplica anexos |
| MailInboxState unico por config | `unique_together = [['mailbox_config']]` |

---

## 2. Capa de Servicios

### 2.1 Arquitectura Modular

```
services/
  __init__.py         re-exports: FacturaBusinessService, FacturaCRUDService,
                      FacturaSelectors, LIST_FIELDS, DETAIL_FIELDS,
                      FacturaService (facade), FacturaServiceMixin
  business_service.py FacturaBusinessService + FacturaService (facade)
  crud_service.py     FacturaCRUDService
  selectors.py        FacturaSelectors + LIST_FIELDS/DETAIL_FIELDS
  api_mixins.py       FacturaServiceMixin (injection en ViewSet)
  services_mail_ingestion.py  Orquestacion ingesta email (enqueue, persist_run, process_sync)
```

### 2.2 Constantes de Campos (SSoT)

```python
LIST_FIELDS = (
    "id", "numero", "naturaleza", "estado", "fecha_emision", "fecha_vencimiento",
    "moneda", "subtotal", "impuestos", "total",
    "emisor_nit", "emisor_razon_social",
    "receptor_nit", "receptor_razon_social",
    "cufe", "qr_url",
)

DETAIL_FIELDS = (
    "id", "numero", "prefijo", "consecutivo", "tipo", "estado", "naturaleza", "categoria",
    "fecha_emision", "fecha_vencimiento",
    "emisor_nit", "emisor_razon_social", "emisor_direccion", "emisor_email",
    "receptor_nit", "receptor_razon_social", "receptor_direccion", "receptor_email",
    "moneda", "subtotal", "impuestos", "total",
    "cufe", "qr_url", "created_at", "updated_at",
)
```

### 2.3 `FacturaSelectors`

**`qs_list(search=None)`:**
```python
Factura.objects.select_related("nota_credito").only(*LIST_FIELDS)
if search: .filter(Q(numero) | Q(cufe) | Q(receptor_razon_social) | Q(emisor_razon_social))
.order_by("-fecha_emision", "-id")
```

**`qs_detail()`:**
```python
Factura.objects.select_related("nota_credito", "anexos").only(*DETAIL_FIELDS)
```

**`get_summary(empresa_id=None)`:** Dos aggregates independientes (ventas / compras):
```python
base_filter = Q(nota_credito__isnull=True)  # Excluye facturas que tienen NC asociada
if empresa_id: base_filter &= Q(empresa_id=empresa_id)
.aggregate(
    subtotal_neto=Coalesce(Sum('subtotal'), Decimal('0.00')),
    impuestos_neto=Coalesce(Sum('impuestos'), Decimal('0.00')),
    total_neto=Coalesce(Sum('total'), Decimal('0.00')),
    cantidad=Count('id')
)
```
Retorna: `{"ventas": {...}, "compras": {...}}`

**`obtener_anexo_xml(factura, tipo)`:**
- `tipo='ubl'` → `anexos.ubl_xml`; `tipo='app'` → `anexos.application_response_xml`
- `MAX_INLINE_BYTES = 2_000_000` (2MB): si XML > 2MB → `Content-Disposition: attachment` (fuerza descarga); si <= 2MB → inline
- Retorna `(HttpResponse | dict, int)`

### 2.4 `FacturaCRUDService`

**`crear(factura_data, anexos_data=None)`:** `@transaction.atomic`
```python
empresa = factura_data.get("empresa") or Empresa.objects.first()  # fallback
factura = Factura.objects.create(**factura_data)
if anexos_data:
    FacturaAnexos.objects.update_or_create(
        factura=factura,
        defaults={"empresa": factura.empresa, **anexos_data}
    )
return factura
```

**`eliminar(factura)`:** `@transaction.atomic`
```python
# 1. Eliminar NotaCredito primero (workaround OneToOne PROTECT)
if hasattr(factura, 'nota_credito') and factura.nota_credito:
    factura.nota_credito.delete()
# 2. Eliminar FacturaAnexos manualmente (CASCADE pero por seguridad)
try: FacturaAnexos.objects.get(factura=factura).delete()
except FacturaAnexos.DoesNotExist: pass
# 3. ItemFactura se elimina por CASCADE en Factura.delete()
factura.delete()
```

**`qs_list(search)` / `qs_detail()`:** Proxies a `FacturaSelectors`.

### 2.5 `FacturaBusinessService` — Orquestador Principal

**`normalize_document_number(value)`:**
```python
# strip() + regex elimina non-word excepto guion/punto
# Si es NIT numerico: elimina guiones y puntos
# Ej: "123.456.789-5" → "1234567895"
```

**`_resolver_naturaleza(emisor_nit, empresa_nit)`:**
```python
nit_dto = normalize_document_number(emisor_nit)
nit_tenant = normalize_document_number(empresa_nit)
return VENTA if nit_dto == nit_tenant else COMPRA
```

**`guardar_desde_dto(dto, xml_text=None, file_bytes=None, file_type='xml')`** → `(dict, int)`:

Flujo completo de persistencia:
```
1. get_empresa_emisor_data() → raise EmpresaNotConfiguredError → 422

2. Extraer: emisor={}, receptor={}, totales={}, identificadores={}, autorizacion={}
   Soporta DTO nested (emisor.nit) y flat (emisor_nit) — compatibilidad dual

3. normalize_document_number(numero, emisor_nit, receptor_nit)
   if missing: return {"error": "missing_required_fields"}, 422

4. _resolver_naturaleza(emisor_nit, empresa_config["nit"]) → VENTA|COMPRA

5. Cascading Security (solo COMPRA):
   if receptor_nit != tenant_nit: return {"error": "document_not_for_tenant"}, 422

6. Empresa.objects.get(nit=tenant_nit) → 404 si no existe

7. cufe = identificadores.get("cufe") or "cude" or "uuid" or dto.get("cufe")

8. Si tipo == "NC" (antes de idempotencia):
   - Buscar factura_original por ref_cufe → ref_numero
   - Si existe NC para factura_original: return {"error": "ya existe NC"}, 422
   - dto["factura_id"] = factura_original.id  [para CRUDService]

9. Idempotencia por CUFE:
   if cufe and Factura.objects.filter(cufe=cufe, empresa=empresa_instance).first():
       return {"id", "numero", "naturaleza", "cufe", "created": False}, 200

10. Resolver fecha_emision (parse_datetime | now), fecha_vencimiento (parse_date)
    Resolver tipo: creditnote → NC; debitnote → ND; default → FE
    estado = dto.get("estado") or ACEPTADA

11. Construir factura_data (30+ campos, snapshot de emisor/receptor)
    anexos_data = {"ubl_xml": xml_text o file_bytes.decode()}

12. FacturaCRUDService.crear(factura_data, anexos_data) @transaction.atomic

13. Si tipo == NC:
    - Buscar factura_original por ref_cufe o ref_factura_numero
    - NotaCredito.objects.create(
          empresa=empresa_instance,
          factura=factura,        [el doc NC, no la factura original]
          cude=cufe,
          motivo, ref_factura_numero, ref_factura_cufe, retefuente, reteica, reteiva
      )

14. Crear ItemFactura por cada item en dto["items"]
    (incluye: linea_id, codigo, descripcion, cantidad, unidad_medida,
     valor_unitario, porcentaje_iva, retefuente, reteica, reteiva, total)

15. return {"id", "numero", "naturaleza", "cufe", "created": True}, 201
```

**`importar_documento(file_bytes, filename, preview, async_mode, **kwargs)`:**
```
if settings.FEATURE_DOCUMENT_PIPELINE:
    result, code = ingest_document(content, filename, preview, async_mode)
    if code >= 400 or preview: return result, code
    dto = result["dto"]
    return guardar_desde_dto(dto, xml_text, file_bytes)
else:
    # Fallback legacy: parse_ubl_to_dict directamente
    root = _parse_xml(xml_str)
    dto = parse_ubl_to_dict(root, xml_bytes)
    if preview: return {"persisted": False, "dto": dto}, 200
    return guardar_desde_dto(dto, xml_text, file_bytes)
```

**`FacturaService` (Facade):** Para Celery/management commands. `crear_desde_xml()` → `importar_documento()`.

### 2.6 `services_mail_ingestion.py`

**`enqueue_mail_ingestion(config_id, profile, limit_messages)`:**
- Crea `MailIngestionRun(status='PENDING', started_by=profile)`
- Encola Celery task, actualiza `MailIngestionRun.task_id`

**`process_mail_ingestion_sync(config_id, empresa_id, run_id, limit_messages)`:**
- Obtiene `MailInboxState` para la config (cursor incremental)
- Llama `maildigester.fetch_and_process_billing_mail()`
- Aplica NIT validation por cada XML detectado
- Llama `guardar_desde_dto()` por cada documento valido
- Actualiza `last_seen_uid` en `MailInboxState`
- Retorna `{"xml_detected": N, "imported": M, "duplicates": K, "errors": J, "rejected_by_validation": R}`

**`persist_run_result(run, status, counts, summary)`:** Actualiza `MailIngestionRun` con resultado final.

---

## 3. Pipeline UBL — `utils/ubl_parser.py`

### 3.1 Pre-Validacion Rapida (Idempotencia)

```python
def fast_get_cufe(xml_bytes: bytes) -> str | None:
    # Regex sobre bytes crudos (NO parsing XML) — ~1-10ms
    patterns = [
        r'<[^>]*:UUID[^>]*>([A-Za-z0-9\-]{20,})</[^>]*:UUID[^>]*>',  # prioritario
        r'<UUID[^>]*>([A-Za-z0-9\-]{20,})</UUID>',                     # fallback
        ...
    ]
    # Retorna CUFE o None si no encontrado
```

Uso en `upload_ubl`:
```
fast_get_cufe(xml_bytes) → CUFE
if CUFE and Factura.objects.filter(cufe=CUFE).exists():
    return 200 OK inmediato  [evita parsing completo]
```

### 3.2 Parser XML Robusto

```python
parser = etree.XMLParser(
    ns_clean=True,
    remove_blank_text=True,
    recover=True,     # Continua con XML malformado
    huge_tree=True    # Soporta XMLs de 500MB+
)
```

**Namespaces dinamicos:** `_ns(root)` extrae namespaces del documento + define defaults UBL para `cbc`/`cac` sin asumir prefijos fijos.

**AttachedDocument:** Si el root es `AttachedDocument`, extrae el `Invoice` interno desde CDATA o `ExternalReference`.

### 3.3 DTO Canonico

`parse_ubl_to_dict(root, xml_bytes, naturaleza)` retorna:
```python
{
    "numero": str,
    "tipo": "FE"|"NC"|"ND",
    "document_type": str,  # Para resolver tipo en guardar_desde_dto
    "fecha_emision": datetime,  # timezone-aware
    "fecha_vencimiento": date | None,
    "emisor": {"nit": str, "razon_social": str, "direccion": str, ...},
    "receptor": {"nit": str, "razon_social": str, ...},
    "totales": {"subtotal": Decimal, "impuestos": Decimal, "total": Decimal,
                "retefuente": Decimal, "reteica": Decimal, "reteiva": Decimal},
    "identificadores": {"cufe": str, "uuid": str},
    "autorizacion": {"numero": str, "prefijo": str, "rango_desde": int, ...},
    "items": [{
        "linea_id": str, "codigo": str, "descripcion": str,
        "cantidad": Decimal, "unidad_medida": str,
        "valor_unitario": Decimal, "porcentaje_iva": Decimal,
        "porcentaje_retefuente": Decimal, "valor_retefuente": Decimal, ...
    }],
    "motivo": str,              # NC
    "ref_factura_cufe": str,    # NC
    "ref_factura_numero": str,  # NC
    ...
}
```

### 3.4 Validacion en Pipeline

`apps/services/document_ingest/validations/factura.py` — `FacturaValidator`:
- `numero` presente
- `identificadores.cufe` o `identificadores.uuid` presente
- `fecha_emision` formato valido
- Coherencia de totales: `abs((subtotal + impuestos) - total) < 0.10` (tolerancia 10 centavos)
- `emisor_nit` y `receptor_nit` presentes
- Retorna `(bool, error_code, [missing_fields])`

---

## 4. API Layer

### 4.1 `FacturaViewSet` — ReadOnly + Ingesta

`http_method_names = ['get', 'head', 'options', 'post', 'delete']` — sin PUT/PATCH (inmutabilidad).

**Permisos:** `[IsTenantMember, IsTenantAdminOrReadOnly]`

**Serializer por accion:**
- `list` → `FacturaListSerializer`
- `retrieve` → `FacturaDetailSerializer`
- `upload_ubl`, `upload_document`, `create_from_dto` → `UploadUBLFileSerializer` / custom

**`get_queryset()`:** Zero-Trust empresa_id en cada accion:
```python
empresa_id = get_or_create_profile(user).empresa_id
if action == "list":     qs = qs_list().filter(empresa_id=empresa_id)
elif action == "retrieve": qs = qs_detail().filter(empresa_id=empresa_id)
elif action == "destroy":  qs = .only('id', 'estado', 'empresa_id').filter(empresa_id=empresa_id)
```

**Filtros:**
```python
filterset_fields = {"estado": ["exact"], "naturaleza": ["exact"],
                    "fecha_emision": ["date__gte", "date__lte", "date", "exact"]}
search_fields = ["numero", "cufe", "receptor_razon_social", "emisor_razon_social"]
ordering_fields = ["fecha_emision", "consecutivo", "total"]
```

### 4.2 URL Map Completo

```
/api/v1/facturas/
  GET    /                            FacturaViewSet.list
  GET    /{id}/                       FacturaViewSet.retrieve
  DELETE /{id}/                       FacturaViewSet.destroy
  GET    /{id}/xml/                   FacturaViewSet._xml_action (UBL)
  GET    /{id}/app-response/          FacturaViewSet._app_response_action
  POST   /upload-ubl/                 FacturaViewSet.upload_ubl (single o batch con files[])
  POST   /upload-document/            FacturaViewSet.upload_document (pipeline universal)
  GET    /ingest/{task_id}/status/    FacturaViewSet.ingest_status
  POST   /create-from-dto/            FacturaViewSet.create_from_dto
  POST   /materialize/                FacturaViewSet.materialize (DEPRECATED)
  GET    /summary/                    FacturaViewSet.summary
  GET    /gestor-offcanvas/           FacturaViewSet.gestor_offcanvas (HTMX)

/api/v1/facturas/notas-credito/
  GET    /                            NotaCreditoViewSet.list
  GET    /{id}/                       NotaCreditoViewSet.retrieve
  DELETE /{id}/                       NotaCreditoViewSet.destroy
  GET    /{id}/xml/                   NotaCreditoViewSet.xml_action

/api/v1/facturas/items-factura/
  GET    /                            ItemFacturaViewSet.list
  GET    /{id}/                       ItemFacturaViewSet.retrieve

/api/v1/facturas/ingesta-correo/
  POST   /run/                        MailIngestionRunCreateAPIView
  GET    /runs/                       MailIngestionRunsListAPIView
  POST   /preview/                    MailIngestionPreviewAPIView
```

### 4.3 Handlers Clave

**`upload_ubl()`** — Algoritmo optimizado v2.61.2:
```
file = request.FILES.get("file")
xml_files = request.FILES.getlist("files[]")

if xml_files (batch):
    → _upload_ubl_batch()
else (single):
    xml_bytes = file.read()
    cufe_rapido = fast_get_cufe(xml_bytes)
    if cufe_rapido and Factura.objects.filter(cufe=cufe_rapido).exists():
        return 200 {"message": "duplicado detectado"}  // pre-validacion, 0 parsing
    if async=true:
        task = batch_upload_facturas_task.delay(xml_bytes, ...)
        return 202 {"task_id": task.id}
    else:
        payload, code = service_importar_documento(xml_bytes, ...)
        return Response(payload, status=code)
        if code in (200, 201): HX-Trigger: "listaFacturasChanged"
```

**`_upload_ubl_batch()`** — Umbral 10 archivos:
```
if len(xml_files) > 10:
    → batch_upload_facturas_task.delay([files]) → 202 Accepted + task_id
else:
    for file in xml_files:
        cufe_rapido = fast_get_cufe(file.read())
        if cufe_rapido duplicado → skip (pre-validacion)
        else: service_importar_documento(file_bytes)
    return 200 {"creados": N, "duplicados": M, "errores": K, "resultados": [...]}
```

**`destroy()`:**
```
instance = get_object()   // 404 si no existe
factura_id, numero = instance.id, instance.numero  // guardar antes de borrar
service_eliminar(instance)  // workaround NotaCredito PROTECT
return 204 con HX-Trigger: "listaFacturasChanged"
if ProtectedError: return 409 Conflict
```

**`create_from_dto()`:**
```
dto = request.data.get("dto")
payload, code = service_materializar(dto, empresa_id)
resp = Response(payload, status=code)
if code == 422 and "missing_fields" in payload:
    resp["HX-Trigger"] = "facturaValidationError"  // frontend error_injector.js
if code in (200, 201):
    resp["HX-Trigger"] = "listaFacturasChanged"
return resp
```

### 4.4 Serializers

**`FacturaListSerializer`** (solo lectura):
- Campos: todos de `LIST_FIELDS` + `has_nota_credito` (computed), `total_formateado`
- `get_total_formateado()`: formato COP → `$123.456,78`
- `get_has_nota_credito()`: `hasattr(obj, 'nota_credito')` y not None

**`FacturaDetailSerializer`** (solo lectura):
- Campos: todos de `DETAIL_FIELDS` + `items` (nested) + `anexos_meta`
- `get_anexos_meta()`: retorna metadata SIN cargar blobs: `{ubl_size, app_response_size, pdf_size, pdf_url, updated_at}`
- `items = ItemFacturaSerializer(many=True, read_only=True)`

**`NotaCreditoListSerializer`** (solo lectura): numero, cude, fecha_emision, subtotal, impuestos, total, retefuente, reteica, reteiva, motivo, ref_factura_numero

**`NotaCreditoDetailSerializer`**: hereda List + `factura_id`

**`MailIngestionRunListSerializer`**: id, started_at, finished_at, status, task_id, naturaleza, counts, summary

---

## 5. Integracion con Contabilidad (Pull Model)

**`apps/tenant/contabilidad/integracion/extractores/facturas.py`** — `ExtractorFacturas(AbstractExtractor)`

Facturas NUNCA importa de contabilidad. Contabilidad lee Factura/NotaCredito directamente.

**`extraer_pendientes()`:**
```
1. Facturas ACEPTADAS + no contabilizadas
2. Notas Credito + no contabilizadas
3. Map cada uno a TransaccionEconomica DTO
```

**`_mapear_factura_a_dto(factura)`:**
```
VENTA:
  Tercero = Receptor (Cliente)
  DEBE: CXC_CLIENTES (neto con retenciones)
  HABER: INGRESO_VENTAS (subtotal), IVA_GENERADO (impuestos)
  Si retefuente > 0: DEBE RETENCION_FUENTE, HABER CXC_CLIENTES (ajuste)

COMPRA:
  Tercero = Emisor (Proveedor)
  DEBE: GASTO_COMPRA (subtotal), IVA_DESCONTABLE (impuestos)
  HABER: PASIVO_PROVEEDORES (total)
```

**`_mapear_nota_a_dto(nota_credito)`:**
```
VENTA: DEVOLUCION_VENTA + reversar CXC_CLIENTES
COMPRA: DEVOLUCION_COMPRA + reversar PASIVO_PROVEEDORES
```

---

## 6. Ingesta por Email (Pipeline Completo)

```
[Usuario] POST /api/v1/facturas/ingesta-correo/run/ {config_id, limit_messages}
    → MailIngestionRunCreateAPIView
    → enqueue_mail_ingestion(config_id, profile, limit_messages)
       → MailIngestionRun(status='PENDING') creado
       → mail_ingestion_task.delay(run_id, config_id) encolado en Celery

[Celery Worker] mail_ingestion_task(run_id, config_id)
    → process_mail_ingestion_sync(config_id, empresa_id, run_id, limit)
       → get_mailbox_config(config_id) → MailboxConfigDTO (via empresa.mailbox_provider)
       → MailInboxState.objects.get_or_create(mailbox_config=config_id)
       → maildigester.fetch_and_process_billing_mail(
             config=MailboxConfigDTO,
             last_uid=state.last_seen_uid,  // NULL = historico completo
             limit=limit_messages
         )
          → IMAP connect → fetch UIDs > last_uid
          → extraer adjuntos XML de cada email
          → document_parser.detect_type() → "factura_electronica"
          → parse_ubl_to_dict() → DTO
       → Por cada DTO: FacturaBusinessService.guardar_desde_dto(dto)
       → Actualizar state.last_seen_uid = max UID procesado
       → persist_run_result(run, status='SUCCESS', counts, summary)

[Frontend] GET /api/v1/facturas/ingesta-correo/runs/ → lista MailIngestionRun
           GET /api/v1/facturas/ingest/{task_id}/status/ → estado Celery
```

---

## 7. Flujos E2E

### Flujo 1: Upload UBL Single (optimizado)

```
[Frontend] POST /api/v1/facturas/upload-ubl/ multipart {file: factura.xml}

[API] FacturaViewSet.upload_ubl()
  → xml_bytes = request.FILES["file"].read()
  → cufe_rapido = fast_get_cufe(xml_bytes)  // regex, ~5ms
  → if cufe_rapido and Factura.filter(cufe=cufe_rapido).exists():
       return 200 {"message": "duplicado"}  // sin parsing, sin DB write
  → service_importar_documento(xml_bytes, filename, preview=False)
  → FacturaBusinessService.importar_documento()
     → if FEATURE_DOCUMENT_PIPELINE: ingest_document() → DTO
       else: _parse_xml() → parse_ubl_to_dict() → DTO
     → guardar_desde_dto(dto, xml_text, file_bytes) @transaction.atomic
        → get_empresa_emisor_data()
        → normalize NITs → _resolver_naturaleza()
        → Cascading Security si COMPRA
        → Idempotencia por CUFE (segunda vez, dentro de atomic)
        → FacturaCRUDService.crear(factura_data, anexos_data)
           → Factura.objects.create()
           → FacturaAnexos.update_or_create()
        → Si NC: NotaCredito.objects.create()
        → ItemFactura.objects.create() x N items
        → return {"id", "numero", "created": True}, 201
  → Response(payload, 201) + HX-Trigger: "listaFacturasChanged"
```

### Flujo 2: Upload Batch > 10 Archivos (Async)

```
[Frontend] POST /api/v1/facturas/upload-ubl/ multipart {files[]: [f1.xml, f2.xml, ...x15]}

[API] FacturaViewSet._upload_ubl_batch()
  → len(xml_files) > 10 → async
  → batch_upload_facturas_task.delay([file_bytes_list], empresa_id)
  → return 202 {"task_id": "...", "message": "Procesando X archivos en background"}

[Celery] batch_upload_facturas_task(file_bytes_list, empresa_id)
  → Por cada file_bytes:
     fast_get_cufe() → check DB → skip si duplicado
     guardar_desde_dto()
  → Actualizar progreso en cache/DB

[Frontend polling] GET /api/v1/facturas/ingest/{task_id}/status/
  → Celery AsyncResult(task_id).state + result
  → PENDING | STARTED | SUCCESS {creados, duplicados, errores}
```

### Flujo 3: Nota Credito desde Email

```
[Email IMAP] Adjunto: NotaCredito.xml

[Maildigester] parse XML
  → document_type = "CreditNote"
  → DTO con tipo="NC", ref_factura_cufe="CUFE-original"

[Business] guardar_desde_dto(dto)
  → tipo = "NC" → buscar Factura con cufe=ref_factura_cufe
  → Validar no-duplicado: NotaCredito.objects.filter(factura=original).exists()
  → FacturaCRUDService.crear(factura_data, anexos_data)
     → Crea Factura (tipo=NC, es el documento NC en si)
     → Crea FacturaAnexos
  → NotaCredito.objects.create(
         factura=nueva_factura_NC,  // el doc NC
         cude=cufe,
         ref_factura_numero=factura_original.numero,
         ref_factura_cufe=factura_original.cufe
     )
```

### Flujo 4: Eliminacion de Factura con Nota Credito

```
[Frontend] DELETE /api/v1/facturas/{id}/

[API] FacturaViewSet.destroy()
  → get_object() → Factura filtrada por empresa_id
  → service_eliminar(instance)
  → FacturaCRUDService.eliminar(factura) @transaction.atomic
     1. factura.nota_credito.delete()  // primero (PROTECT workaround)
     2. FacturaAnexos.objects.get(factura).delete()
     3. factura.delete()  // ItemFactura CASCADE
  → 204 No Content + HX-Trigger: "listaFacturasChanged"
  → if ProtectedError: 409 Conflict
```

### Flujo 5: Resumen Financiero Neto

```
[Frontend] GET /api/v1/facturas/summary/

[API] FacturaViewSet.summary()
  → empresa_id = get_or_create_profile(user).empresa_id
  → FacturaSelectors.get_summary(empresa_id)
     → Q(nota_credito__isnull=True)  // excluye facturas que tienen NC
     → Aggregate ventas: SUM(subtotal, impuestos, total), COUNT(id)
     → Aggregate compras: SUM(subtotal, impuestos, total), COUNT(id)
  → 200 {"ventas": {...}, "compras": {...}}
```

---

## 8. Descomposicion en Microtareas

### MT-FACT-001: Idempotencia por CUFE — doble capa
- **Capa 1 (ms):** `fast_get_cufe()` regex sobre bytes crudos → check DB por index
- **Capa 2 (en transaction):** `Factura.objects.filter(cufe=cufe).first()` dentro de `guardar_desde_dto()`
- La capa 1 evita parsing completo en duplicados → mejora dramática en batch

### MT-FACT-002: Naturaleza automatica (SSoT)
- `_resolver_naturaleza()` normaliza NITs (quita guiones/puntos) antes de comparar
- VENTA si `normalized_emisor_nit == normalized_tenant_nit`
- COMPRA si son distintos
- Cascading Security adicional para COMPRA: valida receptor_nit == tenant_nit

### MT-FACT-003: DTO dual (nested + flat)
- `guardar_desde_dto()` soporta ambos formatos: `emisor.nit` (pipeline universal) y `emisor_nit` (legacy flat)
- Union con `or`: `emisor.get("nit") or dto.get("emisor_nit", "")`
- Permite migracion incremental sin romper clientes existentes

### MT-FACT-004: Blob separation (FacturaAnexos)
- `qs_list()` NO incluye campos blob → listados eficientes
- `qs_detail()` incluye `select_related("anexos")` pero usa `.only(DETAIL_FIELDS)` (sin blobs)
- `get_anexos_meta()` retorna metadata (tamaños, URL) SIN cargar contenido
- XMLs se sirven por endpoint dedicado `/{id}/xml/`

### MT-FACT-005: Silent Success en upload
- Si `FacturaAnexos.update_or_create()` detecta XML existente mas pequeño → actualiza con el nuevo (mas completo)
- Comportamiento documentado en urls.py como "Silent Success"

### MT-FACT-006: Workaround OneToOne PROTECT en eliminacion
- `NotaCredito.factura` es `OneToOne PROTECT` → no se puede eliminar Factura si tiene NC
- `FacturaCRUDService.eliminar()` elimina NC manualmente primero, luego Factura
- Riesgo: si la eliminacion de NC falla silenciosamente, la Factura tampoco se elimina (atomico)

### MT-FACT-007: Ingesta email incremental
- `MailInboxState.last_seen_uid` actua como cursor IMAP
- NULL = primera ejecucion (historico completo)
- Existente = solo procesar UIDs > last_seen_uid
- `unique_together = [['mailbox_config']]` garantiza 1 state por config

### MT-FACT-008: Batch async con umbral 10
- <= 10 archivos: sincrono con pre-validacion por archivo
- > 10 archivos: Celery task asincronico
- Resultado del task polleado via `/ingest/{task_id}/status/`

### MT-FACT-009: NotaCredito — vinculo 1:1 con Factura
- NC en UBL es un documento independiente pero se vincula a la Factura original
- En DB: se crea una `Factura(tipo=NC)` + un `NotaCredito` apuntando a esa Factura NC
- El campo `NotaCredito.factura` apunta al DOC NC, no a la factura original
- La referencia a la factura original esta en `ref_factura_cufe` y `ref_factura_numero`

### MT-FACT-010: FEATURE_DOCUMENT_PIPELINE flag
- Si `True` → usa `ingest_document()` del pipeline universal
- Si `False` → fallback legacy: `_parse_xml()` + `parse_ubl_to_dict()` directamente
- Permite despliegue progresivo sin romper produccion existente

---

## 9. Compliance AGENTS.md

| Regla | Estado | Evidencia |
|---|---|---|
| `SintelTenantBaseModel` | PASS | Todos los modelos heredan correctamente |
| `empresa_id` en queries | PASS | get_queryset() filtra por empresa_id en cada accion |
| `.only()` en querysets | PASS | LIST_FIELDS/DETAIL_FIELDS constantes; select_related controlado |
| `lookup_field = 'uuid'` | FAIL | FacturaViewSet usa PK entero (sin UUID en Factura) |
| Sin signals para logica | PASS | Service layer exclusivo |
| Sin imports de apps.public | PASS | Solo imports de apps.tenant.* y apps.services |
| Sin emojis en .py | PASS | Archivos Python limpios |
| FK a TenantProfile | PASS | MailIngestionRun.started_by → TenantProfile (correcto) |
| `BaseTenantViewSet` | FAIL | FacturaViewSet no hereda de BaseTenantViewSet |
| empresa_id auto-assign en save() | PASS | Factura/ItemFactura/FacturaAnexos/NotaCredito.save() con fallback |

---

## 10. Riesgos Tecnicos

### RIESGO-FACT-01: `FacturaViewSet` no hereda de `BaseTenantViewSet` [MEDIO]

**Descripcion:** `FacturaViewSet` hereda de `ReadOnlyModelViewSet` directamente. Autenticacion JWT+Session configurada manualmente.

**Impacto:** Si `BaseTenantViewSet` recibe updates de seguridad, no se heredan automaticamente.

**Mitigacion:** Refactorizar para heredar de `BaseTenantViewSet`.

### RIESGO-FACT-02: `lookup_field` usa PK entero [BAJO]

**Descripcion:** Factura, NotaCredito e ItemFactura no tienen campo UUID. URLs exponen PK entero.

**Impacto:** Viola AGENTS.md. Permite enumeration de IDs. Relevante para Factura que puede tener miles de registros.

**Mitigacion:** Agregar `uuid = UUIDField(...)` a `Factura` (y opcionalmente a NotaCredito), cambiar `lookup_field = 'uuid'`.

### RIESGO-FACT-03: `MailIngestionConfig` DEPRECADO en produccion [ALTO]

**Descripcion:** El modelo `MailIngestionConfig` en `facturas/models.py` esta marcado como DEPRECADO. Debe migrarse a `apps.tenant.empresa.models.MailInboxConfig`. El migration de datos no existe aun.

**Impacto:** Codigo legacy puede acceder a `MailIngestionConfig` con credenciales desactualizadas. Divergencia de configuracion entre tablas.

**Mitigacion:** Crear migration de datos, actualizar todo el codigo que use `MailIngestionConfig` a `empresa.MailInboxConfig`, eliminar el modelo.

### RIESGO-FACT-04: Doble idempotencia CUFE con race condition potencial [BAJO]

**Descripcion:** La idempotencia tiene dos capas:
1. `fast_get_cufe()` + check DB (fuera de atomic)
2. `Factura.objects.filter(cufe=cufe)` dentro de `guardar_desde_dto()` (dentro de atomic)

Si dos requests llegan simultaneamente con el mismo CUFE:
- Ambos pasan la capa 1 (check DB fuera de atomic devuelve None para ambos)
- Ambos entran a `guardar_desde_dto()`
- La segunda transaccion falla por `IntegrityError` en `cufe unique=True`

**Impacto:** `IntegrityError` no capturado en `guardar_desde_dto()` → 500.

**Mitigacion:** Capturar `IntegrityError` en `FacturaCRUDService.crear()` y retornar idempotentemente si es por CUFE duplicado.

### RIESGO-FACT-05: `get_summary()` excluye facturas con NC por `nota_credito__isnull=True` [MEDIO]

**Descripcion:** `get_summary()` filtra `Q(nota_credito__isnull=True)`. Esto excluye del resumen todas las facturas que tienen una NC asociada, aunque la NC sea parcial.

**Impacto:** El "total neto" no refleja el valor neto real (factura - nota credito). Una factura de $1000 con una NC de $100 deberia contar $900, pero actualmente no cuenta $1000 (excluida).

**Mitigacion correcta:** Calcular `total_facturas - total_NCs` en lugar de excluir facturas.

### RIESGO-FACT-06: NotaCredito.factura apunta al DOC NC, no a la factura original [CONCEPTUAL]

**Descripcion:** El campo `NotaCredito.factura` (OneToOne) apunta a una `Factura(tipo=NC)` que es el documento NC en si mismo. La referencia a la factura ORIGINAL que se esta corrigiendo esta solo en `ref_factura_cufe` y `ref_factura_numero` (campos texto, no FK).

**Impacto:** No se puede hacer JOIN directo entre NC y la factura original. Hay que filtrar por CUFE texto.

**Notar:** Esto es por diseño (UBL 2.1: NC es un documento independiente), pero puede sorprender a desarrolladores.

### RIESGO-FACT-07: `xml_content` DEPRECADO en Factura pero aun en uso [BAJO]

**Descripcion:** `Factura.xml_content` y `Factura.xml_file_path` estan marcados como DEPRECADOS. El contenido XML debe estar en `FacturaAnexos.ubl_xml`. El campo se mantiene "por compatibilidad durante migración" sin un plan de migración claro.

**Mitigacion:** Crear migration de datos que copie `xml_content` → `FacturaAnexos.ubl_xml` para registros existentes, luego null-out `xml_content`.

---

## 11. Catalogo de Eventos

| Evento | Disparado por | Consumidor |
|---|---|---|
| `factura.creada` | `FacturaCRUDService.crear()` | Frontend: HX-Trigger listaFacturasChanged |
| `factura.duplicada` | `guardar_desde_dto()` (idempotencia) | Frontend: 200 OK |
| `factura.eliminada` | `FacturaCRUDService.eliminar()` | Frontend: HX-Trigger listaFacturasChanged |
| `nota_credito.creada` | `NotaCredito.objects.create()` en `guardar_desde_dto()` | Contabilidad: ExtractorFacturas |
| `mail_ingestion.encolada` | `enqueue_mail_ingestion()` | MailIngestionRun: status PENDING |
| `mail_ingestion.completada` | `persist_run_result()` | MailIngestionRun: status SUCCESS/FAILED |
| `factura_batch.encolada` | `batch_upload_facturas_task.delay()` | Frontend polling /ingest/{task_id}/status/ |
| `factura.exportada_xml` | `obtener_anexo_xml()` | HttpResponse descarga/inline |

---

## 12. Estado de Produccion

| Area | Estado | Notas |
|---|---|---|
| Modelos | PRODUCCION | 6 modelos activos; 1 DEPRECADO |
| Pipeline UBL | PRODUCCION | Parser robusto, AttachedDocument, huge_tree |
| Idempotencia | PRODUCCION | Doble capa regex + DB index |
| API REST | PRODUCCION | ReadOnly + 8 acciones custom, batch async |
| Ingesta Email | PRODUCCION | IMAP incremental, Celery, MailIngestionRun |
| Naturaleza Automatica | PRODUCCION | NIT normalization, Cascading Security |
| Integracion Contabilidad | PRODUCCION | Pull Model, ExtractorFacturas con retenciones |
| Nota Credito | PRODUCCION | OneToOne, idempotencia por CUDE |
| Blob Separation | PRODUCCION | FacturaAnexos separado, metadata en detail |
| Tests | BUENO | 16 modulos de test |
| AGENTS.md compliance | 8 PASS / 2 FAIL | lookup_field y BaseTenantViewSet |
| Riesgos criticos | 1 ALTO | MailIngestionConfig DEPRECADO sin migration |
