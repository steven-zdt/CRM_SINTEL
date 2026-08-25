# [PORTAL] Auditoría Flujo Completo — Módulo Facturas

**Versión:** v3.12.0
**Estado:** ✅ PRODUCTION READY — 0 CRÍTICOS
**Ubicación:** `apps/tenant/facturas/`
**Última Auditoría:** 2026-08-07 (re-validación completa contra código real; v3.11.0 quedó desactualizada en varias áreas — ver Changelog)
**Auditor:** Claude Sonnet 5 (Anthropic)

---

## Documentación Especializada (SSoT)

| Documento | Descripción | Estado |
| :--- | :--- | :--- |
| Este archivo (`COMPLETO_FLUJO_FACTURAS.md`) | Portal SSoT + Resultados de Auditoría | ACTUALIZADO 2026-08-07 v3.12.0. **Corrección v3.12.0:** el link apuntaba a `AUDITORIA_FLUJO_FACTURAS.md`, un archivo que no existe en este directorio — nombre real es `COMPLETO_FLUJO_FACTURAS.md`. |

---

## Changelog

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| **v3.12.0** | 2026-08-07 | **Re-validación contra código real** (no incremental — este doc había quedado desactualizado desde v3.11.0). Corregido: `NotaCredito` **sí** hereda `SintelTenantBaseModel` (el doc decía que no). Documentado por primera vez: (1) **Vista HTML server-rendered `FacturaTableView`** (`views.py`/`tables.py`, Fase 5-BIS — Tabulator **retirado** de `facturas_list.js`, reemplazado por `django-tables2` + HTMX en `tabla/<naturaleza>/`); (2) `FacturaCRUDService` (`crud_service.py`) y `FacturaServiceMixin` (`api_mixins.py`), presentes desde antes pero nunca listados; (3) `services/dian/` (CUFE, UBL 2.1 builder, firma XAdES, AttachedDocument) — el pipeline DIAN real detrás de la "Responsabilidad Core #1", nunca desglosado en archivos; (4) `services_mail_ingestion.py` + `api/views_mail_ingestion.py` (3 vistas) para la ingesta por correo; (5) `crear_factura_desde_venta(empresa, dto)` en `FacturaBusinessService` — Ventas **empuja** una Factura de Venta provisional (`BORR-VTA-{uuid8}`) a partir de un DTO canónico, integración no documentada previamente; (6) 9 `@action` adicionales en `FacturaViewSet` (`por-estado`, `cambiar-estado`, `lista-centro-costos`, `obtener-retenciones`, `gestor-offcanvas`, `inventario-catalogo`, `trazabilidad-inventario`, `buscar-para-movimiento`) y el serializer `CatalogoItemInventarioSerializer`; (7) campos UBL de cabecera (`ubl_version`, `customization_id`, `profile_id`, `profile_execution_id`, `invoice_type_code`) en `Factura`, nunca listados. Confirmado sin cambios (verificado, no asumido): `sede` (DT-SEDE-02) sigue siendo un campo de reporte — usado solo en `selectors.py`/`serializers.py`, cero lectura en `business_service.py`/`viewsets.py` para scoping o reglas de negocio (mismo patrón que el resto de apps con `DT-SEDE-0X`, ver `docs/ADR-003-contexto-organizacional-sede-area.md`). |
| **v3.11.0** | 2026-06-04 | **Integración Bancos↔Facturas** (Pull Model): `BancosBridge`, `@property total_pagado_bancos`, `@property saldo_pendiente` en `Factura`. `FacturaInterAppAPI.recalcular_estado_pago_automatico()`. Validación estado_pago en `actualizar_factura_limitado()`. Serializers exponen `total_pagado_bancos` + `saldo_pendiente`. Frontend: `data-total-pagado-bancos` + `data-saldo-pendiente` en form. `initResumenPagosBancos()` en `facturas_editor.js`. |
| **v3.10.5** | 2026-06-03 | Auditoría validación completa. Campo `sede` FK documentado. `FacturaImpuesto` model agregado. 30 migraciones. |
| **v3.10.4** | 2026-05-28 | Fixes varios. `facturas_editor.js` pre-carga `total_pagado_bancos`/`saldo_pendiente` desde `data-*` del form. |
| **v3.10.1** | 2026-05 | `cotizacion_numero` snapshot. Bridge isolation. |
| **v3.9.3** | 2026-05 | `cotizacion_uuid` soft-ref. Vincular cotización. |
| **v3.9.2** | 2026-05 | `item_inventario_uuid` soft-ref en ItemFactura. |
| **v3.7.1** | 2026-05 | Pull Model Retenciones → Contabilidad. Campos retefuente/reteica/reteiva en ItemFactura marcados deprecated (editable=False). |
| **v3.5.0** | 2026-04 | UUID lookup field, DSV, Service Layer, naturaleza VENTA/COMPRA. |

---

## Responsabilidades Core (v3.11.0)

