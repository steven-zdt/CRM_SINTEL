# [PORTAL] Auditoría Flujo Completo — Módulo Facturas

**Versión:** v4.0.0
**Estado:** VERIFIED — regresión real completa confirmada 2026-09-15 (RELEASE-CLOSE-01): Facturas 205/205 passed, regresión de 4 apps (ventas+facturas+cotizaciones+compras) 358/358 passed, 0 failed en ambas corridas. Ver §"RELEASE-CLOSE-01 (2026-09-15)" más abajo para el detalle completo.
**Ubicación:** `apps/tenant/facturas/`
**Última Auditoría:** 2026-09-14 (reestructuración arquitectónica — ver v4.0.0 abajo), re-verificada 2026-09-15 (RELEASE-CLOSE-01). Contenido v3.12.0 (2026-08-07) preservado más abajo sin modificar salvo anotaciones `[REMOVIDO v4.0.0]` en las filas afectadas — no se reescribió el historial.
**Auditor:** Claude Sonnet 5 (Anthropic)

---

## v4.0.0 (2026-09-14) — Reestructuración arquitectónica: Facturas = document store

### Redefinición del alcance

Hasta v3.12.0 esta app funcionaba como un **hub multi-dominio**: además de
ingestar/normalizar/persistir documentos fiscales, creaba Clientes y
Proveedores como efecto lateral de importar un XML, escribía movimientos
de Kardex de Inventario al procesar Notas Crédito, y su UI/backend
bloqueaban ediciones según datos de conciliación bancaria.

**Nueva definición del alcance:**

> `Facturas` es proveedor de datos fiscales/documentales normalizados
> (ingestión → parsing → validación → normalización → persistencia → API
> de lectura). Los demás módulos (Ventas, Compras, Bancos, Clientes,
> Proveedores, Inventario, Contabilidad) son dueños de sus propios
> procesos de negocio y consumen los hechos documentales que Facturas
> expone — nunca al revés.

### Matriz de responsabilidad final

| Responsabilidad | Facturas |
|---|---|
| Recibir XML / Parsear XML | ✅ |
| Normalizar factura, NIT/datos fiscales | ✅ |
| Persistir documento, anexos, impuestos documentales, items | ✅ |
| Calcular/validar CUFE | ✅ |
| Clasificar VENTA/COMPRA (metadata documental) | ✅ |
| Servir API normalizada (`FacturaInterAppAPI`) | ✅ |
| Resolver (solo lectura) Cliente/Proveedor existente por NIT para `cliente_uuid`/`proveedor_uuid` | ✅ |
| Crear Cliente | ❌ (v4.0.0 — antes ✅ vía `ClienteBusinessService.resolver_o_crear_desde_factura_venta`) |
| Crear Proveedor | ❌ (v4.0.0 — antes ✅ vía `ProveedorBusinessService.resolver_o_crear_desde_factura_compra`) |
| Endpoints `vincular-cliente`/`vincular-proveedor`/`vincular-cotizacion` | ❌ (v4.0.0 — removidos, 0 consumidores reales) |
| Endpoint `obtener-retenciones` (consultaba retenciones desde Cliente) | ❌ (v4.0.0 — removido) |
| Endpoints `inventario-catalogo`/`trazabilidad-inventario` | ❌ (v4.0.0 — removidos) |
| Endpoints duplicados de ingestión `importar-ubl`/`materialize` (ya deprecados en el propio código, delegaban al mismo pipeline que `upload-ubl`/`create-from-dto`) | ❌ (v4.0.0 — removidos) |
| Forzar `estado_pago` según conciliación bancaria (JS del editor + validación backend en `actualizar_factura_limitado()`) | ❌ (v4.0.0 — removido) |
| Gestionar Cartera, CxP, conciliar Banco, registrar pago | ❌ (nunca lo hizo — ver deuda pendiente abajo) |
| Crear asiento contable, decidir reglas/PUC | ❌ (nunca lo hizo — Pull Model ADR-001 ya correcto) |
| Escribir Kardex de Inventario (`_generar_entrada_devolucion`, Notas Crédito) | ⚠️ **Sigue existiendo — feature versionada v3.27, NO es deuda, fuera de alcance Fase 2/3, ver abajo** |
| Bancos↔Facturas (`BancosBridge`, `FacturaInterAppAPI.recalcular_estado_pago_automatico`, `total_pagado_bancos`/`saldo_pendiente`) | ✅ **[Fase 2, 2026-09-14] Eliminado por completo** — Bancos ahora solo lee vía `FacturaInterAppAPI.get_by_id()` (read-only), ver abajo |
| Crear Factura desde Venta (`crear_factura_desde_venta`) | ⚠️ **Sigue existiendo — [Fase 3, 2026-09-14] evaluado con evidencia, no eliminado, ver abajo** |

### Qué se removió (verificado con `grep` repo-wide antes de tocar, 0 consumidores externos reales)

**Backend — `services/business_service.py`:**
- `guardar_desde_dto()`: ya NO llama `ClienteBusinessService.resolver_o_crear_desde_factura_venta()` ni
  `ProveedorBusinessService.resolver_o_crear_desde_factura_compra()`. En su lugar, dos helpers nuevos
  de solo lectura — `_resolver_cliente_existente()` / `_resolver_proveedor_existente()` — buscan un
  tercero YA EXISTENTE por NIT (`clean_nit()`, la SSoT real de comparación fiscal del proyecto, no
  `normalize_document_number()` que concatena el DV). Si no existe, `cliente_uuid`/`proveedor_uuid`
  quedan en `None` — ya no bloquea ni crea nada.
