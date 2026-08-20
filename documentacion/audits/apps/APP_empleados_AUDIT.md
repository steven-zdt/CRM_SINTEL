# APP_empleados_AUDIT — Auditoria integral (app 4/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: core -> empresa
-> perfil -> **empleados** -> clientes -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/empleados` ya cuenta con un `.agent/AUDITORIA_FLUJO_
EMPLEADOS.md` propio (v4.8.1, actualizado 2026-06-17, ~2 meses antes de
esta auditoria), extenso (546 lineas), reciente y de alta calidad --
se usa como **fuente primaria** para FASE A/B/C/D/G/H (mapa de negocio,
6 modelos, service layer, API, conformidad AGENTS.md) en vez de
re-derivar todo desde cero, siguiendo la instruccion de CLAUDE.md de
leer el `.agent/` doc de la app antes de cualquier cambio. Esta
auditoria se enfoca en: (1) verificar que las afirmaciones de ese doc
siguen vigentes contra el codigo actual, (2) FASE K (codigo muerto,
no cubierta por ese doc), (3) FASE M (matriz normativa formal,
requerida explicitamente por esta mision para `empleados` -- ver
`APP_empleados_NORMATIVE_MATRIX.md`), (4) FASE Q (regresion).

**Verificacion contra codigo actual:** confirmado 1:1 -- 6 modelos
(`Empleado`, `Contrato`, `Devengo`, `ResolucionDIAN`,
`TransmisionNominaDIAN`, `LiquidacionPrestacion`), 13 migraciones,
4 archivos de servicio (`selectors.py`, `crud_service.py`,
`business_service.py`, `api_mixins.py`), coincide con
`APP_AUDIT_MATRIX.md` (FASE 1) y con el `.agent/` doc.

Resumen de negocio (del `.agent/` doc, verificado): motor de nomina
colombiano (salario proporcional + auxilio + H.E./recargos − salud 4%
− pension 4%, 0 si `PRESTACION`), DSPNE (nomina electronica DIAN vía
`ResolucionDIAN`/`TransmisionNominaDIAN`, resolucion del empleado con
fallback a la de empresa, `select_for_update()` en consecutivo),
liquidacion de prestaciones sociales (prima/cesantias/intereses/
vacaciones), integracion contable via Pull Model (Contabilidad extrae
`Devengo`, empleados nunca importa Contabilidad -- ADR-001).

## FASE C/D/K — Service Layer y codigo muerto

**A diferencia de core/empresa, NO se encontro codigo muerto.**
Estructura limpia: sin `impl/` huerfano, sin shims de permisos sin
consumidores, sin modulos "legacy" desconectados. Verificado con:

- Grep de `deprecad`/`legacy`/`WARNING: LEGACY` en todo `apps/tenant/
  empleados/` (case-insensitive) -- el unico hit real es un comentario
  historico en `.agent/` sobre `cuenta_contable_uuid`, campo ya
  eliminado por las migraciones 0004/0010 (no es codigo vivo, es
  documentacion de una migracion ya aplicada).
- `services/__init__.py` exporta unicamente clases con consumidores
  activos confirmados en `api/viewsets.py` (`EmpleadoCRUDService`,
  `ContratoCRUDService`, `DevengoCRUDService`,
  `EmpleadoBusinessService`, `ContratoBusinessService`,
  `DevengoBusinessService`, `NominaCalculationService`, 3
  `*ServiceMixin`) -- sin funciones huerfanas.
- Sin scripts standalone en `scripts/` relacionados con esta app (a
  diferencia de `empresa`, que tenia `test_empresa_refactor.py`
  huerfano).

**Conclusion FASE K: 0 lineas de codigo muerto confirmado.** Segunda
app consecutiva (junto con `perfil`) sin hallazgos de limpieza.

**Nota de contexto (no bloquea):** `git status` muestra WIP
preexistente sin commitear en `apps/tenant/empleados/tables.py` y 5
archivos de test (`test_api_smoke.py`, `test_crud_smoke_v38.py`,
`test_devengos_api_smoke.py`, `test_multitenant_isolation_tablas_
html.py`, `test_routing_smoke.py`) -- documentado en FASE 0 como WIP
ajeno a esta mision, no se toca ni se commitea junto con esta
auditoria (regla explicita de `APP_AUDIT_MASTER_STATUS.md`). La
regresion de esta app se ejecuta sobre el working tree tal como esta
(incluyendo ese WIP), consistente con como se ejecutaria en cualquier
entorno de desarrollo real.

## FASE I — Seguridad (verificacion puntual, sin cambios)

Confirmado contra el `.agent/` doc y lectura puntual del codigo:

- `BaseTenantViewSet` + `SintelDSVMixin` + `*ServiceMixin` en los 5
  ViewSets (Empleado/Contrato/Devengo/ResolucionDIAN/
  LiquidacionPrestacion) -- permisos `IsTenantMember +
  IsTenantAdminOrReadOnly` importados de `apps.tenant.api.permissions`
  (SSoT, no hay `permissions.py` propio en esta app -- correcto, no
  hay que auditar un shim que no existe).
- `select_for_update()` confirmado en el flujo de asignacion de
  consecutivo DIAN (`procesar_devengo()`), previene condicion de
  carrera en emision de nomina electronica concurrente.
- `Devengo.update()`/`partial_update()` bloqueados (405) -- inmutable
  tras creacion, solo `anular_devengo()` (soft) o `eliminar_devengo()`
  (hard, con guard) -- coherente con el principio de nomina como
  registro contable/legal que no debe editarse silenciosamente.

## FASE M — Normativa colombiana

`empleados` esta en la lista explicita de apps que requieren matriz
normativa (mision). Ver **`documentacion/audits/apps/
APP_empleados_NORMATIVE_MATRIX.md`** -- 15 obligaciones identificadas,
todas con evidencia en codigo (cita de Ley/Decreto/articulo donde el
codigo la trae inline; marcadas `REQUIERE_VALIDACION` donde no hay
cita verificable). Hallazgos principales:

- Las deducciones de ley (salud/pension 4%+4%, exclusion de auxilio
  del IBC, exclusion de auxilio para PRESTACION) **SI** citan articulo
  exacto en el codigo (Ley 100/1993 arts. 20/30/204, Ley 1393/2010
  art. 2) -- alta trazabilidad.
- Las formulas de prestaciones sociales (prima/cesantias/intereses/
  vacaciones) son tecnicamente correctas pero **no citan norma
  inline** -- brecha de documentacion, no de calculo (deferred P3).
- La jornada de referencia (Ley 2101/2021, 42h/200h) esta hardcodeada
  sin parametrizar por fecha historica del periodo -- riesgo teorico
  si el sistema procesara retroactivamente periodos de jornada
  anterior (deferred P2, requiere confirmar con Mintrabajo el
  calendario exacto de escalonamiento).
- DSPNE (nomina electronica DIAN): infraestructura de datos completa
  y correcta (CUNE, consecutivo, resolucion), pero la transmision XML
  real a DIAN **no esta implementada** (`DEUDA-11`, ya documentada y
  ABIERTA en el `.agent/` doc desde 2026-06-17, confirmada vigente en
  este pase). Prioridad P1/P2 segun si hay tenants reales ya
  obligados a DSPNE en produccion (no verificable desde esta
  auditoria de codigo).

## FASE Q — Tests / Regresion

64 tests coleccionados (`apps/tenant/empleados/tests/`, 11 archivos).
Regresion ejecutada sobre el working tree (incluyendo el WIP
preexistente no commiteado en `tables.py` y 5 archivos de test,
documentado como ajeno a esta mision): **64 passed, 0 failed, 7
warnings preexistentes (min_value DRF ya visto en apps anteriores +
`format_html()` sin args, `RemovedInDjango60Warning`, no relacionados
con esta auditoria) en 5089.06s (1:24:49)**. Incluye 3 suites de
`scope_*` (F7/F8/F13/F14 -- alcance organizacional EMPRESA/SEDE/AREA)
todas verdes, confirma que la logica de `alcance` documentada en
`perfil` (ADR-003) esta correctamente aplicada aqui tambien.

## Deferred

Ver tabla completa en `APP_empleados_NORMATIVE_MATRIX.md` (items 1-4).
Resumen:

| # | Item | Prioridad |
|---|---|---|
| 1 | Jornada Ley 2101/2021 no parametrizada por fecha historica del periodo | P2 |
| 2 | Limite de horas extras diarias (CST art. 168, 2h/dia) -- guard no confirmado explicitamente en este pase | P2 |
| 3 | Formulas de prestaciones sociales sin cita normativa inline (correctas, solo brecha de trazabilidad) | P3 |
| 4 | DSPNE sin transmision XML real a DIAN (DEUDA-11, ya conocida) | P1/P2 segun tenants reales obligados |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, sin codigo muerto encontrado (FASE C/D/K)
- [x] Seguridad verificada puntualmente, sin hallazgos nuevos (FASE I)
- [x] Matriz normativa colombiana completa (FASE M, documento separado)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 64 passed, 0 failed
- [x] Deferred items documentados con razon/riesgo/prioridad (4 items,
      todos heredados de hallazgos normativos, ninguno de codigo)

## FASE Y — Decision

**COMPLETED_WITH_DEFERRED** -- 64/64 tests pasan, 0 regresiones, 0
hallazgos de codigo muerto. Se usa `_WITH_DEFERRED` por los 4 items
normativos documentados en `APP_empleados_NORMATIVE_MATRIX.md`
(principalmente DEUDA-11: DSPNE sin transmision XML real a DIAN, ya
conocida desde 2026-06-17, confirmada vigente).
