# Contrato Definitivo — OrganizationalScope vs OrganizationalContext

**Fecha:** 2026-08-09
**Estado de la fase (FASE 3):** 🟢 COMPLETED — cero codigo modificado
**Base de este documento:** sintesis de `documentacion/OCF_TECHNICAL_AUDIT.md` (FASE 1) y `documentacion/OSF_TECHNICAL_AUDIT.md` (FASE 2). No introduce conceptos nuevos — formaliza por escrito lo que el codigo ya implementa y ya decidio, para que quede en un unico lugar citable en vez de disperso en docstrings.

**Regla de nomenclatura (impuesta por el usuario, no discutible en esta fase):** no crear `TenantContext`, `CompanyContext`, `ScopeContext`, `BusinessContext`, `OrganizationContext` ni ningun otro nombre que duplique estos dos conceptos. Todo lo que necesite "contexto organizacional" en el resto del proyecto debe usar `OrganizationalContext` u `OrganizationalScope`, nunca inventar un tercero.

---

## 1. Definicion de una linea

| Concepto | Responde | Analogia |
|---|---|---|
| `OrganizationalContext` | "¿Donde estoy PARADO ahora mismo?" | Una posicion GPS: un unico punto |
| `OrganizationalScope` | "¿Que territorio TOTAL tengo permitido pisar?" | El poligono de un mapa: un conjunto de puntos |

`OrganizationalContext` = **EXECUTION CONTEXT** (contexto de ejecucion de un request/operacion puntual).
`OrganizationalScope` = **AUTHORIZATION BOUNDARY** (limite de autorizacion del perfil, independiente de que se esté ejecutando algo ahora).

**Nunca fusionar.** Motivo verificado con codigo real, no teorico (ver `OSF_TECHNICAL_AUDIT.md` §3.2): un perfil con `sedes_asignadas=[Bogota, Barranquilla]` y `sede_activa` de sesion = Bogota ve, en el mismo request, **1 sola sede** via `OrganizationalContext.filter()` y **2 sedes** via `OrganizationalScope.filter()`. Si se fusionaran en una sola clase, uno de los dos comportamientos se perderia necesariamente.

---

## 2. `OrganizationalContext` — Execution Context

**Definicion:** contexto organizacional efectivo de una ejecucion (request/tarea) concreta: `Tenant -> Empresa -> Sede activa -> Area activa -> Usuario -> Perfil -> Rol -> Alcance -> Timezone -> Configuracion`.

### 2.1 Quien lo crea

`OrganizationalContext.resolve(request)` (`apps/tenant/core/services/organizational_context.py:112-180`) — **unico** punto de creacion. No hay constructor publico alternativo pensado para uso normal (el `__init__` generado por `@dataclass` existe, pero ningun consumidor lo llama directamente fuera de los propios tests — todo el codigo de produccion pasa por `.resolve()`).

### 2.2 Quien lo resuelve

- Directamente: `ContextoOrganizacionalView.get()` (`apps/tenant/core/api/contexto.py:56`), via `OrganizationalContextMixin.get_organizational_context()`.
- Indirectamente (opt-in, sin uso real todavia — ver `OCF_TECHNICAL_AUDIT.md` §1): cualquier ViewSet/vista que herede `OrganizationalContextMixin` y llame `self.get_organizational_context()`. **14 ViewSets heredan el mixin; cero lo invocan hoy** (ver auditoria FASE 1).

### 2.3 Quien puede modificarlo

**Nadie, directamente** — es un `@dataclass(frozen=True)`, inmutable por diseno (`organizational_context.py:41`). No existe ni debe existir un `context.sede_id = X`.

La UNICA forma de cambiar lo que un `OrganizationalContext` resolvera en la PROXIMA llamada a `.resolve()` es cambiar el estado que alimenta la resolucion:
- `request.session['sede_activa_id']` — mutado exclusivamente por `ContextoSedeView.post()` (`apps/tenant/core/api/contexto.py:78-122`), tras verificar DSV (sede pertenece a la empresa + esta en `sedes_asignadas` si `alcance != EMPRESA`).
- `TenantProfile.rol`/`.alcance`/`.sedes_asignadas`/`.areas_asignadas` — mutados por el flujo normal de gestion de perfiles (`perfil` app), fuera del alcance de OCF/OSF.