- Removidos por no tener ya ningún consumidor tras lo anterior: `vincular_cliente()`, `vincular_proveedor()`,
  `obtener_retenciones_desde_cliente()`, `obtener_retenciones_desde_proveedor()`.
- `actualizar_factura_limitado()`: removido el bloque de validación `estado_pago` vs
  `total_pagado_bancos`/`saldo_pendiente` (v3.11.0) — 0 tests lo cubrían en todo el repo (verificado).

**Backend — `api/viewsets.py` + `api/mixins/factura_ubl_mixin.py`:**
- Endpoints removidos: `vincular-cotizacion`, `vincular-cliente`, `vincular-proveedor`,
  `obtener-retenciones`, `inventario-catalogo`, `trazabilidad-inventario`, `importar-ubl`, `materialize`.
- Context injection de `total_pagado_bancos`/`saldo_pendiente` en `gestor_offcanvas()` (era exclusivamente
  "para el JS del editor", comentario propio del código) — removido junto con el JS que lo consumía.
- `ImportUBLSerializer` (solo usado por `importar-ubl`) removido de `api/serializers.py`.

**Frontend:**
- `facturas.api.js`: removidas `vincularCotizacion()`, `vincularCliente()`, `vincularProveedor()`.
- `factura_inventario_vinculacion.js` (225 líneas, feature completa de vinculación factura↔inventario) —
  archivo eliminado, único consumidor de `inventario-catalogo`.
- `facturas_editor.js`: removida `initResumenPagosBancos()` (forzaba `estado_pago` según medio de pago +
  conciliación bancaria) y `guardarVinculacionesInventario()` (guardaba `item_inventario_*` desde la UI
  ya eliminada).
- `ver_detalle_factura.js`: la cotización vinculada pasa de "vincular/desvincular" (acción de negocio) a
  referencia documental de solo lectura — removidos `actualizarCotizacionVinculada()`,
  `cargarCotizacionesDisponibles()` y sus botones.
- Templates: bloque "Resumen de Pagos Bancos" (`offcanvas_editar_factura.html`) y bloque
  "Vincular con Inventario" removidos; bloque "Cotización vinculada" (`offcanvas_detalle_factura.html`)
  convertido a solo lectura.

**No se tocaron** (siguen existiendo, decisión explícita): `cliente_uuid`/`proveedor_uuid`/
`cotizacion_uuid`/`item_inventario_uuid` como campos de referencia documental en el modelo;
`InventarioItemBridge.resolver_item()` (sigue en uso real por `api/serializers.py` para mostrar el nombre
del producto vinculado a un ítem — lectura pura, no lo que se removió); `ClienteBridge`/`ProveedorBridge`/
`CotizacionBridge` (siguen siendo consumidos por `apps/tenant/core/services/organizational_bridges.py`);
`endpoint lista-centro-costos` (tiene un consumidor externo real: `apps/tenant/proyectos/static/proyectos/js/proyectos.api.js`,
quedó fuera de alcance de esta pasada); `endpoint buscar-para-movimiento` (consumidores reales en
Compras/Ventas/Inventario, lectura pura, correcto tal cual).

### Deuda arquitectónica — actualizado tras "PROMPT MAESTRO" (Fase 2 y Fase 3)

La pasada anterior (arriba, ahora superada) había dejado 3 puntos como deuda diferida por decisión
explícita del usuario ("solo lo de bajo riesgo por ahora"). El "PROMPT MAESTRO PARA IA EDITORA" recibido
después **revierte esa decisión conservadora** y autoriza explícitamente ejecutar Fase 2 (desacoplar
Bancos) y Fase 3 (desacoplar Ventas). Estado real tras ejecutarlas:

1. **[EJECUTADO — Fase 2] `FacturaInterAppAPI.recalcular_estado_pago_automatico()` + `BancosBridge` +
   `Factura.total_pagado_bancos`/`saldo_pendiente`** — los 4 elementos fueron **removidos por completo**:
   - `apps/tenant/bancos/services/crud_service.py::conciliar_transaccion()` ya no llama al método
     eliminado; se dejó un comentario explicativo. El trigger de abono en Cartera
     (`CarteraBusinessService.registrar_abono_desde_conciliacion_bancaria`) se mantuvo intacto — es una
     integración Bancos→Clientes, no Bancos→Facturas, y no era parte de lo que había que desacoplar.
   - `FacturaInterAppAPI.recalcular_estado_pago_automatico()` eliminado de `business_service.py`.
   - `Factura.total_pagado_bancos`/`saldo_pendiente` (`@property`) eliminados de `models.py`.
   - `BancosBridge` (clase completa, incl. `obtener_total_conciliado()`) eliminado de `selectors.py`.
   - Frontend: bloque "Resumen de Pagos Bancos" removido del offcanvas de edición
     (`offcanvas_editar_factura.html`), `initResumenPagosBancos()` removido de `facturas_editor.js`,
     serializers (`FacturaListSerializer`/`FacturaDetailSerializer`) y el `gestor_offcanvas()` del
     viewset limpiados de las mismas 2 propiedades.
   - Verificación: `grep -rn "BancosBridge\|total_pagado_bancos\|saldo_pendiente\|recalcular_estado_pago_automatico"`
     en todo el repo (incl. `tests/`) confirma **cero referencias residuales** fuera de este propio
     documento — ningún test dependía de estos símbolos, la remoción fue limpia.
   - Bancos v3.0 (commit `f24d91c`/`68275b6`) sigue funcionando: su propio dominio (`TransaccionBancaria.conciliado`,
     `MovimientoBancarioAplicacion`) nunca dependió de estos campos de `Factura`, solo los escribía.