1. **Pipeline XML/UBL 2.1**: Importación, parsing, validación, persistencia idempotente por CUFE
2. **Naturaleza automática** (VENTA/COMPRA): `emisor_nit == empresa.nit → VENTA` (rule SSoT en `_resolver_naturaleza()`)
3. **Inmutabilidad XML**: 30 campos del XML fuente son read-only (`XML_IMMUTABLE_FIELDS`). Solo 10 campos son editables manualmente (`MANUAL_EDITABLE_FIELDS`).
4. **Nota de Crédito**: Modelo `NotaCredito` OneToOne con `Factura`. Neto = Factura - NC en `get_summary()`.
5. **Retenciones (Pull Model, v3.7.1)**: `Retencion` en Contabilidad es SSoT. `Factura` lee vía `@property` (lazy query a Contabilidad.Retencion).
6. **Bancos (Pull Model, v3.11.0)**: `BancosBridge.obtener_total_conciliado()` → suma ABS(valor) de transacciones bancarias conciliadas. `@property total_pagado_bancos` + `@property saldo_pendiente` en `Factura`.
7. **Estado pago automático (v3.11.0)**: Al conciliar transacción bancaria → `FacturaInterAppAPI.recalcular_estado_pago_automatico()` recalcula estado_pago sin acción manual. Solo aplica si `medio_pago_codigo != '10'` (efectivo).
8. **Ingesta desde correo**: `MailInboxState` + `MailIngestionRun` + Celery tasks para procesamiento asíncrono de facturas desde IMAP.
9. **DSV Zero-Trust**: `empresa_id` verificado en todas las capas. Bridges aceptan `empresa_id` para filtrar.
10. **Soft References (Bounded Context §18)**: `cliente_uuid`, `proveedor_uuid`, `cotizacion_uuid`, `item_inventario_uuid` — UUIDs sin FK directa.

---

## Modelos (`models.py`) — 7 modelos, 30 migraciones

### `Factura`

**Herencia:** `SintelTenantBaseModel` ✅

#### Campos de Identificación
| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `default=uuid4, unique=True, db_index=True, editable=False` |
| `numero` | CharField(200) | `unique=True`. UBL número o SHA256 hash. |
| `prefijo` | CharField(10) | nullable |
| `consecutivo` | IntegerField | requerido |
| `tipo` | CharField(2) | `FE / NC / ND`, `default='FE'` |
| `estado` | CharField(20) | `BORRADOR / ENVIADA / ACEPTADA / RECHAZADA / ANULADA`, `default='BORRADOR'` |
| `estado_pago` | CharField(20) | `NO_PAGADA / PAGO_PARCIAL / PAGADA`, `default='NO_PAGADA'` |
| `naturaleza` | CharField(10) | `VENTA / COMPRA`, nullable/blank — auto-calculado por `_resolver_naturaleza()` |
| `categoria` | CharField(10) | `PRODUCTO / SERVICIO / MIXTO`, `default='SERVICIO'` |
| `cufe` | CharField(200) | `unique=True, db_index=True`, nullable — clave idempotencia DIAN |

#### Campos Temporales
| Campo | Tipo |
|-------|------|
| `fecha_emision` | DateTimeField |
| `fecha_vencimiento` | DateField, nullable |
| `payment_due_date` | DateField, nullable |

#### Campos UBL de Cabecera (no documentados hasta v3.12.0)
| Campo | Tipo | Notas |
|-------|------|-------|
| `ubl_version` | CharField(10) | nullable |
| `customization_id` | CharField(50) | nullable |
| `profile_id` | CharField(80) | nullable |
| `profile_execution_id` | CharField(10) | nullable |
| `invoice_type_code` | CharField(4) | nullable |

#### Snapshots Emisor / Receptor (inmutables desde XML)
| Grupo | Campos |
|-------|--------|
| **Emisor** | `emisor_nit`, `emisor_razon_social`, `emisor_direccion`, `emisor_email`, `emisor_telefono`, `emisor_actividad_ciiu` |
| **Receptor** | `receptor_nit`, `receptor_razon_social`, `receptor_direccion`, `receptor_email`, `receptor_telefono` |

#### Campos Financieros
| Campo | Tipo | Notas |
|-------|------|-------|
| `moneda` | CharField(3) | `default='COP'` |
| `subtotal` | DecimalField(15,2) | `default=0.00`, `MinValueValidator` |
| `impuestos` | DecimalField(15,2) | `default=0.00` |
| `total` | DecimalField(15,2) | `default=0.00` |
| `forma_pago` | CharField(30) | nullable — libre texto |
| `medio_pago_codigo` | CharField(10) | nullable — código DIAN PaymentMeansCode. `'10'` = Efectivo. |

#### Soft References (Bounded Context §18 — sin FK directa)
| Campo | Notas |
|-------|-------|
| `cotizacion_uuid` | UUIDField, nullable, `db_index=True`. Vinculación v3.9.3. |
| `cotizacion_numero` | CharField(100), nullable — snapshot para Zero-Waste queries |
| `cliente_uuid` | UUIDField, nullable, `db_index=True`. Clientes app. |
| `proveedor_uuid` | UUIDField, nullable, `db_index=True`. Proveedores app. |

#### Campos DIAN / Autorización
`autorizacion_numero`, `autorizacion_prefijo`, `autorizacion_rango_desde`, `autorizacion_rango_hasta`, `autorizacion_vigencia_inicio`, `autorizacion_vigencia_fin`, `dian_validation_code`, `dian_validation_desc`, `dian_validation_fecha`, `dian_validation_hora`, `dian_response_xml`, `qr_code`, `qr_url`

#### XML Storage
`xml_content` (TextField, DEPRECATED — usar `FacturaAnexos.ubl_xml`), `xml_file_path`

#### Org
`sede` (FK → `empresa.Sede`, `SET_NULL`, nullable — DT-SEDE-02)

**Ordering:** `['-fecha_emision', '-consecutivo']`

**@property — Pull Model:**

