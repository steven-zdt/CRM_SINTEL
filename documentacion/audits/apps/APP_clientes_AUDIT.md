# APP_clientes_AUDIT — Auditoria integral (app 5/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: core -> empresa
-> perfil -> empleados -> **clientes** -> proveedores -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A/B — Mapa de negocio y modelos

`apps/tenant/clientes` tiene su propio `.agent/AUDITORIA_FLUJO_
CLIENTES.md` (v3.11.0, 2026-06-04, 520 lineas, "16/16 AGENTS.md
COMPLIANCE"), usado como fuente primaria (mismo criterio aplicado en
`empleados`), verificado contra el codigo actual.

**Verificado 1:1 contra codigo:** 3 modelos (`Cliente`, `ContactoCliente`,
`Cartera`), 8 migraciones, coincide con `APP_AUDIT_MATRIX.md`.

Resumen de negocio: SSoT de identidad legal de clientes por empresa
(`UniqueConstraint(empresa, tipo_documento, numero_documento)`),
gestion de contactos, configuracion de retenciones colombianas
(Retefuente/ReteICA/ReteIVA -- solo config, ver FASE M), y **Cartera /
Cuentas por Cobrar via Pull Model** (`CarteraViewSet.list()` lee de
`Factura.naturaleza='VENTA'`, no del modelo `Cartera` -- confirma el
hallazgo heredado de F33.15-B Nivel 3 sobre la migracion FASE 5-BIS).
El modelo `Cartera` en si NO esta muerto: se sigue usando para
`registrar_cartera()`/`registrar_abono()` (escritura), solo el LISTADO
migro a leer directamente de Facturas.

## FASE C/D/K — Service Layer y codigo muerto (CONFIRMADO Y CORREGIDO)

**Encontrado codigo muerto real, a diferencia de perfil/empleados.**
Estructura: `services/{selectors,crud_service,business_service,
api_mixins,services}.py` (5 archivos, coincide con matriz) + `api/
mixins.py` (bridge real hacia ViewSets).

Investigacion de consumidores (grep de nombres de clase/funcion, repo
completo):

- `services/services.py` es un modulo auto-declarado "Backward-
  compatibility layer" (docstring propio) que definia 4 clases:
  `ClienteBusinessService` (subclase que SOMBREABA el import del
  mismo nombre desde `business_service.py`, agregando `qs_list()`/
  `qs_detail()`), `ContactoClienteService`, `ClienteServiceMixin`,
  `ContactoClienteServiceMixin`. **Las 4 tenian CERO consumidores en
  todo el repo** -- `services/__init__.py` (el punto de entrada real
  del paquete) importa `ClienteServiceMixin`/`ContactoClienteServiceMixin`
  desde `.api_mixins` (la version real, con `BaseServiceMixin`), NO
  desde `.services`; `api/viewsets.py` y `api/mixins.py` tambien
  importan exclusivamente desde `.api_mixins`. Las clases de
  `services.py` eran una sombra completa, nunca alcanzada por ningun
  import real -- **DEAD_CONFIRMED, eliminadas** (39 lineas).
- `crear_cliente(empresa, data)`, la unica funcion del mismo archivo,
  **SI tiene consumidores reales**: `tests/test_idempotence_v2614.py`
  y `tests/test_clientes_api_and_service.py` la importan directamente
  (`from apps.tenant.clientes.services.services import crear_cliente`).
  Se conserva sin cambios funcionales -- solo se corrigio para usar el
  `ClienteBusinessService` REAL (ya no habia razon para la sombra,
  dado que `crear_cliente()` solo llama a
  `registrar_cliente_completo()`, metodo que existe identico en la
  clase real). Verificado que el comportamiento no cambia: la
  subclase eliminada no sobreescribia `registrar_cliente_completo()`,
  solo agregaba `qs_list`/`qs_detail`, que `crear_cliente()` nunca
  invoca.
