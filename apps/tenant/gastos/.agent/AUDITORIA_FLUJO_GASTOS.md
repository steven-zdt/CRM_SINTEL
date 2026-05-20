# Auditoría Flujo Completo — Módulo Gastos

**Versión auditada:** v3.7.5  
**Fecha:** 2026-05-19  
**Estado:** ✅ OPERATIVO (0 CRÍTICOS)  
**Auditor:** Claude Code (claude-sonnet-4-6)  
**Ubicación:** `apps/tenant/gastos/`

---

## 1. Responsabilidades del Módulo

| # | Responsabilidad | Estado |
|---|----------------|--------|
| 1 | **Documento Soporte (DS)** — Evidencia legal inmutable para proveedores no obligados a facturar (Decreto 1625/2016 DIAN) | ✅ |
| 2 | **Resolución DIAN** — Gestión de numeración oficial: consecutivos, prefijos, rangos, vigencia | ✅ |
| 3 | **Desacoplamiento Operativo** — `DocumentoSoporte` (legal) separado de clasificación administrativa (`categoria_contable`) | ✅ |
| 4 | **Selectores de Retenciones** — Usuario elige tipo Retefuente/ReteICA desde dropdown; cálculo en tiempo real en el formulario | ✅ (v3.7.3) |
| 5 | **Pull Model Retenciones** — `@property` lee desde `Contabilidad.Retencion`; `DocumentoSoporte` no almacena retenciones | ✅ (v3.7.1) |
| 6 | **Ciclo de Vida Controlado** — `activo → anulado` con trazabilidad: `fecha_anulacion`, `motivo_anulacion`, `usuario_anulacion` | ✅ |
| 7 | **UUID Lookup** — `lookup_field = 'uuid'` en todos los ViewSets | ✅ (mig 0016) |
| 8 | **Vinculación Contable** — `cuenta_gasto_uuid` mapea a `CuentaContable` via Pull Model de Contabilidad | ✅ (mig 0013) |
| 9 | **Precargar Editar Gasto** — Valores de retenciones y base gravable se precargan desde BD al abrir edición | ✅ (v3.7.5) |

---

## 2. Modelos

### 2.1 `ResolucionDIAN`
**Herencia:** `SintelTenantBaseModel` ✅  
**Ordering:** `['-vigente', '-fecha_resolucion']`

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ (mig 0016) |
| `numero_resolucion` | CharField(50) | `db_index=True` |
| `prefijo` | CharField(10) | p.ej. `"DS"`, `"GS"` |
| `rango_desde` | IntegerField | `MinValueValidator(1)` |
| `rango_hasta` | IntegerField | `MinValueValidator(1)` |
| `fecha_resolucion` | DateField | fecha de emisión DIAN |
| `fecha_inicio` | DateField | default `datetime.date.today` |
| `fecha_fin` | DateField | vencimiento de la resolución |
| `clave_tecnica` | CharField(100) | nullable |
| `vigente` | BooleanField | `db_index=True` — solo una vigente por empresa |
| `consecutivo` | IntegerField | `db_index=True, editable=False` — próximo consecutivo a asignar |

**Índices BD:** `(empresa, vigente)`  
**Ordering:** `['-vigente', '-fecha_resolucion']`

**Métodos:**
```python
formar_consecutivo(numero) → f"{prefijo} {numero}"
esta_dentro_de_fecha(fecha_referencia=None) → bool  # valida rango de fechas
save() → full_clean() + super().save()
```

---

### 2.2 `DocumentoSoporte`
**Herencia:** `SintelTenantBaseModel` ✅  
**Ordering:** `['-fecha', '-consecutivo']`

#### Choices SSoT (definidos en este modelo — críticos para sincronía con templates)

```python
RETEFUENTE_CHOICES = [
    ('0.00', '0% - Sin Retefuente'),
    ('0', '0% - Sin Retefuente'),
    ('0.0', '0% - Sin Retefuente'),
    ('0.04', '4% - Servicios (Declarantes)'),
    ('0.06', '6% - Servicios (No Declarantes)'),
    ('0.10', '10% - Honorarios y Consultoria (No declarante)'),
    ('0.11', '11% - Honorarios y Consultoria (Declarante)'),
]

RETEICA_CHOICES = [
    ('0.00', '0% - Exento'),
    ('0', '0% - Exento'),
    ('0.0', '0% - Exento'),
    ('0.0069', '0.69%'),
    ('0.00966', '0.966%'),
    ('0.01104', '1.104%'),
]
```

