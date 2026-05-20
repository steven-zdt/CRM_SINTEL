# Auditoría Flujo Completo — Módulo Cotizaciones

**Versión auditada:** v3.7.5  
**Fecha:** 2026-05-19  
**Estado:** ✅ OPERATIVO (0 CRÍTICOS)  
**Auditor:** Claude Code (claude-sonnet-4-6)  
**Ubicación:** `apps/tenant/cotizaciones/`

---

## 1. Responsabilidades del Módulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **DNA Dinámico** — herencia de configuración (prefijo, sufijo, días validez) desde `ConfiguracionCotizacion` | ✅ |
| 2 | **Snapshot Pattern** — items persisten precio y utilidad en el momento del registro (independiente del catálogo) | ✅ |
| 3 | **Cálculo Centralizado** — motor SSoT en `CotizacionService.calcular_totales()` para AIU, IVA y subtotales | ✅ |
| 4 | **Generación Documental** — pipeline PDF via `xhtml2pdf` en `CotizacionPDFExportService` | ✅ |
| 5 | **Numeración Atómica** — folios únicos por perfil con `select_for_update()` en `generar_codigo_unico()` | ✅ |
| 6 | **UUID Lookup** — `BaseTenantViewSet.lookup_field = 'uuid'` en todos los ViewSets | ✅ (mig 0004) |

---

## 2. Modelos

### 2.1 `Cotizacion`
**Tabla:** `tenant_cotizaciones_documento`  
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `numero_cotizacion` | CharField(50) | Número secuencial desde configuración |
| `codigo_unico` | CharField(100) | `unique=True, db_index=True` — formato `{prefijo}{n:04d}{sufijo}` |
| `cliente` | FK → `tenant_clientes.Cliente` | `SET_NULL, null=True` |
| `configuracion` | FK → `ConfiguracionCotizacion` | `SET_NULL, null=True, related_name='cotizaciones'` |
| `tipo_cotizacion` | CharField(20) | default `'MIXTO'` |
| `fecha_emision` | DateField | `auto_now_add=True` |
| `fecha_vencimiento` | DateField | calculado desde `dias_validez` de la configuración |
| `estado` | CharField | Choices: `BORRADOR / ENVIADA / ACEPTADA / CANCELADA` |
| `porcentaje_aiu_admin` | DecimalField(5,2) | DNA Financiero |
| `porcentaje_aiu_imprevistos` | DecimalField(5,2) | DNA Financiero |
| `porcentaje_aiu_utilidad` | DecimalField(5,2) | DNA Financiero |
| `iva_porcentaje` | DecimalField(5,2) | default `19.00` |
| `total_con_impuestos` | DecimalField(15,2) | calculado por `calcular_totales()` |
| `dias_totales` | PositiveIntegerField | default `1` |
| `dias_infraestructura` | PositiveIntegerField | distribución heurística |
| `dias_instalacion` | PositiveIntegerField | |
| `dias_configuracion` | PositiveIntegerField | |
| `dias_pruebas` | PositiveIntegerField | |

**Constraint:** `unique_numero_cotizacion_por_perfil` → `(empresa, configuracion, numero_cotizacion)`

---

### 2.2 `CotizacionItem`
**Tabla:** `tenant_cotizaciones_item`  
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `cotizacion` | FK → `Cotizacion` | `CASCADE, related_name='items'` |
| `tipo_item` | CharField(20) | Choices: `PRODUCTO / MATERIAL / SERVICIO` |
| `producto` | FK → `Producto` | `SET_NULL, null=True` (snapshot independiente) |
| `servicio` | FK → `Servicio` | `SET_NULL, null=True` |
| `descripcion` | TextField | snapshot del nombre en el momento del registro |
| `marca` | CharField(100) | |
| `referencia` | CharField(100) | |
| `unidad` | CharField(20) | default `'UND'` |
| `cantidad` | DecimalField(12,2) | |
| `costo_unitario` | DecimalField(15,2) | snapshot de costo en el momento del registro |
| `porcentaje_utilidad` | DecimalField(5,2) | |
| `precio_unitario_venta` | DecimalField(15,2) | calculado: `costo * (1 + utilidad/100)` |
| `subtotal_linea` | DecimalField(15,2) | calculado: `precio_venta * cantidad` |
| `orden` | PositiveIntegerField | default `0`, ordering `['orden']` |