2. **[EVALUADO — Fase 3, NO removido, con evidencia] `FacturaBusinessService.crear_factura_desde_venta()`**
   — se investigó a fondo en lugar de eliminar a ciegas. Hallazgos:
   - `ventas/services/business_service.py` define `EMISION_FISCAL_VENTA_AUTORIZADA = False` (constante
     hardcodeada, no settings/env, líneas ~560-740) — SINTEL aún no está autorizado por la DIAN para
     emisión fiscal real. `procesar_y_facturar_venta()` devuelve 403 **antes** de poder alcanzar
     `crear_factura_desde_venta()`. Es decir: hoy, en producción, esa ruta es **estructuralmente
     inalcanzable** — no hay acoplamiento vivo que romper.
   - Pero el método sigue siendo ejercitado por **5 archivos de test reales, en 2 apps**, que mockean el
     flag a `True` deliberadamente para seguir validando el pipeline DIAN completo:
     `apps/tenant/ventas/tests/test_comercial_04_idempotencia.py`,
     `test_f23_venta_inventario.py`, `test_f23_venta_inventario_multitenant.py`,
     `test_vincular_factura_manual.py`, y `apps/tenant/cotizaciones/tests/test_facturar_venta.py`.
     (`test_bloqueo_emision_fiscal.py` se revisó aparte y NO ejercita la rama muerta — solo valida el 403.)
   - Decisión: **no se elimina físicamente el método en esta pasada**. Es un contrato público,
     basado en DTO, ya gateado (por el flag), ya documentado (`PUSH_CONTROLLED` en
     `VENTAS_FACTURAS_AUDIT.md`), sin acoplamiento vivo hoy. Removerlo exigiría reescribir 5 archivos de
     test que hoy validan de forma legítima el pipeline DIAN completo (COMERCIAL-04, F23, vinculación
     manual, cotización→venta→factura) a cambio de un beneficio arquitectónico marginal, dado que el
     "acoplamiento" real ya está neutralizado por el flag. Esto es consistente con la propia Gate F3 del
     PROMPT MAESTRO ("cualquier referencia legítima queda documentada"): Fase 3 se considera
     **sustancialmente satisfecha por evidencia** (el acoplamiento vivo no existe) sin borrado de código.

3. **[SIN CAMBIOS — no es deuda, es feature versionada] `_generar_entrada_devolucion()`**
   (`business_service.py`, dispara `KardexService.registrar_movimiento(ENTRADA_DEVOLUCION)` al procesar
   una Nota Crédito con items resolubles a Producto) — **no es deuda accidental**: es una feature
   versionada v3.27 que cierra un gap de negocio documentado explícitamente ("Cierra la brecha DEFERRED
   desde F23") y tiene su propio archivo de 5 tests dedicados (`test_devolucion_nota_credito.py`).
   Removerla sin reemplazo detendría el ajuste automático de inventario en devoluciones — regresión
   funcional real, no solo arquitectónica. Fuera de alcance de Fase 2/3 (no es Bancos ni Ventas).

`lista-centro-costos` (endpoint con consumidor real en Proyectos) permanece sin tocar por la misma razón
que el punto 3: consumidor real fuera del alcance de las fases ejecutadas.

### v4.0.0 — Estado real de la verificación

```
python manage.py check                              → System check identified no issues (0 silenced)
grep -rn "BancosBridge|total_pagado_bancos|saldo_pendiente|
           recalcular_estado_pago_automatico" (repo completo, incl. tests/) → 0 referencias residuales
pytest apps/tenant/facturas/tests/ (suite completa)  → 1 failed, 205 passed, 12 skipped (5826.45s).
                                                         El unico failure
                                                         (test_factura_total_retenciones_multiples,
                                                         FacturaBackwardCompatTestCase) es PRE-EXISTENTE
                                                         y AJENO a esta mision: contabilidad/services/
                                                         retenciones_service.py::crear_retencion() aplica
                                                         desde el commit 4dbe80c (REM-P0-03, anterior a
                                                         esta sesion) un UniqueConstraint de idempotencia
                                                         por (documento_origen, tipo, reversada=False) --
                                                         el test crea 3 retenciones RETEFUENTE para la
                                                         MISMA factura esperando que se sumen, pero la 2a
                                                         y 3a chocan con el guard de idempotencia y
                                                         devuelven la fila existente (50.00) en vez de
                                                         crear una nueva. No se tocó ese archivo ni ese
                                                         metodo de test en esta sesion (el diff de este
                                                         mismo archivo de test solo retira
                                                         EndpointBackwardCompatTestCase). Queda documentado
                                                         como deuda de contabilidad, fuera de alcance de
                                                         Fase 2/3 (Bancos/Ventas).
pytest apps/tenant/bancos/tests/ (suite completa)    → 58 passed, 0 failed (2496.25s). Re-corrida tras
                                                         Fase 2 (bancos/crud_service.py::
                                                         conciliar_transaccion() editado para remover la
                                                         llamada a recalcular_estado_pago_automatico());
                                                         mismo resultado que la corrida previa a Fase 2
                                                         -- confirma que remover esa llamada no rompió
                                                         nada del dominio propio de Bancos (el trigger de
                                                         abono en Cartera, que sí se mantuvo, sigue
                                                         cubierto por estos mismos tests).
manage.py check + makemigrations --check          → limpios tras Fase 2/3 completas (0 issues, "No
(Fase 8, re-verificado tras Fase 2/3)               changes detected").
tools/organizational_governance/cli.py --report   → PASS limpio (0 FAIL, 0 WARN) en las 8 categorías
(Fase 16, auditoría de dependencias huérfanas)      tras Fase 2 — confirma que no quedó ningún ciclo ni
                                                     import huérfano bancos<->facturas en el grafo real.
pytest apps/tenant/ventas/tests                   → 357 passed, 2 failed, 13 skipped (3:58:20). Cierra
apps/tenant/facturas/tests                          también COTIZACIONES-02 (regresión dirigida que esa
apps/tenant/cotizaciones/tests                      misión dejó pendiente, ver
apps/tenant/compras/tests                           docs/cotizaciones/COTIZACIONES_RELEASE_GATE.md).
(Fase 10, regresión multi-app)                      Los 2 failures fueron investigados con causa raíz real:
                                                     (a) test_factura_total_retenciones_multiples --
                                                     mismo hallazgo pre-existente de arriba. (b)
                                                     test_materialize_sin_dto_retorna_400 -- SÍ causado por
                                                     esta sesión (Fase 1: se eliminó el endpoint
                                                     `materialize`, el test quedó huérfano). Corregido:
                                                     test removido, la única otra referencia (en código
                                                     muerto tras un skipTest incondicional) actualizada a
                                                     `create-from-dto`. Re-verificado en aislado:
                                                     apps/tenant/facturas/tests/test_upload_async_flow.py
                                                     -- 2 passed, 2 skipped, 0 failed.
```

**Estado consolidado v4.0.0:** `manage.py check` limpio, gobernanza de dependencias limpia, `bancos` 58
passed/0 failed, regresión de 4 apps (ventas/facturas/cotizaciones/compras) 357 passed con 2 failures
investigados (1 pre-existente ajeno, 1 causado por esta sesión y ya corregido y re-verificado en verde).
Fase 2 (desacoplar Bancos) y Fase 10 (regresión multi-app) se consideran **COMPLETED** con evidencia real.
Fase 3 (desacoplar Ventas) **COMPLETED_WITH_DEFERRED** por decisión documentada (Gate F3 satisfecha por
evidencia, sin borrado de código). No se declara "PRODUCTION READY" — ese label requiere además la
regresión global de las 11 apps (Fase 14, aún no ejecutada, costo estimado varias horas) — pero "READY
FOR VALIDATION" ya está soportado con corridas reales, no análisis estático (regla explícita de la
misión, §51/§55).

