# F34_core_AUDIT — Auditoria integral de negocio/arquitectura (app 1/16)

Mision F34 (`documentacion/audits/apps/F34_MASTER_STATUS.md`). Distinta
de la auditoria previa ya cerrada (`documentacion/audits/apps/
APP_core_AUDIT.md`, `APP_AUDIT_MASTER_FINAL.md`) -- reutiliza sus
hallazgos como base confirmada y profundiza en angulos nuevos: reglas
de negocio clasificadas, mapa de dominio, N+1 real (no solo
sospechado), frontend estructural.

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## Resumen ejecutivo

`core` es infraestructura compartida, no un dominio de negocio propio:
SSoT de modelos base multi-tenant, resolucion de contexto
organizacional (empresa/sede/area), middleware de excepciones,
gateway publico (`_apps/`), shell de UI del workspace. Consumida por
las 16 apps privadas. En la auditoria previa (F33-style) se
eliminaron 1271 lineas de codigo muerto (5 adaptadores huerfanos) y
se confirmo un fix de seguridad (traceback ya no se filtra al
cliente). Esta pasada (F34) investiga con evidencia nueva 2 items que
habian quedado como sospecha/deferred: el presunto N+1 en las
llamadas `organizational_*`, y el estado del frontend de
`workspace.html` (previamente marcado "no re-auditado"). **Ambos se
resuelven aqui con evidencia: el N+1 NO se confirma (arquitectura
correcta), y el frontend SI esta modernizado (342 lineas, logica
extraida a `workspace.js`, no la version monolitica de 900+ lineas
descrita en documentos historicos de 2025).**

## FASE 1 — Reglas de negocio (clasificadas)

`core` no tiene reglas de negocio transaccionales (no factura, no
calcula dinero) -- sus "reglas de negocio" son reglas arquitectonicas
que SI tienen consecuencias de negocio directas (aislamiento
multi-tenant, seguridad):

| Regla | Clasificacion | Evidencia | Consecuencia si se viola |
|---|---|---|---|
| Todo modelo tenant hereda `SintelTenantBaseModel` con FK `empresa` obligatorio | **CRITICAL** | `apps/tenant/core/models.py` | Fuga de datos cross-tenant |
| El traceback de excepciones nunca se filtra al cliente API, ni con `DEBUG=True` | **CRITICAL** | `middleware.py` (fix ya verificado en auditoria previa) | Filtracion de rutas de servidor/internals via API publica |
| El rol se resuelve via `TenantProfile.rol` (schema tenant), nunca `TenantMembership.rol` (schema public) | **CRITICAL** | Hallazgo heredado de F33.15-B, re-confirmado | Autorizacion incorrecta si se lee la fuente equivocada |
| `OrganizationalContext`/`OrganizationalScope` solo aplican fallback de empresa sin `TenantProfile` cuando `settings.DEBUG=True` | **IMPORTANT** | `organizational_context.py:139`, `organizational_scope.py:153` | Si se desactivara el guard `DEBUG`, cualquier usuario sin perfil operaria sobre la primera empresa del schema -- IDOR critico. Guard confirmado presente en ambos modulos. |
| Resolucion de Sede activa: sesion -> primera sede asignada al perfil -> Sede "Principal" de la empresa | **IMPORTANT** | `sede_context.py:resolve_sede_activa_id()` | Determina que datos ve el usuario en apps con alcance SEDE/AREA |
| `OrganizationalContext` y `OrganizationalScope` resuelven `empresa_id` de forma duplicada e independiente a proposito (no se acoplan entre si) | **SUPPORTING** (decision arquitectonica documentada) | Docstring explicito en `organizational_scope.py:135-141` | Ninguna si se mantiene la duplicacion intencional; un intento de "simplificar" consolidando ambos violaria una decision explicita del usuario |
| `OrganizationalContext.timezone` usa siempre `settings.TIME_ZONE` global (no existe timezone por empresa/perfil) | **DERIVED** | `organizational_context.py:174-178`, comentario explicito | Ninguna -- documentado como ausencia de fuente real, no un bug |
| Gateway `_apps/` en dominio publico permite invocar endpoints tenant desde `home.sintel.net.co` | **SUPPORTING** | ADR-002 | Rompe el dual-registration si se agrega un endpoint solo en un lado |
| `workspace.html`/`workspace.js` -- shell de UI del dashboard privado | **PRESENTATIONAL** | `templates/tenant/core/workspace.html` | Sin impacto de negocio directo |

## FASE 2 — Mapa de dominio

`core` no define entidades de negocio propias -- provee **abstracciones**
que otras apps instancian:

- **Entidad abstracta:** `SintelTenantBaseModel` (campos `empresa`,
  `created_at`, `updated_at`; sin tabla propia).
- **Value object de request:** `OrganizationalContext` (tenant_schema,
  tenant_id, empresa_id, sede_id, area_id, user_id, perfil_id, rol,
  alcance, timezone, configuracion) -- resuelto una vez por request,
  inmutable tras `resolve()`.
- **Value object de request (independiente):** `OrganizationalScope`
  (empresa_id, alcance, sede_ids frozenset, area_ids frozenset) --
  usado para filtrar querysets (`scope.filter(Model)`).
- **Transiciones/estados:** ninguno propio -- `core` no modela ciclos
  de vida de negocio.
- **Invariantes reales:** "un usuario autenticado sin `TenantProfile`
  en el tenant actual no puede resolver contexto/scope fuera de
  `DEBUG=True`" (verificado, ver FASE 1).

