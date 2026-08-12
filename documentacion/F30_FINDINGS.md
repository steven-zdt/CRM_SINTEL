# F30 — Hallazgos

**Fecha:** 2026-08-11 · **Rama:** `feat/onboarding-cookie`

Convención de clasificación: reutiliza la taxonomía de F29
(`F29_URL_REVERSE_AUDIT.md`) para contratos de URL, y la taxonomía de F30.21
(NEW_PRODUCTION_BUG / PREEXISTING_PRODUCTION_BUG / TEST_BUG / FIXTURE_BUG /
HARNESS_BUG / URL_CONTRACT / etc.) para el resto.

---

## F30-A — `test_workspace_crud_integration.py` (Hallazgo F29-003, WORKSPACE)

**Clasificación:** FIXTURE_BUG (harness shadowing).

**Causa raíz exacta:** las 3 clases del archivo sobreescribían `setUp()` con
un `Client()` sin `HTTP_HOST` y un `User` sin `TenantMembership`, reemplazando
la infraestructura que `SintelTenantTestCase.setUp()` ya provee
correctamente (incluye `HTTP_HOST=self.domain.domain`, requerido por el
middleware de resolución de tenant). F29-003 había diagnosticado solo la
mitad del problema (membership); la causa real y suficiente para explicar el
síntoma exacto (contenido vacío con 200, no 403/redirect) es la falta de
`HTTP_HOST`.

**Fix:** eliminados los 3 `setUp()` redundantes; las clases heredan
`SintelTenantTestCase.setUp()` sin modificar. Eliminados imports muertos
(`get_user_model`, `Client`, `TestCase`, `tenant_context`).

**Archivo:** `tests/tenant/core/test_workspace_crud_integration.py`.

**Regla aplicada (F30.3):** reutilización del harness existente, no
duplicación, no creación de nueva infraestructura de test.

---

## F30-B — `tenant_dashboard:index` nunca registrado (Hallazgo F29-006)

**Clasificación:** WRONG_TEST_CONTRACT (no PRODUCT_DECISION, no
MISSING_PRODUCTION_ROUTE).

**Evidencia:**
- `apps/tenant/dashboard/urls.py` declara `app_name = 'tenant_dashboard'` con
  `urlpatterns = []` y comentario explícito de que debe permanecer vacío y no
  incluirse en ningún URLConf — confirmado, no está incluido en
  `config/urls_tenant.py` ni `config/urls_public.py`.
- La ruta real y funcional para `/dashboard/` **ya existe**:
  `config/urls_tenant.py:140` — `path('dashboard/',
  RedirectView.as_view(url='/static/tenant/core/dashboard/index.html',
  permanent=False), name='tenant-dashboard-shell')`. Responde 302 a un shell
  estático, sin namespace (no está dentro de un `include()`).
- Grep exhaustivo repo-wide de `tenant_dashboard` (F30.5) encontró 2 archivos
  adicionales (`tests/tenant/core/test_routing_logic.py`,
  `tests/tenant/landing/test_landing_empresa.py`) que mencionan
  `tenant_dashboard:index` solo en **docstrings**, no en llamadas `reverse()`
  reales — ambos ya verifican correctamente contra la ruta literal
  `/dashboard/` vía `response.url`. No requieren cambio.
- Solo 2 call sites reales usan `reverse("tenant_dashboard:index")`:
  `tests/general/test_system_health.py:207`,
  `tests/tenant/landing/test_private_routing.py:71`.

**Decisión:** no se crea `tenant_dashboard:index` (violaría F30.8: no crear
un contrato solo para que un test pase). El nombre correcto ya registrado es
`tenant-dashboard-shell`. Es un fix de test, no de producción — la ruta
`/dashboard/` funciona igual que antes.

**Fix:** ambos call sites corregidos a `reverse("tenant-dashboard-shell")`.