---

### 2.3 `Producto`
**Tabla:** `tenant_cotizaciones_producto`  
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `codigo` | CharField(50) | blank=True |
| `nombre` | CharField(255) | |
| `marca` | CharField(100) | blank=True |
| `referencia` | CharField(100) | blank=True |
| `unidad` | CharField(20) | default `'UND'` |
| `precio_venta` | DecimalField(15,2) | precio de referencia (catálogo) |
| `activo` | BooleanField | default `True` |

---

### 2.4 `Servicio`
**Tabla:** `tenant_cotizaciones_servicio`  
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `nombre` | CharField(255) | |
| `precio_venta` | DecimalField(15,2) | |
| `activo` | BooleanField | default `True` |

---

### 2.5 `ConfiguracionCotizacion`
**Tabla:** `tenant_cotizaciones_configuracion`  
**App label:** `tenant_cotizaciones`  
**Herencia:** `SintelTenantBaseModel` ✅

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ |
| `nombre_configuracion` | CharField(100) | |
| `es_activo` | BooleanField | default `True` |
| `dias_validez` | IntegerField | default `15`, rango `[1, 30]` |
| `prefijo_secuencia` | CharField(20) | blank, default `''` |
| `sufijo_secuencia` | CharField(20) | blank, default `''` |
| `semilla_inicial` | IntegerField | default `1` |
| `ultimo_numero` | IntegerField | default `0`, se incrementa con `select_for_update()` |

---

### 2.6 Migraciones

| # | Archivo | Descripción |
|---|---------|-------------|
| 0001 | `0001_initial.py` | Creación inicial de todos los modelos |
| 0002 | `0002_configuracioncotizacion_created_at_and_more.py` | Campos de auditoría en ConfiguracionCotizacion |
| 0003 | `0003_cotizacion_dias_configuracion_and_more.py` | Campos de tiempos del proyecto (dias_*) |
| 0004 | `0004_add_uuid_fields.py` | **UUID fields** para Producto, Servicio, CotizacionItem, ConfiguracionCotizacion — 3-phase safe migration con `gen_random_uuid()` |

---

## 3. Service Layer (FSD)

### 3.1 `services/selectors.py` — Lectura Zero-Waste

**Clase:** `CotizacionSelector`

| Método | Descripción |
|--------|-------------|
| `get_list(empresa_id, search, estado, cliente)` | Lista paginada con `.only(LIST_FIELDS)` + `select_related('cliente')` |
| `get_detail(_cotizacion_id, empresa_id)` | Base queryset por empresa — DRF aplica filtro uuid en `get_object()` |
| `get_detail_by_uuid(uuid, empresa_id)` | Detalle directo por uuid + empresa |
| `get_clientes_activos(empresa_id)` | Para poblar selects en formularios |
| `get_configuraciones_activas(empresa_id)` | Para poblar selects en formularios |
| `get_configuracion_by_id(config_id, empresa_id)` | Detalle de configuración para crear preforma |
| `get_configuraciones_lista_completa(empresa_id)` | Sin filtro de activo para listado admin |

**Constantes:**
- `LIST_FIELDS` — 10 campos optimizados para tabla
- `DETAIL_FIELDS` — 25 campos para vista completa (incluye `cliente_id`, `configuracion_id`)

---

### 3.2 `services/crud_service.py` — Escritura Atómica

**Clase:** `CotizacionCRUDService`

| Método | Descripción |
|--------|-------------|
| `create_cotizacion(empresa, cliente, configuracion, ...)` | `@transaction.atomic` — crea registro maestro |
| `update_cotizacion(instance, **update_data)` | `@transaction.atomic` — actualiza campos permitidos |
| `delete_items_for_cotizacion(cotizacion_id)` | Elimina todos los items de una cotización |
| `get_cotizacion_for_totals(cotizacion_id)` | Lectura de campos financieros para recálculo |
| `get_items_subtotal(cotizacion_id)` | `SUM(subtotal_linea)` para cálculo de totales |

---

### 3.3 `services/business_service.py` — Reglas de Negocio

**Clase:** `CotizacionService`  
**Constantes:** `MONEY_Q = Decimal("0.01")`, `HUNDRED = Decimal("100")`

