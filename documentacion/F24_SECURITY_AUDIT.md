# F24 — Auditoria de Seguridad (Zero-Trust, UUID, DSV)

**Fecha:** 2026-08-10
**Alcance:** compras, inventario, ventas, facturas, contabilidad (circuito F21+F22+F23).

## 1. `settings.DEBUG` como posible bypass (F24.37)

```bash
grep -R "if settings.DEBUG" apps/tenant/
```

Resultado: 15 ocurrencias, ninguna dentro de `compras/inventario/ventas/facturas`
directamente relacionada con el circuito F21-F23. Las 2 relevantes por su cercania a
autorizacion (`apps/tenant/core/services/organizational_context.py:139` y
`apps/tenant/core/services/organizational_scope.py:153`) son un fallback **pre-existente,
documentado explicitamente en el propio docstring del modulo**, que solo actua cuando:

1. `settings.DEBUG` es `True` (nunca en produccion), Y
2. el usuario autenticado no tiene `TenantProfile` en el tenant actual (la resolucion
   normal ya fallo).

En ese caso especifico usa la primera `Empresa` del schema (singleton por tenant,
F21) como fallback de desarrollo, dejando un `logger.warning` explicito en cada uso.
No es un bypass de una membresia/rol ya resuelta -- es un valor por defecto para
entornos locales sin `TenantProfile` configurado. Pre-existente a F21/F22/F23, fuera
del alcance de "reabrir sin evidencia" (regla F24.66): no se modifica sin un caso de
explotacion real demostrado.

**Clasificacion:** INFO, pre-existente, documentado. No requiere accion en F24.

## 2. Querysets sin aislamiento (`.objects.all()`) (F24.37)

```bash
grep -rn "\.objects\.all()" apps/tenant/{compras,inventario,ventas,facturas}/services/*.py apps/tenant/{compras,inventario,ventas,facturas}/api/*.py
```

- `selectors.py` (compras): 2 ocurrencias, ambas envueltas inmediatamente en
  `filter_by_scope(Modelo.objects.all(), empresa_id, ...)` -- aislamiento real
  aplicado antes de que el queryset se evalue. No es una violacion.
- `serializers.py` (compras, inventario): ocurrencias de
  `UUIDOrPKRelatedField(queryset=Modelo.objects.all())` -- patron estandar DRF para
  resolver un FK desde su UUID/PK. El aislamiento por `empresa_id` NO se hace aqui a
  proposito: se hace en el `BusinessService` (DSV), tal como exige AGENTS.md
  ("No confiar unicamente en serializer validation. Debe existir BusinessService +
  DSV"). Confirmado con el test F24.12 (ver abajo): un UUID de otro tenant pasado por
  esta ruta es rechazado en la capa de negocio, no en el serializer.

**Clasificacion:** sin hallazgos nuevos.

## 3. `parseInt()` sobre UUIDs (F24.38)

```bash
grep -rn "parseInt(" apps/tenant/{compras,inventario,ventas,facturas,contabilidad}/static/
```

Todas las ocurrencias dentro de `compras/inventario/ventas/facturas` operan sobre
campos enteros legitimos (porcentaje IVA, rangos de consecutivo, indices de array,
ids de plantilla/resolucion que son PK enteras reales, no UUID). Los 2 archivos que
manejan UUIDs de dominio (`inventario_editor.js`, `venta_editor.js`,
`resolucion_editor.js`) tienen comentarios explicitos **prohibiendo** `parseInt()`
sobre esos campos, ya establecidos en fases previas. `contabilidad/` tiene varios usos
de `parseInt()` sobre `cuenta`/`periodo` ids -- fuera del alcance del circuito F21-F23
auditado por F24 (UI legado de Contabilidad, no tocado por ninguna de las 3 fases).

**Clasificacion:** sin hallazgos dentro del alcance de F24.

## 4. `lookup_field = "uuid"` (F24.38)

Confirmado en `apps/tenant/api/base.py:48` (`BaseTenantViewSet`, heredado por
defecto) y explicito en `OrdenCompraViewSet`, `RecepcionCompraViewSet` (via herencia),
`VentaViewSet`, `ResolucionFacturacionViewSet`. Ningun ViewSet del circuito expone PK
entera en URL.

## 5. DSV -- manipulacion de UUID entre tenants (F24.12)

Test real, 2 schemas fisicos (`tenant1`/`tenant2`):
`apps/tenant/contabilidad/tests/test_f24_e2e_multitenant_dsv.py::test_producto_uuid_de_otro_tenant_es_rechazado_limpiamente_en_venta`.

Se inyecta en el payload de una venta de `tenant1` el UUID real de un `Producto` que
solo existe en el schema fisico de `tenant2`. `VentaBusinessService.procesar_y_facturar_venta()`
lo rechaza limpiamente (`ok=False`, codigo 4xx), sin excepcion no controlada y sin
crear ningun `MovimientoInventario` en `tenant1`. La razon estructural: django-tenants
aisla los schemas fisicamente -- el ORM de `tenant1` no puede ver filas de `tenant2` --
y el `BusinessService` resuelve el producto via `.filter(uuid=..., empresa_id=...)`,
por lo que un UUID inexistente en el schema actual simplemente no resuelve (nunca
200 con datos ajenos).

## 6. Multi-tenant E2E completo sin fuga (F24.11)

`test_flujo_completo_compra_venta_asiento_independiente_por_tenant`: circuito
completo (Compra->Movimiento->Kardex->Venta->SALIDA_VENTA->Extractor->Asiento)
corrido end-to-end en `tenant1`; `tenant2` verificado vacio (0 productos con ese
codigo, 0 `MovimientoInventario`, 0 `AsientoContable`) despues.

## Veredicto

0 hallazgos de seguridad nuevos CRITICAL/HIGH. El unico hallazgo con impacto real de
esta auditoria (atomicidad, F24-001) esta documentado en `F24_FINDINGS.md`, no aqui,
porque su naturaleza es de integridad transaccional, no de control de acceso.