**Regla CRÍTICA:** Si se modifican estos choices en `models.py`, los `<option>` de los templates `offcanvas_crear_gasto.html` y `offcanvas_editar_gasto.html` DEBEN sincronizarse manualmente (ver CLAUDE.md § Selectores de Retenciones v3.7.3).

#### Campos

| Campo | Tipo | Notas |
|-------|------|-------|
| `uuid` | UUIDField | `unique=True, db_index=True, editable=False` ✅ (mig 0016) |
| `resolucion_dian` | FK → `ResolucionDIAN` | `PROTECT`, `related_name='documentos_soporte'` |
| `consecutivo` | IntegerField | `db_index=True, editable=False` — asignado por `GastoBusinessService` |
| `categoria_contable` | CharField(50) | `choices=CATEGORIA_CONTABLE_CHOICES`, nullable |
| `fecha` | DateField | fecha del documento |
| `proveedor` | FK → `tenant_proveedores.Proveedor` | `CASCADE` — si elimina proveedor, elimina todos sus DS |
| `numero_documento_proveedor` | CharField(100) | nullable, referencia factura del proveedor |
| `subtotal` | DecimalField(12,2) | `MinValueValidator(0.01)` — **editable**, base gravable |
| `retefuente_porcentaje` | CharField(10) | **DEPRECATED v3.7.1** — `editable=False`, choices=`RETEFUENTE_CHOICES` |
| `retefuente` | DecimalField(15,2) | **DEPRECATED v3.7.1** — `editable=False` |
| `reteica_porcentaje` | CharField(10) | **DEPRECATED v3.7.1** — `editable=False`, choices=`RETEICA_CHOICES` |
| `reteica` | DecimalField(15,2) | **DEPRECATED v3.7.1** — `editable=False` |
| `total` | DecimalField(15,2) | **editable** — `total = subtotal - retenciones` |
| `descripcion` | TextField | nullable |
| `observaciones` | TextField | blank=True |
| `cuenta_gasto_uuid` | UUIDField | nullable, `db_index=True` — mapeo a `CuentaContable` |
| `adjunto` | FileField | `upload_to='documentos_soporte/%Y/%m/'`, nullable |
| `activo` | BooleanField | `default=True, db_index=True` |
| `anulado` | BooleanField | `default=False` |
| `fecha_anulacion` | DateTimeField | nullable |
| `motivo_anulacion` | TextField | nullable |
| `usuario_anulacion` | FK → `perfil.TenantProfile` | `PROTECT`, nullable |

**Índices BD:**
```
(empresa, fecha)
(resolucion_dian, consecutivo)
(proveedor, numero_documento_proveedor)
(categoria_contable)
(fecha) WHERE activo=True AND anulado=False  → 'idx_gastos_activos'
```

**Constraints:**
```
UNIQUE (resolucion_dian, consecutivo)                               → 'unique_ds_resolucion_consecutivo'
UNIQUE (empresa, proveedor, numero_documento_proveedor) WHERE NOT anulado  → 'unique_ds_vendedor_documento'
```

**`clean()`:** Valida que `consecutivo` esté dentro de `rango_desde`..`rango_hasta` de la resolución.

#### Propiedades (Pull Model v3.7.1)

```python
@property prefijo              → resolucion_dian.prefijo
@property numero_documento     → resolucion_dian.formar_consecutivo(consecutivo)
@property total_retefuente     → Retencion(tipo='RETEFUENTE', doc=self.id, reversada=False).Sum('monto')
@property total_reteica        → Retencion(tipo='RETEICA', doc=self.id, reversada=False).Sum('monto')
@property total_reteiva        → Retencion(tipo='RETEIVA', doc=self.id, reversada=False).Sum('monto')
@property total_retenciones    → Retencion(todos tipos, doc=self.id, reversada=False).Sum('monto')
@property retefuente_calculada → alias a total_retefuente (retrocompat)
@property reteica_calculada    → alias a total_reteica (retrocompat)
@property vendedor_nombre      → proveedor.razon_social
@property vendedor_nit         → proveedor.numero_documento
@property vendedor_direccion   → proveedor.direccion
@property vendedor_telefono    → proveedor.telefono_contacto
@property total_cop            → "${total:,.0f}" formateado COP
@property subtotal_cop         → "${subtotal:,.0f}" formateado COP
@property retefuente_cop       → "${retefuente_calculada:,.0f}" formateado COP
@property reteica_cop          → "${reteica_calculada:,.0f}" formateado COP
@property total_retenciones_cop → "${total_retenciones:,.0f}" formateado COP
@property cuenta_gasto_label   → CuentaContableSelector.get_label_by_uuid(empresa_id, cuenta_gasto_uuid)
```

---

### 2.3 Módulo `choices/`

