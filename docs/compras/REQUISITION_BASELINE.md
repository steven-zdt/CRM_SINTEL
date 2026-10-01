# REQUISITION_BASELINE.md — Auditoria Previa (Fase 1)

**Mision:** `PLAN_IMPLEMENTACION_REQUISICIONES_COMPRAS.md`
**Fecha auditoria:** 2026-09-25
**Auditor:** Claude Sonnet 5 (Anthropic)
**Regla aplicada:** NO se ejecuto pytest/tests durante esta fase (plan §0.2). Solo lectura/grep/inspeccion estatica. No se modifico ningun archivo de codigo.

---

## 1. Estado real de `apps/tenant/compras/`

### 1.1 Modelos (`models.py`, 488 lineas)

| Modelo | Base | Notas clave |
|---|---|---|
| `PlantillaOrdenCompra` | `SintelTenantBaseModel` | Numeracion propia (prefijo+rango+consecutivo), `CheckConstraint` rango/consecutivo. |
| `OrdenCompra` | `SedeAwareModel` | `sede` obligatoria (NOT NULL, ya endurecida via migraciones 0006/0007). `proveedor` FK PROTECT obligatoria. `proyecto` FK SET_NULL opcional. `documento_soporte` FK SET_NULL opcional (a `tenant_gastos.DocumentoSoporte`). `factura_asociada` OneToOne SET_NULL opcional a `facturas.Factura` (vinculo MANUAL, nunca automatico — mismo patron que `Venta.factura_asociada`). **NO tiene campo `requisicion` todavia** — es el punto de integracion principal a agregar (plan §14). Estados: BORRADOR/PENDIENTE/APROBADA/PARCIAL/RECIBIDA/ANULADA. |
| `ItemOrdenCompra` | `SintelTenantBaseModel` | `item_inventario_uuid` soft-ref opcional. **Ya tiene `cantidad_recibida`** + `cantidad_pendiente` (property) + `CheckConstraint(cantidad_recibida <= cantidad)` — el mecanismo de atencion parcial por item que el plan pide para Requisicion (§16-17) YA EXISTE en Compras a nivel de OrdenCompra/RecepcionCompra; Requisicion debe seguir el mismo patron (acumular contra `RequisicionCompraItem`, nunca inventar un segundo mecanismo). |
| `RecepcionCompra` / `RecepcionCompraItem` | `SedeAwareModel` / `SintelTenantBaseModel` | Eventos de recepcion parcial contra una OC. Solo `CONFIRMADA` genera `MovimientoInventario` (Kardex). Inmutable una vez CONFIRMADA (no revierte). |

**Numeracion:** cada dominio implementa su propio esquema (PlantillaOrdenCompra en Compras; ResolucionDIAN+consecutivo en Gastos/DocumentoSoporte; ConfiguracionCotizacion en Cotizaciones) — **no existe un servicio de numeracion generico reutilizable**. Patron comun confirmado: `F('consecutivo_actual') + 1` + `.update()` dentro de `select_for_update()` (compras/business_service.py:165, ya "RESUELTO" DT-COMPRAS-01). RequisicionCompra debe construir su propio numerador `REQ-000001` con el mismo patron — consistente con la convencion existente, no una duplicacion.

### 1.2 Service Layer (FSD, completo)
`services/{business_service.py (734L), crud_service.py (370L), selectors.py (195L), api_mixins.py (194L)}`. Sigue el flujo canonico ViewSet→ServiceMixin→BusinessService(DSV)→CRUDService. `_obtener_entidad_por_id_o_uuid()` es el helper DSV anti-IDOR reutilizable ya usado para plantilla/proveedor/proyecto/documento_soporte — **reutilizar el mismo patron para requisicion en el nuevo `crear_orden_desde_requisicion()`**, no reinventar.

### 1.3 API
`api/{viewsets.py, serializers.py, urls.py}`. Base `/api/v1/compras/`. Router: `plantillas/` + raiz para ordenes. Acciones custom ya establecidas: `render-offcanvas/{crear,editar,detalle}`, `cambiar-estado`, `siguiente-consecutivo`. Permisos: `[IsTenantMember(), IsTenantAdminOrReadOnly()]` (import solo desde `apps.tenant.api.permissions`, regla global).

