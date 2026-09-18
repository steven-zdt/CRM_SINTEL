# AUDITORIA_FLUJO_COMPLETO.md — Bancos

## Fecha: 2026-06-04 (actualizado 2026-09-14)
## Modulo: tenant/bancos
## Version: v3.0 — Importacion Multiformato + Aplicaciones Multiples + Matching (motor operativo)

---

## v3.0 (2026-09-14) — Motor operativo `IMPORTAR -> NORMALIZAR -> CLASIFICAR -> SUGERIR -> VINCULAR -> APLICAR -> CONCILIAR`

**Estado honesto: READY FOR TESTING (no "PRODUCTION READY").** Verificado con
evidencia real (fixture bancario real, no sintetico) para lo que SI se
construyo; varios items de la mision original quedaron DEFERRED de forma
explicita (ver tabla al final de esta seccion) -- no se fabrico una
funcionalidad que no existe.

**Verificado:** `pytest apps/tenant/bancos/tests/` completo -> **58 passed,
0 failed** (15 preexistentes sin regresion + 43 nuevos: parser monetario,
importador XLSX contra el fixture real, CSV, validacion de balance,
aplicaciones multiples, matching service, aislamiento cross-tenant, KPIs).
1 bug real encontrado y corregido durante esta verificacion:
`Coalesce(Sum(...), 0)` en el KPI de `render_offcanvas_detalle` mezclaba
`DecimalField`/`IntegerField` sin `output_field` -> 500 real, reproducido
por el test `test_render_offcanvas_detalle_incluye_kpis_fase19`, corregido
con `Value(Decimal("0.00"), output_field=DecimalField())`.

### Que cambio (evolutivo, no reescritura -- se conservo todo lo de v2.0)

1. **Parser monetario robusto** (`services/parsing/money.py`): `parse_money()`
   unico punto de normalizacion, siempre `Decimal`. Soporta formato US
   (coma=miles, punto=decimal, el que usa el extracto real) y formato
   colombiano (punto=miles, coma=decimal), simbolos de moneda y parentesis
   contables. Verificado contra los 7 casos exactos de la mision + edge
   cases (`tests/test_money_parser.py`).

2. **Arquitectura de importacion desacoplada del formato**
   (`services/importers/`): `BankStatementImporter` (ABC) ->
   `XLSXBankStatementImporter` / `CSVBankStatementImporter` /
   `XMLBankStatementImporter`. DTOs internos `NormalizedBankStatement` /
   `NormalizedBankTransaction`. `get_importer_for(nombre_archivo)` selecciona
   por extension; extension desconocida -> `UnsupportedFormatError`
   controlado (nunca 500).
   - **XLSX**: reutiliza la estrategia YA probada en produccion (escanear
     cada fila buscando el patron de fecha corta `D/M`, ignora
     automaticamente titulos/bloques repetidos/"FIN ESTADO DE CUENTA" sin
     asumir posicion fija), + deteccion dinamica de columnas por encabezado
     real (fallback al layout por defecto si no se encuentra) + extraccion
     best-effort del bloque "Resumen:" (saldo anterior, total abonos/cargos,
     saldo actual).
   - **CSV**: `csv.Sniffer` + fallback manual para `,`/`;`/tab, BOM UTF-8,
     decimales colombianos/americanos via `parse_money`, encabezados por
     alias (FECHA/DATE, DESCRIPCION/DETALLE/CONCEPTO, VALOR/MONTO/AMOUNT...).
   - **XML**: contrato/adapter (`XMLBankStatementImporter.importar()` ->
     `NormalizedBankStatement`, mismo shape que XLSX/CSV) sin parser real --
     no existe hoy un esquema XML bancario de referencia disponible para
     este proyecto. `STATUS = UNSUPPORTED_FORMAT` controlado, no rompe el
     resto del sistema. `ADAPTERS_POR_BANCO` preparado para Fase 27
     (agregar un banco = una subclase, sin tocar el resto).

3. **Validacion de balance obligatoria** (Fase 1): `saldo_inicial (derivado
   de la primera fila) + creditos - debitos == saldo_final (ultima fila)`,
   tolerancia `Decimal("0.01")`. Format-agnostica (se deriva de los propios
   movimientos, no depende de que el archivo exponga un bloque resumen). Si
   falla, `ValidationError` -> 422, `extracto.procesado` NUNCA se marca
   `True`. `ExtractoBancario.saldo_inicial/saldo_final` ahora se
   autocompletan desde el archivo procesado (antes eran solo un input manual
   del usuario en la creacion, casi siempre en 0.00).

4. **`MovimientoBancarioAplicacion`** (modelo nuevo, migracion `0007`):
   `TransaccionBancaria` 1->N aplicaciones. 12 `tipo_referencia` (soft-ref
   UUID, `referencia_uuid` opcional -- permite `OTRO`/`referencia_uuid=None`
   para clasificar sin bloquear, Fase 30). Guard de sobreaplicacion real
   (`select_for_update` sobre la transaccion + suma de aplicaciones
   existentes, tolerancia 0.01) en creacion Y edicion. **Deliberadamente
   NO dispara ningun efecto lateral cross-app** (Cartera, estado_pago) --
   ese automatismo sigue siendo EXCLUSIVO del vinculo legado 1:1
   (`conciliar_transaccion()`, sin tocar, mismos tests v2.0 en verde). Unico
   punto de acoplamiento entre ambos mecanismos: `conciliado` solo ASCIENDE
   a `True` cuando el 100% del movimiento queda aplicado via el nuevo
   modelo -- nunca lo revierte a `False` (evita pisar un vinculo legado ya
   completo).

5. **`BankTransactionMatchingService`** (`services/matching_service.py`):
   solo lectura, nunca escribe. CREDITO -> Factura VENTA + Cliente; DEBITO ->
   Factura COMPRA + Proveedor + `DocumentoSoporte` (el "Gasto" real del
   proyecto -- no existe un modelo `Gasto` propiamente dicho, ver
   `apps/tenant/gastos/models.py`). Score ponderado: documento bancario
   (dcto) > NIT en descripcion > nombre/razon social > numero de documento >
   monto (exacto/~5%) > proximidad de fecha.

6. **Endpoints nuevos** (`TransaccionBancariaViewSet`):
   `GET /transacciones/{uuid}/sugerencias/`,
   `GET|POST /transacciones/{uuid}/aplicaciones/`. ViewSet nuevo
   `MovimientoBancarioAplicacionViewSet` -> `GET|PATCH|DELETE
   /aplicaciones/{uuid}/`. `POST .../procesar/` ahora acepta
   `{"forzar": true}` (Fase 24 -- bloquea reprocesar un extracto con
   transacciones ya conciliadas/con aplicaciones salvo `forzar` explicito) y
   devuelve un resultado real (`filas_leidas/importadas/omitidas`, totales,
   formato) en vez de un mensaje generico.