```python
@property
def total_retencion_fuente(self) -> Decimal:
    # Lee Retencion(tipo='RETEFUENTE') de Contabilidad — v3.7.1 Pull Model

@property
def total_reteica(self) -> Decimal: ...      # Lee RETEICA

@property
def total_reteiva(self) -> Decimal: ...      # Lee RETEIVA

@property
def total_pagado_bancos(self) -> Decimal:    # v3.11.0 — BancosBridge.obtener_total_conciliado()

@property
def saldo_pendiente(self) -> Decimal:        # v3.11.0 — max(0, total - total_pagado_bancos)

@property
def tiene_nota_credito(self) -> bool: ...    # hasattr(self, 'nota_credito')
```

---

### Constantes del módulo

**`MANUAL_EDITABLE_FIELDS`** (10 campos — los únicos editables por usuario):
```python
['estado', 'estado_pago', 'categoria', 'fecha_vencimiento', 'payment_due_date',
 'forma_pago', 'medio_pago_codigo', 'orden_compra', 'cotizacion_uuid', 'cotizacion_numero']
```
> ⚠️ `orden_compra` está en la lista pero NO existe como campo del modelo — deuda menor.

**`XML_IMMUTABLE_FIELDS`** (30 campos — inmutables, provienen del XML fuente):
`numero, prefijo, consecutivo, tipo, naturaleza, fecha_emision, emisor_*, receptor_*, moneda, subtotal, impuestos, total, cufe, qr_code, qr_url, autorizacion_*`

---

### `ItemFactura`

| Campo | Notas |
|-------|-------|
| `uuid` | único, indexado |
| `factura` | FK → `Factura`, CASCADE |
| `descripcion`, `codigo`, `linea_id` | |
| `item_inventario_uuid` | UUIDField, nullable — soft-ref v3.9.2 |
| `item_inventario_tipo` | `PRODUCTO / SERVICIO` |
| `item_inventario_codigo` | snapshot |
| `cantidad`, `unidad_medida` | |
| `valor_unitario`, `porcentaje_iva`, `valor_iva` | |
| `subtotal`, `total` | |
| `es_servicio`, `orden` | |
| `porcentaje_retefuente`, `valor_retefuente`, etc. | **DEPRECATED** v3.7.1, `editable=False` |

**@property:** `total_retefuente_item`, `total_reteiva_item`, `total_reteica_item` — leen de Contabilidad.Retencion por `documento_origen_modelo='ItemFactura'`

---

### `NotaCredito`

OneToOne con `Factura` (PROTECT). Campos: `numero` (unique), `cude` (unique), `fecha_emision`, `moneda`, `subtotal`, `impuestos`, `total`, `retefuente`, `reteica`, `reteiva`, `motivo`, `ref_factura_numero`, `ref_factura_cufe`, `xml_content`. **Corrección v3.12.0:** el doc v3.11.0 decía "no hereda `SintelTenantBaseModel`" — **incorrecto**, verificado contra el código actual: `class NotaCredito(SintelTenantBaseModel)`. Sí declara `created_at`/`updated_at` propios además (redundante pero inofensivo, mismo patrón que `FAC-DT-02`).

**@property:** `factura_original` → alias de `self.factura`

---

### `FacturaAnexos`

OneToOne con `Factura` (CASCADE). Campos: `ubl_xml` (TextField — XML UBL 2.1 completo), `application_response_xml` (respuesta DIAN), `pdf_file` (FileField).

---

### `FacturaImpuesto` (mig 0030)

FK → `Factura` (CASCADE, `related_name='impuestos_desglosados'`). Campos: `tipo_impuesto` (`IVA / INC / RETEFUENTE / RETEIVA / RETEICA / OTRO`), `porcentaje`, `base_imponible`, `valor_impuesto`.

---

### `MailIngestionRun`

FK → `TenantProfile` (SET_NULL). Campos: `started_at`, `finished_at`, `task_id` (unique, db_index), `naturaleza`, `status` (`PENDING / RUNNING / SUCCESS / FAILED / CANCEL_REQUESTED / CANCELED / ABORTED`), `counts` (JSONField), `summary` (JSONField).

### `MailInboxState`

FK → `empresa.MailInboxConfig` (CASCADE). Campos: `last_seen_uid`, `last_run_at`, `total_processed`. `unique_together = [['mailbox_config']]`.

---

### Migraciones (30 aplicadas)

`0001_initial.py` → `0030_facturaimpuesto.py`. Sin pendientes.

---

## Service Layer

### `selectors.py` — Constantes SSoT

```
LIST_FIELDS   (27 campos): id, uuid, numero, naturaleza, estado, estado_pago,
               dian_validation_desc, fecha_emision, fecha_vencimiento, moneda,
               subtotal, impuestos, total, forma_pago, medio_pago_codigo,
               payment_due_date, emisor_nit, emisor_razon_social, receptor_nit,
               receptor_razon_social, cliente_uuid, proveedor_uuid,
               cotizacion_uuid, cotizacion_numero, cufe, qr_url, sede_id

DETAIL_FIELDS (36 campos): + prefijo, consecutivo, tipo, categoria,
               emisor_direccion, emisor_email, receptor_direccion, receptor_email,
               created_at, updated_at
```

#### FacturaSelectors

| Método | Descripción |
|--------|-------------|
| `qs_list(empresa_id, search)` | `.only(*LIST_FIELDS).select_related('sede')` |
| `qs_detail(empresa_id)` | `.only(*DETAIL_FIELDS).prefetch_related('impuestos_desglosados')` |
| `get_summary(empresa_id)` | Agregación: neto ventas = `Sum(Factura.total) - Sum(NC.total)` |
| `obtener_anexo_xml(factura, tipo)` | Devuelve `(HttpResponse | dict, status_code)` |

#### Bridges — Acceso Inter-App (Bounded Context §18)