### 1.4 Frontend — patron de sub-pestañas YA EXISTENTE
`compras_list.html` usa `nav-pills` (`#compras-subnav`) con 2 sub-tabs actuales: `#subtab-ordenes` y `#subtab-plantillas` (mismo patron que Clientes/Proveedores, HTMX lazy-load por tab). **Confirma el plan §27**: agregar Requisiciones como una TERCERA sub-pestaña (`#subtab-requisiciones`) dentro de `workspace/#compras`, reutilizando exactamente este patron — NO crear un tab global nuevo `workspace/#requisiciones`.

Assets cargados unicamente desde `workspace.html extra_js` (bug historico BUG-01 ya corregido — no volver a incluir `assets_compras.html` dentro de un template de listado).

### 1.5 Bridge Compras→Proveedores (CxP) — patron a replicar, no modificar
`OrdenCompraBusinessService.cambiar_estado_orden_compra()` llama `_sincronizar_cuenta_por_pagar(orden)` cuando `nuevo_estado == 'APROBADA'`, con import local de `CuentasPagarBusinessService` (mismo patron de bridge cross-app que usa Inventario desde Recepciones). Idempotente via `get_or_create(empresa, proveedor, numero_factura)`. **Requisicion NUNCA debe tocar CxP directamente** — esa responsabilidad se queda en `OrdenCompraBusinessService`, sin cambios.

### 1.6 Deuda tecnica activa
Ninguna abierta relevante a Requisiciones — las 6 + 4 encontradas (BUG-01..06, CO-1..4) estan todas `CORREGIDO`/`RESUELTO` y verificadas con pytest (43+10 passed, documentado en el propio `.agent/AUDITORIA_FLUJO_COMPRAS.md`). Unico pendiente documentado sin relacion: DT-COMPRAS-03 tambien resuelto.

---

## 2. Centro de Costo — NO EXISTE UN SSoT REAL (hallazgo critico para el diseño)

Busqueda exhaustiva (`grep -ri "centro_costo|CentroCosto|CostCenter"` en todo `apps/tenant/`):

- **No existe ningun modelo `CentroCosto`** en el proyecto (cero resultados para `class CentroCosto`).
- `apps/tenant/gastos/models.py::Gasto.centro_costo` **existia y fue eliminado** (migracion `0007_remove_gasto_tenant_gast_centro__968db9_idx_and_more.py`, junto con `codigo_contable`) — era un campo suelto, nunca una entidad real.
- `apps/tenant/contabilidad/models.py::MovimientoContable.centro_costo_id` (linea 521) es un `PositiveIntegerField` **sin FK**, con el comentario explicito: *"v3.0: Centro de costo para analisis por proyecto (sin FK — referencia desacoplada)"* / *"ID del proyecto/centro de costo (sin FK — referencia desacoplada)"* — es decir, en este ERP el concepto "centro de costo" ES, en la practica, **el Proyecto**, referenciado por ID suelto (no una entidad separada).
- `apps/tenant/proyectos/models.py::Proyecto.factura_costo` esta literalmente etiquetado `verbose_name=_('Factura (Centro de Costos)')` — otra confirmacion de que "centro de costos" en SINTEL nunca fue modelado como entidad propia; se superpone con Proyecto/Factura segun el contexto.

**Decision de diseño (Fase 2) derivada de este hallazgo:** `RequisicionCompra.centro_costo` queda **DEFERRED** — no se crea ninguna entidad `CentroCosto` nueva dentro de Compras (violaria plan §2-3/§30, "nunca inventar infraestructura contable dentro de Compras"). El campo `proyecto` (FK real a `tenant_proyectos.Proyecto`, ya usado por `OrdenCompra`) cubre la necesidad real de agrupacion/analisis por proyecto que el resto del sistema ya usa como proxy de "centro de costo".

---

## 3. Modelos de dominios relacionados (para las FKs/junction tables de Requisicion)

### 3.1 `Proyecto` (`apps/tenant/proyectos/models.py`)
Arquitectura "Zero-Coupling" deliberada: **unica FK externa es `Empresa`**. Todo lo demas (cliente, factura) es snapshot/soft-reference (`cliente_id`+`cliente_nombre`, `factura_costo` FK SET_NULL + `factura_costo_numero` snapshot). Relacion con `OrdenCompra` ya existe (`proyecto` FK SET_NULL, `related_name='ordenes_compra'`). Confirma plan §11: **Proyecto es 0..N por requisicion, nunca 1:1** — mismo patron ya usado por OrdenCompra.