### 2.4 Que contiene (los 11 campos, ninguno mas)

`tenant_schema`, `tenant_id`, `empresa_id`, `sede_id` (activa, puede ser `None`), `area_id` (**siempre `None` hoy** — no existe algoritmo de "area activa", ver §2.6), `user_id`, `perfil_id`, `rol`, `alcance`, `timezone`, `configuracion`.

### 2.5 Que NO contiene (limites explicitos, no omisiones accidentales)

- **No contiene el conjunto de sedes/areas permitidas** — eso es responsabilidad exclusiva de `OrganizationalScope` (§3). `OrganizationalContext.filter(Model)` filtra solo por la sede/area ACTIVA, nunca por el conjunto — ver la advertencia explicita en el docstring de `organizational_scope.py:25-39` sobre por que un selector real NUNCA debe llamar `context.filter()` para listar (debe usar `scope.filter()`).
- **No contiene `area_id` resuelto** — ninguna app define hoy un algoritmo de "area activa" (equivalente a `resolve_sede_activa_id`); inventar uno sin un caso de uso real violaria la regla de no fabricar infraestructura especulativa que el propio proyecto se ha impuesto en cada fase anterior.
- **No contiene permisos ni verificaciones** — no decide si el usuario PUEDE hacer algo, solo describe DONDE esta parado. Las decisiones de autorizacion viven en `OrganizationalScope`/`HasOrganizationalScope`/`OrganizationalPermission`.

### 2.6 Consumidores confirmados

Ver `OCF_TECHNICAL_AUDIT.md` §1 — resumen: `ContextoOrganizacionalView` (produccion real), 14 ViewSets (mixin heredado, sin invocar), tests.

---

## 3. `OrganizationalScope` — Authorization Boundary

**Definicion:** el conjunto TOTAL de `sede_ids`/`area_ids` que un perfil tiene permitido tocar, sin colapsar a una posicion "activa".

### 3.1 Quien lo crea

`OrganizationalScope.resolve(request)` (`apps/tenant/core/services/organizational_scope.py:131-181`) — unico punto de creacion, deliberadamente **independiente** de `OrganizationalContext.resolve()` (no lo llama, no depende de que se resuelva primero ni despues — decision explicita documentada en el modulo, linea 135-141).

### 3.2 Quien lo resuelve

En produccion: llamado **directamente** (no via `OrganizationalScopeMixin`, que existe pero no tiene ninguna herencia real, ver `OCF_TECHNICAL_AUDIT.md` §2) desde `services/api_mixins.py`, `api/viewsets.py` y `views.py` de `compras`, `cotizaciones`, `empleados`, `facturas`, `gastos`, `inventario`, `proyectos`, `ventas` — ~20 sitios de llamada, sin cache entre llamadas del mismo request (riesgo de N+1 ya documentado en `OCF_TECHNICAL_AUDIT.md` §2).

### 3.3 Quien puede modificarlo

**Nadie, directamente** — tambien `@dataclass(frozen=True)`. Lo que alimenta su resolucion (`TenantProfile.alcance`/`.sedes_asignadas`/`.areas_asignadas`) se modifica por el flujo normal de gestion de perfiles, igual que en §2.3 — `OrganizationalScope` no tiene un endpoint equivalente a `ContextoSedeView` (no existe "cambiar mi scope activo": el scope no tiene un componente "activo", es el conjunto completo siempre).

### 3.4 Que contiene

`empresa_id`, `alcance`, `sede_ids` (`frozenset[int] | None`), `area_ids` (`frozenset[int] | None`) — 4 campos, deliberadamente menos que `OrganizationalContext` porque no describe una posicion de ejecucion, solo un limite.

### 3.5 Que NO contiene

- No contiene `sede_id`/`area_id` singular — nunca colapsa el conjunto a un solo valor "activo" (esa es exactamente la responsabilidad que `OrganizationalContext` cubre y `OrganizationalScope` deliberadamente no).
- No contiene `user_id`/`perfil_id`/`rol`/`timezone`/`configuracion` — no es un reemplazo de `OrganizationalContext`, es un objeto mas pequeño y de un solo proposito (autorizacion).