### RELEASE-CLOSE-01 (2026-09-15) — re-verificación real contra el código actual

No se reutiliza el resultado histórico de arriba como resultado de esta misión (regla explícita
RELEASE-CLOSE-01 §"REGLA CENTRAL"). Se reprodujo el failure conocido, se clasificó y se re-corrió todo:

```
REPRODUCE: pytest apps/tenant/facturas/tests/test_retenciones_backward_compat.py -q --reuse-db
  → 1 failed, 11 passed (confirma exacto el hallazgo de arriba:
    Decimal('50.00') != Decimal('100.00')).

ROOT CAUSE (confirmado leyendo produccion, no asumido): el unico caller real
  de crear_retencion() para Factura
  (facturas/services/business_service.py::guardar_desde_dto()) lo invoca
  COMO MAXIMO UNA VEZ por tipo por documento (loop sobre
  ['RETEFUENTE','RETEICA','RETEIVA'], una llamada por tipo si monto>0). El
  escenario de 3 llamadas para el mismo tipo+documento que el test ejercitaba
  NUNCA ocurre en produccion -- es un escenario puramente sintetico del test,
  no una regla de negocio real perdida.

CLASSIFY: A -- test obsoleto. La regla nueva (idempotencia real,
  REM-P0-03) esta vigente y el codigo de produccion es correcto; el test
  codificaba una conducta (acumulacion) que la propia idempotencia
  prohibe por diseño.

PATCH: test_factura_total_retenciones_multiples renombrado a
  test_factura_creacion_retencion_repetida_es_idempotente -- ahora verifica
  que 3 llamadas a crear_retencion() con el mismo (documento, tipo) devuelven
  la MISMA fila (mismo pk) y que el total no se duplica (queda en 50.00, el
  monto de la primera llamada). Cero cambios en codigo de produccion.

TEST (re-verificacion): pytest apps/tenant/facturas/tests/test_retenciones_backward_compat.py
  -q --reuse-db → 12 passed, 0 failed.

RE-AUDIT (suite completa, fresca, HOY):
  pytest apps/tenant/facturas/tests -q --reuse-db
  → 205 passed, 0 failed, 12 skipped (5831.04s / 1:37:11).
  0 failures. El unico failure conocido de la pasada anterior esta cerrado.

grep -rn "BancosBridge|total_pagado_bancos|saldo_pendiente|
           recalcular_estado_pago_automatico|materialize|vincular-cliente|
           vincular-proveedor|vincular-cotizacion|obtener-retenciones|
           inventario-catalogo|trazabilidad-inventario|importar-ubl"
  (repo completo) → re-confirmado: 0 referencias vivas en codigo, solo
  comentarios explicativos y documentacion. UNA excepcion real encontrada
  (no capturada por la auditoria anterior): tools/smoke_facturas.sh seguia
  invocando POST /api/v1/facturas/materialize/ -- script de smoke test
  manual, huerfano, no parte de pytest/CI. Corregido: actualizado a
  create-from-dto (mismo patron que test_upload_async_flow.py).

  Tambien se encontraron y corrigieron comentarios desactualizados (sin
  efecto en runtime, solo documentacion-en-codigo) en
  apps/tenant/core/api/urls.py, que listaban importar-ubl/materialize como
  rutas heredadas vigentes de FacturaCoreViewSet -- confirmado con el diff
  real de apps/tenant/core/api/v1/facturas/viewsets.py que esas acciones
  fueron removidas de la lista de accion sin serializer en la misma sesion
  del 2026-09-14 (v4.0.0), el comentario de urls.py simplemente no se
  actualizo entonces.

python manage.py check                    → System check identified no issues (0 silenced). [re-verificado]
python manage.py makemigrations --check --dry-run → No changes detected. [re-verificado]
tools/organizational_governance/cli.py --report → PASS, 0 WARN/FAIL en las 8 categorias. [re-verificado]

pytest apps/tenant/ventas/tests apps/tenant/facturas/tests
       apps/tenant/cotizaciones/tests apps/tenant/compras/tests
       -q --reuse-db (Fase 4/10, regresion multi-app, FRESCA, HOY)
  → 358 passed, 0 failed, 13 skipped (14473.00s / 4:01:13).
  0 failures -- confirma que el fix de retenciones y el resto de v4.0.0
  no rompieron nada en ventas/cotizaciones/compras. (Corrida anterior de
  otra sesion, 2026-09-14, habia dado 357 passed/2 failed -- ambos
  failures ya investigados y cerrados entonces; esta cifra de HOY, 358/0,
  es la que se toma como resultado real de esta mision, no la anterior.)
```

