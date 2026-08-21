# UX Access Context — Auditoría FASE 0/1/2

**Fecha:** 2026-08-21. **Fase:** 0 (Descubrimiento) + 1 (Contrato) + 2 (Gap
Analysis) de la misión "User Experience Access Context". **Estado del
código en esta fase: sin modificar** — este documento es 100% lectura y
análisis, tal como exige la FASE 0 de la misión.

---

## 0. Hallazgo que gobierna todo lo demás (leer esto primero)

Antes de proponer nada nuevo, la búsqueda obligatoria de "infraestructura
existente" (Regla Absoluta #4 de esta misión) encontró que **el "User
Experience Access Context" que esta misión pide ya fue construido por una
misión anterior**, el 2026-08-09 (12 días antes de esta), bajo los nombres
`OrganizationalContext` y `OrganizationalScope` (OCF/OSF). Es infraestructura
real, probada, con 5 commits ya en el historial de git
(`0295932`..`34fc020`, ver `documentacion/FASE11_CONSOLIDACION_GIT.md`), no
un documento de diseño sin ejecutar.

**Dos restricciones explícitas de esa misión anterior, impuestas por el
usuario, siguen vigentes y aplican directamente a esta nueva misión:**

1. **Regla de nomenclatura (no discutible):** *"no crear `TenantContext`,
   `CompanyContext`, `ScopeContext`, `BusinessContext`, `OrganizationContext`
   ni ningun otro nombre que duplique estos dos conceptos... usar
   `OrganizationalContext` u `OrganizationalScope`, nunca inventar un
   tercero."* (`ORGANIZATIONAL_CONTRACT.md` línea 7). La FASE 4 de esta
   nueva misión propone crear `Sintel.UserContext` — **esto es aceptable
   SOLO si `Sintel.UserContext` es un cliente/cache frontend que CONSUME
   los datos de `OrganizationalContext`/`OrganizationalScope` vía el
   endpoint ya existente, nunca una reimplementación paralela de la lógica
   de resolución de contexto o de autorización.**
2. **Gate de autorización explícito, repetido en cada documento de cierre
   de fase de esa misión:** *"Fase completada. No iniciar la siguiente fase
   hasta recibir autorización explícita del usuario."* (`ORGANIZATIONAL_CONTRACT.md`
   línea 174, mismo patrón en `FASE10`/`FASE11`). La única vez que esa
   misión avanzó varias fases seguidas sin pausar fue bajo la instrucción
   explícita del usuario *"termina la tarea en su totalidad"* — y aun así
   la ejecución de los commits de git (la acción más difícil de revertir)
   se dejó pendiente de una confirmación **separada**.

**Implicación para esta misión:** dado que esta nueva misión es, en la
práctica, la continuación directa de esa misma iniciativa (llevar OCF/OSF
al frontend, que es exactamente lo que esa misión anterior dejó pendiente
— ver §2), y dado que las reglas de esa misión anterior siguen escritas en
el propio código/documentación del proyecto sin haber sido revocadas, este
documento completa la FASE 0-2 (análisis, sin tocar código, tal como pide
esta misión) y **se detiene ahí para reportar este hallazgo antes de
escribir cualquier línea de código**, en vez de asumir que la instrucción
"no pedir autorización" de esta nueva misión anula el gate explícito de la
misión anterior sobre el mismo subsistema.

---

## 1. Matriz: qué existe hoy, dónde vive, quién lo usa

