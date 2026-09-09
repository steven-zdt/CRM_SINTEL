# COTIZACIONES_FLOW — flujo empresarial real (COTIZACIONES-01)

Fecha: 2026-09-08. Complementa `docs/cotizaciones/COTIZACIONES_UI_GUIDE.md`
(2026-08-27, sigue vigente para el resto de la UI) — este documento agrega
la parte que faltaba: la máquina de estados y la conversión a Venta,
implementadas en esta misión.

## Flujo end-to-end (verificado con tests reales, no aspiracional)

```
Cliente (apps.tenant.clientes)
   ↓ FK viva + DSV (get_cliente_for_empresa)
Cotizacion (BORRADOR)
   ↓ POST .../enviar/
Cotizacion (ENVIADA) ──POST .../volver-a-borrador/──> Cotizacion (BORRADOR)
   ↓ POST .../aceptar/
Cotizacion (ACEPTADA)  [terminal — no se puede editar ni cancelar desde aquí]
   ↓ POST .../convertir-a-venta/  (idempotente)
Venta (BORRADOR, cotizacion_uuid = uuid de la Cotizacion)
   ↓ [fuera de alcance de esta misión — flujo propio de Ventas]
   ↓ VentaBusinessService.procesar_y_facturar_venta()
Factura (DIAN)
```

En cualquier punto antes de `ACEPTADA`, `BORRADOR`/`ENVIADA` pueden pasar a
`CANCELADA` (terminal, la cotización no prosperó).

## Lo que esta misión NO tocó (fuera de alcance, decisión explícita)

- **Bridge manual `Factura.cotizacion_uuid`**: sigue existiendo, permite
  vincular una Factura directo a una Cotización sin pasar por una Venta.
  Decisión del usuario: dejarlo como está (ya tiene datos reales en
  producción, romperlo sin reemplazo probado sería peor que la
  inconsistencia de diseño que representa). Documentado en
  `COTIZACIONES_INTEGRATIONS.md`.
- **Catálogo `cotizaciones.Producto/Servicio` vs. `inventario.Producto/
  Servicio`**: siguen sin sincronización. La conversión a Venta copia los
  items como snapshot de texto (no vincula producto/servicio de Inventario)
  precisamente por esto — no hay mapeo real entre ambos catálogos.
- **Catálogo Producto/Servicio inalcanzable en la UI** (`#table-productos`/
  `#table-servicios` sin contenedor en ningún template — hallazgo de
  `COTIZACIONES_RELEASE_GATE.md` 2026-08-27): sigue sin resolver, es un
  `GAP_DE_NEGOCIO` que requiere decisión de producto (¿debe existir un tab
  navegable? ¿el picker de ítems del editor debe consumirlo?), no algo que
  esta misión debía decidir por su cuenta.
- **Permisos graduados** (crear/editar/enviar/aceptar/cancelar/convertir
  como niveles distintos VISOR/OPERADOR/ADMIN): se mantiene el patrón
  binario ya usado en todo el módulo (`IsTenantAdminOrReadOnly` — lectura
  para cualquiera, escritura solo ADMIN), consistente con la misma decisión
  ya tomada para `proveedores` en la misma sesión.

## Verificación end-to-end

Ver `apps/tenant/cotizaciones/tests/test_state_machine.py` y
`test_convertir_a_venta.py` para el flujo completo probado con datos reales
(no solo a nivel HTTP simulado): crear cotización → enviar → aceptar →
convertir a venta → verificar items/totales de la Venta resultante.
