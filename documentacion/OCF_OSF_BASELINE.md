# OCF/OSF — Baseline y Congelamiento (FASE 0)

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED
**Metodologia:** Codigo real + `git status`/`git log`/`git diff` real. No se asumio nada de `MEMORY.md`, `arquitectura_general.md` ni de los ADR sin verificar contra el working tree.
**Alcance de esta fase:** solo inventario y clasificacion. **Cero codigo funcional modificado.**

---

## 1. Estado Git

| Hecho | Valor |
|---|---|
| Branch actual | `feat/onboarding-cookie` |
| Ultimo commit real | `371f19d` — 2026-08-05 — "chore: elimina carpeta basura con ruta de Windows mal formada" |
| `main` (rama base) | `1e30cc7` — 2026-03-27 — "test(onboarding): integration test for OTT -> HttpOnly cookie flow" |
| Divergencia `main...HEAD` | `main` no tiene commits propios sobre el merge-base; `HEAD` tiene **95 commits** que `main` no tiene |
| Archivos con cambios en el working tree | **209** (`git status --porcelain`) |
| — Modificados (`M`) | 112 |
| — Nuevos sin trackear (`??`) | 96 |
| — Eliminados (`D`) | 1 (`apps/tenant/facturas/.agent/AUDITORIA_FLUJO_FACTURAS.md`, reemplazado por `COMPLETO_FLUJO_FACTURAS.md`) |
| `git add`/`commit` ejecutados en esta fase | **Ninguno** — cumpliendo la regla de no `git add .` indiscriminado |

**Observacion critica:** `main` esta congelada desde 2026-03-27 y la rama de trabajo real del proyecto es `feat/onboarding-cookie`, que ha acumulado 95 commits y ahora 209 archivos adicionales sin commitear que **no tienen relacion con "onboarding" ni "cookie"** en su mayoria (EKG, Auditoria Enterprise, OCF, OSF). El nombre de la rama ya no describe su contenido. No se corrige en esta fase (es una decision de gobernanza de Git, no de arquitectura organizacional) — se deja como riesgo documentado en §8.

---

## 2. Estado OCF (Organizational Context Framework)

**Afirmacion de `MEMORY.md`:** proyecto completo, 14/14 fases, cerrado 2026-08-08.
**Verificacion contra codigo real:** confirmada — existe codigo real, no solo documentacion.

Componentes centrales, todos **sin trackear en git** (`??`):