### 3.6 Consumidores confirmados

Ver `OSF_TECHNICAL_AUDIT.md` §2-§6 — resumen: 8 apps de negocio en produccion real (el componente de OCF/OSF con mayor adopcion), `HasOrganizationalScope` (semanticamente equivalente pero **no** instancia `OrganizationalScope` directamente — reimplementa el mismo query `perfil.sedes_asignadas.filter(id=sede_id).exists()` inline en vez de llamar `OrganizationalScope.resolve(request).permits_sede(sede_id)` — ver riesgo en §7 de este documento).

---

## 4. Que consume cada pieza vecina (mapa de dependencias, verificado)

### 4.1 Que consume `TenantProfile`

Fuente unica de verdad para `rol`, `alcance`, `sedes_asignadas`, `areas_asignadas`, `empresa_id` (via FK). **Ni `OrganizationalContext` ni `OrganizationalScope` lo reemplazan** — ambos LEEN de `TenantProfile` en su `.resolve()`, ninguno escribe en el, ninguno cachea sus valores mas alla de la vida de la instancia resuelta (un `OrganizationalContext`/`OrganizationalScope` resuelto en el request N no refleja un cambio de `alcance` hecho a mitad del request N — hay que resolver de nuevo, lo cual es automatico porque no persisten entre requests).

### 4.2 Que consume `OrganizationalScope`

- `Selectors` de las 8 apps de negocio (§3.6) — via `filter_by_scope()`/`filter_by_scope_null_safe()` (`organizational_filters.py`), pasando `scope.sede_ids`/`scope.area_ids` como parametros (nunca el objeto completo — los helpers son funciones puras que reciben ids, no `OrganizationalScope`, ver `organizational_filters.py:34-56`).
- `Serializers` (validate()) — via los helpers `sede_esta_en_alcance()`/`area_esta_en_alcance()` (`organizational_scope.py:201-231`), que internamente llaman `OrganizationalScope.resolve(request).permits_sede/area()`.

### 4.3 Que consume el Service Layer (BusinessService/CRUDService)

**Nada de OCF/OSF directamente, hoy.** El unico adaptador (`organizational_service_layer.py`, Fase 8 OCF) que conecta un `OrganizationalContext` con un Business Service real (`OrdenCompraBusinessService.crear_orden_compra`) es codigo de demostracion sin consumidor de produccion (ver `OCF_TECHNICAL_AUDIT.md` §7). Los Business Service de las 17 apps siguen recibiendo `empresa`/`sede` como objetos ya resueltos por el ViewSet/Selector, no un `OrganizationalContext` empaquetado.

### 4.4 Que consumen los Selectors

Ya cubierto en §4.2 — `filter_by_context()` (una sola sede/area, piloto `compras`), `filter_by_scope()` (conjunto estricto, `compras`), `filter_by_scope_null_safe()` (conjunto con NULL visible, `facturas` y otras 5 apps con datos historicos en NULL).

### 4.5 Que consumen los Bridges

**Nada en produccion.** Los 3 `*OrganizationalBridge` (Cotizacion/Cliente/Proveedor) son adaptadores construidos y probados sin consumidor real (ver `OCF_TECHNICAL_AUDIT.md` §5) — los 6 consumidores reales de los bridges originales (`bancos`, `proyectos`, `gastos`, `empleados`, `proveedores`, `contabilidad`) siguen llamando los bridges reales con `empresa_id` suelto, no via el adaptador `OrganizationalContext`-aware.

---

## 5. Diagrama de flujo (texto, verificado contra codigo real — no aspiracional)

```
request HTTP (JWT o Session)
        |
        v
request.user.tenant_profile  <-- TenantProfile (SSoT de rol/alcance/asignaciones)
        |
        +----------------------------------------+
        |                                        |
        v                                        v
OrganizationalContext.resolve(request)   OrganizationalScope.resolve(request)
  (posicion activa: 1 sede/area)          (limite total: conjunto de sedes/areas)
        |                                        |
        v                                        v
  usado hoy solo por:                    usado hoy por:
  - ContextoOrganizacionalView            - Selectors de 8 apps (filter_by_scope*)
    (GET /core/contexto/, sin             - Serializers.validate() (sede_esta_en_alcance)
    consumidor JS todavia)                - (semanticamente, no textualmente)
  - OrganizationalContextMixin              HasOrganizationalScope.has_object_permission
    (heredado en 14 ViewSets,               (reimplementa la misma query inline)
    nunca invocado)
```