| Archivo | Constante | Uso |
|---------|-----------|-----|
| `choices/categoria_contable.py` | `CATEGORIA_CONTABLE_CHOICES` | importado en `DocumentoSoporte.categoria_contable` |
| `choices/centros_costo.py` | `CENTROS_COSTO_CHOICES` | disponible para clasificación administrativa |
| `choices/niif_gastos_choices.py` | `NIIF_GASTOS_CHOICES` | clasificación NIIF de gastos |

---

### 2.4 Migraciones (17 total)

| # | Archivo | Cambio Principal |
|---|---------|-----------------|
| 0001 | `0001_initial.py` | Creación inicial: ResolucionDIAN, DocumentoSoporte, modelo legacy Gasto |
| 0002 | `...idx_and_more.py` | Índices optimización |
| 0003 | `...resoluciondian_options.py` | Opciones de modelo y ordering |
| 0004–0006 | `...unique_ds_resolucion...` | Evolución de constraints únicos |
| 0007 | `...gasto_centro_idx.py` | Índices en Gasto legacy |
| 0008 | `...unique_ds_vendedor_documento.py` | Constraint vendedor+documento |
| 0009 | `...gasto_empresa_idx.py` | Índices empresa en Gasto legacy |
| 0010 | `...remove_gasto_documento_soporte.py` | **Elimina modelo legacy `Gasto`** — queda solo `DocumentoSoporte` |
| 0011 | `...retefuente_porcentaje.py` | Ajustes campos retención (pre-deprecación) |
| 0012 | `...alter_proveedor.py` | FK proveedor CASCADE |
| 0013 | `...add_cuenta_contable_uuid_fields.py` | Agrega `cuenta_gasto_uuid` y `cuenta_contrapartida_uuid` |
| 0014 | `...remove_cuenta_contrapartida_uuid.py` | Elimina `cuenta_contrapartida_uuid` (contabilidad la orquesta) |
| 0015 | `...alter_cuenta_gasto_uuid.py` | Ajuste field `cuenta_gasto_uuid` |
| 0016 | `...add_uuid_fields.py` | UUID fields en ResolucionDIAN y DocumentoSoporte ✅ |
| 0017 | `...alter_retefuente_and_more.py` | **ÚLTIMA (2026-05-17)** — `editable=False` en campos retención (deprecación v3.7.1) |

---

## 3. Service Layer (FSD)

### 3.1 `services/selectors.py` — Lectura Zero-Waste

#### `ResolucionSelector`

| Método | Descripción |
|--------|-------------|
| `get_list(empresa_id, search, solo_vigentes)` | `.only(RESOLUCION_LIST_FIELDS)` + `annotate(conteo_documentos=Count(...))` |
| `get_detail(empresa_id, resolucion_uuid)` | `.only(RESOLUCION_DETAIL_FIELDS)` + filtro opcional por uuid |
| `get_vigente(empresa_id)` | Cache 1 hora con key `resolucion_vigente_{empresa_id}` → `filter(vigente=True).first()` |

#### `DocumentoSelector`

| Método | Descripción |
|--------|-------------|
| `get_list(empresa_id, resolucion_id, search)` | `.only(DOCUMENTO_LIST_FIELDS)` + `select_related('resolucion_dian', 'proveedor')` + filtros opcionales; incluye anulados (consecutividad) |
| `get_detail(empresa_id, documento_uuid)` | `.select_related('resolucion_dian', 'proveedor', 'usuario_anulacion')` + filtro uuid |
| `get_summary(empresa_id)` | Agrega `SUM(total)` + `COUNT(id)` del mes actual para documentos no anulados → `{total_gastos_mes, documentos_emitidos, periodo_actual}` |

**Constantes SSoT:**
```python
RESOLUCION_LIST_FIELDS  = (id, uuid, numero_resolucion, prefijo, vigente,
                           rango_desde, rango_hasta, fecha_resolucion,
                           fecha_inicio, fecha_fin, consecutivo, empresa_id)

DOCUMENTO_LIST_FIELDS   = (id, uuid, consecutivo, subtotal, fecha, total,
                           categoria_contable, descripcion, activo, anulado,
                           numero_documento_proveedor, empresa_id, cuenta_gasto_uuid)

DOCUMENTO_DETAIL_FIELDS = (id, uuid, consecutivo, fecha, total, subtotal,
                           categoria_contable, descripcion, observaciones,
                           activo, anulado, numero_documento_proveedor, empresa_id,
                           cuenta_gasto_uuid, resolucion_dian_id, proveedor_id,
                           created_at, updated_at)

RESOLUCION_DETAIL_FIELDS = (id, uuid, numero_resolucion, prefijo, vigente,
                            rango_desde, rango_hasta, fecha_resolucion,
                            fecha_inicio, fecha_fin, clave_tecnica,
                            empresa_id, created_at, updated_at)
```

