# F25 — Reporte de Seguridad (DSV, Multi-Tenant, Empresa/Sede/Area, Service Layer)

**Fecha:** 2026-08-10

F25 modifico 2 archivos de produccion (`apps/tenant/gastos/services/business_service.py`
en esta fase; `apps/tenant/compras/services/business_service.py` ya en F24). Ambas
correcciones son estrictamente aditivas (`transaction.set_rollback(True)` dentro de
`except` ya existentes) -- no tocan ninguna linea de resolucion de `empresa_id`,
DSV, scope, membresia o rol. Verificado por `git diff`: 0 lineas de logica de
negocio/seguridad modificadas, solo lineas de manejo de transaccion agregadas.

## 1. DSV

Sin cambios. Las correcciones de F25 no alteran ningun punto de resolucion de
entidades (`_obtener_entidad_por_id_o_uuid`, `.filter(empresa_id=...)`, etc.) --
confirmado por inspeccion de diff.

## 2. Multi-tenant

Sin cambios de comportamiento. El fix de `procesar_gasto()` opera dentro del mismo
`empresa` ya resuelto por el llamador (parametro explicito, sin re-derivarlo) -- el
`transaction.set_rollback(True)` no introduce ninguna ruta nueva de acceso a datos.

## 3. Empresa / Sede / Area

Sin cambios. `DocumentoSoporte`/`Retencion` siguen usando los mismos campos
`empresa`/`empresa_id` ya establecidos; el rollback agregado no altera que ocurre,
solo evita que una escritura parcial sobreviva a un error.

## 4. Service Layer

`ViewSet -> ServiceMixin -> BusinessService -> CRUDService` intacto. 0 signals
(`post_save`/`pre_save`/`post_delete`/`pre_delete`/`m2m_changed`/`@receiver`)
encontrados en `compras/ventas/facturas/inventario/contabilidad/gastos` (grep
extendido, ver `F25_FINDINGS.md`). Ninguna logica de negocio nueva se agrego a
Serializer/Model/ViewSet.

## 5. Governance

Ver `F25_EXECUTION_STATUS.md` -- `FINAL STATUS: PASS` antes y despues de los
cambios de F25 (solo 1 archivo de produccion modificado en esta fase, cambio
estrictamente aditivo de manejo de excepciones).

## Veredicto

0 hallazgos de seguridad. La unica correccion de codigo de F25 (gastos) es
transaccional, no de autorizacion/aislamiento -- no hay superficie de ataque nueva
que auditar mas alla de lo ya cubierto en F24_SECURITY_AUDIT.md (que sigue vigente
sin cambios).