**Veredicto RELEASE-CLOSE-01 (Facturas v4.0.0):** `FACTURAS_ARCHITECTURE = PASS`. El unico failure
conocido pendiente fue reproducido, root-caused y cerrado (clasificacion A, test obsoleto, cero cambios
de produccion). Suite completa de Facturas: **205 passed, 0 failed, 12 skipped**. Regresion de 4 apps
(ventas+facturas+cotizaciones+compras): **358 passed, 0 failed, 13 skipped**. Un hallazgo nuevo
(script de smoke huerfano) encontrado y corregido. Ver `RELEASE-CLOSE-01_FINAL_REPORT.md` (raiz del repo)
para el veredicto consolidado incluyendo COTIZACIONES-02.

---

## Documentación Especializada (SSoT)

| Documento | Descripción | Estado |
| :--- | :--- | :--- |
| Este archivo (`COMPLETO_FLUJO_FACTURAS.md`) | Portal SSoT + Resultados de Auditoría | ACTUALIZADO 2026-08-07 v3.12.0. **Corrección v3.12.0:** el link apuntaba a `AUDITORIA_FLUJO_FACTURAS.md`, un archivo que no existe en este directorio — nombre real es `COMPLETO_FLUJO_FACTURAS.md`. |

---

## Changelog

| Versión | Fecha | Descripción |
|---------|-------|-------------|
| **v4.0.0** | 2026-09-14 | **Reestructuración arquitectónica: Facturas = document store.** Ver sección dedicada al inicio de este archivo para el detalle completo (qué se removió, qué se dejó como deuda documentada, matriz de responsabilidad). Resumen: removida la creación automática de Cliente/Proveedor al importar un documento (reemplazada por resolución de solo lectura por NIT); removidos 8 endpoints de negocio ajeno (`vincular-cliente`, `vincular-proveedor`, `vincular-cotizacion`, `obtener-retenciones`, `inventario-catalogo`, `trazabilidad-inventario`, `importar-ubl`, `materialize`); removida la lógica de `estado_pago` forzado por conciliación bancaria (frontend + backend). **Dejados intactos deliberadamente** (consumidores reales activos, sin migrar aún, documentados como deuda explícita): `BancosBridge`/`Factura.total_pagado_bancos`/`saldo_pendiente`/`FacturaInterAppAPI.recalcular_estado_pago_automatico()`, `crear_factura_desde_venta()`, y `_generar_entrada_devolucion()` (escritura de Kardex desde Nota Crédito, feature v3.27 con tests dedicados). |
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
6. ~~**Bancos (Pull Model, v3.11.0)**: `BancosBridge.obtener_total_conciliado()` → suma ABS(valor) de transacciones bancarias conciliadas. `@property total_pagado_bancos` + `@property saldo_pendiente` en `Factura`.~~ **[REMOVIDO v4.0.0]** — Facturas ya no consulta Bancos; ver "Integración con Otros Módulos".
7. ~~**Estado pago automático (v3.11.0)**: Al conciliar transacción bancaria → `FacturaInterAppAPI.recalcular_estado_pago_automatico()` recalcula estado_pago sin acción manual. Solo aplica si `medio_pago_codigo != '10'` (efectivo).~~ **[REMOVIDO v4.0.0]** — `estado_pago` es hoy un campo manual simple.
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
| ~~`obtener_retenciones_desde_cliente(cliente_nit, empresa_id)`~~ | ~~Lee config retenciones del cliente (Pull Model)~~ **[REMOVIDO v4.0.0]** |
| ~~`obtener_retenciones_desde_proveedor(proveedor_nit, empresa_id)`~~ | ~~Lee config retenciones del proveedor~~ **[REMOVIDO v4.0.0]** |
| `guardar_desde_dto(dto, xml_text, file_bytes, empresa_id)` | @atomic. Idempotente por CUFE. Crea/actualiza Factura + FacturaAnexos + items. **v4.0.0**: ya no crea Cliente/Proveedor — solo resuelve uno existente por NIT (lectura). |
| `importar_documento(file_bytes, filename, preview, async_mode)` | Pipeline completo: parse XML → DTO → validar → persistir |
| `resumen(empresa_id)` | Wrapper de `FacturaSelectors.get_summary()` |
| **`actualizar_factura_limitado(factura, data, empresa_id)`** | DSV + rechaza `XML_IMMUTABLE_FIELDS` con 400 explícito. ~~+ validación estado_pago vs bancos (v3.11.0)~~ **[REMOVIDO v4.0.0]** — `estado_pago` es hoy un campo manual simple, sin lógica basada en conciliación bancaria. |
| ~~`vincular_cliente(factura, cliente_uuid, empresa_id)`~~ | ~~Solo VENTA. DSV ClienteBridge.~~ **[REMOVIDO v4.0.0]** — 0 consumidores reales (el endpoint dedicado `vincular-cliente` también fue removido). |
| ~~`vincular_proveedor(factura, proveedor_uuid, empresa_id)`~~ | ~~Solo COMPRA. DSV ProveedorBridge.~~ **[REMOVIDO v4.0.0]** — 0 consumidores reales (el endpoint dedicado `vincular-proveedor` también fue removido). |

