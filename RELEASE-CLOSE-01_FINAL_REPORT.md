# RELEASE-CLOSE-01 — Informe Final

**Fecha:** 2026-09-15
**Rama:** `feat/onboarding-cookie`
**Commit base:** working tree sobre `68275b6` (fix(bancos): AttributeError real en tabla de extractos + KPI de conciliación en vivo)

---

## 1. VEREDICTO

```
RELEASE-CLOSE-01 = COMPLETED
```

Facturas v4.0.0 y COTIZACIONES-02 quedan verificados contra código real, con regresión fresca en
verde (0 failures) y sin residuos arquitectónicos vivos. No se ejecutó ningún `git commit` — ver
§11/§14-15 para el motivo y la clasificación del working tree.

---

## 2. FACTURAS (v4.0.0)

```
Architecture:      PASS — 0 referencias vivas repo-wide a BancosBridge/total_pagado_bancos/
                    saldo_pendiente/recalcular_estado_pago_automatico ni a los 8 endpoints
                    removidos (materialize, vincular-cliente/proveedor/cotizacion,
                    obtener-retenciones, inventario-catalogo, trazabilidad-inventario,
                    importar-ubl). Confirmado por grep repo-wide (código, no solo docs).
Regression:        PASS — 205 passed, 0 failed, 12 skipped (suite completa de facturas).
Tenant isolation:  PASS — sin cambios en esta pasada al mecanismo DSV/empresa_id existente;
                    tests de aislamiento incluidos en la corrida de arriba.
Frontend/backend:  PASS — 0 callers JS a endpoints removidos (confirmado por grep). 1 huérfano
                    encontrado y corregido: tools/smoke_facturas.sh apuntaba a /materialize/
                    (script de smoke manual, no pytest/CI) — actualizado a /create-from-dto/.
Dependencies:      PASS — tools/organizational_governance/cli.py --report: 0 FAIL/WARN en
                    las 8 categorías (ejecutado dos veces: durante Docker corriendo pytest en
                    paralelo, sin conflicto por ser análisis estático puro sin DB; y de nuevo
                    tras liberar el contenedor, vía venv local).
Documentation:     PASS — apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md reconciliado:
                    6 bloques de contenido histórico (v3.11.0, Pull Model Bancos) que
                    contradecían la sección v4.0.0 del mismo archivo marcados [REMOVIDO v4.0.0]
                    / [HISTÓRICO], sin borrar el historial. Comentarios desactualizados en
                    apps/tenant/core/api/urls.py (listaban importar-ubl/materialize como rutas
                    vigentes) corregidos.
Verdict:           PASS
```

---

## 3. COTIZACIONES-02

```
Functional:        PASS — máquina de estados (BORRADOR/ENVIADA/APROBADA/RECHAZADA/ARCHIVADA),
                    Cotización→Venta→Factura, Cotización→Proyecto, historial append-only,
                    todo confirmado vigente en código real (business_service.py leído completo).
Regression:        PASS — 358 passed, 0 failed, 13 skipped (ventas+facturas+cotizaciones+compras,
                    4:01:13). Corrida anterior (otra sesión) había dado 357/2 — no se reutiliza
                    ese resultado; esta cifra de hoy es la que cuenta.
Idempotency:       PASS — UniqueConstraint(empresa, numero) en Factura (migración facturas.0041)
                    + IntegrityError capturado en transaction.atomic() anidado, confirmado en
                    business_service.py de facturas.
State machine:     PASS — degradación/transiciones ya cubiertas por tests existentes,
                    sin regresión en la corrida de arriba.
Documentation:     PASS — docs/cotizaciones/COTIZACIONES_RELEASE_GATE.md actualizado con la
                    re-verificación fresca; MEMORY.md corregido (ya no dice "EN VERIFICACION").
Verdict:           COMPLETED_WITH_DEFERRED (sin cambio respecto al veredicto de 2026-09-14 —
                    Abastecimiento Cotización→OrdenCompra→Inventario sigue DEFERRED explícito,
                    sin evidencia de un matching confiable entre catálogos).
```

---

## 4. TEST MATRIX

