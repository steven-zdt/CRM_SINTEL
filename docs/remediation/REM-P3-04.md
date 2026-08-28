# REM-P3-04 — "Valor de inventario": 2 fórmulas divergentes

**Estado:** VERIFIED
**Prioridad:** P3
**App propietaria:** `inventario` (con `dashboard` como consumidor)
**Fecha:** 2026-08-28

## Hallazgo

`InventarioExtractor.extraer_metricas()` (dashboard,
`apps/tenant/dashboard/services/extractores/inventario_ext.py:44-47`)
filtra `activo=True` al sumar `Σ(stock_actual × costo_promedio)`.
`ProductoTableView.get_context_data()` (`apps/tenant/inventario/
views.py:83-85`) sumaba el mismo concepto **sin** ese filtro — el mismo
KPI de negocio ("valor de inventario") podía mostrar cifras distintas en
el Dashboard vs. en la propia pantalla de Inventario.

## Determinación de SSoT

Se adoptó el criterio del Dashboard (`activo=True`) como el correcto, y se
ajustó `ProductoTableView` para igualarlo — no al revés — porque
"inactivo" en este modelo representa un producto retirado del catálogo
comercial (`Producto.activo`), y un KPI de "valor de inventario" orientado
a decisión de negocio razonablemente debería reflejar el valor de lo que
sigue siendo parte del catálogo activo, no de productos ya descontinuados
con stock residual.

## Corrección

`ProductoTableView.get_context_data()` — el `sum()` de `kpi_valor_total`
ahora filtra `if p.activo`, igual que el extractor del dashboard.

## Archivos modificados

- `apps/tenant/inventario/views.py`

## Modelo afectado

Ninguno. Sin migración.

## Tests

`apps/tenant/inventario/tests/test_remediation_p3_04_valor_inventario.py`
(1 test: un producto activo y uno inactivo, confirma que solo el activo se
cuenta). Se revisó `test_tablas_htmx.py::test_producto_tabla_renderiza_
producto_y_kpis` (existente) — crea un producto sin especificar `activo`
(default `True`), no afectado por este cambio, sigue pasando sin
modificación.

## Evidencia

Corrida local, 2026-08-28: 1/1 PASSED, 242.92s.

**Hallazgo del propio ciclo de validación (paso G/I del plan)**: la
primera corrida falló (`0 != Decimal('1000.00')`) porque el `setUp()` del
test no creaba un `TenantProfile` para el usuario de prueba —
`ProductoTableView._resolver_empresa_id()` no pudo resolver la empresa
(`[ProductoTableView] Sin empresa resuelta para user=...`) y devolvió un
queryset vacío, dando un KPI de `0` sin importar si el fix era correcto.
Bug del test, no del código: se agregó la creación de `TenantProfile`
(mismo patrón ya usado en el resto de tests de esta sesión).

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- Se detectó una divergencia relacionada pero **distinta**, no corregida
  aquí (fuera del alcance explícito de este ítem del plan): "alertas de
  stock bajo" usa `stock_actual < stock_minimo` en el dashboard vs.
  `stock_actual <= stock_minimo` en `views.py` — a diferencia del caso de
  "valor de inventario", aquí no hay una respuesta obviamente correcta sin
  una definición de negocio explícita de si "stock igual al mínimo" ya
  cuenta como alerta o no. Se deja documentado para una decisión de
  producto futura, no se resolvió por intuición.