7. **Frontend**: Paso 5 nuevo en `offcanvas_detalle_extracto.html` (barra
   aplicado/pendiente, lista de aplicaciones con quitar, alta con selector
   de 12 tipos + boton "Sugerir" que trae candidatos clicables). `bancos.api.js`
   SSoT ampliado (`sugerencias`, `listarAplicaciones`, `crearAplicacion`,
   `aplicaciones.editar/eliminar`). Sigue usando `window.Sintel.Core.Http`
   (el wrapper real que usa este modulo -- no `window.http()` directo, que
   es lo que documentaba la mision generica; se siguio el codigo real, no la
   suposicion).

### Validado contra el extracto real `10800014844_AGO2026.xlsx`

```
60 movimientos (24 creditos, 36 debitos)         -- OK, exacto
Creditos:  $8.656.342,15   Debitos: $9.633.350,20  -- OK, exacto
Saldo inicial: $986.830,85 -> Saldo final: $9.822,80 -- OK, exacto
Balance interno (inicial + creditos - debitos = final) -- OK, cuadra exacto
```
Ver `apps/tenant/bancos/tests/test_import_xlsx_real_fixture.py`.

### v3.0.1 (2026-09-14) — Confirmacion: ya consume el contrato nuevo de Facturas (Fase 12/13 "PROMPT MAESTRO")

La mision de reestructuracion de `facturas` (v4.0.0) elimino `BancosBridge` y
`FacturaInterAppAPI.recalcular_estado_pago_automatico()` del lado de Facturas
(Bancos->Facturas de escritura). Se audito el codigo real de Bancos para
confirmar si requeria un rediseño -- **no lo requiere**: el unico punto de
contacto de Bancos con Facturas ya era, desde que se escribio v3.0 en esta
misma sesion, una lectura pura via `FacturaInterAppAPI.get_by_id()`
(`services/crud_service.py::conciliar_transaccion()`, solo para validar que
la fecha del pago no sea anterior a la fecha de emision del documento -- REM
P1-04). Bancos nunca escribio en `Factura`; el estado de conciliacion vive
enteramente en el dominio de Bancos (`TransaccionBancaria.conciliado` +
`MovimientoBancarioAplicacion`). Se removio unicamente la llamada al metodo
de escritura eliminado en Facturas (el disparo del abono en Cartera, una
integracion Bancos->Clientes independiente, se mantuvo intacto). Verificado
con `pytest apps/tenant/bancos/tests/` completo tras el cambio: **58 passed,
0 failed** -- mismo resultado que antes, sin regresion. Fase 12/13 del
"PROMPT MAESTRO" ("rediseñar/migrar Bancos al nuevo contrato de Facturas")
se da por **satisfecha sin cambios adicionales**, ya que el contrato ya
cumplido era el correcto desde el diseño original de v3.0.

### Fix de alineacion frontend<->backend (2026-09-14, hallazgo real de esta pasada)

Sincronizando el frontend contra el backend tras Fase 2/3 de la mision de
Facturas se encontro un gap real, preexistente, no relacionado con esa
mision: el endpoint `POST /extractos/{uuid}/procesar/` (Fase 24, importacion
no destructiva) rechaza con 422 reprocesar un extracto que ya tiene
transacciones conciliadas/aplicaciones, pidiendo reintentar con
`{"forzar": true}` en el body -- pero `bancos.api.js::extractos.procesar()`
nunca aceptaba ni enviaba ese parametro, y ni `extracto_editor.js` (boton
"Procesar" del panel detalle) ni `extracto_list.js` (accion de fila) ofrecian
al usuario una forma de reintentar: el 422 se mostraba como error terminal
sin salida. Corregido: `procesar(uuid, forzar=false)` ahora envia
`{forzar}`; ambos callers detectan el 422 con el mensaje "forzar=true" del
backend, muestran `confirm()` con el mensaje real del servidor, y reintentan
con `forzar=true` si el usuario acepta. Verificado con `node --check` sobre
los 3 archivos (sin runtime de navegador disponible en este pase, ver nota
de Fase 35 abajo).

### DEFERRED explicito (no fabricado, documentado para una fase posterior)

| Item | Por que se deja fuera |
|---|---|
| XML real (Fase 2/27) | No hay esquema XML bancario de referencia disponible en este proyecto -- el adapter/contrato SI esta listo. |
| Transferencias entre cuentas propias, vinculo de 2 movimientos (Fase 13) | Requiere UI/servicio propio (buscar el movimiento espejo en otra `CuentaBancaria`) -- `TRANSFERENCIA_INTERNA` ya existe como `tipo_referencia` aplicable individualmente, falta el vinculo par-a-par. |
| Previsualizacion de efecto contable / "Ver efecto contable" (Fase 23) | Requiere leer la logica real de determinacion de cuenta de Contabilidad (`APP_ORIGEN_PREFIJOS`) para no inventar cuentas -- fuera de alcance de esta pasada. |
| Resolver nombres reales para vinculos legados pre-existentes (BAN-06/07, deuda ya documentada en v2.0) | Sigue igual -- el nuevo panel de Aplicaciones SI resuelve nombre humano en el momento de crear (desde la sugerencia elegida), pero al recargar una aplicacion ya guardada solo muestra `tipo_referencia_display` + notas + UUID truncado (mejor que v2.0, no perfecto). |
| Click-through real en navegador (Fase 35) | Igual que el resto del proyecto (ver AI-UI-01, Mail Hub) -- sandbox del asistente no permite abrir un navegador real contra el dominio del tenant. Verificado via API real (pytest + DRF test client) en su lugar. |
| Bancos hardcodeados por adapter especifico (Fase 27) | Solo existe el layout generico (verificado contra Bancolombia); `ADAPTERS_POR_BANCO` esta preparado pero vacio -- no se inventaron adapters para bancos sin fixture real. |

---

## v2.0 (2026-06-04, Fix B-1 2026-09-12) — historico, preservado abajo

