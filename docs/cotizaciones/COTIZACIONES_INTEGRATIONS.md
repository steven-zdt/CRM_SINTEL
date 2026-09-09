# COTIZACIONES_INTEGRATIONS — mapa de integración real (COTIZACIONES-01)

Fecha: 2026-09-08. Verificado contra código real, contrastado con auditorías
previas del módulo (`.agent/AUDITORIA_FLUJO_COMPLETO.md`,
`documentacion/audits/apps/APP_cotizaciones_AUDIT.md`,
`documentacion/audits/apps/F34_cotizaciones_AUDIT.md`,
`documentacion/audits/cotizaciones/MATRIZ_ESTADOS_COTIZACION.md`,
`docs/integration/CROSS_APP_FINDINGS.md`) — todas coinciden con lo verificado
en código, sin discrepancias significativas (a diferencia de `proveedores`,
donde la documentación estaba desactualizada en varios puntos).

| Integración | Veredicto | Detalle |
|---|---|---|
| **Cotización → Cliente** | ✅ Correcto | FK viva (`SET_NULL`) a `tenant_clientes.Cliente`, con guard DSV explícito (`get_cliente_for_empresa`, `business_service.py:84-97`) — rechaza cliente de otra empresa antes de asignar. |
| **Cotización → Inventario** | ⚠️ Catálogo propio, sin sincronización | `Producto`/`Servicio` de `cotizaciones` son modelos independientes de `inventario.Producto/Servicio`, sin FK ni mapeo. `CotizacionItem` guarda snapshot de precio en la línea. Confirmado: cero imports de `inventario` en todo el módulo. Riesgo real (no solo teórico): el precio cotizado puede divergir del precio real de inventario sin que nada lo detecte. |
| **Cotización → Ventas** | ❌ No existe | `apps/tenant/ventas` no tiene ninguna referencia a `cotizacion` (evidencia negativa, grep 0 resultados). No hay `cotizacion_uuid` en `Venta`, no hay método de conversión. El campo `estado` de `Cotizacion` es decorativo — la única transición real en todo el código es la asignación inicial `BORRADOR` al crear. |
| **Cotización → Facturas** | ⚠️ Bridge directo, salta Ventas | `Factura.cotizacion_uuid` (soft-reference, editable a mano por el usuario) permite vincular una Factura directo a una Cotización, sin pasar por una Venta intermedia. Solo valida existencia, no coherencia de montos/cliente/ítems. Contradice el flujo de capas esperado (Cotización→Venta→Factura), pero **no** viola ADR-001 ni el bridge cross-schema (ambas son apps tenant, acceso vía selector con `empresa_id`). Es lectura pull desde `cotizaciones.eliminar_cotizacion()` (bloquea borrado si hay factura vinculada) + lectura pull desde `facturas.CotizacionBridge` (resuelve el número/uuid al mostrar la factura). |
| **Cotización → Contabilidad/Retenciones** | ✅ Sin violación de ADR-001 | Cero imports de `contabilidad`, cero creación de `AsientoContable`/`MovimientoContable`. IVA con fórmula propia (`iva_porcentaje` configurable por perfil), razonable dado que es un documento pre-venta sin obligación fiscal real. |
| **Cotización → Proyectos** | ➖ Ninguna integración | Confirmado con evidencia negativa. `apps/tenant/proyectos` solo lee `Cotizacion` indirectamente vía el mismo bridge de Facturas (KPIs), no hay relación directa. |
| **Permisos** | ⚠️ Binario, no granular | `IsTenantMember` (lectura) + `IsTenantAdminOrReadOnly` (escritura, solo ADMIN) en los 4 ViewSets principales. `ConfiguracionCotizacionViewSet` es aún más laxo (`IsAuthenticated + IsTenantMember`, sin exigir ADMIN para editar prefijos/numeración — inconsistente con el resto). No existen acciones `enviar`/`aprobar`/`archivar`/`convertir-a-venta` en absoluto — no hay nada que diferenciar todavía. |
| **Multi-tenancy** | ✅ Mayormente correcto | Todos los selectors públicos filtran `empresa_id`. Gap menor sin explotación real: `crud_service.py` `get_cotizacion_for_totals`/`get_items_subtotal` no filtran `empresa_id` (reciben IDs ya pre-validados por el único caller, `calcular_totales()`) — sin defensa en profundidad, vale la pena blindar. |

## Hallazgos adicionales (no integraciones, pero relevantes)

- **PDF "sincronizado" desperdiciado**: `crear_preforma`/`actualizar_cotizacion` generan un PDF que nunca se persiste ni se usa — se descarta tras loguear éxito/fallo. El PDF real que ve el usuario se regenera desde cero en `exportar-pdf`. No es un bug funcional (no hay PDF desactualizado visible), pero es trabajo de servidor desperdiciado en cada create/update.
- **`_cotizacion_anexo_upload_path()`** (`models.py:15-16`) definida pero sin ningún `FileField` que la use — función huérfana.
- **Bytecode huérfano**: `__pycache__` tiene `.pyc` de `test_integration.py`, `test_models.py`, `test_permissions.py`, `test_tasks.py`, `test_views.py` sin `.py` fuente actual — evidencia de limpieza previa incompleta (cosmético, `__pycache__` no forma parte del repo real).
