# APP_cotizaciones_AUDIT — Auditoria integral (app 10/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> ventas
-> **cotizaciones** -> proyectos -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/cotizaciones` tiene `.agent/AUDITORIA_FLUJO_COMPLETO.md`
(v3.10.3, 2026-05-25, 555 lineas, "OPERATIVO, 0 CRITICOS") mas 11
documentos en `documentacion/_archive/` (historial de refactors
v2.40->v2.62, migracion a modo "User-Driven", limpieza v2.60) -- app
con el historial de refactor mas extenso auditado hasta ahora, similar
en ese sentido a `empresa`.

**Correccion a `APP_AUDIT_MATRIX.md` (FASE 1):** la matriz conto **4
modelos** (grep de `models.py` en la raiz: `Producto`, `Servicio`,
`Cotizacion`, `CotizacionItem`), pero **falta `ConfiguracionCotizacion`**,
que vive fisicamente en `configuracion/models.py` (submodulo FSD
separado, mismo `app_label='tenant_cotizaciones'` y mismas
migraciones -- es el MISMO app de Django, no un app distinto). Total
real: **5 modelos concretos**.

Resumen de negocio: cotizaciones con DNA dinamico heredado de
`ConfiguracionCotizacion` (prefijo/sufijo/dias_validez), snapshot
pattern en items (precio/utilidad persisten independiente del
catalogo), motor AIU+IVA centralizado en
`CotizacionService.calcular_totales()`, generacion de PDF, numeracion
atomica por perfil (`select_for_update()`).

## FASE C/D/K — Service Layer y codigo muerto (CONFIRMADO Y CORREGIDO)

Estructura: `services/{selectors,crud_service,business_service,
api_mixins,item_service,producto_service,servicio_service,
pdf_export_service}.py` mas el submodulo `configuracion/services/`
(propio, FSD completo para CRUD de perfiles) -- confirmado NO
duplicativo con el `business_service.py` principal (que solo hace
lookup DSV read-only de la configuracion al crear una cotizacion, via
`get_configuracion_for_empresa()`; el submodulo `configuracion/`
gestiona el CRUD admin de los perfiles en si). Mismo patron legitimo
que se vio en `empresa` (Sede/Area) -- responsabilidades distintas,
sin solapamiento.

**Encontrado codigo muerto real: paquete completo `services/pdf/`**
(`__init__.py`, `generator.py`, `service.py`) -- un pipeline PDF
COMPLETO Y PARALELO al que realmente se usa. Investigacion de
consumidores (grep repo-wide de cada nombre de funcion/clase):

- `services/pdf_export_service.py:CotizacionPDFExportService` --
  **REAL**, importado por `services/__init__.py`, usado por
  `services/business_service.py` (dentro de `crear_preforma()`) y por
  `api/viewsets.py` (endpoint de descarga de PDF).
- `services/pdf/service.py` (`obtener_cotizacion_para_pdf`,
  `preparar_contexto_pdf`, `render_to_pdf`, `generar_pdf_bytes`) y
  `services/pdf/generator.py` (`CotizacionPDFGenerator`) --
  **CERO consumidores en todo el repo** fuera de su propio paquete
  (`pdf/service.py` importa `pdf/generator.py` internamente, pero
  nada fuera de `services/pdf/` importa ninguno de los dos).
  `services/__init__.py` (el punto de entrada real del paquete
  `services/`) **nunca importa desde `.pdf`** -- confirma que es un
  segundo pipeline de generacion de PDF (misma logica de AIU/IVA,
  mismo template `formato_profesional.html`) que quedo huerfano de un
  refactor anterior (consistente con el historial extenso de refactors
  v2.60/v2.62 documentado en `_archive/`).

**DEAD_CONFIRMED, eliminado:** `apps/tenant/cotizaciones/services/pdf/`
completo (3 archivos, ~180 lineas: `__init__.py`, `generator.py`
54 lineas, `service.py` 122 lineas).

`item_service.py`, `producto_service.py`, `servicio_service.py` --
verificados, todos exportados en `services/__init__.py` con
consumidores reales (selectors + mixins usados por los ViewSets
correspondientes). No se tocan.

## FASE J — Frontend

Nota de contexto: `git status` muestra WIP preexistente sin commitear
en `configuracion/viewsets.py` y `tests/test_api.py` -- ajeno a esta
mision, no se toca ni se commitea.

## FASE M — Normativa colombiana

`cotizaciones` NO esta en la lista explicita de apps que requieren
matriz normativa (`facturas, contabilidad, empleados, gastos, compras,
proveedores, ventas, clientes, bancos`). **NO_APLICA.** (El motor
AIU/IVA calcula porcentajes configurables por el usuario, sin
validacion contra tarifas DIAN especificas -- mismo patron ya
documentado como deferred de baja prioridad en `compras`/`ventas`, no
se repite aqui por no ser una app en la lista formal, pero queda
como observacion informal si se retoma en una fase posterior).

## FASE Q — Tests / Regresion

Tests coleccionados: `apps/tenant/cotizaciones/tests/`. Regresion
lanzada en background tras confirmar `db`/`redis` healthy, sobre el
working tree (incluye el WIP preexistente de `test_api.py`).

## Deferred

Ninguno nuevo mas alla de lo ya mencionado informalmente en FASE M
(no aplica formalmente a esta app).

## FASE X — Release Gate (checklist)

- [x] Modelos verificados y corregidos contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, codigo muerto encontrado y eliminado (FASE C/D/K)
- [x] Frontend: WIP ajeno identificado y no tocado (FASE J)
- [x] Normativa colombiana evaluada (FASE M -- NO_APLICA formalmente)
- [x] `py_compile`/`ast.parse` limpio en los archivos afectados
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [ ] Regresion de la app -- **PENDIENTE**, en curso en background
- [x] Sin deferred items formales pendientes

## FASE Y — Decision

**PENDIENTE DE CIERRE** -- bloqueado por el resultado de la regresion
en curso. Se espera `COMPLETED` puro (sin items normativos formales,
el hallazgo de codigo muerto ya fue corregido) si la regresion
confirma 0 fallos.