```
Score Global:     10/10 (2026-06-04) -- 1 hallazgo ALTO nuevo encontrado y
                   corregido 2026-09-12 (B-1), ver seccion abajo. Verificado:
                   pytest apps/tenant/bancos/tests/ completo -> 14 passed
                   (sin regresion) + 1 test nuevo -> 1 passed.
Status:           PRODUCTION READY ✅ (fix B-1 aplicado y verificado, alcance v2.0)
Hallazgos:        0 criticos | 0 importantes | 2 menores (heredados v1.0)
Conformidad:      AGENTS.md §4, §5, §13, §14, §18, §24, §26, §27, §29, §30, §31
Migraciones:      0001 → 0007 (7 aplicadas, public + todos los tenants -- 0007 agrega MovimientoBancarioAplicacion, v3.0)
```

## 2026-09-12 — Fase 2 de remediación: B-1 (ALTO, `docs/remediation/AUDIT_BASELINE_20260912.md`)

**✅ Verificado.** `pytest apps/tenant/bancos/tests/` completo → **14 passed**
(suite preexistente, cero regresión) + `test_b1_resolucion_empresa_id_fallback.py`
(nuevo, mockea `get_empresa_id()` para lanzar `AttributeError`) → **1 passed**.

Auditoría "Bancos — extractos, causación, CRUD" (parte de
`docs/remediation/AUDIT_BASELINE_20260912.md`) trazó la cadena completa
subir→persistir→refresh HTMX→listar extracto y la encontró correctamente
cableada en todos sus eslabones (contrario al síntoma reportado
originalmente). El único punto de fragilidad real encontrado: en
`_BancosTableViewBase._resolver_empresa_id()` (`views.py`) — la vista
server-rendered que realmente maneja la UI de extractos/cuentas (Fase
5-BIS) — solo atrapaba `DRFValidationError`, a diferencia del path de
creación (API), que usa `BaseServiceMixin._get_empresa_id_seguro()` y cae
a un fallback amplio (cualquier excepción → singleton `Empresa`). Si la
resolución de `empresa_id` fallaba por cualquier otro motivo justo en el
GET que repuebla el panel (ej. justo después de subir un extracto), la
tabla caía silenciosamente a queryset vacío sin ningún error visible,
aunque la fila existiera en BD — coincide con el síntoma "subí el extracto
y no aparece". **Fix**: `_resolver_empresa_id()` ahora replica el mismo
fallback amplio (atrapa cualquier excepción, cae al singleton `Empresa`).

**También confirmado en la misma auditoría (no re-abrir)**: ADR-001
respetado — `conciliar_transaccion()` nunca instancia `AsientoContable`/
`MovimientoContable` directamente, solo dispara las APIs propias de
`facturas`/`clientes` (Pull Model). El doc `.agent` sigue describiendo
Tabulator en §1/§5 (línea ~78, ~368+) mientras el código real ya migró a
django-tables2+HTMX (Fase 5-BIS) — deuda documentada preexistente
(hallazgo B-6 del baseline), no corregida en esta pasada por estar fuera
de los 8 ALTO priorizados.

---

## CHANGELOG v1.0 → v2.0

| ID | Tipo | Descripcion |
|---|---|---|
| **CON-01** | Feature | Conciliacion bancaria manual: `factura_uuid`, `proveedor_uuid`, `cliente_uuid`, `conciliado` en `TransaccionBancaria` |
| **CON-02** | Feature | Campo `notas_conciliacion` (TextField) para trazabilidad contable |
| **CON-03** | Feature | Endpoint PATCH `/conciliar/` — guarda vinculos en BD atomicamente |
| **CON-04** | Feature | Endpoints autocomplete: `search-facturas`, `search-proveedores`, `search-clientes` |
| **CON-05** | Feature | Columna "Conciliacion" en `extracto_list.js` con barra de progreso y conteo X/Y |
| **CON-06** | Feature | Boton "Conciliar" en acciones de extracto (solo cuando hay pendientes) |
| **CON-07** | Feature | Offcanvas detalle rediseñado: layout Split (transacciones | panel conciliacion 4 pasos) |
| **CON-08** | Feature | Flujo ciclico guiado: Paso 1 (TX) → Paso 2 (Factura) → Paso 3 (Tercero) → Paso 4 (Notas) |
| **CON-09** | Feature | Auto-deteccion INGRESO/EGRESO segun valor +/- |
| **CON-10** | Feature | Auto-filtro Factura: INGRESO → tab Venta, EGRESO → tab Compra |
| **CON-11** | Feature | Auto-visibilidad Tercero: INGRESO → Cliente, EGRESO → Proveedor |
| **CON-12** | Feature | Valores +/- en tabla: verde (+$) para ingresos, rojo (-$) para egresos |
| **CON-13** | Feature | Filtros rapidos en tabla: Todos / Ingresos / Egresos / Sin conciliar |
| **FIX-01** | Bugfix | `filterset_fields = ["tipo_movimiento"]` — `tipo_movimiento` es @property, causaba 500. Removido DjangoFilterBackend, filtros manuales en `get_queryset()` |
| **FIX-02** | Bugfix | Template usaba `id="oc-extracto-det"` pero `extracto_editor.js` buscaba `id="offcanvas-extracto-detalle"` — offcanvas nunca se mostraba |
| **FIX-03** | Bugfix | `search_facturas` filtraba `tipo='VENTA'` pero el campo correcto es `naturaleza='VENTA'` (`tipo` contiene 'FE'/'NC'/'ND') |
| **FIX-04** | Bugfix | `conciliar_transaccion()` solo incluia `factura_uuid`, `proveedor_uuid` — `cliente_uuid` y `notas_conciliacion` ignorados |
| **ANN-01** | Enhancement | `ExtractoBancarioSelector.get_list()` anota `total_transacciones` y `tx_conciliadas` via `Count()` |

---

## 1. ARQUITECTURA GENERAL

### Proposito del Modulo

`apps/tenant/bancos` gestiona la **conciliacion bancaria** de cada tenant:
- Registro de cuentas bancarias propias de la empresa
- Importacion de extractos bancarios en formato Excel
- ETL automatico: parsing → validacion → bulk insert de transacciones
- Visualizacion de movimientos con formato +/- (ingresos / egresos)
- **Conciliacion manual**: vinculacion de cada transaccion bancaria con Facturas, Proveedores y Clientes del mismo tenant via soft references (UUID, Bounded Context §18)

### Modelos — Jerarquia

```
Empresa (singleton por schema)
    └── CuentaBancaria
         └── ExtractoBancario   (extracto mensual, un archivo Excel por periodo)
              └── TransaccionBancaria  (lineas del extracto, creadas por ETL)
                  ├── factura_uuid     (soft ref → Factura, Bounded Context §18)
                  ├── proveedor_uuid   (soft ref → Proveedor)
                  ├── cliente_uuid     (soft ref → Cliente)
                  ├── conciliado       (bool)
                  └── notas_conciliacion (texto libre, trazabilidad contable)
```