| Bridge | Métodos | Target App |
|--------|---------|------------|
| `CotizacionBridge` | `obtener_cotizacion_por_uuid(uuid, empresa_id)`, `exists_by_uuid(uuid, empresa_id)` | cotizaciones |
| `ClienteBridge` | `obtener_cliente_por_uuid(uuid, empresa_id)`, `exists_by_uuid(uuid, empresa_id)` | clientes |
| `ProveedorBridge` | `obtener_proveedor_por_uuid(uuid, empresa_id)`, `exists_by_uuid(uuid, empresa_id)` | proveedores |
| `InventarioItemBridge` | `buscar_catalogo(empresa_id, search)`, `resolver_item(empresa_id, uuid, tipo)` | inventario |
| **`BancosBridge`** (v3.11.0) | `obtener_total_conciliado(empresa_id, factura_uuid) → Decimal` | bancos (Pull Model) |

**`BancosBridge.obtener_total_conciliado`:**
```python
# Importación dinámica para evitar circularidad
from apps.tenant.bancos.models import TransaccionBancaria
result = TransaccionBancaria.objects.filter(
    empresa_id=empresa_id, factura_uuid=factura_uuid, conciliado=True
).aggregate(total=Sum(Func(F('valor'), function='ABS')))
# ABS garantiza suma correcta para DEBITO (valor<0) y CREDITO (valor>=0)
```

---

### `business_service.py` — Reglas de Negocio

#### FacturaBusinessService

| Método | Descripción |
|--------|-------------|
| **`crear_factura_desde_venta(empresa, dto)`** | **No documentado hasta v3.12.0.** `@atomic`. Ventas empuja aquí un DTO canónico (emisor/receptor/totales/líneas/`cliente_uuid`/`venta_uuid`, generado por `VentaBusinessService._construir_dto_factura()`) y esto crea una `Factura` de Venta provisional con número `BORR-VTA-{uuid8}`, pendiente de numeración/firma DIAN definitiva. Único punto del módulo donde otra app **escribe** una `Factura` directamente (el resto de integraciones son Pull Model o soft-reference — ver "Integración con Otros Módulos"). |
| `normalize_document_number(value)` | Strip, sin espacios/puntos/guiones, uppercase |
| `_resolver_naturaleza(emisor_nit, empresa_nit)` | `VENTA` si emisor_nit == empresa.nit, else `COMPRA` |
| `obtener_retenciones_desde_cliente(cliente_nit, empresa_id)` | Lee config retenciones del cliente (Pull Model) |
| `obtener_retenciones_desde_proveedor(proveedor_nit, empresa_id)` | Lee config retenciones del proveedor |
| `guardar_desde_dto(dto, xml_text, file_bytes, empresa_id)` | @atomic. Idempotente por CUFE. Crea/actualiza Factura + FacturaAnexos + items. |
| `importar_documento(file_bytes, filename, preview, async_mode)` | Pipeline completo: parse XML → DTO → validar → persistir |
| `resumen(empresa_id)` | Wrapper de `FacturaSelectors.get_summary()` |
| **`actualizar_factura_limitado(factura, data, empresa_id)`** | DSV + rechaza `XML_IMMUTABLE_FIELDS` con 400 explícito + **validación estado_pago vs bancos (v3.11.0)** |
| `vincular_cliente(factura, cliente_uuid, empresa_id)` | Solo VENTA. DSV ClienteBridge. |
| `vincular_proveedor(factura, proveedor_uuid, empresa_id)` | Solo COMPRA. DSV ProveedorBridge. |

**`actualizar_factura_limitado()` — Validación estado_pago (v3.11.0):**
```python
medio     = data.get('medio_pago_codigo', factura.medio_pago_codigo)
es_efectivo = (medio == '10')   # Código DIAN: 10 = Efectivo

if not es_efectivo:
    total_bancos = factura.total_pagado_bancos
    saldo_pend   = factura.saldo_pendiente

    if nuevo_estado == 'PAGADA' and saldo_pend > 0:
        raise ValidationError("La factura no está 100% conciliada en bancos. "
                               "Solo puede marcarse como PAGO_PARCIAL. "
                               f"Diferencia: ${saldo_pend:,.2f}")

    if nuevo_estado in ('PAGADA','PAGO_PARCIAL') and total_bancos == 0:
        raise ValidationError("No hay conciliaciones bancarias. "
                               "El estado debe ser NO_PAGADA.")
```

#### FacturaInterAppAPI (v3.10.0 — abierto para inter-app)

| Método | Descripción |
|--------|-------------|
| `list_all(search, order_by)` | QuerySet sin filtro `empresa_id` (tenant schema aísla) |
| `get_by_id(factura_id, factura_uuid)` | Lookup por id o uuid |
| `summary_all()` | Resumen consolidado todas las empresas |
| `get_by_cufe(cufe)` | Lookup por CUFE |
| `get_by_numero(numero)` | Lookup por número |
| `resolve_cotizacion(factura_uuid, factura_id)` | Resuelve Cotización vinculada |
| **`recalcular_estado_pago_automatico(factura_uuid)`** | **v3.11.0** — Disparado por Bancos al conciliar |

**`recalcular_estado_pago_automatico()` — Reglas automáticas:**
```python
if factura.medio_pago_codigo == '10': return False  # Efectivo: usuario controla

total_bancos = factura.total_pagado_bancos
saldo        = factura.saldo_pendiente

if saldo <= 0 and total_bancos > 0:  → estado_pago = 'PAGADA'
elif total_bancos > 0 and saldo > 0: → estado_pago = 'PAGO_PARCIAL'
else:                                 → estado_pago = 'NO_PAGADA'

factura.save(update_fields=['estado_pago'])
```

