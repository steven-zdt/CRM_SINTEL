# Inventario — Baseline (FASE 0, misión de modernización integral)

**Fecha:** 2026-08-27. Fuente de verdad: código real, verificado contra
`apps/tenant/inventario/.agent/AUDITORIA_FLUJO_INVENTARIO.md` (v3.10.2,
2026-05-28, "PRODUCTION READY 0 CRÍTICOS").

## 1. Drift confirmado contra la auditoría previa (v3.10.2 → hoy)

El código evolucionó de forma real desde la última auditoría documentada.
La doc anterior NO menciona:

- `TrasladoInventario` (modelo F21 completo: solicitar → aprobar → enviar →
  recibir/cancelar, con `TrasladoInventarioService` y su ViewSet dedicado).
- `MovimientoInventario.sede` (FK opcional a `empresa.Sede`, DT-SEDE-05).
- `MovimientoInventario.documento_origen_app/modelo/id` + `UniqueConstraint`
  de idempotencia (`uniq_movimiento_documento_origen_tipo`).
- `TipoMovimiento.TRASLADO_SALIDA`/`TRASLADO_ENTRADA` (fuera de
  `TIPOS_ENTRADA`/`TIPOS_SALIDA` — no afectan `stock_actual` agregado por
  empresa, solo la distribución por sede vía `StockPorSedeSelector`).
- `services/ingesta_service.py` como archivo propio (DEUDA-05 de la doc
  anterior ya resuelta parcialmente — los 6 ServiceMixins siguen juntos en
  `api_mixins.py`, no separados por modelo).
- Filtrado por `OrganizationalScope`/`sede_ids` en `MovimientoInventarioViewSet`
  (F7/F13/F14 — mismo patrón que cotizaciones/gastos/compras/facturas).

Esto no invalida el resto del documento (modelos base, Kardex core,
desacoplamiento contable v3.10.2 siguen vigentes y verificados de nuevo hoy),
pero confirma la regla "código real es fuente de verdad #1" — la doc quedó
desactualizada por trabajo real (F21) no reflejado.

## 2. Mapa real (Modelo → Selector → CRUD → BusinessService → Mixin → ViewSet → URL → Frontend → DB)

7 modelos concretos: `CategoriaItem`, `ActivoFijo`, `Producto`, `Servicio`,
`MovimientoInventario`, `TrasladoInventario`, `HistorialServicio`.

```
CategoriaItem   → CategoriaItemSelector   → (sin crud_service dedicado, ViewSet usa .objects directo vía Mixin) → CategoriaItemServiceMixin   → CategoriaItemViewSet   → /categorias/   → categorias_list.js/categorias_editor.js
Producto        → ProductoSelector        → crud_service.crear_producto/actualizar_producto → ProductoServiceMixin  → ProductoViewSet  → /productos/  → productos_list.js/productos_editor.js
Servicio        → ServicioSelector        → crud_service.crear_servicio/actualizar_servicio → ServicioServiceMixin  → ServicioViewSet  → /servicios/  → servicios_list.js/servicios_editor.js
ActivoFijo      → ActivoFijoSelector      → crud_service.crear_activo/actualizar_activo     → ActivoFijoServiceMixin → ActivoFijoViewSet → /activos/  → activos_list.js/activos_editor.js
MovimientoInventario → MovimientoInventarioSelector → KardexService (registrar/actualizar/eliminar) → MovimientoServiceMixin → MovimientoInventarioViewSet → /movimientos/ → movimientos_list.js/movimientos_editor.js
TrasladoInventario → TrasladoInventarioSelector → TrasladoInventarioService → TrasladoInventarioServiceMixin → TrasladoInventarioViewSet → /traslados/ → (sin frontend — solo API, documentado F21)
HistorialServicio → HistorialServicioSelector → (create directo vía ViewSet.perform_create, sin crud_service) → HistorialServiceMixin → HistorialServicioViewSet → /historial-servicios/ → offcanvas_historial_servicio.html
```

**Nota real (no en la doc anterior):** `CategoriaItem` y `HistorialServicio`
NO tienen funciones dedicadas en `crud_service.py` — sus ViewSets llaman
`serializer.save()`/`instance.delete()` directamente. Esto es aceptable
(no hay lógica de negocio que justifique una capa intermedia — mismo
criterio que otras apps: CRUD trivial no necesita `crud_service.py` si el
ModelSerializer ya cubre validación) pero se documenta como asimetría real,
no un bug.

## 3. Hallazgos ya confirmados en FASE 0 (evidencia de código, no inventados)

1. **`crud_service.crear_movimiento_raw()` es código muerto confirmado.**
   `grep` de sus consumidores solo devuelve su propia definición y el
   re-export de `services/__init__.py` — cero llamadores reales.
   `KardexService.registrar_movimiento()` crea el `MovimientoInventario`
   inline (`MovimientoInventario.objects.create(...)`, línea 165 de
   `business_service.py`), no delega a `crud_service`. Candidato DEAD_CONFIRMED
   (FASE 45/46).