| Archivo | Contenido verificado |
|---|---|
| `apps/tenant/core/services/organizational_context.py` | `OrganizationalContext` (dataclass frozen), `OrganizationalContextError`, `OrganizationalContextMixin` |
| `apps/tenant/core/services/organizational_scope.py` | `OrganizationalScope`, `OrganizationalScopeError`, `OrganizationalScopeMixin`, `sede_esta_en_alcance()`, `area_esta_en_alcance()` |
| `apps/tenant/core/services/organizational_permissions.py` | `resolve_organizational_permission_level()`, `level_meets_minimum()` |
| `apps/tenant/core/services/organizational_dsv.py` | `OrganizationalDSVError`, `verify_organizational_dsv()`, `is_organizationally_consistent()` |
| `apps/tenant/core/services/organizational_bridges.py` | `OrganizationalBridge` (Protocol), `CotizacionOrganizationalBridge`, `ClienteOrganizationalBridge`, `ProveedorOrganizationalBridge` |
| `apps/tenant/core/services/organizational_filters.py` | `filter_by_context()`, `filter_by_scope()`, `filter_by_scope_null_safe()` |
| `apps/tenant/core/services/organizational_service_layer.py` | `resolve_empresa_and_sede()`, `resolve_perfil()`, `crear_orden_compra_desde_contexto()` |
| `apps/tenant/core/services/sede_context.py` | `resolve_sede_activa_id()` (consumido por `SintelDSVMixin.get_sede_id()`, ver `apps/tenant/api/mixins.py`) |
| `apps/tenant/core/context_processors.py` | (nuevo, sin auditar contenido en esta fase) |
| `apps/tenant/core/api/contexto.py` | `ContextoOrganizacionalView`, `ContextoSedeView` — endpoints `GET /api/v1/core/contexto/` y `/core/contexto/sede/` (registrados en `apps/tenant/core/api/urls.py`, modificado) |
| `apps/tenant/core/static/core/js/common/sede_selector.js` | Selector de "sede activa" en el header compartido (frontend) |
| `apps/tenant/api/mixins.py` (M) | `SintelDSVMixin.get_sede_id()`, `BaseServiceMixin._get_sede_id_seguro()`/`_get_sede()` — nuevos metodos, no reemplazan `get_empresa_id()` existente |
| `apps/tenant/api/permissions.py` (M, 88+/26-) | `HasOrganizationalScope`, `OrganizationalPermission` — clases nuevas |
| `apps/tenant/perfil/models.py` (M) + `apps/tenant/perfil/migrations/0008_add_alcance_and_sede_area_context.py` (nuevo) | `TenantProfile.alcance`, enum `AlcanceOrganizacional` |
| `apps/tenant/core/models.py` (M) | `SedeAwareModel` (mixin abstracto, ver ADR-003) |
| `docs/ADR-004-organizational-context-framework-diseno.md` | **Sin trackear.** Contenido literal: `**Estado:** PROPOSED (diseño únicamente — cero código, cero módulos modificados)` — **desactualizado**: el codigo de arriba contradice esa frase. No se corrigio el archivo en esta fase (fuera de alcance de FASE 0; queda para FASE 4). |
| `documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md` | Documento maestro de OCF, sin trackear |
| `documentacion/ORGANIZATIONAL CONTEXT FRAMEWORK (OCF).md` | Prompt/encargo original de OCF (analogo al prompt de OSF que origino esta tarea) |
| `documentacion/Nueva recomendación arquitectónica.md` | Nota de replanteo intermedio ("mi recomendacion anterior duplicaba arquitectura existente") — contexto de decision, no especificacion |

`OrganizationalContextMixin` esta cableado (verificado por grep, no por documentacion) en **14 archivos `api/viewsets.py`**: `bancos`, `clientes`, `compras`, `contabilidad`, `cotizaciones`, `dashboard`, `empresa`, `facturas`, `gastos`, `inventario`, `perfil`, `proveedores`, `proyectos`, `ventas`. **No** aparece en `empleados/api/viewsets.py` ni en `core`/`landing` (`core` es la fuente, no un consumidor; `landing` no fue tocado). Este hallazgo (`empleados` sin el Mixin pese a tener tests de scope) se deja para verificacion detallada en FASE 1/FASE 5 — no se investiga a fondo en FASE 0.

---

## 3. Estado OSF (Organizational Scope Framework)

**Afirmacion de `MEMORY.md`:** proyecto completo, F0-F16 (17/17 fases), cerrado 2026-08-08, "reencuadra/continua" OCF.
**Verificacion contra codigo real:** confirmada parcialmente — hay codigo y tests reales con sufijos de fase (`_f5`, `_f7`, `_f8`, `_f9`, `_f10`, `_f11`, `_f13`, `_f14`), pero el enforcement no es uniforme entre apps (ver tabla abajo). **No se debe asumir "terminado" solo porque `MEMORY.md` lo dice** — esta es exactamente la instruccion explicita de esta tarea.

**Documentacion OSF (toda sin trackear):**
- `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md` (1469 lineas, plan maestro)
- `documentacion/ORGANIZATIONAL_SCOPE_BASELINE.md` (**ya existe** — no confundir con este archivo nuevo `OCF_OSF_BASELINE.md`; son documentos distintos, revisar solapamiento en FASE 1)
- `documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md` (**ya existe** — se solapa directamente con el entregable pedido para FASE 5 de esta tarea; en FASE 5 se debe auditar y reutilizar/corregir este archivo, no crear uno paralelo)

**Sin ADR propio.** No existe `docs/ADR-005-*.md`. Todo OSF vive solo en los tres documentos de arriba.

**Tests con sufijo de fase encontrados** (sin trackear, `??`):

