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
| 1 | core | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_core_AUDIT.md` |
| 2 | empresa | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_empresa_AUDIT.md` |
| 3 | perfil | COMPLETED | `documentacion/audits/apps/APP_perfil_AUDIT.md` |
| 4 | empleados | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_empleados_AUDIT.md` |
| 5 | clientes | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_clientes_AUDIT.md` |
| 6 | proveedores | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_proveedores_AUDIT.md` |
| 7 | inventario | COMPLETED | `documentacion/audits/apps/APP_inventario_AUDIT.md` |
| 8 | compras | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_compras_AUDIT.md` |
| 9 | ventas | COMPLETED_WITH_DEFERRED | `documentacion/audits/apps/APP_ventas_AUDIT.md` |
| 10 | cotizaciones | COMPLETED | `documentacion/audits/apps/APP_cotizaciones_AUDIT.md` |
| 11 | proyectos | COMPLETED | `documentacion/audits/apps/APP_proyectos_AUDIT.md` |
| 12 | gastos | COMPLETED | `documentacion/audits/apps/APP_gastos_AUDIT.md` |
| 13 | bancos | EN PROGRESO | `documentacion/audits/apps/APP_bancos_AUDIT.md` |
| 14 | facturas | PENDIENTE | `documentacion/audits/apps/APP_facturas_AUDIT.md` |
| 15 | contabilidad | PENDIENTE | `documentacion/audits/apps/APP_contabilidad_AUDIT.md` |
| 16 | dashboard | PENDIENTE | `documentacion/audits/apps/APP_dashboard_AUDIT.md` |

**APP_AUDIT_PROGRAM:** EN PROGRESO (12/16 -- 7 COMPLETED_WITH_DEFERRED,
5 COMPLETED)

**Regresion core (FASE Q, cierre):** `apps/tenant/core/` -- 73 passed,
19 skipped, 0 failed, 1 warning (min_value en DocumentoUploadAPITests,
preexistente, no relacionado con esta mision) en 8010s -- coincide
exactamente con el baseline conocido. Core cerrado como
`COMPLETED_WITH_DEFERRED` (2 items P2/P3 diferidos documentados en su
audit doc, no bloquean cierre segun regla de la mision).

**Regresion empresa (FASE Q, cierre):** `apps/tenant/empresa/` -- 30
passed, 0 failed, 1 warning (min_value, mismo hallazgo preexistente
que core) en 2525s. Se eliminaron 445 lineas de codigo muerto
confirmado (`impl/empresa_service.py`, `permissions.py` shim
deprecado, `scripts/test_empresa_refactor.py`) -- ver
`APP_empresa_AUDIT.md`. Cerrado como `COMPLETED_WITH_DEFERRED` (1 item
P2 diferido: cifrado de credenciales de correo en `MailInboxConfig`,
requiere decision de producto).

**Regresion perfil (FASE Q, cierre):** `apps/tenant/perfil/` -- 4
passed, 0 failed, 1 warning (min_value, mismo hallazgo preexistente)
en 1499.94s. **0 codigo muerto encontrado** -- primera app auditada sin
hallazgos de limpieza (arquitectura ya limpia: separacion
autoservicio/admin clara, sin shims huerfanos). Cerrado como
`COMPLETED` puro (sin items deferred).

**Regresion empleados (FASE Q, cierre):** `apps/tenant/empleados/` --
64 passed, 0 failed, 7 warnings preexistentes en 5089.06s (1:24:49).
**0 codigo muerto encontrado** (reutilizo el `.agent/` doc propio de
la app, de alta calidad, en vez de re-derivar). Matriz normativa
colombiana completa (`APP_empleados_NORMATIVE_MATRIX.md`, 15
obligaciones). Cerrado como `COMPLETED_WITH_DEFERRED` (4 items P1-P3,
principal: DSPNE sin transmision XML real a DIAN, DEUDA-11 ya
conocida).

**Regresion clientes (FASE Q, cierre):** `apps/tenant/clientes/` -- 35
passed, 0 failed, 3 warnings preexistentes en 1732.36s (0:28:52).
Se eliminaron 39 lineas de codigo muerto confirmado (4 clases sombra
sin consumidores en `services/services.py`, se conservo `crear_cliente()`
por tener 2 consumidores reales). Confirmado hallazgo Nivel3: Cartera
usa Pull Model para listado (lee de Facturas), modelo `Cartera` en si
sigue vivo para escritura. Cerrado como `COMPLETED_WITH_DEFERRED` (3
items P3).

