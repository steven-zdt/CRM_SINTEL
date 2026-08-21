# F34_perfil_AUDIT — Auditoria integral de negocio/arquitectura (app 3/16)

Mision F34. Base confirmada: `documentacion/audits/apps/
APP_perfil_AUDIT.md` (0 codigo muerto, arquitectura ya limpia).

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## Resumen ejecutivo

`perfil` es la SSoT de rol/alcance organizacional del colaborador
dentro del tenant (`TenantProfile`). Sin cambios de codigo en esta
pasada -- ya confirmada como la app mas limpia auditada hasta ahora.
Se agregan aqui las dimensiones nuevas de F34.

## FASE 1 — Reglas de negocio (clasificadas)

| Regla | Clasificacion | Evidencia |
|---|---|---|
| El rol (`ADMIN`/`OPERADOR`/`VISOR`) se resuelve exclusivamente desde `TenantProfile.rol` (schema tenant) | **CRITICAL** | SSoT de permisos en todo el sistema, hallazgo heredado F33.15-B |
| `rol` y `alcance` son ortogonales -- rol = QUE puede hacer, alcance = DONDE puede hacerlo | **CRITICAL** | Docstring explicito de `AlcanceOrganizacional`, ADR-003 |
| `assign_rol()` es la UNICA via para cambiar rol -- separada de `update_profile()` (autoservicio) | **CRITICAL** | `crud_service.py`, allowlist `[SEG-3]` excluye `rol` de `MUTABLE_FIELDS` |
| Un usuario tiene a lo sumo 1 `TenantProfile` por empresa (`unique_together('user','empresa')`) | **CRITICAL** | `models.py` |
| `update_profile()` (autoservicio) rechaza payloads que intenten cambiar `empresa_id`/`user_id` | **CRITICAL** (anti-IDOR) | `perfil_service.py`, verificado en auditoria previa |
| Avatar: solo JPEG/PNG/GIF/WEBP, maximo 5MB | **IMPORTANT** | `_validate_avatar_file()` |
| `alcance=SEDE`/`AREA` requiere `sedes_asignadas`/`areas_asignadas` pobladas para tener efecto | **IMPORTANT** | M2M en `models.py`, consumido por `organizational_scope.py` (auditado en `core`) |
| `get_permissions_context()` calcula `is_owner` via `check_primary_admin()` (schema public) | **IMPORTANT** | `api/permissions.py`, cruza schema con `apps.tenant.core.services.membership` |

## FASE 2 — Mapa de dominio

```
TenantProfile (1 por user+empresa)
  |-- user (OneToOne -> AUTH_USER_MODEL, schema public, direccion unica)
  |-- departamento (FK opcional -> Departamento)
  |-- rol (ADMIN|OPERADOR|VISOR)
  |-- alcance (EMPRESA|SEDE|AREA)
  |-- sedes_asignadas (M2M -> empresa.Sede, relevante solo si alcance != EMPRESA)
  `-- areas_asignadas (M2M -> empresa.Area, relevante solo si alcance == AREA)

Departamento (catalogo simple, unique por empresa+nombre)
```

**Estados:** ninguno propio (perfil no tiene ciclo de vida, existe
mientras el usuario tenga membresia en el tenant).

## FASE 6 — ORM/BD: verificacion N+1

Verificado en `services/selectors.py` y `services/crud_service.py`:
**los 5 metodos de lectura (`list_profiles`, `get_profile_by_*` x3,
`PerfilSelector.get_list`/`get_detail`) usan `select_related('user',
'departamento')` consistentemente**, y los que exponen las M2M
(`sedes_asignadas`/`areas_asignadas`) usan `prefetch_related`
correctamente (no `select_related`, que seria incorrecto para M2M).
**Sin hallazgos de N+1** -- confirma el patron "Zero Waste" ya
documentado.

## FASE 11 — Frontend

App pequeña en frontend (`views.py` FASE 5-BIS con django-tables2,
`views_ui.py` con un solo partial). Sin senales de duplicacion o
codigo muerto. No amerita auditoria linea por linea adicional.

## Codigo muerto / duplicacion / normativa

Sin hallazgos nuevos (ya confirmado limpio). `perfil` NO_APLICA a
matriz normativa formal.

## Cambios realizados en esta pasada

**Ninguno.**

## FASE 22 — Release Gate

- [x] Reglas de negocio clasificadas
- [x] Mapa de dominio construido
- [x] N+1 verificado -- sin hallazgos (select_related/prefetch_related consistentes)
- [x] Frontend verificado -- bajo riesgo
- [x] Sin cambios de codigo -> sin necesidad de validacion puntual nueva

**APP = COMPLETED.**