| Suite | PASS | FAIL | ERROR | SKIP | Estado |
| ----- | ---: | ---: | ----: | ---: | ------ |
| `apps/tenant/facturas/tests` (aislada) | 205 | 0 | 0 | 12 | PASS |
| `apps/tenant/facturas/tests/test_retenciones_backward_compat.py` (aislada, post-fix) | 12 | 0 | 0 | 0 | PASS |
| `ventas + facturas + cotizaciones + compras` (regresión 4 apps) | 358 | 0 | 0 | 13 | PASS |
| `manage.py check` | — | — | — | — | PASS (0 issues) |
| `manage.py makemigrations --check --dry-run` | — | — | — | — | PASS (No changes detected) |
| `tools/organizational_governance/cli.py --report` | — | — | — | — | PASS (0 WARN/FAIL, 8/8 categorías) |

Todas las corridas de esta tabla se ejecutaron frescas en esta sesión (no se reutilizó ningún
resultado histórico), primero vía `docker compose exec web pytest` (mientras el contenedor estaba
libre) y, tras la nueva regla de testing establecida a mitad de sesión, vía `venv/Scripts/python.exe`
local para `manage.py check`/`makemigrations`/`organizational_governance` (re-confirmados sin
cambios de resultado).

---

## 5. FAILURES

### `test_factura_total_retenciones_multiples`

```
root cause:      RetencionesService.crear_retencion() aplica un UniqueConstraint de idempotencia
                 real (documento_origen, tipo, reversada=False) desde el commit 4dbe80c
                 (REM-P0-03, anterior y ajeno a esta misión). El test creaba 3 retenciones
                 RETEFUENTE para la MISMA factura esperando que se sumaran (50+30+20=100); la
                 2a y 3a llamada chocan con el guard y devuelven la fila existente (50.00) en
                 vez de crear una nueva -- comportamiento correcto por diseño, no un bug.
classification:  A -- test obsoleto. Confirmado leyendo producción (no asumido): el único
                 caller real (facturas/business_service.py::guardar_desde_dto()) invoca
                 crear_retencion() como máximo una vez por tipo por documento -- el escenario
                 de 3 llamadas al mismo tipo/documento nunca ocurre en producción.
action:          Test renombrado a test_factura_creacion_retencion_repetida_es_idempotente,
                 reescrito para verificar la conducta idempotente real (3 llamadas devuelven
                 la MISMA fila, total permanece en 50.00). Cero cambios en código de producción.
evidence:        Reproducido (`1 failed, 11 passed`, AssertionError Decimal('50.00') !=
                 Decimal('100.00')) antes del fix; 12 passed, 0 failed después.
```

No quedan failures sin clasificar.

---

## 6. FILES

### CREATED (esta sesión)

- `RELEASE-CLOSE-01_FINAL_REPORT.md` (este archivo)

### MODIFIED (esta sesión, directamente atribuibles a RELEASE-CLOSE-01)

- `apps/tenant/facturas/tests/test_retenciones_backward_compat.py` — fix del test obsoleto (§5)
- `tools/smoke_facturas.sh` — endpoint huérfano corregido (`/materialize/` → `/create-from-dto/`)
- `apps/tenant/core/api/urls.py` — comentarios desactualizados corregidos (sin cambio de código)
- `apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md` — reconciliación de contradicciones + resultados frescos
- `docs/cotizaciones/COTIZACIONES_RELEASE_GATE.md` — re-verificación fresca añadida
- `documentacion/arquitectura_general.md` — DOC-M56 nuevo + correcciones de punteros "EN VERIFICACION"
- `MEMORY.md` — entrada de cierre + corrección de estado histórico + regla de testing local

### EXCLUDED (deliberadamente, no tocados ni commiteados — ver §11)

Todo lo demás en el working tree: cambios preexistentes de Clientes, Empleados, Bancos (parcial),
Compras, AI/N8N y otras misiones — ver clasificación completa en §14-15.

---

## 7. MIGRATIONS

