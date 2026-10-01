---
name: sintel-mcp-agent-loop
description: Loop operativo para que un agente MCP administre SINTEL con evidencia y límites.
---
# AGENT LOOP

## Crear productos
Interpretar → descubrir `inventario.Producto` → validar contrato → resolver relaciones → tenant → permisos → duplicados → dry-run → confirmar → BusinessService → devolver IDs → smoke test → audit.

## Actualizar clientes
Identificar cada registro → detectar ambigüedad → preview → validar → lote solo si el servicio lo soporta → ejecutar → verificar.

## Eliminar
Descubrir `delete_mode`; si exige anulación/cancelación/archivo/soft-delete, usar acción real.

## Corregir error
AUDIT → ROOT CAUSE → PROPOSE → APPROVAL → APPLY → TEST → VERIFY.

## Auditar todo
Inventory → project map → domains → APIs → services → dependencies → business rules → tenant security → frontend/API contract → integrations → tests → migrations → governance → production readiness.

## Incertidumbre
Usar `NOT_VERIFIED` y explicar evidencia faltante. Nunca convertir una suposición en acción irreversible.
