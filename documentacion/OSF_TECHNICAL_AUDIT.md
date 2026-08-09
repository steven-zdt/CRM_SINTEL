# Auditoria de Organizational Scope (OSF) — FASE 2

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED (auditoria) — cero codigo modificado
**Metodologia:** lectura completa de `organizational_scope.py`, `organizational_filters.py`, `TenantProfile` (`apps/tenant/perfil/models.py`), `HasOrganizationalScope`/`OrganizationalPermission` (`apps/tenant/api/permissions.py`), y de las suites de test reales que demuestran (no solo documentan) el comportamiento. Todo lo afirmado abajo esta respaldado por un test que pasa (una vez confirmada la ejecucion, ver §7) o por lectura directa de codigo — nada se asume.

---

## 1. Que significa cada valor de `alcance`

**Fuente:** `apps/tenant/perfil/models.py:16-29` (`AlcanceOrganizacional`), campo `TenantProfile.alcance` (linea 166-173, default `EMPRESA`, `db_index=True`).

| Valor | Significado textual (del propio modelo) | Efecto real verificado |
|---|---|---|
| `EMPRESA` | "Empresa completa" | Sin restriccion de sede/area — el perfil ve/opera sobre TODA la empresa. Es el default de todo `TenantProfile` nuevo. |
| `SEDE` | "Sede(s) asignada(s)" | Restringido al conjunto de `perfil.sedes_asignadas` (M2M a `empresa.Sede`) — **el conjunto completo, no una sola sede "activa"**. |
| `AREA` | "Area(s) asignada(s)" | Restringido al conjunto de `perfil.areas_asignadas` (M2M a `empresa.Area`) — mismo criterio que SEDE. |

`alcance` es **ortogonal** a `rol` (`RolTenant`: `ADMIN`/`OPERADOR`/`VISOR`) — confirmado en el docstring del propio enum (linea 19-21): "rol dice QUE puede hacer, alcance dice DONDE puede hacerlo". No hay combinacion prohibida entre ellos a nivel de modelo (un `VISOR` puede tener `alcance=SEDE`, un `ADMIN` puede tener `alcance=AREA`, etc.).

**"ADMIN GLOBAL" no es un valor de `alcance`** — confirmado explicitamente en el docstring del enum (linea 23-25): es el staff/superuser de Django del esquema publico, fuera de `TenantProfile` por completo. Esto es consistente con `organizational_permissions.py` (`ADMIN_GLOBAL` se resuelve desde `is_staff`, no desde `alcance`, ver auditoria FASE 1 §3).

---

## 2. Como se resuelve el alcance y los conjuntos permitidos — `OrganizationalScope.resolve()`

**Fuente:** `apps/tenant/core/services/organizational_scope.py:131-181`.

Algoritmo exacto (verificado linea por linea):
1. Requiere `request.user.is_authenticated` — si no, `OrganizationalScopeError` (demostrado por `test_resolve_raises_for_anonymous_user`).
2. Lee `perfil = request.user.tenant_profile`. Si no hay perfil y `settings.DEBUG=True`, cae al mismo fallback "primera Empresa del tenant" que `SintelDSVMixin.get_empresa_id()` (duplicado a proposito, ver auditoria FASE 1 §1/§2 — riesgo de paridad ya documentado ahi, no se repite aqui).
3. `alcance = perfil.alcance or "EMPRESA"` — si el perfil no tiene `alcance` seteado (no deberia pasar, el campo tiene `default='EMPRESA'` a nivel de BD), tambien cae a `EMPRESA`.
4. Si `alcance in ("SEDE", "AREA")`: `sede_ids = frozenset(perfil.sedes_asignadas.values_list("id", flat=True))` — **siempre** se calcula para SEDE y AREA (un perfil AREA tambien tiene `sede_ids` resuelto, no solo `area_ids`).
5. Si `alcance == "AREA"`: ademas `area_ids = frozenset(perfil.areas_asignadas.values_list("id", flat=True))`.
6. Si `alcance == "EMPRESA"`: `sede_ids = None` y `area_ids = None` (nunca se calculan, ni siquiera como conjunto vacio).

---

## 3. Que sucede exactamente con cada alcance — demostrado por test, no supuesto

