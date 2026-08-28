# REM-P2-02 — ¿Cotización debe convertirse automáticamente en Venta?

**Estado:** DEFERRED (decisión documentada como correcta, no un gap a cerrar)
**Prioridad:** P2
**Apps involucradas:** `cotizaciones`, `ventas`
**Fecha:** 2026-08-28

## Investigación

Grafo de dependencias real (`F15_INTEGRATION_BASELINE.md`, verificado por
AST, no por grep de texto): **sin arista `cotizaciones → ventas`
detectada.** Re-confirmado explícitamente en `F15_F20_EXECUTION_STATUS.md`:
*"La matriz del prompt asumía 2 integraciones (`compras→proveedores`
Bridge, `cotizaciones→ventas`) que el código real no tiene así."* Ningún
documento de las 3 misiones de auditoría/modernización de `cotizaciones`
en esta sesión (2026-08-27) menciona una integración pendiente o rota
hacia `ventas` — al contrario, se confirmó explícitamente que el propio
picker de ítems de Cotización usa texto libre, sin siquiera consumir el
catálogo de `inventario.Producto`/`Servicio`, reforzando que Cotización es
un documento comercial deliberadamente desacoplado del resto del ciclo
transaccional.

## Decisión

**No se implementa conversión automática.** No hay evidencia de que sea un
gap accidental — es una ausencia consistente, re-confirmada de forma
independiente en 3 sesiones/documentos distintos (F15 original, F15_F20
execution status, auditoría de cotizaciones de esta sesión). Implementar
`Cotización → Venta` automática por intuición violaría la regla explícita
"No inventar reglas... No implementar por intuición."

**Se documenta como decisión correcta, no como `GAP`.** Si el negocio
confirma que sí necesita ese paso (ej. un botón "Convertir a Venta" que
prellene una `Venta` nueva desde los datos de la `Cotización` aceptada),
es una funcionalidad nueva a diseñar con su propio alcance — no una
corrección de bug, y no se improvisa aquí.

## Archivos que se tocarían si se aprueba (no modificados en esta sesión)

Ninguno identificado aún — requeriría diseño de producto primero (¿qué
campos se prellenan? ¿qué pasa si la Cotización cambia después de
convertida? ¿es 1:1 o puede una Cotización generar varias Ventas
parciales?) antes de cualquier estimación de archivos afectados.

## Governance

N/A — sin cambio de código.
