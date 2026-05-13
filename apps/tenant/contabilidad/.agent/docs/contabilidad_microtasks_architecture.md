# CONTABILIDAD — Arquitectura de Microtareas

**Version:** 3.5.0
**App:** `apps/tenant/contabilidad/`

---

## 📂 Navegación de Documentación
- [🗺️ Mapa de Flujos y Secuencias](contabilidad_flow_map.md)
- [⚖️ Lógica de Negocio y Reglas SSoT](contabilidad_business_logic.md)
- [🏠 Portal de Auditoría](../AUDITORIA_FLUJO_CONTABILIDAD.md)

---

## 1. Resumen General

`contabilidad` es el bounded context mas complejo del sistema. Tiene **dos caminos de entrada para crear asientos** completamente independientes:

| Camino | Trigger | Orquestador | Estado resultante |
|---|---|---|---|
| **Pull Model (ETL automatico)** | Celery task / management command | `Contabilizador` via `Extractores` | `BORRADOR` |
| **Manual On-Demand (UI)** | Usuario desde pendientes en workspace | `ContabilidadBusinessService.contabilizar_documento_manual()` | `APROBADO` |

Las apps fuente (`gastos`, `facturas`, `inventario`, `empleados`) **nunca importan de `contabilidad`**. La extraccion es activa: `contabilidad` lee las fuentes, no al reves.

**Principio de inmutabilidad por estado:**
- `BORRADOR` — editable
- `APROBADO` — solo lectura, cuadrado verificado
- `CERRADO` — periodo cerrado, inmutable

---

## 2. Mapa de Archivos

```
apps/tenant/contabilidad/
├── models.py                          # 8 modelos de dominio
├── admin.py
├── apps.py
├── tasks.py                           # 2 tareas Celery
├── views_ui.py                        # Vistas UI legado
├── urls.py                            # URL config
│
├── choices/
│   └── choices.py                     # CATALOGO_NIIF_COLOMBIA (choices estaticos)
│
├── integracion/                       # NUCLEO: Pull Model ETL
│   ├── dtos.py                        # DTOs inmutables (frozen dataclasses)
│   ├── contabilizador.py              # Orquestador principal de materializacion
│   ├── resolver.py                    # Resolucion de cuentas PUC via ReglaContable
│   ├── validadores.py                 # Validadores stateless (cuadratura, periodo)
│   ├── excepciones.py                 # Jerarquia ContabilidadError
│   └── extractores/
│       ├── base.py                    # AbstractExtractor (template method pattern)
│       ├── gastos.py                  # ExtractorGastos ← DocumentoSoporte
│       ├── facturas.py                # ExtractorFacturas ← Factura ACEPTADA
│       ├── inventario.py              # ExtractorInventario ← MovimientoInventario
│       └── nomina.py                  # ExtractorNomina ← Devengo aprobado
│
├── services/
│   ├── __init__.py
│   ├── selectors.py                   # Todos los QuerySets read-only + reportes
│   ├── crud_service.py                # Persistencia atomica DB
│   ├── business_service.py            # Orquestacion, reglas dominio, IA, integracion
│   └── api_mixins.py                  # ContabilidadServiceMixin
│
├── api/
│   ├── __init__.py
│   ├── serializers.py                 # 15+ serializers por modelo y accion
│   ├── viewsets.py                    # 7 ViewSets
│   ├── urls.py                        # DRF Router (7 rutas registradas)
│   ├── filters.py
│   ├── pagination.py
│   ├── permissions.py
│   └── datatables.py                  # LEGADO — eliminado funcionalidad
│
├── management/commands/
│   ├── backfill_contabilidad.py       # CLI: ejecutar ETL Pull manualmente
│   ├── poblar_catalogo_niif.py        # CLI: seed CatalogoMaestroNIIF
│   └── seed_reglas_contables.py       # CLI: seed ReglaContable defaults
│
├── templates/tenant/contabilidad/
│   ├── asiento_page.html
│   ├── cuenta_page.html
│   ├── periodo_page.html
│   ├── reporte_page.html
│   └── partials/
│       ├── asiento_offcanvas_form.html
│       ├── asiento_offcanvas_editar.html
│       ├── asiento_offcanvas_detalle.html
│       ├── cuenta_offcanvas_form.html
│       ├── cuenta_offcanvas_detalle.html
│       ├── periodo_offcanvas_form.html
│       ├── periodo_offcanvas_detalle.html
│       ├── pendiente_offcanvas_contabilizar.html
│       ├── pendientes_list.html
│       ├── contabilidad_asientos_list.html
│       ├── contabilidad_cuentas_list.html
│       ├── contabilidad_periodos_list.html
│       ├── summary.html
│       └── assets_*.html              # 6 archivos de carga de assets JS
│
├── static/contabilidad/js/
│   ├── contabilidad.js                # Orquestador general
│   ├── asiento/
│   │   ├── asiento.api.js             # SSoT endpoints asientos
│   │   ├── tipo_comprobante.api.js    # SSoT endpoints tipos comprobante
│   │   └── features/
│   │       ├── asiento_list.js        # Grilla Tabulator asientos
│   │       ├── asiento_editor.js      # Editor de asiento (lineas manejo)
│   │       └── asiento_cargar_desde_docs.js  # Carga desde documentos pendientes
│   ├── cuenta/
│   │   ├── cuenta.api.js
│   │   └── features/
│   │       ├── cuenta_list.js
│   │       └── cuenta_editor.js
│   ├── periodo/
│   │   ├── periodo.api.js
│   │   └── features/
│   │       ├── periodo_list.js
│   │       └── periodo_editor.js
│   ├── pendiente/
│   │   └── pendiente_list.js          # Lista documentos pendientes de contabilizar
│   └── reporte/
│       ├── reporte.api.js
│       └── reporte.ui.js              # Balance de prueba + Estado de Resultados
│
├── scratch/                           # Scripts de diagnostico (no produccion)
│   ├── audit_gastos.py
│   └── validate_extractor_gastos.py
│
└── tests/
    ├── test_api_contabilidad.py
    ├── test_fase1_gastos.py
    ├── test_integracion_contabilizador.py
    └── test_templates.py
```

---

## 3. Modelos

