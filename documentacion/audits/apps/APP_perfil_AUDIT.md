# APP_perfil_AUDIT — Auditoria integral (app 3/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: core -> empresa
-> **perfil** -> empleados -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A — Mapa de negocio

`apps/tenant/perfil` es la **SSoT de perfiles de colaborador dentro del
tenant** (`TenantProfile`) y del catalogo de `Departamento`. Es el
modulo que resuelve **rol** (`ADMIN`/`OPERADOR`/`VISOR`) y **alcance
organizacional** (`EMPRESA`/`SEDE`/`AREA`, ver ADR-003) para cada
usuario -- consumido por practicamente toda la superficie de permisos
del sistema:

- `apps.tenant.api.permissions` (SSoT central de permisos, `[SECURITY]`
  AGENTS.md §15) resuelve el rol via `TenantProfile.rol` -- **NO** via
  `TenantMembership.rol` del esquema public (hallazgo ya conocido,
  heredado de F33.15-B Nivel 3, ver `APP_AUDIT_MASTER_STATUS.md`
  "Contexto heredado relevante").
- `apps.tenant.core.services.membership.check_primary_admin` -- usado
  por `perfil/api/permissions.py:get_permissions_context()` para el
  flag `is_owner` (Auto-Admin Elevation).
- `apps.tenant.facturas.api.views_mail_ingestion` consume
  `perfil_service.get_or_create_profile` directamente.
- Todas las apps tenant heredan `empresa_id` via `SintelTenantBaseModel`,
  pero el **rol/alcance especifico del colaborador** vive unicamente
  aqui.

No se encontraron auditorias previas de `perfil` en
`documentacion/_archive/` (a diferencia de `empresa`, que tenia 10
documentos historicos) -- primera auditoria formal de esta app.

## FASE B — Modelos (2, confirma matriz FASE 1)

1. **`Departamento`** -- catalogo simple por empresa (`unique_together
   ('nombre', 'empresa')`), FK `on_delete` estandar via
   `SintelTenantBaseModel` (no tiene la excepcion `[ARQ-A2]`).
2. **`TenantProfile`** -- perfil del colaborador. Puntos clave:
   - `user` es `OneToOneField` a `settings.AUTH_USER_MODEL` (esquema
     public) -- unica direccion permitida de la relacion
     (`TenantProfile -> User`, documentado inline como "REGLA DE ORO").
   - `empresa` con excepcion `[ARQ-A2]` (`on_delete=CASCADE`, igual
     patron que `Sede`/`Area` en `empresa/models.py`): un perfil no
     tiene sentido sin la empresa, debe desaparecer con ella.
   - `rol` (`RolTenant`) y `alcance` (`AlcanceOrganizacional`) son
     **campos ortogonales**, documentado explicitamente en el
     docstring del choices class: rol = QUE puede hacer, alcance =
     DONDE puede hacerlo. Diseño correcto, no hay solapamiento.
   - `sedes_asignadas`/`areas_asignadas` (M2M a `empresa.Sede`/`Area`)
     -- usados cuando `alcance != EMPRESA`.
   - `unique_together ('user', 'empresa')` -- un usuario puede tener
     como maximo un perfil por empresa (coherente con el diseño
     multi-tenant: un perfil por schema/tenant).

Migraciones (8) muestran evolucion incremental coherente: 0001 inicial
-> 0005 agrega `rol` -> 0008 agrega `alcance`/sede/area (ADR-003). Sin
migraciones huerfanas o revertidas.

## FASE C/D/K — Service Layer y codigo muerto

Estructura (FSD, 5 archivos + `perfil_service.py` legacy explicito):
`services/{selectors,crud_service,business_service,perfil_service,
__init__}.py` + `api/mixins.py` (real) + `services/api_mixins.py`
(stub vacio intencional).

**A diferencia de `empresa` (donde `impl/` habia quedado huerfano tras
un refactor posterior), aqui NO se encontro codigo muerto real.**
Investigacion de consumidores (grep de nombres de funcion/clase,
repo completo):

