# F30 — Matriz de Contratos de URL

**Fecha:** 2026-08-11 · Cierra los 3 hallazgos abiertos por
`F29_URL_REVERSE_AUDIT.md` (sección 2-4). Detalle completo de cada uno en
`F30_FINDINGS.md`.

| Hallazgo | Nombre usado en tests (incorrecto) | Nombre real registrado | Path HTTP | Namespace | Clasificación | Archivos corregidos | Sites |
|---|---|---|---|---|---|---|---|
| F29-003 / F30-A | N/A (no es un nombre de URL — `self.client`/`self.user` shadowed) | N/A | N/A | N/A | FIXTURE_BUG | `tests/tenant/core/test_workspace_crud_integration.py` | 3 clases |
| F29-006 / F30-B | `tenant_dashboard:index` | `tenant-dashboard-shell` | `/dashboard/` | ninguno (top-level en `config/urls_tenant.py:140`) | WRONG_TEST_CONTRACT | `tests/general/test_system_health.py`, `tests/tenant/landing/test_private_routing.py` | 2 |
| F29-007 / F30-C | `user-list` / `user-detail` (colisión, resolvía a `PublicUserViewSet`) | `admin-user-list` / `admin-user-detail` (tras rename de `UserAdminViewSet`) | `/api/admin/v1/accounts/users/` | ninguno (`config/urls_public.py:104`) | URL_CONTRACT (colisión real de basename DRF) | `tests/public/accounts/test_user_crud_api.py`, `tests/public/accounts/test_admin_users_list.py` | 16 |

## Contrato de referencia — `PublicUserViewSet` (no modificado)

| Nombre | Path HTTP | Namespace | Estado |
|---|---|---|---|
| `user-list` / `user-detail` | `/api/public/v1/users/` | ninguno (`config/urls_public.py:95` -> `config/public_api_urls.py` -> `apps/public/accounts/api/public_urls.py`) | SSoT confirmado, sin cambios |

## Verificación

`pytest --collect-only` completo (sin argumentos): **2053 tests, 0 errores**
tras todos los fixes de F30 (contratos URL + harness de colección). Ejecución
real de los 5 archivos tocados en F30 pendiente de confirmación final en
`F30_REGRESSION_REPORT.md`.