- `services/api_mixins.py` (real, con `BaseServiceMixin`) -- verificado
  con consumidores activos en `api/viewsets.py`/`api/mixins.py`, sin
  cambios.

**Total eliminado: 39 lineas** (4 clases sombra sin consumidores,
dentro de `services/services.py`; el archivo se conserva porque
`crear_cliente()` sigue siendo necesario para los 2 tests existentes).

**Deferred (no bloquea cierre):** `crear_cliente()` sigue marcado como
"Deprecated backward-compatibility function for testing" en su propio
docstring -- los 2 tests que la usan podrian migrar a llamar
`ClienteBusinessService.registrar_cliente_completo()` directamente en
una sesion futura de limpieza de tests, pero no es un gap funcional
real (los tests pasan, la funcion es correcta), asi que no se toca
ahora (regla de la mision: no modificar tests sin una razon funcional
real).

## FASE J — Frontend

`views.py`/`urls.py` (22 lineas, wireado en `config/urls_tenant.py:182`)
y `tables.py` verificados, sin hallazgos.

## FASE M — Normativa colombiana

`clientes` esta en la lista explicita de apps que requieren matriz
normativa. Ver **`documentacion/audits/apps/
APP_clientes_NORMATIVE_MATRIX.md`**. Hallazgo principal: `clientes` es
un modulo de **configuracion** de retenciones (flags + porcentajes
por cliente, con Zero Trust en `_sanitize_retenciones()`), no de
**calculo** -- la validacion normativa real de tarifas/cuantias contra
la DIAN vive en `apps/tenant/contabilidad` (`RetencionesService`,
ADR-001, Pull Model), fuera del alcance de esta app. Se revisara con
evidencia completa en la auditoria de `contabilidad` (app 15/16).

## FASE Q — Tests / Regresion

Tests coleccionados: `apps/tenant/clientes/tests/` (7 archivos segun
`.agent/` doc: `test_auth_session_smoke`, `test_clientes_api_and_
service`, `test_clientes_crud_workspace`, `test_contacto_cliente_crud`,
`test_cartera_crud_api`, `test_idempotence_v2614`, `conftest`).
Regresion ejecutada tras la eliminacion de codigo muerto: **35 passed,
0 failed, 3 warnings preexistentes (min_value DRF, ya visto en apps
anteriores) en 1732.36s (0:28:52)**. Confirmado especificamente:
`test_idempotence_v2614.py` (los 2 tests que consumen `crear_cliente()`
desde el archivo editado) -- ambos PASSED, sin efectos secundarios del
cambio en `services/services.py`.

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | `crear_cliente()` sigue siendo un shim "deprecado para testing" con 2 consumidores reales -- migrar los tests a la API real en una sesion de limpieza futura | P3 |
| 2 | Validacion de tarifas de retencion contra normativa DIAN vigente -- pertenece a `contabilidad`, no a `clientes` (ver matriz normativa) | P3 para esta app |
| CLI-01 a CLI-04 | 4 items ya documentados en el `.agent/` doc propio de la app (columna Saldo Pendiente en UI, highlighting de vencidas, paginacion server-side de cartera_resumen para >500 facturas, test de concurrencia de `registrar_abono`) -- preexistentes, no generados por esta auditoria, se listan por completitud | MEDIA/BAJA (segun `.agent/` doc original) |

## FASE X — Release Gate (checklist)

- [x] Modelos verificados contra `.agent/` doc existente (FASE B)
- [x] Service Layer auditado, codigo muerto encontrado y eliminado (FASE C/D/K)
- [x] Frontend verificado, sin hallazgos (FASE J)
- [x] Matriz normativa colombiana completa (FASE M, documento separado)
- [x] `py_compile` limpio en el archivo editado
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 35 passed, 0 failed
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**COMPLETED_WITH_DEFERRED** -- 35/35 tests pasan, 0 regresiones,
confirmado especificamente que el cambio en `services/services.py` no
afecto a sus consumidores directos. 3 items deferred (ninguno
bloqueante, todos P3).