### Stack Tecnico

| Capa | Tecnologia |
|---|---|
| Backend | Django 5 + DRF + django-tenants |
| Base de datos | PostgreSQL multi-schema |
| Autenticacion | Dual-Auth: JWT + Session (BaseTenantViewSet) |
| Frontend | Vanilla JS ES6 + HTMX 1.9.10 + Tabulator 6.2.5 + Bootstrap 5.3.2 |
| File upload | multipart/form-data → S3/Local FileField |
| ETL | pandas + openpyxl para parsing de Excel bancario |

---

## 2. MODELOS (`models.py`)

### 2.1 CuentaBancaria

```python
class CuentaBancaria(SintelTenantBaseModel):
    uuid    = UUIDField(unique=True, db_index=True, editable=False)
    nombre  = CharField(max_length=100)
    banco   = CharField(max_length=100)     # choices via ViewSet context
    tipo    = CharField(max_length=50)       # CORRIENTE | AHORROS
    numero  = CharField(max_length=50)

    class Meta:
        db_table = "bancos_cuenta_bancaria"
        indexes  = [Index(fields=["empresa", "numero"])]
```

### 2.2 ExtractoBancario

```python
class ExtractoBancario(SintelTenantBaseModel):
    uuid          = UUIDField(unique=True, db_index=True, editable=False)
    cuenta        = ForeignKey(CuentaBancaria, on_delete=CASCADE, related_name="extractos")
    mes           = IntegerField(choices=MES_CHOICES)   # 1-12, choices habilitados (get_mes_display OK)
    anio          = IntegerField()
    archivo_s3    = FileField(upload_to="extractos/", null=True, blank=True)
    procesado     = BooleanField(default=False)
    saldo_inicial = DecimalField(max_digits=15, decimal_places=2, default=0.00)
    saldo_final   = DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        db_table = "bancos_extracto_bancario"
        indexes  = [Index(fields=["empresa", "cuenta", "anio", "mes"])]
```

**Nota v2.0:** `mes` ya tiene `choices=MES_CHOICES` — `{{ extracto.get_mes_display }}` funciona correctamente (OBS-02 v1.0 resuelto via mig 0003).

### 2.3 TransaccionBancaria

```python
class TransaccionBancaria(SintelTenantBaseModel):
    uuid        = UUIDField(unique=True, db_index=True, editable=False)
    extracto    = ForeignKey(ExtractoBancario, on_delete=CASCADE, related_name="transacciones")
    fecha       = DateField()
    descripcion = TextField()
    sucursal    = CharField(max_length=100, null=True, blank=True)
    dcto        = CharField(max_length=50, null=True, blank=True)
    valor       = DecimalField(max_digits=15, decimal_places=2)  # negativo=DEBITO, positivo=CREDITO
    saldo       = DecimalField(max_digits=15, decimal_places=2)

    # ── Conciliacion bancaria — Bounded Context §18 (soft refs, no FK directa) ──
    factura_uuid        = UUIDField(null=True, blank=True, db_index=True)   # mig 0003
    proveedor_uuid      = UUIDField(null=True, blank=True, db_index=True)   # mig 0003
    cliente_uuid        = UUIDField(null=True, blank=True, db_index=True)   # mig 0004
    conciliado          = BooleanField(default=False)                       # mig 0003
    notas_conciliacion  = TextField(null=True, blank=True)                  # mig 0005

    # ── Propiedades calculadas ────────────────────────────────────────────────
    @property
    def tipo_movimiento(self):
        return 'DEBITO' if self.valor < Decimal('0') else 'CREDITO'

    @property
    def monto(self):
        return abs(self.valor)

    class Meta:
        db_table = "bancos_transaccion_bancaria"
        ordering = ["-fecha", "-created_at"]
        indexes  = [
            Index(fields=["empresa", "extracto"]),
            Index(fields=["empresa", "fecha"]),
        ]
```

**CRITICO:** `tipo_movimiento` y `monto` son `@property` — NO son campos de BD.
- `tipo_movimiento` NO puede usarse en `filterset_fields` (causa TypeError 500)
- El filtro se implementa manualmente: `DEBITO → filter(valor__lt=0)`, `CREDITO → filter(valor__gte=0)`

### 2.4 Migraciones

| # | Archivo | Contenido |
|---|---|---|
| 0001 | `initial.py` | `CuentaBancaria`, `ExtractoBancario`, `TransaccionBancaria` base |
| 0002 | `extractobancario_saldo_final_and_more.py` | `saldo_inicial`, `saldo_final` en `ExtractoBancario` |
| 0003 | `add_conciliacion_and_mes_choices.py` | `factura_uuid`, `proveedor_uuid`, `conciliado` en TX; `choices` en `mes` |
| 0004 | `transaccion_add_cliente_uuid.py` | `cliente_uuid` en `TransaccionBancaria` |
| 0005 | `transaccion_add_notas_conciliacion.py` | `notas_conciliacion` en `TransaccionBancaria` |

---

## 3. SERVICE LAYER

### 3.1 Selectors (`services/selectors.py`)

```python
from django.db.models import Count, Q

class ExtractoBancarioSelector:
    @staticmethod
    def get_list(empresa_id, cuenta_uuid=None, search=None):
        qs = (
            ExtractoBancario.objects
            .filter(empresa_id=empresa_id)
            .select_related("cuenta")
            .only(*EXTRACTO_LIST_FIELDS)
            .annotate(
                total_transacciones=Count('transacciones'),
                tx_conciliadas=Count('transacciones', filter=Q(transacciones__conciliado=True)),
            )
        )
        ...
```

**v2.0:** `get_list()` anota `total_transacciones` y `tx_conciliadas` en una sola query (sin N+1).
El serializer calcula `tx_pendientes = total_transacciones - tx_conciliadas`.

### 3.2 CRUD Service (`services/crud_service.py`)

```
CuentaBancariaCRUDService
    crear_cuenta(data, empresa)         @atomic — valida numero unico, full_clean(), save()
    editar_cuenta(cuenta, data)         @atomic — setattr loop, full_clean(), save()
    eliminar_cuenta(cuenta)             @atomic — bloquea si tiene extractos

ExtractoBancarioCRUDService
    crear_extracto(data, empresa)       @atomic — valida (empresa, cuenta, mes, anio) unico
    eliminar_extracto(extracto)         @atomic — CASCADE transacciones

TransaccionBancariaCRUDService
    crear_transacciones_bulk(list, extracto, empresa)    @atomic — bulk_create ETL
    conciliar_transaccion(transaccion, data)             @atomic — v2.0
```

