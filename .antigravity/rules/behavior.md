# Comportamiento y Flujo Operativo - Antigravity

**LECTURA OBLIGATORIA ANTES DE CUALQUIER ACCION**

## 🛡️ Enforcement Automático (Simulado)

Antigravity debe emular los hooks de seguridad del proyecto:

1.  **apps/public/ BLOQUEADO**: Cualquier intento de editar `apps/public/` está restringido. Requiere autorización explícita del usuario + RFC + etiqueta `needs-admin-approval`.
2.  **Validación py_compile**: Después de editar cualquier archivo `.py`, Antigravity DEBE intentar compilar el archivo usando `python -m py_compile <archivo>` si el entorno lo permite, o al menos asegurar que no se incluyeron caracteres prohibidos.

## 📋 Checklist antes de proponer código

1.  **Identificar App**: Determinar el módulo afectado y leer su `AUDITORIA_FLUJO_COMPLETO.md`.
2.  **Verificar AGENTS.md**: Asegurar cumplimiento con el stack y restricciones de arquitectura.
3.  **Doble Verificación Semántica (DSV)**: En mutaciones, validar que las entidades pertenezcan al tenant actual (`empresa_id`).

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