**Regresion proveedores (FASE Q, cierre):** `apps/tenant/proveedores/`
-- 18 passed, 0 failed, 2 warnings preexistentes en 1655.60s
(0:27:35). Sin cambios de codigo (0 codigo muerto encontrado, a
diferencia de clientes). **Hallazgo P1 (CONTRACT_DRIFT) -- RESUELTO al
auditar `gastos` (app 12/16):**
`obtener_configuracion_retenciones()`/`calcular_componentes_retencion()`
(Retefuente 4%, ReteICA 0.966%) confirmadas como codigo muerto real
(nunca conectadas) -- `gastos.GastoBusinessService.procesar_gasto()`
usa `contabilidad.RetencionesService.obtener_retenciones_desde_tercero()`,
una implementacion independiente y correcta, ya centralizada segun
ADR-001 Pull Model. Sin gap funcional real. Reclasificado P1 -> P3
(limpieza de codigo muerto pendiente, no ejecutado en esta sesion para
no reabrir la app).
Cerrado como `COMPLETED_WITH_DEFERRED`.

**Regresion gastos (FASE Q, cierre):** `apps/tenant/gastos/` -- 21
passed, 0 failed, 3 warnings preexistentes en 3944.24s (1:05:44). Se
elimino `services.py` inalcanzable (shadowing con el paquete
`services/` del mismo nombre, verificado empiricamente con un import
real en interprete Python -- mismo bug historico de `empresa` 2025,
nunca corregido aqui). Cerrado como `COMPLETED` puro.

**Regresion inventario (FASE Q, cierre):** `apps/tenant/inventario/` --
25 passed, 0 failed, 6 warnings preexistentes en 5210.10s (1:26:50).
0 codigo muerto, 0 items deferred. Corregido el conteo de modelos de
`APP_AUDIT_MATRIX.md` (6 reales, no 1 -- herencia indirecta via
`TimeStampedModel`). Cerrado como `COMPLETED` puro.

**Regresion compras (FASE Q, cierre):** `apps/tenant/compras/` -- 31
passed, 0 failed, 2 warnings preexistentes en 5383.42s (1:29:43). 0
codigo muerto. 2 correcciones de seguridad/deuda tecnica documentadas
en el `.agent/` doc propio re-verificadas vigentes (DEBUG bypass
eliminado, F() atomico). Confirmado: sin logica de retencion (a
diferencia de proveedores) -- es workflow de Ordenes de Compra puro.
Cerrado como `COMPLETED_WITH_DEFERRED` (2 items P3).

**Regresion ventas (FASE Q, cierre):** `apps/tenant/ventas/` -- 13
passed, 0 failed, 1 warning preexistente en 2207.31s (0:36:47),
incluye la suite F23 completa (venta->inventario->contabilidad)
verde. 0 codigo muerto. Normativa: alcance delimitado -- ventas
gestiona `ResolucionFacturacion`/consecutivo, pero CUFE/UBL2.1/XAdES
se delegan a `facturas` (pendiente de auditar esa app). Cerrado como
`COMPLETED_WITH_DEFERRED` (2 items P2 + 1 puntero a `facturas`).

**Regresion cotizaciones (FASE Q, cierre):** `apps/tenant/cotizaciones/`
-- 14 passed, 0 failed, 1 warning preexistente en 2829.69s (0:47:09).
Se elimino un pipeline PDF completo y huerfano (`services/pdf/`, ~180
lineas) que duplicaba al realmente usado. Corregido conteo de modelos
en la matriz (5 reales, no 4 -- `ConfiguracionCotizacion` vive en
`configuracion/models.py`). Cerrado como `COMPLETED` puro.

**Regresion proyectos (FASE Q, cierre):** `apps/tenant/proyectos/` --
56 passed, 2 skipped preexistentes, 0 failed, 1 warning preexistente
en 6506.80s (1:48:26). Se elimino una clase `ProyectoServiceMixin`
sombra en `services/api_mixins.py` -- copy-paste de `gastos`
(docstring: "Service mixin para Gasto ViewSet"), sin consumidores
reales. Cerrado como `COMPLETED` puro.

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