### `CatalogoMaestroNIIF(SintelTenantBaseModel)`
Catalogo oficial NIIF Colombia. Cada tenant tiene su propia copia. Campos `nombre`, `nivel`, `naturaleza` son `editable=False` — se autocompletan desde `choices/choices.py`.

| Campo | Tipo | Notas |
|---|---|---|
| `codigo` | CharField(20) | UNIQUE — codigo PUC oficial |
| `nombre` | CharField(200) | editable=False — auto desde catalogo |
| `nivel` | IntegerField | editable=False — 1,2,4,6 |
| `naturaleza` | CharField(1) | D=Debito / C=Credito, editable=False |
| `activa` | BooleanField | Puede desactivarse por tenant |

### `CuentaContable(SintelTenantBaseModel)`
Plan de cuentas del tenant. Puede vincular al catalogo maestro o ser libre.

| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUID | Lookup publico en API |
| `codigo` | CharField(20) | UNIQUE por empresa |
| `nombre` | CharField(200) | |
| `tipo` | CharField | ACTIVO/PASIVO/PATRIMONIO/INGRESO/GASTO |
| `nivel` | PositiveSmallIntegerField | 1-6. Solo nivel 6 permite movimientos |
| `cuenta_padre` | FK('self', SET_NULL) | Jerarquia del PUC |
| `catalogo_referencia` | FK(CatalogoMaestroNIIF, SET_NULL) | Vinculo con NIIF oficial |
| `activa` | BooleanField | |

**Regla critica: solo cuentas de nivel 6 (auxiliares) aceptan movimientos.**

### `TipoComprobante(SintelTenantBaseModel)`
Plantilla para numeracion dinamica de comprobantes.

| Campo | Notas |
|---|---|
| `uuid` | Lookup publico |
| `codigo` | Sigla (CC, RC, ND, etc.) — UNIQUE por empresa |
| `prefijo` | Prefijo del consecutivo |
| `consecutivo_actual` | Autoincrementa con `obtener_siguiente_numero()` |

**Metodo critico:** `obtener_siguiente_numero()` — genera `{prefijo}{00001}` e incrementa el consecutivo en la misma llamada. Side effect: llama a `self.save(update_fields=['consecutivo_actual'])`.

### `AsientoContable(SintelTenantBaseModel)`
Asiento contable completo. Corazon del modulo.

| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUID | Lookup publico |
| `numero` | CharField(50) | UNIQUE — formato `ASI-YYYYMMDD-{UUID8}` o `RVER-...` |
| `fecha` | DateField | |
| `estado` | CharField | BORRADOR / APROBADO / CERRADO |
| `tipo_comprobante` | CharField | Legado (choices FVE/CE/RC/GN/ND/NC) |
| `tipo_comprobante_ref` | FK(TipoComprobante, PROTECT) | Referencia dinamica v3.5 |
| `numero_comprobante` | CharField(50) | Numero del comprobante origen |
| `documento_origen_app` | CharField(30) | facturas / gastos / empleados / inventario |
| `documento_origen_modelo` | CharField(50) | Factura / DocumentoSoporte / Devengo |
| `documento_origen_id` | PositiveIntegerField | PK en la app origen |
| `documento_origen_numero` | CharField(50) | Numero legible del origen |
| `documento_origen_reversado` | BooleanField | True si es reversal |
| `asiento_reversado` | FK('self', SET_NULL) | Asiento que reverte |
| `periodo_contable` | FK(PeriodoContable, PROTECT) | |
| `debe_total` | Decimal(15,2) | Suma debitos |
| `haber_total` | Decimal(15,2) | Suma creditos. DEBE == HABER siempre |
| `total_debe` / `total_haber` | Decimal | Legado — sincronizado en `save()` |

**Indexes criticos:** `(documento_origen_app, documento_origen_modelo, documento_origen_id)` — idempotencia Pull Model.

### `MovimientoContable(SintelTenantBaseModel)`
Partida individual de un asiento (linea del libro mayor).

| Campo | Notas |
|---|---|
| `asiento` | FK(AsientoContable, CASCADE) |
| `cuenta_codigo` | CharField — resolucion directa PUC (v3.0) |
| `cuenta` | FK(CuentaContable, PROTECT) — legado |
| `tipo_tercero` | CLIENTE / PROVEEDOR / EMPLEADO / OTRO |
| `tercero_nit` | Snapshot NIT (desnormalizado) |
| `tercero_razon_social` | Snapshot nombre (desnormalizado) |
| `debe` / `haber` | Decimal(15,2) |
| `base_iva` / `iva_generado` / `iva_descontable` | Decimal — campos NIIF |
| `retefuente` / `reteica` | Decimal — retenciones |
| `centro_costo_id` | PositiveIntegerField — referencia desacoplada a proyectos |

### `PeriodoContable(SintelTenantBaseModel)`
Periodo mensual que controla cuando se pueden crear asientos.

| Campo | Notas |
|---|---|
| `uuid` | Lookup publico |
| `periodo` | YYYY-MM — UNIQUE por empresa |
| `fecha_inicio` / `fecha_fin` | Rango del mes |
| `estado` | ABIERTO / CERRADO |
| `cerrado_por` | FK(perfil.TenantProfile, SET_NULL) |

**Regla critica:** Un periodo CERRADO bloquea creacion y edicion de asientos cuya fecha caiga en ese rango. `PeriodoCerradoError` se lanza desde `validadores.py`.

### `ReglaContable(SintelTenantBaseModel)`
Mapeo `(tipo_transaccion, concepto) → cuenta_codigo PUC`. SSoT para resolucion automatica de cuentas.

| Campo | Notas |
|---|---|
| `tipo_transaccion` | VENTA_FACTURA, COMPRA_GASTO, etc. |
| `concepto` | INGRESO_PRINCIPAL, GASTO_GENERAL, RETEFUENTE, etc. |
| `cuenta_codigo` | Codigo PUC 6 digitos |
| `activo` | BooleanField |

**Constraint:** `UNIQUE (empresa, tipo_transaccion, concepto) WHERE activo=True`.

### `TarifaImpuesto(SintelTenantBaseModel)`
Tasa vigente de impuesto o deduccion por fecha. Reemplaza tasas hardcodeadas.

