# F13/F14 — Baseline previo a Knowledge Graph Organizacional + Gobernanza Automática

**Fecha:** 2026-08-09
**Branch:** `feat/onboarding-cookie`
**Commit base:** `34fc020` (`docs: ADR-003/004/005 + consolidacion completa OCF/OSF`)

## Estado Git

```
34fc020 docs: ADR-003/004/005 + consolidacion completa OCF/OSF (auditoria FASE 0-12)
1d19d8f test(scope): suite de adopcion OCF por app + aislamiento organizacional Empresa/Sede/Area
c63b35e feat(scope): filtrado por alcance organizacional en 6 apps (OSF F7/F9/F10/F11) + adopcion aditiva del resto
120d17e feat(compras): piloto oficial ADR-003/OSF - SedeAwareModel + HasOrganizationalScope
0295932 feat(core): Organizational Context Framework (OCF) - contexto organizacional Empresa->Sede->Area
371f19d chore: elimina carpeta basura con ruta de Windows mal formada
```

`git status --short`: **79 archivos sin commitear**, todos categoría E (líneas de trabajo no
relacionadas a OCF/OSF/F13/F14) — verificado archivo por archivo contra la clasificación ya hecha
en `documentacion/OCF_OSF_BASELINE.md` §4:
- `tools/ekg/*` (8 modificados + 8 nuevos) — pipeline EKG existente, propio, sin commitear.
- Fixes puntuales de la Remediación Auditoría Enterprise 2026-08-06 (IDs duplicados en `empresa`/`gastos`/`empleados`/`inventario`/`proveedores`, `nginx.conf`, `middleware.py`).
- Infraestructura/dependencias (`docker-compose.yaml`, `requirements.txt`, `.github/workflows/ci-quality-gate.yml`, `Makefile`).
- `notas.txt`, `nul` (debris), `.claude/launch.json`.
- Documentos `documentacion/*.md` de esta misma sesión que aún no se habían commiteado en el commit de docs (`FASE11_CONSOLIDACION_GIT.md`, `ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md`, `ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`, `arquitectura_general.md` — actualizados en el turno de sincronización posterior al commit `34fc020`, correctamente pendientes de un commit propio, no de F13/F14).

**Ninguno de estos 79 archivos se toca en F13/F14** (regla §8 del prompt maestro).

## Regla de no regresión — evidencia de baseline

En vez de re-ejecutar la suite completa de OCF/OSF (24 min + 9 min la última vez que corrió
completa, en la misma sesión), se usa como evidencia de baseline la **confirmada más reciente**
(mismo día, mismo estado de código, sin cambios intermedios en los archivos de test/producción de
OCF/OSF entre esa corrida y este momento — verificado con `git status`, cero diffs nuevos en
`apps/tenant/core/`, `apps/tenant/compras/` desde el commit `34fc020`):

| Suite | Resultado real (ejecutado en esta sesión) |
|---|---|
| `apps/tenant/core/tests/test_organizational_*.py` (9 archivos) | `53 passed, 1 warning in 1452.86s` |
| `apps/tenant/compras/tests/` (piloto completo, incl. aislamiento) | `20 passed, 1 warning in 503.96s` |

Adicionalmente, en este mismo baseline: `python manage.py check` → `System check identified no
issues (0 silenced)`, verificado de nuevo justo antes de iniciar F13.

## Estado OCF/OSF/EKG

- **OCF:** commiteado (`0295932`). Baseline 🟢 (`ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md`).
- **OSF:** commiteado (`120d17e`, `c63b35e`). Baseline 🟢.
- **EKG existente (`tools/ekg/`):** pipeline propio (extractores Python/JS/docs, `build_graph.py`,
  `governance.py`, `impact.py`, `platform.py`, `export_html.py`) — **sin commitear, línea de
  trabajo separada**. Ver auditoría de descubrimiento en `documentacion/F13_0_EKG_AUDIT.md`.

## Resolución del conflicto entre F13.0 ("extender EKG existente") y §8 ("no tocar los 78 archivos")

Documentado explícitamente, no resuelto en silencio (regla de conflicto del prompt maestro §0):
`tools/ekg/` es simultáneamente "el EKG existente" que F13.0 pide extender, y parte de los
archivos de categoría E que §8 prohíbe tocar/commitear. Resolución aplicada: el Knowledge Graph
organizacional de F13 se construye como **módulo nuevo y separado**
(`tools/organizational_governance/`), que **lee** el código fuente de forma independiente (no
importa ni modifica ningún archivo de `tools/ekg/`), preservando intacta la línea de trabajo EKG
existente. Esto cumple el espíritu de "extender, no reemplazar" (el concepto de grafo de
conocimiento se extiende al dominio organizacional) sin violar la regla más estricta y explícita
de no tocar/commitear los 78 archivos no relacionados.

**Estado: 🟢 COMPLETED.**
