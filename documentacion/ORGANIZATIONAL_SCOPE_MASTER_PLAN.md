# Organizational Scope Framework (OSF) — Plan Maestro

**Origen:** `documentacion/Nueva recomendación arquitectónica.md` (2026-08-08). Reencuadra el
proyecto "Organizational Context Framework" (OCF, 14 fases, cerrado el mismo día) como la
finalización y estandarización del **Contexto Organizacional Sede/Área ya iniciado por ADR-003**
— no un framework nuevo. El objetivo no es "crear" nada: es terminar de propagar
`SedeAwareModel` + `TenantProfile.alcance` + `HasOrganizationalScope` (hoy solo reales en
`compras`) al resto del ERP, empezando por validar y cerrar el piloto de `compras`.

**Relación con OCF (no duplicar):** OCF construyó el *resolver contract*
(`OrganizationalContext`, `OrganizationalContextMixin`) y lo adoptó de forma aditiva en 14 apps,
pero **deliberadamente sin migrar ningún selector/business service a filtrar por sede/área de
verdad** — documentado en cada cierre de app de la Fase 9 de OCF. OSF continúa exactamente ahí:
Fases F7 (Selectors) y F8 (Business Services) son el trabajo que OCF dejó pendiente a propósito.

**Última actualización:** 2026-08-09
**Fase actual:** F16 — Gobernanza automática ampliada — 🟢 COMPLETA (proyecto cerrado)
**Progreso global:** 17/17 fases (F0-F16) = 100%

```
F0  Governance Baseline          ██████████████████████ 100% 🟢 COMPLETA
F1  Normalizar ADR/Scope         ██████████████████████ 100% 🟢 COMPLETA
F2  Contrato Organizacional      ██████████████████████ 100% 🟢 COMPLETA
F3  Resolver Contexto            ██████████████████████ 100% 🟢 COMPLETA
F4  Datos Existentes             ██████████████████████ 100% 🟢 COMPLETA
F5  Compras — Piloto             ██████████████████████ 100% 🟢 COMPLETA
F6  Matriz Organizacional        ██████████████████████ 100% 🟢 COMPLETA
F7  Selectors                    ██████████████████████ 100% 🟢 COMPLETA
F8  Business Services            ██████████████████████ 100% 🟢 COMPLETA
F9  Bridges                      ██████████████████████ 100% 🟢 COMPLETA
F10 Ventas → Facturas            ██████████████████████ 100% 🟢 COMPLETA
F11 Facturas                     ██████████████████████ 100% 🟢 COMPLETA
F12 Contabilidad                 ██████████████████████ 100% 🟢 COMPLETA
F13 Resto de Apps                ██████████████████████ 100% 🟢 COMPLETA
F14 Tests de Aislamiento         ██████████████████████ 100% 🟢 COMPLETA
F15 Knowledge Graph              ██████████████████████ 100% 🟢 COMPLETA
F16 Governance Engine            ██████████████████████ 100% 🟢 COMPLETA
```

> **Nota (2026-08-09):** este encabezado quedó desactualizado entre F9 y F14 — cada fase se
> documentó correctamente en su propia sección (§9-§16 más abajo) pero nadie actualizó este
> resumen hasta que un agente de auditoría de F15 lo detectó. Corregido para reflejar el estado
> real del cuerpo del documento (fuente de verdad).

> **Regla de gobernanza (impuesta por el propio documento de recomendación, §8):** ninguna fase se
> ejecuta de forma completamente automática. Cada fase sigue: AUDITORÍA → IMPLEMENTACIÓN → TESTS →
> AUDITORÍA POST → DOCUMENTACIÓN → GRAPH UPDATE → 🟢 COMPLETA → AUTORIZACIÓN → SIGUIENTE FASE.
> Estados: ⚪ NO INICIADA · 🔵 AUDITANDO · 🟡 IMPLEMENTANDO · 🟣 VALIDANDO · 🟢 COMPLETADA ·
> 🔴 BLOQUEADA · ⚫ ROLLBACK.

---

## 1. Documento maestro y satélites (per §9 de la recomendación)

- `documentacion/ORGANIZATIONAL_SCOPE_BASELINE.md` — Fase 0, auditoría inicial (🟢 completo)
- `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md` — este archivo, tracking F0-F16
- `documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md` — Fase F6, matriz de 17 apps (🟢 completo)
- `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md` — Fase F13 (pendiente de crear)
- `docs/ADR-003-contexto-organizacional-sede-area.md` — ya existe, sin renombrar (ver F1)
- `apps/tenant/core/services/organizational_scope.py` — Fase F2, contrato `OrganizationalScope`
  (distinto y complementario a `OrganizationalContext` de OCF — no fusionado, no renombrado)

---

## 2. F0 — Governance Baseline — 🟢 COMPLETA

Ver `documentacion/ORGANIZATIONAL_SCOPE_BASELINE.md` para el detalle completo. Resumen:

- Validado el estado real de `SedeAwareModel`, `TenantProfile.alcance`, `HasOrganizationalScope`,
  `sedes_asignadas`/`areas_asignadas` contra `compras`, `empresa`, `perfil`, `facturas`.
- **Inconsistencia documental real encontrada** (más amplia que la que señalaba el propio
  documento de recomendación): numeración ADR duplicada en **dos** números (002 y 003, no solo
  003), entre la tabla histórica de `arquitectura_general.md` §7 y los archivos reales
  `docs/ADR-NNN-*.md`. Verificado por grep exhaustivo antes de tocar nada.
- Matriz preliminar de `sede`/`area`: 7 modelos candidatos, 1 migrado (`compras.OrdenCompra`), 6
  pendientes — con precisión exacta gracias a la regla de gobernanza EKG que OCF Fase 11 ya
  construyó (no una estimación nueva).
- Relación con OCF documentada explícitamente para no duplicar trabajo.

**Checklist:** [x] Arquitectura [x] Auditoría real (no asumida) [x] Documentación
[x] Inconsistencia resuelta antes de continuar (regla del propio documento)

---

## 3. F1 — Normalizar ADR-003 y numeración canónica — 🟢 COMPLETA

**Qué se hizo:**
- Corregida la tabla de ADRs en `documentacion/arquitectura_general.md` §7: se conservan los 4
  archivos `docs/ADR-001..004-*.md` sin renombrar (convención activa, referenciada en docenas de
  archivos de código — renombrarlos habría sido mucho más disruptivo que corregir una tabla). Las
  2 decisiones históricas sin archivo propio ("Desacoplamiento Contable Total", "TareaCorta FK")
  se retiraron de la numeración ADR-NNN y quedan documentadas como "Decisiones técnicas
  históricas (pre-ADR)".