---

### 3.2 `services/crud_service.py` — Escritura Atómica

#### `ResolucionCRUDService`

| Método | Descripción |
|--------|-------------|
| `_invalidar_cache_vigente(empresa_id)` | Invalida cache `resolucion_vigente_{empresa_id}` |
| `crear_resolucion(data, empresa)` | `@transaction.atomic` — crea resolución, invalida cache si `vigente=True` |
| `desactivar_resolucion(resolucion)` | `@transaction.atomic` — `vigente=False`, invalida cache |
| `actualizar_resolucion(resolucion, data)` | `@transaction.atomic` — actualiza campos permitidos |
| `eliminar_resolucion(resolucion)` | Elimina si no tiene documentos asociados |

#### `DocumentoCRUDService`

| Método | Descripción |
|--------|-------------|
| `crear_documento(empresa, data, resolucion)` | `@transaction.atomic` — asigna consecutivo atómico desde resolución, crea DS |
| `actualizar_documento(instance, data)` | `@transaction.atomic` — actualiza campos editables del DS |
| `anular_documento(instance, motivo, usuario)` | `@transaction.atomic` — `anulado=True`, registra trazabilidad |
| `desactivar_documento(instance)` | `@transaction.atomic` — `activo=False` |
| `eliminar_documento(instance)` | Elimina físicamente si `anulado=True` |

---

### 3.3 `services/business_service.py` — Reglas de Negocio

#### `GastoBusinessService`

| Método | Descripción |
|--------|-------------|
| `anular_gasto(gasto_id, motivo, usuario, empresa_id)` | DSV `empresa_id` + `DocumentoCRUDService.anular_documento()` |
| `desactivar_gasto(gasto_id, empresa_id)` | DSV + `DocumentoCRUDService.desactivar_documento()` |
| `eliminar_gasto(gasto_id, empresa_id)` | DSV + valida `anulado=True` antes de eliminar físicamente |
| `procesar_gasto(empresa, data)` | Orquestador principal: resuelve resolución vigente → asigna consecutivo → crea DS → crea `Retencion` via Pull Model |

**Flujo `procesar_gasto`:**
```
1. Resolver resolucion_dian (de data o usar vigente)
2. DSV: resolucion.empresa_id == empresa.id
3. Validar consecutivo dentro del rango
4. DocumentoCRUDService.crear_documento() @transaction.atomic
5. Si retefuente_porcentaje > 0 → RetencionesService.crear_retencion(tipo='RETEFUENTE', ...)
6. Si reteica_porcentaje > 0 → RetencionesService.crear_retencion(tipo='RETEICA', ...)
7. return (success, documento, status_code)
```

#### `ResolucionBusinessService`

| Método | Descripción |
|--------|-------------|
| `validar_fechas_y_rangos(data)` | Valida `rango_desde < rango_hasta`, `fecha_inicio < fecha_fin` |
| `crear_resolucion(empresa, data)` | Valida + `ResolucionCRUDService.crear_resolucion()` |
| `desactivar_resolucion(empresa_id, resolucion_id)` | DSV + `ResolucionCRUDService.desactivar_resolucion()` |
| `puede_eliminar(empresa_id, resolucion_id)` | Retorna `(bool, mensaje)` — false si tiene documentos asociados |

---

### 3.4 `services/api_mixins.py` — Inyección en ViewSet

#### `GastoServiceMixin`

| Método | Descripción |
|--------|-------------|
| `_get_empresa_id_seguro()` | `tenant_profile.empresa_id` o fallback `Empresa.objects.first()` en DEBUG |
| `get_qs_list()` | `DocumentoSelector.get_list(empresa_id, ...)` con params del request |
| `get_qs_detail()` | `DocumentoSelector.get_detail(empresa_id)` |
| `service_crear_gasto(data, empresa)` | `GastoBusinessService.procesar_gasto()` |
| `service_anular_gasto(gasto, motivo, usuario)` | `GastoBusinessService.anular_gasto()` |
| `service_get_summary()` | `DocumentoSelector.get_summary(empresa_id)` |
| `_get_empresa()` | `resolve_tenant_empresa(request, self)` |

#### `ResolucionServiceMixin`

