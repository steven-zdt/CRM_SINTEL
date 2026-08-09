# ADR-005: Organizational Scope Framework (OSF) — Contrato Independiente y Rollout sin Migración de Esquema

**Estado:** ACCEPTED (parcialmente implementado — ver "Alcance verificado" abajo antes de asumir cobertura total)
**Fecha:** 2026-08-09 (formalizado retroactivamente; el trabajo que documenta se ejecutó 2026-08-08/09 según `MEMORY.md` y `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`)
**Autores:** Sintel Engineering
**Relacionado con:** ADR-003 (piloto `compras`, `SedeAwareModel`), ADR-004 (diseño original de OCF, ver su "Adenda 2026-08-09" — este ADR formaliza 2 decisiones que divergieron de ese diseño)

---

## Por qué existe este ADR (criterio de creación, no solo numeración)

El plan de consolidación OCF/OSF (FASE 4, `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`)
exige explícitamente **no crear un ADR nuevo solo por numeración** — debe existir una decisión
arquitectónica real que lo justifique. Tras auditar el código real
(`documentacion/OCF_TECHNICAL_AUDIT.md`, `OSF_TECHNICAL_AUDIT.md`,
`ORGANIZATIONAL_CONTRACT.md`) se confirmaron **dos decisiones arquitectónicas reales**, tomadas
explícitamente con el usuario durante el proyecto OSF, que divergen de lo que ADR-003/ADR-004 ya
habían decidido — no son continuación mecánica de esos ADR, son pivotes documentados:

1. `OrganizationalScope` se resuelve de forma **independiente** de `OrganizationalContext`, no
   como un envoltorio construido a partir de él (ADR-004 lo diseñaba al revés — ver su Adenda).
2. El rollout a las apps con datos históricos (`facturas`, `cotizaciones`, `gastos`, `inventario`,
   `proyectos`, `empleados`) **no sigue** el patrón de ADR-003 (`SedeAwareModel` + migración
   nullable→backfill→harden `NOT NULL`) — usa un patrón nuevo, de solo lectura, que nunca
   endurece el esquema.

Ambas decisiones tienen impacto real en cómo cualquier ingeniero futuro debe razonar sobre el
código — merecen registro propio, no una nota de pie de página en ADR-003/004.

---

## Contexto

ADR-003 (2026-08-07) estableció el patrón "Rollout pendiente" para las 16 apps no-piloto: cada
una adoptaría `SedeAwareModel`, correría una migración controlada de 3 pasos
(nullable→backfill→`NOT NULL`), y decidiría individualmente si aplicar `HasOrganizationalScope`.
ADR-004 (mismo día) diseñó `OrganizationalScope` como una clase construida a partir de un
`OrganizationalContext` ya resuelto (`__init__(self, context, sedes_asignadas, areas_asignadas)`).

Al ejecutar el rollout real (proyecto OSF, `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`,
fases F2 y F7), ambos planes se toparon con hechos que no se conocían al escribir esos dos ADR:

- **F2** (`organizational_scope.py`): acoplar `OrganizationalScope` a un `OrganizationalContext`
  ya resuelto habría heredado un bug latente — `OrganizationalContext.filter()` filtra por la
  sede ACTIVA (una sola), mientras que el permiso de objeto ya existente
  (`HasOrganizationalScope`, ADR-003) verifica contra el conjunto COMPLETO de sedes asignadas. Un
  perfil con 3 sedes asignadas vería en un listado construido sobre `OrganizationalContext` solo
  1 de las 3, pese a poder acceder a las 3 directamente por UUID. Verificado con código real, no
  solo argumentado (ver `ORGANIZATIONAL_SCOPE_MASTER_PLAN.md` §4, y el test
  `test_context_active_sede_vs_scope_full_set_es_la_distincion_real`).