- `perfil_service.py` (`get_or_create_profile`, `read_profile`,
  `update_profile`, `update_profile_config`) -- etiquetado "Legacy
  compatibilidad" en `services/__init__.py`, pero **SI tiene
  consumidores reales activos**: `api/viewsets.py` (autoservicio "mi
  perfil": lectura/actualizacion del PROPIO perfil del usuario
  autenticado, incluye validacion de avatar MIME/tamaño y guardas
  anti-IDOR explicitas) y `facturas/api/views_mail_ingestion.py`. No es
  duplicacion con `PerfilCRUDService`/`PerfilBusinessService`: esos
  cubren la gestion ADMIN de perfiles de OTROS colaboradores
  (`list_profiles`, `get_profile_by_id_and_tenant`, `assign_rol`,
  `delete_profile`) -- dominios distintos (autoservicio vs
  administracion), ambos legitimos y sin solapamiento de responsabilidad.
- `services/api_mixins.py` -- archivo vacio **intencional**, con
  docstring explicito explicando que existe solo para romper un ciclo
  de import (`services/__init__.py -> services/api_mixins.py ->
  api/mixins.py -> services/business_service.py ->
  services/__init__.py`). No es un resto de refactor, es una guarda
  deliberada y ya documentada -- no se toca.
- `api/permissions.py` -- reexporta clases desde
  `apps.tenant.api.permissions` (SSoT, cumple la regla de CLAUDE.md
  "Permissions: import only from apps.tenant.api.permissions") y
  agrega funciones propias de la app (`ROLE_ACTIONS`,
  `get_available_actions`, `get_permissions_context`) con
  consumidores reales confirmados (`TenantProfileSerializer`,
  UI/Tabulator). Sin duplicacion, sin shim huerfano (a diferencia del
  `permissions.py` raiz de `empresa`, que si estaba huerfano y fue
  eliminado en esa auditoria).

**Conclusion FASE K: 0 lineas de codigo muerto confirmado en esta
app.** No se realizaron eliminaciones -- la app ya esta en buen estado
arquitectonico (separacion autoservicio/admin clara, sin shims
huerfanos, sin shadowing de modulos).

## FASE I — Seguridad (confirmacion, sin cambios)

- `update_profile()` en `perfil_service.py` tiene verificacion anti-IDOR
  explicita: rechaza payloads que intenten cambiar `empresa_id`/`user_id`
  a un valor distinto del perfil autenticado actual.
- `PerfilCRUDService.update_profile()` usa allowlist de campos mutables
  (`MUTABLE_FIELDS`, comentario `[SEG-3]`) -- rechaza silenciosamente
  `rol`, `user`, `empresa`, `id`, `uuid` si vinieran en el payload.
- `assign_rol()` es la UNICA via para cambiar `rol` -- separada
  deliberadamente de `update_profile()` (coherente con que cambiar rol
  es una accion administrativa distinta a editar datos propios).
- Confirma el hallazgo heredado de Nivel 3: el rol se resuelve via
  `TenantProfile.rol` (este modulo), no via `TenantMembership.rol`
  (schema public) -- sin discrepancias nuevas encontradas.

## FASE M — Normativa colombiana

`perfil` no esta en la lista de apps que requieren matriz normativa
DIAN. **NO_APLICA**.

## FASE Q — Tests / Regresion

4 tests coleccionados (`apps/tenant/perfil/tests/`). Regresion
ejecutada (db/redis healthy): **4 passed, 0 failed, 1 warning
preexistente (min_value en DRF, mismo hallazgo ya visto en core/empresa,
no relacionado) en 1499.94s (0:24:59)**.

## Deferred

Ninguno nuevo. Esta app no genero hallazgos que requieran seguimiento
diferido -- primera app de las 16 en este estado (core y empresa
tuvieron 4 y 3 items diferidos respectivamente).

## FASE X — Release Gate (checklist)

- [x] Modelos auditados (FASE B)
- [x] Service Layer auditado, sin codigo muerto encontrado (FASE C/D/K)
- [x] Seguridad confirmada, sin hallazgos nuevos (FASE I)
- [x] Normativa colombiana evaluada (FASE M -- NO_APLICA)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] Regresion de la app -- 4 passed, 0 failed
- [x] Sin deferred items pendientes de documentar

## FASE Y — Decision

**COMPLETED** -- 4/4 tests pasan, 0 regresiones, 0 hallazgos de codigo
muerto, sin items deferred. Segunda app cerrada como `COMPLETED` puro
(la primera fue ninguna hasta ahora -- core y empresa cerraron
`_WITH_DEFERRED`).
