# F34_cotizaciones_AUDIT — Auditoria integral de negocio/arquitectura (app 9/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_cotizaciones_AUDIT.md` (~180 lineas de codigo muerto ya
eliminadas: pipeline PDF duplicado y huerfano en `services/pdf/`).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`cotizaciones` gestiona cotizaciones con DNA dinamico (perfil de
configuracion), snapshot pattern en items, motor AIU+IVA centralizado.
Sin cambios de codigo en esta pasada -- barrido fresco de
`business_service.py`, `item_service.py`, `producto_service.py`,
`servicio_service.py` (patron Selector-CRUD-Mixin repetido por
entidad) no encontro codigo muerto adicional al ya eliminado.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| `generar_codigo_unico()` usa `select_for_update()` + incremento atomico -- numeracion nunca se duplica bajo concurrencia | **CRITICAL** | `business_service.py:201` |
| `_sync_items()` sincroniza items maestro-detalle por UUID->ID->nuevo, elimina remanentes no enviados | **CRITICAL** | `business_service.py:125` |
| `crear_preforma()`/`actualizar_cotizacion()` generan el PDF SINCRONICAMENTE tras persistir (`_generar_pdf_sincronizado()`) -- no es un job asincrono | **IMPORTANT** | `business_service.py:17,196,273` |
| `calcular_totales()` es el unico punto de calculo de AIU+IVA+subtotal | **CRITICAL** | Motor SSoT, ya documentado |
| `get_configuracion_for_empresa()`/`get_cliente_for_empresa()` son guards DSV explicitos antes de crear cualquier cotizacion | **CRITICAL** (anti-IDOR) | `business_service.py:55,85` |

## FASE 2 — Mapa de dominio

Sin cambios respecto a la auditoria previa (`Cotizacion`,
`CotizacionItem`, `Producto`, `Servicio`, `ConfiguracionCotizacion` --
5 modelos reales, el ultimo vive en el submodulo `configuracion/`).

## FASE 6 — ORM/BD: verificacion N+1

`selectors.py`: `select_related` en list/detail, `prefetch_related
('items')` en detail -- confirmado consistente. **Sin hallazgos de
N+1.**

## FASE 12/13 — Codigo muerto / duplicacion

Barrido fresco de los 4 archivos de servicio principales (business_
service, item_service, producto_service, servicio_service): patron
repetido Selector-CRUD-Mixin por entidad, todos con consumidores
reales confirmados via `services/__init__.py`. La unica funcion
module-level suelta (`_generar_pdf_sincronizado`, con prefijo `_`)
tiene 2 consumidores internos confirmados -- no es dead code, es un
helper privado legitimo. **Sin hallazgos nuevos** (el pipeline PDF
duplicado ya se elimino en la pasada anterior).

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio (sin cambios)
- [x] N+1 verificado -- sin hallazgos
- [x] Codigo muerto -- barrido fresco, sin hallazgos nuevos mas alla de lo ya corregido
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED.**