```
new:      ninguna generada en esta sesión.
pending:  0 (makemigrations --check --dry-run → "No changes detected", confirmado 2 veces:
          durante la sesión y en la re-verificación final vía venv local).
verified: facturas.0041 (uniq_factura_numero_por_empresa) y tenant_cotizaciones.0010
          (rename de estados + CotizacionHistorialEstado/CotizacionEstadoConfig) — ambas
          preexistentes de sesiones anteriores, confirmadas aplicadas y consistentes con
          el estado real de los modelos.
```

---

## 8. DOCUMENTATION

```
updated:                  apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md,
                          docs/cotizaciones/COTIZACIONES_RELEASE_GATE.md,
                          documentacion/arquitectura_general.md (DOC-M56),
                          MEMORY.md.
historical corrections:   6 bloques de COMPLETO_FLUJO_FACTURAS.md (Pull Model Bancos v3.11.0,
                          tabla "Integración con Otros Módulos", tabla de compliance AGENTS.md,
                          tabla de Service Layer con vincular_cliente/proveedor ya removidos)
                          marcados [REMOVIDO v4.0.0]/[HISTÓRICO] sin borrar el contenido original.
contradictions resolved:  "COTIZACIONES-02 EN VERIFICACION" (MEMORY.md, arquitectura_general.md
                          DOC-M51 §D) corregido a COMPLETED_WITH_DEFERRED con puntero a la
                          evidencia fresca de esta misión (DOC-M56).
```

`docs/comercial/COMERCIAL_04_IDEMPOTENCIA.md` fue auditado y encontrado ya preciso — no requirió
cambios.

---

## 9. NEXT NATURAL STEP

```
BANCOS-04
```

Objetivo conceptual: `CuentaBancaria → Extracto → Movimiento → Matching → Aplicación 1:N →
Conciliación`. Debe consumir Facturas **únicamente** mediante el contrato de lectura ya
estabilizado en esta misión (`FacturaInterAppAPI.get_by_id()`, confirmado 100% read-only) — nunca
reintroducir `BancosBridge` ni ningún mecanismo de escritura Bancos→Facturas. No implementado en
esta misión.

---

## 10. Auditoría de dependencias (Fase 9 de la misión)

`tools/organizational_governance/cli.py --report` — PASS, 0 WARN/FAIL en las 8 categorías
(Architecture, Security, Multi Tenant, Organizational, Integrations, Service Layer, Documentation,
Test Coverage). Ejecutado dos veces en esta sesión con resultado idéntico.

---

## 11. Reconciliación del working tree — nota importante

**No se ejecutó ningún `git add`/`git commit` en esta misión.** El working tree al momento de
iniciar esta misión ya contenía cambios sin commitear de MUCHAS misiones distintas y simultáneas —
no solo Facturas/Cotizaciones:

- Bancos v3.0 (mayormente ya commiteado en `f24d91c`/`68275b6`; quedan unos pocos archivos con
  cambios de la Fase 2 de Facturas v4.0.0 — legítimamente parte de esta misión, ver §14).
- Clientes (cartera, contactos, migraciones nuevas de representante legal) — mission separada.
- Empleados (NOMINA-01) — misión separada.
- Compras (CO-1..4, sincronización con Facturas vía `factura_asociada`) — misión separada
  (VENTAS_COMPRAS_FACTURAS-01 / auditoría 2026-09-12).
- AI/N8N (`apps/services/ai/`, `apps/services/integration_events/`, AI-UI-01) — misiones separadas.
- Un directorio huérfano `C:/Users/steve/AppData/Local/Temp` creado accidentalmente en la raíz del
  repo (fecha 2026-09-14, vacío) — probablemente un bug de alguna herramienta anterior interpretando
  una ruta absoluta de Windows dentro de un contexto POSIX. No se eliminó (no es parte del alcance
  de esta misión), se deja señalado para que el usuario decida.

