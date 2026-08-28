# REM-P2-01 — Segregación de funciones en Compras/Gastos/Bancos

**Estado:** BLOCKED (BUSINESS_DECISION_REQUIRED — no bloquea el resto del plan)
**Prioridad:** P2
**Apps involucradas:** `compras`, `gastos`, `bancos`
**Fecha:** 2026-08-28

## Hallazgo (heredado de `INTERNAL_CONTROL_MATRIX.md`, auditoría empresarial)

De 5 flujos transaccionales auditados, solo Nómina tiene segregación de rol
real (`PeriodoNominaViewSet._ROLES_POR_ACCION`, `apps/tenant/empleados/
api/viewsets.py:2110-2135`): `preliquidar`/`create` permiten
`['ADMIN','OPERADOR']`; `aprobar`/`marcar_pagado`/`cerrar`/`anular`
exigen `['ADMIN']` exclusivamente. Compras, Gastos y Bancos no tienen
ningún punto de control que impida que el mismo usuario ejecute el ciclo
completo (crear→aprobar→recibir/pagar/conciliar).

## Investigación (regla explícita: no inventar una matriz de roles nueva)

Roles reales del sistema (`apps/tenant/perfil/models.py:RolTenant`):
únicamente **ADMIN, OPERADOR, VISOR**. No existen roles `APROBADOR`,
`PAGADOR`, `CONTADOR`, `TESORERÍA` como conceptos de sistema — la auditoría
empresarial de esta misma sesión ya confirmó esto con grep exhaustivo
(`EXECUTIVE_AUDIT_REPORT.md`).

El patrón real usado por Nómina (`HasTenantRole` + `_ROLES_POR_ACCION` por
acción del ViewSet) es reutilizable tal cual para Compras/Gastos/Bancos si
el negocio decide que lo necesita — no requiere ningún RBAC nuevo, solo
aplicar el patrón existente a las acciones correspondientes de esos 3
ViewSets (`aprobar`/`cambiar-estado` en `OrdenCompraViewSet`, `anular` en
`GastoViewSet`, `conciliar` en `TransaccionBancariaViewSet`).

## Decisión

**No se implementa ningún cambio de código.** Con solo 3 roles reales
(ADMIN/OPERADOR/VISOR) y sin evidencia de que el negocio objetivo (MIPYME)
requiera que "quien crea" ≠ "quien aprueba" ≠ "quien paga" en Compras/
Gastos/Bancos específicamente, imponer esa restricción ahora sería inventar
una política de control interno no solicitada — podría bloquear
operaciones legítimas de un tenant pequeño donde el mismo ADMIN
razonablemente hace todo el ciclo.

**Se registra `BUSINESS_DECISION_REQUIRED`**: si el negocio confirma que sí
necesita segregación forzada en estos 3 flujos, la implementación es
directa (reutilizar `HasTenantRole`/`_ROLES_POR_ACCION`, sin RBAC nuevo) —
queda documentado aquí como ítem listo para ejecutar en cuanto exista esa
decisión, sin bloquear el resto de `REMEDIATION_MASTER_PLAN.md`.

## Archivos que se tocarían si se aprueba (no modificados en esta sesión)

- `apps/tenant/compras/api/viewsets.py` (`OrdenCompraViewSet`)
- `apps/tenant/gastos/api/viewsets.py` (`GastoViewSet`)
- `apps/tenant/bancos/api/viewsets.py` (`TransaccionBancariaViewSet`)

## Governance

N/A — sin cambio de código.