- **F7** (`organizational_filters.py`, `filter_by_scope_null_safe`): antes de migrar los
  Selectors de las 6 apps candidatas, se auditaron los datos reales de los 3 tenants del entorno
  (pedido explícito del usuario, no asumido) — el campo `sede` de esas 6 apps está en **NULL en
  el 100% de los registros existentes** (era puramente informativo para un reporte KPI, nunca se
  exigió). Aplicar el patrón estricto de ADR-003 (`filter_by_scope()`, correcto en `compras`
  porque ahí `sede` es `NOT NULL`) habría ocultado el 100% de los datos existentes a cualquier
  usuario con alcance SEDE/AREA — una regresión severa disfrazada de mejora de seguridad.

---

## Decisión

### 1. `OrganizationalScope` es un contrato independiente, no un envoltorio de `OrganizationalContext`

`OrganizationalScope.resolve(request)` (`apps/tenant/core/services/organizational_scope.py:131-181`)
duplica deliberadamente el mismo algoritmo de resolución de `empresa_id` que usa
`OrganizationalContext.resolve()` (y que a su vez ya usa `SintelDSVMixin.get_empresa_id()`) en vez
de recibir un `OrganizationalContext` ya resuelto como parámetro. Ninguno de los dos objetos
depende de que el otro se resuelva primero o exista.

**Regla de nomenclatura y relación, definitiva (no se reabre en fases futuras sin una decisión
igual de explícita):**

```
OrganizationalContext = EXECUTION CONTEXT  ("dónde estoy parado ahora": 1 sede activa)
OrganizationalScope    = AUTHORIZATION BOUNDARY ("qué puedo tocar en total": conjunto completo)
```

Ver `documentacion/ORGANIZATIONAL_CONTRACT.md` (FASE 3 del plan de consolidación) para el
contrato completo verificado — quién crea cada uno, qué contiene, qué consume qué.

**Costo aceptado de esta decisión:** la resolución de `empresa_id` queda triplicada en el código
(`SintelDSVMixin.get_empresa_id()`, `OrganizationalContext.resolve()`,
`OrganizationalScope.resolve()`) — solo el primer par tiene un test de paridad automatizado
(`test_organizational_context.py`). Riesgo aceptado explícitamente, no descubierto después;
documentado también en `OCF_TECHNICAL_AUDIT.md` §1 como pendiente de blindar con un test
equivalente para el tercer algoritmo.

### 2. Rollout sin migración de esquema: `filter_by_scope_null_safe()`

Para las 6 apps con campo `sede` histórico y 100% NULL (`facturas`, `cotizaciones`, `gastos`,
`inventario`, `proyectos`, `empleados`), el rollout **no** sigue el checklist de ADR-003
("Rollout pendiente"): no se adopta `SedeAwareModel`, no se ejecuta la migración
nullable→backfill→`NOT NULL`, y el campo `sede` permanece exactamente como estaba (nullable,
`DT-SEDE-0X`, informativo).

En su lugar, `filter_by_scope_null_safe()` (`apps/tenant/core/services/organizational_filters.py:59-90`)
aplica esta regla: un registro con `sede_id`/`area_id` en `NULL` es **visible para todos los
alcances** (EMPRESA/SEDE/AREA) — preserva el 100% del comportamiento actual mientras la capacidad
de filtrado real se activa progresivamente a medida que se asignen sedes/áreas reales a registros
nuevos.

**Único adoptante del patrón original de ADR-003** (`SedeAwareModel` + migración completa +
`filter_by_scope()` estricto, sin NULL-safety): `compras`, porque `OrdenCompra.sede` es `NOT
NULL` desde su propia migración `0007`. **Ningún otro app adoptó `SedeAwareModel`** — confirmado
por grep en `OCF_TECHNICAL_AUDIT.md` §2, cero herencias fuera de `OrdenCompra`.

**Asimetría conocida y no resuelta por este ADR (documentada, no oculta):**
`HasOrganizationalScope.has_object_permission()` (ADR-003, `apps/tenant/api/permissions.py:182-195`)
**deniega** el acceso a un objeto con `sede_id=None` para un perfil alcance SEDE — comportamiento
opuesto a `filter_by_scope_null_safe()`, que lo deja visible. Hoy no es un bug porque
`HasOrganizationalScope` solo protege `compras` (donde `sede` nunca es NULL). Es una condición de
bloqueo explícita para cualquier fase futura que quiera aplicar `HasOrganizationalScope` a una de
las 6 apps de este ADR sin corregir antes esa asimetría — ver `OSF_TECHNICAL_AUDIT.md` §4/§8.

