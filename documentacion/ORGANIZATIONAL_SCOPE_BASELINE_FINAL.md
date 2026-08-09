# Baseline Organizacional Final — FASE 12

**Fecha:** 2026-08-09 (actualizado tras la ejecución de FASE 11)
**Estado de la fase:** 🟢 ORGANIZATIONAL BASELINE — Código+Tests+ADR+Documentación+Git alineados. Los 5 commits del plan de FASE 11 se ejecutaron con autorización explícita del usuario (`git log --oneline -5`: `0295932` OCF core, `120d17e` piloto compras, `c63b35e` scope en 6 apps, `1d19d8f` tests, `34fc020` ADRs/documentación) — pre-commit hooks (SSoT Guard) pasaron en los 5, y `git status` confirma que solo quedan sin commitear los ~75 archivos de la categoría E (EKG, Remediación Auditoría Enterprise, infraestructura — deliberadamente fuera de alcance, ver `FASE11_CONSOLIDACION_GIT.md` §3). El Knowledge Graph (FASE 13, no es precondición de esta fase per el prompt maestro) sigue pendiente — ver cierre de sesión al final de este documento.

---

## 1. Estado de OCF (Organizational Context Framework)

**Código:** completo y probado. `apps/tenant/core/services/organizational_context.py` (+ 6 módulos hermanos), `OrganizationalContextMixin` heredado en 14 ViewSets.
**Adopción real:** baja. `OrganizationalContext.resolve()` solo se invoca de verdad en `ContextoOrganizacionalView` (`GET /api/v1/core/contexto/`, sin consumidor JS todavía) y directamente en `ventas` (defaulteo de `sede_id`, sin Mixin). El Mixin en sí está inerte en las otras 13 apps.
**Cadena 100% funcional en producción:** selector de "sede activa" (header + sesión + `POST /api/v1/core/contexto/sede/`).
**Tests:** 9 suites, 53/53 pasan (confirmado por ejecución real, FASE 1).

## 2. Estado de OSF (Organizational Scope Framework)

**Código:** completo y probado para el contrato central (`OrganizationalScope`, `filter_by_scope*`). **Adopción real:** `OrganizationalScope.resolve()` en uso directo en 8 apps de negocio (compras + las 6 de F7 + core). `OrganizationalScopeMixin` sin ninguna herencia — código muerto. `HasOrganizationalScope` (el único enforcement de objeto real) sigue limitado a `compras`.
**Tests:** suite de `compras` completa (piloto): **20/20 pasan** tras corregir los 2 bugs de FASE 7. Suites `test_scope_*_fN.py` de las otras 5 apps (facturas, cotizaciones, gastos, inventario, proyectos, empleados) **no se re-ejecutaron en esta consolidación** — quedan pendientes de una corrida de verificación si se necesita confianza total en ellas antes de darlas por definitivas.

## 3. Estado de los ADR

| ADR | Estado final | Nota |
|---|---|---|
| ADR-003 | ACCEPTED (alcance parcial) | Sin cambios de estado en esta consolidación — la interpretación de "alcance parcial" se refinó en FASE 2/3 (distinción `HasOrganizationalScope` compras-only vs. filtrado OSF en 6 apps) |
| ADR-004 | ACCEPTED (parcialmente implementado) | Actualizado en FASE 4 con Adenda 2026-08-09 — documenta 2 divergencias reales de diseño (`OrganizationalScope` independiente de `OrganizationalContext`; `OrganizationalSelector` nunca construido como clase) |
| ADR-005 | ACCEPTED (parcialmente implementado) | Nuevo, creado en FASE 4 — formaliza la independencia Scope/Context y el rollout sin migración de esquema (`filter_by_scope_null_safe`) |

## 4. Apps — estado final consolidado (FASE 5 + FASE 10)

| Estado | Apps |
|---|---|
| 🟢 Completo | `compras` (piloto, 20/20 tests) |
| 🟢 Completo por diseño (sin campo necesario) | `ventas` |
| 🟡 Parcial (lectura completa, enforcement de objeto diferido por asimetría NULL) | `facturas`, `cotizaciones`, `gastos`, `inventario`, `proyectos`, `empleados` |
| ⚪ No aplica (decisión de negocio/diseño) | `clientes`, `dashboard` |
| 🔴 Sin empezar, backlog no urgente (sin infraestructura especulativa) | `proveedores`, `bancos`, `contabilidad` |
| ⚪ Fuente/infraestructura, no consumidor | `core`, `empresa`, `perfil`, `landing` |

**17/17 apps tenant tienen un veredicto explícito y justificado — ninguna quedó "pendiente" sin razón.**

## 5. Cobertura de tests — resumen ejecutado realmente

| Suite | Resultado real |
|---|---|
| `apps/tenant/core/tests/test_organizational_*.py` (9 archivos) | **53 passed** (FASE 1) |
| `apps/tenant/compras/tests/` (piloto completo, incl. aislamiento F7) | **20 passed**, 1 fallo preexistente no relacionado (`test_multitenant_isolation_tabla_html.py`, bug de `force_login()` ya diagnosticado en `MEMORY.md`) |
| `test_scope_*_fN.py` de facturas/cotizaciones/gastos/inventario/proyectos/empleados | **No re-ejecutadas en esta consolidación** — su contenido se auditó por lectura (FASE 8/`ORGANIZATIONAL_SCOPE_MATRIX.md`), no por ejecución fresca |
| `test_organizational_context_adoption.py` (13 apps) | No re-ejecutadas en esta consolidación |

