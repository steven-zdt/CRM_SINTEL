# F34_gastos_AUDIT — Auditoria integral de negocio/arquitectura (app 11/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_gastos_AUDIT.md` (398 bytes eliminados -- `services.py`
inalcanzable por shadowing con el paquete `services/` del mismo
nombre, verificado empiricamente).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`gastos` gestiona `DocumentoSoporte`/`ResolucionDIAN`, con retenciones
via Pull Model desde `contabilidad.RetencionesService` (arquitectura
ya verificada end-to-end en la mision anterior, incluyendo el cierre
del hallazgo P1 de `proveedores`). Sin cambios de codigo en esta
pasada.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| Retenciones de un `DocumentoSoporte` se calculan via `contabilidad.RetencionesService.obtener_retenciones_desde_tercero()`, NUNCA localmente | **CRITICAL** (arquitectonica) | Ya verificado end-to-end |
| `Devengo`/movimientos de gasto son inmutables tras crearse salvo `anular_gasto()`/`eliminar_gasto()` controlados | **CRITICAL** | `business_service.py` |
| `materializar_gasto_desde_dto()` es el punto de entrada real desde el gateway universal de documentos (`core/document_router.py`) | **CRITICAL** | Confirmado consumidor real |
| Numeracion de `DocumentoSoporte` via `ResolucionDIAN` con rango autorizado | **IMPORTANT** | Mismo patron `select_for_update()` que otras apps con resolucion DIAN |

## FASE 2 — Mapa de dominio

Sin cambios respecto a la auditoria previa (`ResolucionDIAN`,
`DocumentoSoporte`).

## FASE 6 — ORM/BD: verificacion N+1

`selectors.py`: `select_related` presente en los queries principales.
**Sin hallazgos de N+1.**

## FASE 12/13 — Codigo muerto / duplicacion

Verificado que `materializar_gasto_desde_dto()` (unica funcion
module-level suelta del archivo) tiene un consumidor real confirmado
(`apps/tenant/core/document_router.py`, el gateway universal de
documentos) ademas de tests dedicados -- no es dead code. `parse_nit()`
(helper de clase) se usa internamente dentro de la misma funcion.
**Sin hallazgos nuevos** mas alla de lo ya corregido (shadowing
`services.py`).

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio (sin cambios)
- [x] N+1 verificado -- sin hallazgos
- [x] Codigo muerto -- verificado, sin hallazgos nuevos
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED.**