---

## Alcance verificado (qué está realmente en producción, no lo que el plan maestro afirma sin verificar)

`documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md` reporta las 17 fases (F0-F16) como 🟢
COMPLETA, incluyendo Knowledge Graph organizacional y gobernanza automática. La auditoría de
código real de esta consolidación (FASE 1/2 del plan) verificó, con grep sobre las 17 apps
tenant, que la adopción real en producción es más acotada que ese reporte sugiere a primera
lectura:

| Componente | Estado verificado por código (no por el plan maestro) |
|---|---|
| `filter_by_scope_null_safe()` en selectors de 6 apps | ✅ Confirmado, consumidores reales |
| `OrganizationalScope.resolve()` llamado directo en ViewSets/mixins de 8 apps | ✅ Confirmado |
| `OrganizationalScopeMixin` | ❌ Cero herencias en todo el proyecto — código muerto |
| `HasOrganizationalScope` fuera de `compras` | ❌ Cero — sigue siendo solo el piloto de ADR-003 |
| `SedeAwareModel` fuera de `OrdenCompra` | ❌ Cero adopciones |
| Knowledge Graph organizacional (F15) / Gobernanza ampliada (F16) | No auditado en detalle por esta consolidación — pendiente de verificación independiente si se necesita confiar en ese resultado específico |

Este ADR documenta la decisión arquitectónica (por qué se hizo así), no certifica que el 100% del
plan maestro esté implementado y probado — para eso, ver FASE 5 (Matriz Global de Cobertura) del
plan de consolidación.

---

## Consecuencias

**Positivas:**
- El rollout a 6 apps con datos históricos no rompió ni ocultó ningún dato existente — verificado
  con auditoría de datos real antes de escribir código, no asumido.
- `OrganizationalScope` desacoplado de `OrganizationalContext` evita que un selector herede sin
  saberlo el bug de "solo veo mi sede activa, no todas las asignadas".
- Ninguna de las 6 apps requirió una migración de esquema disruptiva para obtener filtrado por
  alcance — reduce el riesgo de la Fase 10 (Rollout Controlado) del plan de consolidación.

**Negativas / riesgos aceptados:**
- Triplicación de la resolución de `empresa_id`, con solo 1 de los 2 pares protegido por test de
  paridad automatizado.
- Asimetría NULL entre `filter_by_scope_null_safe()` (permite) y `HasOrganizationalScope` (deniega)
  — mina activa para cualquier futuro rollout de `HasOrganizationalScope` a las 6 apps de este ADR.
- El filtrado NULL-safe es deliberadamente permisivo (no restringe lo NUNCA clasificado) — un
  perfil alcance SEDE sigue viendo el 100% de los registros históricos de esas 6 apps hasta que
  se les asigne una sede real; esto es el comportamiento correcto elegido explícitamente, pero
  significa que el "aislamiento por sede" en esas 6 apps es hoy parcial por diseño, no un defecto
  de implementación.

---

## Archivos relevantes de esta decisión

| Archivo | Rol |
|---|---|
| `apps/tenant/core/services/organizational_scope.py` | `OrganizationalScope`, resolución independiente |
| `apps/tenant/core/services/organizational_filters.py` | `filter_by_scope_null_safe()` |
| `apps/tenant/core/tests/test_organizational_scope.py` | Test que pinea la distinción Context-activa vs Scope-conjunto-completo |
| `apps/tenant/core/tests/test_organizational_filters.py` | Test de `filter_by_scope` vs `filter_by_scope_null_safe` |
| `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md` §4, §9 | Registro original de ambas decisiones, con el usuario, en el momento en que se tomaron |
| `documentacion/OSF_TECHNICAL_AUDIT.md` | Auditoría de código real que motivó este ADR |
| `documentacion/ORGANIZATIONAL_CONTRACT.md` | Contrato completo Context vs Scope |