### 3.1 `alcance = EMPRESA`

**Demostrado por:** `test_alcance_empresa_no_restringe` (`test_organizational_scope.py:46-59`).

- `scope.sede_ids is None`, `scope.area_ids is None`.
- `scope.permits_sede(sede_a.id) == True` y **`scope.permits_sede(None) == True`** — un perfil EMPRESA tambien puede tocar objetos sin sede asignada.
- `OrganizationalScope.filter(Model)` (`organizational_scope.py:105-129`) no agrega ningun `.filter(sede_id__in=...)` cuando `sede_ids is None` — el queryset queda filtrado solo por `empresa_id`, exactamente el comportamiento pre-OSF.

### 3.2 `alcance = SEDE`, con sedes asignadas

**Demostrado por:** `test_alcance_sede_resuelve_conjunto_completo_no_una_sola_activa` (linea 61-72) y `test_context_active_sede_vs_scope_full_set_es_la_distincion_real` (linea 85-125, con objetos `OrdenCompra` reales).

- `scope.sede_ids == frozenset({sede_a.id, sede_b.id})` para un perfil con ambas asignadas — el **conjunto completo**, no la sede activa de sesion.
- Prueba concreta con datos reales: un perfil con `sedes_asignadas=[A,B]` y `sede_activa` en sesion = A. `OrganizationalContext.filter(OrdenCompra)` devuelve **solo** la orden de la sede A (la activa). `OrganizationalScope.filter(OrdenCompra)` devuelve **ambas** (A y B) — la asimetria que justifica que los dos conceptos existan por separado, verificada con codigo real, no solo argumentada en un docstring.

### 3.3 `alcance = SEDE`, **sin** ninguna sede asignada ("que sucede si no existe sede")

**Demostrado por:** `test_alcance_sede_sin_asignaciones_restringe_a_nada_no_a_todo` (linea 74-83).

- `scope.sede_ids == frozenset()` (conjunto vacio, **no** `None`).
- `scope.permits_sede(sede_a.id) == False`.
- Distincion critica de diseno (documentada en el docstring de la clase, `organizational_scope.py:66-69`, y verificada aqui): `None` = "sin restriccion" (EMPRESA), `frozenset()` = "restringe a nada" (SEDE/AREA sin asignaciones). Un perfil `alcance=SEDE` recien creado sin `sedes_asignadas` **no ve ningun dato** hasta que se le asigne al menos una sede — fail-closed correcto, no fail-open.

### 3.4 `alcance = AREA`

**Demostrado por:** `test_area_esta_en_alcance_helper_respeta_asignaciones` (linea 158-175, via el helper `area_esta_en_alcance`, misma logica que `OrganizationalScope.resolve()` para `area_ids`).

- Mismo patron que SEDE: conjunto completo de `areas_asignadas`, `frozenset()` si no hay ninguna asignada (mismo fail-closed, no verificado con un test dedicado a `OrganizationalScope.resolve()` directamente para AREA sin asignaciones — el test existente prueba el helper `area_esta_en_alcance`, no `scope.area_ids` vacio explicitamente; **gap menor de cobertura**, el comportamiento es el mismo por lectura de codigo pero no tiene un test que lo fije igual que `test_alcance_sede_sin_asignaciones_restringe_a_nada_no_a_todo` lo hace para SEDE).
- Un perfil `alcance=AREA` **tambien** tiene `sede_ids` resuelto (paso 4 del algoritmo, §2) ademas de `area_ids` — es decir, AREA restringe por area Y por la sede a la que esas areas pertenecen implicitamente via `sedes_asignadas` (que debe declararse por separado, no se infiere de las areas — ver riesgo §8).

---

## 4. Que sucede con datos historicos (`sede`/`area` en NULL) — la pieza mas delicada de la auditoria

**Fuente:** `organizational_filters.py:59-90` (`filter_by_scope_null_safe`), verificado empiricamente por el propio comentario del modulo: "100% de los registros reales de Factura/Cotizacion/DocumentoSoporte/MovimientoInventario/Proyecto/Empleado tienen sede=NULL hoy".