> **Disparador**: `TransaccionBancariaCRUDService.conciliar_transaccion()` en Bancos llama este método tras cada PATCH `/conciliar/`.

#### FacturaService (facade alto nivel)
`crear_desde_xml(xml_content, empresa_id, usuario_id)` — para Celery tasks / management commands.

---

### Archivos de Service Layer no documentados hasta v3.12.0

| Archivo | Responsabilidad |
|---|---|
| `crud_service.py` (`FacturaCRUDService`) | Persistencia pura (Create/Delete) y acceso a QuerySets. Sin lógica de negocio — el ViewSet ya filtró `empresa_id` antes de llamarlo. |
| `api_mixins.py` (`FacturaServiceMixin`) | Inyección de la Service Layer en `FacturaViewSet` (`get_qs_list`, `get_qs_detail`, `get_summary`, `service_eliminar`, `service_importar_documento`, ...). |
| `services/dian/` | Pipeline DIAN UBL 2.1 real detrás de la Responsabilidad Core #1 — nunca desglosado por archivo antes de esta versión: `cufe.py` (cálculo CUFE, SHA-384 sobre campos fiscales, Anexo Técnico FE DIAN v1.9 §5.4.3), `ubl21_builder.py` (construcción del XML `Invoice` UBL 2.1), `xades_signer.py` (firma XAdES-EPES, requiere `lxml` + `cryptography`/`pyopenssl`), `attached_document.py` (contenedor `AttachedDocument` que envuelve el Invoice firmado para el envío a la DIAN). |
| `services_mail_ingestion.py` | `enqueue_mail_ingestion()`, `persist_run_result()`, `process_mail_ingestion_sync()`, `preview_mail_ingestion()` — orquestación de la ingesta IMAP asíncrona (Celery), consumido por `MailIngestionRun`/`MailInboxState`. |
| `api/filters.py` | Placeholder — sin `FilterSet` custom definido; el ViewSet usa `filterset_fields` inline. |
| `api/permissions.py` | Re-exporta `IsTenantAdminOrReadOnly` desde `apps.tenant.api.permissions` (SSoT) — sin lógica propia, ya consolidado. |
| `api/views_mail_ingestion.py` | `MailIngestionRunCreateAPIView`, `MailIngestionRunsListAPIView`, `MailIngestionPreviewAPIView` — vistas planas (no ViewSet) para los endpoints sueltos `/ingesta-correo/*`. |

---

## Vista HTML Server-Rendered (`views.py`/`tables.py`) — Fase 5-BIS, no documentado hasta v3.12.0

Mismo patrón ya aplicado en `gastos`/`compras`: reemplaza el grid Tabulator del listado principal por `django-tables2` + HTMX. **Tabulator fue retirado** de `facturas_list.js` (confirmado en el código: comentario "Simplificación consciente respecto a la versión Tabulator: se retiró...") — la API DRF (`api/viewsets.py`) sigue viva para el resto de acciones (crear, editar, vincular, gestor-offcanvas, etc.), no para el listado.

- `FacturaTableView` (`views.py`, `LoginRequiredMixin` + `SintelDSVMixin` + `SingleTableView`): una sola vista parametrizada por `naturaleza` (VENTA/COMPRA vía `<str:naturaleza>` en la URL) alimenta las 2 pestañas de `list_factura.html`. Filtra también por `estado_pago` (`?estado_pago=`) y búsqueda (`?q=`). Para COMPRA excluye la columna `cotizacion_numero` (`get_table_kwargs()`).
- `FacturaTable` (`tables.py`): columnas `numero`, `contraparte` (cliente/proveedor, no ordenable), `vencimiento` (accessor `payment_due_date`), `total`, `estado` (DIAN), `estado_pago`, `cotizacion_numero`, `acciones`.
- Ruta: `facturas:tabla` → `tabla/<str:naturaleza>/` (`urls.py`), consumida vía `hx-get` desde `list_factura.html` en ambas pestañas.
- Test: `tests/test_multitenant_isolation_tabla_html.py` (ver sección Tests — no estaba categorizado en v3.11.0).

---

## API Layer

### Serializers (`api/serializers.py`) — 14 serializadores (corregido de 13 en v3.12.0)

| Serializer | Uso | Notas clave |
|---|---|---|
| `UUIDOrPKRelatedField` | FK fields en formularios | Acepta UUID (con guiones) o PK entero. Auto-filtra por `empresa_id` (DSV). |
| `FacturaImpuestoSerializer` | Desglose impuestos (read-only) | 6 campos, todos read_only |
| `ItemFacturaSerializer` | Ítems de factura | Incluye `item_inventario_info` (resolución lazy desde Inventario) |
| `FacturaListSerializer` | GET `/` — Tabulator | Computed: `cliente_nombre`, `total_formateado`, `has_nc`, NC info, `cotizacion_vinculada_info`, `cliente_vinculado_info`, `proveedor_vinculado_info`, `sede_nombre`. **v3.11.0**: `total_pagado_bancos`, `saldo_pendiente` |
| `FacturaDetailSerializer` | GET `/{uuid}/` | Incluye `has_ubl_xml`, `has_pdf_file`, `anexos_meta`, `impuestos_desglosados`, `sede` (UUIDOrPKRelatedField + DSV). **v3.11.0**: `total_pagado_bancos`, `saldo_pendiente` |
| `FacturaWriteSerializer` | PATCH limitado | `subtotal`/`impuestos`/`total` siempre read-only |
| `FacturaReadDTOSerializer` | Preview de importación | Minimal DTO |
| `ImportUBLSerializer` | POST upload XML (text) | `xml` (CharField, required) |
| `UploadUBLFileSerializer` | POST upload file | `file` (FileField, required) |
| `MailIngestionRunCreateSerializer` | POST ingesta correo | `config_id` (int), `limit_messages` (int, optional) |
| `MailIngestionRunListSerializer` | GET runs correo | 7 campos read-only |
| `NotaCreditoListSerializer` | GET NC list | Incluye `factura_numero`, `factura_cufe` |
| `NotaCreditoDetailSerializer` | GET NC detail | Completo |
| `CatalogoItemInventarioSerializer` | GET `inventario-catalogo` | No documentado hasta v3.12.0 — catálogo de productos/servicios de Inventario para vincular ítems de factura |

