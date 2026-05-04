# SINTEL ERP — Instrucciones Obligatorias para Claude Code

**LECTURA OBLIGATORIA ANTES DE CUALQUIER ACCION:**
Lee y aplica `AGENTS.md` (raíz del proyecto) en TODA solicitud, sin excepción.

---

## Enforcement Automático Activo

Este proyecto tiene hooks configurados en `.claude/settings.json` que se ejecutan en cada `Edit`/`Write`:

1. **PreToolUse — apps/public/ BLOQUEADO:** Cualquier intento de editar `apps/public/` es bloqueado automáticamente. Requiere autorización explícita del usuario + RFC + etiqueta `needs-admin-approval`.

2. **PostToolUse — py_compile OBLIGATORIO:** Después de editar cualquier `.py`, el sistema ejecuta `python -m py_compile` automáticamente. Si hay `SyntaxError`, la operación se bloquea y debes corregir antes de continuar.

---

## Reglas de Comportamiento — Vigentes en TODA Solicitud

### SIEMPRE antes de proponer código:
- Leer `AGENTS.md` para verificar restricciones aplicables a la app/módulo objetivo
- Verificar si existe `AUDITORIA_FLUJO_COMPLETO.md` en la app antes de modificarla
- Confirmar que el archivo pertenece a la estructura de Service Layer autorizada

### NUNCA:
- Crear archivos `.py` fuera de la estructura Service Layer sin autorización explícita del usuario
- Usar emojis o caracteres Unicode en archivos `.py` (causa `SyntaxError`)
- Realizar consultas ORM sin filtrar por `empresa_id`
- Usar Django Signals para lógica de negocio
- Crear `AsientoContable` directamente — siempre via `Contabilizador`
- Importar desde `apps.public.*` en apps tenant (excepción: `apps.tenant.core` y `apps.tenant.api`)

### Arquitectura obligatoria:
- Stack: Django + DRF + django-tenants + PostgreSQL + HTMX + Vanilla JS ES6+
- Todos los modelos heredan de `SintelTenantBaseModel`
- Templates tenant: `apps/tenant/<app>/templates/tenant/<app>/` (prefijo `tenant/` obligatorio)
- Integración contable: siempre via `Contabilizador(empresa_id).contabilizar(dto)`

### Flujo de respuesta para solicitudes de código:
1. Identifica la app/módulo objetivo
2. Verifica restricciones en `AGENTS.md` (sección relevante)
3. Lee el archivo actual antes de editar
4. Implementa siguiendo el patrón FSD + Service Layer
5. Verifica que no hay `SyntaxError` (el hook lo valida automáticamente)

---

## Versión de Reglas: SINTEL v2.62.0
## Fuente canónica: `AGENTS.md` (raíz del proyecto)
## Última actualización: 2026-05-04
