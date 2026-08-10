# F24 — Hallazgos

**Fecha:** 2026-08-10

Formato por hallazgo: ID, Severidad, App, Archivo, Linea, Descripcion, Evidencia,
Impacto, Reproduccion, Correccion, Test, Estado.

---

## F24-001 — Atomicidad rota en `confirmar_recepcion()` (compras)

- **Severidad:** HIGH
- **App:** compras
- **Archivo:** `apps/tenant/compras/services/business_service.py`
- **Linea:** 563-567 (antes de la correccion)
- **Descripcion:** `confirmar_recepcion()` esta decorado `@transaction.atomic` y procesa
  varios `RecepcionCompraItem` en un loop. Su `except ValidationError`/`except Exception`
  capturaba la excepcion y retornaba `(False, ..., 400/500)` **sin volver a lanzarla y
  sin `transaction.set_rollback(True)`**. Si el item N (N>1) fallaba validacion
  DESPUES de que el item N-1 ya hubiera escrito su `ItemOrdenCompra.cantidad_recibida`
  y su `MovimientoInventario(ENTRADA_COMPRA)` real, Django confirmaba (commit) esas
  escrituras igual, porque la excepcion nunca escapo de la funcion decorada.
- **Evidencia:** Escaneo AST de todos los `@transaction.atomic` en
  `compras/inventario/ventas/facturas` buscando `except` con `return` sin `raise` ni
  `set_rollback` (mismo patron que el bug que F23 encontro y corrigio en
  `procesar_y_facturar_venta()`, ver `F23_FINAL_REPORT.md` #3). Reproducido con un
  test real: recepcion con 2 items, el segundo simulando una condicion de carrera
  (otra recepcion concurrente ya confirmo casi todo el cupo de ese item) --
  `apps/tenant/compras/tests/test_f24_confirmar_recepcion_atomicidad.py`.
- **Impacto:** Compromete la integridad del Kardex (F21): un `MovimientoInventario`
  real y un `ItemOrdenCompra.cantidad_recibida` quedaban persistidos pese a que la
  API reportaba `ok=False`, produciendo stock fantasma no reflejado en la respuesta
  al usuario ni en el estado de la `RecepcionCompra` (que seguia en BORRADOR).
- **Reproduccion:** Ver `test_fallo_en_segundo_item_revierte_por_completo_el_primero`.
  Confirmado ANTES/DESPUES: revirtiendo el fix (`git stash`) el test falla
  (`item_a.cantidad_recibida == Decimal('20.00')` en vez de `0.00`, 1 movimiento
  fantasma) en `245.63s`; con el fix, `2 passed in 242.56s`.
- **Correccion:** `transaction.set_rollback(True)` agregado en los 2 `except` de
  `confirmar_recepcion()` y en el unico `except` de `anular_recepcion()` (misma clase
  de riesgo, fix defensivo de bajo costo aplicado por consistencia dentro del mismo
  flujo F21).
- **Test:** `apps/tenant/compras/tests/test_f24_confirmar_recepcion_atomicidad.py`
  (2/2 pasan).
- **Estado:** FIXED, VERIFIED.

---

## F24-002 — `PeriodoCerradoError` referenciaba un atributo inexistente (contabilidad)

- **Severidad:** MEDIUM
- **App:** contabilidad
- **Archivo:** `apps/tenant/contabilidad/integracion/validadores.py`
- **Linea:** 43 (antes de la correccion)
- **Descripcion:** `validar_periodo_abierto()` construia el mensaje de error con
  `f"Periodo {periodo.nombre} esta cerrado..."`, pero `PeriodoContable` (modelo real,
  `apps/tenant/contabilidad/models.py:568`) **no tiene** un campo `nombre` -- el campo
  real es `periodo` (CharField `YYYY-MM`). Al evaluar el f-string, Python lanzaba
  `AttributeError` en vez de construir el `PeriodoCerradoError` intencionado.
- **Evidencia:** Lectura directa del modelo (campos: `uuid`, `periodo`, `fecha_inicio`,
  `fecha_fin`, `estado`, `fecha_cierre`, `cerrado_por`, `observaciones` -- sin `nombre`)
  y de `validadores.py`. Confirmado con el test
  `test_f24_periodo_cerrado_rechaza_contabilizacion`
  (`apps/tenant/contabilidad/tests/test_f24_e2e_circuito_completo.py`).
- **Impacto:** El `AttributeError` SI era capturado por el `except Exception` generico
  de `AbstractExtractor.contabilizar_pendientes()` (que no distingue tipos de
  excepcion), por lo que la proteccion real -- ningun `AsientoContable` se crea en un
  periodo cerrado -- **nunca se vio comprometida**. El defecto era puramente de
  diagnostico: el mensaje de error reportado en `resultados['errores']` era
  `"'PeriodoContable' object has no attribute 'nombre'"` en vez de un mensaje claro de
  negocio ("Periodo 2026-08 esta cerrado..."), dificultando la operacion/soporte.
- **Correccion:** Un caracter: `periodo.nombre` -> `periodo.periodo`.
- **Test:** `test_f24_periodo_cerrado_rechaza_contabilizacion` (1/1 pasa, verifica
  `"cerrado"` en el mensaje de error y 0 `AsientoContable` creados).
- **Estado:** FIXED, VERIFIED.

---

## F24-003 — Mismo patron de atomicidad (except-return-sin-reraise) en otros 25 sitios

- **Severidad:** MEDIUM (no confirmado individualmente como explotable; ver nota)
- **App:** compras, ventas, facturas
- **Archivo/Linea:** ver lista completa abajo (deteccion via AST).
- **Descripcion:** El mismo escaneo AST que encontro F24-001 detecto 25 ocurrencias
  adicionales del patron `@transaction.atomic` + `except ... return` sin `raise` ni
  `transaction.set_rollback(True)`, fuera de `confirmar_recepcion`/`anular_recepcion`
  (ya corregidos) y de `procesar_y_facturar_venta` (ya corregido en F23):
  - `compras/services/business_service.py`: `crear_orden_compra`,
    `actualizar_orden_compra`, `cambiar_estado_orden_compra`, `eliminar_orden_compra`,
    `crear_recepcion`.
  - `ventas/services/business_service.py`: `crear_venta_borrador`, `anular_venta`,
    `crear_resolucion`, `actualizar_resolucion`, `eliminar_resolucion`.
  - `facturas/services/business_service.py`: `guardar_desde_dto` (multiples `except`
    dentro del mismo metodo).
- **Evidencia:** Escaneo AST reproducible (ver metodologia F24-001).
  `crear_recepcion` fue inspeccionado manualmente: toda la validacion ocurre antes de
  la unica escritura real (`RecepcionCompraCRUDService.crear_recepcion()` al final del
  metodo), por lo que no hay una segunda escritura previa que pudiera quedar
  comprometida -- riesgo bajo/teorico en ese caso especifico. Los demas 24 sitios
  **no fueron verificados individualmente uno por uno** (haria falta reproducir cada
  uno con un escenario de escritura-parcial-luego-fallo real, como se hizo para
  F24-001) dentro del alcance proporcionado de F24.
- **Impacto:** Mismo mecanismo que F24-001/F23#3: si alguno de estos metodos tiene una
  ruta con 2+ escrituras reales donde la segunda puede fallar despues de que la
  primera ya se ejecuto, el rollback no ocurriria. La mayoria de estos son operaciones
  CRUD de un solo objeto (bajo riesgo estructural), pero no se garantiza sin
  verificacion caso por caso.
- **Correccion:** NO aplicada en F24 (fuera del alcance quirurgico: aplicar 25 fixes
  sin verificar individualmente cada escenario de escritura-parcial viola la regla
  F24.45 de "reproducir -> causa raiz -> fix minimo -> test" por cada correccion, y
  la regla general de no agrupar multiples fixes no relacionados en un solo cambio).
- **Estado:** DEFERRED. Recomendacion: auditoria dedicada de atomicidad
  (`grep`/AST + verificacion caso por caso + test de regresion por cada uno), fuera
  de una fase de negocio especifica, ya sugerida en `F23_FINAL_REPORT.md` #15.

---

## F24-004 — `ventas -> facturas` clasificado `UNKNOWN` por el motor de governance

- **Severidad:** INFO
- **App:** ventas / facturas
- **Archivo:** `apps/tenant/ventas/services/business_service.py:576-591`
- **Descripcion:** 4 imports directos de servicios DIAN de `facturas`
  (`CufeService`, `UBL21BuilderService`, `XadesSignerService`, `AttachedDocumentService`)
  se clasifican `UNKNOWN` ("sin patron reconocido - requiere revision manual") porque
  el clasificador de `tools/organizational_governance/dependencies.py` solo reconoce
  imports de Selectors o imports-directo-con-filtro-empresa_id-cercano. Estos son
  servicios de firma/construccion XML sin estado (no requieren `empresa_id`), por lo
  que el patron no aplica.
- **Evidencia:** `discover_dependency_edges()` -- 4 edges `UNKNOWN`, 0 `FORBIDDEN` en
  total (375 edges). Pre-existente a F23 (mismo archivo que F23 explicitamente no
  toco, confirmado por `git show --stat` de los commits F23).
- **Impacto:** Ninguno funcional -- `FINAL STATUS: PASS` no se ve afectado
  (`UNKNOWN` no es `FORBIDDEN`). Limitacion de cobertura del clasificador, no un
  riesgo de arquitectura.
- **Correccion:** No aplica (no se modifica el motor de governance sin evidencia de
  que la regla general sea necesaria -- F24.61: reutilizar patrones existentes,
  no crear reglas nuevas salvo que sean claras/generales/no redundantes).
- **Estado:** FALSE_POSITIVE (del clasificador, no del codigo auditado).

---

## Resumen

| ID | Severidad | Estado |
|---|---|---|
| F24-001 | HIGH | FIXED, VERIFIED |
| F24-002 | MEDIUM | FIXED, VERIFIED |
| F24-003 | MEDIUM | DEFERRED |
| F24-004 | INFO | FALSE_POSITIVE |

0 findings CRITICAL sin corregir. 0 findings HIGH sin corregir. Ningun hallazgo
oculto: F24-003 se documenta explicitamente con su alcance no verificado, en vez de
declararse resuelto sin evidencia.