16 tipos: IVA, RETEFUENTE, RETEICA, RETEIVA, y todas las parafiscales de nomina (SALUD, PENSION, ARL, CAJA, ICBF, SENA, CESANTIAS, PRIMA, VACACIONES, INTERESES_CESANTIAS).

---

## 4. DTOs del Contrato de Integracion

Definidos en `integracion/dtos.py`. Todos son `@dataclass(frozen=True)` — inmutables.

```
TransaccionEconomica          ← DTO principal, contrato con apps fuente
  tipo: TipoTransaccion       ← Enum (17 tipos)
  fecha: date
  descripcion: str
  tercero: TerceroSnapshot    ← Snapshot desnormalizado (sin FK)
  lineas: List[LineaTransaccion]
  documento_origen: DocumentoOrigen  ← Para idempotencia
  empresa_id: Optional[int]   ← Inyectado por Contabilizador, NO por caller

LineaTransaccion
  concepto: str               ← Llave de busqueda en ReglaContable
  monto: Decimal
  lado: str                   ← 'DEBE' o 'HABER'
  impuestos: List[ImpuestoLinea]
  cuenta_hint: Optional[str]  ← Override explicito de cuenta PUC

ImpuestoLinea
  tipo: str                   ← IVA_GENERADO, RETEFUENTE, RETEICA, etc.
  base / porcentaje / valor: Decimal
  lado: str                   ← 'HABER' por defecto (retenciones son pasivo)

TerceroSnapshot
  tipo: TipoTercero           ← CLIENTE / PROVEEDOR / EMPLEADO / OTRO
  id_origen / nit / razon_social  ← Snapshot, sin FK

DocumentoOrigen
  app_label / modelo / id / numero  ← Traza al documento fuente

# DTOs para flujo Manual On-Demand:
LineaManual                   ← cuenta_codigo explicito (sin ReglaContable)
ComprobanteManualDTO          ← Payload del offcanvas de contabilizacion manual
```

---

## 5. Nucleo de Integracion — Pull Model

### `integracion/contabilizador.py` — `Contabilizador`

Orquestador principal. **Unico punto de entrada para crear asientos programaticamente.**

```
Contabilizador(empresa_id)
  ├── resolver = ResolverCuentas(empresa_id)  ← cache de ReglaContable

  contabilizar(transaccion: TransaccionEconomica) → AsientoContable
    @transaction.atomic
    1. _resolver_periodo(fecha) → PeriodoContable
    2. validar_periodo_abierto(periodo)
    3. _validar_no_existe(documento_origen)   ← idempotencia
    4. _construir_asiento(transaccion, periodo)
       → Por cada LineaTransaccion:
           resolver.resolver_cuenta(concepto, tipo) → codigo_PUC
           → MovimientoContable (principal, lado DEBE o HABER segun linea.lado)
           → Por cada ImpuestoLinea:
               resolver.resolver_cuenta(impuesto.tipo, tipo) → codigo_PUC
               → MovimientoContable (impuesto, lado segun impuesto.lado)
       → Acumula debe_total / haber_total
       → asiento.movimientos_por_guardar = [...]
    5. validar_no_vacio(debe_total, haber_total)
    6. validar_cuadratura(debe_total, haber_total)  ← DEBE == HABER
    7. asiento.save()
    8. movimiento.save() por cada uno

  existe_asiento_para(app_label, modelo, id) → bool
    ← filter(empresa_id, documento_origen_*, reversado=False).exists()

  reversar_asiento(asiento_original) → AsientoContable
    @transaction.atomic
    → Nuevo asiento numero RVER-{fecha}-{UUID8}
    → Movimientos espejo con DEBE/HABER invertidos
    → documento_origen_reversado=True + asiento_reversado=original
```

### `integracion/resolver.py` — `ResolverCuentas`

```
ResolverCuentas(empresa_id)
  _cache_reglas / _cache_tarifas  ← in-memory cache por request

  resolver_cuenta(concepto, tipo_transaccion, cuenta_hint=None) → str
    1. Si cuenta_hint → retornar directamente (override)
    2. Buscar en _cache_reglas[(tipo, concepto)]
    3. ReglaContable.filter(empresa_id, tipo, concepto, activo=True).first()
    4. Si no existe → ReglaContableNoDefinidaError

  resolver_tarifa(tipo_impuesto, fecha) → Decimal
    → TarifaImpuesto con vigencia en fecha → valor_porcentaje / 100

  resolver_tarifa_patron_parafiscal(tipo, salario_base, fecha)
    → Si salario_base < 10 * SMMLV_2026 → return Decimal('0')  [exoneracion]
    → Sino → resolver_tarifa(tipo, fecha)
```

### `integracion/validadores.py` — Validators stateless

```
validar_cuadratura(debe, haber)
  → AsientoNoCuadradoError si debe != haber

validar_periodo_abierto(periodo)
  → PeriodoCerradoError si periodo.estado == 'CERRADO'

validar_no_vacio(debe, haber)
  → AsientoNoCuadradoError si ambos son 0
```

### `integracion/extractores/` — AbstractExtractor + 4 implementaciones

**Template Method Pattern:** `AbstractExtractor.contabilizar_pendientes()` orquesta el loop, cada extractor implementa solo `extraer_pendientes()`.

```
AbstractExtractor(empresa_id)
  contabilizador = Contabilizador(empresa_id)

  contabilizar_pendientes() → dict
    pendientes = self.extraer_pendientes()
    for dto in pendientes:
      try:
        contabilizador.contabilizar(dto)
        resultados['contabilizados'] += 1
      except AsientoYaExisteError:
        resultados['omitidos'] += 1
      except Exception as e:
        resultados['errores'].append({doc, error, ref})
    return resultados

ExtractorGastos.extraer_pendientes()
  → ya_contabilizados = AsientoContable.filter(empresa_id, app='gastos').values_list('documento_origen_id')
  → DocumentoSoporte.filter(empresa_id, anulado=False).exclude(id__in=ya_contabilizados)
  → _mapear_a_dto(doc):
      tercero = TerceroSnapshot(PROVEEDOR, doc.proveedor_id, nit, razon_social)
      lineas:
        - LineaTransaccion(GASTO_GENERAL|categoria_contable, subtotal, 'DEBE')
        - LineaTransaccion('RETEFUENTE', retefuente, 'HABER') si > 0
        - LineaTransaccion('RETEICA', reteica, 'HABER') si > 0
        - LineaTransaccion('PASIVO_COMPRA_GASTO', total, 'HABER')
      TransaccionEconomica(COMPRA_GASTO, fecha, descripcion, tercero, lineas, DocumentoOrigen)

ExtractorFacturas / ExtractorInventario / ExtractorNomina — patron identico
```