**v2.0 — `conciliar_transaccion(transaccion, data)`:**
```python
CAMPOS_CONCILIACION = (
    "factura_uuid", "proveedor_uuid", "cliente_uuid",
    "conciliado", "notas_conciliacion"
)
for field in CAMPOS_CONCILIACION:
    if field in data:
        setattr(transaccion, field, data[field])
        campos_a_guardar.append(field)
transaccion.save(update_fields=campos_a_guardar)
```
- Solo guarda los campos presentes en `data` (update minimo)
- Log completo con uuid, factura, proveedor, cliente, conciliado

### 3.3 Business Service (`services/business_service.py`)

Sin cambios respecto a v1.0. Ver flujo ETL en §8.

### 3.4 API Mixins (`services/api_mixins.py`)

```python
class TransaccionBancariaServiceMixin(BaseServiceMixin):
    # v2.0: agrega bridge para conciliacion
    service_conciliar_transaccion(transaccion, data)
        → TransaccionBancariaCRUDService.conciliar_transaccion(transaccion, data)
```

---

## 4. API LAYER

### 4.1 ViewSets (`api/viewsets.py`)

#### CuentaBancariaViewSet — sin cambios v1.0

#### ExtractoBancarioViewSet

**v2.0 — `render_offcanvas_detalle` enriquecido:**
```python
@action(detail=True, methods=["get"], url_path="render-offcanvas/detalle")
def render_offcanvas_detalle(self, request, uuid=None):
    extracto = self.get_object()
    transacciones = (
        extracto.transacciones
        .only('id','uuid','fecha','descripcion','sucursal','dcto',
              'valor','saldo','conciliado',
              'factura_uuid','proveedor_uuid','cliente_uuid',
              'notas_conciliacion','empresa_id')
        .order_by('-fecha', '-created_at')
    )
    context = {
        "extracto": extracto,
        "transacciones": transacciones,   # ← v2.0: pre-cargadas con .only()
        "empresa_id": empresa_id,
    }
```

#### TransaccionBancariaViewSet (v2.0)

```
Herencia  : TransaccionBancariaServiceMixin → SintelDSVMixin → BaseTenantViewSet
Metodos   : ["get", "patch", "head", "options"]  ← v2.0: agrega PATCH para conciliar
Permisos  : IsTenantMember()
Filtros   : SearchFilter + OrderingFilter (DjangoFilterBackend REMOVIDO — ver FIX-01)
```

**CRITICO — FIX-01:** `filterset_fields = ["tipo_movimiento"]` fue removido.
`tipo_movimiento` es `@property`, no campo BD. El filtrado se hace manualmente:

```python
def get_queryset(self):
    if not hasattr(self, "action") or self.action is None:
        return TransaccionBancaria.objects.none()
    empresa_id = self.get_empresa_id()
    qs = TransaccionBancaria.objects.filter(empresa_id=empresa_id)

    # Filtro extracto
    if extracto_uuid := self.request.query_params.get('extracto_uuid'):
        qs = qs.filter(extracto__uuid=extracto_uuid)

    # Filtro tipo (manual — tipo_movimiento es @property, no campo BD)
    tipo_mov = self.request.query_params.get('tipo_movimiento','').upper()
    if   tipo_mov == 'DEBITO':  qs = qs.filter(valor__lt=0)
    elif tipo_mov == 'CREDITO': qs = qs.filter(valor__gte=0)

    # Filtro conciliacion
    conc = self.request.query_params.get('conciliado','')
    if   conc.lower() in ('true','1'):  qs = qs.filter(conciliado=True)
    elif conc.lower() in ('false','0'): qs = qs.filter(conciliado=False)

    if self.action == "list":
        return self.get_qs_list()
    return qs
```

**Endpoints TransaccionBancariaViewSet:**

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/bancos/transacciones/` | GET | Lista con filtros extracto_uuid, tipo_movimiento, conciliado |
| `/api/v1/bancos/transacciones/{uuid}/` | GET | Detalle de una transaccion |
| `/api/v1/bancos/transacciones/{uuid}/conciliar/` | PATCH | Guarda vinculo factura/proveedor/cliente/notas |
| `/api/v1/bancos/transacciones/search-facturas/` | GET | Autocomplete facturas por `?q=&naturaleza=VENTA\|COMPRA` |
| `/api/v1/bancos/transacciones/search-proveedores/` | GET | Autocomplete proveedores por `?q=` |
| `/api/v1/bancos/transacciones/search-clientes/` | GET | Autocomplete clientes por `?q=` |

**CRITICO — FIX-03 — `search_facturas`:**
```python
# INCORRECTO (v1.0): tipo='VENTA' — el campo `tipo` contiene 'FE'/'NC'/'ND'
qs = Factura.objects.filter(tipo='VENTA')   # → cero resultados siempre

# CORRECTO (v2.0): naturaleza='VENTA' — el campo correcto para VENTA/COMPRA
qs = Factura.objects.filter(naturaleza=naturaleza)   # → resultados reales

# Para VENTA: tercero = receptor_nit + receptor_razon_social (el cliente)
# Para COMPRA: tercero = emisor_nit + emisor_razon_social (el proveedor)
```

### 4.2 Serializers (`api/serializers.py`)

#### ExtractoBancarioListSerializer (v2.0)
```python
total_transacciones  = IntegerField(read_only=True, default=0)   # annotacion
tx_conciliadas       = IntegerField(read_only=True, default=0)   # annotacion
tx_pendientes        = SerializerMethodField()  # total - conciliadas
```

#### TransaccionBancariaListSerializer (v2.0)
```python
tipo_movimiento      = CharField(read_only=True)       # @property DEBITO | CREDITO
monto                = DecimalField(read_only=True)    # @property abs(valor)
factura_info         = SerializerMethodField()         # {'uuid': str}
proveedor_info       = SerializerMethodField()         # {'uuid': str}
conciliacion_display = SerializerMethodField()         # "Vinculado: Factura + Cliente"
notas_conciliacion   = campo de modelo
```

#### TransaccionBancariaConciliarSerializer (v2.0)
```python
class Meta:
    fields = ("factura_uuid", "proveedor_uuid", "cliente_uuid",
              "conciliado", "notas_conciliacion")

def validate(attrs):
    # Auto-marca conciliado=True si hay cualquier UUID vinculado
