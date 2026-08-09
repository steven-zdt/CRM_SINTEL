# Validación del Piloto Compras (ADR-003/OSF F5) — FASE 6

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED (auditoría + matriz + verificación de tests existentes) — sin escribir tests nuevos, ver §5
**Metodología:** lectura completa del ciclo `OrdenCompra`/`PlantillaOrdenCompra`/`ItemOrdenCompra` (Selectors, Services, ViewSet, Serializer, Permissions, Templates, HTMX, JS), más ejecución real de la suite de tests de `compras` en Docker.

---

## 1. Auditoría del ciclo completo — `OrdenCompra`

| Capa | Archivo | Estado organizacional |
|---|---|---|
| Model | `apps/tenant/compras/models.py` | `OrdenCompra(SedeAwareModel)` — `sede` `NOT NULL` (migración 0007), `area` opcional (`SET_NULL`). Único adoptante de `SedeAwareModel` en las 17 apps. |
| Selector | `apps/tenant/compras/services/selectors.py:96-137` | `OrdenCompraSelector.get_list(empresa_id, sede_ids=None, area_ids=None)` usa `filter_by_scope()` (estricto, no null-safe — correcto porque `sede` es `NOT NULL`). `select_related('sede', 'area')` + traversals `_SEDE_TRAVERSALS`/`_AREA_TRAVERSALS` para exponer el nombre en el listado. |
| ServiceMixin | `apps/tenant/compras/services/api_mixins.py:41-134` | `get_qs_list()` resuelve `OrganizationalScope.resolve(self.request)` y pasa el **conjunto completo** `sede_ids`/`area_ids` (no una sola sede activa) — degrada a "sin restricción" si `OrganizationalScopeError` (mismo criterio que el resto de OSF). `service_crear_orden_compra()` resuelve `sede` vía `self._get_sede()` (activa) y la pasa explícita al Business Service. |
| BusinessService | `apps/tenant/compras/services/business_service.py:137-172,296-310` | DSV real: `sede is None` → 422; `sede.empresa_id != empresa.id` → 422 (anti-IDOR); `area` debe pertenecer a la empresa Y a la MISMA `sede` de la orden (`area.sede_id != sede.id` → 400 `area_invalida`) — verificado tanto en creación como en actualización. |
| CRUDService | `apps/tenant/compras/services/crud_service.py` | Persiste `sede`/`area` ya resueltos y validados por el Business Service — no re-deriva ni re-valida (capa de persistencia pura, consistente con FSD). |
| ViewSet | `apps/tenant/compras/api/viewsets.py:62-67` | `get_permissions()` → `[IsTenantMember(), IsTenantAdminOrReadOnly(), HasOrganizationalScope()]` — único ViewSet de las 17 apps con `HasOrganizationalScope` real. |
| Serializer | `apps/tenant/compras/api/serializers.py` | Expone `sede`/`area` como campos escribibles (corregido en F5 — antes `area` se descartaba silenciosamente); expone `sede_nombre` en el listado (agregado en F5 para distinguir filas de distintas sedes cuando alcance=EMPRESA las mezcla). |
| Template/HTMX | `apps/tenant/compras/templates/tenant/compras/offcanvas_detalle_compras.html:119` | `{{ instance.sede.nombre }}` — la sede se muestra en el detalle real que ve el usuario. |
| Vista HTML (no-DRF) | `apps/tenant/compras/views.py` (`OrdenCompraTableView`) | Filtra la grilla HTMX real por el mismo `OrganizationalScope` — corregido en F5 tras encontrar que la grilla HTML (la que el usuario ve, distinta de la API DRF) no aplicaba ningún filtro de sede antes de esta fase. |

**`PlantillaOrdenCompra`** (la plantilla de numeración, no el registro transaccional): no hereda `SedeAwareModel`, no tiene `sede`/`area` — es correcto por diseño (una plantilla de numeración de documentos es de toda la empresa, no de una sede). Su `ViewSet` usa `[IsTenantMember(), IsTenantAdminOrReadOnly()]` sin `HasOrganizationalScope` — consistente, no un gap.

---

## 2. Matriz de pruebas: ROL × ALCANCE

Construida contra el comportamiento real de `HasOrganizationalScope`/`OrganizationalScope`
(`OSF_TECHNICAL_AUDIT.md` §5-6) — `rol` y `alcance` son ortogonales (§1 de ese documento), así
que la matriz cruza los 3 roles (`ADMIN`/`OPERADOR`/`VISOR`) con los 3 alcances
(`EMPRESA`/`SEDE`/`AREA`). Cada celda indica: **comportamiento esperado según el código** (auditado, no supuesto) y **si existe un test real que lo demuestre** en la suite de `compras`.

