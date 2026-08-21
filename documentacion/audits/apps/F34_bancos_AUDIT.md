# F34_bancos_AUDIT — Auditoria integral de negocio/arquitectura (app 13/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_bancos_AUDIT.md` (0 codigo muerto, confirmado modulo de
conciliacion puro sin logica tributaria).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`bancos` gestiona conciliacion bancaria (cuentas, extractos ETL,
transacciones con vinculacion soft-reference a Factura/Proveedor/
Cliente). Sin cambios de codigo en esta pasada.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| `crear_transacciones_bulk()` usa `bulk_create` para el ETL de extractos -- nunca crea transacciones una por una | **CRITICAL** (performance/negocio) | `crud_service.py:112` |
| `conciliar_transaccion()` es el unico punto de escritura de vinculos `factura_uuid`/`proveedor_uuid`/`cliente_uuid`/`conciliado` | **CRITICAL** | `crud_service.py:129` |
| `tipo_movimiento`/`monto` son `@property` calculadas, nunca campos de BD -- no usar en `filterset_fields` (leccion de FIX-01) | **CRITICAL** (leccion de bug real ya corregido) | Ya documentado, re-confirmado sin regresion |

## FASE 2 — Mapa de dominio

Sin cambios (`CuentaBancaria -> ExtractoBancario -> TransaccionBancaria`).

## FASE 6 — ORM/BD: verificacion N+1

`selectors.py`: `select_related` presente en los 4 querysets
principales (cuenta, extracto). `crear_transacciones_bulk()` confirma
`bulk_create` para el ETL (no loop de `.save()` individual). **Sin
hallazgos de N+1.**

## FASE 12/13 — Codigo muerto

`parse_decimal()` (module-level, helper de conversion) usado
internamente por `procesar_archivo_extracto()`. Estructura de
servicios limpia, sin duplicacion. **Sin hallazgos nuevos.**

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio (sin cambios)
- [x] N+1 verificado -- sin hallazgos, `bulk_create` confirmado en el ETL
- [x] Codigo muerto -- barrido fresco, sin hallazgos nuevos
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED.**