```

---

## 5. FRONTEND

### 5.1 Estructura de Archivos

```
static/bancos/js/
    bancos.api.js         SSoT endpoints (window.Sintel.Bancos.API)
    bancos.main.js        Orquestador: tabs, event delegation, modal eliminar
                          v2.0: agrega delegacion btn-conciliar-extracto
    features/
        cuenta_list.js    Tabulator grid CuentaBancaria (sin cambios)
        cuenta_editor.js  Offcanvas crear/editar Cuenta (sin cambios)
        extracto_list.js  v2.0: nueva columna Conciliacion + boton Conciliar
        extracto_editor.js v2.0: reescrito — flujo guiado 4 pasos + autocomplete
```

### 5.2 Namespace Global (v2.0)

```javascript
window.Sintel.Bancos = {
    API:           { cuentas, extractos }               // bancos.api.js
    Main:          { init, refresh }                    // bancos.main.js
    CuentaList:    { init, refresh }                    // cuenta_list.js
    CuentaEditor:  { openOffcanvas }                    // cuenta_editor.js
    ExtractoList:  { init, refresh, redraw, procesarExtracto }  // extracto_list.js
    ExtractoEditor:{ openOffcanvas, openDetalle }       // extracto_editor.js — v2.0
}
```

### 5.3 `extracto_list.js` — Nueva Columna Conciliacion (v2.0)

```javascript
{
    title: "Conciliacion",
    field: "tx_conciliadas",
    formatter(cell) {
        const total = row.total_transacciones || 0;
        const conc  = row.tx_conciliadas      || 0;
        const pct   = total > 0 ? Math.round((conc / total) * 100) : 0;
        const color = pct === 100 ? 'bg-success' : pct > 0 ? 'bg-warning' : 'bg-danger';
        // Muestra: "3/10 [2 pendientes]" + barra de progreso coloreada
    }
}
// Boton Conciliar en Acciones: solo visible si procesado && tx_pendientes > 0
```

### 5.4 `extracto_editor.js` — Flujo Guiado 4 Pasos (v2.0)

**`_bindDetalle(container)` — logica completa:**

```
1. FILTROS DE TABLA
   [Todos] [↑Ingresos] [↓Egresos] [Sin conciliar] [Todos]
   → filtran filas por valor >= 0 / < 0 / conciliado

2. CLICK EN FILA → PANEL CONCILIACION
   a) Leer row.dataset.tipo = 'INGRESO' | 'EGRESO'
   b) Paso 1: rellenar info TX (desc, fecha, valor coloreado, badge tipo)
   c) Paso 2: auto-activar tab Factura
      - INGRESO → _activarTabFac('VENTA')  → label "Factura de Venta"
      - EGRESO  → _activarTabFac('COMPRA') → label "Factura de Compra"
   d) Paso 3: mostrar/ocultar tercero
      - INGRESO → mostrar Cliente, ocultar Proveedor
      - EGRESO  → mostrar Proveedor, ocultar Cliente
   e) Paso 4: notas — pre-cargar row.dataset.notas si ya existian
   f) Pre-cargar chips si la TX ya tenia vinculos (factura_uuid, etc.)

3. AUTOCOMPLETE (factory _initAC)
   - Endpoint como funcion: (q) => URL — captura naturalezaFac dinamicamente
   - Debounce 280ms
   - Resultados: nombre, NIT, fecha, total, badges estado
   - Click resultado → chip con info completa

4. GUARDAR VINCULO
   payload = {
     factura_uuid,
     proveedor_uuid: esEgreso  ? hidProv.value : null,
     cliente_uuid:   !esEgreso ? hidCli.value  : null,
     notas_conciliacion: notasEl.value || null,
   }
   → PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
   → Actualizar badge en la fila sin recargar
   → Marcar paso 1 como done (circulo verde)

5. QUITAR VINCULO
   payload = { factura_uuid: null, proveedor_uuid: null,
               cliente_uuid: null, conciliado: false }
   → PATCH mismo endpoint
   → Limpiar chips, feedback
```

**CRITICO — FIX-02 resuelto:**
```javascript
// extracto_editor.js busca este ID exacto tras htmx:afterSettle:
const offcanvasEl = target.querySelector('#offcanvas-extracto-detalle');
// El template debe tener id="offcanvas-extracto-detalle" (no "oc-extracto-det")
```

### 5.5 `offcanvas_detalle_extracto.html` — Layout Split (v2.0)

```
┌──────────── Offcanvas 1100px ──────────────────────────────────┐
│ Header: Cuenta | Periodo | Saldos | Estado | [Procesar]        │
├─────────────────────────────┬──────────────────────────────────┤
│  IZQUIERDO (flex:1)         │  DERECHO (380px)                 │
│  Transacciones              │  Conciliar Transaccion           │
│                             │  Cuenta — Mes Anio               │
│  [Todos][↑In][↓Eg]         │                                   │
│  [Sin conciliar][Todos]     │  Paso 1 ● Movimiento             │
│                             │    Descripcion | Fecha | Valor   │
│  Fecha | Desc | Tipo | Valor│    badge: ↑Ingreso / ↓Egreso    │
│  ──────────────────────     │                                   │
│  20/06  Pago  ↑ +$1.201.902│  Paso 2 ● Factura de Venta       │
│  21/06  Ret.  ↓ -$200.000  │    [Buscar factura...]           │
│  ...   click → →           │                                   │
│                             │  Paso 3 ● Cliente (o Proveedor) │
│                             │    [Buscar tercero...]           │
│                             │                                   │
│                             │  Paso 4 ● Notas (opcional)      │
│                             │    [textarea...]                  │
│                             │                                   │
│                             │  [Quitar] [Guardar vinculo]      │
└─────────────────────────────┴──────────────────────────────────┘
```

**CSS de pasos:**
```css
.conc-step           { position:relative; padding-left:36px; margin-bottom:.5rem; }
.conc-step::before   { linea vertical conectora entre pasos }
.conc-step-num       { circulo numerado azul oscuro; .done = verde }
.conc-step-label     { texto uppercase 0.72rem }
.conc-step-body      { tarjeta blanca con borde, padding 10px }
```

### 5.6 Logica de Auto-deteccion (v2.0)

| Condicion | Accion automatica |
|---|---|
| `row.dataset.tipo === 'INGRESO'` (valor >= 0) | Tab Factura → VENTA, Paso 3 → Cliente visible, Proveedor oculto |
| `row.dataset.tipo === 'EGRESO'` (valor < 0) | Tab Factura → COMPRA, Paso 3 → Proveedor visible, Cliente oculto |
| Payload PATCH con INGRESO | `{factura_uuid, cliente_uuid, notas_conciliacion}` |
| Payload PATCH con EGRESO | `{factura_uuid, proveedor_uuid, notas_conciliacion}` |

---

## 6. TEMPLATES

```
templates/tenant/bancos/
    list.html                     Wrapper → incluye list_bancos.html
    list_bancos.html              Layout: 2 tabs (Cuentas / Extractos)
    assets_bancos.html            Carga scripts en orden
    offcanvas_crear_cuenta.html   Form nueva cuenta
    offcanvas_editar_cuenta.html  Form editar cuenta
    offcanvas_crear_extracto.html Form upload Excel multipart
    offcanvas_detalle_extracto.html  v2.0: Split layout + 4 pasos conciliacion