| | **EMPRESA** | **SEDE** | **AREA** |
|---|---|---|---|
| **ADMIN** | Ve/opera todo. Puede crear/editar/eliminar cualquier orden. | Ve/opera solo `sedes_asignadas`. Puede administrar (rol) pero solo dentro de su alcance. | Ve/opera solo `areas_asignadas` (de sedes en `sedes_asignadas`). |
| | ✅ Testeado: `test_api_list_con_alcance_empresa_sigue_viendo_todo`, `test_crear_orden_con_area_de_la_misma_sede_activa_funciona` (ambos con rol=ADMIN) | 🟡 Testeado solo el **listado** (`test_tabla_htmx_con_alcance_sede_ve_todas_las_sedes_asignadas` usa rol=OPERADOR, no ADMIN — el caso ADMIN+SEDE no tiene test propio, aunque el código no distingue rol para el filtrado de listas) | 🔴 Sin test — ningún test combina rol=ADMIN con alcance=AREA explícitamente (los tests de AREA usan rol=OPERADOR) |
| **OPERADOR** | Ve/opera todo (rol no restringe lectura; escritura permitida por `IsTenantAdminOrReadOnly`... **ver riesgo §4**). | Ve/opera solo `sedes_asignadas`. | Ve/opera solo `areas_asignadas`. |
| | 🔴 Sin test — todos los tests de alcance=EMPRESA usan rol=ADMIN | ✅ Testeado: `test_api_list_con_alcance_sede_ve_todas_las_sedes_asignadas_no_solo_una`, `test_tabla_htmx_...` (listado) | ✅ Testeado: `test_api_list_con_alcance_area_filtra_por_area_no_solo_por_sede` (listado) |
| **VISOR** | Solo lectura de todo. | Solo lectura de `sedes_asignadas`. | Solo lectura de `areas_asignadas`. |
| | 🔴 **Sin ningún test** | 🔴 **Sin ningún test** | 🔴 **Sin ningún test** |

**Aislamiento a nivel de objeto individual (`HasOrganizationalScope.has_object_permission()` — retrieve/update/delete de una `OrdenCompra` específica por UUID, el mecanismo anti-IDOR real):** confirmado por `grep -rln "HasOrganizationalScope" apps/tenant/compras/tests/` → **sin resultados**. Ninguna celda de la matriz de arriba, para ningún rol/alcance, tiene un test que confirme que un perfil `alcance=SEDE` recibe 403/404 al intentar `GET`/`PATCH`/`DELETE` una `OrdenCompra` de una sede fuera de `sedes_asignadas` por UUID directo. **Este es el gap de cobertura más grave del piloto** — ya señalado en FASE 2 (`OSF_TECHNICAL_AUDIT.md` §4/§8) y confirmado aquí específicamente contra la suite de `compras`.

**`VISOR` no aparece ni una sola vez en ningún test de `compras`** (`grep -rn "VISOR" apps/tenant/compras/tests/*.py` → sin resultados) — la fila completa de VISOR en la matriz es comportamiento inferido del código (`HasOrganizationalScope`/`OrganizationalScope` no leen `rol` en absoluto, solo `alcance` — un VISOR se comporta igual que un ADMIN/OPERADOR en cuanto a qué sedes/áreas puede *listar*; lo que debería impedirle escribir es `IsTenantAdminOrReadOnly`/`HasTenantRole`, no `HasOrganizationalScope`), no verificado por ningún test end-to-end.

---

## 3. Aislamiento verificado — resumen de lo que SÍ está probado

De las 9 combinaciones rol×alcance, la suite real (`test_scope_pilot_f5.py`, 7 tests) cubre con
certeza:
- **Listado** filtra correctamente por conjunto completo de sedes (no una sola activa) para alcance SEDE — 2 sedes asignadas, ve ambas.
- **Listado** filtra correctamente por área (no solo por sede) para alcance AREA.
- **Listado** con alcance EMPRESA ve todo, incluidas 3 sedes distintas mezcladas, con `sede_nombre` distinguiéndolas.
- **Grilla HTMX real** (no solo la API DRF) aplica el mismo filtro — corregido tras encontrar que antes no filtraba en absoluto.
- **Creación** con `area` de la sede correcta funciona.
- **Creación** con `area` de otra sede falla con `400 area_invalida` (anti-inconsistencia).
- **Actualización** con `area` de otra sede falla igual, y no persiste el cambio inválido (`refresh_from_db` confirma `area_id` sigue `None`).

Ninguno de estos 7 tests varía `rol` de forma sistemática (usan ADMIN u OPERADOR según lo que sea conveniente para el escenario, no como variable de prueba) ni ejerce el permiso de objeto individual (`HasOrganizationalScope.has_object_permission()`).

---

## 4. Riesgos identificados en FASE 6 (nuevos, adicionales a FASE 0-5)

