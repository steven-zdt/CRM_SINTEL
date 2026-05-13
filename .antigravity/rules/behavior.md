# Comportamiento y Flujo Operativo - Antigravity

**LECTURA OBLIGATORIA ANTES DE CUALQUIER ACCION**

## 🛡️ Enforcement Automático (Simulado)

Antigravity debe emular los hooks de seguridad del proyecto:

1.  **apps/public/ BLOQUEADO**: Cualquier intento de editar `apps/public/` está restringido. Requiere autorización explícita del usuario + RFC + etiqueta `needs-admin-approval`.
2.  **Validación py_compile**: Después de editar cualquier archivo `.py`, Antigravity DEBE intentar compilar el archivo usando `python -m py_compile <archivo>` si el entorno lo permite, o al menos asegurar que no se incluyeron caracteres prohibidos.

## Principios Karpathy (Caution over Speed) — OBLIGATORIO

Aplicar en CADA tarea, antes de escribir una sola linea de codigo:

1. **Pensar antes de Codificar**: No asumir. Preguntar si hay incertidumbre. Presentar suposiciones explicitas y tradeoffs antes de elegir una interpretacion.
2. **Simplicidad Primero**: Codigo minimo necesario. Si se puede hacer en 50 lineas en vez de 200, reescribir. Prohibido agregar flexibilidad no solicitada o abstracciones de un solo uso.
3. **Cambios Quirurgicos**: Tocar SOLO lo estrictamente necesario. No "mejorar" codigo adyacente. Empatar estilo existente. Codigo muerto no relacionado: reportar, NO borrar sin permiso.
4. **Ejecucion Basada en Objetivos**: Definir un plan verificable antes de ejecutar. `Paso → verificar: [check]`. No avanzar al siguiente paso sin confirmar el anterior.

## 📋 Checklist antes de proponer código

1.  **Karpathy**: Aplicar los 4 principios anteriores como primer filtro.
2.  **Identificar App**: Determinar el módulo afectado y leer su `AUDITORIA_FLUJO_COMPLETO.md`.
3.  **Verificar AGENTS.md**: Asegurar cumplimiento con el stack y restricciones de arquitectura.
4.  **Doble Verificación Semántica (DSV)**: En mutaciones, validar que las entidades pertenezcan al tenant actual (`empresa_id`).

## 🚫 Prohibiciones Estrictas

-   **Emoji/Unicode**: Prohibido en archivos `.py`.
-   **Consultas Abiertas**: Prohibido `.all()`. Siempre filtrar por `empresa_id`.
-   **Signals**: No usar para lógica de negocio.
-   **Contabilidad**: No crear asientos directamente.

## 🏗️ Estructura FSD + Service Layer

-   `selectors.py`: Solo lectura optimizada con `.only()`.
-   `business_service.py`: Lógica de negocio y validación IDOR.
-   `crud_service.py`: Persistencia transaccional.
-   `api_mixins.py`: Inyección de servicios en ViewSets.

## Skills + MCP

Antes de tareas grandes, Antigravity debe consultar las skills disponibles y cargar solo las necesarias:

- Backend CRUD: `backend/service-layer`, `backend/drf-viewset`, `backend/drf-serializers`.
- Frontend: `frontend/crud-fsd`, `frontend/htmx`, `frontend/tabulator`, `frontend/vanilla-js`.
- Seguridad: `security/zero-trust`, `anti-idor-security`.
- Workflow: `workflow/antigravity-mcp` o `.antigravity/skills/sintel-antigravity-mcp`.

Usar MCP cuando este disponible:

- `list_available_skills` para confirmar descubrimiento.
- `audit_bridge_isolation` antes de cerrar cambios en apps tenant.
- Auditorias de estructura/service layer/assets si el cambio toca esas superficies.

Fallback local obligatorio si MCP no esta disponible: `python -m py_compile`, `python manage.py check`, tests enfocados y `docker compose config` cuando se toca Docker.