## 6. Riesgos abiertos (consolidado de FASE 0-10, ninguno resuelto en silencio)

1. Triplicación de `empresa_id` (mixins.py / OrganizationalContext / OrganizationalScope) — solo 1 de 3 pares con test de paridad.
2. Asimetría NULL entre `filter_by_scope_null_safe()` (permite) y `HasOrganizationalScope` (deniega) — bloquea extender el permiso de objeto a las 6 apps de F7 sin antes resolverla.
3. `OrganizationalScopeMixin`/`OrganizationalPermission`/DSV generalizado/Bridges adaptados — código real sin consumidor de producción (infraestructura en espera, no un bug, pero tampoco "terminado" en el sentido de "en uso").
4. `HasOrganizationalScope.permits_sede()` reimplementado de forma independiente en `apps/tenant/api/permissions.py` en vez de delegar en `OrganizationalScope` — lógica de autorización duplicada (FASE 3).
5. `test_scope_*_fN.py` de las 6 apps de F7 no re-verificadas por ejecución en esta consolidación (punto 5 arriba).
6. Todo el trabajo de FASE 0-11 sigue **sin commitear** — ver §7.

## 7. Deuda técnica y trabajo NO hecho, explícito

- `proveedores`/`bancos`/`contabilidad`: sin scope organizacional, backlog documentado con punto de partida concreto para cada una (`FASE10_ROLLOUT_CONTROLADO.md` §6-8).
- `FacturaInterAppAPI` sigue sin filtro `empresa_id` (riesgo D-4/R-2, decisión de producto pendiente desde ADR-004, no tocada).
- `Serializer` de `inventario` — no se confirmó si valida `sede_esta_en_alcance()` en escritura (gap de verificación, no necesariamente un bug).
- FASE 13 (Knowledge Graph organizacional) y FASE 14 (Gobernanza automática) — **no ejecutadas todavía**, ver documento de cierre de esa decisión más abajo en este mismo turno.
- **Git:** 5 commits preparados y validados (`manage.py check` limpio, `makemigrations --check` limpio, tests pasando) en `FASE11_CONSOLIDACION_GIT.md`, pendientes de tu autorización explícita para ejecutar.

## 8. Trazabilidad Código↔Test↔ADR↔Documentación↔Matriz↔Git↔Knowledge Graph

| Relación | Estado |
|---|---|
| Código ↔ Test | ✅ Verificable — 53+20 tests reales ejecutados, resultado citado en cada documento |
| Código ↔ ADR | ✅ Verificable — ADR-004/005 citan archivo:línea real |
| Código ↔ Documentación | ✅ Verificable — cada auditoría (`OCF_TECHNICAL_AUDIT.md`, `OSF_TECHNICAL_AUDIT.md`, `FACTURAS_AUDIT.md`, etc.) cita archivo:línea |
| Código ↔ Matriz | ✅ Verificable — `ORGANIZATIONAL_SCOPE_MATRIX.md` §4 y `FASE10_ROLLOUT_CONTROLADO.md` |
| Código ↔ Git | ✅ **Verificable** — 5 commits reales, `git log`/`git show` citables, pre-commit hooks pasados |
| Código ↔ Knowledge Graph | 🔴 **No verificable** — FASE 13 no ejecutada, ver nota de cierre abajo |

**Las 5 dimensiones que el prompt maestro exige como precondición de esta fase (Código+Tests+ADR+Documentación+Git) están alineadas y verificadas — se declara 🟢 ORGANIZATIONAL BASELINE.** El Knowledge Graph (columna extra de esta tabla, no parte de la precondición literal de FASE 12) queda como el trabajo de FASE 13, evaluado por separado abajo.

---

## 9. Nota de cierre de sesión — FASE 13/14

FASE 13 (Knowledge Graph organizacional) y FASE 14 (Gobernanza automática) extienden `tools/ekg/`
— una herramienta que **tiene su propia línea de trabajo separada y sin commitear** (8 módulos
modificados + 8 nuevos, categoría E de `OCF_OSF_BASELINE.md`, deliberadamente no tocada en toda
esta consolidación para no mezclar responsabilidades). Hacerlo bien requeriría: diseñar qué
significa un nodo "Scope"/"Context" en el grafo (decisión de modelado, no solo extracción),
extender el extractor Python para detectar consumo real de `OrganizationalContext`/
`OrganizationalScope` (patrón similar a los 5 bugs de resolución cross-app que la propia auditoría
EKG de 2026-08-07 encontró y corrigió), y nuevas reglas de gobernanza en `governance.py`. Es un
proyecto de tamaño comparable a las FASE 0-12 ya completadas hoy, no un paso final rápido — y
forzarlo superficialmente ahora violaría el mismo principio de "no infraestructura especulativa"
sostenido en toda esta sesión (ver `organizational_bridges.py`/`organizational_service_layer.py`,
que deliberadamente no construyeron adaptadores sin consumidor real). Se recomienda como una
sesión dedicada propia, no como cierre apurado de esta. **No se marca 🟢 ni se fabrica una
version reducida — queda 🔴 BLOCKED por decisión explícita, con esta justificación, no por
omisión.**