1. **Gap crítico confirmado: `HasOrganizationalScope.has_object_permission()` sin ningún test en `compras`**, pese a ser la pieza de enforcement real del piloto oficial. Recomendación para una fase de implementación futura: agregar al menos 2 tests — (a) perfil `alcance=SEDE` sin la sede de la orden → `GET`/`PATCH` por UUID directo devuelve 403/404; (b) mismo perfil con la sede correcta → permite. No se escriben en esta fase (FASE 6 es validación/auditoría, ver §5).
2. **`rol` nunca se varía sistemáticamente en los tests existentes** — no hay evidencia automatizada de que `VISOR` efectivamente no pueda escribir (aunque el código lo sugiere vía `IsTenantAdminOrReadOnly`, mecanismo preexistente y no específico de este piloto).
3. **Interacción `rol=VISOR` + `HasOrganizationalScope` no verificada**: `HasOrganizationalScope.has_permission()` siempre retorna `True` (el filtrado de listas ocurre en el selector) — para un VISOR, ¿el 403 de escritura lo da `IsTenantAdminOrReadOnly` antes de que `HasOrganizationalScope` evalúe el objeto? El orden de la lista `[IsTenantMember(), IsTenantAdminOrReadOnly(), HasOrganizationalScope()]` en `get_permissions()` sugiere que sí (DRF evalúa en orden y corta en el primer `False`), pero no está confirmado con un test.
4. Confirma (no nuevo, ya en FASE 5): ningún test de `compras` ejercita el caso "objeto sin sede" (`sede_id=None`) porque `OrdenCompra.sede` es `NOT NULL` — la asimetría NULL de `OSF_TECHNICAL_AUDIT.md` §4 simplemente no puede manifestarse aquí, confirmando que es un riesgo específico de la Fase 10 (rollout a otras apps), no del piloto en sí.

---

## 5. Por qué no se escribieron tests nuevos en esta fase

El prompt maestro pide "crear una matriz de pruebas... y verificar aislamiento" — se interpretó
como construir la matriz (documento, arriba) y verificar mediante ejecución real de la suite
existente (§6), no como autorización implícita para escribir producción de tests nuevos (eso es
un paso de `IMPLEMENTACIÓN`, con su propio ciclo de auditoría→cambios→tests→documentación que el
propio prompt maestro exige, y requeriría decidir detalles de implementación — ej. fixtures,
nombres de sede/área de prueba — que no corresponde asumir unilateralmente). El gap del punto 1
de §4 queda documentado y priorizado explícitamente para que el usuario autorice esa
implementación como su propio paso, si la quiere antes de continuar el rollout.

---

## 6. Ejecución real de tests (pytest, Docker)

Comando: `docker compose exec web python -m pytest apps/tenant/compras/tests/test_scope_pilot_f5.py apps/tenant/compras/tests/test_organizational_context_adoption.py apps/tenant/compras/tests/test_multitenant_isolation_tabla_html.py --reuse-db -q`.

**Resultado confirmado (2026-08-09): `1 failed, 8 passed, 1 warning in 563.84s (0:09:23)`.**

El fallo es `test_multitenant_isolation_compras_tabla_html`
(`test_multitenant_isolation_tabla_html.py`) — **preexistente y ya diagnosticado antes de esta
consolidación**, no causado por nada de FASE 0-7. `MEMORY.md` (entrada OSF F5, 2026-08-07/08) ya
documentó este mismo fallo: un `force_login()` que no persiste la sesión en el request siguiente,
confirmado como bug ajeno al trabajo de scope corriendo el equivalente exacto en `gastos`
(`test_multitenant_isolation.py`), que falla idéntico sin haber sido tocado. No se investiga de
nuevo aquí (ya diagnosticado) ni se corrige (fuera del alcance de "validar el piloto" — es un bug
de infraestructura de test, no del código de `compras`). Los 8 tests restantes de la suite del
piloto (incluidos los 7 de `test_scope_pilot_f5.py` citados en §3 de este documento) **pasan**.

**Actualización post-FASE 7 (2026-08-09):** los 2 bugs reales encontrados por la suite de
aislamiento de FASE 7 (bypass de `HasOrganizationalScope` en las acciones HTMX de offcanvas;
`PermissionDenied` convertido en `500` en vez de `403` por `handle_service_error()`) fueron
corregidos con autorización explícita del usuario — ver
`documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md`. Re-ejecución completa de la suite del piloto
(`test_organizational_isolation_empresa_a.py` + `test_scope_pilot_f5.py` +
`test_organizational_context_adoption.py`) tras el fix:

**`20 passed, 1 warning in 503.96s (0:08:23)`.** Las 12 pruebas de aislamiento (incluidas las 3
que antes documentaban los 2 bugs) más las 7 del piloto F5 más la de paridad de contexto — todas
pasan con los códigos de estado correctos. El piloto `compras` queda validado end-to-end: los 9
tests restantes preexistentes de `test_multitenant_isolation_tabla_html.py` no se re-corrieron en
esta pasada (su único test falla por el bug de infraestructura ya diagnosticado, ajeno a esta
consolidación, ver arriba).

---

## Cierre de FASE 6

Ningún archivo de código funcional modificado. Documento creado: `documentacion/COMPRAS_PILOT_VALIDATION.md` (este archivo).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