| Método | Descripción |
|--------|-------------|
| `_get_empresa_id_seguro()` | Idéntico al de GastoServiceMixin |
| `get_qs_list()` | `ResolucionSelector.get_list(empresa_id, ...)` |
| `get_qs_detail()` | `ResolucionSelector.get_detail(empresa_id)` |
| `service_crear_resolucion(empresa, data)` | `ResolucionBusinessService.crear_resolucion()` |
| `service_desactivar_resolucion(empresa_id, resolucion_id)` | `ResolucionBusinessService.desactivar_resolucion()` |
| `service_puede_eliminar(empresa_id, resolucion_id)` | `ResolucionBusinessService.puede_eliminar()` |

---

## 4. API Layer

### 4.1 ViewSets

| ViewSet | Herencia | lookup_field | Acciones |
|---------|----------|-------------|----------|
| `GastoViewSet` | `GastoServiceMixin, SintelDSVMixin, BaseTenantViewSet` | `uuid` | CRUD + `anular`, `summary`, `gestor_offcanvas` |
| `ResolucionDIANViewSet` | `ResolucionServiceMixin, SintelDSVMixin, BaseTenantViewSet` | `uuid` | CRUD + `activa`, `desactivar` |

---

### 4.2 Serializers (`api/serializers.py`)

| Serializer | Propósito |
|------------|-----------|
| `ResolucionDIANNestedSerializer` | Embedding en DocumentoSoporte (campos mínimos) |
| `ResolucionDIANListSerializer` | GET lista resoluciones |
| `ResolucionDIANCreateSerializer` | POST/PATCH resoluciones |
| `ResolucionDIANDetailSerializer` | GET detalle resolución |
| `DocumentoSoporteListSerializer` | GET lista gastos |
| `DocumentoSoporteDetailSerializer` | GET detalle + `@property` retenciones via Pull Model |

---