2. **Regla #2 (Kardex es SSoT) violada dos veces en `ingesta_service.py`.**
   Tanto `materializar_inventario_desde_dto()` (línea 85-92) como
   `materializar_carga_masiva_productos()` (línea 196-203) crean
   `MovimientoInventario.objects.create(tipo=ENTRADA_AJUSTE, ...)`
   directamente y luego llaman `KardexService.recalcular_stock_producto()`
   a mano — duplicando exactamente lo que
   `KardexService.registrar_movimiento(tipo=ENTRADA_AJUSTE, ...)` ya hace
   (incluida la creación del movimiento + el recálculo). El resultado neto
   en `stock_actual` es correcto hoy, pero es lógica de negocio duplicada
   (Regla #1: no reimplementar el motor de Kardex) y además se salta la
   validación de `cantidad > 0` de `registrar_movimiento` (mitigado hoy
   solo porque ambos callers ya chequean `if stock_inicial > 0` antes).
   **Candidato real a corregir en FASE 8/48** (llamar a
   `KardexService.registrar_movimiento()` en vez de duplicar).

3. **Asimetría real en `destroy()` entre Producto/Servicio y ActivoFijo.**
   `ProductoServiceMixin.service_producto_destroy()` y
   `ServicioServiceMixin.service_servicio_destroy()` bloquean el borrado si
   `instance.activo == True` (obliga a inactivar antes de borrar).
   `ActivoFijoServiceMixin.service_activo_destroy()` (línea 199-202 de
   `api_mixins.py`) **no tiene ninguna validación** — borra
   incondicionalmente, incluyendo activos con `estado=ACTIVO` y con
   movimientos de Kardex asociados (que se eliminan en CASCADE igual que
   Producto). No hay evidencia de que ActivoFijo deba comportarse distinto
   a Producto/Servicio aquí — es la misma clase de riesgo (pérdida
   silenciosa de historial Kardex). **Candidato real a corregir en FASE 6**
   (aplicar el mismo guard `estado != BAJA` no es equivalente — se decidirá
   en fase dedicada con evidencia, no se inventa la regla aquí).

4. **Gap de cobertura de tests confirmado, no un bug.** 7 archivos de test
   existen (`test_f21_traslado_inventario.py`,
   `test_organizational_context_adoption.py`, `test_reporting_provider.py`,
   `test_scope_isolation_f14.py`, `test_scope_object_level_f13.py`,
   `test_scope_selectors_f7.py`, `test_tablas_htmx.py`) — todos sobre F21
   (traslados), scope/OSF, HTMX y reporting. **Cero tests existen para:**
   `KardexService.registrar_movimiento()` (stock insuficiente, cálculo
   entradas-salidas, concurrencia), CRUD real de Producto/Servicio/
   ActivoFijo/Categoría vía API, `MovimientoInventarioViewSet` CRUD,
   aislamiento cross-tenant de Producto/Categoría (solo Traslado tiene
   `test_no_se_puede_trasladar_a_sede_de_otro_tenant`), idempotencia de
   `registrar_movimiento()` fuera del contexto de Traslados. Esto es
   significativo para un motor que la propia arquitectura declara SSoT de
   stock. **Prioridad alta para FASE 49/50.**

5. **`PRODUCTO_LIST_FIELDS`/`SERVICIO_LIST_FIELDS`/`ACTIVO_LIST_FIELDS` no
   incluyen `empresa_id` explícito en `.only()`** (a diferencia de
   `CATEGORIA_LIST_FIELDS` y los `*_DETAIL_FIELDS`, que sí lo incluyen).
   Deferred field access en Django dispara una query adicional por fila si
   algún serializer accede a `obj.empresa_id` — a verificar en FASE 47
   (performance) si esto ocurre realmente en los serializers de lista.

## 4. Alcance NO tocado en FASE 0 (pendiente de fases posteriores)

- Frontend JS/templates (FASE 31-42): pendiente de auditoría detallada.
- Integraciones cross-app reales con compras/ventas/facturas/gastos/
  contabilidad/proyectos (FASE 19-23): pendiente de verificación con grep
  real de consumidores.
- `reporting/provider.py` (dashboard/KPI feed): solo tocado tangencialmente,
  tiene su propio test file (`test_reporting_provider.py`) — pendiente de
  lectura completa.

## 5. Reglas de la misión aplicadas desde ya

- Ninguna corrección se hizo todavía — este documento es solo lectura
  (regla explícita de FASE 0: "NO modificar todavía").
- Los 5 hallazgos de arriba están basados en evidencia de código citada con
  archivo:línea, no en suposiciones.
