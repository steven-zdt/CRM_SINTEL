# APP_empresa_AUDIT — Auditoria integral (app 2/16)

Mision: `documentacion/APP_AUDIT_MASTER_STATUS.md`. Orden: core (COMPLETED_WITH_DEFERRED) -> **empresa** -> perfil -> ...

**Fecha:** 2026-08-20. **Rama:** `feat/onboarding-cookie`.

---

## FASE A — Mapa de negocio

`apps/tenant/empresa` es el **SSoT de datos empresariales del tenant**
(razon social, NIT, regimen tributario, moneda, sedes, areas) y el punto
de configuracion de buzones de correo para ingesta de facturas
(`MailInboxConfig`). Es consumida por:

- `apps/tenant/facturas` (`get_empresa_emisor_data()` -- determina
  naturaleza VENTA/COMPRA comparando NIT emisor del XML vs NIT del
  tenant; `services_mail_ingestion.py` para credenciales de correo).
- `apps/tenant/core/services/empresa.py`, `orchestration.py` --
  orquestacion para el Core API del workspace (`get_empresa_data()`).
- `apps/tenant/core/services/organizational_*.py` (OCF/OSF) -- resuelve
  Sede/Area via los modelos de esta app.
- 14 apps mas (todas heredan `empresa_id` via `SintelTenantBaseModel`).

App con historial documental extenso: 10 documentos en
`documentacion/_archive/` (informes, correcciones, refactors previos
2025-2026). El mas completo (`INFORME_COMPLETO_APP_EMPRESA.md`,
2025-01) describe una version del modelo `Empresa` con campos DIAN
(`tipo_contribuyente_clase`, `responsabilidades_rut_codigos`,
`actividad_economica`) que **ya no existen** en `models.py` actual --
el modelo vigente es mas simple (razon_social, nit, dv, direccion,
ciudad, departamento, telefono, email/email_contacto, owner_email,
regimen_tributario, moneda, logo, website, activa). Tratado como
contexto historico, no como fuente de verdad; `models.py` real prevalece.

## FASE B — Modelos (4, confirma matriz FASE 1)

1. **`Empresa`** -- singleton por schema (`UniqueConstraint` en
   `singleton_key`), NIT unico. `empresa` FK a si misma es `null=True`
   (necesario para el bootstrap: la primera instancia no puede
   auto-referenciarse antes de existir) con override explicito de
   `save()` que documenta por que salta la guardia de
   `SintelTenantBaseModel`. Patron correcto, ya documentado en el
   propio codigo.
2. **`MailInboxConfig`** -- config de buzones IMAP/SMTP. Campos legacy
   (`host`, `port`, `username`, `password`, `protocol`, `ssl`, ...)
   marcados `# WARNING: DEPRECADO` en el propio `help_text`, coexisten
   con los campos `imap_*`/`smtp_*` vigentes -- migracion de datos
   real, no codigo muerto (los campos legacy siguen en la tabla por
   compatibilidad hacia atras, consistente con `MailInboxConfig` de
   tenants ya existentes).
3. **`Sede`** -- excepcion documentada a `SintelTenantBaseModel`
   (`on_delete=CASCADE` en vez de `PROTECT` para `empresa`), justificada
   inline (`[ARQ-A2]`): al eliminar la Empresa (accion STAFF/ADMIN),
   la estructura organizativa debe desaparecer con ella.
4. **`Area`** -- misma excepcion `[ARQ-A2]`, FK a `Sede`.

`Empresa.password` en `MailInboxConfig`: **sin cifrar** -- hallazgo
YA CONOCIDO y documentado desde 2025 (`INFORME_COMPLETO_APP_EMPRESA.md`
§11.5, §15.3) como TODO pendiente. Se mantiene como DEFERRED (ver
tabla al final) -- requiere decision de producto (que libreria de
cifrado, rotacion de claves) fuera del alcance de una auditoria de
codigo.

## FASE C/D/K — Service Layer y codigo muerto (CONFIRMADO Y CORREGIDO)