---

## 6. Service Layer

### `services/selectors.py` — Queries read-only y reportes

**Field Sets SSoT:**
- `CUENTA_LIST_FIELDS` (7 campos) / `CUENTA_DETAIL_FIELDS` (9 campos)
- `ASIENTO_LIST_FIELDS` (9 campos) / `ASIENTO_DETAIL_FIELDS` (11 campos)
- `PERIODO_LIST_FIELDS` (8 campos) / `PERIODO_DETAIL_FIELDS` (11 campos)
- `CATALOGO_LIST_FIELDS`, `TIPO_COMPROBANTE_LIST_FIELDS/DETAIL_FIELDS`
- `MOVIMIENTO_LIST_FIELDS` / `MOVIMIENTO_DETAIL_FIELDS`

**Selectors basicos:**
```
qs_cuenta_list(empresa_id) → CuentaContable.filter(empresa_id).only(LIST_FIELDS)
qs_cuenta_detail(empresa_id) → select_related(cuenta_padre, catalogo_referencia)
qs_asiento_list(empresa_id) → prefetch_related(movimientos)
qs_asiento_detail(empresa_id) → prefetch_related(movimientos, movimientos__cuenta)
qs_periodo_list/detail(empresa_id) → select_related(cerrado_por)
get_*_by_identifier(id_o_uuid, empresa_id) → objeto o ValidationError
```

**`APP_ORIGEN_PREFIJOS`** — SSoT de prefijos PUC por app. Usado en `CuentaContableViewSet` con `?app_origen=gastos` para filtrar solo cuentas relevantes al tipo de documento.

**Pendientes de contabilizar:**
```
qs_facturas_pendientes(empresa_id)
  → Factura.exclude(id__in=AsientoContable.filter(app='facturas').values_list('documento_origen_id'))

qs_gastos_pendientes(empresa_id)
  → DocumentoSoporte.filter(anulado=False).exclude(id__in=...)

qs_nominas_pendientes(empresa_id)
  → Devengo.filter(anulado=False).exclude(id__in=...)

qs_inventario_pendientes(empresa_id)
  → MovimientoInventario.exclude(id__in=...)
```

**Reportes financieros:**
```
balance_prueba_selector(empresa_id, fecha_inicio, fecha_fin)
  1. MovimientoContable.filter(empresa_id, fecha_range, estado=APROBADO)
     .values(cuenta__codigo, cuenta__nombre, cuenta__nivel)
     .annotate(debito=Sum(debe), credito=Sum(haber))
  2. Saldos anteriores: MovimientoContable.filter(fecha < fecha_inicio)
  3. Calcular saldo_anterior + nuevo_saldo por naturaleza cuenta
  → Lista ordenada por codigo

estado_resultados_selector(empresa_id, fecha_inicio, fecha_fin)
  → MovimientoContable.filter(cuenta__codigo__regex='^[456]')
  → Agrupa: Clase 4=Ingresos(C), Clase 5=Gastos(D), Clase 6=Costos(D)
  → Calcula: utilidad_bruta = ingresos - costos; utilidad_neta = bruta - gastos

verificar_periodo_cerrado(fecha, empresa_id) → (bool, periodo_str)
  → PeriodoContable.filter(CERRADO, fecha_inicio__lte, fecha_fin__gte)

filtrar_cuentas_por_app_origen(qs, app_origen)
  → Aplica Q(codigo__startswith=...) por cada prefijo en APP_ORIGEN_PREFIJOS[app_origen]
```

### `services/business_service.py` — `ContabilidadBusinessService`

**Validaciones de dominio:**
```
_validar_cuadratura(movimientos, estado)
  → Si estado APROBADO/CERRADO: |DEBE - HABER| >= 0.01 → ValidationError

_validar_periodo(fecha, empresa_id)
  → verificar_periodo_cerrado(fecha, empresa_id) → PeriodoCerradoError si True

_validar_cuentas_auxiliares(movimientos)
  → CuentaContable.filter(id__in).exclude(nivel=6) → ValidationError si existen
```

**Acciones de asientos:**
```
crear_asiento(empresa_id, payload) → dict
  1. _validar_periodo
  2. _validar_cuadratura
  3. _validar_cuentas_auxiliares
  4. crud.crear_asiento(empresa_id, payload, movimientos)

actualizar_asiento(asiento_id, payload)
  → Guard: estado APROBADO/CERRADO → inmutable
  → Re-validar si cambia fecha o movimientos

eliminar_asiento(asiento_id)
  → Guard: estado APROBADO/CERRADO → no eliminable

aprobar_asiento(asiento_id)
  → prefetch movimientos → _validar_cuadratura(datos, 'APROBADO') → estado=APROBADO
```

**CRUD Cuentas:**
```
crear_cuenta(empresa_id, payload)
  → Unicidad: CuentaContable.filter(empresa_id, codigo).exists() → error
  → crud.crear_cuenta

actualizar_cuenta(cuenta_id, payload)
  → Unicidad codigo: exclude(id=cuenta_id)

eliminar_cuenta(cuenta_id)
  → Guard: tiene cuentas_hijas → error
  → Guard: tiene MovimientoContable → error
```

**CRUD Periodos:**
```
crear_periodo / actualizar_periodo / eliminar_periodo
  → Guard eliminar: estado CERRADO → no eliminable
```