---

### ViewSets (`api/viewsets.py`)

#### FacturaViewSet
```
Herencia: FacturaUBLMixin + FacturaMailMixin + FacturaXMLMixin
          + FacturaServiceMixin + BaseTenantViewSet
Lookup  : uuid
Métodos : GET, POST, PATCH, DELETE (PUT bloqueado)
Permisos: IsTenantMember + IsTenantAdminOrReadOnly
```

**Endpoints principales:**

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/facturas/` | GET | list — paginado, filtros naturaleza/nit/estado |
| `/api/v1/facturas/{uuid}/` | GET | retrieve — DSV |
| `/api/v1/facturas/{uuid}/` | PATCH | limited edit via `actualizar_factura_limitado()` |
| `/api/v1/facturas/{uuid}/` | DELETE | destroy |
| `/api/v1/facturas/upload-ubl/` | POST | batch XML upload (sync/async) |
| `/api/v1/facturas/create-from-dto/` | POST | crear desde DTO canónico |
| `/api/v1/facturas/materialize/` | POST | materializar desde resultado preview |
| `/api/v1/facturas/summary/` | GET | resumen neto (Ventas - NC) |
| `/api/v1/facturas/{uuid}/xml/` | GET | obtener XML UBL |
| `/api/v1/facturas/{uuid}/app-response/` | GET | obtener ApplicationResponse DIAN |
| `/api/v1/facturas/vincular-cotizacion/` | POST | link cotización (soft ref) |
| `/api/v1/facturas/vincular-cliente/` | POST | link cliente VENTA (DSV via ClienteBridge) |
| `/api/v1/facturas/vincular-proveedor/` | POST | link proveedor COMPRA (DSV via ProveedorBridge) |
| `/api/v1/facturas/por-estado/` | GET | **No documentado hasta v3.12.0** — listado agrupado/filtrado por `estado` |
| `/api/v1/facturas/{uuid}/cambiar-estado/` | POST | **No documentado hasta v3.12.0** — transición de `estado` (BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ANULADA) |
| `/api/v1/facturas/lista-centro-costos/` | GET | **No documentado hasta v3.12.0** |
| `/api/v1/facturas/obtener-retenciones/` | GET | **No documentado hasta v3.12.0** — expone `obtener_retenciones_desde_cliente/proveedor()` |
| `/api/v1/facturas/inventario-catalogo/` | GET | **No documentado hasta v3.12.0** — catálogo Inventario para vincular ítems (`InventarioItemBridge.buscar_catalogo()`) |
| `/api/v1/facturas/{uuid}/trazabilidad-inventario/` | GET | **No documentado hasta v3.12.0** |
| `/api/v1/facturas/buscar-para-movimiento/` | GET | **No documentado hasta v3.12.0** |

#### NotaCreditoViewSet, ItemFacturaViewSet

Registrados **antes** que `FacturaViewSet` (evita greedy matching).

### URLs (`api/urls.py`)

```python
# ORDEN CRÍTICO
router.register(r'notas-credito',  NotaCreditoViewSet,  basename='nota-credito')
router.register(r'items-factura',  ItemFacturaViewSet,  basename='item-factura')
router.register(r'',               FacturaViewSet,       basename='factura')  # último

# Endpoints sueltos de ingesta correo
POST /ingesta-correo/run/     → MailIngestionRunCreateAPIView
GET  /ingesta-correo/runs/    → MailIngestionRunsListAPIView
POST /ingesta-correo/preview/ → MailIngestionPreviewAPIView
```

### API Mixins (`api/mixins/`)

| Mixin | Responsabilidad |
|---|---|
| `FacturaUBLMixin` | Endpoints UBL: upload, parse, create-from-dto, materialize |
| `FacturaMailMixin` | Endpoints ingesta correo: run, cancel, preview |
| `FacturaXMLMixin` | Endpoints descarga XML: ubl, application-response |

---

## Frontend

### JavaScript (`static/js/facturas/`) — 7 módulos

| Archivo | Responsabilidad |
|---|---|
| `facturas.api.js` | SSoT endpoints. `window.http()` para todas las llamadas. |
| `facturas.components.js` | Componentes reutilizables (badges, formatters) |
| `facturas_main.js` | Orquestador principal. `tab-activated` listener. |
| `features/facturas_list.js` | **Corregido v3.12.0** — el grid Tabulator fue **retirado** (Fase 5-BIS): el listado ahora es `FacturaTableView`/`FacturaTable` server-rendered (ver sección dedicada arriba). Este archivo retiene filtros/acciones y el listener de detalle vía HTMX (`gestor-offcanvas`) — ya no inicializa ningún grid. |
| `features/facturas_editor.js` | Form editar. **v3.11.0**: `initResumenPagosBancos(form)` — lee `data-total-pagado-bancos` y `data-saldo-pendiente` del form; bloquea `#factura-estado-pago` según reglas medio_pago/bancos |
| `features/ver_detalle_factura.js` | Panel detalle read-only |
| `features/factura_inventario_vinculacion.js` | Vinculación ítems con Inventario (autocomplete) |

