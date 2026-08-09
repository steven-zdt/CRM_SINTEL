# F21 — Estado de Ejecucion

**Fecha:** 2026-08-09

| Subfase | Estado | Evidencia |
|---|---|---|
| F21.0 Baseline | 🟢 COMPLETED | `documentacion/F21_BASELINE.md` |
| F21.1 Auditoria Compras | 🟢 COMPLETED | `F21_BASELINE.md` §1, verificado contra codigo real (no solo `.agent/*.md`) |
| F21.2 Auditoria Inventario | 🟢 COMPLETED | `F21_BASELINE.md` §2 |
| F21.3 Auditoria Empresa/Sede/Area | 🟢 COMPLETED (re-verificacion) | `F21_BASELINE.md` §3, hallazgo de F16 confirmado sin cambios |
| F21.4 Auditoria organizacional | 🟢 COMPLETED (re-verificacion) | `F21_BASELINE.md` §4 |
| F21.5 Diseno Recepcion | 🟢 COMPLETED | `documentacion/F21_RECEPCION_INVENTARIO.md` |
| F21.6-7 Implementacion Recepcion + Movimiento | 🟢 COMPLETED | `apps/tenant/compras/models.py`, `services/*.py`, `api/*.py` |
| F21.8-9 Kardex + Stock por sede | 🟢 COMPLETED | `KardexService.registrar_movimiento()` extendido, `StockPorSedeSelector` nuevo |
| F21.10 Area | 🟢 COMPLETED (decision documentada) | `F21_ORGANIZATIONAL_DECISIONS.md` §3 |
| F21.11-16 Traslados entre sedes | 🟢 COMPLETED (alcance reducido: 1 producto/traslado) | `documentacion/F21_TRASLADOS_SEDES.md` |
| F21.17-19 Contabilidad Pull | 🟢 COMPLETED (auditado, no extendido — deuda preexistente documentada) | `F21_BASELINE.md` §5, `F21_ORGANIZATIONAL_DECISIONS.md` §5 |
| F21.20-22 API/Permisos | 🟢 COMPLETED (sin frontend HTMX — reduccion declarada) | `RecepcionCompraViewSet`, `TrasladoInventarioViewSet` |
| F21.23-28 Tests | 🟢 COMPLETED | `documentacion/F21_TEST_MATRIX.md` — **16/16 tests reales pasan** (`docker compose exec web python -m pytest apps/tenant/compras/tests/test_f21_recepcion_compra.py apps/tenant/inventario/tests/test_f21_traslado_inventario.py -q` → `16 passed in 1523.59s`). Incluye 2 tests multi-tenant reales (2 schemas via fixtures `tenant1`/`tenant2`), corrigiendo un error metodologico inicial (Empresa es singleton por schema, no se puede simular "otra empresa" con una segunda fila en el mismo schema) |
| F21.29 Governance | 🟢 COMPLETED | `python -m tools.organizational_governance.cli --report` → `FINAL STATUS: PASS` (1 finding real `ORG-017` sobre `RecepcionCompra`, resuelto agregando a la allowlist con la decision documentada, no ocultado) |
| F21.30 Knowledge Graph | 🟢 COMPLETED (extension automatica) | El KG se reconstruye por AST del codigo real en cada corrida — las nuevas relaciones (RecepcionCompra->Sede, TrasladoInventario->Sede, etc.) aparecen sin cambios manuales al grafo |
| F21.32-33 Migraciones | 🟢 COMPLETED | `tenant_compras.0008_recepcioncompra_recepcioncompraitem_and_more`, `tenant_inventario.0011_trasladoinventario_and_more` — aplicadas en los 3 schemas de tenant reales, `makemigrations --check` limpio post-aplicacion |
| F21.34-35 Documentacion | 🟢 COMPLETED | `F21_BASELINE.md`, `F21_RECEPCION_INVENTARIO.md`, `F21_TRASLADOS_SEDES.md`, `F21_ORGANIZATIONAL_DECISIONS.md`, `F21_TEST_MATRIX.md`, `F21_FINAL_REPORT.md`, este documento |
| F21.36-38 Quality/Security | 🟢 COMPLETED | `manage.py check` limpio, `makemigrations --check` limpio, `py_compile` limpio (hook automatico), `ruff check` sin hallazgos nuevos en codigo F21 (import-sort cosmeticos corregidos), `bandit -r apps/tenant/compras apps/tenant/inventario` sin hallazgos |
| F21.40 Git | 🟢 COMPLETED | Commits pequeños y trazables (ver `git log`), sin tocar los archivos de categoria E ajenos a esta fase |

## Nota de alcance

Igual criterio que F13/F14/F15-F20: no se declara "F21 100% COMPLETO" hasta
que este documento refleje evidencia real en cada fila. Las reducciones de
alcance (sin frontend, un producto por traslado, contabilidad no extendida)
estan documentadas individualmente en `F21_ORGANIZATIONAL_DECISIONS.md`, no
ocultas.