Estructura real (FSD): `services/{crud_service,business_service,
selectors,api_mixins}.py` + un paquete adicional `impl/` (histórico,
ver `documentacion/_archive/CORRECCION_IMPORT_EMPRESA.md`: en 2025 hubo
un shadowing `services.py` archivo vs `services/` paquete, resuelto
renombrando el paquete viejo a `impl/`). Desde entonces la app fue
refactorizada UNA VEZ MAS hacia el patron FSD estandar (`services/`
volvio a ser paquete, con `crud_service.py`/`business_service.py`
propios), dejando `impl/` como resto de la generacion anterior.

**Investigacion de consumidores real (grep de nombres de funcion Y de
modulo, repo completo, incluyendo tests/scripts/management commands):**

| Archivo | Funciones | Consumidores reales |
|---|---|---|
| `impl/empresa_service.py` | `get_empresa`, `get_or_create_empresa`, `update_empresa` | **CERO** en produccion -- `business_service.py`/`crud_service.py` (vigentes) NO lo importan. Unicos importadores: `management/commands/audit_empresa_app.py` (comando de diagnostico nunca invocado por Makefile/CI/docs) y `scripts/test_empresa_refactor.py` (script manual de validacion post-refactor de 2025, ya obsoleto, no en `pytest.ini`, no referenciado en ningun otro archivo). |
| `impl/mailbox_provider.py` | `get_mailbox_config` | SI usado -- `services/crud_service.py`, `services/__init__.py`. |
| `impl/mailbox_service.py` | CRUD `MailInboxConfig` | SI usado (verificado via `impl/__init__.py`, consumido por `api/viewsets.py`). |
| `apps/tenant/empresa/permissions.py` (raiz) | `IsTenantAdmin` (shim deprecado desde v2.61.8, reexporta `apps.tenant.api.permissions.IsTenantAdmin`) | **CERO** consumidores en todo el repo -- el propio archivo se auto-declara deprecado pero nadie lo importa ya. |

**DEAD_CONFIRMED, eliminado (evidencia: grep function+module name repo-wide,
sin resultados fuera de si mismos/tooling huerfano; sin referencias en
`urls.py`/tests; `manage.py check` + regresion de la app confirman 0
impacto):**

- `apps/tenant/empresa/impl/empresa_service.py` (184 lineas) --
  eliminado completo. `impl/__init__.py` actualizado (ya no re-exporta
  `get_empresa`/`get_or_create_empresa`/`update_empresa`).
- `apps/tenant/empresa/permissions.py` (19 lineas, shim deprecado sin
  consumidores) -- eliminado completo.
- `apps/tenant/empresa/management/commands/audit_empresa_app.py` --
  se removio unicamente el bloque que probaba `impl.get_empresa()`
  (11 lineas), que testeaba una API ya no vigente; el resto del
  comando (verificacion de modelo, `services.get_empresa_emisor_data`,
  APIs) sigue intacto y funcional. El comando en si sigue sin estar
  wireado a Makefile/CI -- **no se elimino** (fuera del alcance minimo:
  es una herramienta de diagnostico, no logica de negocio, y sigue
  siendo utilizable manualmente).
- `scripts/test_empresa_refactor.py` (231 lineas) -- eliminado. Script
  de validacion manual de un refactor ya cerrado en 2025 (ver
  `documentacion/_archive/CORRECCION_IMPORT_EMPRESA.md`), sin
  referencias en ningun otro archivo del repo, no colectado por pytest
  (`scripts/` esta en `norecursedirs`), y roto de facto tras eliminar
  `impl/empresa_service.py` (importaba directamente de ahi).

**Total eliminado: 434 lineas** (184 + 19 + 231, mas 11 lineas de
`audit_empresa_app.py`).

