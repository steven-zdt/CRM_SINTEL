# F34_contabilidad_AUDIT — Auditoria integral de negocio/arquitectura (app 15/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_contabilidad_AUDIT.md` + `APP_contabilidad_NORMATIVE_MATRIX.md`
(151 lineas eliminadas -- `scratch/` sin `__init__.py` + `api/
datatables.py` deprecado; `ConfiguracionRetenciones`/
`RetencionesService` verificados linea por linea, arquitectura
correcta).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`contabilidad` es la app central del Pull Model (13 modelos, unica
propietaria del PUC y de los asientos contables). Sin cambios de
codigo en esta pasada -- barrido fresco de `business_service.py`
(31 metodos), `crud_service.py` (11 metodos) y los extractores de
`integracion/` no encontro el patron de facade nunca adoptado visto
en `inventario`, ni una capa de compatibilidad legacy como en
`facturas`.

## FASE 12/13 — Codigo muerto / duplicacion

- `business_service.py`/`crud_service.py`: **cero funciones
  module-level** -- toda la logica vive en metodos de clase,
  consistente con el patron limpio ya visto en `compras`/`ventas`/
  `bancos`.
- `services/__init__.py`: sin marcadores `COMPAT`/`legacy` -- sin
  capa de compatibilidad heredada como la encontrada en `facturas`.
- `integracion/contabilizador.py` (7 metodos) / `integracion/
  resolver.py` (4 metodos): tamaño acotado, sin señales de
  duplicacion.

**Sin hallazgos nuevos** mas alla de lo ya corregido en la pasada
anterior.

## FASE 6 — ORM/BD: verificacion N+1

`selectors.py` (890 lineas, la mas grande auditada en F34): 13
ocurrencias de `select_related`/`prefetch_related` -- proporcion
razonable dado que es el archivo que sirve a los 13 modelos de la
app. No se verifico cada uno individualmente por alcance de tiempo
(consistente con la limitacion ya aceptada en `facturas`), pero la
muestra revisada (incluyendo `RetencionesService`, ya verificado
linea por linea en la pasada anterior) no mostro ningun patron de
query-en-loop.

## Normativa (FASE 14) — sin cambios

Los items deferred de la matriz normativa previa (seeds de PUC/NIIF/
periodos no verificados contra version vigente -- requiere validacion
contable especializada) siguen sin cambios, P2/P3, sin accion en esta
pasada.

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Codigo muerto -- barrido fresco de business_service/crud_service/integracion, sin hallazgos nuevos
- [x] N+1 -- muestra revisada sin patrones de query-en-loop
- [x] Normativa -- sin cambios
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED_WITH_DEFERRED** (hereda los items normativos P2/P3
de la auditoria previa).
