# APP_AUDIT_MASTER_STATUS — Auditoria integral de apps privadas SINTEL

**Mision:** auditoria integral, autonoma, progresiva y controlada de las
16 apps de `apps/tenant/**`, una app a la vez, siguiendo las fases
A-Z definidas en la mision (modelos, servicios, ORM, API, permisos,
multitenant/empresa/sede/area, frontend, codigo muerto, duplicacion,
normativa colombiana, tests, performance, documentacion).

**Inicio:** 2026-08-20.
**Orden de ejecucion** (segun mision, sujeto a ajuste documentado si
una dependencia real lo exige):
1. core
2. empresa
3. perfil
4. empleados
5. clientes
6. proveedores
7. inventario
8. compras
9. ventas
10. cotizaciones
11. proyectos
12. gastos
13. bancos
14. facturas
15. contabilidad
16. dashboard

---

## FASE 0 — Baseline global (2026-08-20)

- **Rama:** `feat/onboarding-cookie`
- **Commit:** `622a5d1` (docs: arquitectura_general DOC-M39 -- cierre completo Nivel 3)
- **`git status`:** working tree tiene WIP preexistente extenso NO
  relacionado con esta mision (workflows CI, Makefile, docker-compose,
  nginx, requirements.txt, herramientas EKG (`tools/ekg/`), tests de
  `empleados`/`cotizaciones`/`inventario`/`proveedores`, documentos
  varios) -- de sesiones anteriores del usuario o de otras sesiones
  paralelas. **No se toca, no se commitea junto con cambios de esta
  mision.** Cada commit de esta auditoria debe listar archivos
  explicitos (`git add <archivo>`), nunca `git add -A`.
- **`manage.py check`:** `System check identified no issues (0 silenced)` -- PASS.
- **`makemigrations --check --dry-run`:** `No changes detected` -- PASS
  (0 migraciones pendientes).
- **`pytest --collect-only`:** 2 hallazgos reales de infraestructura de
  tests bloqueaban la coleccion global por completo (nunca se habia
  intentado sin argumentos en esta sesion, solo por app/archivo):
  1. Archivo espurio `nul` en la raiz del repo (6662 bytes, contenido
     JS, artefacto de Windows por un `> nul` mal interpretado en Git
     Bash, sin trackear en git, fecha 2026-08-13, ajeno a esta
     mision) -- `AssertionError: WindowsPath('.../nul') is not a
     file`. Se movio (no elimino) al scratchpad de la sesion.
  2. `pytest.ini` no excluia `node_modules` de `norecursedirs` --
     pytest intentaba recolectar dentro de
     `tests/e2e/node_modules/.bin/playwright` (symlink de npm que
     Windows no puede resolver via `os.stat`) ->
     `OSError: [WinError 1920]`. Se agrego `node_modules` a
     `norecursedirs` en `pytest.ini` (fix minimo, 1 linea).
  - **Resultado tras ambos fixes: `2064 tests collected in 41.01s`,
    0 errores de coleccion** -- coincide con el baseline global ya
    conocido de sesiones anteriores (`documentacion/F33.15_
    TESTING_EXECUTION_STATUS.md`). FASE 0 PASS.

## FASE 1 — Inventario real de `apps/tenant/*`

Ver `documentacion/APP_AUDIT_MATRIX.md` para el inventario completo
(modelos, migraciones, tests, JS, templates por app).

---

## Progreso por app

| # | App | Estado | Doc |
|---|-----|--------|-----|
| 1 | core | COMPLETED_WITH_DEFERRED (regresion en curso) | `documentacion/audits/apps/APP_core_AUDIT.md` |
| 2 | empresa | PENDIENTE | `documentacion/audits/apps/APP_empresa_AUDIT.md` |
| 3 | perfil | PENDIENTE | `documentacion/audits/apps/APP_perfil_AUDIT.md` |
| 4 | empleados | PENDIENTE | `documentacion/audits/apps/APP_empleados_AUDIT.md` |
| 5 | clientes | PENDIENTE | `documentacion/audits/apps/APP_clientes_AUDIT.md` |
| 6 | proveedores | PENDIENTE | `documentacion/audits/apps/APP_proveedores_AUDIT.md` |
| 7 | inventario | PENDIENTE | `documentacion/audits/apps/APP_inventario_AUDIT.md` |
| 8 | compras | PENDIENTE | `documentacion/audits/apps/APP_compras_AUDIT.md` |
| 9 | ventas | PENDIENTE | `documentacion/audits/apps/APP_ventas_AUDIT.md` |
| 10 | cotizaciones | PENDIENTE | `documentacion/audits/apps/APP_cotizaciones_AUDIT.md` |
| 11 | proyectos | PENDIENTE | `documentacion/audits/apps/APP_proyectos_AUDIT.md` |
| 12 | gastos | PENDIENTE | `documentacion/audits/apps/APP_gastos_AUDIT.md` |
| 13 | bancos | PENDIENTE | `documentacion/audits/apps/APP_bancos_AUDIT.md` |
| 14 | facturas | PENDIENTE | `documentacion/audits/apps/APP_facturas_AUDIT.md` |
| 15 | contabilidad | PENDIENTE | `documentacion/audits/apps/APP_contabilidad_AUDIT.md` |
| 16 | dashboard | PENDIENTE | `documentacion/audits/apps/APP_dashboard_AUDIT.md` |

**APP_AUDIT_PROGRAM:** EN PROGRESO (0/16 COMPLETED)

---

## Contexto heredado relevante (no repetir investigacion)

Esta auditoria se apoya en hallazgos ya confirmados en la sesion
inmediatamente anterior (F33.15-B Nivel 3, regresion incremental de
tests, ver `documentacion/F33.15_TESTING_EXECUTION_STATUS.md`):

- `Empresa` es singleton por schema (`UniqueConstraint` en
  `singleton_key`) -- un tenant nunca puede tener una segunda empresa
  real.
- `IsTenantAdminOrReadOnly` resuelve el rol via `TenantProfile.rol`
  (schema tenant), no `TenantMembership.rol` (schema public).
- `@override_settings(...)` como decorador de clase no aplica con
  `TenantTestCase` (django_tenants) -- requiere `with
  override_settings(...):` por request/test.
- `clientes/CarteraViewSet` y varios modulos de grillas migraron a
  Pull Model / django-tables2+HTMX (FASE 5-BIS) -- UI legacy
  (Tabulator, modales XML dedicados) fue reemplazada, no coexiste.
- Endpoint universal de documentos real:
  `/api/v1/core/_apps/facturas/upload-document/` (protegido por
  `FEATURE_UPLOAD_DOCUMENT_ENDPOINT`). `factura-upload-ubl` esta
  `DEPRECATED` en su propio docstring; `ingest_document(async_mode=...)`
  esta documentado como "FASE 5: placeholder para futuro", sin
  implementar.
- Tarea flageada en sesion separada por el usuario (`task_c077c6a7`):
  agregar try/except a la rama activa de
  `FacturaBusinessService.importar_documento()` alrededor de
  `ingest_document()` -- en curso de forma independiente, no forma
  parte de esta mision salvo que se confirme cerrada y se integre.
