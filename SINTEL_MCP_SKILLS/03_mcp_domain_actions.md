---
name: sintel-mcp-domain-actions
description: Ejecuta acciones empresariales mediante los BusinessServices y máquinas de estado reales.
---
# DOMAIN ACTIONS

CRUD modifica recursos; las acciones de dominio ejecutan comportamiento empresarial. Una acción real tiene precedencia sobre PATCH genérico.

Descubrir, no inventar, acciones para: cotizaciones (estado, PDF/envío, convertir a venta/proyecto, facturar); ventas (procesar/facturar, anular, estados); facturas (crear desde venta, importar, transmitir, reconciliar, notas); proveedores/CxP (abonos, resolución/materialización); inventario (Kardex, traslado, recepción); compras (orden, recepción); bancos (extracto, movimiento, matching, aplicación, conciliación); contabilidad (catálogos, asientos, períodos); empleados/nómina (contrato, devengo, liquidación, transmisión); proyectos (asignación, presupuesto, pedidos, tareas); gastos (documento soporte y acciones fiscales).

Si existe máquina de estados, rechazar `PATCH estado=X` y usar el método real (`cambiar_estado()` o equivalente).

Efectos externos: `VALIDATE → PREVIEW → CONFIRM → EXECUTE → RECONCILE`. Nunca ejecutar DIAN/Wompi/WhatsApp/email únicamente porque el LLM lo sugiera.