| Método | Descripción |
|--------|-------------|
| `_to_decimal(value, field_name, default)` | Conversión segura con ValueError explícito |
| `_q(value)` | Cuantización `ROUND_HALF_UP` a 2 decimales |
| `get_configuracion_for_empresa(input, empresa_id)` | DSV: valida que configuración pertenece al tenant |
| `get_cliente_for_empresa(input, empresa_id)` | DSV: valida que cliente pertenece al tenant |
| `_build_header_fields(configuracion, datos)` | Construye campos cabecera con defaults desde configuración |
| `_sync_items(cotizacion, items_data)` | `@transaction.atomic` — sync maestro-detalle por UUID→ID→new |
| `crear_preforma(empresa, datos)` | `@transaction.atomic` — crea cotización + items + PDF |
| `generar_codigo_unico(perfil_id, empresa_id)` | `select_for_update()` + incremento atómico de `ultimo_numero` |
| `calcular_totales(cotizacion_id)` | Recalcula `total_con_impuestos` desde items + AIU + IVA |
| `actualizar_cotizacion(instance, datos)` | `@transaction.atomic` — actualiza cabecera + sync items + PDF |

**Flujo `_sync_items`:**
```
1. Mapear items existentes: {uuid → item} + {id → item}
2. Para cada item en payload:
   a. uuid match → update
   b. id match → update
   c. sin match → create
3. Eliminar remanentes (los que no llegaron en payload)
```

**Función helper:** `_generar_pdf_sincronizado(cotizacion, empresa)` — genera PDF post-save (no-fatal: loggea errores sin romper transacción).

---

### 3.4 `services/api_mixins.py` — Inyección en ViewSet

**Clase:** `CotizacionServiceMixin`

| Método | Descripción |
|--------|-------------|
| `get_qs_list()` | Delega a `CotizacionSelector.get_list()` con params del request |
| `get_qs_detail()` | Retorna queryset base filtrado por empresa (DRF aplica uuid) |
| `service_crear_cotizacion(serializer)` | Resuelve `Empresa` y llama `crear_preforma()` |
| `service_actualizar_cotizacion(instance, serializer)` | Delega a `actualizar_cotizacion()` con `validated_data` |

---

### 3.5 `services/item_service.py`

| Clase | Métodos Clave |
|-------|---------------|
| `CotizacionItemSelector` | `get_list(empresa_id, cotizacion_id)`, `get_detail(empresa_id, item_uuid)` |
| `CotizacionItemCRUDService` | `create_item(cotizacion, data)`, `update_item(instance, data)`, `delete_item(instance)` |
| `CotizacionItemBusinessService` | `registrar(empresa_id, data, instance=None)` — calcula `precio_unitario_venta` y `subtotal_linea` antes de persistir; `eliminar_item(item)` |
| `CotizacionItemServiceMixin` | `get_qs_list()`, `service_crear_item()`, `service_actualizar_item()` |

---

### 3.6 `services/producto_service.py` y `servicio_service.py`

| Clase | Responsabilidad |
|-------|----------------|
| `ProductoSelector` | `get_list(empresa_id, search)`, `get_detail(empresa_id, uuid)` |
| `ProductoCRUDService` | `create()`, `update()` — `@transaction.atomic` |
| `ProductoBusinessService` | `crear_producto(data, empresa_id)`, `actualizar_producto(instance, data)` |
| `ProductoServiceMixin` | Inyecta en `ProductoViewSet` |
| `ServicioSelector` | Análogo a Producto |
| `ServicioCRUDService` | Análogo a Producto |
| `ServicioBusinessService` | Análogo a Producto |
| `ServicioServiceMixin` | Inyecta en `ServicioViewSet` |

---

### 3.7 `services/pdf_export_service.py`

**Clase:** `CotizacionPDFExportService`

| Método | Descripción |
|--------|-------------|
| `generar_pdf_publico(cotizacion, empresa, request)` | Entry point — prepara contexto y llama al generador |
| `preparar_contexto(cotizacion, empresa)` | Construye dict con datos para el template PDF |

**Template:** `templates/tenant/cotizaciones/pdf/formato_profesional.html`  
**Motor:** `xhtml2pdf`

---

### 3.8 `configuracion/services/`

