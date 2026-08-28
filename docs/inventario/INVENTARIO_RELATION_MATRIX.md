# Inventario — Matriz de Relaciones Cross-App (FASE 43, consolidado)

**Fecha:** 2026-08-27. Basado en auditoría real de código (grep + lectura de
archivos), no en documentación previa.

---

## Principio de propiedad (confirmado, sin violaciones)

INVENTARIO es dueño de: Productos, Servicios, Activos Fijos, Categorías,
Stock, Kardex, Movimientos de Inventario, Historial de Servicios.

INVENTARIO NO es dueño de: Facturas, Ventas, Compras, Contabilidad, Bancos,
Proyectos, Clientes, Proveedores — y **nunca las importa** (confirmado por
grep: `from apps.tenant.contabilidad` / `import apps.tenant.contabilidad`
dentro de `apps/tenant/inventario/` da CERO resultados en código `.py` de
producción).

---

## Matriz

| App externa | Dirección real | Mecanismo | Veredicto |
|---|---|---|---|
| **Compras** | Compras → Inventario | `RecepcionCompraBusinessService` (`apps/tenant/compras/services/business_service.py:521-570`) llama `KardexService.registrar_movimiento()` directo, `documento_origen_app='compras'`, `documento_origen_modelo='RecepcionCompraItem'` (idempotencia real vía `UniqueConstraint`) | CONFIRMADO_SEGURO — Inventario no crea la Recepción |
| **Ventas** | Ventas → Inventario | `_generar_salida_inventario()` (`apps/tenant/ventas/services/business_service.py:681-713`) filtra `items.filter(producto__isnull=False)` (excluye Servicios) y llama `KardexService.registrar_movimiento(SALIDA_VENTA, documento_origen_app="ventas", documento_origen_modelo="ItemVenta", ...)` | CONFIRMADO_SEGURO — idempotente, excluye servicios |
| **Facturas** | Facturas → Inventario | Notas Crédito generan `ItemNotaCredito` y disparan `KardexService.registrar_movimiento(ENTRADA_DEVOLUCION)` (`documentacion/arquitectura_general.md:1610-1616`, test real `test_devolucion_nota_credito.py`). `MovimientoInventario.factura_uuid/factura_numero` son soft-refs de trazabilidad. | CONFIRMADO_SEGURO |
| **Gastos** | Gastos → Inventario | `DocumentoSoporte.movimiento_inventario_uuid` (UUIDField, sin FK) + `MovimientoInventarioSelector.get_detail()` para resolver | CONFIRMADO_SEGURO — Pull, dirección correcta |
| **Proyectos** | Proyectos → Inventario (lectura) + Inventario → Proyectos (escritura soft-ref) | `Proyecto.movimiento_referencia` lee `MovimientoInventarioSelector.get_detail()` (Pull correcto). `HistorialServicio.proyecto_uuid/proyecto_nombre` se escribe desde 2 endpoints `vincular_proyecto` — ver hallazgo abajo | **GAP corregido 2026-08-27** (ver sección siguiente) |
| **Contabilidad** | Contabilidad → Inventario (Pull puro) | `ExtractorInventario` (`apps/tenant/contabilidad/integracion/extractores/inventario.py`) lee `MovimientoInventario` directo vía ORM y resuelve `ReglaContable` por concepto (`APP_ORIGEN_PREFIJOS['inventario']`). Inventario nunca llama a Contabilidad. | CONFIRMADO_SEGURO — Pure Pull Model intacto (v3.10.2) |
| **Bancos** | Ninguna | Sin FK, import ni soft-ref en ninguna dirección (grep negativo) | CONFIRMADO_SEGURO — sin relación, no inventada |

---

## Hallazgo real: dos endpoints `vincular_proyecto` con validación DSV desigual

Antes de esta misión existían dos endpoints haciendo la misma operación
(vincular un `HistorialServicio` a un `Proyecto` via soft-ref UUID):

- `ProyectoViewSet.vincular_proyecto` (`apps/tenant/proyectos/api/viewsets.py:384-424`)
  — validaba el proyecto real vía `proyecto_detail_selector(empresa_id=...)`.
- `HistorialServicioViewSet.vincular_proyecto` (`apps/tenant/inventario/api/viewsets.py`)
  — grababa `proyecto_uuid`/`proyecto_nombre` **sin verificar que el proyecto
  existiera ni perteneciera al tenant**.

**Corregido 2026-08-27**: se agregó la misma validación DSV al endpoint de
Inventario (`qs_detail(empresa_id, proyecto_uuid).exists()` antes de guardar),
sin duplicar lógica de negocio — solo una verificación de existencia, mismo
patrón que ya usa `MovimientoInventarioDetailSerializer.validate_producto()`
para sus propias soft-refs. No se tocó el endpoint del lado Proyectos (ya
era correcto). Test real: `test_vincular_proyecto_inexistente_es_rechazado`
en `tests/tenant/inventario/test_crud_permissions.py`.

Severidad original: BAJA-MEDIA (no crítica — `proyecto_uuid` es una soft
reference sin FK, así que no había riesgo de corrupción de integridad
referencial, solo la posibilidad de grabar un `proyecto_nombre` engañoso).

---

## DSV — hallazgo real corregido: `actualizar_movimiento`/`eliminar_movimiento`

`KardexService.actualizar_movimiento()` y `eliminar_movimiento()`
(`apps/tenant/inventario/services/business_service.py`) recibían el objeto
`movimiento` ya cargado y nunca reverificaban `movimiento.empresa_id ==
empresa_id` dentro del propio método — a diferencia de
`registrar_movimiento()`/`registrar_movimiento_activo()` y los 5 métodos de
`TrasladoInventarioService`, que sí re-filtran por `empresa_id` antes de
mutar. No era explotable hoy (el único llamador real,
`MovimientoInventarioViewSet.get_object()`, ya resuelve el objeto
empresa-scoped y lanza 404 si no pertenece al tenant), pero violaba el
principio de "no confiar en un objeto ya cargado" que sí siguen
consistentemente el resto de métodos de escritura del módulo.

**Corregido 2026-08-27**: ambos métodos ahora validan
`movimiento.empresa_id != empresa_id` y lanzan `ValidationError` — defensa
en profundidad para cualquier futuro llamador que no pase por el ViewSet.
Tests reales: `test_actualizar_movimiento_de_otra_empresa_es_rechazado` y
`test_eliminar_movimiento_de_otra_empresa_es_rechazado` en
`test_kardex_service.py`.

---

## Confirmado sin evidencia de necesidad (no inventado)

- Sin integración `Cotización → Inventario` directa: los ítems de
  Cotización son texto libre, no consumen el catálogo Producto/Servicio
  (confirmado en la auditoría de la misión de Cotizaciones, 2026-08-27).
- `costo_promedio` sigue siendo estático por decisión deliberada
  (`documentacion/F23_SALE_INVENTORY_CONTRACT.md` §6) — no se implementó
  costeo FIFO/promedio-ponderado real porque no hay evidencia de que el
  negocio lo necesite hoy; sería un método de costeo nuevo, fuera de
  alcance de una auditoría/corrección.
