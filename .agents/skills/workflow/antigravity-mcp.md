# Skill: Antigravity + MCP Workflow

**Carga cuando:** mejorar reglas de agentes, MCP, skills, auditorias automaticas o flujos Antigravity.

## Orden Operativo

1. Leer `MEMORY.md` y `AGENTS.md`.
2. Localizar la app afectada y leer `AUDITORIA_FLUJO_*.md`.
3. Cargar máximo 3 skills desde `.agents/skills/` según la tarea.
4. Ejecutar checks MCP o fallback local antes de cerrar.

## Skills por Área

- Backend: `backend/service-layer`, `backend/drf-viewset`, `backend/drf-serializers`, `backend/django-tenant`
- Frontend: `frontend/crud-fsd`, `frontend/htmx`, `frontend/tabulator`, `frontend/vanilla-js`
- Seguridad: `security/zero-trust`, `anti-idor-security`
- Docker/infra: `workflow/docker-services`

## Checks Mínimos (fallback si MCP no disponible)

```powershell
python -m py_compile <archivos.py>
python manage.py check
python -m pytest apps/tenant/<app_name>/tests -q
docker compose config
```

## MCP A Mejorar

- Descubrir skills en carpetas con `SKILL.md`.
- Descubrir skills markdown legacy bajo `.agents/skills/<grupo>/<skill>.md`.
- Exponer rutas e instrucciones sin cargar todo el árbol de skills al contexto.

> Para el flujo completo (Flash mode, General-purpose app rule, Finish): ver `.antigravity/skills/sintel-antigravity-mcp/SKILL.md`.