**`actualizar_factura_limitado()` — Validación estado_pago (v3.11.0) — [REMOVIDO v4.0.0]:**

> **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15]** Bloque histórico — este código ya no existe en `actualizar_factura_limitado()`. Preservado como referencia.

```python
# [HISTÓRICO v3.11.0 -- eliminado en v4.0.0, no existe en el código actual]
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
| ~~**`recalcular_estado_pago_automatico(factura_uuid)`**~~ | ~~**v3.11.0** — Disparado por Bancos al conciliar~~ **[REMOVIDO v4.0.0]** |

**`recalcular_estado_pago_automatico()` — Reglas automáticas — [REMOVIDO v4.0.0]:**

> **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15]** Método histórico, eliminado por completo en v4.0.0 Fase 2. Bancos ya no dispara ningún recálculo en Facturas; su único punto de contacto hoy es una lectura pura vía `FacturaInterAppAPI.get_by_id()` (confirmado en `apps/tenant/bancos/services/crud_service.py::conciliar_transaccion()`). Bloque preservado como referencia histórica.

```python
# [HISTÓRICO v3.11.0 -- eliminado en v4.0.0, no existe en el código actual]
if factura.medio_pago_codigo == '10': return False  # Efectivo: usuario controla

total_bancos = factura.total_pagado_bancos
saldo        = factura.saldo_pendiente

if saldo <= 0 and total_bancos > 0:  → estado_pago = 'PAGADA'
elif total_bancos > 0 and saldo > 0: → estado_pago = 'PAGO_PARCIAL'
else:                                 → estado_pago = 'NO_PAGADA'

factura.save(update_fields=['estado_pago'])
```

> ~~**Disparador**: `TransaccionBancariaCRUDService.conciliar_transaccion()` en Bancos llama este método tras cada PATCH `/conciliar/`.~~ **[REMOVIDO v4.0.0]** — ya no hay disparador; ver nota arriba.

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
| ~~`ImportUBLSerializer`~~ | ~~POST upload XML (text)~~ | **[REMOVIDO v4.0.0]** — único consumidor era el endpoint `importar-ubl`, también removido |
| `UploadUBLFileSerializer` | POST upload file | `file` (FileField, required) |
| `MailIngestionRunCreateSerializer` | POST ingesta correo | `config_id` (int), `limit_messages` (int, optional) |
| `MailIngestionRunListSerializer` | GET runs correo | 7 campos read-only |
| `NotaCreditoListSerializer` | GET NC list | Incluye `factura_numero`, `factura_cufe` |
| `NotaCreditoDetailSerializer` | GET NC detail | Completo |
| ~~`CatalogoItemInventarioSerializer`~~ | ~~GET `inventario-catalogo`~~ | **[REMOVIDO v4.0.0]** — único consumidor era el endpoint `inventario-catalogo`, también removido |

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
| ~~`/api/v1/facturas/materialize/`~~ | ~~POST~~ | **[REMOVIDO v4.0.0]** duplicaba `create-from-dto`, ya marcado DEPRECATED en el propio código, 0 consumidores reales |
| `/api/v1/facturas/summary/` | GET | resumen neto (Ventas - NC) |
| `/api/v1/facturas/{uuid}/xml/` | GET | obtener XML UBL |
| `/api/v1/facturas/{uuid}/app-response/` | GET | obtener ApplicationResponse DIAN |
| ~~`/api/v1/facturas/vincular-cotizacion/`~~ | ~~POST~~ | **[REMOVIDO v4.0.0]** — `cotizacion_uuid` sigue editable vía PATCH estándar (campo de referencia documental), solo se removió la acción dedicada de "vincular" |
| ~~`/api/v1/facturas/vincular-cliente/`~~ | ~~POST~~ | **[REMOVIDO v4.0.0]** — 0 consumidores reales |
| ~~`/api/v1/facturas/vincular-proveedor/`~~ | ~~POST~~ | **[REMOVIDO v4.0.0]** — 0 consumidores reales |
| `/api/v1/facturas/por-estado/` | GET | **No documentado hasta v3.12.0** — listado agrupado/filtrado por `estado` |
| `/api/v1/facturas/{uuid}/cambiar-estado/` | POST | **No documentado hasta v3.12.0** — transición de `estado` (BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ANULADA) |
| `/api/v1/facturas/lista-centro-costos/` | GET | **Deuda pendiente v4.0.0**: candidato a REMOVE por la misión (responsabilidad de Proyectos), pero tiene un consumidor externo real (`proyectos.api.js:fetchCentrosCostos()`) — quedó fuera de alcance, no migrado |
| ~~`/api/v1/facturas/obtener-retenciones/`~~ | ~~GET~~ | **[REMOVIDO v4.0.0]** — 0 consumidores reales, solo su propio test (también removido) |
| ~~`/api/v1/facturas/inventario-catalogo/`~~ | ~~GET~~ | **[REMOVIDO v4.0.0]** — único consumidor era `factura_inventario_vinculacion.js`, también removido |
| ~~`/api/v1/facturas/{uuid}/trazabilidad-inventario/`~~ | ~~GET~~ | **[REMOVIDO v4.0.0]** — 0 consumidores reales |
| `/api/v1/facturas/buscar-para-movimiento/` | GET | Lectura pura, consumidores reales en Compras/Ventas/Inventario — correcto tal cual, no tocado |

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
| `FacturaUBLMixin` | Endpoints UBL: upload, parse, create-from-dto (`importar-ubl`/`materialize` removidos v4.0.0) |
| `FacturaMailMixin` | Endpoints ingesta correo: run, cancel, preview |
| `FacturaXMLMixin` | Endpoints descarga XML: ubl, application-response |

---

## Frontend

### JavaScript (`static/js/facturas/`) — 6 módulos vigentes (histórico decía 7, ver nota v4.0.0)

> **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15]** Esta tabla es contenido histórico v3.12.0. `features/factura_inventario_vinculacion.js` fue **eliminado por completo** en v4.0.0 (225 líneas, único consumidor del endpoint `inventario-catalogo`, también removido) — confirmado (`git status` muestra el archivo como `D`, y `grep` repo-wide no encuentra referencias vivas). La fila se deja abajo marcada `[REMOVIDO v4.0.0]` en vez de borrarse, por la misma regla de no reescribir historial que ya usa el resto de este documento.

| Archivo | Responsabilidad |
|---|---|
| `facturas.api.js` | SSoT endpoints. `window.http()` para todas las llamadas. |
| `facturas.components.js` | Componentes reutilizables (badges, formatters) |
| `facturas_main.js` | Orquestador principal. `tab-activated` listener. |
| `features/facturas_list.js` | **Corregido v3.12.0** — el grid Tabulator fue **retirado** (Fase 5-BIS): el listado ahora es `FacturaTableView`/`FacturaTable` server-rendered (ver sección dedicada arriba). Este archivo retiene filtros/acciones y el listener de detalle vía HTMX (`gestor-offcanvas`) — ya no inicializa ningún grid. |
| `features/facturas_editor.js` | Form editar. ~~**v3.11.0**: `initResumenPagosBancos(form)` — lee `data-total-pagado-bancos` y `data-saldo-pendiente` del form; bloquea `#factura-estado-pago` según reglas medio_pago/bancos~~ **[REMOVIDO v4.0.0]** — ver nota abajo. |
| `features/ver_detalle_factura.js` | Panel detalle read-only |
| ~~`features/factura_inventario_vinculacion.js`~~ | ~~Vinculación ítems con Inventario (autocomplete)~~ **[REMOVIDO v4.0.0]** — archivo eliminado (225 líneas), único consumidor del endpoint `inventario-catalogo`, también removido. |

