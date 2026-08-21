# F34_empleados_AUDIT — Auditoria integral de negocio/arquitectura (app 12/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_empleados_AUDIT.md` + `APP_empleados_NORMATIVE_MATRIX.md` (0
codigo muerto, matriz normativa laboral completa -- deducciones 4%+4%
con cita de articulo Ley 100/1993, DSPNE con DEUDA-11 abierta).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`empleados` es el motor de nomina colombiano (salario proporcional +
auxilio + H.E./recargos − deducciones de ley) + DSPNE (nomina
electronica DIAN) + liquidacion de prestaciones sociales. Sin cambios
de codigo en esta pasada -- la matriz normativa de la mision anterior
ya es exhaustiva; F34 se enfoca en verificar N+1 (no cubierto antes
con este detalle) y un barrido fresco de codigo muerto.

## FASE 1 — Reglas de negocio (referencia)

Ya clasificadas exhaustivamente en `APP_empleados_NORMATIVE_MATRIX.md`
(15 obligaciones con evidencia de codigo). No se repite aqui --
resumen de las CRITICAL: deducciones 4%+4% sobre IBC (Ley 100/1993
arts. 20/204), exclusion de auxilio de transporte del IBC (art. 30),
contratos PRESTACION sin auxilio/deducciones (Ley 1393/2010 art. 2),
`Devengo` inmutable tras creacion salvo anulacion.

## FASE 6 — ORM/BD: verificacion N+1 (nuevo en esta pasada)

`selectors.py` verificado exhaustivamente: **`select_related`
presente en TODOS los querysets de lectura** de `Empleado`
(sede/area, empresa+sede+area en detalle), `Contrato`
(empresa+empleado), y `Devengo` (empresa+empleado+contrato en
detalle, empleado+contrato en listado) -- consistente con traversals
explicitos (`_SEDE_AREA_TRAVERSALS`, `_CONTRATO_DETAIL_TRAVERSALS`,
etc.) y `.only()` en cada caso. **Sin hallazgos de N+1** -- esta app
tiene el patron Zero-Waste mas consistente verificado hasta ahora en
F34.

## FASE 12/13 — Codigo muerto (barrido fresco)

`business_service.py`: 15 metodos de clase + 1 unica funcion
module-level (`_to_decimal`, helper privado de conversion segura,
prefijo `_`). Sin patron de facade duplicado (a diferencia de
`inventario`). **Sin hallazgos nuevos.**

## Normativa (FASE 14) — sin cambios

Los 4 items deferred de la matriz normativa previa siguen vigentes,
sin re-verificacion en esta pasada (no hay evidencia nueva que
cambie su clasificacion):
1. Jornada Ley 2101/2021 no parametrizada por fecha historica -- P2
2. Limite 2h/dia de horas extra no confirmado explicitamente -- P2
3. Formulas de prestaciones sin cita normativa inline (correctas, solo documentacion) -- P3
4. **DEUDA-11: DSPNE sin transmision XML real a DIAN** -- P1/P2 segun tenants reales obligados, mismo patron confirmado ahora tambien en `facturas` (transmision DIAN de ventas, hallazgo mas critico de toda la mision anterior)

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio (referencia a matriz normativa previa, exhaustiva)
- [x] N+1 verificado a fondo -- sin hallazgos, patron Zero-Waste mas consistente visto en F34
- [x] Codigo muerto -- barrido fresco, sin hallazgos nuevos
- [x] Normativa -- sin cambios, items deferred previos siguen vigentes
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED_WITH_DEFERRED** (hereda los items normativos P1/P2
de la auditoria previa, ninguno nuevo).
