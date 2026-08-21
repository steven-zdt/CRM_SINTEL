# F34_proyectos_AUDIT — Auditoria integral de negocio/arquitectura (app 10/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_proyectos_AUDIT.md` (25 lineas de codigo muerto ya eliminadas:
`ProyectoServiceMixin` sombra, copy-paste de `gastos`).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.
**Nota:** sin ejecucion de tests -- validacion por evidencia estatica.

---

## Resumen ejecutivo

`proyectos` gestiona proyectos con maquina de estados de edicion
granular (fase CIERRE bloquea campos criticos), presupuesto manual,
indicadores P&L. Sin cambios de codigo en esta pasada. Estilo
arquitectonico distinto al resto del sistema: `business_service.py`
usa **funciones module-level** (no clases) para la mayoria de la
logica de negocio -- verificado que esto es una decision deliberada,
no un resto de refactor: cada funcion tiene consumidores internos
reales (composicion funcional).

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| `calcular_indicadores_financieros()` = utilidad (contrato - MO - materiales), margen = utilidad/contrato×100, division por cero no genera excepcion | **CRITICAL** | Verificado con test dedicado en la auditoria previa |
| `calcular_costo_mano_obra()` solo suma asignaciones `activo=True` | **IMPORTANT** | Verificado, `calcular_indicadores_financieros` lo compone |
| `calcular_costo_materiales()` solo suma pedidos `estado='APROBADO'`, excluye `BORRADOR` | **IMPORTANT** | Idem |
| Fase `CIERRE` bloquea: campos criticos/financieros del proyecto, creacion/edicion de `AsignacionPersonal`, `PedidoProyecto` | **CRITICAL** | `api/serializers.py` `.validate()`, ya verificado |
| `asignar_snapshot_factura`/`asignar_snapshot_proveedor`/`validar_servicio_asociado_dsv` se ejecutan dentro de `orchestrate_create_proyecto`/`orchestrate_update_proyecto` -- son composicion interna, no funciones independientes con consumidores externos propios | **SUPPORTING** (aclaracion arquitectonica) | Ver FASE 12 |
| `ItemPresupuestoViewSet` usa `lookup_field='id'` (no `uuid`) -- desviacion deliberada revertida tras un bug real documentado | **IMPORTANT** (decision ya tomada, no reabrir) | `.agent/` doc, Critical Fixes #3-5 |

## FASE 2 — Mapa de dominio

Sin cambios respecto a la auditoria previa (7 modelos:
`Proyecto`, `AsignacionPersonal`, `PedidoProyecto`, `ItemPedido`,
`ItemPresupuestoProyecto`, `TareaDiariaProyecto`, `TareaCorta`).

## FASE 6 — ORM/BD: verificacion N+1

`selectors.py`: `select_related`/`prefetch_related` presentes
consistentemente, incluyendo `prefetch_related('items_presupuesto')`
(comentado explicitamente como "Zero Waste" en el propio codigo) y
traversals de doble nivel (`'empleado__empresa'`). **Sin hallazgos de
N+1.**

## FASE 12/13 — Codigo muerto / duplicacion (verificacion profunda)

Investigacion especifica de las funciones module-level que a primera
vista parecian sin consumidores externos (`asignar_snapshot_factura`,
`asignar_snapshot_proveedor`, `validar_servicio_asociado_dsv`,
`calcular_costo_mano_obra`, `calcular_costo_materiales`) -- **todas
confirmadas con consumidores internos reales**: se invocan dentro de
`orchestrate_create_proyecto()`/`orchestrate_update_proyecto()`
(los verdaderos puntos de entrada, consumidos por `api/mixins.py`) o
dentro de `calcular_indicadores_financieros()`. No son dead code, son
descomposicion funcional del mismo flujo -- un patron arquitectonico
distinto al resto de las apps (que usan clases) pero igual de valido,
sin duplicacion real. **Sin hallazgos nuevos** mas alla de lo ya
corregido en la pasada anterior.

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio (sin cambios)
- [x] N+1 verificado -- sin hallazgos
- [x] Codigo muerto -- verificacion profunda de funciones aparentemente huerfanas, todas confirmadas con consumidores internos reales
- [x] Sin cambios de codigo -> sin necesidad de validacion adicional

**APP = COMPLETED.**