**Flujo Manual On-Demand:**
```
contabilizar_documento_manual(empresa_id, ComprobanteManualDTO)
  @transaction.atomic
  1. Idempotencia: AsientoContable.filter(empresa_id, app, modelo, doc_id) → error si existe
  2. _validar_periodo(dto.fecha, empresa_id)
  3. Por cada LineaManual:
     - Buscar CuentaContable(empresa_id, codigo, activa=True)
     - Guard: nivel != 6 → error
     - Armar dict movimiento con cuenta_id, debe, haber
  4. _validar_cuadratura(movimientos, 'APROBADO')  ← partida doble obligatoria
  5. Obtener TipoComprobante(empresa_id, id, activa=True)
  6. tipo_comprobante.obtener_siguiente_numero()  ← side effect: incrementa consecutivo
  7. crud.crear_asiento_manual(empresa_id, data, movimientos) → AsientoContable APROBADO
```

**Asistente IA (Claude Haiku):**
```
sugerir_lineas_asiento_ia(empresa_id, app_label, ctx) → List[dict]
  1. Verificar ANTHROPIC_API_KEY en env
  2. Filtrar CuentaContable nivel=6 activa para empresa_id
  3. filtrar_cuentas_por_app_origen(qs, app_label) → max 50 cuentas
  4. Construir prompt con tipo documento, montos, tercero, cuentas disponibles
  5. anthropic.Anthropic(api_key).messages.create(
       model='claude-haiku-4-5-20251001', max_tokens=1024
     )
  6. json.loads(response.content[0].text)
  7. Por cada cuenta sugerida: DSV → CuentaContable.filter(empresa_id, codigo, nivel=6, activa)
  8. Validar cuadratura: |DEBE - HABER| < 0.01
  9. Retornar lista validada [{cuenta_codigo, cuenta_nombre, debe, haber, descripcion}]
```

---

## 7. API — ViewSets y Endpoints

### 7 ViewSets registrados

| ViewSet | Prefijo | Modelos/Funcion |
|---|---|---|
| `CuentaContableViewSet` | `/api/v1/contabilidad/cuentas-contables/` | CRUD plan de cuentas + HTMX offcanvas |
| `AsientoContableViewSet` | `/api/v1/contabilidad/asientos-contables/` | CRUD asientos + aprobar + reportes + HTMX |
| `MovimientoContableViewSet` | `/api/v1/contabilidad/movimientos-contables/` | CRUD partidas |
| `PeriodoContableViewSet` | `/api/v1/contabilidad/periodos-contables/` | CRUD periodos + cerrar |
| `CatalogoMaestroNIIFViewSet` | `/api/v1/contabilidad/catalogo-niif/` | Catalogo oficial + buscar por tipo |
| `TipoComprobanteViewSet` | `/api/v1/contabilidad/tipos-comprobante/` | CRUD tipos comprobante |
| `DocumentosPendientesViewSet` | `/api/v1/contabilidad/pendientes/` | Lista pendientes + contabilizar manual + asistente IA |

### Endpoints criticos por ViewSet

**`CuentaContableViewSet`**
- `GET /cuentas-contables/?app_origen=gastos` — filtra por `APP_ORIGEN_PREFIJOS`
- `GET /cuentas-contables/render-offcanvas/crear/` — HTML offcanvas crear
- `GET /cuentas-contables/{uuid}/render-offcanvas/editar/` — HTML offcanvas editar
- `GET /cuentas-contables/{uuid}/render-offcanvas/detalle/` — HTML offcanvas detalle

**`AsientoContableViewSet`**
- `POST /asientos-contables/{id}/aprobar/` — cambia estado a APROBADO
- `GET /asientos-contables/reporte-balance-prueba/?fecha_inicio=...&fecha_fin=...`
- `GET /asientos-contables/reporte-estado-resultados/?fecha_inicio=...&fecha_fin=...`
- `GET /asientos-contables/reporte/` — carga template UI de reportes
- `GET /asientos-contables/render-offcanvas/crear/` — HTML offcanvas crear
- `GET /asientos-contables/{uuid}/render-offcanvas/editar/`
- `GET /asientos-contables/{uuid}/render-offcanvas/detalle/`

**`DocumentosPendientesViewSet`**
- `GET /pendientes/?tipo=facturas|gastos|nominas|inventario` — lista documentos pendientes
- `POST /pendientes/contabilizar/` — flujo manual On-Demand
- `POST /pendientes/asistente-ia/` — sugerencia de cuentas via Claude Haiku
- `GET /pendientes/{id}/render-offcanvas/contabilizar/?app_label=...&modelo=...` — HTML formulario

### `ContabilidadServiceMixin(SintelServiceMixin)`

```python
service_class = ContabilidadBusinessService
mutation_lookup_fields = ("id", "uuid")

get_mutation_queryset(model_class, *extra_fields)
  → model_class.objects.only(id, uuid, *extra_fields)
```

---

## 8. Flujos End-to-End Completos

### 8A. Pull Model ETL — Contabilizacion automatica

```
TRIGGER: Celery Beat periodic / manual CLI:
  python manage.py backfill_contabilidad

1. ejecutar_integracion_contable_task(schema_name)
   [Celery @shared_task, tenant-aware via schema_context(schema_name)]
   → with schema_context(schema_name):
       empresa = Empresa.objects.first()
       service = ContabilidadBusinessService()
       resumen = service.ejecutar_integracion_completa(empresa.id)

2. ejecutar_integracion_completa(empresa_id)
   → Instancia 4 extractores: [ExtractorGastos, ExtractorInventario, ExtractorFacturas, ExtractorNomina]
   → Para cada extractor:
       nombre = Extractor.__class__.__name__
       stats = extractor.contabilizar_pendientes()

3. ExtractorGastos.contabilizar_pendientes() [via AbstractExtractor]
   → pendientes = extraer_pendientes()
       → ya_contabilizados = AsientoContable.filter(empresa_id, app='gastos').values_list('documento_origen_id')
       → DocumentoSoporte.filter(empresa_id, anulado=False).exclude(id__in=ya_contabilizados)
       → [_mapear_a_dto(doc) for doc in documentos]

4. Para cada TransaccionEconomica dto:
   Contabilizador(empresa_id).contabilizar(dto)
   → @transaction.atomic
   → _resolver_periodo(dto.fecha) → PeriodoContable
   → validar_periodo_abierto(periodo)
   → _validar_no_existe(dto.documento_origen)
   → _construir_asiento(dto, periodo)
       → ResolverCuentas.resolver_cuenta(concepto, tipo) → PUC via ReglaContable
       → AsientoContable(unsaved) + movimientos_por_guardar
   → validar_no_vacio + validar_cuadratura
   → asiento.save() + movimiento.save() x N

5. Resultado: {contabilizados: N, omitidos: M, errores: [...]}
   → AsientoYaExisteError → omitido (idempotencia, no error)
   → Cualquier otra excepcion → errores[] (loguea, continua)
```