Dado que `core` es pura infraestructura sin entidades de negocio, las
Fases 3 (modelo)/12 (codigo muerto de modelos)/13 (duplicacion de
modelos) no aplican con el mismo peso que en apps de dominio -- ya
cubiertas en la auditoria previa (0 modelos concretos).

## FASE 6 — Auditoria ORM/BD: investigacion del N+1 sospechado (RESUELTO)

La auditoria previa dejo como deferred (P2): *"N+1 en llamadas
organizational_* desde apps consumidoras"*. Investigado a fondo en
esta pasada:

1. `OrganizationalContext.resolve(request)` se cachea en
   `self._organizational_context` (mixin, `organizational_context.py:
   200-205`) -- una sola resolucion por instancia de vista/ViewSet,
   sin importar cuantas veces se llame `get_organizational_context()`
   dentro del mismo request.
2. `resolve_sede_activa_id()` (invocado UNA vez dentro de
   `resolve()`) hace como maximo 2 queries (chequeo de sesion +
   fallback a sedes_asignadas/principal) -- fijo, no proporcional a
   ninguna coleccion.
3. `OrganizationalScope.resolve(request)` materializa `sede_ids`/
   `area_ids` como `frozenset` en el momento de resolver (`.values_
   list("id", flat=True)` evaluado una vez), y se cachea en
   `self._organizational_scope` -- mismo patron.
4. `OrganizationalScope.filter(model)` usa `sede_id__in=self.sede_ids`
   / `area_id__in=self.area_ids` -- filtro de una sola query, no una
   query por fila.

**Conclusion: el N+1 sospechado NO se confirma.** La unica
"duplicacion de query" real es que `OrganizationalContext.resolve()`
y `OrganizationalScope.resolve()` cada uno resuelve `empresa_id`
independientemente si un ViewSet hereda AMBOS mixins (decision
arquitectonica documentada, ver FASE 1) -- esto es, como maximo, 1-2
queries redundantes por request en el caso de doble-herencia, no un
N+1 proporcional al tamaño de una coleccion. Se cierra este deferred
con evidencia: **no requiere accion**.

## FASE 11 — Auditoria de frontend (workspace.html)

La auditoria previa marco `workspace.html` como "no re-auditado mas
alla de Nivel 3" (P3 deferred). Verificado en esta pasada:

- `workspace.html` actual: **342 lineas**, no las 900+ lineas de JS
  inline descritas en `documentacion/_archive/
  INFORME_COMPLETO_APP_EMPRESA.md` (documento historico de 2025).
- Logica extraida a `{% static 'core/js/workspace.js' %}` (modulo
  externo, `type="module"`), consistente con el patron FSD/modular ya
  confirmado en todas las apps auditadas (namespace `window.Sintel.*`).
- Carga de HTMX con fallback CDN->cdnjs y verificacion `checkHTMX()`
  con reintentos -- patron defensivo razonable, no codigo muerto.

**Conclusion: el frontend de `core` SI esta modernizado.** El deferred
anterior se cierra -- no se encontro codigo legado monolitico
pendiente de refactor.

## Codigo muerto / duplicacion (FASE 12/13)

Sin hallazgos nuevos en esta pasada mas alla de lo ya eliminado en la
auditoria previa (5 adaptadores huerfanos, 1271 lineas). La
duplicacion intencional `OrganizationalContext`/`OrganizationalScope`
(FASE 1) se reconfirma como `INTENTIONAL_VARIANT` -- no se consolida.

## Integraciones (FASE 7)

Sin cambios respecto a la auditoria previa: las 16 apps consumen
`core` (empresa_id, middleware, OCF/OSF, gateway `_apps/`). Ningun
contrato roto encontrado.

## Normativa colombiana (FASE 14)

NO_APLICA -- `core` no calcula ni almacena datos con obligaciones
tributarias/laborales propias.

## Cambios realizados en esta pasada

**Ninguno.** Esta pasada F34 fue puramente de investigacion/evidencia
(resolvio 2 items deferred con evidencia negativa/positiva, sin
requerir cambios de codigo). Consistente con la regla F34 de "auditar
primero, modificar solo si hay hallazgo real que lo justifique".

## FASE 17 — Validacion puntual

No aplica -- sin cambios de codigo en esta pasada, no hay nada que
validar puntualmente. La regresion completa de `core` (73 passed, 19
skipped, 0 failed) ya esta confirmada vigente desde la auditoria
previa (sin cambios de codigo desde entonces).

## Riesgos y deuda diferida (actualizada)

| Item | Estado |
|---|---|
| N+1 en `organizational_*` | **CERRADO** -- investigado, no confirmado |
| `workspace.html` sin re-auditar | **CERRADO** -- confirmado modernizado |
| `Meta.indexes` non-merge (Django, limitacion conocida del framework) | Sigue abierto, P2, requiere verificacion por-app (fuera del alcance de `core` en si) |

## FASE 22 — Release Gate

- [x] Reglas de negocio identificadas y clasificadas
- [x] Mapa de dominio (thin, consistente con rol de infraestructura)
- [x] N+1 investigado con evidencia -- cerrado
- [x] Frontend auditado estructuralmente -- cerrado
- [x] Codigo muerto/duplicacion -- sin hallazgos nuevos
- [x] Integraciones -- sin contratos rotos
- [x] Normativa -- NO_APLICA
- [x] Sin cambios de codigo -> sin necesidad de validacion puntual nueva
- [x] Documentacion completa

**APP = COMPLETED.** core cierra F34 sin cambios de codigo -- la
pasada anterior (F33-style) ya habia resuelto sus hallazgos reales;
esta pasada cierra con evidencia los 2 items que quedaban como
sospecha, confirmando que no requieren accion.