| Clase | Métodos |
|-------|---------|
| `ConfiguracionSelector` | `get_list(empresa_id)`, `get_detail(config_uuid, empresa_id)` |
| `ConfiguracionCRUDService` | `create_configuracion(empresa, data)`, `update_configuracion(instance, data)`, `delete_configuracion(instance)` |
| `ConfiguracionBusinessService` | `crear_configuracion(data, empresa)`, `actualizar_configuracion(instance, data)` |
| `ConfiguracionServiceMixin` | `get_qs_list()`, `get_qs_detail()`, `service_crear_configuracion()`, `service_actualizar_configuracion()` |

---

## 4. API Layer

### 4.1 ViewSets

| ViewSet | Herencia | lookup_field | Acciones |
|---------|----------|-------------|----------|
| `CotizacionViewSet` | `SintelDSVMixin, CotizacionServiceMixin, BaseTenantViewSet` | `uuid` | CRUD + `exportar_pdf`, `render_offcanvas_crear`, `render_offcanvas_editar`, `render_offcanvas_detalle`, `recalcular` |
| `CotizacionItemViewSet` | `SintelDSVMixin, CotizacionItemServiceMixin, BaseTenantViewSet` | `uuid` (heredado) | CRUD |
| `ProductoViewSet` | `SintelDSVMixin, ProductoServiceMixin, BaseTenantViewSet` | `uuid` (heredado) | CRUD |
| `ServicioViewSet` | `SintelDSVMixin, ServicioServiceMixin, BaseTenantViewSet` | `uuid` (heredado) | CRUD |
| `ConfiguracionCotizacionViewSet` | `SintelDSVMixin, ConfiguracionServiceMixin, BaseTenantViewSet` | `uuid` (heredado) | CRUD + acciones offcanvas |

---

### 4.2 Serializers (`api/serializers.py`)

| Serializer | Modelo | Notas |
|------------|--------|-------|
| `ProductoSerializer` | `Producto` | `uuid` read-only, `created_at` read-only |
| `ServicioSerializer` | `Servicio` | `uuid` read-only, `created_at` read-only |
| `CotizacionItemNestedSerializer` | `CotizacionItem` | `id` **writable** (IntegerField, optional) para matching en `_sync_items`; `uuid/precio_unitario_venta/subtotal_linea` read-only |
| `CotizacionItemSerializer` | `CotizacionItem` | Standalone para CRUD directo |
| `CotizacionListSerializer` | `Cotizacion` | Todos los campos `read_only_fields = fields` |
| `CotizacionSerializer` | `Cotizacion` | `cliente`/`configuracion` PrimaryKeyRelatedField; queryset resuelto via `resolve_tenant_empresa()` en `__init__` |

**Fix crítico (v3.7.5):**
- `CotizacionSerializer.__init__` usa `resolve_tenant_empresa(request)` para resolver `empresa_id` — evita querysets `.none()` que causaban 400 en PATCH.
- `CotizacionItemNestedSerializer.id = IntegerField(required=False)` — permite matching de items existentes en `_sync_items`.

---

### 4.3 Endpoints REST

| Método | URL | ViewSet | Descripción |
|--------|-----|---------|-------------|
| GET | `/api/v1/cotizaciones/` | `CotizacionViewSet.list` | Lista paginada |
| POST | `/api/v1/cotizaciones/` | `CotizacionViewSet.create` | Crear cotización + items + PDF |
| GET | `/api/v1/cotizaciones/{uuid}/` | `CotizacionViewSet.retrieve` | Detalle completo |
| PUT/PATCH | `/api/v1/cotizaciones/{uuid}/` | `CotizacionViewSet.update` | Actualizar + sync items + PDF |
| DELETE | `/api/v1/cotizaciones/{uuid}/` | `CotizacionViewSet.destroy` | Eliminar |
| GET | `/api/v1/cotizaciones/{uuid}/exportar-pdf/` | `.exportar_pdf` | Descargar PDF |
| GET | `/api/v1/cotizaciones/render-offcanvas/crear/` | `.render_offcanvas_crear` | HTML Shell creación |
| GET | `/api/v1/cotizaciones/{uuid}/render-offcanvas/editar/` | `.render_offcanvas_editar` | HTML Shell edición |
| GET | `/api/v1/cotizaciones/{uuid}/render-offcanvas/detalle/` | `.render_offcanvas_detalle` | HTML Shell detalle |
| POST | `/api/v1/cotizaciones/{uuid}/recalcular/` | `.recalcular` | Recálculo forzado de totales |
| GET/POST | `/api/v1/cotizaciones/items/` | `CotizacionItemViewSet` | CRUD items |
| GET/POST | `/api/v1/cotizaciones/productos/` | `ProductoViewSet` | CRUD catálogo productos |
| GET/POST | `/api/v1/cotizaciones/servicios/` | `ServicioViewSet` | CRUD catálogo servicios |
| GET/POST | `/api/v1/cotizaciones/configuracion/` | `ConfiguracionCotizacionViewSet` | CRUD perfiles |