### 8B. Manual On-Demand — Contabilizacion desde UI

```
1. Usuario abre tab "Pendientes" en workspace/#contabilidad
   → pendiente_list.js carga GET /api/v1/contabilidad/pendientes/?tipo=gastos
   → DocumentosPendientesViewSet.list()
   → qs_gastos_pendientes(empresa_id) → JSON [{id, consecutivo, fecha, subtotal, ...}]
   → Tabulator renderiza tabla de documentos pendientes

2. Usuario click "Contabilizar" en fila
   → htmx.ajax GET /api/v1/contabilidad/pendientes/{id}/render-offcanvas/contabilizar/
     ?app_label=gastos&modelo=DocumentoSoporte
   → DocumentosPendientesViewSet.render_offcanvas_contabilizar()
   → get_documento_pendiente('gastos', 'DocumentoSoporte', id, empresa_id) → doc
   → GET /api/v1/contabilidad/cuentas-contables/?app_origen=gastos
   → Render pendiente_offcanvas_contabilizar.html

3. (Opcional) Usuario click "Sugerir con IA"
   → POST /api/v1/contabilidad/pendientes/asistente-ia/
     {app_label, modelo, documento_id, subtotal, impuestos, total, tercero_nit, tercero_nombre}
   → DocumentosPendientesViewSet.asistente_ia()
   → business_service.sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)
   → Claude Haiku API → JSON [{cuenta_codigo, debe, haber, descripcion}]
   → Validacion DSV + cuadratura en backend
   → Frontend rellena las filas del formulario

4. Usuario asigna cuentas PUC manualmente (o acepta sugerencia IA)
   → asiento_cargar_desde_docs.js construye payload
   → POST /api/v1/contabilidad/pendientes/contabilizar/
     {app_label, modelo, documento_id, documento_numero, tipo_comprobante_id,
      fecha, descripcion, lineas: [{cuenta_codigo, debe, haber}]}

5. DocumentosPendientesViewSet.contabilizar()
   → ContabilizarManualInputSerializer.validate()
   → Construir ComprobanteManualDTO
   → business_service.contabilizar_documento_manual(empresa_id, dto)
       1. Idempotencia → error si ya existe asiento
       2. _validar_periodo(fecha)
       3. Por cada LineaManual: buscar cuenta nivel 6
       4. _validar_cuadratura('APROBADO')
       5. tipo_comprobante.obtener_siguiente_numero()
       6. crud.crear_asiento_manual() → AsientoContable APROBADO

6. HTTP 201 → {id, uuid, numero}
   → Frontend: 'asientoCreado' event → replaceData() en tabla pendientes y tabla asientos
```

### 8C. Crear asiento manual desde editor UI

```
1. Usuario click "Nuevo Asiento" en workspace/#contabilidad
   → htmx.ajax GET /api/v1/contabilidad/asientos-contables/render-offcanvas/crear/
   → AsientoContableViewSet.render_offcanvas_crear()
   → Retorna asiento_offcanvas_form.html

2. asiento_editor.js gestiona el formulario:
   - Selector de TipoComprobante (GET /api/v1/contabilidad/tipos-comprobante/)
   - Cada linea: buscar cuenta PUC (GET /cuentas-contables/?search=...)
   - Calculo en tiempo real: DEBE total vs HABER total
   - Guard local: no permite guardar si |DEBE - HABER| >= 0.01

3. Submit → POST /api/v1/contabilidad/asientos-contables/
   {empresa_id, fecha, descripcion, estado, tipo_comprobante_id,
    movimientos: [{cuenta_id, debe, haber, descripcion, tercero_nit, orden}]}

4. AsientoContableViewSet.create()
   → get_empresa_id() [DSV]
   → business_service.crear_asiento(empresa_id, payload)
       1. _validar_periodo → PeriodoCerradoError si aplica
       2. _validar_cuadratura (tolerancia 0.01 si APROBADO)
       3. _validar_cuentas_auxiliares → todas deben ser nivel 6
       4. crud.crear_asiento(empresa_id, payload, movimientos)
   → qs_asiento_detail().get(id) → AsientoContableDetailSerializer
   → HTTP 201

5. Frontend: 'asientoGuardado' → asiento_list.js.replaceData()
```

### 8D. Aprobar asiento

```
1. Tabla asientos: usuario click "Aprobar" → POST /asientos-contables/{id}/aprobar/
2. AsientoContableViewSet.aprobar()
   → get_asiento_by_identifier(id) [DSV empresa_id]
   → business_service.aprobar_asiento(asiento.id)
       → prefetch movimientos existentes
       → _validar_cuadratura(movimientos_data, 'APROBADO')
       → asiento.estado = 'APROBADO'; asiento.save(update_fields=['estado'])
   → HTTP 200 + AsientoContableDetailSerializer
3. Frontend actualiza fila Tabulator via replaceData()
```

### 8E. Reportes financieros

```
1. usuario selecciona fecha_inicio, fecha_fin en reporte.ui.js
2. Balance de Prueba:
   GET /asientos-contables/reporte-balance-prueba/?fecha_inicio=...&fecha_fin=...
   → balance_prueba_selector(empresa_id, fi, ff)
   → Movimientos del periodo por cuenta (sum DEBE / HABER)
   → Saldos anteriores (fecha < fi)
   → Calculo saldo_anterior + nuevo_saldo por naturaleza (D=1,5,6 / C=2,3,4)
   → Lista ordenada por codigo → BalancePruebaOutputSerializer

3. Estado de Resultados:
   GET /asientos-contables/reporte-estado-resultados/?fecha_inicio=...&fecha_fin=...
   → estado_resultados_selector
   → Clase 4 (Ingresos, naturaleza C), Clase 5 (Gastos, D), Clase 6 (Costos, D)
   → utilidad_bruta = ingresos - costos; utilidad_neta = bruta - gastos
   → EstadoResultadosOutputSerializer
```