### 4.3 Endpoints REST

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/api/v1/gastos/` | Lista Documentos Soporte (paginada) |
| POST | `/api/v1/gastos/` | Crear DS + asignar consecutivo + crear Retenciones |
| GET | `/api/v1/gastos/{uuid}/` | Detalle completo |
| PATCH | `/api/v1/gastos/{uuid}/` | Actualizar campos editables |
| DELETE | `/api/v1/gastos/{uuid}/` | Eliminar (solo si anulado) |
| POST | `/api/v1/gastos/{uuid}/anular/` | Anular DS (inmutable desde ese momento) |
| GET | `/api/v1/gastos/summary/` | KPIs del mes: total gastos, documentos emitidos |
| GET | `/api/v1/gastos/gestor-offcanvas/` | Render HTML offcanvas gestor |
| GET | `/api/v1/gastos/resoluciones/` | Lista resoluciones DIAN |
| POST | `/api/v1/gastos/resoluciones/` | Crear resolución |
| GET | `/api/v1/gastos/resoluciones/{uuid}/` | Detalle resolución |
| PATCH | `/api/v1/gastos/resoluciones/{uuid}/` | Actualizar resolución |
| DELETE | `/api/v1/gastos/resoluciones/{uuid}/` | Eliminar resolución (si no tiene DS) |
| GET | `/api/v1/gastos/resoluciones/activa/` | Resolución vigente activa |
| POST | `/api/v1/gastos/resoluciones/{uuid}/desactivar/` | Desactivar resolución |

**Orden de registro en Router** (anti-greedy — fix v3.7.5):
```python
router.register(r'resoluciones', ResolucionDIANViewSet, ...)  # PRIMERO
router.register(r'', GastoViewSet, ...)                       # AL FINAL
```
**Motivo:** `r''` genera `^(?P<uuid>[^/.]+)/$` que capturaría `"resoluciones"` como UUID si va primero, causando 500 `"resoluciones" no es UUID válido`.

---

## 5. Frontend

### 5.1 JavaScript (`static/gastos/js/`)

| Archivo | Líneas | Namespace / Responsabilidad |
|---------|--------|----------------------------|
| `gastos.api.js` | 164 | **SSoT de URLs** — `window.Sintel.Gastos.API`: métodos `gastos.*`, `resoluciones.*`, `contabilidad.obtenerRetenciones()` |
| `gastos.utils.js` | 181 | Helpers con cache: `fetchProveedores()`, `fetchCuentas()`, `fetchResoluciones()`, `loadProveedoresSelect()`, `loadCuentasSelect()`, `loadResolucionesSelect()`, `invalidateCache()` |
| `features/gasto_editor.js` | 407 | Editor crear/editar: `init()`, `cargarProveedores()`, `obtenerRetencionesProveedor()`, `calcularTotales()`, `submitGasto()` |
| `features/gasto_list.js` | 422 | Tabulator: `init()`, `getColumnas()`, `handleCellAction()`, `verDetalle()`, `abrirEditarGasto()`, `anularGasto()`, `eliminarGasto()` |
| `features/resolucion_editor.js` | 185 | CRUD resoluciones: `init()`, `submitResolucion()` |

**Flujo de retenciones en formulario (v3.7.3):**
```
Usuario selecciona Retefuente desde dropdown
  → JS listener: #retefuente_select → #retefuente_porcentaje (hidden) = valor
  → calcularTotales() corre:
       subtotal = parseFloat(#base_gravable.value)
       retefuente = subtotal × porcentaje_retefuente / 100
       reteica    = subtotal × porcentaje_reteica / 100
       total      = subtotal - retefuente - reteica
  → actualiza displays: #retefuente_display, #reteica_display, #total_display
On save: backend recibe subtotal + total → crea Retencion via Pull Model
```

**Flujo precargar editar (v3.7.5):**
```
abrirEditarGasto(uuid) → GET /api/v1/gastos/{uuid}/
  → response.retefuente_calculada → setea valor en #base_gravable
  → response.cuenta_gasto_uuid → precarga select contable
  → response.total → precarga campo total
```

---

### 5.2 Templates HTML (`templates/tenant/gastos/`)

| Template | Líneas | Propósito |
|----------|--------|-----------|
| `gastos_list.html` | 148 | Lista principal con Tabulator + botones crear, filtrar |
| `list.html` | 3 | Wrapper mínimo (incluye `gastos_list.html`) |
| `offcanvas_crear_gasto.html` | 283 | Form crear DS: resolución, proveedor, base gravable, selectores retefuente/reteica, cuenta contable |
| `offcanvas_editar_gasto.html` | 291 | Form editar DS: misma estructura que crear pero con datos precargados desde BD |
| `offcanvas_detalle_gasto.html` | 141 | Vista read-only: todos los campos + retenciones calculadas |
| `offcanvas_resolucion.html` | 48 | Form crear/editar ResolucionDIAN |
| `assets_gastos.html` | 12 | Include CSS/JS del módulo |

**Estructura de secciones en `offcanvas_crear_gasto.html` y `offcanvas_editar_gasto.html`:**
```
1. Documento Soporte: resolucion_dian (select), consecutivo (auto), fecha
2. Información Proveedor: proveedor (select), display info (NIT, dirección, teléfono)
3. Valores:
   - Base Gravable: #base_gravable (editable)
   - Retefuente: #retefuente_select (dropdown RETEFUENTE_CHOICES) + #retefuente_display (readonly)
   - ReteICA: #reteica_select (dropdown RETEICA_CHOICES) + #reteica_display (readonly)
   - Total: #total_display (calculado automáticamente)
   - Inputs ocultos: #retefuente_porcentaje, #reteica_porcentaje
4. Categorización Contable: categoria_contable (select CATEGORIA_CONTABLE_CHOICES), cuenta_gasto_uuid
5. Observaciones: textarea
```

---

## 6. Tests (`tests/` — 6 archivos)

| Archivo | Propósito |
|---------|-----------|
| `conftest.py` | Fixtures multi-tenant: `tenant1`, `tenant2` con schemas aislados |
| `test_auth_session_smoke.py` | Smoke test de autenticación |
| `test_fase9_persistence.py` | Tests de persistencia (fase 9 Contabilidad) |
| `test_gastos_login_session_loop.py` | Tests de sesión en loop |
| `test_multitenant_isolation.py` | Verifica aislamiento por schema entre `tenant1` y `tenant2` |
| `test_proveedor_integration.py` | Integración con módulo Proveedores |

---

## 7. Checklist AGENTS.md — Estado de Cumplimiento

| Regla | Estado | Detalle |
|-------|--------|---------|
| `SintelTenantBaseModel` | ✅ | `ResolucionDIAN` y `DocumentoSoporte` |
| `empresa_id` en queries | ✅ | Todos los selectores filtran por `empresa_id` |
| `.only()` en querysets | ✅ | `RESOLUCION_LIST_FIELDS`, `DOCUMENTO_LIST_FIELDS`, `RESOLUCION_DETAIL_FIELDS`, `DOCUMENTO_DETAIL_FIELDS` |
| `lookup_field = 'uuid'` | ✅ | Ambos ViewSets (heredado de `BaseTenantViewSet`) |
| UUID en modelos | ✅ | Migración 0016 aplicada |
| No signals para negocio | ✅ | Service Layer exclusivo |
| `@transaction.atomic` en CRUD | ✅ | Todos los métodos de `ResolucionCRUDService` y `DocumentoCRUDService` |
| `BaseTenantViewSet` sin override auth | ✅ | Ningún ViewSet sobreescribe `authentication_classes` |
| FK a `perfil.TenantProfile` (no a `AUTH_USER_MODEL`) | ✅ | `usuario_anulacion` FK a `TenantProfile` |
| Pull Model retenciones | ✅ | `@property` lee desde `Contabilidad.Retencion`, `editable=False` en campos deprecated |
| Router anti-greedy | ✅ | `r'resoluciones'` registrado ANTES que `r''` |
| Sincronía CHOICES templates | ✅ | `RETEFUENTE_CHOICES`/`RETEICA_CHOICES` en `models.py` — templates sincronizados |
| `APP_ORIGEN_PREFIJOS['gastos']` en Contabilidad | ✅ | `cuenta_gasto_uuid` válida contra prefijos de contabilidad |
| Imports globales (no dentro de `def`) | ⚠️ | `models.py` usa imports locales en `@property` — excepción justificada (circular import con contabilidad) |

---

## 8. Fixes Aplicados (v3.7.x)

### F1 — Router Greedy Matching → 500 en GET `/resoluciones/` (v3.7.5)

**Causa:** `r''` (GastoViewSet) registrado primero en `api/urls.py`. El patrón `^(?P<uuid>[^/.]+)/$` capturaba `"resoluciones"` como UUID → `500 '"resoluciones" no es un UUID válido'`.

**Fix:**
```python
# ANTES (roto):
router.register(r'', GastoViewSet, basename='gastos')
router.register(r'resoluciones', ResolucionDIANViewSet, basename='resoluciones-dian')

# DESPUÉS (correcto):
router.register(r'resoluciones', ResolucionDIANViewSet, ...)  # PRIMERO
router.register(r'', GastoViewSet, ...)                       # AL FINAL
```

---

### F2 — Selectores de Retenciones UI (v3.7.3)

**Cambio:** Usuario selecciona tipo de retención desde dropdown en formulario. Los porcentajes se calcutan en tiempo real en el cliente. Los montos se envían al backend que crea `Retencion` records via Pull Model.

**Arquitectura:**
- SSoT: `RETEFUENTE_CHOICES` / `RETEICA_CHOICES` en `models.py`
- Frontend: Replicados como `<option>` en ambos templates
- IDs HTML: `#retefuente_select`, `#reteica_select`, `#retefuente_porcentaje`, `#reteica_porcentaje`
- Listener JS en `gasto_editor.js` → `calcularTotales()` en tiempo real

---

### F3 — Precargar Editar Gasto desde BD (v3.7.5)

**Cambio:** Al abrir el offcanvas de edición, los valores de retenciones y base gravable se precargan desde la respuesta del API Detail, evitando que el usuario tenga que reintroducirlos.

---

### F4 — Base Gravable como campo editable (v3.7.5)

**Cambio:** Campo `Base Gravable` es un input editable directo. El usuario ingresa el monto base; el sistema calcula retenciones y total automáticamente.

---

## 9. Deuda Técnica

| ID | Archivo | Severidad | Descripción |
|----|---------|-----------|-------------|
| DEUDA-01 | `models.py` - `retefuente*`/`reteica*` | MEDIA | Campos `editable=False` DEPRECATED v3.7.1 aún en modelo — eliminar en v3.9 junto cleanup global retenciones |
| DEUDA-02 | `services/selectors.py` - `LIST_FIELDS`/`DETAIL_FIELDS` | BAJA | Exportados como dict `{documento: ..., resolucion: ...}` — inconsistente con el patrón de otras apps que exportan tuplas directas |
| DEUDA-03 | `choices/` directory | BAJA | `centros_costo.py` y `niif_gastos_choices.py` — validar si están en uso en algún campo o solo disponibles |
| DEUDA-04 | `gasto_editor.js` | BAJA | 407 líneas — el editor podría fragmentarse en `gasto_editor_retenciones.js` + `gasto_editor_form.js` |
| DEUDA-05 | `models.py` - imports locales en `@property` | BAJA | `from apps.tenant.contabilidad.models import Retencion` dentro de cada `@property` — repetitivo; considerar helper privado centralizado |
| DEUDA-06 | Tests | MEDIA | Solo 6 archivos de test — faltan tests para: `GastoBusinessService.procesar_gasto()`, consecutivos atómicos, anulación con trazabilidad, Pull Model retenciones |

---

## 10. Patrones Clave

### 10.1 Consecutivo Atómico

```
DocumentoCRUDService.crear_documento():
  @transaction.atomic
  → ResolucionDIAN.objects.select_for_update().get(id=resolucion_id)
  → consecutivo = resolucion.consecutivo  (incrementar)
  → DS.clean() → valida rango
  → resolucion.consecutivo += 1; resolucion.save()
  → DocumentoSoporte.objects.create(consecutivo=consecutivo, ...)
```
Garantiza que dos transacciones simultáneas no asignen el mismo consecutivo.

### 10.2 Pull Model (ADR-001 v3.7.1)

```
DocumentoSoporte.total_retefuente [@property]
  → Contabilidad.Retencion.objects.filter(
      tipo='RETEFUENTE',
      documento_origen_app='gastos',
      documento_origen_modelo='DocumentoSoporte',
      documento_origen_id=self.id,
      reversada=False
    ).aggregate(Sum('monto'))
```

`DocumentoSoporte` nunca almacena retenciones propias. Los campos `retefuente`/`reteica` son vestigios con `editable=False`.

### 10.3 Cache Resolución Vigente

```python
cache_key = f"resolucion_vigente_{empresa_id}"
# TTL: 1 hora
# Invalidado en: ResolucionCRUDService.crear_resolucion() si vigente=True
#               ResolucionCRUDService.desactivar_resolucion()
```

### 10.4 Inmutabilidad por Anulación (no por estado)

```
DS.activo=True, DS.anulado=False  → Activo, editable
DS.activo=False                   → Desactivado, no editable
DS.anulado=True                   → Anulado, eliminar físicamente permitido
Consecutivo: NUNCA reutilizable (constraint unique)
```

---

## 11. Flujo Completo: Crear Documento Soporte

```
[Frontend offcanvas_crear_gasto.html]
  ↓ usuario selecciona proveedor → obtenerRetencionesProveedor()
    → GET /api/v1/contabilidad/retenciones/obtener-por-tercero/?nit=NIT&tipo=PROVEEDOR&naturaleza=COMPRA
    → Pre-llena dropdown Retefuente/ReteICA si hay retenciones configuradas
  ↓ usuario ingresa Base Gravable → calcularTotales()
    → retefuente = base × pct_retefuente / 100
    → reteica    = base × pct_reteica / 100
    → total      = base - retefuente - reteica
  ↓ usuario confirma → POST /api/v1/gastos/
    Body: {resolucion_dian, proveedor, fecha, subtotal, total,
           retefuente_porcentaje, reteica_porcentaje,
           categoria_contable, cuenta_gasto_uuid, descripcion}
      ↓
[GastoViewSet.create()]
  → empresa = _get_empresa()
  → service_crear_gasto(data, empresa)
    ↓
[GastoBusinessService.procesar_gasto(empresa, data)]
  → Resolver resolucion_dian (data o vigente)
  → DSV: resolucion.empresa_id == empresa.id
  → DocumentoCRUDService.crear_documento() @transaction.atomic
      → select_for_update resolucion
      → asignar consecutivo atómico
      → DocumentoSoporte.objects.create(...)
      → resolucion.consecutivo += 1
  → Si retefuente_porcentaje > 0:
      → RetencionesService.crear_retencion(tipo='RETEFUENTE', monto=..., doc=DS)
  → Si reteica_porcentaje > 0:
      → RetencionesService.crear_retencion(tipo='RETEICA', monto=..., doc=DS)
  → return (True, documento, 201)
      ↓
[Response 201 + serialized DocumentoSoporte]
  ↓
[gasto_list.js] → table.replaceData() → tabla se refresca
```

---

## 12. Flujo Completo: Anular Documento Soporte

```
[gasto_list.js] → usuario clic en btn "Anular"
  → confirma en modal con campo motivo
  → POST /api/v1/gastos/{uuid}/anular/
    Body: {motivo: "descripcion del motivo"}
      ↓
[GastoViewSet.anular()]
  → get_object() → DS con empresa_id verificado
  → service_anular_gasto(instance, motivo, request.user)
    ↓
[GastoBusinessService.anular_gasto(gasto_id, motivo, usuario, empresa_id)]
  → DSV: DS.empresa_id == empresa_id → 403 si no coincide
  → DocumentoCRUDService.anular_documento(instance, motivo, usuario_profile)
      @transaction.atomic
      → DS.anulado = True
      → DS.fecha_anulacion = timezone.now()
      → DS.motivo_anulacion = motivo
      → DS.usuario_anulacion = usuario_profile (TenantProfile)
      → DS.save()
      ↓ Consecuencias:
      → Consecutivo queda en "hueco" en la secuencia (inmutable por constraint)
      → DS ahora eliminable físicamente si se requiere
      ↓
[Response 200 + {detail: "Documento anulado"}]
  ↓
[gasto_list.js] → table.replaceData() → fila aparece con badge "Anulado"
```
