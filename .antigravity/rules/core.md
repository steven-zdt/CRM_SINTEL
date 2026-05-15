---
name: reglas
description: Reglas Core — SINTEL v2.62.0 (referencia completa en AGENTS.md)
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

## Karpathy (aplicar antes de cada tarea)

1. Pensar antes de codificar — asumir → preguntar si hay incertidumbre
2. Código mínimo — sin abstracciones especulativas
3. Cambios quirúrgicos — tocar solo lo necesario, no "mejorar" lo adyacente
4. Ejecución basada en objetivos — `Paso → verificar: [check]`

## Service Layer (flujo unidireccional)

`ViewSet → ServiceMixin → business_service.py (DSV) → crud_service.py → Response`

- `selectors.py` — lectura con `.only()`, filtrado por `empresa_id`
- `business_service.py` — reglas de negocio + Doble Verificación Semántica (DSV)
- `crud_service.py` — `@transaction.atomic`, solo escrituras
- `api_mixins.py` — inyecta servicios al ViewSet

## Stack (bloqueado — alternativas requieren autorización)

- Backend: Django, DRF, django-tenants, PostgreSQL, Celery
- Frontend: HTMX, Vanilla JS (namespace `window.Sintel.<App>`), Bootstrap 5, Tabulator