- **Definición formal de Empresa/Sede/Área/Alcance/Rol/Permiso**: ya existe y es correcta —
  `docs/ADR-003-contexto-organizacional-sede-area.md` §5 ("Alcance organizacional en permisos,
  ortogonal a `rol`") ya documenta exactamente la separación Rol≠Alcance que pide esta fase, con
  los mismos ejemplos conceptuales (Usuario con Rol=OPERADOR, Alcance=SEDE, Sede Bogotá). No se
  escribió contenido nuevo porque ya existía y es correcto — verificado, no asumido.

**Componentes pendientes:** ninguno para el alcance de esta fase.

**Cambios realizados:** 1 archivo modificado (`documentacion/arquitectura_general.md` §7,
sólo la tabla de ADRs y su nota de gobernanza). Cero código de producción tocado.

**Validaciones ejecutadas:** `grep` exhaustivo de "ADR-002"/"ADR-003" en `apps/` confirmando cero
referencias rotas tras el cambio (el cambio es puramente en la tabla histórica, ningún código
referencia esas 2 decisiones por número).

**Checklist:** [x] Arquitectura [x] Documentación [x] Sin romper referencias existentes
[x] Rol≠Alcance confirmado ya formalizado (ADR-003 §5)

---

## 4. F2 — Contrato Organizacional (`OrganizationalScope`) — 🟢 COMPLETA

**Decisión de relación con OCF (dada explícitamente por el usuario, no derivada):**
`OrganizationalScope` **no se renombra a `OrganizationalContext` ni se fusiona con él** — se
mantienen como conceptos distintos y complementarios. Esta fase formaliza esa decisión con un
motivo técnico concreto encontrado durante el diseño (no solo documental):

- **`OrganizationalContext`** (OCF) responde *"dónde estoy parado ahora"*: una posición activa
  única — `sede_id` es LA sede activa (sesión → primera asignada → Sede Principal,
  `resolve_sede_activa_id()`). Sirve para defaultear registros nuevos y pintar el header.
- **`OrganizationalScope`** (OSF, nuevo) responde *"qué puedo tocar en total"*: el conjunto
  COMPLETO `perfil.sedes_asignadas`/`areas_asignadas`, sin colapsar a una activa. Es lo que un
  Selector necesita para listar (F7) y lo que un Business Service/Bridge necesita para validar
  (F8/F9).

**Hallazgo que justifica la distinción (no teórico):** `OrganizationalContext.filter(Model)`
(OCF Fase 6) filtra solo por la sede activa (un único id), mientras que `HasOrganizationalScope`
(`apps/tenant/api/permissions.py`, ADR-003) ya verifica contra el conjunto **completo** de sedes
asignadas para permisos de objeto. Un perfil con alcance SEDE asignado a 3 sedes vería en un
listado vía `OrganizationalContext.filter()` solo 1 de las 3, aunque el permiso de objeto le
permitiría acceder a las 3 directamente por UUID — asimetría real entre "lo que se lista" y "lo
que se permite". Hoy no se manifiesta como bug porque ningún selector real usa
`OrganizationalContext.filter()` todavía (adopción real es F7) — pero confirma que colapsar ambos
conceptos en uno solo habría heredado ese bug latente. Documentado explícitamente para que **F7
migre los selectors a `OrganizationalScope.filter()`, no a `OrganizationalContext.filter()`** — no
se corrige `OrganizationalContext` en esta fase (F2 es solo "definir el contrato").

**Qué se construyó:**
- [apps/tenant/core/services/organizational_scope.py](../apps/tenant/core/services/organizational_scope.py)
  (nuevo): `OrganizationalScope` (dataclass inmutable: `empresa_id`, `alcance`, `sede_ids`,
  `area_ids` — estos dos últimos `frozenset[int] | None`, `None` = sin restricción, conjunto vacío
  = alcance SEDE/AREA sin ninguna asignación todavía, restringe a "nada"), con `.resolve(request)`,
  `.permits_sede()`, `.permits_area()`, `.filter(model)` (usa `sede_id__in`/`area_id__in`, no un
  único id) y `OrganizationalScopeMixin` (opt-in, independiente de `OrganizationalContextMixin` —
  no comparten estado ni caché).
- `.resolve()` duplica deliberadamente la resolución de `empresa_id` (mismo algoritmo que
  `OrganizationalContext.resolve()`) en vez de leerla desde un `OrganizationalContext` ya resuelto
  — decisión explícita de no acoplar ambos conceptos entre sí.
- [apps/tenant/core/tests/test_organizational_scope.py](../apps/tenant/core/tests/test_organizational_scope.py)
  (nuevo, 5 tests): alcance EMPRESA sin restricción, alcance SEDE con conjunto completo (no una
  sola activa), alcance SEDE sin asignaciones (restringe a nada, no a todo), usuario anónimo
  (`OrganizationalScopeError`), y el test que **pinea la distinción real** con datos concretos:
  perfil asignado a `sede_a`+`sede_b`, sede activa en sesión = `sede_a`, 1 `OrdenCompra` por cada
  sede → `OrganizationalContext.filter()` devuelve solo la de `sede_a`,
  `OrganizationalScope.filter()` devuelve ambas.

**Componentes pendientes:** ninguno para el alcance de esta fase — `OrganizationalScope` no se
conecta todavía a ningún ViewSet/Selector real (esa es F7/F8, igual que
`OrganizationalContextMixin` en su momento no se conectó hasta la Fase 9 de OCF).

**Cambios realizados:** 2 archivos nuevos, cero archivos de producción existentes modificados
(no se tocó `organizational_context.py`, `permissions.py` ni ningún selector).

**Validaciones ejecutadas:** suite nueva `test_organizational_scope.py` +
`test_organizational_context.py` (paridad no rota) ejecutadas juntas.

**Checklist:** [x] Contrato definido [x] Relación con OCF resuelta por decisión explícita del
usuario (no fusionar, no renombrar) [x] Motivo técnico real documentado (no solo preferencia)
[x] Tests [x] Cero código de producción existente modificado [x] Documentación

---

## 5. F3 — Resolver el Contexto del Usuario (end-to-end) — 🟢 COMPLETA

**Objetivo de la fase (literal, del documento de recomendación):** al entrar al tenant debe quedar
"perfectamente determinado" `TENANT → EMPRESA → USUARIO → TENANTPROFILE → ROL → ALCANCE →
SEDE/S → ÁREA/S`. Nótese el plural explícito en `SEDE/S`/`ÁREA/S` — es la primera pista de que
esta fase pertenece a `OrganizationalScope` (F2), no a `OrganizationalContext` (OCF), que
resuelve una sola sede activa por diseño.

**Auditoría previa (antes de escribir código):** la cadena de resolución YA existía por completo
a nivel de datos/algoritmo — `OrganizationalContext.resolve()` (OCF) cubre
tenant→empresa→usuario→perfil→rol→alcance→sede-activa, y `OrganizationalScope.resolve()` (F2,
recién construido) cubre alcance→sede/s→área/s en conjunto completo. **El hallazgo real de esta
fase no fue en la lógica de resolución, sino en su exposición**: `GET /api/v1/core/contexto/`
(`ContextoOrganizacionalView`, el único endpoint que el Workspace consulta al cargar tras el
login) devolvía solo `OrganizationalContext.to_dict()` — nunca exponía el conjunto plural de
sedes/áreas permitidas a ninguna pieza de UI/JS. Ninguna otra ruta lo exponía tampoco (el
selector de "sede activa" del header lee `perfil.sedes_asignadas` server-side vía template, no
vía este endpoint). Es decir: el dato existía en el modelo (`TenantProfile.sedes_asignadas`),
pero ninguna API de solo lectura lo consolidaba junto al resto del contexto en un solo lugar.

**Hallazgo secundario, documentado y NO corregido en esta fase** (edge case de política, no de
código roto): `resolve_sede_activa_id()` (`apps/tenant/core/services/sede_context.py`), usado por
`OrganizationalContext`, cae de vuelta a la Sede "Principal" de la empresa como último fallback
**sin verificar si esa sede está en `sedes_asignadas`** — un perfil con `alcance=SEDE` y CERO
sedes asignadas terminaría con una "sede activa" (Principal) aunque `OrganizationalScope` para ese
mismo perfil calcule correctamente `sede_ids=frozenset()` (sin acceso a ninguna). Hoy es
inocuo porque nada lee `sede_id` para autorizar accesos (solo para defaultear); documentado aquí
para que F4 (estrategia de sede/área por defecto) o una fase de permisos futura lo evalúe
explícitamente, no se decide unilateralmente en esta fase de solo-resolución.

**Qué se construyó:**
- `OrganizationalScope.to_dict()` (nuevo método en
  [organizational_scope.py](../apps/tenant/core/services/organizational_scope.py)): serializa
  `sede_ids`/`area_ids` (`frozenset` → lista ordenada; `None` se preserva — "sin restricción" es
  distinto de "restringe a nada").
- [apps/tenant/core/api/contexto.py](../apps/tenant/core/api/contexto.py):
  `ContextoOrganizacionalView.get()` ahora agrega un bloque `"scope": {...}` a la respuesta
  existente, resolviendo `OrganizationalScope` de forma independiente (try/except propio — si
  fallara, degrada a `"scope": None` sin romper el resto de la respuesta, ya aditiva por diseño).
  Se extendió el endpoint ya existente en vez de crear uno nuevo — es el mismo punto de entrada
  que el Workspace ya consulta al cargar, mismo criterio de "no duplicar mecanismos" de toda la
  sesión.
- Tests nuevos en
  [test_organizational_resolver.py](../apps/tenant/core/tests/test_organizational_resolver.py):
  round-trip HTTP real confirmando que, con un perfil `alcance=SEDE` asignado a 2 sedes, la
  respuesta trae `sede_id` (una sola, OCF) Y `scope.sede_ids` (las 2, OSF) simultáneamente; y que
  `alcance=EMPRESA` produce `scope.sede_ids`/`area_ids` en `None` (sin restricción).

**Componentes pendientes:** ninguno para el alcance de esta fase. La UI/JS que consuma
`scope.sede_ids`/`area_ids` para construir selectores multi-sede reales es trabajo de UI, fuera
del alcance de "resolver el contexto" (podría abordarse junto con F5/F6 si se necesita).

**Cambios realizados:** 2 archivos de producción modificados de forma aditiva
(`organizational_scope.py`: +1 método; `contexto.py`: +1 bloque en la respuesta existente, ningún
campo removido ni renombrado). 1 archivo de test extendido.

**Validaciones ejecutadas:** suite `test_organizational_resolver.py` +
`test_organizational_scope.py` + `test_organizational_context.py` juntas (paridad OCF intacta,
scope nuevo cubierto, endpoint real vía HTTP).

**Checklist:** [x] Cadena completa auditada (ya resuelta a nivel de dato, gap era de exposición)
[x] Gap real identificado y cerrado (endpoint) [x] Edge case de política documentado sin decidir
fuera de alcance [x] Tests end-to-end vía HTTP real [x] Cero campo existente removido/roto
[x] Documentación

---

## 6. F4 — Datos Existentes (Sede/Área por defecto) — 🟢 COMPLETA

**Objetivo de la fase (del documento de recomendación):** para cada empresa existente garantizar
Empresa→Sede Principal→Área General, sin migración ciega de datos históricos.

**Auditoría empírica previa (no asumida desde `MEMORY.md`):** la semilla de onboarding
(`asegurar_estructura_organizacional_inicial()`, invocada desde `crear_tenant_con_owner()` y
`onboard_tenant()`) y el comando de backfill (`manage.py backfill_sede_area`) ya existían desde el
piloto ADR-003. Se verificó contra los 3 tenants reales del entorno (`home`, `qaisotest`,
`shelltest1`) con `--dry-run` primero: los 3 "ya tenían" Sede — pero una inspección más profunda
por conteo (`Sede.objects.count()`/`Area.objects.count()` por tenant) reveló un caso real
inconsistente antes de cerrar la fase.

**Bug real encontrado y corregido (2 capas, no 1):**
1. `asegurar_estructura_organizacional_inicial()` (`apps/tenant/empresa/services/business_service.py`)
   solo verificaba "¿la empresa ya tiene alguna Sede?" para decidir si saltarse TODO el seed — una
   empresa con Sede pero sin ninguna Área (creada por otra vía, ej. CRUD manual, no por este seed)
   nunca recibía su Área "General". Confirmado en producción: `shelltest1` tenía 1 Sede y 0 Área.
   Corregido para verificar Sede y Área **por separado** (idempotente en ambos niveles).
2. El propio comando `backfill_sede_area` tenía **su propio chequeo duplicado** ("¿tiene alguna
   Sede?") ANTES de siquiera llamar a la función ya corregida — por lo que el fix del punto 1
   nunca se ejecutaba para `shelltest1` (verificado: correr el comando corregido en el paso 1 solo
   seguía reportando "ya tenía, se omite"). Corregido delegando el chequeo real (Sede Y Área,
   sobre la sede específica que la función usa/crea) sin duplicar la lógica de la función.

**Qué se hizo:**
- [apps/tenant/empresa/services/business_service.py](../apps/tenant/empresa/services/business_service.py):
  `asegurar_estructura_organizacional_inicial()` ahora verifica Sede y Área de forma independiente.
- [apps/tenant/empresa/management/commands/backfill_sede_area.py](../apps/tenant/empresa/management/commands/backfill_sede_area.py):
  chequeo de "ya completo" corregido para mirar la Sede específica + su Área, no solo "alguna Sede".
- [apps/tenant/empresa/tests/test_estructura_organizacional_inicial.py](../apps/tenant/empresa/tests/test_estructura_organizacional_inicial.py)
  (nuevo, 3 tests): sin Sede (crea ambas), con Sede sin Área (crea solo el Área faltante, no
  duplica Sede), con Sede y Área (no-op).
- **Backfill real ejecutado** (no solo probado) contra los 3 tenants reales: `shelltest1` recibió
  su Área "General" faltante. Re-verificado empíricamente: los 3 tenants tienen `sedes>=1 Y
  areas>=1` después del fix.

**Edge case de F3 (`resolve_sede_activa_id()` cae a "Principal" sin verificar asignación):**
evaluado explícitamente en esta fase — se decide **no tocarlo ahora**: es un resolver de "sede
ACTIVA para defaultear" (OrganizationalContext), nunca usado para autorizar acceso
(`HasOrganizationalScope`/`OrganizationalScope` no lo consultan). Cambiar su fallback es una
decisión de producto (¿un perfil SEDE sin asignaciones debe defaultear a Principal, o a
ninguna?) fuera del alcance de "backfill de datos", no de "resolver el contexto". Queda
documentado para revisarse si una fase de permisos futura empieza a depender de `sede_id` para
autorizar.

**Hallazgo colateral real, deliberadamente NO corregido en esta fase, escalado a F5:** durante
esta auditoría se confirmó que compras' propio selector de LISTADO (`OrdenCompraServiceMixin.
get_qs_list()` → `_get_sede_id_seguro()`, `apps/tenant/compras/services/api_mixins.py:63-67`) ya
usa hoy la misma resolución de "una sola sede activa" para filtrar listas de `OrdenCompra` cuando
`alcance` es SEDE/AREA — es decir, el bug teórico de "lista solo la sede activa, no todas las
asignadas" que motivó separar `OrganizationalScope` de `OrganizationalContext` (F2) **ya existe en
producción hoy en compras**, no solo en el `OrganizationalContext.filter()` sin usar. F5 (piloto
oficial de compras) es la fase que audita exhaustivamente el Selector de compras — se documenta
aquí para que no se pierda, no se corrige en F4 (fuera de su alcance: "datos existentes", no
"lógica de selectors").

**Componentes pendientes:** ninguno para el alcance de esta fase.

**Cambios realizados:** 2 archivos de producción corregidos (bug de idempotencia en 2 capas),
1 archivo de test nuevo. Cero migración de esquema (ningún modelo cambió de forma; el fix es en
la lógica de un seed/backfill ya existente).

**Validaciones ejecutadas:** 3 tests nuevos + suite completa de `apps/tenant/empresa/tests/`
(regresión) + verificación empírica directa contra los 3 tenants reales (antes y después del
fix) + `manage.py backfill_sede_area --dry-run` y luego real.

**Checklist:** [x] Estrategia Sede Principal/Área General verificada, no solo asumida
[x] Bug real encontrado por auditoría empírica (no solo lectura de código) [x] Corregido en las
2 capas donde vivía, no solo la superficial [x] Backfill real ejecutado y re-verificado
[x] Edge case de F3 evaluado y resuelto explícitamente (no tocar, documentado por qué)
[x] Hallazgo de compras escalado a F5, no ignorado ni corregido fuera de alcance [x] Tests
[x] Documentación

---

## 7. F5 — Compras como Piloto Oficial (auditoría exhaustiva) — 🟢 COMPLETA

**Objetivo de la fase:** auditar exhaustivamente Model/Selector/BusinessService/CRUDService/
ViewSet/Serializer/Permission/Template/HTMX/JS/Tests de `compras` y demostrar
EMPRESA+SEDE+ÁREA+ROL+ALCANCE funcionando correctamente — no solo filtrando, sino
consistentemente en toda la pila. A diferencia de F0-F4 (mayormente auditoría/documentación), esta
fase encontró y corrigió **5 bugs reales** en código de producción.

**Bug 1 (el más grave, heredado de F4) — filtrado por una sola sede, no el conjunto asignado:**
`OrdenCompraServiceMixin.get_qs_list()` (API DRF) y `OrdenCompraTableView.get_queryset()` (grilla
HTML/HTMX real, la que el usuario efectivamente ve) filtraban ambos por una única "sede activa" —
la tabla HTML ni siquiera eso: **no aplicaba ningún filtro de sede en absoluto**, mostrando todas
las órdenes de la empresa sin importar el alcance del perfil. Corregido: ambos ahora usan
`OrganizationalScope` (F2) y filtran por el conjunto completo `sede_ids`/`area_ids` vía el nuevo
`filter_by_scope()` (`apps/tenant/core/services/organizational_filters.py`). `OrdenCompraSelector.
get_list()` cambió su firma de `sede_id: int` a `sede_ids`/`area_ids` (conjuntos).

**Bug 2 — ningún selector/serializer exponía `sede`/`area`:** con listados que ahora pueden traer
órdenes de múltiples sedes a la vez, no había forma visual de distinguir de dónde era cada fila —
ni en la API (`OrdenCompraListSerializer`/`DetailSerializer`) ni en la grilla HTML
(`OrdenCompraTable`) ni en el offcanvas de detalle. Agregado `sede_nombre`/`area_nombre`
(read-only) a ambos serializers, columna "Sede" a la tabla, y sección Sede/Área al offcanvas de
detalle — con los `select_related()`/`.only()` correspondientes para no introducir N+1.

**Bug 3 — `area` era imposible de asignar via la API:** `OrdenCompraBusinessService.
crear_orden_compra()` ya tenía DSV completa para `area` (opcional) desde el piloto ADR-003
original, pero `OrdenCompraCreateUpdateSerializer` nunca declaraba el campo — DRF lo descartaba de
`validated_data` antes de llegar al business service. Agregado `area` como campo escribible
(`UUIDOrPKRelatedField`, mismo patrón que `proyecto`/`documento_soporte`).

**Bug 4 — sin validar consistencia Sede↔Área:** ni crear ni actualizar verificaban que el Área
perteneciera a la MISMA Sede de la orden (solo que perteneciera a la misma empresa) — un Área de
otra sede habría dejado la orden en un estado organizacionalmente inconsistente. Agregada la
verificación `area.sede_id == sede.id` en ambos flujos (`crear_orden_compra`/
`actualizar_orden_compra`), retornando `400 area_invalida` si no coincide.

**Bug 5 — `actualizar_orden_compra` no tenía NINGÚN bloque DSV para `area`:** una vez agregado el
campo al serializer (Bug 3), sin este bloque un update habría pasado el valor de `area` sin
validar en absoluto al CRUD service (`setattr` genérico). Agregado el bloque DSV completo,
simétrico a los de proveedor/proyecto/documento_soporte ya existentes.

**Qué se construyó:**
- [organizational_filters.py](../apps/tenant/core/services/organizational_filters.py):
  `filter_by_scope()` nuevo (usa `__in`, complementa `filter_by_context()` sin reemplazarlo).
- [selectors.py](../apps/tenant/compras/services/selectors.py): `get_list()` con `sede_ids`/
  `area_ids`; `.only()`/`select_related()` extendidos con `sede`/`area` en list y detail.
- [api_mixins.py](../apps/tenant/compras/services/api_mixins.py): `get_qs_list()` usa
  `OrganizationalScope.resolve()` con degradación explícita a "sin restricción" si falla (mismas
  precondiciones más laxas que `_get_empresa_id_seguro()` ya usaba).
- [views.py](../apps/tenant/compras/views.py): `OrdenCompraTableView.get_queryset()` idem.
- [serializers.py](../apps/tenant/compras/api/serializers.py): `area` escribible +
  `sede_nombre`/`area_nombre` de solo lectura en ambos serializers de lectura.
- [business_service.py](../apps/tenant/compras/services/business_service.py): validación
  sede↔área en creación y actualización.
- [tables.py](../apps/tenant/compras/tables.py) y
  [offcanvas_detalle_compras.html](../apps/tenant/compras/templates/tenant/compras/offcanvas_detalle_compras.html):
  visibilidad de Sede/Área.
- [test_scope_pilot_f5.py](../apps/tenant/compras/tests/test_scope_pilot_f5.py) (nuevo, 7 tests):
  listado API con alcance SEDE (multi-sede) y AREA, listado sin restricción con alcance EMPRESA
  (+ `sede_nombre` visible), tabla HTMX con alcance SEDE, crear con área válida, crear con área de
  otra sede (falla), actualizar con área de otra sede (falla).

**Hallazgo verificado como PRE-EXISTENTE, no introducido por esta fase:**
`test_multitenant_isolation_compras_tabla_html` sigue fallando (`assert 302 == 200`,
`force_login()` no persiste sesión) — es el riesgo R-6 ya documentado desde Fase 0 de OCF.
Verificado con `git stash` de `views.py` (el único archivo de esta fase que toca esa vista):
falla idéntico sin el cambio de F5.

**Componentes pendientes:** ninguno para el alcance de esta fase. El edge case de
`resolve_sede_activa_id()` (F3/F4, fallback a Principal sin verificar asignación) sigue
deliberadamente sin tocar — no afecta la creación en este piloto porque el serializer nunca
expone `sede` como escribible (siempre se inyecta server-side).

**Cambios realizados:** 8 archivos de producción modificados, 1 test nuevo (7 casos), cero
migraciones de esquema nuevas (ningún campo de modelo cambió de forma).

**Validaciones ejecutadas:** suite completa `apps/tenant/compras/` + `tests/tenant/compras/`
(14 tests, 13 pasan + 1 pre-existente verificado con stash), `manage.py check`,
`makemigrations --check --dry-run`, `ruff check` sobre todos los archivos tocados/nuevos.

**Checklist:** [x] Model [x] Selector [x] BusinessService [x] CRUDService (sin cambios
necesarios) [x] ViewSet [x] Serializer [x] Permission (verificado correcto, sin cambios)
[x] Template [x] HTMX [x] JS (sin cambios necesarios — la tabla HTMX se re-renderiza server-side)
[x] Tests [x] EMPRESA+SEDE+ÁREA+ROL+ALCANCE demostrado funcionando end-to-end
[x] Fallo pre-existente verificado con stash, no atribuido erróneamente

---

## 8. F6 — Matriz de Alcance Organizacional — 🟢 COMPLETA

**Objetivo de la fase (del documento de recomendación):** "decidir qué entidad realmente necesita
sede y área" — con la advertencia explícita del propio documento: **"No debemos poner sede y area
indiscriminadamente en todos los modelos."**

**Por qué esta fase no fue solo copiar la tabla del documento:** el documento de recomendación
incluye una tabla de ejemplo que marca 15 de 17 apps genéricamente como "⏳ Pendiente" en Sede y
Área, sin distinguir "el campo ya existe pero nunca se usa" de "el campo no existe y hay que
decidir si tiene sentido crearlo", y sin aplicar su propia advertencia contra agregar el campo
indiscriminadamente. Se auditaron las 17 apps reales (incluyendo `core` y `landing`, ausentes de
la tabla de ejemplo) contra el código, no contra la plantilla.

**Método:** reutilizados los 6 hallazgos ya verificados de la regla de gobernanza EKG
(`find_sede_or_area_field_without_sede_aware_model`, OCF Fase 11) + el hallazgo de `empleados`
(OCF Fase 0) para las apps que YA tienen el campo; para las 8 apps restantes sin campo (`bancos`,
`clientes`, `contabilidad`, `core`, `dashboard`, `landing`, `proveedores`, `ventas`), un agente de
exploración dedicado leyó directamente cada `models.py` (cita archivo:línea) y emitió un juicio
explícito de plausibilidad de negocio para cada una — no un "pendiente" genérico.

**Resultado — 3 categorías reales, no 2:**
- **🟡 Candidatos fuertes (6 apps, campo ya existe):** `facturas`, `cotizaciones`, `gastos`,
  `inventario`, `proyectos`, `empleados` — menor esfuerzo para F13 (no requieren migración de
  esquema, solo activar el uso del campo que ya está en la base de datos).
- **🟢/🟠 Candidatos plausibles sin campo aún (4 apps):** `ventas` (prioridad alta — predecesor
  directo de `facturas`), `bancos`, `contabilidad` (solo `AsientoContable`/`MovimientoContable`,
  nunca el catálogo de cuentas ni los períodos fiscales), `proveedores` (caso débil).
- **🔴/⚪ No recomendado o no aplica (7 apps):** `clientes` (un cliente no está atado a una sede
  del vendedor), `dashboard` (agregador de solo lectura, requeriría rediseño del modelo de
  snapshot), `core`/`landing` (no son apps de dominio), `empresa`/`perfil` (son la fuente de la
  jerarquía, no consumidores).

**Qué se construyó:**
- [ORGANIZATIONAL_SCOPE_MATRIX.md](../documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md) (nuevo):
  matriz completa de 17 apps (`empresa_id`/campo `sede`/campo `area`/`SedeAwareModel`/alcance
  funcional hoy/veredicto), priorización recomendada para F13 en 3 tiers, y la justificación
  explícita de por qué difiere de la tabla del documento original.

**Componentes pendientes:** ninguno para el alcance de esta fase — es un documento de
planificación, no código. La ejecución de las prioridades que establece es F7-F13.

**Cambios realizados:** 1 documento nuevo, cero código de producción tocado.

**Validaciones ejecutadas:** los 6 campos "existe" se verificaron contra hallazgos ya confirmados
en fases previas (no re-derivados a ciegas); los 8 campos "no existe" se verificaron con lectura
directa de código por un agente de exploración dedicado.

**Checklist:** [x] Las 17 apps auditadas (no solo las 15 de la tabla de ejemplo) [x] Estado
verificado empíricamente, no asumido [x] Veredicto de plausibilidad de negocio explícito por app
(cumple la advertencia del propio documento) [x] Priorización para F13 [x] Documentación

---

## 9. F7 — Migrar Selectors a scope-aware — 🟢 COMPLETA

**Objetivo de la fase:** migrar los Selectors de los 6 "candidatos fuertes" de F6 (`facturas`,
`cotizaciones`, `gastos`, `inventario`, `proyectos`, `empleados`) para que filtren por
`OrganizationalScope` (sede/área), replicando el patrón que F5 ya probó y verificó en `compras` —
pero con una diferencia crítica encontrada ANTES de escribir código.

**Hallazgo real que cambió el diseño (auditoría de datos antes de implementar, pedida
explícitamente al usuario vía AskUserQuestion):** en los 3 tenants reales del entorno, el campo
`sede` está en **NULL en el 100% de los registros existentes** de las 6 apps (nunca se completó,
era puramente informativo para un reporte KPI del dashboard). Aplicar el filtrado estricto que
usa `compras` (`filter_by_scope()`, correcto ahí porque `OrdenCompra.sede` es `NOT NULL`) habría
**ocultado el 100% de los datos existentes** a cualquier usuario con alcance SEDE/AREA — una
regresión severa, no una mejora.

**Decisión del usuario:** filtrado NULL-safe — un registro con `sede`/`area` en `NULL` queda
**visible para todos los alcances** (EMPRESA/SEDE/AREA), no solo EMPRESA. Preserva el 100% del
comportamiento actual (toda la data real está en NULL hoy) mientras la capacidad de filtrado real
se activa progresivamente a medida que se asignen sedes/áreas reales a nuevos registros.

**Qué se construyó:**
- [organizational_filters.py](../apps/tenant/core/services/organizational_filters.py):
  `filter_by_scope_null_safe()` (nuevo, tercera función junto a `filter_by_context`/
  `filter_by_scope` — usa `Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids)`).
- **6 selectors migrados**, cada uno con `sede_ids=None` (default, sin restricción) y filtro
  NULL-safe cuando se pasa un valor: `FacturaSelectors.qs_list()`, `CotizacionSelector.get_list()`,
  `DocumentoSelector.get_list()` (gastos), `MovimientoInventarioSelector.get_list()`,
  `qs_list()` (proyectos, función de módulo, no clase), `EmpleadoSelector.get_list()` (única con
  AMBOS `sede_ids` y `area_ids`, por ser la única de las 6 con campo `area`).
- **6 ViewSets/mixins actualizados** para resolver `OrganizationalScope` y pasar `sede_ids`
  (y `area_ids` en empleados) al selector, con el mismo criterio de degradación ya usado en F5:
  si `OrganizationalScope.resolve()` falla, no restringir (comportamiento idéntico al de antes).
- **6 archivos de test nuevos** (`test_scope_selectors_f7.py` por app, 13 tests en total):
  alcance SEDE ve NULL + su sede pero no la de otra; alcance EMPRESA sigue viendo todo; empleados
  además prueba alcance AREA filtrando por área (no solo por sede).
- [test_organizational_filters.py](../apps/tenant/core/tests/test_organizational_filters.py)
  (nuevo): tests directos de `filter_by_scope()` (estricto, compras) vs.
  `filter_by_scope_null_safe()` (F7), pineando la distinción con datos reales.

**Hallazgo colateral, fuera de alcance, flageado por separado:** `apps/tenant/facturas/api/
viewsets.py:800` llama a `logger.exception(...)` sin que `logger` este definido en el módulo
(`ruff` F821, confirmado pre-existente vía `git diff` — no relacionado con los cambios de esta
fase). Escalado como tarea aparte, no corregido aquí.

**Complicación operativa durante esta fase (no de código):** múltiples corridas de test
sufrieron colisiones de base de datos de test (`test_sintel`) por conexiones que no cerraban
limpio entre corridas consecutivas — cada caso se resolvió terminando conexiones huérfanas
(`pg_terminate_backend`) y/o recreando la base, re-verificado que el fallo desaparecía sin
cambiar ninguna línea de código (documentado para no confundir con una regresión real).

**Componentes pendientes:** ninguno para el alcance de esta fase. Serializers/Templates/JS de
estas 6 apps (visibilidad de `sede`/`area` en la UI, como F5 hizo para `compras`) quedan para
cuando cada app tenga su propia fase dedicada (ej. F11 para `facturas`) — F7 es solo "Selectors".

**Cambios realizados:** 1 archivo nuevo (`organizational_filters.py` extendido), 12 archivos de
producción modificados (2 por app: selector + viewset/mixin), 7 archivos de test nuevos.

**Validaciones ejecutadas:** 13 tests nuevos de scope (uno por escenario/app) + 3 de
`filter_by_scope`/`filter_by_scope_null_safe` + suites `test_organizational_context_adoption.py`
existentes de las 6 apps (paridad OCF no rota) — 16/16 pasan. `manage.py check`,
`makemigrations --check --dry-run`, `ruff check` en todos los archivos tocados/nuevos.

**Checklist:** [x] Auditoría de datos ANTES de implementar (no asumido) [x] Decisión de política
NULL explícita del usuario, no asumida [x] 6/6 apps candidatas migradas [x] Mismo criterio de
degradación que F5 (sin scope resoluble, no restringir) [x] Tests por app + regresión OCF
[x] Hallazgo colateral (`logger` indefinido) escalado, no ignorado ni corregido fuera de alcance
[x] `manage.py check`/migraciones/lint limpios [x] Documentación

---

## 10. F8 — Migrar Business Services a scope-aware — 🟢 COMPLETA

**Objetivo de la fase:** que los Business Services de las 6 apps trabajen con el contexto
organizacional en vez de `empresa_id`/`sede_id`/`area_id`/`user_id` dispersos arbitrariamente por
método.

**Auditoría real (antes de asumir el patrón "hay que unificar parámetros"):** se grepeó `sede` en
los 6 `business_service.py` — **cero coincidencias en las 6 apps**. Conclusión inicial ("nada que
unificar, el campo nunca se toca en escritura") resultó **incompleta**: una segunda pasada sobre
los **serializers** (no solo business_service.py) reveló que 5 de las 6 apps
(`facturas`/`cotizaciones`/`gastos`/`proyectos`/`empleados`) ya tienen `sede` como campo
**escribible con DSV** a nivel de serializer (iniciativa previa `DT-SEDE-0X`, verificada por
primera vez a este nivel de detalle en esta fase) — el flujo real es
Serializer.validate() → `**data` genérico → CRUD service, sin pasar por lógica explícita en
business_service.py. `inventario.MovimientoInventario.sede` es la única de las 6 con el campo en
**solo lectura** en su serializer (no escribible por ningún medio hoy).

**Hallazgo real (el gap genuino de esta fase):** la DSV existente en los 5 serializers
verificaba **"la sede pertenece a la empresa"** (anti-IDOR) pero **nunca** "la sede está dentro
del alcance organizacional del usuario que hace la petición". Un perfil con `alcance=SEDE`
asignado solo a Sede A podía, vía API, asignarle a una Factura/Cotización/Gasto/Proyecto/Empleado
la Sede B (misma empresa, fuera de su alcance) sin ninguna restricción — el mismo tipo de bug que
F5 corrigió para compras (área/sede), aquí aplicado a sede/alcance.

**Verificación empírica de alcanzabilidad (no asumida) — resultado desigual entre apps:**
- **`cotizaciones`, `proyectos`, `empleados`:** `create()`/`update()`/`partial_update()` llaman
  `serializer.is_valid(raise_exception=True)` — el fix es **totalmente alcanzable**, confirmado
  con test end-to-end real en `empleados` (POST/PATCH vía API).
- **`gastos`:** `create()` bypasea el serializer por completo (pasa `request.data.copy()`
  directo al business service) — el fix **NO aplica en creación**, pero `update()`/
  `partial_update()` usan el flujo genérico de DRF (`ModelViewSet`, sin override) que **sí** llama
  al serializer — el fix protege ediciones, no altas.
- **`facturas`:** `create()` está bloqueado (solo `upload-ubl`) y `partial_update()` usa su
  propia whitelist `MANUAL_EDITABLE_FIELDS` que **no incluye** `sede` — el fix es **código muerto
  hoy** (no alcanzable por ningún endpoint actual), pero correcto y listo para cuando F11 ("Migrar
  Facturas funcional") conecte `sede` a un flujo real de escritura.

**Qué se construyó:**
- [organizational_scope.py](../apps/tenant/core/services/organizational_scope.py):
  `sede_esta_en_alcance(sede_id, request)` y `area_esta_en_alcance(area_id, request)` (nuevas,
  usan `OrganizationalScope.permits_sede()`/`.permits_area()` ya construidos en F2 — primer uso
  real de esos métodos). Mismo criterio de degradación de F5/F7: sin `request`/scope resoluble,
  permite (no bloquea un flujo que hoy funciona).
- **5 serializers actualizados** (`facturas`, `cotizaciones`, `gastos`, `proyectos`, `empleados`):
  `validate()` ahora llama a `sede_esta_en_alcance()` (y `area_esta_en_alcance()` en `empleados`,
  la única con ambos campos) inmediatamente después de la DSV de empresa ya existente — aditivo,
  ningún campo ni validación previa se modificó.
- Tests: 3 nuevos en `test_organizational_scope.py` (unitarios, para los 2 helpers) + 3 nuevos en
  `apps/tenant/empleados/tests/test_scope_write_validation_f8.py` (end-to-end vía API real: SEDE
  no puede asignar sede ajena, SEDE sí puede asignar la suya, EMPRESA puede cualquiera).

**Componentes pendientes:** ninguno para el alcance verificado de esta fase. La reconexión de
`gastos.create()`/`facturas.partial_update()` para que pasen por el serializer (haciendo el fix
alcanzable ahí también) es un cambio de flujo más profundo, fuera del alcance de "Business
Services" — queda para F11 (`facturas`) y una futura revisión de `gastos` si F13 la prioriza.

**Cambios realizados:** 1 archivo de servicio compartido extendido (2 funciones nuevas), 5
serializers modificados de forma aditiva, 2 archivos de test nuevos/extendidos.

**Validaciones ejecutadas (Testing Progresivo por Alcance, primera fase bajo la norma nueva):**
tests específicos de los 2 helpers nuevos + test de componente/app end-to-end en `empleados`
(la única app con ambos campos, cubre el patrón más completo) — no se corrió la suite completa
de las otras 4 apps porque el cambio es idéntico y mecánico en cada una (mismo import, misma
llamada, mismo lugar en `validate()`) y ya se verificó por lectura de código que cada `validate()`
sigue el mismo flujo. `manage.py check` y `ruff check` sobre los archivos tocados, limpios.

**Checklist:** [x] Auditoría real de business_service.py (0 apps) [x] Auditoría real de
serializers (5/6 con sede escribible, hallazgo no anticipado) [x] Gap genuino identificado
(DSV de empresa sí, DSV de alcance no) [x] Alcanzabilidad verificada por app, no asumida
uniforme [x] Fix aditivo en las 5 apps [x] Test end-to-end real en al menos una app
[x] `manage.py check`/`ruff` limpios [x] Documentación honesta de qué está vivo vs. código muerto
hoy

---

## 11. F9 — Migrar Bridges (sin romper soft references) — 🟢 COMPLETA

**Objetivo de la fase:** que los Bridges (`ClienteBridge`/`ProveedorBridge`/`InventarioItemBridge`/
`CotizacionBridge`/`BancosBridge`, todos en `apps/tenant/facturas/services/selectors.py`, ya
inventariados por OCF Fase 7) conozcan el alcance organizacional cuando el dominio lo necesite,
sin convertirse en Foreign Keys entre apps — preservando el diseño de soft references.

**Auditoría real de los 5 bridges (no asumida):**
- **`ClienteBridge`/`ProveedorBridge`:** resuelven `Cliente`/`Proveedor`, que F6 marcó
  explícitamente **"NO RECOMENDADO"** para sede/área (un cliente/proveedor no está atado a una
  sede del vendedor). **No aplica scope-awareness aquí** — hacerlo violaría la propia decisión ya
  tomada en F6.
- **`InventarioItemBridge`:** resuelve `Producto`/`Servicio` (catálogo), que **no tienen** campo
  `sede` (solo `MovimientoInventario`, la app candidata de F6/F7, lo tiene). **No aplica.**
- **`BancosBridge`:** resuelve `TransaccionBancaria` para conciliación (agregado numérico, no
  lookup de entidad) — `bancos` es tier 2 en F6 ("candidato plausible sin campo aún"), sin campo
  `sede` hoy. **No aplica.**
- **`CotizacionBridge`:** resuelve `Cotizacion`, que SÍ tiene `sede` (candidato fuerte de F6/F7
  ya migrado en su selector). **Único bridge con sustancia real para esta fase.**

**Hallazgo real:** `FacturaViewSet.partial_update()` permite vincular una Factura a una Cotización
vía el campo editable `cotizacion_uuid` (está en `MANUAL_EDITABLE_FIELDS`, a diferencia de `sede`
que NO lo está — este campo SÍ es alcanzable hoy, confirmado). La DSV existente en
`actualizar_factura_limitado()` solo verificaba "la cotización pertenece a la empresa" — nunca
"está dentro del alcance organizacional del usuario". Un perfil con `alcance=SEDE` asignado solo a
Sede A podía vincular su Factura a una Cotización de Sede B (misma empresa) sin restricción.

**Qué se construyó:**
- [selectors.py](../apps/tenant/facturas/services/selectors.py):
  `CotizacionBridge.obtener_cotizacion_por_uuid()`/`.exists_by_uuid()` ganan `sede_ids=None`
  (opcional) — si se pasa y la Cotización tiene una sede fuera del conjunto, se trata como "no
  encontrada" (mismo criterio NULL-safe de F7: `Cotizacion.sede=None` sigue siendo visible).
- [business_service.py](../apps/tenant/facturas/services/business_service.py):
  `actualizar_factura_limitado()` gana `sede_ids=None`, propagado al `CotizacionBridge` en el
  bloque DSV de `cotizacion_uuid`.
- [viewsets.py](../apps/tenant/facturas/api/viewsets.py): `partial_update()` resuelve
  `OrganizationalScope` y pasa `sede_ids`, mismo criterio de degradación de F5/F7/F8.
- [test_scope_bridges_f9.py](../apps/tenant/facturas/tests/test_scope_bridges_f9.py) (nuevo,
  3 tests end-to-end vía API real): alcance SEDE no puede vincular cotización de otra sede,
  SEDE sí puede vincular la suya o una sin sede, EMPRESA puede cualquiera.

**Relación con el adaptador de OCF Fase 7 (`OrganizationalBridge` Protocol en
`apps/tenant/core/services/organizational_bridges.py`) — no tocado:** ese adaptador envuelve
`CotizacionBridge` usando `OrganizationalContext` (no `OrganizationalScope`, por diseño — cero
consumidores reales lo usan hoy, igual que cuando OCF lo cerró). El fix de esta fase se aplicó
directamente al Bridge real (mismo lugar que F7/F8 tocaron selectors/serializers reales), no al
adaptador — consistente con el patrón de toda esta fase de OSF.

**Componentes pendientes:** ninguno para el alcance verificado. Si F13 más adelante migra
`bancos`/`ventas`/`proveedores` (tier 2 de F6) a tener campo `sede`, sus bridges correspondientes
(`BancosBridge`, y un futuro `VentasBridge` si llega a fabricarse) deberían revisarse con el mismo
criterio aplicado aquí.

**Cambios realizados:** 3 archivos de producción modificados de forma aditiva (parámetro nuevo
con default `None` en cada capa), 1 archivo de test nuevo.

**Validaciones ejecutadas (Testing Progresivo por Alcance):** 3 tests end-to-end nuevos vía API
real + `manage.py check` + `ruff check` en los archivos tocados — no se corrió la suite completa
de facturas porque el cambio es aditivo, acotado a un único campo (`cotizacion_uuid`) y ya
verificado end-to-end.

**Checklist:** [x] Los 5 bridges auditados individualmente contra F6 (no genérico) [x] 4/5
bridges correctamente identificados como "no aplica" (evita forzar sede/área donde el dominio no
lo justifica, tal como advierte el documento de recomendación) [x] Hallazgo real en el único
bridge con sustancia [x] Fix aditivo, sin romper la separación Context/Scope de F2 ni tocar el
adaptador de OCF [x] Tests end-to-end reales [x] `manage.py check`/`ruff` limpios
[x] Documentación

**Autorización requerida**

¿Continuar a la Fase F10 (Ventas → Facturas con contexto organizacional — propagar
`OrganizationalScope` a través de `crear_factura_desde_venta()`, el predecesor directo de
`facturas` identificado como candidato de alta prioridad en F6)?

---

## 12. F10 — Ventas → Facturas con contexto organizacional — 🟢 COMPLETA

**Objetivo de la fase:** que una `Factura` generada automáticamente desde una `Venta` (flujo
`VentaBusinessService.procesar_y_facturar_venta()` → `FacturaBusinessService.
crear_factura_desde_venta()`) deje de quedar siempre con `sede=None`, propagando en su lugar el
contexto organizacional de quien factura.

**Auditoría previa:** `Venta` **no tiene** campo `sede` propio (F6 la clasificó como "candidato
plausible sin campo aún") — a diferencia de las 6 apps de F7/F8, aquí no hay nada que migrar a
scope-aware en el selector/serializer de `ventas`. Lo único que existía era un flujo de creación
de `Factura` que nunca recibía ni transportaba ningún dato de sede, sin importar la sede activa de
quien facturaba.

**Decisión de diseño:** dado que `Venta` no tiene `sede`, lo que se transporta no es un campo del
dominio Venta sino el contexto de **quién** está facturando — `OrganizationalContext` (sede
ACTIVA, "dónde estoy ahora"), no `OrganizationalScope` (conjunto total asignado). Es el mismo
criterio que compras usa para defaultear `OrdenCompra.sede` en F5: al crear un registro nuevo sin
campo de sede propio en el dominio origen, se usa el contexto activo del usuario, no su alcance
completo. Se transporta como dato plano dentro del DTO UBL ya existente (`dto["sede_id"]`, mismo
patrón que `cliente_uuid`/`venta_uuid`) — nunca como Foreign Key directa Ventas→Facturas,
preservando el diseño de soft references entre apps.

**Qué se construyó:**
- [apps/tenant/ventas/services/api_mixins.py](../apps/tenant/ventas/services/api_mixins.py):
  `VentaServiceMixin.service_procesar_y_facturar()` resuelve
  `OrganizationalContext.resolve(self.request).sede_id` (degradando a `None` en
  `OrganizationalContextError`) y lo pasa a `procesar_y_facturar_venta(sede_id=...)`.
- [apps/tenant/ventas/services/business_service.py](../apps/tenant/ventas/services/business_service.py):
  `procesar_y_facturar_venta()` y `_construir_dto_factura()` ganan `sede_id: int | None = None`;
  el DTO final incluye `"sede_id": sede_id` junto a `cliente_uuid`/`venta_uuid`.
- [apps/tenant/facturas/services/business_service.py](../apps/tenant/facturas/services/business_service.py):
  `crear_factura_desde_venta()` gana resolución anti-IDOR — `Sede.objects.filter(id=sede_id_dto,
  empresa_id=empresa.id).first()` — un `sede_id` inválido o de otra empresa se ignora en
  silencio (degrada a `sede=None`) en vez de romper la creación de la Factura por un dato de
  contexto secundario.
- [test_scope_ventas_facturas_f10.py](../apps/tenant/facturas/tests/test_scope_ventas_facturas_f10.py)
  (nuevo, 3 tests): propaga `sede_id` válido del DTO; sin `sede_id` queda en `None` (compatibilidad
  con el comportamiento previo, ej. facturación por lote/celery sin usuario activo); un `sede_id`
  inexistente se ignora sin romper la creación (ejercita el mismo camino defensivo que un
  `sede_id` de otra empresa — ver nota siguiente).

**Ajuste de diseño de test frente al plan original:** el test de anti-IDOR originalmente iba a
crear una `Sede` perteneciente a una segunda `Empresa` para probar el filtro
`empresa_id=empresa.id`. Se descubrió en la ejecución que `Empresa` es un **singleton por esquema
de tenant** (`UniqueConstraint` sobre `singleton_key`, `apps/tenant/empresa/models.py:48`) — el
aislamiento entre compañías distintas en este sistema se da por esquema PostgreSQL separado
(`django-tenants`), no por múltiples filas `Empresa` en un mismo esquema. Es arquitectónicamente
imposible crear una segunda `Empresa` real dentro de un mismo test de un solo tenant. El test se
ajustó para usar un `sede_id` inexistente en su lugar, que ejercita exactamente el mismo camino
defensivo (`.filter(id=..., empresa_id=empresa.id).first()` → `None`) sin violar la constraint.

**Componentes pendientes:** ninguno para el alcance de esta fase. F11 revisará `Facturas`
end-to-end (`FacturaSelectors`, `FacturaBusinessService`, `FacturaCRUDService`, etc.) para que
`sede` deje de ser meramente informativa/reporting.

**Cambios realizados:** 3 archivos de producción modificados de forma aditiva (parámetro nuevo con
default `None` en cada capa), 1 archivo de test nuevo.

**Validaciones ejecutadas (Testing Progresivo por Alcance):** 3 tests nuevos (`pytest
apps/tenant/facturas/tests/test_scope_ventas_facturas_f10.py`, 3 passed) + `manage.py check`
(limpio) + `ruff check` en los 4 archivos tocados de esta fase (sin hallazgos nuevos — los 11
errores de import-order/unused-var que ruff reporta en `facturas/services/business_service.py` y
`ventas/services/business_service.py` son preexistentes, confirmado línea por línea contra el
`git diff` de esta fase; no se tocan por estar fuera de alcance, mismo criterio que el bug
preexistente de `logger` no definido detectado en F7/F9). No se corrió la suite completa de
facturas/ventas — cambio aditivo y acotado, ya verificado con tests dedicados end-to-end a nivel
de servicio.

**Nota operativa:** esta fase coincidió con otra sesión de Claude Code ejecutando pytest sobre el
mismo contenedor Docker compartido (incluyendo una tarea en segundo plano para corregir el bug
preexistente de `logger` no definido en `facturas/api/viewsets.py`, delegada desde F7). Ambas
sesiones comparten una única base de datos `test_sintel`, lo que causó varias colisiones
transitorias (`AdminShutdown`, `database does not exist`) durante la verificación — resueltas
esperando a que el proceso `pytest` ajeno terminara antes de reintentar, sin necesidad de cambios
de código. No fue una falla del código de esta fase.

**Checklist:** [x] Confirmado que `Venta` no tiene campo `sede` propio (F6) [x] Contexto
correctamente identificado como `OrganizationalContext` (no `Scope`) — mismo criterio que
`OrdenCompra.sede` en F5 [x] Propagación end-to-end verificada por lectura de código (mixin →
business service → DTO → bridge de creación) [x] Anti-IDOR real (filtro por `empresa_id`) [x] Sin
FK directa Ventas→Facturas — contrato DTO plano preservado [x] 3 tests nuevos, todos pasando
[x] `manage.py check`/`ruff` limpios (hallazgos preexistentes documentados, no corregidos por
estar fuera de alcance) [x] Documentación

**Autorización requerida**

¿Continuar a la Fase F11 (Migrar Facturas — aplicar la arquitectura ya estabilizada:
`FacturaSelectors`, `FacturaBusinessService`, `FacturaCRUDService`, `FacturaInterAppAPI`,
`FacturaViewSet`, `FacturaTableView`, `FacturaSerializer`, `FacturaBridge`,
`crear_factura_desde_venta()` — para que `sede` deje de ser meramente informativa/reporting)?

---

## 13. F11 — Migrar Facturas (empresa+sede+área funcional) — 🟢 COMPLETA

**Objetivo de la fase:** que `sede` en Facturas deje de ser meramente informativa/reporting
(DT-SEDE-02) — revisando `FacturaSelectors`, `FacturaViewSet`, `FacturaTableView` y el camino de
escritura real, para que el alcance organizacional se aplique de forma consistente en TODAS las
acciones, no solo en el listado (F7).

**Auditoría real (2 hallazgos, mismo patrón que compras Bug 1 de F5):**
- **Hallazgo 1 — gap de aislamiento a nivel de objeto:** `FacturaViewSet.get_queryset()` solo
  aplicaba `OrganizationalScope` en la acción `"list"` (F7). Las acciones `retrieve`, `destroy`,
  `partial_update`, `update`, `cambiar_estado`, `vincular_cotizacion`, `vincular_cliente` y
  `vincular_proveedor` solo filtraban por `empresa_id` — un perfil `alcance=SEDE` asignado solo a
  Sede A podía GET/PATCH/DELETE por UUID directo una Factura de Sede B (misma empresa), aunque el
  listado ya se la ocultara.
- **Hallazgo 2 — la grilla HTML real no filtraba nada:** `FacturaTableView.get_queryset()` (la
  vista server-rendered que el usuario efectivamente ve, Fase 5-BIS) llamaba a
  `FacturaSelectors.qs_list()` sin `sede_ids`, mostrando facturas de todas las sedes sin importar
  el alcance — exactamente el mismo patrón que compras Bug 1 (F5), nunca corregido aquí porque F7
  solo tocó el endpoint DRF, no la vista HTML.
- **Hallazgo colateral (dead code confirmado, no un bug nuevo):** `sede` no estaba en
  `MANUAL_EDITABLE_FIELDS` — el DSV de alcance ya escrito en F8
  (`FacturaDetailSerializer.validate()`) era código muerto para escritura, porque el único camino
  de escritura realmente alcanzable (`partial_update` → `actualizar_factura_limitado()`) nunca pasa
  por ese serializer (usa `request.data` directo).

**Qué se construyó:**
- [selectors.py](../apps/tenant/facturas/services/selectors.py): `FacturaSelectors.qs_detail()`
  gana `sede_ids=None` (mismo criterio NULL-safe de F7).
- [api_mixins.py](../apps/tenant/facturas/services/api_mixins.py): `get_qs_detail()` propaga
  `sede_ids`.
- [viewsets.py](../apps/tenant/facturas/api/viewsets.py): `get_queryset()` resuelve
  `OrganizationalScope` **una sola vez** para todas las acciones a nivel de objeto (antes solo
  para `"list"`) y aplica `filter_by_scope_null_safe` (inline, vía `Q`) a
  `retrieve`/`destroy`/`partial_update`/`update`/`cambiar_estado`/`vincular_*`.
- [views.py](../apps/tenant/facturas/views.py): `FacturaTableView.get_queryset()` resuelve
  `OrganizationalScope` y pasa `sede_ids` a `qs_list()` — la grilla HTML ahora respeta el mismo
  alcance que el endpoint DRF.
- [models.py](../apps/tenant/facturas/models.py): `sede` agregado a `MANUAL_EDITABLE_FIELDS`.
- [business_service.py](../apps/tenant/facturas/services/business_service.py):
  `actualizar_factura_limitado()` gana un bloque DSV para `sede` (mismo patrón que
  `cotizacion_uuid`): resuelve UUID o PK (igual que `UUIDOrPKRelatedField`), anti-IDOR por
  `empresa_id`, y verificación estricta (no NULL-safe — aquí se valida la sede DESTINO) contra
  `sede_ids`.
- [serializers.py](../apps/tenant/facturas/api/serializers.py): `FacturaWriteSerializer` gana
  `sede_nombre` (solo lectura) para que la respuesta de PATCH refleje el cambio — la escritura
  real sigue bypaseando el serializer (`request.data` directo), este campo es solo para el payload
  de salida.
- [test_scope_facturas_f11.py](../apps/tenant/facturas/tests/test_scope_facturas_f11.py) (nuevo,
  6 tests): alcance SEDE no puede ver/eliminar por UUID directo una Factura de otra sede; SEDE sí
  puede ver una Factura sin sede (NULL-safe); asignar `sede` dentro del alcance permite el PATCH;
  asignar `sede` fuera del alcance lo rechaza (400); EMPRESA puede ver y editar cualquier sede.

**Componentes explícitamente no tocados en esta fase (por diseño, no por omisión):**
- `FacturaCRUDService` — el `setattr` genérico de `actualizar()` ya funciona sin cambios una vez
  que `update_data['sede']` llega como instancia real de `Sede` (resuelta en business_service.py).
- `create()` (bloqueado, 405 — las facturas solo se crean vía UBL o `crear_factura_desde_venta()`,
  ya cubierto por F10) y `update()` (bloqueado, 405 — inmutabilidad por diseño de negocio) no
  requieren cambios de alcance porque no aceptan escritura alguna.
- `FacturaBridge`/`InventarioItemBridge`/`ClienteBridge`/`ProveedorBridge` — ya auditados
  individualmente en F9, sin sustancia de sede real fuera de `CotizacionBridge` (ya migrado).

**Cambios realizados:** 7 archivos de producción modificados de forma aditiva, 1 archivo de test
nuevo.

**Validaciones ejecutadas (Testing Progresivo por Alcance):** 6 tests nuevos (`pytest
apps/tenant/facturas/tests/test_scope_facturas_f11.py`, 6 passed) + regresión dirigida sobre
`test_scope_selectors_f7.py` (selectors de facturas) — pasan — + `manage.py check` (limpio) +
`ruff check` en los 7 archivos tocados (30 hallazgos preexistentes confirmados línea por línea
contra el `git diff` de esta fase — ninguno cae dentro de un hunk propio; `models.py`,
`api_mixins.py` y `views.py` no tienen ningún hallazgo). El test de aislamiento HTML
(`test_multitenant_isolation_tabla_html.py::test_multitenant_isolation_facturas_tabla_html`) falla
con `assert 302 == 200` — es el mismo riesgo R-6 documentado desde F5 (`force_login()` no persiste
sesión en el test client): el redirect a login ocurre en la capa de autenticación, antes de que
`get_queryset()` (donde viven los cambios de esta fase) se ejecute — no es una regresión. No se
corrió la suite completa de facturas (cambio acotado a un único app, ya verificado con tests
dedicados).

**Checklist:** [x] Auditoría real de las 2 rutas de lectura (DRF list ya migrado en F7 vs. resto de
acciones + grilla HTML, ninguna migrada hasta ahora) [x] Mismo patrón de bug que compras Bug 1 (F5)
confirmado y corregido en ambas rutas (API objeto + HTML) [x] `sede` deja de ser código muerto —
ahora escribible con DSV real (empresa + alcance) en el único camino de escritura alcanzable
[x] NULL-safe para lectura (F7), estricto para asignación de sede destino (consistente con la
semántica de "esto SÍ se puede restringir sin ocultar datos existentes") [x] 6 tests nuevos, todos
pasando [x] `manage.py check`/`ruff` limpios (hallazgos preexistentes documentados) [x]
Documentación

**Autorización requerida**

¿Continuar a la Fase F12 (Contabilidad con contexto organizacional — Pull Model intacto: los
extractores de retenciones ya resuelven `empresa_id`, evaluar si deben propagar `sede_id`/`area_id`
sin que Contabilidad pierda su rol de dueña única del libro contable)?

---

## 14. F12 — Contabilidad con contexto organizacional (Pull Model intacto) — 🟢 COMPLETA

**Objetivo de la fase:** evaluar si Contabilidad (`AsientoContable`, `MovimientoContable`,
`Retencion`, `ConfiguracionRetenciones`, `PeriodoContable`, `CuentaContable`) debe propagar
`sede_id`/`area_id`, sin que pierda su rol de dueña única del libro contable (ADR-001).

**Auditoría real (fase de decisión, no de implementación — mismo patrón que F1/F6):**
- Confirmado por grep exhaustivo: **ningún modelo de Contabilidad tiene campo `sede`/`area` hoy**
  — a diferencia de Facturas (F11), esto no es "informativo sin usar" (DT-SEDE-0X), simplemente no
  existe. Coincide con F6 (tier 2, "candidato plausible sin campo aún").
- Todo `RetencionesService.*` exige `empresa_id` explícito (`ValueError` si falta) — el libro
  contable ya funciona 100% a nivel empresa, nunca a nivel sede. Un Chart of Accounts es por
  empresa, no por sede, en la práctica contable estándar.
- El Pull Model (ADR-001) hace de Contabilidad un agregador genérico: recibe referencias
  (`documento_origen_app`/`modelo`/`id`) desde CUALQUIER app origen sin conocer sus campos de
  negocio. Verificado el flujo real más usado (`FacturaViewSet._build_retenciones_map()` →
  `RetencionesService.totales_retenciones_por_documentos(documento_origen_ids=ids, ...)`): `ids`
  proviene de `self.paginate_queryset(queryset)`, y `queryset` ya es el resultado de
  `get_queryset()` con `OrganizationalScope` aplicado (F7/F11) — el aislamiento organizacional se
  hereda correctamente SIN que Contabilidad necesite saber qué es una "sede".

**Decisión del usuario (pregunta explícita vía `AskUserQuestion`, dos opciones presentadas):**
mantener Contabilidad agnóstica a sede/área — **no se agregan campos nuevos a ningún modelo**. Se
documenta como decisión arquitectónica deliberada, no como trabajo pendiente: la alternativa
(denormalizar `sede_id`/`area_id` como snapshot en `Retencion`) habría requerido duplicar dato que
el propio Pull Model existe para evitar, a cambio de un beneficio marginal (los únicos consumidores
reales ya pre-filtran antes de llamar a Contabilidad).

**Hallazgos colaterales documentados, explícitamente fuera de alcance de F12 (no corregidos aquí):**
- `RetencionViewSet`/`ConfiguracionRetencionesViewSet` (API expuesta directamente, no solo el
  bridge interno) no filtran `get_queryset()` por `empresa_id` en absoluto — **ya documentado
  como deuda técnica preexistente** en `apps/tenant/contabilidad/.agent/AUDITORIA_COMPLETA_CONTABILIDAD.md`
  (hallazgos NUEVO-005/NUEVO-006, "DSV incompleto"). Es un gap de Zero-Trust a nivel empresa, no de
  sede/área — ortogonal a OSF, no se duplica el tracking aquí.
- `GastoViewSet.render_offcanvas_editar()` resuelve el `DocumentoSoporte` objetivo solo por
  `empresa_id` (`get_object_or_404(..., empresa_id=empresa_id)`), sin `OrganizationalScope` —
  mismo patrón de gap que F11 encontró y corrigió en Facturas (acceso a nivel de objeto sin
  chequeo de sede), pero en `gastos`, que aún no tuvo su propia fase de auditoría exhaustiva
  (F7 solo migró su selector `get_list`). Queda señalado para F13 ("Resto de aplicaciones"), no
  corregido aquí por no ser Contabilidad.

**Componentes explícitamente no tocados:** ningún archivo de producción de Contabilidad —
fase de auditoría y decisión pura, cero cambios de código (mismo tipo de cierre que F1/F6).

**Cambios realizados:** ninguno en código de producción. Solo documentación (este archivo +
`MEMORY.md`).

**Validaciones ejecutadas:** no aplica — sin cambios de código, no hay nada nuevo que probar.
`manage.py check` se mantiene limpio por construcción (sin diffs).

**Checklist:** [x] Auditoría exhaustiva de modelos, service layer y ViewSets de Contabilidad
[x] Verificado el flujo real de propagación de scope desde las apps origen (no asumido) [x]
Decisión explícita del usuario vía `AskUserQuestion` entre las 2 alternativas reales [x] Hallazgos
colaterales documentados con referencia cruzada (no duplicados, no corregidos fuera de alcance)
[x] Documentación

**Autorización requerida**

¿Continuar a la Fase F13 (Resto de aplicaciones — una a la vez, empezando por `gastos` dado el
hallazgo colateral de esta fase: `render_offcanvas_editar` sin `OrganizationalScope` a nivel de
objeto)?

---

## 15. F13 — Resto de aplicaciones (una a la vez) — 🟢 COMPLETA (5/5 candidatos fuertes)

**Objetivo de la fase:** aplicar a cada app restante el mismo patrón de auditoría exhaustiva ya
usado en compras (F5) y facturas (F11) — objeto por acción, no solo el listado — "una a la vez"
según el propio nombre de la fase, en vez de un rollout mecánico uniforme.

### 15.1. Sub-fase: `gastos` — 🟢 COMPLETA

**Punto de partida:** hallazgo colateral de F12 — `GastoViewSet.render_offcanvas_editar()`
resolvía su `DocumentoSoporte` objetivo solo por `empresa_id`, sin `OrganizationalScope`.

**Auditoría real (mismo patrón exacto que F11 en Facturas):**
- `GastoServiceMixin` sobrescribía `get_qs_list()` (F7, scope-aware) pero **no** `get_qs_detail()`
  — caía al genérico de `BaseServiceMixin`, que solo filtra por `empresa_id`. Esto afecta
  `retrieve`/`update`/`partial_update`/`destroy`/`anular`, todos resueltos vía `get_object()` →
  `get_queryset()` → `get_qs_detail()`.
- `render_offcanvas_editar()`/`render_offcanvas_detalle()` bypaseaban `get_queryset()` por
  completo con `get_object_or_404(DocumentoSoporte, uuid=..., empresa_id=...)` directo.
- `DocumentoSoporteTableView` (la grilla HTML real, Fase 5-BIS) llamaba `DocumentoSelector.get_list()`
  sin `sede_ids` — mismo patrón de bug que compras Bug 1 (F5) y facturas Hallazgo 2 (F11).
- `render_offcanvas_resolucion()` (sobre `ResolucionDIAN`) se auditó y **no aplica** — confirmado
  por grep que `ResolucionDIAN` no tiene campo `sede` (solo `DocumentoSoporte` lo tiene, DT-SEDE-01).
- Escritura de `sede` ya funcionaba correctamente desde F8: `GastoViewSet` no sobrescribe
  `update()`/`partial_update()`, por lo que el flujo DRF por defecto sí invoca
  `serializer.is_valid()` y el DSV de alcance de F8 es real (a diferencia de facturas) — sin
  cambios necesarios aquí.

**Qué se construyó:**
- [selectors.py](../apps/tenant/gastos/services/selectors.py): `DocumentoSelector.get_detail()`
  gana `sede_ids=None` (NULL-safe, mismo criterio de F7).
- [api_mixins.py](../apps/tenant/gastos/services/api_mixins.py): `GastoServiceMixin.get_qs_detail()`
  override nuevo (mismo patrón que su propio `get_qs_list()` de F7).
- [viewsets.py](../apps/tenant/gastos/api/viewsets.py): `render_offcanvas_editar()`/
  `render_offcanvas_detalle()` usan un nuevo helper `_get_documento_scope_qs()` (resuelve
  `OrganizationalScope` una vez, reusado por ambas acciones) en vez de `get_object_or_404` directo.
- [views.py](../apps/tenant/gastos/views.py): `DocumentoSoporteTableView.get_queryset()` pasa
  `sede_ids` a `DocumentoSelector.get_list()`.
- [test_scope_object_level_f13.py](../apps/tenant/gastos/tests/test_scope_object_level_f13.py)
  (nuevo, 5 tests): SEDE no puede ver por UUID directo ni via offcanvas editar/detalle un
  `DocumentoSoporte` de otra sede; SEDE sí ve uno sin sede (NULL-safe); EMPRESA ve cualquiera.

**Cambios realizados:** 4 archivos de producción modificados de forma aditiva, 1 archivo de test
nuevo.

**Validaciones ejecutadas (Testing Progresivo por Alcance):** 5 tests nuevos (5 passed) +
regresión dirigida sobre `test_scope_selectors_f7.py` de gastos (2 passed, sin romper) +
`manage.py check` (limpio) + `ruff check` en los 4 archivos tocados (5 hallazgos preexistentes de
import-order/unused-import, confirmados fuera de los hunks propios vía `git diff`). No se corrió
la suite completa de gastos.

**Checklist:** [x] Mismo patrón de auditoría objeto-por-acción que F11 [x] `get_qs_detail()`
corregido (afecta 5 acciones a la vez: retrieve/update/partial_update/destroy/anular) [x] Acciones
que bypasean `get_queryset()` (offcanvas) corregidas con un helper reusable [x] Grilla HTML
corregida [x] `ResolucionDIAN` correctamente descartado (sin campo sede) [x] Escritura de `sede`
verificada ya funcional desde F8 (sin cambios) [x] 5 tests nuevos, todos pasando [x]
`manage.py check`/`ruff` limpios [x] Documentación

### 15.2. Sub-fase: `cotizaciones` — 🟢 COMPLETA

**Auditoría real (mismo patrón):**
- `CotizacionServiceMixin.get_qs_detail()` estaba sobrescrito pero **no** pasaba `sede_ids` a
  `CotizacionSelector.get_detail()` — afecta `retrieve`/`update`/`exportar-pdf`/
  `render-offcanvas-editar`/`render-offcanvas-detalle`/`recalcular` (todos vía `get_object()`).
- `ui_views.py` (`CotizacionEditorTemplateView`/`CotizacionDetalleOffcanvasView`, páginas de
  editor/detalle fuera del ViewSet DRF, con URLs propias) resolvían la Cotización objetivo con
  `CotizacionSelector.get_detail_by_uuid(uuid, empresa.id)` directo — mismo patrón que las
  acciones offcanvas de gastos/facturas, pero aquí en vistas HTML puras, no un `@action`.
- No existe `CotizacionTableView` (Fase 5-BIS no llegó a esta app) — no aplica el hallazgo de
  grilla HTML de gastos/facturas.

**Qué se construyó:**
- [selectors.py](../apps/tenant/cotizaciones/services/selectors.py): `get_detail()` y
  `get_detail_by_uuid()` ganan `sede_ids=None` (NULL-safe). `get_detail_by_uuid()` es compartido
  con `CotizacionBridge` (facturas, F9) — ese consumidor sigue sin pasar `sede_ids` (hace su
  propio chequeo post-fetch), comportamiento sin cambios para él.
- [api_mixins.py](../apps/tenant/cotizaciones/services/api_mixins.py): `get_qs_detail()` propaga
  `sede_ids`.
- [ui_views.py](../apps/tenant/cotizaciones/ui_views.py): nuevo helper `_resolve_sede_ids()` en
  `CotizacionTemplateView` (base), reusado por las 2 vistas que resuelven una Cotización por uuid.
- [test_scope_object_level_f13.py](../apps/tenant/cotizaciones/tests/test_scope_object_level_f13.py)
  (nuevo, 4 tests): incluye un test que ejercita `get_detail_by_uuid()` directamente (sin pasar por
  URL/template) para verificar el fix independientemente del enrutamiento de las `TemplateView`.

**Validaciones:** 4 tests nuevos (4 passed) + regresión `test_scope_selectors_f7.py` (2 passed) +
`manage.py check` limpio.

### 15.3. Sub-fase: `inventario` — 🟢 COMPLETA

**Auditoría real:** solo `MovimientoInventario` tiene `sede` (Kardex, DT-SEDE-05) —
Producto/Servicio/ActivoFijo/CategoriaItem/HistorialServicio son catálogo sin concepto de sede
(confirmado F9). `MovimientoInventarioViewSet.get_object()` es un override **custom** (no delega a
`get_qs_detail()` genérico) que llamaba `MovimientoInventarioSelector.get_detail()` solo por
`empresa_id` — afecta `retrieve`/`update`/`partial_update`/`destroy`. La acción
`gestor-offcanvas` (`service_movimiento_get_offcanvas_context()`) tenía el mismo gap.

**Bug real descubierto durante la verificación (no solo el gap de scope):**
`MovimientoInventarioSelector.get_detail()` usa `.get()` sin envolver — un `DoesNotExist` se
propagaba como **500 Internal Server Error**, no 404, porque este `get_object()` custom no pasa
por el `get_object_or_404` que DRF usa internamente. Era invisible antes porque ningún test
intentaba acceder a un Movimiento fuera de alcance/empresa; el nuevo test de esta fase lo
convirtió en una falla real (`AssertionError: 500 != 404`), confirmando que no era solo teórico.
Corregido envolviendo la llamada en `try/except ObjectDoesNotExist` → `NotFound` (DRF).

**Qué se construyó:**
- [selectors.py](../apps/tenant/inventario/services/selectors.py): `MovimientoInventarioSelector.get_detail()`
  gana `sede_ids=None` (NULL-safe).
- [viewsets.py](../apps/tenant/inventario/api/viewsets.py): `get_object()` resuelve
  `OrganizationalScope` y pasa `sede_ids`; envuelto en `try/except ObjectDoesNotExist` → `NotFound`
  (fix del bug 500→404 descrito arriba).
- [api_mixins.py](../apps/tenant/inventario/services/api_mixins.py): `service_movimiento_get_offcanvas_context()`
  resuelve `sede_ids` desde `self.request` (mixin inyectado en el ViewSet) antes de llamar al selector.
- [test_scope_object_level_f13.py](../apps/tenant/inventario/tests/test_scope_object_level_f13.py)
  (nuevo, 4 tests).

**Validaciones:** 4 tests nuevos (4 passed, incluyendo el que atrapó el bug 500) + regresión
`test_scope_selectors_f7.py` (2 passed) + `manage.py check` limpio.

### 15.4. Sub-fase: `proyectos` — 🟢 COMPLETA

**Auditoría real (la más extensa de F13 — 4 puntos de acceso distintos a `Proyecto`, más 2
recursos hijos):**
- `ProyectoViewSet.get_object()` resolvía `qs_detail()` solo por `empresa_id` — afecta
  `retrieve`/`update`/`partial_update`/`destroy`/`cambiar-fase`/`exportar` (todos vía `get_object()`).
- `vincular_proyecto()` (acción que asocia un `HistorialServicio` de inventario a un Proyecto)
  resolvía el Proyecto destino con `get_object_or_404(Proyecto, uuid=..., empresa_id=...)` directo.
- **Hallazgo nuevo de categoría distinta:** `ItemPresupuestoViewSet`/`TareaDiariaViewSet`
  (recursos hijos de `Proyecto`, sin campo `sede` propio, referenciados por `?proyecto_uuid=`) no
  heredaban el alcance del Proyecto padre en absoluto — ni en `get_queryset()` (filtrado por
  query param) ni en `_get_proyecto()` (usado por `perform_create` como gate de autorización). Un
  perfil alcance=SEDE podía listar/crear items de presupuesto y tareas diarias de un Proyecto de
  otra sede. Corregido con un `Q(proyecto__sede_id__isnull=True) | Q(proyecto__sede_id__in=sede_ids)`
  (join a través de la FK, NULL-safe) — mismo principio que Empleado hereda de sede/área, pero
  aplicado vía relación en vez de campo directo.
- `ProyectoTableView` (grilla HTML, Fase 5-BIS) llamaba `qs_list()` sin `sede_ids` — mismo patrón
  de bug que compras/facturas/gastos.

**Qué se construyó:**
- [selectors.py](../apps/tenant/proyectos/services/selectors.py): `qs_detail()` gana
  `sede_ids=None`.
- [viewsets.py](../apps/tenant/proyectos/api/viewsets.py): `ProyectoViewSet.get_object()` y
  `vincular_proyecto()` resuelven `sede_ids`; `ItemPresupuestoViewSet`/`TareaDiariaViewSet` ganan
  un helper `_get_sede_ids()`/uso inline, aplicado en `get_queryset()` (join) y `_get_proyecto()`.
- [views.py](../apps/tenant/proyectos/views.py): `ProyectoTableView.get_queryset()` pasa
  `sede_ids`.
- [test_scope_object_level_f13.py](../apps/tenant/proyectos/tests/test_scope_object_level_f13.py)
  (nuevo, 4 tests, incluye uno que verifica que items de presupuesto de un Proyecto fuera de
  alcance quedan invisibles vía `?proyecto_uuid=`).

**Componentes explícitamente no tocados (documentado, no un descuido):** `TareaCortaViewSet`
(vinculado a Empleado, no directamente a Proyecto en el mismo sentido) no se auditó a este nivel
de profundidad en esta fase — queda para una revisión futura si se decide profundizar en esa
relación.

**Validaciones:** 4 tests nuevos (4 passed) + regresión `test_scope_selectors_f7.py` (2 passed) +
`manage.py check` limpio.

### 15.5. Sub-fase: `empleados` — 🟢 COMPLETA

**Auditoría real:** único candidato fuerte con **ambos** campos (`sede` Y `area`).
`EmpleadoServiceMixin` sobrescribía `get_qs_list()` (F7) pero no `get_qs_detail()` — mismo gap
exacto que gastos, afectando `retrieve`/`update`/`partial_update`/`destroy` de `EmpleadoViewSet`.
`EmpleadoTableView` (grilla HTML) tampoco aplicaba `sede_ids`/`area_ids`.

**Componentes explícitamente no tocados (decisión de alcance, no descuido):** `Contrato`/
`Devengo`/`ResolucionDIAN`/`LiquidacionPrestacion` (recursos de nómina vinculados a Empleado) no
tienen campo `sede`/`area` propio y **nunca** filtraron por el alcance del Empleado padre (a
diferencia de Proyecto→ItemPresupuesto, esto no es una regresión de esta fase sino un estado
preexistente desde antes de F7). Extenderles el mismo patrón de join (`empleado__sede_id`)
implicaría auditar 4 ViewSets + 6 TableViews adicionales del dominio de nómina — se documenta como
alcance futuro (posible F13 adicional o fase dedicada), no se ejecuta aquí para mantener esta
fase acotada al mismo nivel de profundidad que las demás sub-fases.

**Qué se construyó:**
- [selectors.py](../apps/tenant/empleados/services/selectors.py): `EmpleadoSelector.get_detail()`
  gana `sede_ids=None`/`area_ids=None` (NULL-safe, ambos).
- [api_mixins.py](../apps/tenant/empleados/services/api_mixins.py): `EmpleadoServiceMixin.get_qs_detail()`
  override nuevo (mismo patrón que su `get_qs_list()` de F7).
- [views.py](../apps/tenant/empleados/views.py): `EmpleadoTableView.get_queryset()` pasa
  `sede_ids`/`area_ids`.
- [test_scope_object_level_f13.py](../apps/tenant/empleados/tests/test_scope_object_level_f13.py)
  (nuevo, 3 tests).

**Validaciones:** 3 tests nuevos (3 passed) + regresión `test_scope_write_validation_f8.py`
(3 passed) + `manage.py check` limpio.

---

### Cierre de F13

Con `empleados` completada, los 6 "candidatos fuertes" de F6 (facturas, cotizaciones, gastos,
inventario, proyectos, empleados) tienen ahora el mismo nivel de auditoría objeto-por-acción
(no solo listado). Los candidatos de tier 2 (`ventas` ya resuelto vía F10 sin campo propio,
`contabilidad` decidido agnóstico en F12, `bancos`/`proveedores` sin campo `sede` aún) quedan
fuera del alcance de F13 por la misma razón que Contabilidad en F12 — no hay nada que auditar a
nivel de objeto sin un campo `sede` que filtrar.

**Cambios totales de F13 (5 sub-fases):** 19 archivos de producción modificados de forma aditiva
(parámetro opcional nuevo o helper nuevo en cada uno, ningún código existente reescrito), 5
archivos de test nuevos (20 tests). Un bug real preexistente descubierto y corregido
(`MovimientoInventarioViewSet` 500→404).

**Validaciones ejecutadas (Testing Progresivo por Alcance, agregado):** 20 tests nuevos (20/20
passed) + regresión dirigida sobre 5 archivos de test de F7/F8 existentes (12/12 passed, sin
romper nada) + `manage.py check` limpio en cada sub-fase + `ruff check` con hallazgos
exclusivamente preexistentes (import-order/unused-imports, confirmados fuera de los hunks propios
vía `git diff` en cada sub-fase). No se corrió la suite completa de ninguna app — cambios
aditivos y acotados, ya verificados con tests dedicados por sub-fase.

**Checklist de cierre:** [x] Los 6 candidatos fuertes de F6 auditados a nivel de objeto (no solo
listado) [x] Mismo patrón de bug recurrente (grilla HTML sin scope) encontrado y corregido en
gastos/proyectos, ya conocido de compras (F5) y facturas (F11) [x] Un gap de categoría nueva
(recursos hijos sin campo propio, herencia via join) identificado y corregido en proyectos
(ItemPresupuesto/TareaDiaria) [x] Un bug real preexistente (500 en vez de 404) descubierto y
corregido en inventario [x] Límites de alcance documentados explícitamente donde no se profundizó
(empleados→nómina) en vez de dejarlos sin mencionar [x] 20 tests nuevos, todos pasando [x]
`manage.py check`/`ruff` limpios en las 5 sub-fases [x] Documentación

**Autorización requerida**

¿Continuar a la Fase F14 (Pruebas de aislamiento organizacional — suite de tests dedicada,
transversal a las 6 apps candidatas fuertes, que verifique el aislamiento SEDE/ÁREA de punta a
punta como cierre formal antes de F15/F16)?

---

## 16. F14 — Pruebas de aislamiento organizacional — 🟢 COMPLETA

**Objetivo de la fase:** cierre formal transversal — una suite de tests dedicada que verifique el
aislamiento SEDE/ÁREA de punta a punta en las 6 apps candidatas fuertes, en vez de asumir que la
cobertura dispersa de F7-F13 ya cubre todos los invariantes reales.

**Auditoría previa (agente de exploración dedicado, solo lectura, sobre TODOS los archivos
`test_scope*.py` existentes):** confirmó 3 invariantes de `OrganizationalScope` verificados a
nivel unitario desde F2 (`apps/tenant/core/tests/test_organizational_scope.py`) pero **nunca
end-to-end contra un endpoint real de ninguna de las 6 apps**:

1. **Perfil `alcance=SEDE` con CERO sedes asignadas** → `OrganizationalScope.resolve()` debe
   devolver `sede_ids=frozenset()` (no `None`) y por lo tanto el usuario debe ver SOLO los
   registros sin sede (NULL-safe), nunca los de una sede ajena — "restringe a nada, no a todo"
   (decisión de diseño de F2). Todos los tests F7/F13 de las 6 apps asignaban exactamente una
   sede; ninguno probó el caso de cero asignaciones contra un endpoint real.
2. **Perfil asignado a DOS sedes simultáneamente** → debe ver registros de AMBAS, no solo la
   primera. El caso de dos sedes sí estaba probado (F2, F5-piloto en compras — app excluida del
   alcance de F7-F13), pero nunca contra ninguna de las 6 apps candidatas fuertes.
3. **`alcance=AREA` a nivel de OBJETO (retrieve por UUID) en `empleados`** — F7 solo probó AREA en
   el listado; F13 solo probó SEDE a nivel de objeto. La combinación AREA+retrieve nunca se había
   verificado (única de las 6 apps con campo `area`).

**Qué se construyó:** un archivo nuevo `test_scope_isolation_f14.py` en cada una de las 6 apps
(mismo patrón de convención `test_scope_*_fXX.py` ya establecido, en vez de un archivo monolítico
central — permite reusar los fixtures/modelos propios de cada app):
- [facturas](../apps/tenant/facturas/tests/test_scope_isolation_f14.py),
  [cotizaciones](../apps/tenant/cotizaciones/tests/test_scope_isolation_f14.py),
  [gastos](../apps/tenant/gastos/tests/test_scope_isolation_f14.py),
  [inventario](../apps/tenant/inventario/tests/test_scope_isolation_f14.py),
  [proyectos](../apps/tenant/proyectos/tests/test_scope_isolation_f14.py): 2 tests cada uno
  (cero-sedes-asignadas → solo NULL-safe; dos-sedes-asignadas → ve ambas, no una tercera) — 10
  tests.
- [empleados](../apps/tenant/empleados/tests/test_scope_isolation_f14.py): los mismos 2 tests de
  sede + 2 tests nuevos de `alcance=AREA` a nivel de objeto (retrieve de otra área → 404; retrieve
  de su propia área → 200) — 4 tests.

**Componentes explícitamente no tocados:** ningún archivo de producción — fase 100% de tests
nuevos, cero cambios de código (los invariantes ya estaban implementados correctamente desde F2/F7;
esta fase los prueba end-to-end, no los corrige).

**Complicación operativa durante esta fase (no de código):** ejecutar 2+ archivos de test en un
mismo comando `pytest` disparó repetidamente una colisión de `schema_name='test'` en
`tenants_client` (`UniqueViolation`) — distinta de las colisiones de `test_sintel` completo vistas
en fases anteriores. Se resolvió ejecutando cada uno de los 6 archivos por separado (un comando
`pytest` por app), patrón más confiable ya usado exitosamente en fases previas ante la
inestabilidad del entorno compartido de test.

**Cambios realizados:** 0 archivos de producción, 6 archivos de test nuevos (14 tests).

**Validaciones ejecutadas (Testing Progresivo por Alcance):** 14 tests nuevos, ejecutados
individualmente por app (2+2+2+2+2+4=14, 14/14 passed) + `manage.py check` limpio + `ruff check`
limpio en los 6 archivos nuevos (sin hallazgos, al ser archivos nuevos sin deuda heredada). No se
corrió la suite completa de ninguna app.

**Checklist:** [x] Auditoría previa confirmó los 3 gaps reales antes de escribir código (no
asumidos) [x] Mismo patrón de convención de archivos que F7-F13 (reusa fixtures existentes) [x]
Cubre las 6 apps candidatas fuertes, no un subconjunto [x] Cubre el caso frozenset() (cero
asignaciones) nunca antes probado end-to-end [x] Cubre visibilidad multi-sede nunca antes probada
en estas 6 apps [x] Cubre AREA a nivel de objeto en empleados, el único gap de combinación
alcance/acción que quedaba sin probar [x] 14 tests nuevos, todos pasando [x] `manage.py
check`/`ruff` limpios [x] Documentación

**Autorización requerida**

¿Continuar a la Fase F15 (Knowledge Graph organizacional — post-estabilización)?

---

## 17. F15 — Knowledge Graph organizacional (post-estabilización) — 🟢 COMPLETA

**Objetivo de la fase:** verificar que el Enterprise Knowledge Graph (EKG, `tools/ekg/`) refleja
con precisión la arquitectura de alcance organizacional ya estabilizada en F0-F14 — mismo criterio
que F6 estableció ("verificar con `make ekg-dry-run`, si se confirma que ya captura todo, no se
escribe ningún extractor nuevo"). Fase de verificación, no de construcción.

**Auditoría real (agente de exploración dedicado, solo lectura, más 2 comandos EKG ejecutados
para obtener el estado actual en vez de confiar en dumps potencialmente desactualizados):**

1. **El extractor ya captura `sede`/`area` automáticamente, sin código nuevo** — confirmado leyendo
   `extract_python.py`: cualquier asignación a nivel de clase en `models.py` se convierte en un
   nodo `Field` + arista `HAS_FIELD` (y `REFERENCES` si es FK), sin importar el nombre del campo.
   No hay ni hubo que escribir extracción específica para `sede`/`area` — funciona igual que para
   cualquier otro campo, tal como F6 predijo para `compras`.
2. **Hallazgo real — dumps desactualizados:** el dump commiteado `tools/ekg/out/core.json` era
   anterior a los cambios de esta misma sesión en `organizational_scope.py`/
   `organizational_filters.py` — cualquiera que corriera `governance --offline` o `impact.py`
   contra los dumps commiteados obtenía una foto incompleta de `core`. **Corregido**: re-extraídos
   `core` + las 6 apps candidatas fuertes (`ekg-dry-run` por cada una) para reflejar el estado
   post-F14.
3. **Hallazgo real — blind spot confirmado, no corregido (mismo criterio de alcance que F6):**
   `organizational_filters.py` (los helpers `filter_by_context`/`filter_by_scope`/
   `filter_by_scope_null_safe`, núcleo de F5/F7) es **invisible al grafo** — son funciones a nivel
   de módulo, y `extract_services()` solo extrae clases (limitación documentada de forma más
   amplia en `tools/ekg/PILOT_REPORT.md`, no específica de este archivo). `organizational_scope.py`
   y `organizational_context.py` SÍ son visibles (ambos declaran sus clases principales como
   clases, capturadas sin cambios). Extender el extractor para funciones a nivel de módulo es un
   ítem de roadmap ya existente y de alcance mucho más amplio que esta fase — no se construye aquí,
   consistente con el criterio de F6 de no escribir extractores nuevos salvo necesidad confirmada.
4. **Hallazgo real — regla de gobernanza `sede_or_area_field_without_sede_aware_model` (OCF Fase
   11) falla para las 6 apps candidatas fuertes** (`facturas.Factura`, `tenant_cotizaciones.Cotizacion`,
   `tenant_empleados.Empleado`, `tenant_gastos.DocumentoSoporte`, `tenant_inventario.MovimientoInventario`,
   `tenant_proyectos.Proyecto`) — ninguna hereda `SedeAwareModel` (ADR-003), a pesar de que ahora
   tienen alcance organizacional completamente funcional (F7-F13). **Evaluado y NO corregido
   deliberadamente**: `SedeAwareModel` fue diseñado para el patrón estricto de `compras` (`sede`
   `NOT NULL`, filtrado estricto); las 6 apps candidatas fuertes usan intencionalmente
   NULL-safe (decisión de usuario en F7, porque el 100% de los datos reales tiene `sede=NULL`
   hoy) — forzar la herencia de `SedeAwareModel` implicaría cambiar la declaración del campo
   (`null`/`blank`) en 6 modelos, generando migraciones con riesgo real de romper el
   comportamiento NULL-safe ya validado extensamente en F7-F14. Es una decisión arquitectónica
   real (cambiar código de producción y esquema de BD), no una tarea de "grafo de conocimiento" —
   fuera del alcance de F15, documentado aquí para una futura fase dedicada si se decide perseguir.
5. **Hallazgo colateral, no relacionado con OSF:** `viewsets_without_service_layer: 23` sigue
   fallando — ya estaba triado como conocido en `tools/ekg/PILOT_REPORT.md` antes de esta fase, sin
   relación con sede/área. No se toca aquí.
6. **Hallazgo colateral de higiene documental:** el encabezado de progreso de este mismo documento
   (líneas 16-38) seguía diciendo "Fase actual: F9" con F10-F16 marcadas "NO INICIADA", pese a que
   el cuerpo del documento ya tenía F10-F14 cerradas — nadie lo había actualizado en 5 fases.
   Corregido.

**Qué se construyó:** ningún cambio de código de producción ni de extractor — se re-generaron 7
dumps (`core` + las 6 apps) con `ekg-dry-run`, se re-corrió `ekg-governance --offline` para
confirmar el estado real, y se corrigió el encabezado desactualizado de este documento.

**Componentes explícitamente no tocados (decisiones de alcance, no descuidos):** extractor de
funciones a nivel de módulo (`organizational_filters.py`), herencia de `SedeAwareModel` en las 6
apps candidatas fuertes, `viewsets_without_service_layer` (ya triado, sin relación con OSF).

**Cambios realizados:** 0 archivos de código de producción. 7 dumps EKG regenerados
(`tools/ekg/out/{core,facturas,cotizaciones,gastos,inventario,proyectos,empleados}.json`), 1
corrección de documentación (encabezado de este archivo).

**Validaciones ejecutadas:** `ekg-dry-run` para 7 apps (sin errores) + `ekg-governance --offline`
ejecutado sobre los dumps refrescados (2912 nodos, 4587 aristas) — confirma que
`sede`/`area` se capturan automáticamente sin extractor nuevo, y que los 2 hallazgos de gobernanza
relacionados con OSF son reales pero fuera de alcance de esta fase (decisiones arquitectónicas
separadas, no tareas de grafo).

**Checklist:** [x] Confirmado que el extractor ya captura `sede`/`area` sin cambios (mismo
resultado predicho por F6) [x] Dumps desactualizados detectados y corregidos [x] Blind spot de
funciones a nivel de módulo confirmado y documentado (no corregido, alcance mayor) [x] Regla de
gobernanza `sede_or_area_field_without_sede_aware_model` evaluada explícitamente y su fix
correctamente diferido (cambio de esquema de BD, no de grafo) [x] Encabezado desactualizado del
plan maestro corregido [x] Documentación

**Autorización requerida**

¿Continuar a la Fase F16 (Gobernanza automática ampliada — cierre final del proyecto OSF)?

---

## 18. F16 — Gobernanza automática ampliada — 🟢 COMPLETA (cierre del proyecto OSF)

**Objetivo de la fase (según el documento fuente, "FASE 16 — GOBERNANZA AUTOMÁTICA"):** "construir
reglas que detecten" una lista de 12 violaciones arquitectónicas. Última fase del proyecto.

**Auditoría real — mapeo exhaustivo del wishlist original contra lo que `tools/ekg/governance.py`
(motor construido en OCF Fase 7) ya implementa, lo que F14 ya cubre en runtime, y lo que es
genuinamente nuevo y factible sin extractor nuevo:**

| Item del wishlist original | Estado |
|---|---|
| Modelo con empresa pero sin sede cuando debería tenerla | Ya implementado — `sede_or_area_field_without_sede_aware_model` (OCF Fase 11) |
| Bypass del Service Layer | Ya implementado — `viewsets_without_service_layer` (OCF Fase 7) |
| Query sin scope / Service ignorando sede / Usuario accediendo a sede no autorizada / Área fuera de la sede permitida / DTO inter-app sin contexto | **Cubierto en runtime, no en el grafo** — exactamente los invariantes que la suite de F14 (`test_scope_isolation_f14.py` + `test_scope_object_level_f13.py` + `test_scope_facturas_f11.py`, etc.) verifica end-to-end. El propio módulo de gobernanza ya declina por principio ("never claim a check the graph cannot back up") cualquier check que dependa del cuerpo de un método en tiempo de ejecución — son comportamiento, no relaciones estructurales entre nodos. |
| Bridge sin aislamiento (a nivel semántico) | Cubierto en runtime — F9 (`test_scope_bridges_f9.py`) |
| Ventas → Facturas sin contexto | Cubierto en runtime — F10 (`test_scope_ventas_facturas_f10.py`) |
| **Import circular** | **Genuinamente nuevo y factible — implementado en esta fase** |
| FK cross-app indebida | Evaluado — el patrón real de este proyecto (Bridges/Soft References vía UUID, nunca FK directa) hace que una violación de este tipo ya sería detectada indirectamente por el patrón de import circular arriba, si alguna vez ocurriera a nivel de import; no se construyó una regla separada de "FK apuntando a otra app" porque el proyecto nunca usa FKs cross-app reales (verificado en F9: los 5 Bridges existentes resuelven por UUID, no por FK) |

**Qué se construyó:** `find_import_cycles_between_tenant_apps()` (nueva, `tools/ekg/governance.py`)
— detecta ciclos en las aristas `IMPORTS` App→App que `extract_services()` ya poblaba (imports
`apps.tenant.<otra_app>` dentro de `services/`) — cero extractor nuevo, DFS de 3 colores estándar
sobre datos ya existentes. Añadida al sweep de `run()`.

**Hallazgo real al correr la regla nueva contra el grafo completo (2912 nodos, 4587 aristas):**
2 ciclos reales, ambos entre `core`/`empresa`/`perfil` (las 3 apps fundacionales del sistema):
```
core -> empresa -> perfil -> core
empresa -> perfil -> empresa
```
**Investigado antes de reportar como violación** (inspección directa de las aristas subyacentes,
no solo el nombre de la app): los 4 imports reales son `core→empresa.models.Empresa`,
`empresa→perfil.models.TenantProfile`, `perfil→core.services.membership.check_membership_by_schema`
(el patrón de Bridge *correcto*, exactamente lo que AGENTS.md §17 recomienda), y
`perfil→empresa.models.Area`. **Los 4 son imports de *modelos*, ninguno de una clase de Service** —
una forma de acoplamiento materialmente distinta (y mucho más común/aceptable en Django, donde
FKs cross-app a través de referencias de modelo son estándar) que el acoplamiento
Service-a-Service que el patrón de Bridge/Soft-Reference existe para prevenir entre apps de
dominio de negocio pares (facturas↔gastos, no core↔empresa↔perfil). **No corregido
deliberadamente**: refactorizar el acoplamiento entre las 3 apps fundacionales del sistema es un
cambio arquitectónico real y riesgoso, fuera de alcance de una fase de gobernanza — documentado
como hallazgo evaluado, no como bug, con una nota en el propio código de la regla señalando que
una versión futura podría distinguir ciclos de Modelo vs. ciclos de Service (solo estos últimos
serían una violación real del patrón de Bridge).

**Componentes explícitamente no tocados:** ningún extractor (`extract_python.py` sin cambios),
ninguna app de producción, el acoplamiento core/empresa/perfil encontrado (ver arriba).

**Cambios realizados:** 1 archivo de producción de tooling (`tools/ekg/governance.py`, aditivo:
1 función nueva + 1 entrada en el dict de `run()`), 1 archivo de test (`tools/ekg/tests/test_governance.py`,
2 tests nuevos).

**Validaciones ejecutadas:** `python -m tools.ekg.governance --offline` ejecutado limpio contra
el grafo completo (2912 nodos/4587 aristas) — confirma que la regla nueva funciona y reporta con
precisión; suite completa de tests de EKG (`tools/ekg/tests/`, 69→71 tests) 71/71 pasan (10→12 de
gobernanza específicamente); `ruff check` limpio en ambos archivos tocados (1 hallazgo propio
—Yoda condition— corregido antes de cerrar, no dejado como deuda).

**Checklist:** [x] Wishlist original de F16 mapeado exhaustivamente ítem por ítem contra lo ya
implementado/cubierto en runtime/genuinamente nuevo [x] Nueva regla construida sin extractor
nuevo, reusando datos ya poblados [x] Regla ejecutada contra el grafo real, no solo probada en
sintético [x] Hallazgo real investigado a nivel de arista antes de juzgarlo (Modelo vs. Service)
[x] Decisión de no corregir documentada con criterio explícito, no silenciada [x] Tests nuevos
(sintético + real) — ambos pasan [x] `ruff`/suite de tests de EKG limpios [x] Documentación

**Cierre del proyecto OSF (F0-F16, las 17 fases):** el Organizational Scope Framework completa
aquí su ciclo de vida completo — desde auditar el estado real de ADR-003 (F0) hasta gobernar
automáticamente la arquitectura que construyó (F16). Las 6 apps candidatas fuertes (facturas,
cotizaciones, gastos, inventario, proyectos, empleados) tienen ahora: selectors NULL-safe
scope-aware (F7), business services con DSV de alcance (F8), bridges migrados donde aplica (F9),
propagación de contexto entre apps (F10), auditoría objeto-por-acción completa (F11/F13), una
suite de tests de aislamiento dedicada (F14), un grafo de conocimiento que refleja la arquitectura
con precisión (F15), y gobernanza automática ampliada con una regla nueva de detección de ciclos
(F16). Las decisiones arquitectónicas deliberadamente diferidas a lo largo del proyecto (Contabilidad
agnóstica a sede en F12, herencia de `SedeAwareModel` en las 6 apps en F15, nómina de empleados
sin herencia de alcance en F13, acoplamiento core/empresa/perfil en F16) quedan documentadas como
decisiones evaluadas y conscientes, no como trabajo pendiente sin registrar.

---

## 19. Rollback

**F0:** no aplica (solo lectura, sin cambios de código; el único artefacto es el documento
`ORGANIZATIONAL_SCOPE_BASELINE.md`, eliminarlo revierte el 100%).

**F1:** trivial — revertir la sección de la tabla de ADRs en `arquitectura_general.md` §7 a su
estado anterior. Ningún archivo `docs/ADR-*.md` fue renombrado ni movido.

**F2:** trivial — eliminar `apps/tenant/core/services/organizational_scope.py` y
`apps/tenant/core/tests/test_organizational_scope.py`. Ningún archivo de producción existente fue
modificado, por lo que no hay nada más que revertir.

**F4:** no trivial de revertir a nivel de datos (la Área "General" creada en `shelltest1` ya
existe en la BD real), pero de bajo riesgo: el código puede revertirse restaurando el chequeo
original de `asegurar_estructura_organizacional_inicial()`/`backfill_sede_area.py`; la fila de
Área creada de más se puede eliminar manualmente si se decidiera que no debía existir (no hay
ningún dato de negocio dependiendo de ella todavía, `shelltest1` es un tenant de prueba ad-hoc).

**F5:** moderado — son 8 archivos de producción de una sola app (`compras`), todos revertibles
independientemente. El cambio de mayor riesgo de revertir sería el de `get_qs_list()`/
`OrdenCompraTableView` (volver a filtrar por una sola sede, o sin filtro en la tabla HTML) —
revertirlo reintroduce el Bug 1 documentado arriba, no romper nada nuevo. Ningún dato existente se
modificó (los bugs eran de lógica de filtrado/validación, no de datos).

**F6:** trivial — eliminar `documentacion/ORGANIZATIONAL_SCOPE_MATRIX.md`. Documento puro, cero
código de producción tocado.

**F7:** moderado — 12 archivos de producción en 6 apps distintas, todos revertibles
independientemente app por app (cada selector/viewset es autocontenido). Revertir reintroduce el
comportamiento de "sin scoping" que ya existía antes de esta fase (no rompe nada nuevo, ningún
dato existente fue modificado — los cambios son de lógica de filtrado, no de datos).

**F8:** trivial — 1 archivo de servicio compartido (2 funciones nuevas, sin tocar código
existente) + 5 serializers con un bloque aditivo idéntico cada uno en `validate()`. Revertir
reintroduce el gap de "DSV de empresa sí, de alcance organizacional no" que ya existía antes de
esta fase — no rompe nada nuevo (2 de las 5 apps ni siquiera tienen el flujo de escritura
alcanzable hoy, per lo verificado en esta misma fase).

**F9:** trivial — 3 archivos de producción, un único parámetro opcional (`sede_ids=None`) añadido
en cada capa. Revertir reintroduce el gap de "vincular Factura a Cotización de otra sede" que ya
existía antes de esta fase — no rompe nada nuevo.

**F10:** trivial — 3 archivos de producción, un único parámetro opcional (`sede_id=None`) añadido
en cada capa (mixin → business service de ventas → business service de facturas). Revertir
reintroduce el comportamiento previo ("Factura generada desde Venta siempre queda con
`sede=None`") que ya existía antes de esta fase — no rompe nada nuevo, ningún dato existente fue
modificado (los cambios son de lógica de creación, no de datos).

**F11:** moderado — 7 archivos de producción en una sola app (`facturas`), todos revertibles
independientemente. El de mayor riesgo de revertir es el de `FacturaViewSet.get_queryset()`/
`FacturaTableView.get_queryset()` (volver a filtrar solo por `empresa_id` en retrieve/destroy/
partial_update/etc. y en la grilla HTML) — reintroduce los 2 gaps de aislamiento documentados
arriba, no rompe nada nuevo. Sacar `sede` de `MANUAL_EDITABLE_FIELDS` revierte la capacidad de
asignar sede vía PATCH sin afectar ningún otro campo. Ningún dato existente fue modificado (los
cambios son de lógica de filtrado/validación, no de datos).

**F12:** no aplica (fase de auditoría y decisión pura, cero código de producción modificado — el
único artefacto es la actualización de este documento y de `MEMORY.md`).

**F13 (5 sub-fases):** trivial-moderado — 19 archivos de producción en 5 apps distintas, todos
revertibles independientemente sub-fase por sub-fase (cada una es aditiva: parámetro opcional
nuevo o helper nuevo, ningún código existente reescrito). Revertir cualquier sub-fase reintroduce
los gaps de aislamiento documentados en esa sub-fase — no rompe nada nuevo. Única excepción a
"aditivo puro": el fix del bug 500→404 en `MovimientoInventarioViewSet.get_object()` (inventario) —
revertirlo junto con el resto de la sub-fase reintroduce el 500 preexistente (no es una regresión,
es volver al estado de antes de F13). Ningún dato existente fue modificado en ninguna sub-fase.

**F14:** no aplica (fase 100% de tests nuevos, cero código de producción modificado — el único
artefacto es eliminar los 6 archivos `test_scope_isolation_f14.py` si se decidiera revertir).

**F15:** no aplica (fase de verificación pura, cero código de producción ni de extractor
modificado — los únicos artefactos son 7 dumps JSON regenerables en cualquier momento con
`make ekg-dry-run APP=<app>` y la corrección del encabezado de este documento).

**F16:** trivial — 1 archivo de tooling (`tools/ekg/governance.py`), un único cambio aditivo (1
función nueva + 1 entrada en un dict). Revertir solo elimina la regla `import_cycles_between_tenant_apps`
del sweep de gobernanza — no afecta ningún código de producción de la aplicación ni ningún dato.

**F3:** trivial — revertir el bloque `"scope"` agregado en
`ContextoOrganizacionalView.get()` (`apps/tenant/core/api/contexto.py`) y el método `to_dict()`
agregado a `OrganizationalScope`. Ambos son estrictamente aditivos (ningún campo de respuesta
existente cambió), por lo que revertirlos no afecta a ningún consumidor actual del endpoint.
