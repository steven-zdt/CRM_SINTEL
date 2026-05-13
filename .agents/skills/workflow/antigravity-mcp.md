# Skill: Antigravity + MCP Workflow

**Carga cuando:** mejorar reglas de agentes, MCP, skills, auditorias automaticas o flujos Antigravity.

## Orden Operativo

1. Leer `MEMORY.md` y `AGENTS.md`.
2. Localizar la app afectada y leer `AUDITORIA_FLUJO_*.md`.
3. Consultar skills disponibles con el MCP (`list_available_skills`) o revisar `.agents/skills`.
4. Elegir maximo 3 skills para la tarea.
5. Ejecutar checks MCP o fallback local antes de cerrar.

## Skills Recomendadas

- Service Layer: `backend/service-layer`
- ViewSets DRF: `backend/drf-viewset`
- Serializers: `backend/drf-serializers`
- Tenant isolation: `backend/django-tenant`
- Frontend FSD: `frontend/crud-fsd`
- HTMX: `frontend/htmx`
- Tabulator: `frontend/tabulator`
- Security/IDOR: `security/zero-trust`, `anti-idor-security`

## Marco General Por App

Todo flujo debe aceptar `app_name` y funcionar para cualquier modulo en `apps/tenant/<app_name>`.

- Usar `sintel_app_quality_plan(app_name, scope)` como entrada general.
- No hardcodear nombres de modulos de negocio en tools, prompts, comandos o docs.
- Usar rutas parametrizadas: `apps/tenant/<app_name>/`, `templates/tenant/<app_name>/`, `static/<app_name>/js/`.
- Las validaciones enfocadas deben usar `python -m pytest apps/tenant/<app_name>/tests -q`.
- Si una validacion necesita tabla SQL, el caller debe pasar la tabla; no usar defaults de una app concreta.

## Checks Minimos

```powershell
python -m py_compile <archivos.py>
python manage.py check
python -m pytest <tests enfocados> -q
docker compose config
```

## Modo Flash

Usar cuando el usuario pida respuestas rapidas, validacion puntual, estado de avance o mejoras de Antigravity.

- `antigravity_official_context`: contexto oficial resumido de Google Antigravity y Gemini Flash.
- `antigravity_flash_brief`: plantilla corta para responder con resultado, evidencia y siguiente accion.
- `antigravity_flash_check`: control de calidad para evitar respuestas largas, vagas o sin fuente oficial.

Contrato de respuesta:

1. Resultado primero.
2. Evidencia minima y verificable.
3. Sin relleno ni historia larga.
4. Fuentes oficiales cuando se mencionen docs oficiales o informacion actual.

## MCP A Mejorar

- Descubrir skills en carpetas con `SKILL.md`.
- Descubrir skills markdown legacy bajo `.agents/skills/<grupo>/<skill>.md`.
- Mantener `documentacion/skills` como fuente documental secundaria.
- Exponer rutas e instrucciones sin cargar todo el arbol de skills al contexto.
