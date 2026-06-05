---
name: reglas
description: Reglas Core — SINTEL v3.16.0 (referencia completa en AGENTS.md)
---

# SINTEL Core Rules

> Arquitectura completa en `AGENTS.md`. Leer antes de cualquier cambio.

## Reglas No Negociables

| Regla | Detalle |
|---|---|
| Sin emoji en `.py` | SyntaxError → Django 500 |
| `empresa_id` en toda query | Sin `.all()` ni `.filter()` sin `empresa_id` |
| `.only()` / `.defer()` obligatorio | En todo queryset; nunca `.filter()` suelto |
| `SintelTenantBaseModel` | Todos los modelos tenant heredan de él |
| Sin Signals para negocio | Solo Service Layer |
| `apps/public/` bloqueado | Usar Core Bridge: `apps.tenant.core.services.membership` |
| Sin `AsientoContable` directo | Usar `materializar_asiento_desde_gasto()` |
| UUID lookup | `BaseTenantViewSet` → `lookup_field = "uuid"` |
| FK a `TenantProfile` | Nunca FK a `settings.AUTH_USER_MODEL` en tenant |
| `apps/public/` requiere RFC | + etiqueta `needs-admin-approval` |
| **Zero-Hardcoding (§29)** | **PROHIBIDO** nombres propios de tenants en codigo (`'home'`,`'cliente'`,`'tupapi'`...). SIEMPRE usar ORM: `Client.objects.exclude(schema_name='public').filter(is_active=True)` |
| **Fixtures de test** | **PROHIBIDO** `schema_name='home'` en tests. Usar `test_{app}_{desc}_01` + dominio `.sintel.local` |
| **Scripts/commands** | **OBLIGATORIO** aceptar `--schema <schema_name>` + iterar todos los tenants activos via ORM si no se pasa |

## Karpathy (aplicar antes de cada tarea) — OBLIGATORIO

**Ciclo:** EXAMINAR → PLAN → EJECUTAR → CERRAR (ver `behavior.md` §1).

1. **Pensar antes de codificar** — Si dudas, PREGUNTA antes de tocar archivos.
2. **Codigo minimo** — Sin abstracciones especulativas. Si 200 lineas pueden ser 50, reescribir.
3. **Cambios quirurgicos** — Tocar SOLO lo del objetivo literal. Prohibido "mejorar" lo adyacente.
   - ¿Test roto cerca? → Anotar, NO arreglar.
   - ¿Bug adyacente? → Reportar al cerrar, NO arreglar.
   - ¿Refactor tentador? → NO. Solo el objetivo.
4. **Ejecucion basada en objetivos** — `Paso → verificar: [check de exito concreto]`.
   El check por defecto es `py_compile` / `manage.py check` / leer el diff — **NO una suite de tests.**
5. **Contrato de alcance** — Declarar archivos EN/FUERA de alcance antes del primer Edit (ver `behavior.md` §0).
6. **Tests solo bajo demanda** — NO correr ni escribir tests salvo que el usuario lo pida.
   `py_compile`/`check` son sintaxis, no tests, y se corren siempre (ver `behavior.md` §6).

## Service Layer (flujo unidireccional)

`ViewSet → ServiceMixin → business_service.py (DSV) → crud_service.py → Response`

- `selectors.py` — lectura con `.only()`, filtrado por `empresa_id`
- `business_service.py` — reglas de negocio + Doble Verificación Semántica (DSV)
- `crud_service.py` — `@transaction.atomic`, solo escrituras
- `api_mixins.py` — inyecta servicios al ViewSet

## Stack (bloqueado — alternativas requieren autorización)

- Backend: Django, DRF, django-tenants, PostgreSQL, Celery
- Frontend: HTMX, Vanilla JS (namespace `window.Sintel.<App>`), Bootstrap 5, Tabulator

## Aislamiento Multi-Tenant — 3 Niveles Obligatorios (§24.5 AGENTS.md)

> **Nota:** El agente no escribe tests por iniciativa (ver `behavior.md` §6). Esta regla define
> QUE debe contener el test **cuando el usuario pide escribirlo** — nunca relaja los 3 niveles.

**[OBLIGATORIO]** Toda app tenant con modelos propios DEBE tener `test_multitenant_isolation.py` verificando:

| Nivel | Que valida | Assert |
|---|---|---|
| **1 — Listado** | `GET` desde tenant1 NO expone datos de tenant2 | `assert obj_t2 not in results` |
| **2 — IDOR directo** | `GET /{uuid_t2}/` desde tenant1 → 404 | `assert resp.status_code == 404` |
| **3 — IDOR en FKs** | `POST` con FK de tenant2 desde tenant1 → 400/403/404 | `assert resp.status_code in (400,403,404)` |

**Canon:** `apps/tenant/gastos/tests/test_multitenant_isolation.py`
**[PROHIBIDO]** Tests CRUD sin niveles 2 y 3.

## Zero-Hardcoding — Enforcement Rapido (§29 AGENTS.md)

```bash
# Verificar ANTES de merge — resultado esperado: 0 lineas
grep -rn "'home'\|'cliente'\|'putito'\|'tupapi'\|home\.sintel\.com\|cliente\.sintel\.com" \
    apps/ tests/ scripts/ scratch/ --include="*.py" \
    | grep -v "__pycache__\|migration\|assertNotIn\|\.sintel\.local\|{schema\|schema_name='public'"
```

**Patron canonico para cualquier script/management command sobre tenants:**
```python
from apps.public.tenants.models import Client
tenants = Client.objects.exclude(schema_name="public").filter(is_active=True)
if schema_filter:  # arg CLI opcional --schema <name>
    tenants = tenants.filter(schema_name=schema_filter)
for tenant in tenants:
    with tenant_context(tenant): ...
```