**`initResumenPagosBancos(form)` — v3.11.0 — [REMOVIDO v4.0.0]:**

> **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15]** Este bloque documenta un comportamiento histórico (v3.11.0) que ya no existe en el código. La reestructuración v4.0.0 (2026-09-14, ver sección al inicio de este archivo) eliminó `initResumenPagosBancos()` de `facturas_editor.js` junto con `Factura.total_pagado_bancos`/`saldo_pendiente` y `BancosBridge`. `estado_pago` es hoy un campo manual simple sin lógica automática basada en conciliación bancaria. Se preserva el bloque original abajo sin reescribir, marcado como histórico.

```javascript
// [HISTÓRICO v3.11.0 -- ya no existe, ver nota arriba]
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
| `offcanvas_editar_factura.html` | Form editar campos `MANUAL_EDITABLE_FIELDS`. ~~**v3.11.0**: `data-total-pagado-bancos` y `data-saldo-pendiente` inyectados en `<form>`. Tarjeta "Conciliación Bancaria" con KPIs.~~ **[REMOVIDO v4.0.0]** — el bloque "Resumen de Pagos Bancos" fue removido del template. |
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

### 4. ~~Pull Model Bancos (v3.11.0)~~ [REMOVIDO v4.0.0, ver nota]

> **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15]** Patrón histórico (v3.11.0), eliminado por completo en la reestructuración v4.0.0 (2026-09-14, Fase 2): `total_pagado_bancos`, `saldo_pendiente` y `BancosBridge` ya no existen en el código (confirmado por `grep` repo-wide — 0 referencias vivas fuera de comentarios explicativos). Facturas ya no lee de Bancos. El código de abajo se preserva como referencia histórica, no como estado actual.

```python
# [HISTÓRICO v3.11.0 -- eliminado en v4.0.0, no existe en el código actual]
# @property en Factura — lazy query a Bancos via Bridge
@property
def total_pagado_bancos(self) -> Decimal:
    from apps.tenant.facturas.services.selectors import BancosBridge
    return BancosBridge.obtener_total_conciliado(self.empresa_id, self.uuid)