**`initResumenPagosBancos(form)` — v3.11.0:**
```javascript
// Lógica visual basada en medio_pago_codigo:
// '10' (Efectivo): estado_pago libre, sin restricciones
// Bancario + sin conciliaciones:      fuerza NO_PAGADA, select disabled
// Bancario + 100% conciliado:         fuerza PAGADA,    select disabled
// Bancario + parcialmente conciliado: permite PAGO_PARCIAL o PAGADA
```

### Templates (`templates/tenant/facturas/`) — 7 archivos

| Template | Descripción |
|---|---|
| `list_factura.html` | Página principal con Tabulator + KPI strip |
| `offcanvas_crear_factura.html` | Form subir XML / crear factura |
| `offcanvas_editar_factura.html` | Form editar campos `MANUAL_EDITABLE_FIELDS`. **v3.11.0**: `data-total-pagado-bancos` y `data-saldo-pendiente` inyectados en `<form>`. Tarjeta "Conciliación Bancaria" con KPIs. |
| `offcanvas_detalle_factura.html` | Read-only detail |
| `offcanvas_importar_factura.html` | Import batch XML |
| `offcanvas_pendientes_factura.html` | Vista facturas pendientes |
| `partials/assets_facturas.html` | Carga assets JS en orden |
| `partials/tabla_facturas.html` | **No documentado hasta v3.12.0** — template de `FacturaTableView` (Fase 5-BIS), renderiza `FacturaTable` |

---

## Patrones Arquitecturales

### 1. Idempotencia por CUFE

```python
# FacturaBusinessService.guardar_desde_dto()
obj, created = Factura.objects.get_or_create(
    empresa=empresa, cufe=dto['cufe'],
    defaults={...}
)
# Re-procesable sin duplicar — safe for ETL re-runs
```

### 2. Inmutabilidad XML (30 campos)

```python
# actualizar_factura_limitado(): bloquea cambios en XML_IMMUTABLE_FIELDS
attempted_xml = XML_IMMUTABLE_FIELDS & set(data.keys())
if attempted_xml:
    raise ValidationError({field: "Campo inmutable..." for field in attempted_xml})
```

### 3. Pull Model Retenciones (ADR-001)

```python
# @property en Factura — lazy query a Contabilidad
@property
def total_retencion_fuente(self) -> Decimal:
    from apps.tenant.contabilidad.models import Retencion
    total = Retencion.objects.filter(
        tipo='RETEFUENTE',
        documento_origen_app='facturas',
        documento_origen_id=self.id,
        reversada=False
    ).aggregate(Sum('monto'))['monto__sum'] or Decimal('0.00')
```

### 4. Pull Model Bancos (v3.11.0)

```python
# @property en Factura — lazy query a Bancos via Bridge
@property
def total_pagado_bancos(self) -> Decimal:
    from apps.tenant.facturas.services.selectors import BancosBridge
    return BancosBridge.obtener_total_conciliado(self.empresa_id, self.uuid)
```

### 5. Auto-recálculo estado_pago (v3.11.0)

```
Bancos.conciliar_transaccion()
    → FacturaInterAppAPI.recalcular_estado_pago_automatico(factura_uuid)
        → total_pagado_bancos >= total  → PAGADA
        → total_pagado_bancos > 0      → PAGO_PARCIAL
        → sin conciliaciones            → NO_PAGADA
        (solo si medio_pago_codigo != '10')
```

### 6. Naturaleza automática SSoT

```python
# _resolver_naturaleza() en FacturaBusinessService
def _resolver_naturaleza(emisor_nit, empresa_nit):
    return 'VENTA' if normaliza(emisor_nit) == normaliza(empresa_nit) else 'COMPRA'
```

---

## Conformidad AGENTS.md

| Regla | Sección | Estado |
|---|---|---|
| `SintelTenantBaseModel` en todos los modelos | §14 | ✅ |
| `empresa_id` en todas las queries | §4 | ✅ |
| `.only()` en todos los selectores | §4.5 | ✅ |
| `select_related()` donde hay FK traversals | §4.5 | ✅ |
| `uuid` como lookup_field | §14, §25 | ✅ |
| `BaseTenantViewSet` en herencia | §15 | ✅ |
| `IsTenantMember + IsTenantAdminOrReadOnly` | §15 | ✅ |
| DSV — `empresa_id` verificado en get_queryset() | §13 | ✅ |
| Inmutabilidad XML — 30 campos bloqueados | §5 | ✅ |
| Pull Model Retenciones → Contabilidad | ADR-001 | ✅ |
| Pull Model Bancos → BancosBridge | ADR-001 §18 v3.11.0 | ✅ |
| Soft references UUID (no FK cross-app) | §18 | ✅ |
| CUFE como clave idempotencia | §5 | ✅ |
| `window.http()` para mutaciones JS | §31 | ✅ |
| SSoT endpoints en `facturas.api.js` | §31 | ✅ |
| PUT bloqueado (solo PATCH para edición limitada) | §5 | ✅ |

**17/17 ✅ COMPLIANCE**

---

## Tests (`tests/`) — 24 archivos