| App | Tests OSF encontrados |
|---|---|
| `core` | `test_organizational_bridges.py`, `test_organizational_context.py`, `test_organizational_dsv.py`, `test_organizational_filters.py`, `test_organizational_permissions.py`, `test_organizational_resolver.py`, `test_organizational_scope.py`, `test_organizational_selectors.py`, `test_organizational_service_layer.py` |
| `compras` | `test_organizational_context_adoption.py`, `test_scope_pilot_f5.py` |
| `cotizaciones` | `test_organizational_context_adoption.py`, `test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`, `test_scope_selectors_f7.py` |
| `empleados` | `test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`, `test_scope_selectors_f7.py`, `test_scope_write_validation_f8.py` (**sin** `test_organizational_context_adoption.py`) |
| `facturas` | `test_organizational_context_adoption.py`, `test_scope_bridges_f9.py`, `test_scope_facturas_f11.py`, `test_scope_isolation_f14.py`, `test_scope_selectors_f7.py`, `test_scope_ventas_facturas_f10.py` |
| `gastos` | `test_organizational_context_adoption.py`, `test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`, `test_scope_selectors_f7.py` |
| `proyectos` | `test_organizational_context_adoption.py`, `test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`, `test_scope_selectors_f7.py` |
| `bancos`, `clientes`, `contabilidad`, `dashboard`, `empresa`, `perfil`, `proveedores`, `ventas` | Solo `test_organizational_context_adoption.py` (sin suite de fases `_fN`) |
| `inventario`, `landing` | Carpeta `tests/` nueva vacia/minima (`??` como directorio) — **sin test de adopcion ni de scope** |

**Codigo de produccion que consume `OrganizationalScope`/`filter_by_scope*` (verificado por grep, no por test):** `compras`, `cotizaciones`, `empleados`, `facturas`, `gastos`, `inventario`, `proyectos`, `ventas` (+ `core` como fuente) = **8 apps de negocio**. Esto es menor que el numero de apps con algun test OSF (13) — hay apps con tests pero sin consumo real en `services/`/`api/` (posible test que audita ausencia, o gap real a confirmar en FASE 1/2).

**Migraciones OSF/ADR-003 nuevas, sin trackear:**
- `apps/tenant/compras/migrations/0004_add_alcance_and_sede_area_context.py`
- `apps/tenant/compras/migrations/0005_add_empresa_sede_composite_index.py`
- `apps/tenant/compras/migrations/0006_backfill_orden_compra_sede.py`
- `apps/tenant/compras/migrations/0007_harden_orden_compra_sede_not_null.py`
- `apps/tenant/perfil/migrations/0008_add_alcance_and_sede_area_context.py`

**`SedeAwareModel` (mixin de modelo):** sigue heredado **solo** por `OrdenCompra` (`apps/tenant/compras/models.py`) — verificado por grep sobre los 17 `models.py` de apps tenant. Las demas apps "integradas" en OSF filtran por `sede_id`/`area_id` como campos FK sueltos, no via el mixin.

**`HasOrganizationalScope` (permiso DRF):** sigue aplicado **solo** a `OrdenCompraViewSet` y a `apps/tenant/core/api/contexto.py` — no tiene rollout real pese a que el filtrado si se extendio a 8 apps por otra via (`filter_by_scope*`).

---

## 4. Archivos involucrados — clasificacion completa (209 archivos)

### A. OCF (Organizational Context Framework — nucleo)
`apps/tenant/core/services/organizational_context.py`, `organizational_scope.py`, `organizational_permissions.py`, `organizational_dsv.py`, `organizational_bridges.py`, `organizational_filters.py`, `organizational_service_layer.py`, `sede_context.py`, `context_processors.py`; `apps/tenant/core/api/contexto.py`; `apps/tenant/core/api/urls.py` (M); `apps/tenant/core/static/core/js/common/sede_selector.js`; `apps/tenant/core/models.py` (M, `SedeAwareModel`); `apps/tenant/core/templates/tenant/core/workspace.html` (M) y `apps/tenant/core/templates/tenant/partials/_header.html` (M) — probablemente el selector de sede en el header, sin confirmar contenido exacto en esta fase; `apps/tenant/api/mixins.py` (M); `apps/tenant/api/permissions.py` (M); `apps/tenant/perfil/models.py` (M) + `apps/tenant/perfil/migrations/0008_*.py`; `apps/tenant/core/tests/test_organizational_*.py` (9 archivos); `docs/ADR-004-organizational-context-framework-diseno.md`; `documentacion/IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md`; `documentacion/ORGANIZATIONAL CONTEXT FRAMEWORK (OCF).md`; `documentacion/Nueva recomendación arquitectónica.md`.

