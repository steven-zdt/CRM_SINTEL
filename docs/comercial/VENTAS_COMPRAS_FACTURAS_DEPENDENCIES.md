# VENTAS_COMPRAS_FACTURAS_DEPENDENCIES — matriz real de dependencias

Mision VENTAS-COMPRAS-FACTURAS-01 (2026-09-09). Matriz construida por
lectura directa del codigo (grep + lectura completa de los archivos
citados), no de documentacion historica. Cada fila cita archivo/simbolo
real.

## Matriz (estado real ANTES de esta mision, luego columna "Post-mision")

| Origen | Destino | Relacion real hoy | Evidencia | Clasificacion | Post-mision |
|---|---|---|---|---|---|
| `ventas` | `facturas` | **PUSH/WRITE** — `VentaBusinessService.procesar_y_facturar_venta()` construye DTO DIAN completo (CUFE, XML UBL 2.1, firma XAdES-EPES) e invoca `FacturaBusinessService.crear_factura_desde_venta()` | `apps/tenant/ventas/services/business_service.py:491-698` (linea real tras el fix), endpoint `POST /api/v1/ventas/{uuid}/procesar-facturar/` (`viewsets.py:108`) | **FORBIDDEN** (viola la regla objetivo de esta mision) | **BLOQUEADO** (Fase 8) — `EMISION_FISCAL_VENTA_AUTORIZADA = False`, rechaza con 403 antes de cualquier escritura. Codigo DIAN intacto, inalcanzable. |
| `cotizaciones` | `ventas` → `facturas` | **PUSH/WRITE indirecto** — `CotizacionService.facturar_venta_de_cotizacion()` reutiliza el flujo de arriba (`venta_existente=venta`) | `apps/tenant/cotizaciones/services/business_service.py:597-650` (COTIZACIONES-02) | **FORBIDDEN** (hereda la violacion de `ventas→facturas`) | **BLOQUEADO** automaticamente (mismo guard, un solo punto de escritura real) |
| `compras` | `facturas` | **NO EXISTE** — `OrdenCompra`/`RecepcionCompra` no tienen campo, FK, ni import relacionado con `facturas` | grep exhaustivo `Factura\|FacturaBusinessService\|factura_uuid\|CUFE` en `apps/tenant/compras/` → 0 resultados reales (solo 1 mencion en docstring de test, no codigo) | **N/A** — ya cumple la regla, nunca tuvo este camino | Sin cambios necesarios |
| `facturas` | `ventas` | **READ parcial, unidireccional** — `Venta.factura_asociada` es `OneToOneField` DIRECTO a `facturas.Factura` (no soft-reference UUID, a diferencia del resto del bounded context de Facturas) | `apps/tenant/ventas/models.py:174-181` | **CONTROLLED** (funciona, pero rompe el patron Bounded Context §18 que el resto de `facturas.*_uuid` sigue) | Sin cambios en esta mision (ver DEFERRED #1 — cambiarlo a soft-reference es un refactor de esquema con riesgo de datos, no demostrado como necesario) |
| `facturas` | `compras` | **NO EXISTE** — ningun modelo de Compras referencia Factura | idem arriba | **N/A** | DEFERRED (Fase 9) — no hay contrato de consumo, ver seccion "DEFERRED" abajo |
| `facturas` (XML externo) | `facturas` (persistencia) | **Pipeline real y correcto** — `FacturaBusinessService.guardar_desde_dto()`, idempotente por CUFE, `_resolver_naturaleza()` (`emisor_nit == empresa.nit → VENTA`) | `apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md:272,275` | **ALLOWED** (es el camino objetivo de esta mision, ya construido) | Sin cambios — SSoT confirmado, no se duplica |
| `ventas` | `inventario` | **CONTROLLED** — `VentaBusinessService._generar_salida_inventario()` → `KardexService.registrar_movimiento(SALIDA_VENTA)`, idempotente por `UniqueConstraint` (F23) | `apps/tenant/ventas/services/business_service.py` (metodo `_generar_salida_inventario`) | **ALLOWED** (cumple arquitectura Pull/Controlled ya establecida) | Sin cambios |
| `compras` | `inventario` | **CONTROLLED** — `RecepcionCompraBusinessService.confirmar_recepcion()` → `MovimientoInventario` (F21) | `apps/tenant/compras/services/business_service.py` | **ALLOWED** | Sin cambios |
| `inventario` | `contabilidad` | **PULL** — `ExtractorInventario` (F22), Contabilidad consulta, nunca Inventario escribe en Contabilidad | `apps/tenant/contabilidad/integracion/extractores/inventario.py` | **ALLOWED** | Sin cambios (Fase 6 de la mision: no tocar sin blocker real, no hay blocker) |
| `compras` | `proveedores` (CxP) | **CONTROLLED** — `_sincronizar_cuenta_por_pagar()` al aprobar la orden (2026-08-26), independiente de si existe Factura DIAN | `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md` §10 | **ALLOWED** (fuera del alcance directo de esta mision, documentado como contexto — confirma que Compras nunca dependio de Factura para su ciclo de negocio real) | Sin cambios |
| `facturas` | `bancos` | **PULL** — `BancosBridge.obtener_total_conciliado()` | `apps/tenant/facturas/.agent/COMPLETO_FLUJO_FACTURAS.md` v3.11.0 | **ALLOWED** | Sin cambios (Fase 6: no modificar sin necesidad demostrada) |
| `facturas` | `cotizaciones` | **Soft-reference READ** — `cotizacion_uuid` + `FacturaInterAppAPI.resolve_cotizacion()` | `apps/tenant/facturas/.agent/VINCULACION_COTIZACION_v3101_COMPLETO.md` | **ALLOWED** (patron correcto, referencia para el contrato DEFERRED de abajo) | Sin cambios — es el precedente a seguir cuando se implemente el consumo real |

## `FacturaInterAppAPI` — el contrato de lectura YA existe, pero nadie en Ventas/Compras lo usa

`apps/tenant/facturas/.agent/INTER_APP_API_v3100.md` documenta un
contrato real (`list_all()`, `get_by_id()`, `get_by_cufe()`,
`get_by_numero()`, `resolve_cotizacion()`) pensado exactamente para esto
(Fase 4 de la mision: "determinar si ya existe... selector; DTO;
adapter"). Grep confirmado: **cero imports de `FacturaInterAppAPI` en
`apps/tenant/ventas/` o `apps/tenant/compras/`** — hoy lo usan `bancos`,
`proveedores`/`proyectos` (via docs) y `contabilidad`. Es el candidato
correcto para construir el contrato de consumo de la Fase 9 (ver DEFERRED
#1/#2) — **no se necesita crear una segunda abstraccion**, solo agregar
metodos si `list_all()`/`get_by_numero()` no cubren algun caso especifico
de Ventas/Compras.

**Advertencia de seguridad heredada, no introducida por esta mision:**
`FacturaInterAppAPI.list_all()` devuelve **todas las facturas de todos
los tenants sin filtro `empresa_id`** (documentado como "correcto para
extracciones en lotes... PROHIBIDO exponerlo a HTTP"). Cualquier
consumidor futuro desde Ventas/Compras (Fase 9) DEBE filtrar por
`empresa_id` explicitamente en el punto de consumo — la propia API no lo
hace por diseño. Si se usa, debe ser `FacturaInterAppAPI.list_all().filter(empresa_id=...)`
o un metodo dedicado, nunca expuesto sin filtro a un ViewSet.

## Clasificacion final por relacion

```
ventas       -> facturas      FORBIDDEN -> BLOQUEADO (Fase 8, implementado)
compras      -> facturas      N/A (nunca existio)
facturas     -> ventas        CONTROLLED (parcial, solo lectura de la FK ya escrita)
facturas     -> compras       N/A (DEFERRED, Fase 9)
ventas       -> inventario    ALLOWED (sin cambios)
compras      -> inventario    ALLOWED (sin cambios)
inventario   -> contabilidad  ALLOWED (sin cambios, Pull)
```