**A nivel de listado (Selectors, `filter_by_scope_null_safe`):** un registro con `sede_id IS NULL` es **visible** para cualquier alcance (EMPRESA/SEDE/AREA) — decision explicita para no ocultar el 100% de los datos existentes a un perfil SEDE/AREA. Demostrado por `test_filter_by_scope_null_safe_deja_visible_lo_no_clasificado` (`test_organizational_filters.py:71-87`).

**A nivel de objeto individual (`HasOrganizationalScope.has_object_permission()`, `apps/tenant/api/permissions.py:182-195`):** comportamiento **contrario** — `sede_id is not None and perfil.sedes_asignadas.filter(id=sede_id).exists()`. Si `obj.sede_id` es `None`, la expresion es `False` — **deniega** el acceso a un perfil `alcance=SEDE` para CUALQUIER objeto sin sede, exactamente lo opuesto de `filter_by_scope_null_safe()`.

**Esto es una asimetria real, no teorica, entre el filtrado de listas y el permiso de objeto individual — el hallazgo mas importante de FASE 2:**

- **Hoy no es un bug en produccion** porque `HasOrganizationalScope` solo esta aplicado a `OrdenCompraViewSet` (`apps/tenant/compras/api/viewsets.py:67`), y `OrdenCompra.sede` es `NOT NULL` desde la migracion `0007_harden_orden_compra_sede_not_null.py` — nunca hay un `OrdenCompra` con `sede_id=None` que pueda disparar la denegacion.
- **Es una mina para FASE 10 (Rollout):** si `HasOrganizationalScope` se agrega tal cual a `FacturaViewSet`/`GastoViewSet`/etc. (los 6+ apps donde `filter_by_scope_null_safe` ya deja visibles los registros con `sede=NULL`), un perfil `alcance=SEDE` que hoy VE una Factura en el listado (porque tiene `sede=NULL`) recibiria un **403 al intentar abrirla/editarla individualmente** — una regresion de UX grave y silenciosa si no se corrige `HasOrganizationalScope` (o se crea una variante NULL-safe de la verificacion de objeto) antes de aplicarla a esas apps. Documentado aqui para que FASE 10 no lo descubra en produccion.

**No se encontro ningun test** que ejercite `HasOrganizationalScope.has_object_permission()` directamente (ni con `sede_id=None` ni con `sede_id` fuera de asignacion) — confirmado por `grep -rln "HasOrganizationalScope" apps/ tests/`: la clase se menciona en un comentario de `test_organizational_dsv.py:56` (comparacion textual, no una llamada real a la clase) y en `apps/tenant/compras/tests/test_scope_pilot_f5.py` los tests con "otra_sede" en el nombre validan creacion/actualizacion con `area` de otra sede (validacion de `sede_esta_en_alcance`), **no** el `retrieve`/`update`/`delete` de un objeto vía `HasOrganizationalScope`. Es decir: **la unica pieza de OSF que hace cumplimiento real a nivel de objeto (`HasOrganizationalScope`) nunca se ha probado directamente con un test desde que se introdujo (ADR-003, 2026-08-07)** — brecha de cobertura real, no solo teorica.

---

## 5. `HasOrganizationalScope` — contrato completo verificado

**Fuente:** `apps/tenant/api/permissions.py:160-195`.

```
has_permission(request, view) -> True siempre
  (el filtrado de listas ya ocurre en el selector - ver §4; esta clase
  solo actua a nivel de objeto individual)

has_object_permission(request, view, obj):
  perfil = _get_perfil(request.user)
  si perfil is None o perfil.alcance == 'EMPRESA': True
  si perfil.alcance == 'SEDE':
      sede_id = obj.sede_id
      return sede_id is not None AND sede_id in perfil.sedes_asignadas
  si perfil.alcance == 'AREA':
      area_id = obj.area_id
      return area_id is not None AND area_id in perfil.areas_asignadas
  (cualquier otro valor de alcance): True
```

**Unico consumidor real:** `apps/tenant/compras/api/viewsets.py:67` (`OrdenCompraViewSet.get_permissions()`, junto a `IsTenantMember`/`IsTenantAdminOrReadOnly`). Ningun otro ViewSet la usa (confirmado, ver auditoria FASE 0/1).

---

## 6. Matriz EMPRESA/SEDE/AREA — sintesis para FASE 6 (piloto compras)