**Hallazgo adicional descubierto al verificar (no visible hasta ahora por el
`NoReverseMatch` previo):**
`tests/tenant/landing/test_private_routing.py::test_authenticated_root_redirects_to_dashboard`
esperaba que `response.url == reverse("tenant-dashboard-shell")` (`/dashboard/`),
pero `TenantRootView.get()` (`config/urls_tenant.py:78-80`) redirige a los
usuarios autenticados **directamente** a
`/static/tenant/core/dashboard/index.html`, sin pasar por `/dashboard/` como
paso intermedio. Clasificación: TEST_BUG (expectativa de test no coincide
con el routing real, independiente del nombre de URL usado). Fix: la
aserción ahora compara contra el path estático real
(`/static/tenant/core/dashboard/index.html`), no contra `reverse(...)`.

---

## F30-C — Colisión de nombre `user-list`/`user-detail` (Hallazgo F29-007)

**Clasificación:** URL_CONTRACT real (colisión de `basename` de router DRF),
no `WRONG_ROOT_URLCONF`, no `WRONG_LOOKUP`.

**Naturaleza exacta de la colisión (demostrada antes de tocar producción,
por regla F30.12):**

| ViewSet | Registro | basename (antes) | Incluido en | Path |
|---|---|---|---|---|
| `PublicUserViewSet` | `apps/public/accounts/api/public_urls.py:8` | `"user"` | `config/public_api_urls.py` -> `config/urls_public.py:95` (`api/public/v1/`, sin namespace) | `/api/public/v1/users/` |
| `UserAdminViewSet` | `apps/public/accounts/api/viewsets.py:171` (`VIEWSETS`) | `"user"` | `apps/public/accounts/api/urls.py` -> `config/urls_public.py:104` (`api/admin/v1/accounts/`, sin namespace) | `/api/admin/v1/accounts/users/` |

Ambos `include()` cuelgan del mismo urlconf plano (`config.urls_public`), sin
namespace, con el **mismo** basename `"user"` -> ambos registran
`user-list`/`user-detail` en el mismo `reverse_dict`. Como
`api/public/v1/` se registra primero en `urlpatterns`
(`config/urls_public.py:95` antes que línea 104),
`reverse("user-list")`/`reverse("user-detail")` resolvía siempre al endpoint
PÚBLICO — confirmado empíricamente en F29 y no modificado en este hallazgo.

**Por qué no es un simple typo:** ambos ViewSets son implementaciones reales,
funcionales y casi paralelas de CRUD de `User` (mismos mixins, mismos
serializers, mismo `user_service`), diferenciados solo por: `PublicUserViewSet`
permite `create` público (`AllowAny`) y expone `me`; `UserAdminViewSet` es
management puro, sin acción pública. Ninguno es código muerto ni un
duplicado exacto — no se justifica eliminar ninguno de los dos (fuera de
alcance de F30; sería un rediseño de API, no un fix de contrato de nombre).

**SSoT determinado:** `PublicUserViewSet` conserva el nombre `"user"` sin
cambios — es el que actualmente "gana" `reverse()`, no tiene otros
consumidores que dependan de un nombre distinto, y `config/urls_public.py`
ya lo trata como ruta determinística deliberada (comentario explícito
"tests/middleware swaps cannot hide it" en la ruta fallback
`public-user-create-root` de la misma vista). Cambiar su nombre habría sido
el movimiento de mayor riesgo sin beneficio.

**Fix aplicado:** `UserAdminViewSet` renombrado de basename `"user"` a
`"admin-user"` (`apps/public/accounts/api/viewsets.py:171`). **Ningún path
HTTP cambia** — solo el nombre interno usado por `reverse()`. Grep
repo-wide confirmó que los únicos consumidores de `reverse("user-list")`/
`reverse("user-detail")` en todo el repositorio eran los 16 call sites de
los 2 archivos de test listados abajo (ninguna plantilla, JS ni otro
Python los usa) — cambio de bajo riesgo, sin romper contratos externos.

**Consumidores actualizados (16 call sites, 2 archivos — ambos documentan
explícitamente en su docstring que prueban `/api/admin/v1/accounts/users/`,
confirmando que **ya estaban ejercitando el endpoint equivocado** por la
colisión):**
- `tests/public/accounts/test_user_crud_api.py` (11 sites):
  `reverse("user-list")` -> `reverse("admin-user-list")`,
  `reverse("user-detail", ...)` -> `reverse("admin-user-detail", ...)`.