| Dato | Fuente real (modelo) | Endpoint | Servicio/resolución | Consumidores confirmados | Estado |
|---|---|---|---|---|---|
| `user_id`, `user_email`, etc. | `auth.User` (schema public) | `GET /api/v1/perfil/perfiles/me/` | `PerfilCRUDService.get_or_initialize_profile` | `perfil.page.js` (tabla de usuarios) | ✅ Completo |
| `rol` (ADMIN/OPERADOR/VISOR) | `TenantProfile.rol` | `/me/` (campo `rol`) **y** `/core/contexto/` (campo `rol`) | Ambos leen `TenantProfile` directo | Ambos endpoints, ninguna UI de navegación | ✅ Dato completo, ⚠️ sin consumidor de navegación |
| `permissions_context` (can_edit_users, can_delete_users, can_assign_roles, can_create_profiles, is_owner) | Calculado en `perfil/api/permissions.py:get_permissions_context()` | `/me/` (campo `permissions_context`) | — | `perfil.page.js` (botones de la tabla de usuarios) | ✅ Completo, pero **alcance limitado a gestión de usuarios**, no es un permiso general de módulos/acciones de negocio |
| `tenant_id`, `tenant_schema` | `django_tenants` (conexión activa) | `/core/contexto/` únicamente | `OrganizationalContext.resolve()` | Ninguna UI todavía (ver §0) | ✅ Dato completo, ❌ sin consumidor |
| `empresa_id` | `TenantProfile.empresa_id` | `/core/contexto/` (y de forma indirecta en `/me/` vía relaciones, no expuesto directo) | `OrganizationalContext.resolve()` | Ninguna UI todavía | ✅ Dato completo, ❌ sin consumidor directo |
| `sede_id` **activa** (singular) | `request.session['sede_activa_id']`, mutado por `POST /api/v1/core/contexto/sede/` | `/core/contexto/` (campo `sede_id`) | `OrganizationalContext.resolve()` | `sede_selector.js` (dropdown del header, YA FUNCIONA -- cambia la sesión y recarga la página) | ✅ Completo y con consumidor real |
| `area_id` **activa** | Campo existe en `OrganizationalContext`, **siempre `None` hoy** | `/core/contexto/` (campo `area_id`, siempre null) | No existe algoritmo de "área activa" (documentado explícitamente como límite, no omisión) | Ninguno | ❌ No implementado -- deliberado, sin caso de uso todavía |
| `sede_ids`/`area_ids` **conjunto completo permitido** | `TenantProfile.sedes_asignadas`/`.areas_asignadas` (M2M) | `/core/contexto/` (bloque `scope`) | `OrganizationalScope.resolve()` | Selectors de 8 apps de negocio (backend, filtrado de listas) | ✅ Completo en backend, ❌ sin consumidor frontend (ningún selector de sede/área en formularios usa este conjunto para poblar opciones) |
| `alcance` (EMPRESA / SEDE / AREA) | `TenantProfile.alcance` | `/core/contexto/` (campo `alcance` y dentro de `scope.alcance`) | Ambos resolvers | Backend únicamente | ✅ Completo, ❌ sin traducción a UX ("¿qué significa mi alcance?" no se explica en ningún lado del frontend) |
| Enforcement objeto-a-objeto (`HasOrganizationalScope`) | `apps/tenant/api/permissions.py:182-195` | N/A (permission class de DRF, no endpoint) | Reimplementación paralela de `OrganizationalScope.permits_sede()` (ver `ORGANIZATIONAL_CONTRACT.md` §7 -- riesgo ya documentado, no corregido) | Solo `compras` (piloto) en producción real | 🟡 Parcial -- ver §2, deliberadamente no aplicado a 6 apps por riesgo de regresión NULL |
| **Módulos permitidos por rol** (qué apps ve un VISOR vs un ADMIN en el sidebar) | **No existe ningún modelo/campo para esto** | **No existe endpoint** | **No existe servicio** | **N/A** | ❌ **Inexistente por completo -- gap real confirmado por grep, cero resultados para cualquier variante de "modulos_permitidos"/"allowed_modules"** |
| **Acciones permitidas por módulo** (inventario.create/view/delete tipo FASE 8 de la misión) | No existe un concepto genérico -- cada app resuelve sus propios botones vía `permission_classes` de DRF, sin exponer la matriz completa a la UI | N/A | N/A | Cada app oculta/muestra botones con lógica propia, no centralizada | ❌ Inexistente como concepto centralizado (existe de forma implícita y dispersa en 16 `permissions.py` distintos) |

---

## 2. Gap Analysis (P0–P3)

### P0 — Seguridad / aislamiento