| alcance | `sede_ids`/`area_ids` resueltos | Listado (Selector, `filter_by_scope`) | Objeto individual (`HasOrganizationalScope`) |
|---|---|---|---|
| EMPRESA | `None`/`None` | Todo lo de la empresa | Todo lo de la empresa |
| SEDE, con asignaciones | conjunto completo / `None` | Solo `sede_id` en el conjunto (NULL visible si se usa la variante null-safe) | Solo `sede_id` en el conjunto; **NULL siempre denegado**, sin variante null-safe |
| SEDE, sin asignaciones | `frozenset()` / `None` | Nada | Nada (`sede_id is not None and ... in frozenset()` siempre `False`) |
| AREA, con asignaciones | conjunto de sedes + conjunto de areas | Solo `area_id` en el conjunto (mismo patron NULL) | Solo `area_id` en el conjunto; NULL siempre denegado |
| AREA, sin asignaciones | `frozenset()` / `frozenset()` | Nada | Nada |

Esta tabla es la base directa para la "matriz de pruebas ADMIN/OPERADOR/VISOR x EMPRESA/SEDE/AREA" que pide FASE 6 — **nota importante para esa fase**: `rol` (ADMIN/OPERADOR/VISOR) no interviene en absoluto en `OrganizationalScope`/`HasOrganizationalScope` (son ortogonales, ver §1) — la matriz de FASE 6 debe probar `rol` por separado (via `HasTenantRole`/`IsTenantAdminOrReadOnly`, ya existentes) y `alcance` via esta tabla, no una combinacion fusionada que no corresponde a como el codigo real esta particionado.

---

## 7. Estado de ejecucion de tests (pytest real, Docker)

La corrida lanzada en FASE 1 (`docker compose exec web python -m pytest apps/tenant/core/tests/test_organizational_*.py -q`, que incluye `test_organizational_scope.py` y `test_organizational_filters.py`, ambos centrales a esta fase) **confirmo: `53 passed, 1 warning in 1452.86s (0:24:12)`** (2026-08-09). Las 9 suites completas (994 lineas) pasan, incluidos los 9 tests de `test_organizational_scope.py` citados en §3 y los tests NULL-safe de `test_organizational_filters.py` citados en §4. Todas las afirmaciones "demostrado por" de este documento quedan verificadas por ejecucion real.

---

## 8. Riesgos identificados en FASE 2 (nuevos, adicionales a los de FASE 0/1)

1. **Asimetria NULL entre `filter_by_scope_null_safe()` (permite) y `HasOrganizationalScope.has_object_permission()` (deniega)** — ver §4. El riesgo mas concreto de toda la auditoria hasta ahora: silenciosamente romperia UX (403 en objetos visibles en el listado) si `HasOrganizationalScope` se copia tal cual a una app con `sede` nullable en FASE 10.
2. **`HasOrganizationalScope.has_object_permission()` nunca se ha probado con un test dedicado** desde su introduccion (ADR-003) — cobertura real es cero pese a ser la unica pieza de enforcement de objeto de todo OSF.
3. **AREA implica SEDE de forma no explicita:** un perfil `alcance=AREA` tiene tanto `sede_ids` como `area_ids` resueltos (§2, paso 4-5) pero `sedes_asignadas` y `areas_asignadas` son M2M **independientes** — nada en el modelo obliga a que las `areas_asignadas` de un perfil pertenezcan a sus `sedes_asignadas` (no hay `clean()`/constraint verificado en esta fase que lo valide). Un perfil podria tener `areas_asignadas` de una sede que NO esta en `sedes_asignadas` sin que el sistema lo detecte — candidato a revisar en FASE 3 (Contrato Definitivo) o FASE 6.
4. **Gap de cobertura AREA-sin-asignaciones:** existe test explicito para "SEDE sin asignaciones restringe a nada" pero no un equivalente literal para "AREA sin asignaciones restringe a nada" sobre `OrganizationalScope.resolve()` directamente (solo se prueba indirectamente via el helper `area_esta_en_alcance`).

---

## Cierre de FASE 2

Ningun archivo de codigo funcional fue modificado. Documento creado: `documentacion/OSF_TECHNICAL_AUDIT.md` (este archivo).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