```

### Cambios en `offcanvas_detalle_extracto.html` (v2.0)

| Elemento | v1.0 | v2.0 |
|---|---|---|
| ID offcanvas | `oc-extracto-det` ❌ | `offcanvas-extracto-detalle` ✅ |
| ID boton procesar | `btn-procesar-ext` ❌ | `btn-procesar-extracto-detalle` ✅ |
| Layout | Columna simple | Split flex (tabla + panel derecho) |
| Valores | Sin formato | `+$X` verde / `−$X` rojo |
| Conciliacion | Panel UUID raw | 4 pasos guiados con autocomplete |
| Notas | No existia | Paso 4 textarea |
| data- attrs en TX | `data-tx-uuid` | + `data-notas`, `data-cliente-uuid` |
| templatetags | `{% load humanize %}` ❌ | `{% load currency_filters %}` ✅ |

---

## 7. CONFORMIDAD CON AGENTS.md

### ✅ Reglas Cumplidas

| Regla | Seccion | Estado |
|---|---|---|
| `SintelTenantBaseModel` en todos los modelos | §14 | ✅ |
| `empresa_id` en todas las queries ORM | §4 | ✅ |
| `.only()` en todos los selectores y queryset de transacciones | §4.5 | ✅ |
| `select_related()` donde hay FK traversals | §4.5 | ✅ |
| `uuid` como lookup_field (no PK entero) | §25 | ✅ |
| `BaseTenantViewSet` en herencia ViewSets | §15 | ✅ |
| `IsTenantMember + IsTenantAdminOrReadOnly` | §15 | ✅ |
| `SintelDSVMixin` en ViewSets | §5 | ✅ |
| DSV en serializers (`validate()`) | §5 | ✅ |
| `@transaction.atomic` en CRUD (incluye `conciliar_transaccion`) | §5 | ✅ |
| Service Layer separado (CRUD + Business) | §5 | ✅ |
| `LIST_FIELDS` / `DETAIL_FIELDS` en selectors con `.only()` | §4.5 | ✅ |
| `window.Sintel.Bancos.*` namespace FSD | §23, §31 | ✅ |
| `window.http()` para todas las mutaciones | §31 | ✅ |
| `htmx:afterSettle` en `document.addEventListener` | §26 | ✅ |
| `UIManager.handleOffcanvas(el, 'show')` (no getOrCreateInstance) | §26 | ✅ |
| Soft references UUID (no FK directa cross-app) — Bounded Context | §18 | ✅ |
| Zero-Hardcoding de tenant names | §29 | ✅ |
| Idempotencia ETL (delete + bulk_create) | §5 | ✅ |
| Filtros manuales para @property (no filterset_fields) | §4 | ✅ |

### ⚠️ Observaciones Menores (heredadas v1.0)

#### OBS-01 — Naming `dcto` (menor)
- `TransaccionBancaria.dcto` (CharField) — nombre corto por convencion del Excel bancario colombiano
- Todos los templates y JS usan `dcto` correctamente
- No requiere accion

#### OBS-02 — RESUELTO en v2.0
- `mes = IntegerField(choices=MES_CHOICES)` — `get_mes_display()` ahora funciona en templates

---

## 8. FLUJOS COMPLETOS END-TO-END

### Flujo 1: Crear Cuenta Bancaria (sin cambios v1.0)

```
[UI] Click "Nueva Cuenta"
    → hx-get /api/v1/bancos/cuentas/render-offcanvas/crear/
    → htmx:afterSettle → UIManager.handleOffcanvas('show')
    → cuenta_editor._bindCrear()

[UI] Guardar
    → window.http('POST', '/api/v1/bancos/cuentas/', payload)
    → CuentaBancariaViewSet.create() → DSV → CuentaBancariaCRUDService.crear_cuenta()
    → 201 → CuentaList.refresh()
```

### Flujo 2: Importar y Procesar Extracto Excel (sin cambios v1.0)

```
[UI] "Importar Extracto" → FormData (cuenta, mes, anio, archivo)
    → POST /api/v1/bancos/extractos/ → ExtractoBancarioCRUDService.crear_extracto()
    → 201 { procesado: false }

[UI] "Procesar" → POST /api/v1/bancos/extractos/{uuid}/procesar/
    → ExtractoBancarioBusinessService.procesar_archivo_extracto()
    → pd.read_excel + parse + bulk_create(transacciones)
    → extracto.procesado = True
    → ExtractoList.refresh()
```

### Flujo 3: Ver Detalle y Conciliar Transacciones (v2.0)

```
[UI] Click "Ver Detalle" o "Conciliar" en ExtractoList
    → ExtractoEditor.openDetalle(uuid)
    → htmx.ajax GET /api/v1/bancos/extractos/{uuid}/render-offcanvas/detalle/
    → htmx:afterSettle → id="offcanvas-extracto-detalle" encontrado
    → UIManager.handleOffcanvas('show')
    → _bindDetalle(container)
        - Filtra tabla por tipo/conciliacion
        - Inicializa autocomplete facturas, proveedores, clientes

[UI] Click en fila de transaccion
    → Panel derecho se activa
    → Paso 1: info TX con badge ↑Ingreso / ↓Egreso
    → Paso 2: tab Factura se activa (VENTA si +, COMPRA si -)
    → Paso 3: Cliente visible (si +) / Proveedor visible (si -)
    → Paso 4: notas pre-cargadas si ya existian