**Ya identificado y documentado por la misión anterior, no es un hallazgo
nuevo de esta auditoría:** `HasOrganizationalScope.has_object_permission()`
deniega objetos con `sede_id=None`, pero `filter_by_scope_null_safe()` (el
filtro de listado) SÍ los deja visibles. Aplicar el permiso de objeto a las
6 apps que ya filtran listas (`facturas`, `inventario`, `gastos`,
`empleados`, `cotizaciones`, `proyectos`) causaría que un usuario vea un
registro en la tabla pero reciba 403 al abrirlo — el 100% de los registros
históricos de esas apps tiene `sede=NULL`. **Diferido deliberadamente por
la misión anterior, sigue diferido hoy.** No se toca en esta fase.

**Nuevo, confirmado en esta auditoría:** el sidebar actual (`workspace.html`,
FASE 3 de la misión UX de esta misma sesión) muestra los 15 módulos a
**cualquier** `IsTenantMember`, sin distinguir `rol`. Esto es
**presentación, no seguridad** — cada endpoint individual ya valida su
propio `permission_classes` (confirmado: `PerfilViewSet` usa
`IsTenantMember`/`IsTenantProfileAdmin` según la acción, y así cada app) —
así que un VISOR que hace clic en "Contabilidad" y ve la UI no puede
realmente escribir nada (el backend lo bloquea), pero SÍ ve una UI que
sugiere capacidades que no tiene. No es una vulnerabilidad (Regla Absoluta
#3 de esta misión: "backend = autoridad definitiva", ya se cumple), pero es
exactamente el tipo de confusión de UX que esta misión busca resolver.

### P1 — Funcionamiento

- `ContextoOrganizacionalView` (`GET /api/v1/core/contexto/`) existe,
  funciona, devuelve exactamente la forma que la FASE 6-9 de esta misión
  necesita (tenant/empresa/sede/area/rol/alcance/scope) — **pero ningún JS
  lo consume todavía**. Este es el gap real y accionable de mayor prioridad.
- No existe traducción de "módulos permitidos por rol" a la navegación. El
  sidebar es estático para todos.
- `area_id` activa nunca se resuelve (siempre `None`) — no bloquea nada hoy
  porque ninguna app usa "área activa" como filtro operativo todavía, pero
  sí significa que la FASE 9-11 de esta misión (selección automática de
  sede/área única) solo puede implementarse para **sede**, no para área,
  sin construir primero el algoritmo de área activa (fuera del alcance
  mínimo, sin caso de uso confirmado — mismo criterio que la misión
  anterior aplicó consistentemente).

### P2 — UX

- El usuario no tiene, en ningún lugar de la UI, una respuesta visible a
  "¿en qué sede estoy trabajando ahora?" más allá del selector del header
  (que sí existe y funciona). No hay indicación de "área actual" (consistente
  con que el backend tampoco la resuelve) ni de "alcance" (¿por qué veo
  todas las sedes o solo la mía?).
- `permissions_context` de `/me/` es específico de gestión de usuarios
  (`can_edit_users`, etc.) — no sirve como fuente para "qué puedo hacer en
  Inventario", que es lo que la FASE 8 de esta misión pide. Confirmar esto
  evita el error de intentar extender `permissions_context` para un
  propósito que no es el suyo (violaría la Regla Absoluta #4 de "revisar
  antes de crear", en el sentido de que ya sabemos que este campo no es la
  pieza correcta para reutilizar en ese caso específico).

### P3 — Mejora futura (no priorizar sin caso de uso)

- Área activa (algoritmo equivalente a `resolve_sede_activa_id`).
- Extender `contabilidad`/`bancos`/`proveedores` con sede real (ya
  ratificado como "candidato sin caso de uso confirmado" por la misión
  anterior, FASE 10).
- Unificar `HasOrganizationalScope` para que llame
  `OrganizationalScope.permits_sede()` en vez de reimplementar la query
  (hallazgo de `ORGANIZATIONAL_CONTRACT.md` §7, sin corregir).

---

## 3. Recomendación para FASE 3 (no ejecutada todavía — solo la evidencia)

**No extender `/me/`.** `/me/` y `/core/contexto/` responden preguntas
distintas y ambas son necesarias, no redundantes:

- `/me/` = "¿quién soy y qué puedo hacer con OTROS usuarios?" (identidad +
  gestión de perfiles).
- `/core/contexto/` = "¿dónde estoy parado (tenant/empresa/sede/área) y
  cuál es mi límite total de alcance?" (ejecución + autorización
  organizacional).