### B. OSF (Organizational Scope Framework — rollout)
`apps/tenant/{bancos,clientes,compras,contabilidad,cotizaciones,dashboard,empleados,empresa,facturas,gastos,inventario,perfil,proveedores,proyectos,ventas}/api/viewsets.py` y `services/{api_mixins,selectors,business_service}.py` modificados (integracion `OrganizationalContextMixin`/`filter_by_scope`); `apps/tenant/compras/migrations/0004-0007`; `apps/tenant/perfil/migrations/0008` (compartida con OCF); `apps/tenant/empresa/management/commands/backfill_sede_area.py`; `apps/tenant/empresa/services/business_service.py` (M, `asegurar_estructura_organizacional_inicial`); todos los `test_scope_*_fN.py` y `test_organizational_context_adoption.py` por app (listados en §3); `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`, `ORGANIZATIONAL_SCOPE_BASELINE.md`, `ORGANIZATIONAL_SCOPE_MATRIX.md`.

### C. Documentacion general (no especifica de OCF/OSF)
`documentacion/arquitectura_general.md` (M — ya validado/actualizado en pasada previa, ver version 3.18.0 dentro del propio archivo); `documentacion/plan_refactorizacion.md` (M); `documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md` (M); `documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md` (nuevo, EKG); `documentacion/PLAN_PRUEBASUI_PRIVADAS.md`, `REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`, `REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md` (nuevos, Auditoria Enterprise — no relacionados a OCF/OSF); `apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md` (nuevo, reemplaza `AUDITORIA_FLUJO_FACTURAS.md` eliminado — contenido no auditado en esta fase, pendiente confirmar si incorpora OCF/OSF); `AGENTS.md` (M, +33 lineas — regla "Testing Progresivo por Alcance" 2026-08-08, **no** relacionada a "alcance organizacional", es alcance de testing); `CLAUDE.md` (M, sin diferencias sustanciales verificadas en esta fase); `MEMORY.md` (M — contiene las entradas OCF/OSF ya citadas).

### D. Tests / infraestructura de testing (no atados a una sola categoria)
`pytest.ini` (nuevo); `apps/tenant/bancos/__init__.py`, `apps/tenant/compras/__init__.py`, `apps/tenant/cotizaciones/tests/__init__.py` (nuevos, arreglan paquetes Python faltantes); `apps/tenant/inventario/tests/`, `apps/tenant/landing/tests/` (directorios nuevos, minimos); `tests/tenant/compras/test_compras_plantillas.py` (M, fixtures con `sede` — ya documentado en `MEMORY.md` como fix de ADR-003); `apps/tenant/contabilidad/tests/test_retenciones_api.py` (M); `apps/tenant/compras/tests/test_multitenant_isolation_tabla_html.py` (M); `apps/tenant/bancos/tests/test_cross_tenant_isolation.py`, `test_organizational_context_adoption.py` (nuevos).