### 3.2 `Cotizacion` (`apps/tenant/cotizaciones/models.py`)
**Confirmado: es una cotizacion COMERCIAL A CLIENTE** (`cliente = FK a tenant_clientes.Cliente`), no una cotizacion de proveedor. Estados: BORRADOR/ENVIADA/APROBADA/RECHAZADA/ARCHIVADA (`TRANSICIONES_VALIDAS` en su `CotizacionService`, recien reforzado esta misma sesion). **Confirma plan §11-13 explicitamente: NO se puede reutilizar/repropositar este modelo como "cotizacion de proveedor" sin romper su semantica real.** Si Requisicion necesita vincular una Cotizacion, es solo para trazabilidad ("esta compra es para atender la venta cotizada X"), vía junction table `RequisicionCotizacion` (referencia, no reinterpretacion) — nunca tocar `CotizacionService.convertir_a_venta()`.

### 3.3 `Factura` (`apps/tenant/facturas/models.py`)
SSoT fiscal DIAN completo (CUFE, subtotal/IVA/total, estado). `OrdenCompra.factura_asociada` ya es un vinculo manual 1:1 a Factura naturaleza COMPRA. Requisicion, si necesita referenciar una factura, debe usar el mismo patron soft/manual (junction `RequisicionFactura`, o snapshot de `numero_factura` unicamente) — **nunca duplicar CUFE/totales/estado DIAN** (plan §30).

### 3.4 `DocumentoSoporte` (`apps/tenant/gastos/models.py`)
Evidencia legal de gasto con numeracion propia (`resolucion_dian` + `consecutivo`), FK obligatoria a `Proveedor` (CASCADE). Ya vinculado a `OrdenCompra.documento_soporte` (SET_NULL). Relevante como precedente de "documento de soporte no fiscal" — analogo a lo que `RequisicionDocumento` (plan §8) necesita generalizar para tipos internos/externos.

---

## 4. AI Tools — dominio `compras` ya registrado

`apps/services/ai/tools/compras_tools.py` ya existe con tools registrados bajo `domain="compras"`. Cualquier tool nuevo para Requisiciones (ej. `buscar_requisiciones`, futuro, no incluido en esta fase) debe seguir el mismo archivo/convencion y mantenerse **READ-only tenant-scoped** — nunca registrar `crear_requisicion`/`aprobar_requisicion`/`crear_orden` como `ToolKind.WRITE` auto-aprobado (regla global ya vigente en `AUTO_APPROVED_KINDS`, ver ADR-MCP-001). Fuera de alcance de Fase 1-9; se documenta aqui solo como constraint a respetar si aparece en Fase 6/7.

---

## 5. Conclusiones de la Auditoria Previa (Fase 1 → cierre)

1. **Confirmado:** Compras tiene FSD completo y sano, sin deuda tecnica abierta relevante — es seguro extenderlo.
2. **Confirmado:** el mecanismo de atencion parcial por item (cantidad_recibida/cantidad_pendiente + CheckConstraint) ya existe en `ItemOrdenCompra`; Requisicion debe seguir el mismo patron a su propio nivel (`RequisicionCompraItem.cantidad_ordenada` acumulado), sin inventar un segundo esquema.
3. **Confirmado:** NO existe una entidad `CentroCosto` real en ningun dominio del proyecto — decision para Fase 2: campo `centro_costo` en `RequisicionCompra` queda **DEFERRED**, se usa `proyecto` (FK real) como el mecanismo de agrupacion que el resto del sistema ya trata como equivalente.
4. **Confirmado:** `Cotizacion` es exclusivamente comercial-a-cliente; cualquier vinculo Requisicion↔Cotizacion es de trazabilidad (junction table), nunca de reutilizacion semantica.
5. **Confirmado:** el patron de sub-pestañas HTMX (`nav-pills` dentro de `workspace/#compras`) es el punto de integracion frontend correcto para Requisiciones — no crear un tab global nuevo.
6. **Confirmado:** el bridge Compras→CxP vive integro en `OrdenCompraBusinessService`; Requisicion no debe tocarlo.
7. **Sin bloqueadores** para iniciar Fase 2 (Diseño). No se requiere migracion de datos historica en Compras aun (esa discusion es propia de Fase 7, cuando se decida la fase de transicion NULL→NOT NULL de `OrdenCompra.requisicion`).

**Siguiente paso (Fase 2, plan §47-48):** producir `docs/compras/REQUISICIONES_DESIGN.md` con el diseño concreto de modelos/estados/servicios, sin migraciones ni código todavía, sin ejecutar tests.
