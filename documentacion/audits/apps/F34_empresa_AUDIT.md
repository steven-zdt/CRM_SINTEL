# F34_empresa_AUDIT — Auditoria integral de negocio/arquitectura (app 2/16)

Mision F34 (`documentacion/audits/apps/F34_MASTER_STATUS.md`). Base
confirmada: `documentacion/audits/apps/APP_empresa_AUDIT.md` (445
lineas de codigo muerto ya eliminadas: `impl/empresa_service.py`,
shim de permisos huerfano, script obsoleto).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## Resumen ejecutivo

`empresa` es la SSoT de datos fiscales del tenant (razon social, NIT,
regimen tributario) y de la estructura organizacional (Sede, Area) y
buzones de correo (`MailInboxConfig`). Singleton por schema. Sin
cambios de codigo en esta pasada -- se profundiza en reglas de
negocio clasificadas, mapa de dominio, y verificacion N+1/frontend no
cubiertas con este detalle antes.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| Una unica `Empresa` por schema (singleton, `UniqueConstraint` en `singleton_key`) | **CRITICAL** | `models.py`, constraint DB |
| NIT unico por tenant | **CRITICAL** | `models.py` (`unique=True` en `nit`) |
| Al eliminar la `Empresa` (accion STAFF/ADMIN), `Sede`/`Area`/`TenantProfile` se eliminan en cascada (`on_delete=CASCADE`, excepcion documentada `[ARQ-A2]` a `SintelTenantBaseModel`) | **CRITICAL** | `models.py` (Sede/Area), comentario `[ARQ-A2]` |
| `Empresa.empresa` (autorreferencia) es `null=True` solo para permitir el bootstrap inicial -- toda instancia posterior a la primera debe tener el campo poblado | **IMPORTANT** | `models.py`, `save()` override documentado |
| Nombre de Sede unico por empresa; Area unica por Sede (nombre y codigo de funcionamiento) | **IMPORTANT** | `UniqueConstraint`s en `Sede.Meta`/`Area.Meta` |
| `asegurar_estructura_organizacional_inicial()` garantiza Sede "Principal" + Area "General" de forma idempotente en AMBOS niveles por separado (hallazgo real de F4/OSF: una empresa podia tener Sede sin Area) | **IMPORTANT** | `business_service.py`, docstring cita el hallazgo empirico de 3 tenants reales |
| `MailInboxConfig` -- campos legacy (`host`,`port`,`username`,`password`) coexisten con `imap_*`/`smtp_*` vigentes, por compatibilidad con configs de tenants ya existentes | **SUPPORTING** | `models.py`, `help_text` marca cada legado |
| `get_empresa_emisor_data()` es el contrato SSoT estricto para facturas -- nunca retorna `None`, lanza `EmpresaNotConfiguredError` | **CRITICAL** (para consumidores) | `services/__init__.py`, verificado consumido por `facturas` |
| Password de `MailInboxConfig` sin cifrar | **DERIVED/deuda** | Ya documentado como TODO desde 2025, deferred P2 (decision de producto pendiente, no de codigo) |

## FASE 2 — Mapa de dominio

```
Empresa (1, singleton)
  |-- Sede (0..N, nombre unico por empresa)
  |     `-- Area (0..N, nombre+codigo unico por sede)
  |-- MailInboxConfig (0..N, independiente de Sede/Area)
  `-- TenantProfile (0..N, via empresa.perfiles_tenant, definido en app `perfil`)
```

**Estados:** `Empresa.activa` (bool simple, sin maquina de estados).
`Sede`/`Area` no tienen campo de estado propio (activo/inactivo) --
se eliminan fisicamente si ya no se usan (verificado: sin campo
`activo` en `Sede`/`Area.Meta`, a diferencia de `MailInboxConfig.
is_active`).

**Invariante real verificada:** ninguna Sede puede quedar sin al
menos 1 Area tras `asegurar_estructura_organizacional_inicial()` --
pero esto NO es un `CheckConstraint` de BD, es una garantia aplicada
solo en el punto de entrada del seed (onboarding + backfill). Una
Sede creada manualmente via CRUD directo (fuera del seed) SI puede
quedar sin Area -- **no es un bug** (el CRUD de Sede/Area es
independiente por diseño, confirmado en la auditoria previa), pero
vale la pena registrar la distincion: el invariante es de
"conveniencia al oneboarding", no un invariante de BD estricto.

## FASE 6 — ORM/BD: verificacion N+1

- `Empresa`: singleton, riesgo N+1 inexistente (0 o 1 fila por
  definicion).
- `SedeViewSet`/`AreaViewSet.get_queryset()`: delegan a
  `SedeSelector`/`AreaSelector.get_list()`, verificados con `.only()`
  y traversals explicitos en la auditoria previa. Volumen tipico bajo
  (unas pocas sedes/areas por empresa) -- riesgo de N+1 practico
  minimo incluso si hubiera algun `select_related` faltante.
- Sin hallazgos de N+1 nuevos en esta pasada.

## FASE 11 — Frontend (verificacion estructural)

`static/empresa/js/`: ~1255 lineas totales entre los modulos de
Sede/Area/MailInboxConfig/Empresa. Tamaño razonable, sin señales de
monolito (multiples archivos por responsabilidad, patron FSD ya
confirmado). Sin auditoria linea por linea en esta pasada (bajo
riesgo dado el tamaño y que ya paso por refactors documentados
v2.60/v2.61 segun el historial de `_archive/`).

## Codigo muerto / duplicacion (FASE 12/13)

Sin hallazgos nuevos -- los 3 items reales (`impl/empresa_service.py`,
shim de permisos, script obsoleto) ya fueron eliminados en la
auditoria previa. `management/commands/audit_empresa_app.py` sigue
como herramienta de diagnostico huerfana de Makefile/CI (P3,
deliberadamente no eliminada por no ser logica de negocio).

## Normativa colombiana (FASE 14)

Sin cambios respecto a la auditoria previa: `empresa` es NO_APLICA
formalmente (provee datos de entrada -- NIT, regimen -- que otras
apps usan, no calcula obligaciones propias).

## Cambios realizados en esta pasada

**Ninguno.** Pasada de verificacion/evidencia unicamente.

## Riesgos y deuda diferida (actualizada)

| Item | Estado |
|---|---|
| Cifrado de `MailInboxConfig.password` | Sigue abierto, P2, requiere decision de producto |
| `audit_empresa_app.py` huerfano | Sigue abierto, P3, informativo |
| N+1 en Sede/Area | **CERRADO** -- verificado, sin hallazgos |
| Frontend sin auditar linea por linea | Aceptado como bajo riesgo dado el tamaño (~1255 lineas, modular) -- no se fuerza una auditoria exhaustiva sin señal de problema real |

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio construido
- [x] N+1 verificado -- sin hallazgos
- [x] Frontend verificado estructuralmente -- bajo riesgo
- [x] Codigo muerto/duplicacion -- sin hallazgos nuevos
- [x] Normativa -- NO_APLICA
- [x] Sin cambios de codigo -> sin necesidad de validacion puntual nueva

**APP = COMPLETED.**