### E. Cambios NO relacionados a OCF/OSF (mezclados en el mismo working tree)
- **EKG (Enterprise Knowledge Graph, iniciativa de tooling/gobernanza separada):** `.github/workflows/ci-quality-gate.yml` (M), `Makefile` (M), `tools/ekg/*` (8 modificados + 8 nuevos, incluye `governance.py`, `impact.py`, `platform.py`, `export_html.py`).
- **Remediacion Auditoria Enterprise 2026-08-06 (ya cerrada segun `MEMORY.md`, documentos sin commitear):** `apps/tenant/core/middleware.py` (M, fix de traceback en DEBUG), partes de `apps/services/onboarding/empresa_service.py` (fix de `crear_empresa`/`onboard_tenant` — aunque esta misma funcion tambien gano una llamada a `asegurar_estructura_organizacional_inicial()`, asi que este archivo esta mezclado entre categoria E y A/B), `nginx/nginx.conf` (M, cache de estaticos), varios `apps/tenant/*/static/*/js/*` y `templates/*` (fixes de IDs duplicados/doble-submit, Fases 2-3 de la remediacion — afecta `bancos`, `contabilidad`, `empleados`, `empresa`, `gastos`, `inventario`, `proveedores`, `proyectos`).
- **Infra/DevOps sin relacion:** `apps/public/tenants/management/commands/ensure_tenant_dns.py` (M), `docker-compose.yaml` (M), `requirements.txt` (M — bump de `Pillow`/`lxml` para soporte Python 3.13, pin de `pytest-django<4.9` por incompatibilidad real documentada inline), `.claude/launch.json` (nuevo, config de dev server de Claude Code, no es codigo de la app).
- **Ruido/debris:** `nul` (archivo nuevo, 0 bytes — artefacto de una redireccion de shell de Windows mal ejecutada, ej. `comando > nul`; no tiene funcion, candidato a eliminar en una fase posterior, **no se elimina en FASE 0** por no ser estrictamente necesario para seguridad/corrupcion); `notas.txt` (M, notas personales del usuario, no se audita contenido).

---

## 5. Apps afectadas (resumen)

| App | OCF (`OrganizationalContextMixin`) | OSF (`filter_by_scope`/`OrganizationalScope` en produccion) | Test de adopcion | Migraciones OSF nuevas |
|---|:---:|:---:|:---:|:---:|
| core | fuente (no aplica) | fuente (no aplica) | 9 tests unitarios del framework | — |
| empresa | ✅ | — (usa `asegurar_estructura_organizacional_inicial`, no `filter_by_scope`) | ✅ | — |
| perfil | ✅ | — | ✅ | ✅ (`0008`) |
| facturas | ✅ | ✅ | ✅ | — |
| contabilidad | ✅ | — | ✅ | — |
| gastos | ✅ | ✅ | ✅ | — |
| inventario | ✅ | ✅ | directorio `tests/` nuevo, sin confirmar contenido | — |
| empleados | ❌ (no tiene el Mixin en `api/viewsets.py`) | ✅ | ❌ (no tiene `_adoption`, si tiene `_fN`) | — |
| cotizaciones | ✅ | ✅ | ✅ | — |
| clientes | ✅ | — | ✅ | — |
| proveedores | ✅ | — | ✅ | — |
| proyectos | ✅ | ✅ | ✅ | — |
| dashboard | ✅ | — | ✅ | — |
| bancos | ✅ | — | ✅ | — |
| compras (piloto oficial ADR-003) | ✅ | ✅ | ✅ + `test_scope_pilot_f5.py` | ✅ (`0004-0007`) |
| ventas | ✅ | ✅ | ✅ | — |
| landing | ❌ | ❌ | directorio `tests/` nuevo, vacio | — |

**Lectura de esta tabla:** ninguna app cumple hoy el ciclo completo `MODEL -> SELECTOR -> SERVICE -> PERMISSION -> VIEWSET -> API -> FRONTEND -> TESTS` salvo, parcialmente, `compras`. Esto contradice la lectura superficial de "OCF/OSF completo" y confirma la instruccion explicita de esta tarea: **no asumir terminado solo porque existen los modulos.**

---

## 6. Tests encontrados (conteo)

- Tests nuevos directamente atribuibles a OCF: **9** (`apps/tenant/core/tests/test_organizational_*.py`)
- Tests nuevos directamente atribuibles a OSF (adopcion + `_fN`): **31** (13 `test_organizational_context_adoption.py` + 18 `test_scope_*_fN.py`, contando `empresa` con `test_estructura_organizacional_inicial.py`, `test_tabla_*_view.py` como relacionados a la estructura organizacional aunque no lleven sufijo `_f`)
- Ningun test OCF/OSF se ha ejecutado todavia en esta fase — **FASE 0 es solo inventario**, la ejecucion de `pytest`/`make dj-check` queda para FASE 1 en adelante.

---

## 7. ADRs relacionados

