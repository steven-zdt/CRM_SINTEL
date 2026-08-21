# APP_contabilidad_AUDIT — Auditoria integral (app 15/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> facturas
-> **contabilidad** -> dashboard -> ...

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/contabilidad` tiene `.agent/AUDITORIA_COMPLETA_
CONTABILIDAD.md` (2318 lineas -- el doc mas extenso de todos, no
leido integramente por alcance de tiempo, usado como referencia
puntual). App central del sistema: **13 modelos** (`CatalogoMaestroNIIF`,
`CuentaContable`, `TipoComprobante`, `AsientoContable`,
`MovimientoContable`, `PeriodoContable`, `ReglaContable`,
`TarifaImpuesto`, `ConfiguracionRetenciones`, `Retencion`,
`PlantillaContable`, `LineaPlantilla`, `ImpuestoDocumento`), coincide
con `APP_AUDIT_MATRIX.md`. Unica propietaria del PUC y de los
asientos contables -- 15 apps consumen `contabilidad` via Pull Model
(nunca al reves, `contabilidad` nunca importa de las apps origen mas
alla de resolver referencias de `documento_origen_app`).

## FASE C/D/K — Codigo muerto (CONFIRMADO Y CORREGIDO)

**Encontrados 2 hallazgos reales de codigo muerto:**

1. **`apps/tenant/contabilidad/scratch/`** -- directorio completo
   (`audit_gastos.py`, `validate_extractor_gastos.py`, 44 lineas
   totales) que **no es ni siquiera un paquete Python valido** (sin
   `__init__.py`). Ambos archivos son scripts de depuracion ad-hoc con
   codigo a nivel de modulo que ejecuta queries reales contra la BD al
   importarse (`for t in TenantModel.objects...`, `with schema_context
   ('home'): ...`) -- el segundo ademas **hardcodea el nombre de un
   tenant** (`'home'`), violando la regla "Zero-Hardcoding de tenant
   names" documentada como estandar en varios `.agent/` docs de otras
   apps. Confirmado con grep: cero imports de `contabilidad.scratch`
   en ningun otro archivo. Este es el mismo tipo de hallazgo que el
   `.agent/` doc de `core` en Nivel 3 clasificaria como scratch/
   debugging accidentalmente commiteado -- nunca debio estar dentro de
   un paquete de app en produccion. **DEAD_CONFIRMED, eliminado.**
2. **`apps/tenant/contabilidad/api/datatables.py`** (107 lineas) --
   auto-declarado `"DEPRECATED v2.40"` en su propia primera linea, Y
   confirmado estructuralmente desconectado: su import en
   `api/urls.py:36` esta **comentado** (`# from
   apps.tenant.contabilidad.api.datatables import (`), prueba de que
   fue deliberadamente deshabilitado, no un olvido. Sin otros
   consumidores (grep repo-wide, incluyendo tests). **DEAD_CONFIRMED,
   eliminado.**

**No se elimino** `views_ui.py` (tambien auto-declarado "DEPRECADO --
UI movida a Core") ni la ruta 404 stub en `api/urls.py:71-80` -- a
diferencia de `datatables.py`, estos son **stubs 404 intencionales y
activos** (la ruta SI esta registrada, retorna 404 deliberadamente
por compatibilidad hacia atras con clientes que aun apunten a la URL
vieja) -- comportamiento documentado y funcional, no codigo muerto.

**Total eliminado: 151 lineas** (44 de `scratch/` + 107 de
`api/datatables.py`).

## FASE M — Normativa colombiana (cierra el ciclo de retenciones)

`contabilidad` esta en la lista explicita de apps que requieren
matriz normativa. Ver **`documentacion/audits/apps/
APP_contabilidad_NORMATIVE_MATRIX.md`** -- verifica
`RetencionesService`/`ConfiguracionRetenciones` con el mismo nivel de
detalle aplicado a CUFE en `facturas`. **Confirma y cierra
positivamente** el ciclo de hallazgos sobre retenciones iniciado en
`clientes`/`proveedores`/`gastos`: la arquitectura real
(`ConfiguracionRetenciones`, tabla de configuracion por tenant/
tercero/naturaleza, con FK a cuenta contable, tarifas NO hardcodeadas)
es **correcta y bien diseñada** -- contrasta positivamente con las
funciones dead-code de `proveedores` que si hardcodeaban tarifas.

Items deferred (PUC/NIIF/periodos/reglas contables seedeados, no
verificados contra version normativa vigente -- requiere validacion
contable especializada, fuera del alcance de una auditoria de codigo)
documentados en la matriz.

## FASE Q — Tests / Regresion

Tests coleccionados: `apps/tenant/contabilidad/tests/` (14 archivos
segun `APP_AUDIT_MATRIX.md`, la app con mas tests junto a `facturas`).
Regresion lanzada en background tras confirmar `db`/`redis` healthy.

## Deferred

Ver tabla completa en `APP_contabilidad_NORMATIVE_MATRIX.md`. Resumen:

| # | Item | Prioridad |
|---|---|---|
| 1 | Seeds (PUC, NIIF, periodos, reglas, tipos de comprobante) no verificados contra version normativa vigente | P2 (requiere validacion contable especializada) |
| 2 | Extractores del Pull Model no revisados linea por linea (validados indirectamente por 4+ apps consumidoras sin contratos rotos) | P3 |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados (FASE B, 13 confirmados)
- [x] Codigo muerto encontrado y eliminado -- 151 lineas (FASE C/D/K)
- [x] Matriz normativa colombiana completa -- cierra ciclo de retenciones (FASE M)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [ ] Regresion de la app -- **PENDIENTE**, en curso en background
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**PENDIENTE DE CIERRE** -- bloqueado por el resultado de la regresion
en curso. Se espera `COMPLETED_WITH_DEFERRED` (2 items P2/P3, ninguno
bloqueante) si la regresion confirma 0 fallos nuevos.
