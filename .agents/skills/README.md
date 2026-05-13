# SINTEL ERP — Índice de Skills de Desarrollo

Skills pequeñas y precisas que se cargan **solo cuando son relevantes**.
Cada skill = 1 responsabilidad = <150 líneas.

## Cuándo Cargar Cada Skill

| Si la tarea involucra... | Carga esta skill |
|---|---|
| Crear/editar modelo, app nueva | `backend/service-layer.md` |
| ViewSet, endpoint REST | `backend/drf-viewset.md` |
| Multi-tenant, empresa_id | `backend/django-tenant.md` |
| Serializer, validación | `backend/drf-serializers.md` |
| HTMX, hx-get, hx-post | `frontend/htmx.md` |
| Tabulator, grid de datos | `frontend/tabulator.md` |
| JavaScript, namespace, módulo | `frontend/vanilla-js.md` |
| Offcanvas Bootstrap, modal | `frontend/offcanvas.md` |
| Formulario, DOM Shield | `frontend/forms.md` |
| QuerySet, `.only()`, prefetch | `database/selectors.md` |
| Migración, `migrate_schemas` | `database/migrations.md` |
| `@transaction.atomic` | `database/atomic.md` |
| Permisos, roles, JWT | `security/zero-trust.md` |
| Autenticación JWT+Session | `security/jwt-auth.md` |
| Asiento contable, movimiento | `contabilidad/asientos.md` |
| DTO, TransaccionEconomica | `contabilidad/dtos.md` |
| Test, pytest, TestCase | `testing/django.md` |
| Test de API, DRF test | `testing/api.md` |
| Módulo nuevo FSD completo | `workflow/fsd-module.md` |
| Debug, error 500, traza | `workflow/debugging.md` |
| MCP, Antigravity, reglas de agente | `workflow/antigravity-mcp.md` |

## Regla de Carga
- **Máximo 3 skills activas a la vez**
- Descargar la skill después de terminar la tarea
- Las skills son READ-ONLY — describen el patrón, no lo reemplazan
- Verificar siempre el archivo `AUDITORIA_FLUJO_*.md` de la app antes de modificar

## Meta-Principio: Karpathy (siempre activo, no requiere carga)

Los principios Karpathy del `AGENTS.md §21` aplican a TODA tarea sin importar qué skill esté cargada:
1. Pensar antes de codificar — no asumir, preguntar si hay incertidumbre
2. Simplicidad primero — código mínimo, sin abstracciones especulativas
3. Cambios quirúrgicos — tocar solo lo necesario, no "mejorar" lo adyacente
4. Ejecución orientada a metas — `Paso → verificar: [check]` antes de continuar
