# APP_dashboard_AUDIT — Auditoria integral (app 16/16, la ULTIMA app individual)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: ... -> contabilidad
-> **dashboard** (fin del barrido app-por-app -> FASE FINAL).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/dashboard` tiene `.agent/AUDITORIA_FLUJO_DASHBOARD.md` --
usado como referencia. **1 modelo concreto** (`SnapshotMetricaDiaria`),
coincide con `APP_AUDIT_MATRIX.md`. App pequeña en modelos pero con
logica de agregacion compleja: **8 extractores Pull Model** (uno por
app de dominio -- `facturas_ext`, `inventario_ext`, `empleados_ext`,
`gastos_ext`, `proyectos_ext`, `clientes_ext`, `sedes_ext`,
`proveedores_ext`), orquestados por `DashboardBusinessService`, mas
Celery (`tasks.py`, `celery_beat_schedule.py`) para el snapshot
periodico.

## FASE C/D/K — Codigo muerto (INVESTIGADO, SIN ELIMINACION -- hallazgo importante)

**Encontrado el mismo patron estructural que en `gastos`
(`services.py` sibling de `services/`), pero aqui resuelto
CORRECTAMENTE, no es codigo muerto.**

Verificado empiricamente (igual que en `gastos`): `import
apps.tenant.dashboard.services` resuelve al paquete
(`services/__init__.py`), nunca al archivo sibling `services.py`
("Legacy facade... delega a Core Membership Bridge y BusinessService",
4015 bytes, funciones `get_user_role_in_tenant`,
`get_dashboard_redirect_url`, `get_dashboard_context`).

**A diferencia de `gastos` (donde el contenido de `services.py` ya
estaba duplicado en el paquete real, haciendolo genuinamente
inalcanzable e innecesario), aqui `services/__init__.py` contiene una
solucion deliberada al problema de shadowing:** usa
`importlib.util.spec_from_file_location()` para cargar `services.py`
**por su ruta de archivo exacta**, sin pasar por el sistema de import
normal de Python (que es justamente lo que causa el shadowing), y
re-exporta sus 3 funciones (`services/__init__.py:10-25`). Estas 3
funciones **SI se consumen activamente** en produccion:
`api/permissions.py` (3 usos de `get_user_role_in_tenant`) y
`api/views.py` (multiples usos de las 3 funciones).

**Conclusion: `services.py` NO es codigo muerto en `dashboard` -- es
codigo vivo, cargado mediante un workaround deliberado y funcional
para el mismo problema estructural que en `gastos` resulto ser
inofensivo por casualidad (contenido duplicado) pero aqui fue resuelto
con ingenieria explicita.** No se elimina nada. Este hallazgo confirma
que el patron "services.py + services/" no puede asumirse como
"siempre dead code" sin verificar cada caso -- se debe confirmar
consumidores reales antes de concluir, tal como se hizo aqui.

Resto de la app: 8 extractores verificados con consumidores reales
(`extractores/__init__.py` los reexporta todos, `business_service.py`
los orquesta). `urls_ui.py`/`views_ui.py` son stubs 404 intencionales
("UI movida a Core"), mismo patron ya visto en `contabilidad` --
activos y funcionales, no codigo muerto. Serializers/vistas "legacy"
en `api/` mantenidas explicitamente "por compatibilidad", wireadas en
`api/urls.py`.

**Conclusion FASE K: 0 lineas de codigo muerto confirmado para
eliminar** -- investigacion completa, sin acciones de limpieza en
esta app.

## FASE M — Normativa colombiana

`dashboard` NO esta en la lista explicita de apps que requieren
matriz normativa. **NO_APLICA** (agrega/visualiza metricas ya
calculadas por otras apps, no genera ni calcula obligaciones
tributarias propias).

## FASE Q — Tests / Regresion

Tests coleccionados: `apps/tenant/dashboard/tests/`. Regresion
lanzada en background tras confirmar `db`/`redis` healthy. Sin
cambios de codigo en esta app.

## Deferred

Ninguno nuevo.

## FASE X — Release Gate (checklist)

- [x] Modelos verificados (FASE B, 1 confirmado)
- [x] Codigo muerto investigado a fondo -- confirmado que NO hay nada que eliminar, incluyendo verificacion empirica del patron services.py/services/ (FASE C/D/K)
- [x] Normativa colombiana evaluada (FASE M -- NO_APLICA)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [ ] Regresion de la app -- **PENDIENTE**, en curso en background
- [x] Sin deferred items pendientes

## FASE Y — Decision

**PENDIENTE DE CIERRE** -- bloqueado por el resultado de la regresion
en curso. Se espera `COMPLETED` puro (sin hallazgos, sin cambios de
codigo) si la regresion confirma 0 fallos. **Esta es la ultima app
individual de las 16 -- al cerrarse, se avanza a FASE FINAL
(regresion global, auditoria cross-app, governance,
APP_AUDIT_MASTER_FINAL.md).**
