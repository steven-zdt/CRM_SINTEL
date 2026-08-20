# APP_inventario_AUDIT — Auditoria integral (app 7/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> proveedores
-> **inventario** -> compras -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/inventario` tiene `.agent/AUDITORIA_FLUJO_INVENTARIO.md`
(v3.10.2, 2026-05-28, 709 lineas, "PRODUCTION READY, 0 CRITICOS") mas
`AUDITORIA_INTEGRACION_INVENTARIO_CONTABILIDAD.md` y
`RESUMEN_AUDITORIA_INVENTARIO_v371.md` -- usados como fuente primaria.

**Correccion a `APP_AUDIT_MATRIX.md` (FASE 1):** la matriz conto solo
**1 modelo** para `inventario` via el grep automatico
(`^class .*SintelTenantBaseModel|^class .*(models.Model)`), pero el
conteo real es **6 modelos concretos** (`CategoriaItem`, `ActivoFijo`,
`Producto`, `Servicio`, `MovimientoInventario`, `HistorialServicio`)
mas 1 abstracto (`TimeStampedModel`) -- todos heredan de
`TimeStampedModel(SintelTenantBaseModel)`, un nivel de indireccion que
el regex de la matriz no capturaba (la matriz ya advertia esta
limitacion explicitamente: "puede subcontar si hay modelos definidos
... via herencia indirecta"). Se corrige aqui para que quede
documentado con precision.

Resumen de negocio: catalogo multitipo (Producto/Servicio/ActivoFijo),
motor Kardex (`KardexService`, `select_for_update()`, movimientos
append-first, `stock_actual` desnormalizado recalculado atomicamente),
desacoplamiento contable completo (campos `cuenta_*_uuid` eliminados
en migracion 0009 -- Contabilidad es la unica propietaria de mapeos
PUC via Pull Model), ingesta masiva desde Excel, y
`get_movimientos_timeline()` como **contrato autorizado unico** que
usa Contabilidad para leer movimientos (Productos + Activos +
Servicios combinados) -- Contabilidad nunca consulta `Producto`/
`Servicio`/`ActivoFijo` directamente.

## FASE C/D/K — Service Layer y codigo muerto

Estructura limpia: `services/{selectors,crud_service,business_service,
ingesta_service,api_mixins}.py` (5 archivos, coincide con matriz).
**Sin `services/services.py`** (a diferencia de `clientes`/`proveedores`
-- esta app nunca tuvo esa capa de backward-compatibility, o ya fue
removida en una limpieza anterior no documentada). **Sin `api/mixins.py`
separado de `services/api_mixins.py`** (a diferencia de `perfil`, que
tenia esa duplicacion intencional para evitar import circular) --
un solo archivo, sin riesgo de confusion entre versiones.

Grep de `deprecad`/`legacy` en todo `apps/tenant/inventario/`
(excluyendo tests): un unico hit, un comentario de docstring
("formularios legacy" en `api/serializers.py:53`) que describe un
campo de serializer que ACEPTA tanto UUID publico como PK interno --
no es codigo muerto, es una compatibilidad de INPUT deliberada y
documentada, no un resto de refactor.

**Conclusion FASE K: 0 lineas de codigo muerto confirmado.** Tercera
app consecutiva (junto con `perfil`, `empleados`, `proveedores`) sin
hallazgos de limpieza -- de las 7 apps auditadas hasta ahora, 4 no
requirieron eliminacion de codigo (`perfil`, `empleados`, `proveedores`,
`inventario`) y 3 si (`core`, `empresa`, `clientes`).

## FASE J — Frontend

Nota de contexto: `git status` muestra WIP preexistente sin commitear
en `templates/tenant/inventario/list_inventario.html` y
`list_movimientos.html`, y varios tests nuevos sin trackear
(`test_organizational_context_adoption.py`,
`test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`,
`test_scope_selectors_f7.py`, `tests/__init__.py`) -- mismo patron
de trabajo de alcance organizacional (F7/F8/F13/F14) visto en
`empleados`, ajeno a esta mision, no se toca ni se commitea.

`urls.py` verificado, wireado correctamente en
`config/urls_tenant.py:179`.

## FASE M — Normativa colombiana

`inventario` NO esta en la lista explicita de apps que requieren
matriz normativa (`facturas, contabilidad, empleados, gastos, compras,
proveedores, ventas, clientes, bancos`). **NO_APLICA.**

## FASE Q — Tests / Regresion

25 tests coleccionados (`apps/tenant/inventario/tests/`, incluye los 4
archivos nuevos de scope/alcance sin commitear). Regresion ejecutada:
**25 passed, 0 failed, 6 warnings preexistentes (min_value DRF +
`format_html()` sin args, ya vistos en apps anteriores) en 5210.10s
(1:26:50)**. Incluye `test_scope_isolation_f14.py` (WIP ajeno a esta
mision) -- verde, sin conflicto con esta auditoria.

## Deferred

Ninguno nuevo generado por esta auditoria.

## FASE X — Release Gate (checklist)

- [x] Modelos verificados y corregidos contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto encontrado (FASE C/D/K)
- [x] Frontend verificado, WIP ajeno identificado y no tocado (FASE J)
- [x] Normativa colombiana evaluada (FASE M -- NO_APLICA)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 25 passed, 0 failed
- [x] Sin deferred items pendientes de documentar

## FASE Y — Decision

**COMPLETED** -- 25/25 tests pasan, 0 regresiones, 0 codigo muerto, 0
items deferred.