`business_service.py`/`crud_service.py` (vigentes, NO tocados):
arquitectura FSD correcta -- `crud_service.py` = primitivas DB
(`crear_empresa_db`, `actualizar_empresa_db`, CRUD Sede/Area con
verificacion anti-IDOR `empresa_id` en cada query), `business_service.py`
= reglas (`EmpresaService.get_or_create_empresa` valida NIT duplicado,
`SedeService`/`AreaService` con verificacion de pertenencia a empresa).
Confirmado: **NO hay duplicacion real entre `crud_service.get_empresa_data()`
y `services/__init__.py:get_empresa_emisor_data()`** -- son dos
contratos distintos e intencionales: `get_empresa_data()` es un DTO
generico (usado por `core/services/empresa.py` para el workspace),
`get_empresa_emisor_data()` es el contrato SSoT estricto para facturas
(nunca retorna `None`, lanza `EmpresaNotConfiguredError`) -- confirmado
con test dedicado (`facturas/tests/test_ssot_empresa_provider.py`) que
verifica exactamente ese contrato. No se toca.

## FASE J — Frontend

`views.py` (FASE 5-BIS, django-tables2+HTMX, Sede/Area/MailInboxConfig)
y `views_ui.py` (partial HTML para card de empresa, API-First) tienen
propositos distintos y no coexisten con UI legacy -- ambos wireados en
`urls_ui.py` (`config/urls_tenant.py:174`). Sin hallazgos.

## FASE M — Normativa colombiana

`empresa` no esta en la lista explicita de apps que requieren matriz
normativa DIAN (`facturas, contabilidad, empleados, gastos, compras,
proveedores, ventas, clientes, bancos` -- ver mision). Provee datos de
entrada (NIT, regimen_tributario) que otras apps SI usan para calculos
normativos, pero no contiene logica normativa propia. **NO_APLICA**
para esta app especificamente.

## FASE Q — Tests / Regresion

30 tests coleccionados (`apps/tenant/empresa/tests/`, 9 archivos).
Regresion post-limpieza ejecutada (`REDIS_URL=... pytest
apps/tenant/empresa/ -v`, db/redis healthy): **30 passed, 0 failed,
1 warning preexistente (min_value en DRF, no relacionado) en 2525s
(0:42:05)**. Coincide exactamente con el conteo esperado -- 0
regresiones introducidas por la eliminacion de codigo muerto.

## Deferred (no bloquean cierre)

| # | Item | Razon | Riesgo | Prioridad |
|---|---|---|---|---|
| 1 | `MailInboxConfig.password`/`imap_password`/`smtp_password` sin cifrar | Requiere decision de producto (libreria, rotacion de claves) fuera de alcance de una auditoria de codigo | Credenciales de correo en texto plano en la BD | P2 (seguridad, pero requiere diseño, no es un fix mecanico) |
| 2 | `management/commands/audit_empresa_app.py` es una herramienta de diagnostico huerfana (no wireada a Makefile/CI/docs, solo se auto-referencia) | Fuera del alcance minimo de esta auditoria (no es logica de negocio); se limpio solo el bloque que quedo roto | Ninguno -- comando funcional para uso manual | P3 |
| 3 | Campos DIAN descritos en `INFORME_COMPLETO_APP_EMPRESA.md` (2025) no existen en el modelo actual | Documentacion archivada desactualizada, no se corrige retroactivamente (esta en `_archive/`, ya marcada como historica) | Ninguno -- `models.py` es la fuente de verdad | P3 |

## FASE X — Release Gate (checklist)

- [x] Modelos auditados (FASE B)
- [x] Service Layer auditado, codigo muerto identificado y eliminado (FASE C/D/K)
- [x] Frontend auditado (FASE J)
- [x] Normativa colombiana evaluada (FASE M -- NO_APLICA)
- [x] `manage.py check` PASS (heredado de FASE 0, sin cambios de modelos)
- [x] `py_compile` limpio en todos los archivos editados
- [x] Regresion de la app (30 tests) -- 30 passed, 0 failed
- [x] Deferred items documentados con razon/riesgo/prioridad

## FASE Y — Decision

**COMPLETED_WITH_DEFERRED** -- 30/30 tests pasan, 0 regresiones. Se
usa `_WITH_DEFERRED` (no `COMPLETED` puro) por el item #1 de la tabla
de diferidos (cifrado de `MailInboxConfig.password`, P2 -- requiere
decision de producto, no bloquea cierre por regla explicita de la
mision).
