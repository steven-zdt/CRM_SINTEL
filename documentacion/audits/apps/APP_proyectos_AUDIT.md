# APP_proyectos_AUDIT — Auditoria integral (app 11/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> cotizaciones
-> **proyectos** -> gastos -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/proyectos` tiene `.agent/AUDITORIA_FLUJO_COMPLETO.md`
(v3.10.5, 2026-08-05 -- solo 2 semanas antes de esta auditoria, la
mas reciente vista hasta ahora, "PRODUCTION READY, 0 criticos/
importantes/menores", roadmaps M3/M4/M5 completados + 8 critical
fixes de sesion 2026-05-20 ya resueltos) -- usada como fuente primaria.

**Verificado 1:1:** 7 modelos (`Proyecto`, `AsignacionPersonal`,
`PedidoProyecto`, `ItemPedido`, `ItemPresupuestoProyecto`,
`TareaDiariaProyecto`, `TareaCorta`), coincide con
`APP_AUDIT_MATRIX.md`.

Resumen de negocio: gestion de proyectos con maquina de estados de
edicion granular (fase CIERRE bloquea campos criticos/financieros),
presupuesto manual (`ItemPresupuestoProyecto`, cache de
costo/utilidad/margen planeado recalculado atomicamente), indicadores
P&L (`calcular_indicadores_financieros`), asignacion de personal y
pedidos, tareas diarias/cortas. Nota curiosa ya documentada por la app
misma: `ItemPresupuestoViewSet` usa `lookup_field='id'` (no `uuid`)
-- desviacion deliberada de la regla UUID-lookup, revertida a proposito
tras un bug real (Critical Fix #3-5 del `.agent/` doc, sesion
2026-05-20) -- no se re-abre esa decision aqui.

## FASE C/D/K — Service Layer y codigo muerto (CONFIRMADO Y CORREGIDO)

**Encontrado codigo muerto real: colision de nombres entre
`api/mixins.py:ProyectoServiceMixin` (el que SI se usa) y
`services/api_mixins.py:ProyectoServiceMixin` (sombra, sin
consumidores).** Mismo patron de riesgo que `perfil` (que evito
correctamente esta colision con un stub vacio documentado) pero aqui
la colision SI resulto en una clase completa y funcional que nunca se
ejecuta:

- `api/viewsets.py:25` importa `ProyectoServiceMixin` desde `.mixins`
  (`api/mixins.py`) -- version simple, basada en properties sobre el
  modulo `services` (`services.qs_list`, `services.business_service`,
  etc.). Esta es la que **realmente usa** `ProyectoViewSet`.
- `services/api_mixins.py` definia OTRA `ProyectoServiceMixin(BaseServiceMixin)`
  con metodos `service_crear_proyecto`/`service_actualizar_proyecto` --
  **cero consumidores confirmados con grep repo-wide** (nadie importa
  `ProyectoServiceMixin` desde `services.api_mixins` ni desde el
  paquete `services` reexportado). Su propio docstring interno decia
  *"Service mixin para Gasto ViewSet"* -- evidencia de copy-paste
  desde otra app (`gastos`) nunca adaptado ni conectado.
- `TareaCortaServiceMixin`, definida en el MISMO archivo, **SI es
  real** -- usada por `TareaCortaViewSet` via el paquete `services`.
  Por eso no se elimino el archivo completo, solo la clase muerta.

**DEAD_CONFIRMED, eliminado:**
`services/api_mixins.py:ProyectoServiceMixin` (25 lineas) + sus
imports huerfanos asociados (`LIST_FIELDS`, `DETAIL_FIELDS`,
`qs_list`, `qs_detail` de `selectors.py`; `calcular_indicadores_
financieros` de `business_service.py`; `save_proyecto`,
`delete_proyecto` de `crud_service.py` -- estos ultimos dos ya estaban
importados sin usarse en absoluto dentro del archivo, un hallazgo
menor adicional). `services/__init__.py` actualizado para dejar de
reexportar la clase eliminada.

Verificado con `py_compile`/`ast.parse`: ambos archivos compilan
limpio tras el cambio. `orchestrate_create_proyecto`/
`orchestrate_update_proyecto` (las funciones reales que la clase
muerta intentaba envolver) siguen usandose correctamente via
`api/mixins.py`'s `proyecto_business_service` property -- confirmado
con grep, sin cambio de comportamiento.

## FASE M — Normativa colombiana

`proyectos` NO esta en la lista explicita de apps que requieren
matriz normativa. **NO_APLICA.**

## FASE Q — Tests / Regresion

58 tests coleccionados (`apps/tenant/proyectos/tests/`). Regresion
ejecutada: **56 passed, 2 skipped, 0 failed, 1 warning preexistente
(min_value DRF) en 6506.80s (1:48:26)**. Los 2 skips
(`TestServicioAsociado::test_dsv_asociar_servicio_otro_tenant`,
`test_serializer_queryset_filtrado_por_empresa`, ambos en
`test_legacy_smoke_financials.py`) son preexistentes, no relacionados
con el cambio de esta auditoria. `test_legacy_smoke_financials.py`
(que ejercita directamente `orchestrate_create_proyecto`/
`orchestrate_update_proyecto`, las funciones reales cerca de donde se
elimino la clase sombra) -- todos los tests no-skip PASSED, confirma
que el cambio no afecto el codigo real.

## Deferred

Ninguno nuevo.

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, codigo muerto encontrado y eliminado (FASE C/D/K)
- [x] Normativa colombiana evaluada (FASE M -- NO_APLICA)
- [x] `py_compile`/`ast.parse` limpio en los archivos editados
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 56 passed, 2 skipped preexistentes, 0 failed
- [x] Sin deferred items pendientes de documentar

## FASE Y — Decision

**COMPLETED** -- 0 fallos, 0 regresiones causadas por el cambio de
esta auditoria. Los 2 skips son preexistentes y no relacionados.