- `tests/public/accounts/test_admin_users_list.py` (5 sites): idem.

**Regla aplicada (F30.12):** SSoT determinado con evidencia antes de tocar
producción; rename mínimo, no arbitrario; retrocompatibilidad de paths HTTP
preservada al 100%; consumidores/tests actualizados en el mismo cambio.

**Hallazgo adicional descubierto al verificar -- confirma exactamente la
sospecha documentada en F29 ("bug silencioso: el test puede pasar
ejercitando el endpoint equivocado"):** tras el rename, 3 de los 16 tests
(`test_create_user_requires_admin`, `test_create_user_success`,
`test_create_user_duplicate_email` en `test_user_crud_api.py`) fallaron por
primera vez -- porque **ahora sí golpean el endpoint admin real**
(`UserAdminViewSet`) en vez del público (`PublicUserViewSet`) que los
enmascaraba antes. Causa: `UserCreateSerializer.password2` es
`required=True`, pero `PublicUserViewSet.create()` (no `UserAdminViewSet`)
tiene una conveniencia propia que auto-rellena `password2 = password` cuando
falta (`apps/public/accounts/api/public_viewsets.py:68-69`) -- los tests,
escritos contra el comportamiento observado del endpoint equivocado, nunca
enviaban `password2`. Clasificación: TEST_BUG (payload incompleto para el
contrato real de `UserAdminViewSet`, no falta ninguna funcionalidad de
producción -- un panel admin real pide password+confirmación explícitos).
Fix: agregado `password2` a los 2 payloads de creación exitosa; corregida
además la aserción de `test_create_user_duplicate_email`, que leía
`response.data["error"]` (clave que no existe en el formato de error
estándar de DRF) en vez de `response.data["email"]` (formato real que
retorna `serializer.is_valid(raise_exception=True)` sin wrapper custom).

---

## F30-D — 10 errores de colección bloqueaban el 100% de la regresión global (nuevo, no reportado en F27-F29)

**Clasificación:** HARNESS_BUG (7 casos) + TEST_BUG real (1 caso) +
producción-adyacente/export gap (1 caso, ver F30-E) + entorno/bytecode
obsoleto (2 casos).

Primer intento real de ejecutar el comando canónico documentado
(`make test` == `pytest` sin argumentos, `Makefile` `test:` target) en toda
la vida de este arco de fases F21-F30: **abortó en fase de colección con 10
errores, 0 tests ejecutados** (`21 skipped, 5 warnings, 10 errors in
123.59s`). Nunca antes se había invocado pytest sin argumentos/paths
acotados en F21-F29.

| # | Archivo | Error | Clasificación | Fix |
|---|---|---|---|---|
| 1 | `documentacion/_archive/test_isolation_output.txt` | `UnicodeDecodeError` (binario) | HARNESS_BUG | `pytest.ini`: `documentacion` añadido a `norecursedirs` |
| 2 | `documentacion/_archive/test_out.txt` | idem | HARNESS_BUG | idem |
| 3 | `documentacion/_archive/test_output.txt` | idem | HARNESS_BUG | idem |
| 4 | `scratch/test_client_headers.py` | `RuntimeError: Database access not allowed` (script ad-hoc, no test real) | HARNESS_BUG | `pytest.ini`: `scratch` añadido a `norecursedirs` |
| 5 | `scratch/test_delete_simple.py` | idem | HARNESS_BUG | idem |
| 6 | `scratch/test_delete_tenant.py` | idem | HARNESS_BUG | idem |
| 7 | `scripts/test_onboard.py` | idem | HARNESS_BUG | `pytest.ini`: `scripts` añadido a `norecursedirs` |
| 8 | `apps/public/console/tests.py` | `import file mismatch` contra `apps/public/console/tests/` (paquete real) | HARNESS_BUG (colisión de nombre módulo, no bytecode obsoleto pese al HINT genérico de pytest) | `git mv` a `apps/public/console/tests/test_legacy_public_tenants_api.py` |
| 9 | `apps/tenant/proyectos/tests.py` | idem contra `apps/tenant/proyectos/tests/` | HARNESS_BUG | `git mv` a `apps/tenant/proyectos/tests/test_legacy_smoke_financials.py` |
| 10 | `tests/tenant/empresa/test_empresa_ssoT.py` | `ImportError: cannot import name 'get_empresa_data'` | Ver F30-E (no es TEST_BUG puro) | Ver F30-E |

**Casos 8-9 — investigación antes de mover (no se asumió duplicado
byte-idéntico como en F27-005):** se comparó el contenido de cada
`tests.py` legacy contra su paquete `tests/` hermano por nombre de
clase/método. **Ninguno de los dos es duplicado** — `console/tests.py`
prueba el API REST paginado real `/api/public/v1/tenants/`
(`ConsoleAPIConsumptionTests`, etc., usando `TenantTestCase` crudo, patrón
pre-F27/28), mientras `console/tests/` prueba los endpoints DataTables de
la consola admin (`TenantsDataTableViewTest`, etc.) — cobertura
complementaria, no redundante. Igual para `proyectos/tests.py` (smoke de
arquitectura + cálculos financieros: `calcular_costo_mano_obra`,
`calcular_indicadores_financieros`) vs `proyectos/tests/` (scope
organizacional F7/F13/F14, tabla, tareas diarias) — cero solapamiento de
nombres. **Decisión:** mover (no eliminar) para preservar el 100% de la
cobertura, resolviendo únicamente la ambigüedad de import Python
`apps.public.console.tests` / `apps.tenant.proyectos.tests` (paquete vs
módulo con el mismo nombre punteado).

**Nota:** los `tests.py` movidos siguen usando `TenantTestCase` crudo (no
`SintelTenantTestCase`) — migrarlos es trabajo de F28/futuro, explícitamente
fuera de alcance de este fix (que es solo de colección/import, F30.19).

---

## F30-E — `get_empresa_data` no exportado desde `apps.tenant.empresa.services` (nuevo)

**Clasificación:** PREEXISTING_PRODUCTION_BUG (no solo TEST_BUG).

**Evidencia:** `get_empresa_data()` está completamente implementado en
`apps/tenant/empresa/services/crud_service.py:58` (forma correcta: retorna
`None` si no hay empresa, dict completo con `id`/`nit`/`logo`/`website`/
`moneda`/etc. si existe), pero `apps/tenant/empresa/services/__init__.py`
nunca lo reexportaba — solo exportaba `get_empresa_emisor_data` (función
distinta, con semántica de "raise si no configurado", usada por facturas).

**Impacto real en producción, no solo en tests:**
`apps/tenant/core/services/empresa.py` (`get_mi_empresa()` y
`get_empresas_snapshot()`, consumidos por el dashboard/API
`/api/v1/core/mi-empresa/`) **ya importaba** `get_empresa_data` desde
`apps.tenant.empresa.services` esperando que existiera ahí — el
`ImportError` resultante era silenciosamente tragado por un `except
Exception: return None` / `return []` genérico dentro de la función. Esto
significa que `get_mi_empresa()`/`get_empresas_snapshot()` **fallaban
silenciosamente en el 100% de las invocaciones**, siempre devolviendo
`None`/`[]` sin importar si la Empresa existía — probablemente desde que se
introdujo esa dependencia (no se pudo determinar el commit exacto sin
`git blame`, fuera de alcance de este hallazgo).

`tests/tenant/empresa/test_empresa_ssoT.py` (import roto en línea 10)
depende de la misma función y por eso fallaba en colección — el fix del
export resuelve ambos problemas con el mismo cambio de una línea.

**Fix:** `apps/tenant/empresa/services/__init__.py` — agregado
`from .crud_service import get_empresa_data` y `'get_empresa_data'` a
`__all__`.

**Pendiente de verificación (F30.19-23):** confirmar vía regresión que
`test_core_mi_empresa_endpoint`/`test_core_mi_empresa_setup_required` pasan
ahora con datos reales (antes probablemente pasaban "por accidente" ya que
`setup_required=True` siempre, incluso con empresa creada — hay que
verificar si el test anterior a este fix realmente detectaba el bug o
también fallaba en falso positivo).