[UI] Escribir en campo busqueda (≥ 2 chars, debounce 280ms)
    → Para Factura:
       GET /api/v1/bancos/transacciones/search-facturas/?naturaleza=VENTA&q=term
       → Factura.objects.filter(naturaleza='VENTA', Q(numero|receptor_nit|receptor_razon_social))
       → Resultados: numero, nombre, NIT, total, badges
    → Para Proveedor:
       GET /api/v1/bancos/transacciones/search-proveedores/?q=term
       → Proveedor.objects.filter(Q(numero_documento|razon_social|nombre_comercial|ciudad))
    → Para Cliente:
       GET /api/v1/bancos/transacciones/search-clientes/?q=term
       → Cliente.objects.filter(Q(numero_documento|razon_social|nombre_comercial|ciudad))

[UI] Click resultado → chip aparece con nombre + NIT/doc

[UI] Click "Guardar vinculo"
    → payload = { factura_uuid, cliente_uuid|proveedor_uuid, notas_conciliacion }
    → PATCH /api/v1/bancos/transacciones/{uuid}/conciliar/
    → TransaccionBancariaConciliarSerializer.validate()
      → conciliado=True automatico si hay cualquier UUID
    → service_conciliar_transaccion()
    → TransaccionBancariaCRUDService.conciliar_transaccion(tx, data) @atomic
      → setattr(tx, campo, valor) solo para campos presentes
      → tx.save(update_fields=[...])
    → 200 { tx actualizada }
    → Badge en fila cambia: Pendiente → Factura / Cliente / F+C
    → Circulo paso 1 → verde (done)

[UI] Click "Quitar vinculo"
    → payload = { factura_uuid: null, proveedor_uuid: null, cliente_uuid: null, conciliado: false }
    → PATCH mismo endpoint → bd limpia
    → Badge → Pendiente (gris)
```

---

## 9. COMANDOS UTILES

```bash
# Ver estado de migraciones bancos
docker compose exec web python manage.py showmigrations | grep bancos

# Aplicar migraciones en todos los schemas
docker compose exec web python manage.py migrate_schemas

# Probar endpoint conciliar directamente
curl -X PATCH http://cliente.sintel.net.co:8000/api/v1/bancos/transacciones/{uuid}/conciliar/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"factura_uuid":"xxx","conciliado":true,"notas_conciliacion":"Pago cuota 3/6"}'

# Verificar campos del modelo
docker compose exec web python manage.py shell -c "
from django_tenants.utils import schema_context
from apps.tenant.bancos.models import TransaccionBancaria
with schema_context('cliente'):
    tx = TransaccionBancaria.objects.first()
    print(tx.uuid, tx.conciliado, tx.notas_conciliacion)
"

# Buscar facturas del tenant (verificar naturaleza correcta)
docker compose exec web python manage.py shell -c "
from django_tenants.utils import schema_context
from apps.tenant.facturas.models import Factura
with schema_context('cliente'):
    print(list(Factura.objects.values('naturaleza').distinct()[:5]))
"
```

---

## 10. PROXIMOS PASOS RECOMENDADOS

| ID | Prioridad | Descripcion | Estado |
|---|---|---|---|
| BAN-06 | ALTA | Mostrar nombre/numero de la Factura vinculada en el chip (antes solo mostraba UUID truncado al pre-cargar vinculo existente). | **RESUELTO (2026-09-18).** Resuelto server-side en `render_offcanvas_detalle` via `TerceroDisplaySelector.resolver()` (3 queries bulk, una por tipo -- factura/proveedor/cliente -- en vez de N+1 por transaccion). El nombre viaja en `data-factura-info`/`data-proveedor-info`/`data-cliente-info`; `extracto_editor.js` los usa al pre-cargar el chip, con fallback al UUID truncado si el registro no resuelve (soft-ref, no bloquea). |
| BAN-07 | MEDIA | Al abrir detalle de TX ya conciliada, resolver nombres reales via llamada a los 3 endpoints de busqueda usando los UUIDs guardados. | **RESUELTO (2026-09-18), mismo cambio que BAN-06.** Implementado como resolucion bulk server-side (arriba) en vez de 3 llamadas a los endpoints `search-*` por transaccion -- evita N+1 y es mas eficiente que lo sugerido originalmente sin cambiar el resultado visible. |
| BAN-08 | MEDIA | Agregar `test_conciliacion.py` con los 3 escenarios: INGRESO→Cliente, EGRESO→Proveedor, quitar vinculo. | **RESUELTO (2026-09-18).** `tests/test_conciliacion.py`, 3 tests, verificados en verde. |
| BAN-09 | MEDIA | KPI Panel en tab Extractos: % conciliado total de la empresa, monto sin conciliar. | **RESUELTO (2026-09-18).** `ExtractoBancarioKpiSelector.get_kpis_empresa()` (nuevo, `selectors.py`) + `ExtractoBancarioTableView.get_context_data()` + fila de `sintel_kpi_card` en `partials/tabla_extractos.html` (Transacciones/Conciliadas/Pendientes/%Conciliado/Monto sin conciliar). |
| BAN-10 | BAJA | Eliminar alias deprecado `w.bancosAPI = w.Sintel.Bancos.API` en bancos.api.js. | **RESUELTO (2026-09-18).** Verificado sin usos restantes antes de eliminar. |
| BAN-11 | BAJA | Campo `sede` FK en `ExtractoBancario` para KPIs por sede (patron DT-SEDE). | **RESUELTO (2026-09-18).** Migracion `0008_extractobancario_sede.py`, mismo patron DT-SEDE-01 que `gastos.DocumentoSoporte.sede` (opcional, `SET_NULL`, DSV + `sede_esta_en_alcance()` anti-IDOR en `ExtractoBancarioCreateSerializer`). Sin UI de seleccion todavia (mismo estado que el resto del rollout DT-SEDE-01 en el proyecto -- backend/API listo, selector de UI diferido). |
| BAN-12 | BAJA | Exportar reporte de conciliacion a CSV/Excel por periodo. | **RESUELTO (2026-09-18) -- solo CSV.** `GET /api/v1/bancos/extractos/{uuid}/exportar/` (`ExtractoBancarioExportService.generar_csv_conciliacion()`, reutiliza `TransaccionBancariaSelector`+`TerceroDisplaySelector`). El "periodo" es el extracto (cuenta+mes/anio), consistente con el resto del modulo. Boton de descarga directa en `tables.py::render_acciones()` (solo si `procesado` y hay transacciones). Excel (XLSX) no se implemento -- CSV ya satisface el requisito y evita agregar `openpyxl` como dependencia de escritura solo para esto. |

Tests nuevos de esta pasada: `test_conciliacion.py` (3), `test_extracto_sede.py` (3, incluye
aislamiento cross-tenant real via `tenant1`/`tenant2`), `test_export_conciliacion.py` (1).