### 4.4 URLs UI (vistas HTML)

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/cotizaciones/editor/<uuid:uuid>/` | `CotizacionEditorTemplateView` | Editor completo (editar existente) |
| `/cotizaciones/editor/draft/` | `CotizacionEditorDraftView` | Editor borrador (crear nuevo) |
| `/cotizaciones/partials/configuracion/lista/` | `ConfiguracionListOffcanvasView` | Lista de plantillas |
| `/cotizaciones/partials/configuracion/crear/` | `ConfiguracionCrearOffcanvasView` | Offcanvas crear plantilla |
| `/cotizaciones/partials/configuracion/editar/<id>/` | `ConfiguracionEditarOffcanvasView` | Offcanvas editar plantilla |
| `/cotizaciones/partials/configuracion/ver/<id>/` | `ConfiguracionVerOffcanvasView` | Offcanvas ver plantilla |
| `/cotizaciones/partials/ver/<uuid:uuid>/` | `CotizacionDetalleOffcanvasView` | Offcanvas detalle cotización |

---

## 5. Frontend

### 5.1 JavaScript — Módulos (`static/cotizaciones/js/`)

| Archivo | Namespace | Responsabilidad |
|---------|-----------|----------------|
| `cotizaciones.api.js` | `w.Sintel.Cotizaciones.api` | SSoT de URLs de API: `createUrl`, `updateUrl(uuid)`, `detailUrl(uuid)`, `exportarPdfUrl(uuid)`, `getHeaders()` |
| `cotizaciones.main.js` | `w.Sintel.Cotizaciones` | Orquestador de inicialización de módulos |
| `cotizaciones.module.js` | — | Bootstrapper del namespace global |
| `cotizaciones.utils.js` | `w.Sintel.Cotizaciones.utils` | `fmtMoney()`, `parseFloatSafe()` |
| `cotizaciones.ui.js` | `w.Sintel.Cotizaciones.ui` | Gestión offcanvas, modales, notificaciones |
| `cotizaciones.table.js` | `w.Sintel.Cotizaciones.table` | Integración Tabulator: columnas, opciones, refresh |
| `cotizaciones.editor.js` | — | Entry point del editor completo |
| `cotizaciones.list.js` | — | Entry point del listado |
| `cotizaciones.detalle.js` | — | Entry point de detalle |

### 5.2 JavaScript — Features (`features/`)

| Archivo | Responsabilidad |
|---------|----------------|
| `cotizacion_editor.js` | Editor maestro-detalle completo: `init(uuid)`, `addRow(tipo, data)`, `calculateRow(row)`, `calculateTotals()`, `calculateSchedule()`, `save()`, `syncIds(items)`, `handlePaste(e)` |
| `cotizacion_list.js` | Tabla Tabulator de cotizaciones |
| `configuracion_editor.js` | CRUD de perfiles de configuración |
| `configuracion_list.js` | Tabla de perfiles |
| `item_editor.js` | Editor de ítem individual |
| `producto_editor.js` | CRUD de productos del catálogo |
| `producto_list.js` | Tabla de productos |
| `servicio_editor.js` | CRUD de servicios del catálogo |
| `servicio_list.js` | Tabla de servicios |

**Flujo de guardado (`cotizacion_editor.js save()`):**
```
1. Construir payload: {cliente(int), configuracion(int), items[], campos financieros}
2. Validar: cliente && configuracion → si faltan, notifyError y abort
3. PATCH {uuid} si existe, POST si es nuevo
4. On success: syncIds(data.items), notifySuccess, actualizar URL, activar btn PDF
```

---

### 5.3 Templates HTML (`templates/tenant/cotizaciones/`)

| Template | Líneas | Propósito |
|----------|--------|-----------|
| `editor_cotizacion.html` | 437 | Editor principal: tabla maestro-detalle, DNA financiero, tiempos del proyecto |
| `offcanvas_detalle_cotizacion.html` | 242 | Vista de solo lectura en offcanvas |
| `list_full.html` | 82 | Listado con Tabulator + filtros |
| `list.html` | 50 | Listado básico |
| `list_cotizaciones.html` | 12 | Página raíz del módulo |
| `offcanvas_crear_cotizacion.html` | 40 | Form creación rápida |
| `offcanvas_editar_cotizacion.html` | 41 | Form edición rápida |
| `offcanvas_crear_producto.html` | 28 | Form producto |
| `offcanvas_crear_servicio.html` | 24 | Form servicio |
| `offcanvas_list_plantillas.html` | 21 | Lista de configuraciones |
| `offcanvas_plantilla_crear.html` | 41 | Form crear configuración |
| `offcanvas_plantilla_editar.html` | 41 | Form editar configuración |
| `offcanvas_plantilla_detalle.html` | 33 | Vista detalle configuración |
| `assets_cotizaciones.html` | 29 | Include de CSS/JS del módulo |
| `pdf/formato_profesional.html` | — | Template para generación PDF |

---

## 6. Checklist AGENTS.md — Estado de Cumplimiento

| Regla | Estado | Detalle |
|-------|--------|---------|
| `SintelTenantBaseModel` | ✅ | Todos los 5 modelos |
| `empresa_id` en queries | ✅ | Todos los selectors filtran por `empresa_id` |
| `.only()` en querysets | ✅ | `LIST_FIELDS` y `DETAIL_FIELDS` definidos en selectors |
| `lookup_field = 'uuid'` | ✅ | Todos los ViewSets (heredado de `BaseTenantViewSet`) |
| UUID en modelos | ✅ | Migración 0004 aplicada |
| No signals para negocio | ✅ | Service Layer exclusivo |
| `@transaction.atomic` en CRUD | ✅ | `crear_preforma`, `actualizar_cotizacion`, `_sync_items` |
| `BaseTenantViewSet` sin override auth | ✅ | Ningún ViewSet sobreescribe `authentication_classes` |
| FK a `perfil.TenantProfile` | ✅ | No hay FKs incorrectas |
| No imports de `apps.public.*` | ✅ | Solo importa de tenant apps |
| Permisos de `apps.tenant.api.permissions` | ✅ | `IsTenantMember`, `IsTenantAdminOrReadOnly` |
| Imports globales (no dentro de `def`) | ⚠️ | `business_service.py` usa imports locales en algunos métodos — no crítico pero revisar |
| `resolve_tenant_empresa` en serializer | ✅ | Fix v3.7.5 aplicado |

---

## 7. Fixes Aplicados en v3.7.5 (2026-05-19)

### F1: PATCH `/api/v1/cotizaciones/{uuid}/` → 400 Bad Request

**Causa:** `CotizacionSerializer.__init__` intentaba `request.empresa` y `request.tenant.empresa_id` — ninguno existe en el objeto request de django-tenants. `empresa_id` quedaba `None`, querysets de `cliente` y `configuracion` permanecían `.none()`. Cualquier valor enviado fallaba con _"Invalid pk - object does not exist"_.

**Fix:** Reemplazado con `resolve_tenant_empresa(request)` que hace fallback a `Empresa.objects.first()` dentro del schema del tenant activo.

```python
# ANTES (roto)
if hasattr(request, 'empresa') and request.empresa:
    empresa_id = request.empresa.id