---

## 6. Verificacion de la regla de nomenclatura

`grep -rn "class.*Context\b\|class.*Scope\b" apps/tenant/core/services/ apps/tenant/api/` confirma que las unicas clases con estos sufijos en todo el proyecto son `OrganizationalContext`, `OrganizationalContextMixin`, `OrganizationalContextError`, `OrganizationalScope`, `OrganizationalScopeMixin`, `OrganizationalScopeError` — ningun `TenantContext`/`CompanyContext`/`ScopeContext`/`BusinessContext` fue introducido en ninguna fase anterior. Regla respetada hasta la fecha; este documento no la modifica, solo la registra como verificada.

---

## 7. Hallazgo nuevo de esta fase: `HasOrganizationalScope` no usa `OrganizationalScope`

**No detectado explicitamente en FASE 1/2** (se noto ahi que `HasOrganizationalScope` es "semanticamente equivalente" a `OrganizationalScope`, pero al formalizar el contrato de "que consume que" en esta fase queda claro que es una **reimplementacion paralela**, no un consumo real):

- `HasOrganizationalScope.has_object_permission()` (`apps/tenant/api/permissions.py:182-195`) escribe su propia consulta: `sede_id is not None and perfil.sedes_asignadas.filter(id=sede_id).exists()`.
- `OrganizationalScope.permits_sede()` (`organizational_scope.py:76-85`) hace exactamente lo mismo pero contra un `frozenset` ya resuelto: `sede_id is not None and sede_id in self.sede_ids`.
- Son **dos implementaciones independientes de la misma regla**, escritas en fases distintas (`HasOrganizationalScope` es ADR-003, anterior a `OrganizationalScope`/OSF). No es la "fuente de verdad paralela" que el prompt maestro prohibe expresamente para `TenantProfile`/roles/permisos (`HasOrganizationalScope` SI lee de `TenantProfile` como unica fuente de datos) — pero SI es logica de autorizacion duplicada que podria divergir si una de las dos cambia sin la otra (mismo patron de riesgo que la triplicacion de `empresa_id` documentada en FASE 1).
- **No se corrige en esta fase** (FASE 3 es solo "definir el contrato", igual que FASE 2 dejo la correccion de `OrganizationalContext.filter()` para FASE 7) — se dejar documentado aqui para que una fase de implementacion futura decida si `HasOrganizationalScope` debe reescribirse para llamar `OrganizationalScope.resolve(request).permits_sede(sede_id)` en vez de reimplementar la query.

---

## 8. Resumen para las fases siguientes

- **FASE 4 (ADR Governance):** debe reflejar que OCF/OSF tienen codigo real y probado, pero con adopcion real limitada a: sede activa (header/sesion), `OrganizationalScope` en 8 apps, y los helpers `filter_by_scope*`. Todo lo demas (DSV generalizado, Bridges, Service Layer adapter, `OrganizationalContextMixin` en si, `OrganizationalPermission`) es infraestructura construida sin consumidor de produccion.
- **FASE 5 (Matriz Global de Cobertura):** no debe marcar una app "COMPLETA" solo por heredar `OrganizationalContextMixin` — debe distinguir "hereda el mixin" de "invoca `get_organizational_context()`" (ver §2.6).
- **FASE 6 (Piloto compras):** debe agregar el test que falta para `HasOrganizationalScope.has_object_permission()` (ver `OSF_TECHNICAL_AUDIT.md` §4/§8) antes de dar el piloto por completamente validado.
- **FASE 10 (Rollout):** antes de aplicar `HasOrganizationalScope` a una app nueva, resolver la asimetria NULL documentada en `OSF_TECHNICAL_AUDIT.md` §4 y, si se decide, la unificacion de §7 de este documento.

---

## Cierre de FASE 3

Ningun archivo de codigo funcional fue modificado. Documento creado: `documentacion/ORGANIZATIONAL_CONTRACT.md` (este archivo).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