El "Access Context" que pide esta misión es la **unión** de ambos, no una
extensión de uno sobre el otro. La opción de menor riesgo y cero
duplicación es que el futuro `Sintel.UserContext` (FASE 4) haga **2
llamadas en paralelo** (`/me/` + `/core/contexto/`) en la carga inicial del
workspace y las combine en un solo objeto en memoria — exactamente el
patrón "una carga inicial, memoria temporal" que la FASE 4 de esta misión
ya pide, sin inventar un tercer endpoint (cumple la Regla Absoluta #4 y la
instrucción explícita de la FASE 3 de no crear `/access-context/` si algo
existente puede cumplir esa función — aquí son 2 "algo existente", no uno,
pero sigue siendo cero endpoints nuevos).

**Lo que SÍ falta y no existe en ningún lado (candidato real a construir,
no a reutilizar):** el mapa "rol → módulos permitidos" para generar la
navegación dinámica de la FASE 7. Esto no es una duplicación de nada
existente porque nada existente resuelve esta pregunta hoy.

---

## 4. Riesgos identificados para las fases siguientes

1. **Alto volumen / alto radio de impacto:** esta misión, en su forma
   completa (FASE 3-26), toca potencialmente las 16 apps, navegación
   global, y — si se llega a aplicar `HasOrganizationalScope` a más apps —
   comportamiento de autorización en producción. Es una diferencia
   cualitativa frente a la misión UX de esta misma sesión (solo
   presentación/templates).
2. **El gate de autorización de la misión anterior sigue sin revocar.** Este
   documento no lo revoca por su cuenta.
3. **Construir `Sintel.UserContext` mal** (como una reimplementación en vez
   de un cliente delgado de `/me/` + `/core/contexto/`) recrearía
   exactamente el problema que la Regla Absoluta #1 de esta misión prohíbe
   y que la misión anterior ya previno con su regla de nomenclatura.

---

## 5. Checklist FASE 0-2 (autoevaluación contra lo pedido)

- [x] Leída arquitectura general, AGENTS.md (contexto ya cargado en sesión).
- [x] Leída documentación Perfil (`AUDITORIA_FLUJO_PERFIL.md`, actualizada
      esta misma sesión) y Core (`ORGANIZATIONAL_CONTRACT.md` y anexos).
- [x] Analizado código real: `PerfilViewSet.me()`, `permissions.py`,
      `ContextoOrganizacionalView`, `ContextoSedeView`,
      `OrganizationalContext`/`OrganizationalScope`.
- [x] Confirmadas las respuestas REALES de `/me/` y `/core/contexto/` vía
      Django test Client (no asumidas, ver §1).
- [x] Matriz Dato/Fuente/Endpoint/Servicio/Consumidores/Estado construida.
- [x] Gap analysis P0-P3 completado.
- [x] Documento creado en `documentacion/ux/UX_ACCESS_CONTEXT_AUDIT.md`.
- [ ] Knowledge Graph / EKG consultado formalmente (herramienta
      `tools/ekg/` existe en el proyecto; no se ejecutó en esta pasada --
      la evidencia de código real vía lectura directa + test Client ya
      resolvió las preguntas de FASE 0 sin necesidad de correrlo; queda
      disponible si una fase futura de implementación lo requiere para
      impact analysis de FASE 17).
- [x] **Cero código modificado en esta fase.**

**Estado de esta fase: 🟢 COMPLETED.**

**Siguiente paso propuesto, pendiente de confirmación del usuario dado el
hallazgo de §0:** si se autoriza continuar, FASE 3 sería trivial (no
extender nada, ya está todo servido por 2 endpoints existentes) y FASE 4
empezaría el trabajo real: un `Sintel.UserContext` delgado en
`apps/tenant/core/static/core/js/common/`, que haga las 2 llamadas ya
existentes y las combine en memoria, más el mapa rol→módulos (la única
pieza genuinamente nueva) para la navegación dinámica de FASE 7.