---

## 9. Tareas Celery

```
ejecutar_integracion_contable_task(schema_name)
  @shared_task
  with schema_context(schema_name):
    empresa = Empresa.objects.first()
    ContabilidadBusinessService().ejecutar_integracion_completa(empresa.id)

integracion_contable_global_task()
  @shared_task (broadcast)
  → TenantModel.exclude(schema_name='public').values_list('schema_name')
  → Para cada schema: ejecutar_integracion_contable_task.delay(schema)
  → Paralelo por tenant, no secuencial
```

**Activacion:** Celery Beat configurado en `config/celery.py`. Tambien invocable via:
```bash
python manage.py backfill_contabilidad
```

---

## 10. Management Commands

```
poblar_catalogo_niif.py
  → Lee CATALOGO_NIIF_COLOMBIA desde choices/choices.py
  → CatalogoMaestroNIIF.update_or_create(codigo, defaults={nombre, nivel, naturaleza, empresa})
  → Idempotente — puede ejecutarse multiple veces

seed_reglas_contables.py
  → Inserta ReglaContable defaults por tipo_transaccion + concepto → cuenta_codigo
  → Cubre: COMPRA_GASTO, VENTA_FACTURA, NOMINA_LIQUIDACION, etc.

backfill_contabilidad.py
  → Ejecuta ExtractorGastos, ExtractorFacturas, ExtractorInventario, ExtractorNomina
  → Equivalente a la tarea Celery pero sincrono en CLI
```

---

## 11. Microtareas Atomicas por Proceso

### `Contabilizador.contabilizar(dto)` — 10 microtareas

```
1.  Abrir @transaction.atomic
2.  _resolver_periodo(fecha) — filter PeriodoContable por rango de fechas
3.  validar_periodo_abierto(periodo) — PeriodoCerradoError si CERRADO
4.  _validar_no_existe(documento_origen) — AsientoYaExisteError si duplicado
5.  _construir_asiento(dto, periodo):
    5a. Crear AsientoContable(unsaved) con numero ASI-{fecha}-{uuid}
    5b. Por cada LineaTransaccion:
        - resolver.resolver_cuenta(concepto, tipo) → PUC codigo (cache + ReglaContable)
        - MovimientoContable principal (lado DEBE o HABER segun linea.lado)
        - Por cada ImpuestoLinea: MovimientoContable impuesto (lado segun impuesto.lado)
        - Acumular debe_total / haber_total
    5c. asiento.movimientos_por_guardar = movimientos
6.  validar_no_vacio(debe_total, haber_total)
7.  validar_cuadratura(debe_total, haber_total) — AsientoNoCuadradoError si diferencia
8.  asiento.save()
9.  Para cada movimiento: movimiento.asiento = asiento; movimiento.save()
10. Commit transaccion — retornar AsientoContable
```

### `contabilizar_documento_manual(empresa_id, dto)` — 9 microtareas

```
1.  Abrir @transaction.atomic
2.  Idempotencia: AsientoContable.filter(empresa_id, app, modelo, doc_id).exists() → error
3.  _validar_periodo(dto.fecha) — verifica periodo no cerrado
4.  Por cada LineaManual:
    4a. CuentaContable.filter(empresa_id, codigo, activa=True)
    4b. Guard: cuenta.nivel != 6 → error
    4c. Armar dict {cuenta_id, cuenta_codigo, debe, haber, descripcion, tercero_*}
5.  _validar_cuadratura(movimientos, 'APROBADO') — |DEBE - HABER| < 0.01
6.  TipoComprobante.filter(empresa_id, id, activa=True) → obtener_siguiente_numero()
    (side effect: incrementa consecutivo_actual en BD)
7.  crud.crear_asiento_manual(empresa_id, data, movimientos) → AsientoContable APROBADO
8.  Commit transaccion
9.  Retornar {id, uuid, numero}
```

### `sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)` — 8 microtareas

```
1.  Verificar import anthropic y ANTHROPIC_API_KEY env
2.  CuentaContable.filter(empresa_id, activa=True, nivel=6).only(codigo, nombre, tipo)
3.  filtrar_cuentas_por_app_origen(qs, app_label) → max 50 cuentas contextuales
4.  Construir prompt (tipo documento, montos, tercero, lista cuentas)
5.  anthropic.Anthropic(api_key).messages.create(model='claude-haiku-4-5-20251001')
6.  json.loads(response.content[0].text) — limpiar markdown si presente
7.  Por cada cuenta sugerida: DSV → CuentaContable.filter(empresa_id, codigo, nivel=6, activa)
8.  validar cuadratura sugerida: |DEBE - HABER| < 0.01 → error si no cuadra
```

### `aprobar_asiento(asiento_id)` — 5 microtareas

```
1.  AsientoContable.prefetch_related('movimientos').get(id=asiento_id)
2.  Armar lista [{cuenta_id, debe, haber}] desde movimientos existentes
3.  _validar_cuadratura(lista, 'APROBADO') — diferencia < 0.01
4.  asiento.estado = 'APROBADO'; asiento.save(update_fields=['estado'])
5.  Retornar {id, estado}
```

### `AbstractExtractor.contabilizar_pendientes()` — 6 microtareas

```
1.  extraer_pendientes() — consultar ya_contabilizados ids
2.  Queryset documentos excluidos los ya contabilizados
3.  [_mapear_a_dto(doc) for doc in documentos] — construir DTOs
4.  Para cada dto: Contabilizador.contabilizar(dto)
    → Exito: contabilizados += 1
    → AsientoYaExisteError: omitidos += 1 (idempotente)
    → Otra excepcion: errores.append({doc, error})
5.  Continua con el siguiente (no bloquea el batch)
6.  Retornar {contabilizados, omitidos, errores, total}
```

---

## 12. Dependencias