Commitear todo esto junto violaría explícitamente la instrucción de la misión ("no mezclar cambios
funcionalmente independientes en un commit... no sobrescribir/revertir/incluir accidentalmente
Clientes/Empleados/Bancos/AI/N8N") y la política general de esta sesión de nunca commitear sin
pedido explícito del usuario. Se recomienda que el usuario decida la estrategia de commits
(probablemente varios commits separados, uno por misión) antes de cerrar la rama.

---

## 12-13. Auditoría multi-tenant y frontend↔backend

Ver §2 (Facturas) y §3 (Cotizaciones-02) — ambas confirmadas PASS con evidencia real (grep
repo-wide + regresión de tests de aislamiento incluidos en las suites ejecutadas). No se
encontraron violaciones de tenant isolation ni endpoints/callers huérfanos nuevos más allá del
ya reportado en §2 (smoke script).

---

## 14. Clasificación del working tree (por app/misión)

| Área | Estado en working tree | Pertenece a RELEASE-CLOSE-01 |
|---|---|---|
| `apps/tenant/facturas/**` | M (extenso) | ✅ Sí — Facturas v4.0.0 |
| `apps/tenant/cotizaciones/**` | M + nuevos | ✅ Sí — COTIZACIONES-02 |
| `apps/tenant/ventas/**` | M + nuevos | ✅ Sí — COMERCIAL-04/COTIZACIONES-02 (tramo Venta→Factura) |
| `apps/tenant/bancos/services/crud_service.py` + 3 JS + `.agent` doc | M (pequeño) | ✅ Sí — Fase 2 de Facturas v4.0.0 (desacople) + alineación frontend↔backend |
| `apps/tenant/core/api/urls.py`, `core/api/v1/facturas/viewsets.py` | M (pequeño) | ✅ Sí — dual-registration ADR-002 de Facturas |
| `tools/smoke_facturas.sh` | M | ✅ Sí — fix de esta misión |
| `documentacion/arquitectura_general.md`, `MEMORY.md`, docs de cotizaciones/facturas | M | ✅ Sí — Fase 10 de esta misión |
| `apps/tenant/compras/**` (grueso) | M extenso | ❌ No — CO-1..4 / VENTAS_COMPRAS_FACTURAS-01 (misión separada) |
| `apps/tenant/clientes/**` | M + nuevos | ❌ No — Clientes v3.12-3.15 (misión separada) |
| `apps/tenant/empleados/**` | M + nuevos | ❌ No — NOMINA-01 (misión separada) |
| `apps/tenant/proyectos/**` | M (pequeño) | ❌ No — auditoría 2026-09-12 (P-1) |
| `apps/tenant/contabilidad/**` (JS + tests F24) | M | ❌ No — sin relación con esta misión |
| `apps/tenant/core/static/.../ai.assistant.js`, `workspace.html`, `_header.html`, offcanvas IA | M/nuevos | ❌ No — AI-UI-01 |
| `apps/services/ai/`, `apps/services/integration_events/`, `crear_identidad_tecnica_n8n.py`, `docs/n8n/`, `docs/ai/` | nuevos | ❌ No — AI-VECTOR/N8N-SINTEL-01 |
| `.claude/settings.local.json`, `.env.example`, `docker-compose.yaml`, `notas.txt` | M | ❌ No — infraestructura/config, sin relación |
| `apps/tenant/proveedores/**` | Sin cambios al iniciar; ahora M (misión PROVEEDORES en curso, en paralelo) | ❌ No — misión distinta, iniciada por el usuario durante esta sesión |
| Directorio huérfano `C:/` en raíz del repo | untracked, vacío | ⚠️ Ni uno ni otro — residuo accidental, señalado, no tocado |

---

## 15. Archivos deliberadamente excluidos de cualquier acción de esta misión

Todos los listados como "❌ No" en la tabla de §14, más cualquier archivo `?? ` (untracked) no
mencionado explícitamente en §6 CREATED. Ninguno fue leído más allá de lo necesario para
clasificarlo, ninguno fue modificado, movido ni eliminado.

---

## Principio aplicado

Esta misión no buscó crear código nuevo. Buscó y consiguió demostrar, con evidencia real (no
inferencia ni reutilización de resultados históricos), que Facturas v4.0.0 y COTIZACIONES-02
funcionan, respetan sus límites de dominio, no tienen dependencias huérfanas nuevas (más allá de
la ya corregida) y no tienen contradicciones documentales sin resolver.