elif hasattr(request, 'tenant'):
    empresa_id = getattr(request.tenant, 'empresa_id', None)

# DESPUÉS (correcto)
empresa = resolve_tenant_empresa(request)
if not empresa:
    return
self.fields['cliente'].queryset = Cliente.objects.filter(empresa_id=empresa.id, activo=True)
self.fields['configuracion'].queryset = ConfiguracionCotizacion.objects.filter(empresa_id=empresa.id)
```

---

### F2: Duplicado de items al guardar múltiples veces

**Causa:** `CotizacionItemNestedSerializer` no declaraba `id` explícitamente → DRF auto-genera el campo `id` como `read_only=True` (es la PK AutoField). El frontend enviaba `items[n].id = 5` pero el `id` era descartado de `validated_data`. `_sync_items` nunca encontraba el item existente → siempre creaba nuevos.

**Fix:** Declaración explícita de campo writable:

```python
class CotizacionItemNestedSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)  # writable para matching
```

---

### F3: UUID fields en modelos (migración 0004)

**Causa:** `Producto`, `Servicio`, `CotizacionItem`, `ConfiguracionCotizacion` no tenían `uuid` field → `lookup_field='uuid'` en ViewSets causaba errores en detalle/actualización.

**Fix:** Migración 0004 — 3-phase safe migration:
1. `AddField(nullable)` para todos los modelos
2. `RunPython` → `gen_random_uuid()` para registros existentes
3. `AlterField(unique=True, db_index=True)` para establecer constraint

---

## 8. Deuda Técnica

| ID | Archivo | Severidad | Descripción |
|----|---------|-----------|-------------|
| DEUDA-01 | `api/serializers_new.py` | MEDIA | Archivo alternativo de serializers — verificar si está en uso; si no, eliminar |
| DEUDA-02 | `api/pdf_viewsets.py` | MEDIA | ViewSet PDF separado — validar si duplica lógica de `exportar_pdf` action en `CotizacionViewSet` |
| DEUDA-03 | `api/pagination.py` | BAJA | `CotizacionesResultsSetPagination` — verificar si se usa o si hereda del paginador global `StandardResultsSetPagination` |
| DEUDA-04 | `facturas_prueba/` | BAJA | Directorio con archivos XML/PDF de prueba en código de producción — mover a fixtures o eliminar |
| DEUDA-05 | `list.html` + `list_cotizaciones.html` | BAJA | Dos templates de listado posiblemente redundantes — verificar cuál está activo |
| DEUDA-06 | `business_service.py` imports locales | BAJA | Algunos `import` dentro de métodos (e.g., `from .item_service import ...` dentro de `_sync_items`) — consolidar a nivel de archivo |
| DEUDA-07 | `ui_views.py` params de URL | BAJA | `ConfiguracionEditarOffcanvasView` y `ConfiguracionVerOffcanvasView` usan `<int:id>` — debería ser `<uuid:uuid>` para consistencia con `lookup_field` |

---

## 9. Estadísticas del Módulo

| Categoría | Archivos | Clases |
|-----------|---------|--------|
| Modelos | 2 | 5 |
| Servicios (business + crud + selectors + mixins) | 10 | 16+ |
| ViewSets | 5 | 5 |
| Serializers | 2 | 6 |
| Admin | 1 | 5 |
| UI Views | 1 | 8 |
| JS Core | 9 | — |
| JS Features | 9 | — |
| Templates HTML | 15 | — |
| Migraciones | 4 | — |

---

## 10. Flujo Completo: Crear/Editar Cotización

```
[Frontend editor_cotizacion.html]
  ↓ usuario modifica items y hace clic en "Guardar"
