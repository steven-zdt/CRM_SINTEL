# F34_facturas_AUDIT — Auditoria integral de negocio/arquitectura (app 14/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_facturas_AUDIT.md` + `APP_facturas_NORMATIVE_MATRIX.md`
(**hallazgo P1 principal de toda la mision anterior**: CUFE/XAdES
verificados tecnicamente correctos, pero la transmision real del
documento firmado al webservice DIAN nunca esta implementada en
ningun punto del sistema).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.
App mas grande del sistema (8 modelos, 33 migraciones, ~30+ archivos
de servicio) -- esta pasada prioriza profundidad en un hallazgo
concreto sobre cobertura exhaustiva de cada archivo, consistente con
la limitacion ya documentada en la auditoria previa.

---

## FASE 12/13 — Codigo muerto: investigacion de la capa de compatibilidad

`services/__init__.py` tiene una seccion explicitamente marcada
`[COMPAT] Wrappers funcionales de compatibilidad para tests y
management commands que usan la API funcional de nivel de modulo
(pre-refactorizacion v3.10)` -- con la advertencia expresa `No usar
desde ViewSets`. Mismo patron arquetipo que las capas legacy ya
encontradas en `clientes`/`proveedores`/`gastos`/`dashboard`.

**Investigado con evidencia:** `crear_factura()`, `importar_ubl()`,
`importar_ubl_sync()`, `materializar_factura_desde_result()`
(los 4 wrappers publicos, ademas de 3 helpers privados internos) --
**NO estan completamente muertos**: ademas de multiples tests,
tienen **2 consumidores de produccion reales confirmados**:
`apps/tenant/facturas/api/mixins/factura_ubl_mixin.py` y
`apps/services/maildigester/__init__.py` (el digestor de correo que
procesa facturas recibidas por IMAP). **Conclusion: no se elimina
nada** -- a diferencia de los casos anteriores, esta capa de
compatibilidad SI tiene consumidores de produccion vigentes, no solo
tests.

**Nota de precision:** `factura_ubl_mixin.py` es el mismo archivo
donde vive el endpoint `factura-upload-ubl`, ya documentado como
`DEPRECATED` en su propio docstring desde el contexto heredado de
F33.15-B. Esto significa que parte de esta capa de compatibilidad
sigue viva PORQUE alimenta un endpoint deprecado que aun no se ha
retirado -- es deuda tecnica conocida y ya registrada, no un hallazgo
nuevo que amerite accion en esta pasada.

## FASE 6 — ORM/BD: verificacion N+1

`FacturaSelectors` (unica clase selectora, `selectors.py`, 578
lineas): `select_related("nota_credito", "sede")` en list Y detail,
mas `prefetch_related("impuestos_desglosados")` en detail. El bajo
numero de traversals (`select_related`/`prefetch_related` aparecen
solo 4 veces en 578 lineas) es coherente con la arquitectura
documentada -- la mayoria de las relaciones cross-app de `Factura`
son soft-references UUID (Bounded Context §18), no FKs reales de
Django, por lo que no hay mucho que optimizar con `select_related`.
**Sin hallazgos de N+1.**

## Normativa (FASE 14) — sin cambios, hallazgo P1 sigue abierto

El hallazgo principal de toda la mision anterior sigue vigente y sin
resolver (requiere decision de producto e implementacion real de
cliente SOAP/HTTP contra DIAN, fuera del alcance de una auditoria de
codigo): **la transmision real de facturas de venta al webservice de
la DIAN nunca esta implementada**. No se re-verifica con mas
profundidad en esta pasada (ya se verifico exhaustivamente en la
mision anterior con grep completo de `requests.post`/`zeep`/`SOAP`/
`wsdl`).

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Codigo muerto: capa de compatibilidad investigada con evidencia, confirmada NO completamente muerta (2 consumidores de produccion reales)
- [x] N+1 verificado -- sin hallazgos, arquitectura de soft-references explica el bajo conteo de select_related
- [x] Normativa -- hallazgo P1 (transmision DIAN) sigue documentado, sin cambios
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED_WITH_DEFERRED** (hereda el hallazgo P1 de la
auditoria previa, confirmado aun abierto).