| ADR | Archivo | Trackeado en git | Estado declarado en el archivo |
|---|---|:---:|---|
| ADR-001 | `docs/ADR-001-retention-pull-model.md` | Si (commiteado) | ACCEPTED — no relacionado a OCF/OSF |
| ADR-002 | `docs/ADR-002-public-schema-api-dual-registration.md` | Si (commiteado) | ACCEPTED — no relacionado a OCF/OSF |
| ADR-003 | `docs/ADR-003-contexto-organizacional-sede-area.md` | **No** (`??`, sin trackear) | ACCEPTED (alcance parcial) — piloto `compras` |
| ADR-004 | `docs/ADR-004-organizational-context-framework-diseno.md` | **No** (`??`, sin trackear) | PROPOSED (segun el archivo) — **contradicho por el codigo real existente** |
| — | (ninguno) | — | OSF no tiene ADR propio; ver §3 |

---

## 8. Riesgos identificados en FASE 0

1. **Nada de OCF/OSF esta commiteado.** 96 archivos nuevos y ~90 modificados relacionados (parcial o totalmente) a este trabajo existen solo en el working tree local. Cualquier `git checkout -- .`, `git clean -fd`, o perdida del entorno local borraria el trabajo completo sin posibilidad de recuperacion desde git.
2. **`ADR-004` desactualizado respecto al codigo real** — riesgo de que un agente o desarrollador futuro lea "PROPOSED" y asuma que no hay nada implementado, o al reves, que asuma que esta 100% aceptado sin revisar el detalle.
3. **Inconsistencia `empleados`:** tiene tests de scope (`_f7`, `_f8`, `_f13`, `_f14`) y usa `filter_by_scope` en produccion, pero **no** tiene `OrganizationalContextMixin` en sus ViewSets ni el test de adopcion estandar — sugiere una integracion por una via distinta (posiblemente `views.py` con vistas basadas en funcion en vez de DRF ViewSets) que debe verificarse explicitamente en FASE 1/5, no asumirse equivalente.
4. **Solapamiento de entregables:** `documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md` y `ORGANIZATIONAL_SCOPE_BASELINE.md` **ya existen** sin trackear y se solapan con los entregables pedidos en FASE 5 de este mismo plan. No auditarlos antes de FASE 5 arriesga crear contenido duplicado o contradictorio.
5. **`HasOrganizationalScope` sin rollout real** (solo `compras`) pese a que el filtrado por otra via (`filter_by_scope`) si llego a 8 apps — dos mecanismos de enforcement con cobertura distinta y ninguno de los dos universal. Riesgo de seguridad si se asume que "hay scope enforcement" en una app que solo tiene filtrado de lectura pero no proteccion de escritura via permiso DRF.
6. **Working tree mezcla 5 iniciativas no relacionadas** (OCF, OSF, EKG, Remediacion Auditoria Enterprise, fixes de infra/dependencias) en los mismos 209 archivos sin commitear. Un commit apresurado que agrupe todo bajo "OCF/OSF" mezclaria historial de cosas no relacionadas — reforzar en FASE 11 la separacion por responsabilidad ya indicada en el plan.
7. **Archivo `nul`** (0 bytes, artefacto de Windows) y **rama `feat/onboarding-cookie`** con nombre que ya no refleja su contenido — riesgos menores de higiene, no bloqueantes.
8. **`main` muy atrasada** (2026-03-27) respecto al trabajo real del proyecto — cualquier intento futuro de abrir un PR contra `main` implicaria un diff de 95 commits + 209 archivos, no solo el trabajo de OCF/OSF.

---

## 9. Cambios no relacionados (resumen ejecutivo, ver detalle en §4.E)

EKG (tooling de grafo de conocimiento/gobernanza automatica), Remediacion completa de la Auditoria Enterprise 2026-08-06 (seguridad, UI, rendimiento, onboarding), y varios fixes de infraestructura/dependencias — **todos documentados y cerrados segun `MEMORY.md`, pero tampoco commiteados**. No se tocan en esta tarea; se listan aqui solo para que FASE 11 (Consolidacion Git) no los mezcle con los commits de OCF/OSF.

---

## Cierre de FASE 0

Ningun archivo de codigo funcional fue modificado en esta fase. Se crearon dos documentos nuevos:
- `documentacion/OCF_OSF_BASELINE.md` (este archivo)
- `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md` (tablero de estado de fases)

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