```

### 5. ~~Auto-recálculo estado_pago (v3.11.0)~~ [REMOVIDO v4.0.0, ver nota]

> **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15]** Igual que el patrón #4: `FacturaInterAppAPI.recalcular_estado_pago_automatico()` fue eliminado en v4.0.0 Fase 2. Bancos ya no dispara ningún recálculo de `estado_pago` en Facturas; hoy es un campo manual simple. Bloque preservado como referencia histórica.

```
[HISTÓRICO v3.11.0 -- eliminado en v4.0.0, no existe en el código actual]
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
| ~~Pull Model Bancos → BancosBridge~~ **[REMOVIDO v4.0.0]** — Facturas ya no lee de Bancos; Bancos lee Facturas vía `FacturaInterAppAPI.get_by_id()` (dirección correcta) | ADR-001 §18 | ✅ |
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
| FAC-DT-04 | ~~Bancos v3.11.0~~ | ~~MEDIA~~ | ~~`total_pagado_bancos` / `saldo_pendiente` son `@property` con query por llamada — N+1 si se serializa en list con muchas facturas.~~ | **RESUELTO v4.0.0 — [Fase 2, 2026-09-14] ambas properties fueron eliminadas por completo, el N+1 ya no existe porque el dato ya no existe en Facturas** |
| FAC-DT-05 | `Factura.xml_content` | BAJA | Campo DEPRECATED — usar `FacturaAnexos.ubl_xml`. Eliminar en future migration. | **ABIERTO** |
| FAC-DT-06 | `business_service.py::_generar_entrada_devolucion` | ALTA | Facturas escribe directamente `MovimientoInventario` (Kardex) al procesar una Nota Crédito con items resolubles — viola el alcance documental de v4.0.0 (§14 de la misión), pero es una feature versionada v3.27 con 5 tests dedicados que cierra un gap de negocio real (devoluciones no ajustaban stock antes). Migrar requiere que Inventario consuma el hecho documental (NC con items) en vez de que Facturas empuje el movimiento. | **ABIERTO — deuda documentada v4.0.0, no ejecutada deliberadamente** |
| FAC-DT-07a | ~~`FacturaInterAppAPI.recalcular_estado_pago_automatico` + `BancosBridge`~~ | ~~ALTA~~ | ~~Consumidor real activo (Bancos) sin migrar.~~ | **RESUELTO v4.0.0 — [Fase 2, 2026-09-14] eliminados por completo, Bancos migrado a lectura pura vía `FacturaInterAppAPI.get_by_id()`, ver `apps/tenant/bancos/.agent/AUDITORIA_FLUJO_COMPLETO.md` §"v3.0.1"** |
| FAC-DT-07b | `business_service.py::crear_factura_desde_venta` | MEDIA (bajada de ALTA) | Único camino interno de creación de `Factura` desde `Ventas`. [Fase 3, 2026-09-14] Evaluado con evidencia: `EMISION_FISCAL_VENTA_AUTORIZADA=False` hace la ruta estructuralmente inalcanzable hoy en producción (0 acoplamiento vivo), pero 5 archivos de test (ventas+cotizaciones) mockean el flag para seguir ejercitando el pipeline DIAN completo — remover exigiría reescribir esa cobertura legítima a cambio de un beneficio marginal. Ver sección "v4.0.0 — Deuda arquitectónica" al inicio de este archivo. | **ABIERTO — Gate F3 satisfecha por evidencia, sin borrado de código, decisión documentada** |

---

## Integración con Otros Módulos

| Módulo | Tipo | Contrato |
|---|---|---|
| **Contabilidad** | Pull Model — Contabilidad lee de Facturas | `ExtractorFacturas` extrae datos. Facturas NUNCA importa Contabilidad. |
| **Retenciones** | Pull Model — Facturas lee de Contabilidad | `@property total_retencion_fuente/reteica/reteiva` → `Retencion` table. |
| **Bancos** | Pull Model — Bancos lee de Facturas (dirección correcta) | ~~`BancosBridge.obtener_total_conciliado()` → `TransaccionBancaria`. Auto-recálculo via `FacturaInterAppAPI`. **⚠️ Deuda documentada v4.0.0**...~~ **[RECONCILIADO RELEASE-CLOSE-01, 2026-09-15] Esta fila describía deuda ya resuelta.** `BancosBridge`, `total_pagado_bancos`, `saldo_pendiente` y `recalcular_estado_pago_automatico()` fueron eliminados por completo en v4.0.0 Fase 2 (2026-09-14) — confirmado sin referencias vivas repo-wide. Hoy Bancos lee Facturas vía `FacturaInterAppAPI.get_by_id()` (solo lectura, dirección correcta), ver `apps/tenant/bancos/.agent/AUDITORIA_FLUJO_COMPLETO.md` §"v3.0.1". Ver también FAC-DT-07a (RESUELTO) en "Deudas Técnicas". |
| **Ventas** | Push: Ventas escribe una Factura | `FacturaBusinessService.crear_factura_desde_venta(empresa, dto)` — único caso del módulo donde otra app crea una `Factura` directamente (no soft-reference, no Pull Model). El DTO viene de `VentaBusinessService._construir_dto_factura()`. **⚠️ Deuda documentada v4.0.0**: la misión pide que "Ventas no cree Factura mediante FacturaBusinessService" — NO se tocó porque es la única vía interna de creación hoy; eliminarla detiene la facturación automática (cambio de comportamiento visible, requiere decisión de negocio). |
| **Clientes** | Soft reference, solo lectura | `cliente_uuid` + `ClienteBridge` sin FK. **v4.0.0**: `guardar_desde_dto()` ya NO crea Cliente — solo resuelve uno existente por NIT (lectura); si no existe, `cliente_uuid` queda `None`. |
| **Proveedores** | Soft reference, solo lectura | `proveedor_uuid` + `ProveedorBridge` sin FK. **v4.0.0**: mismo cambio que Clientes — solo resuelve, nunca crea. |
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

**Última Actualización (contenido v3.12.0 original):** 2026-08-07 (re-validación completa contra código real)
**Última Actualización (vigente):** 2026-09-14 — v4.0.0, reestructuración arquitectónica (ver sección al inicio del archivo)
**Auditor:** Claude Sonnet 5 (Anthropic)
**Status vigente:** READY FOR VALIDATION — ver "v4.0.0 — Estado real de la verificación" al inicio de este archivo para el resultado real de la suite de tests. El "✅ PRODUCTION READY" de abajo describe el estado en 2026-08-07, antes de esta reestructuración — no usar como estado actual.