[cotizacion_editor.js save()]
  → build payload: {cliente, configuracion, items[], iva, aiu, dias}
  → POST /api/v1/cotizaciones/ (nuevo) | PATCH /api/v1/cotizaciones/{uuid}/ (editar)
    ↓
[CotizacionViewSet.create() / .update()]
  → CotizacionSerializer.is_valid()
     [__init__]: resolve_tenant_empresa() → cliente/configuracion querysets correctos
     [items]: CotizacionItemNestedSerializer, id writable → id llega en validated_data
  → service_crear_cotizacion(serializer) | service_actualizar_cotizacion(instance, serializer)
    ↓
[CotizacionService.crear_preforma() / .actualizar_cotizacion()]
  → DSV: get_configuracion_for_empresa() | get_cliente_for_empresa()
  → _build_header_fields() → fecha_vencimiento, tipo_cotizacion, etc.
  → CotizacionCRUDService.create/update_cotizacion() [@transaction.atomic]
  → _sync_items(cotizacion, items_data)
     → match por uuid → match por id → create nuevo
     → delete remanentes
  → calcular_totales() → subtotal + AIU + IVA → total_con_impuestos
  → _generar_pdf_sincronizado() → xhtml2pdf
    ↓
[Response 200/201]
  → cotizacion.uuid, items[].id
    ↓
[cotizacion_editor.js]
  → syncIds(data.items) → row.dataset.id = item.id
  → notifySuccess, activar btn PDF, replaceState URL
```