```
Contabilizador
  ├── ResolverCuentas
  │   └── ReglaContable (DB)
  │   └── TarifaImpuesto (DB)
  ├── validadores.py (stateless)
  ├── excepciones.py
  └── models: AsientoContable, MovimientoContable, PeriodoContable

AbstractExtractor
  ├── Contabilizador
  └── apps fuente (via import local):
      ├── gastos.models.DocumentoSoporte
      ├── facturas.models.Factura
      ├── empleados.models.Devengo
      └── inventario.models.MovimientoInventario

ContabilidadBusinessService
  ├── ContabilidadCRUDService (crud_service.py)
  ├── selectors.py
  ├── AbstractExtractor + 4 implementaciones
  └── anthropic (opcional — solo si ANTHROPIC_API_KEY configurada)

ViewSets
  ├── BaseTenantViewSet
  ├── SintelDSVMixin (get_empresa_id())
  ├── SintelServiceMixin (service = ContabilidadBusinessService())
  ├── ContabilidadBusinessService
  ├── selectors.py (todos los qs_* y get_*_by_identifier)
  ├── 15+ serializers
  ├── IsTenantMember, IsTenantAdminOrReadOnly
  └── StandardResultsSetPagination

Frontend
  ├── window.TabulatorFactory
  ├── window.UIManager
  ├── window.http
  ├── htmx (CDN)
  └── APIs: asiento.api.js, cuenta.api.js, periodo.api.js, reporte.api.js
```

---

## 13. Eventos y Side Effects

| Evento | Origen | Efecto |
|---|---|---|
| `asientoGuardado` | JS post-save | `asiento_list.js.replaceData()` |
| `asientoEliminado` | JS post-delete | `asiento_list.js.replaceData()` |
| `cuentaGuardada` | JS post-save | `cuenta_list.js.replaceData()` |
| `periodoGuardado` | JS post-save | `periodo_list.js.replaceData()` |
| `documentoContabilizado` | JS post-contabilizar | `pendiente_list.js.replaceData()` + `asiento_list.js.replaceData()` |
| `htmx:afterSettle` | HTMX | `UIManager.handleOffcanvas('show')` |
| `TipoComprobante.obtener_siguiente_numero()` | Cada contabilizacion manual | `UPDATE tipo_comprobante SET consecutivo_actual += 1` |
| `Celery Beat` | Programado | `integracion_contable_global_task` → N tareas individuales |

**Sin Signals Django** — todo via Service Layer explicito.

---

## 14. Riesgos Tecnicos Detectados

### CRITICO — `ejecutar_integracion_completa` corre 4 extractores en secuencia, no en paralelo

`ContabilidadBusinessService.ejecutar_integracion_completa()` itera `[ExtractorGastos, ExtractorInventario, ExtractorFacturas, ExtractorNomina]` secuencialmente. Si hay 1000 facturas pendientes y 500 gastos, el tiempo de ejecucion es O(n) sin paralelismo. Cada extractor abre su propia transaccion, pero no se solapan.

**Solucion recomendada:** Lanzar cada extractor como subtarea Celery separada con `group()`.

### CRITICO — `_resolver_periodo` puede fallar silenciosamente en el Pull Model

Si no existe `PeriodoContable` para la fecha del documento, `_resolver_periodo` lanza `ValueError` (no `PeriodoCerradoError`). `AbstractExtractor.contabilizar_pendientes()` captura `Exception` generico, lo manda a `errores[]` y continua. El documento queda perpetuamente pendiente sin alerta visible al usuario.

### MEDIO — `get_balance_prueba` en selectors.py tiene N+1 query potencial

`get_balance_prueba` itera sobre cuentas nivel 6 y por cada una llama a `calcular_saldos_cuenta(cuenta.id)`. Con 200 cuentas auxiliares, genera 200+ queries. Debe reemplazarse con un `annotate()` sobre movimientos agrupados por cuenta.

### MEDIO — `TipoComprobante.obtener_siguiente_numero()` no es atomico bajo concurrencia

`obtener_siguiente_numero()` hace `.save(update_fields=['consecutivo_actual'])` sin `select_for_update()`. Bajo concurrencia (dos usuarios creando asientos simultaneamente), puede generar numeros duplicados de comprobante.

**Solucion:** `TipoComprobante.objects.select_for_update().get(id=...)` antes de incrementar.

### MEDIO — `CuentaContableViewSet.create()` llama `crud` directamente, bypasea `business_service`

Linea `resultado = self.service.crud.crear_cuenta(...)` accede al CRUD directamente en el ViewSet, sin pasar por `business_service.crear_cuenta()` que hace la validacion de unicidad de codigo. Hay un `TODO: v3.5` comentado al respecto.

### BAJO — `SMMLV_2026` hardcodeado en `resolver.py`

`SMMLV_2026 = Decimal('1315000')` esta hardcodeado. Comentado como `TODO: Link to salary_master.SMMLVHistorico`. Si el salario minimo cambia, el umbral de exoneracion de parafiscales es incorrecto.

### BAJO — Doble campo `debe_total`/`total_debe` en `AsientoContable`

El modelo tiene `debe_total`, `haber_total` (nuevos) y `total_debe`, `total_haber` (legado, `editable=False`). El metodo `save()` sincroniza los legados con los nuevos. Es deuda tecnica — los selectors usan `total_debe`/`total_haber` (legado) pero los calculos usan `debe_total`/`haber_total`. Riesgo de inconsistencia si alguien no llama a `save()`.

---

## 15. Conformidad con AGENTS.md

| Regla | Estado |
|---|---|
| `SintelTenantBaseModel` | PASS — 8 modelos heredan correctamente |
| `empresa_id` en toda query | PASS — todos los selectors y DSV filtran por empresa_id |
| `.only()` obligatorio | PASS — todos los qs_* usan LIST_FIELDS/DETAIL_FIELDS |
| `select_related` / `prefetch_related` | PASS — cuentas_vinculadas, movimientos, cerrado_por |
| Sin imports directos de `apps.public` | PASS |
| Pull Model (no Push) | PASS — apps fuente no importan de contabilidad |
| `AsientoContable` solo via `Contabilizador` o `business_service` | PASS |
| `lookup_field = "uuid"` | PARCIAL — los ViewSets soportan id/uuid en `get_*_by_identifier` pero no como `lookup_field` nativo de DRF |
| Permisos desde `apps.tenant.api.permissions` | PASS |
| Sin Signals | PASS — ningun signals.py |
| Celery tasks tenant-aware | PASS — `schema_context(schema_name)` en task |