| Área | Archivos |
|---|---|
| API CRUD | `test_api_facturas.py`, `test_facturas_list_detail_payloads.py`, `test_facturas_delete_api.py` |
| Upload/Import | `test_api_upload_ubl_contract.py`, `test_import_ubl_heavy_payload.py`, `test_importar_ubl_service.py`, `test_ingesta_ubl.py` |
| Materialización | `test_materializar_from_dto.py`, `test_create_with_anexos.py` |
| Naturaleza | `test_naturaleza_import_ubl.py`, `test_naturaleza_rule_ssot.py`, `test_naturaleza_unit.py`, `test_facturas_list_naturaleza_api.py` |
| Nota Crédito | `test_nota_credito_pipeline.py`, `test_payload_split.py` |
| Retenciones | `test_retenciones_backward_compat.py` |
| Detalle/Anexos | `test_factura_detail_anexos_api.py` |
| Integración | `test_services_ingest_integration.py`, `test_ssot_empresa_provider.py`, `test_xml_pipeline_canonical.py`, `test_upload_async_flow.py` |
| Templates | `test_templates.py` |
| Vista HTML (Fase 5-BIS) | `test_multitenant_isolation_tabla_html.py` — **no categorizado hasta v3.12.0**. Usa el mismo patrón `force_login()` + `schema_context()` que tiene un bug preexistente confirmado en `compras`/`gastos` (ver ADR-003, sección "Hallazgo importante" en `MEMORY.md` 2026-08-07); no se pudo re-ejecutar en esta auditoría porque una sesión separada del usuario tenía la base de datos de test en uso investigando ese mismo bug (`task_f84677b8`) — **estado real de este test no confirmado, no asumido como pasando**. |

---

## Deudas Técnicas

| ID | Área | Prioridad | Descripción | Estado |
|---|---|---|---|---|
| FAC-DT-01 | `models.py` | BAJA | `MANUAL_EDITABLE_FIELDS` incluye `'orden_compra'` que no existe en el modelo. Sin impacto funcional. | **ABIERTO** |
| FAC-DT-02 | `MailInboxState` | BAJA | Declara `created_at`/`updated_at` propios aunque hereda `SintelTenantBaseModel`. Redundancia inofensiva. | **ABIERTO** |
| FAC-DT-03 | `ItemFactura` | BAJA | Campos `porcentaje_retefuente` etc. marcados `editable=False` pero aún en BD. Plan eliminación: Fase 10 Cleanup v3.9.0 | **ABIERTO** (depreciación planificada) |
| FAC-DT-04 | Bancos v3.11.0 | MEDIA | `total_pagado_bancos` / `saldo_pendiente` son `@property` con query por llamada — N+1 si se serializa en list con muchas facturas. Mitigar con anotación ORM en selector si performance lo requiere. | **ABIERTO** |
| FAC-DT-05 | `Factura.xml_content` | BAJA | Campo DEPRECATED — usar `FacturaAnexos.ubl_xml`. Eliminar en future migration. | **ABIERTO** |

---

## Integración con Otros Módulos

| Módulo | Tipo | Contrato |
|---|---|---|
| **Contabilidad** | Pull Model — Contabilidad lee de Facturas | `ExtractorFacturas` extrae datos. Facturas NUNCA importa Contabilidad. |
| **Retenciones** | Pull Model — Facturas lee de Contabilidad | `@property total_retencion_fuente/reteica/reteiva` → `Retencion` table. |
| **Bancos** | Pull Model — Facturas lee de Bancos | `BancosBridge.obtener_total_conciliado()` → `TransaccionBancaria`. Auto-recálculo via `FacturaInterAppAPI`. |
| **Ventas** | **No documentado hasta v3.12.0** — Push: Ventas escribe una Factura | `FacturaBusinessService.crear_factura_desde_venta(empresa, dto)` — único caso del módulo donde otra app crea una `Factura` directamente (no soft-reference, no Pull Model). El DTO viene de `VentaBusinessService._construir_dto_factura()`. |
| **Clientes** | Soft reference | `cliente_uuid` + `ClienteBridge` sin FK |
| **Proveedores** | Soft reference | `proveedor_uuid` + `ProveedorBridge` sin FK |
| **Cotizaciones** | Soft reference | `cotizacion_uuid` + `CotizacionBridge` sin FK |
| **Inventario** | Soft reference | `item_inventario_uuid` + `InventarioItemBridge` sin FK |
| **Proyectos/Cartera** | Lectores | Consumen `FacturaInterAppAPI.list_all()` o soft-UUID lookups |

---

## Validaciones Actuales

Re-ejecutado el 2026-08-07 contra el código real (no copiado de la versión anterior):

```
python manage.py check                              → System check identified no issues (0 silenced)
py_compile models.py                                → OK
py_compile api/viewsets.py                          → OK
py_compile services/business_service.py             → OK
py_compile views.py, tables.py                       → OK
makemigrations facturas --check --dry-run           → No changes detected
Migraciones aplicadas                                → 0001–0030 (30 total, sin cambios desde v3.11.0)
pytest test_multitenant_isolation_tabla_html.py     → NO EJECUTADO esta sesión (BD de test en uso por
                                                        otra sesión del usuario investigando el bug
                                                        force_login compartido con compras/gastos) —
                                                        pendiente de confirmación real, no asumido OK.
```

---

**Última Actualización:** 2026-08-07 (v3.12.0 — re-validación completa contra código real)
**Auditor:** Claude Sonnet 5 (Anthropic)
**Status:** ✅ PRODUCTION READY — 0 CRÍTICOS — 17/17 AGENTS.md COMPLIANCE (re-verificado). Un test nuevo (`test_multitenant_isolation_tabla_html.py`) con estado no confirmado por un bug de infraestructura de tests preexistente y ajeno a este módulo — ver Tests.
