# REQUISICIONES_ARCHITECTURE.md

**Mision:** `PLAN_IMPLEMENTACION_REQUISICIONES_COMPRAS.md`. Ver tambien `REQUISITION_BASELINE.md` (Fase 1) y `REQUISICIONES_DESIGN.md` (Fase 2) para el razonamiento detras de cada decision — este documento describe el estado FINAL implementado.

## 1. Ubicacion

App Django propia dentro del paquete `compras`: `apps.tenant.compras.requisiciones` (`app_label='tenant_compras_requisiciones'`), registrada en `TENANT_APPS` justo despues de `apps.tenant.compras`. Comparte tenant/empresa/sede con Compras y se integra con `OrdenCompra` via FK real.

```
apps/tenant/compras/requisiciones/
  apps.py                      # AppConfig, label tenant_compras_requisiciones
  models.py                    # 6 modelos (ver #2)
  migrations/0001_...py
  services/
    selectors.py                # RequisicionCompraSelector
    crud_service.py             # RequisicionCompraCRUDService (numeracion, DB writes)
    business_service.py         # RequisicionCompraBusinessService (DSV, maquina de estados)
    api_mixins.py                # RequisicionCompraServiceMixin
  api/
    serializers.py / viewsets.py / urls.py
  templates/tenant/compras/requisiciones/
    offcanvas_crear_requisicion.html
    offcanvas_detalle_requisicion.html
    partials/tabla_requisiciones.html
  static/compras/js/features/
    requisiciones_list.js
    requisiciones_editor.js
```

El frontend vive como una TERCERA sub-pestaña (`#subtab-requisiciones`) dentro de `workspace/#compras` (mismo patron `nav-pills` que "Ordenes"/"Plantillas"), NO un tab global nuevo.

## 2. Modelos (`models.py`)

| Modelo | Base | Rol |
|---|---|---|
| `RequisicionCompra` | `SedeAwareModel` (sede NOT NULL desde el inicio, tabla nueva) | Cabecera: numero, fechas, tipo, prioridad, estado, justificacion, proyecto (0..1), totales estimados |
| `RequisicionCompraItem` | `SintelTenantBaseModel` | Linea: cantidad_solicitada/aprobada/ordenada/cancelada + `cantidad_pendiente` (property) |
| `RequisicionDocumento` | `SintelTenantBaseModel` | Evidencia/archivo adjunto, `documento_uuid` soft-ref (soporta placeholders externos no reconciliados) |
| `RequisicionCotizacion` | `SintelTenantBaseModel` | Junction de trazabilidad a `tenant_cotizaciones.Cotizacion` (FK real, PROTECT) |
| `RequisicionFactura` | `SintelTenantBaseModel` | Junction de trazabilidad a `facturas.Factura` (FK real, PROTECT) |
| `RequisicionHistorialEstado` | `SintelTenantBaseModel` | Append-only, mismo patron que `CotizacionHistorialEstado` |

**Sin `RequisicionOrdenCompra`:** la relacion 1 Requisicion : N OrdenCompra vive como FK real (`OrdenCompra.requisicion`, `related_name='ordenes_compra'`) — una junction table paralela hubiera sido redundante (ver `REQUISICIONES_DESIGN.md` #7).

**Sin `centro_costo`:** no existe una entidad `CentroCosto` real en el proyecto (`REQUISITION_BASELINE.md` #2) — se usa `proyecto` (FK real) como agrupador, igual que el resto del sistema.

## 3. Cambios en `apps/tenant/compras/models.py::OrdenCompra`

```python
requisicion = models.ForeignKey('tenant_compras_requisiciones.RequisicionCompra',
    on_delete=models.PROTECT, null=True, blank=True, related_name='ordenes_compra')
es_excepcional = models.BooleanField(default=False)
motivo_excepcion = models.TextField(blank=True)
```
`null=True` deliberado (FASE A de la migracion por fases — ver #6). Indice `['empresa', 'requisicion']` agregado.

## 4. Maquina de estados

```
BORRADOR -> PENDIENTE_APROBACION -> APROBADA -> EN_PROCESO_COMPRA -> PARCIALMENTE_ATENDIDA -> ATENDIDA
                |                       |
            RECHAZADA               CANCELADA
BORRADOR tambien -> CANCELADA directo.
```
`EN_PROCESO_COMPRA`/`PARCIALMENTE_ATENDIDA`/`ATENDIDA` son derivados automaticamente por `recalcular_estado()` — nunca transiciones manuales del usuario. `RECHAZADA` y `CANCELADA` aceptan un `motivo`/`comentario` (RECHAZADA lo exige, CANCELADA es opcional), guardado en `RequisicionHistorialEstado`.

## 5. Servicios

- **Numeracion:** `REQ-{consecutivo:06d}`, propia (sin plantilla configurable), `Max(consecutivo)+1` bajo `select_for_update()` (`RequisicionCompraCRUDService.asignar_siguiente_numero`).
- **DSV anti-IDOR:** `RequisicionCompraBusinessService._obtener_entidad_por_id_o_uuid()`, copia autocontenida del mismo helper de `OrdenCompraBusinessService` (arquitectura Zero-Coupling, cada `business_service.py` es independiente).
- **`crear_orden_desde_requisicion()`:** valida cantidades pendientes por item, delega la creacion real de la `OrdenCompra` a `OrdenCompraBusinessService.crear_orden_compra()` (nunca duplica su logica DSV de plantilla/proveedor/proyecto/documento_soporte), acumula `cantidad_ordenada` en los items via `select_for_update()`, y dispara `recalcular_estado()`.
- **Bridge a Compras:** `OrdenCompra.requisicion` (opcional en esta mision) habilita, cuando esta presente, la regla: una orden con requisicion vinculada solo puede pasar a `APROBADA` si `requisicion.estado == 'APROBADA'` (o `es_excepcional` + `motivo_excepcion`). Implementado en `OrdenCompraBusinessService.cambiar_estado_orden_compra()` — sin efecto sobre ordenes sin requisicion (cero regresion).

## 6. Migracion por fases (OrdenCompra.requisicion)

- **FASE A (esta mision):** campo nullable, opcional en creacion, sin backfill retroactivo, sin bloqueo de ordenes nuevas sin requisicion.
- **FASE B/C/D (DEFERRED, fuera de alcance):** backfill historico solo si aparece evidencia real; bloqueo de ordenes nuevas sin requisicion solo cuando el negocio lo decida; `NOT NULL` solo al final. Ninguna se implementa aqui — documentado explicitamente como deuda futura, no como "completado".

## 7. API

Base `/api/v1/compras/requisiciones/` (montada ANTES de `/api/v1/compras/` en `config/api_urls.py` — ver nota critica en #9). CRUD estandar (`estado` `read_only`) + `enviar-aprobacion/`, `aprobar/`, `rechazar/`, `cancelar/`, `vincular-cotizacion/`, `vincular-factura/`, `crear-orden/`, `historial/`, `documentos/`, `dt/` (DataTables server-side), `render-offcanvas/{crear,editar,detalle}/`.

## 8. Permisos y multitenant

Mismo patron que `OrdenCompraViewSet`: `[IsTenantMember(), IsTenantAdminOrReadOnly(), HasOrganizationalScope()]`, filtrado por `OrganizationalScope` (sede/area) via `RequisicionCompraServiceMixin.get_qs_list()`. Toda query de servicio filtra por `empresa_id` explicito (verificado, ver `REQUISICIONES_PRE_TEST_AUDIT.md`).

## 9. Hallazgo critico de esta implementacion (para no repetir)

`path('compras/requisiciones/', ...)` en `config/api_urls.py` **debe registrarse ANTES** de `path('compras/', ...)`: como `include()` resuelve por prefijo en ORDEN DE REGISTRO (no por especificidad), si `compras/` fuera primero, cualquier request a `compras/requisiciones/...` caeria en el patron catch-all de detalle de `OrdenCompraViewSet` (`^(?P<uuid>[^/.]+)/$`, leyendo "requisiciones" como si fuera un UUID) y nunca llegaria al urlconf real — produce un 405 "Metodo no permitido" enganoso. Verificado en vivo contra el tenant `admin` durante esta mision (ver `REQUISICIONES_PRE_TEST_AUDIT.md`).

## 10. Trazabilidad automatica desde Proyecto (2026-09-25, pedido explicito del usuario)

Al crear una requisicion con `proyecto` asignado, `RequisicionCompraBusinessService._sincronizar_trazabilidad_desde_proyecto()`
intenta resolver y vincular (best-effort, nunca bloquea la creacion) su Cotizacion/Factura de
origen, usando SOLO mecanismos reales ya existentes -- Proyecto es Zero-Coupling (sin FK a
Cotizaciones):

- **Cotizacion**: `Proyecto.codigo` sigue el patron determinista `PRJ-COT-<codigo_unico>` que ya
  genera `CotizacionService.convertir_a_proyecto()` — se parsea ese prefijo y se busca la
  Cotizacion por `codigo_unico` (fallback `numero_cotizacion`). Si el codigo no sigue el patron
  (proyecto no viene de una conversion), no se vincula nada — no es un error.
- **Factura**: primero `Proyecto.factura_costo` (FK real y directa, ya existente en Proyectos);
  si no esta, se busca una `Venta` con `cotizacion_uuid` igual al `uuid` de la Cotizacion resuelta
  arriba, y se toma su `factura_asociada` (mismo patron que `OrdenCompra.factura_asociada`).

Verificado contra datos reales del tenant `admin`: de 32 Proyectos reales, solo 3 tienen
`factura_costo` poblado y 0 Ventas reales tienen `cotizacion_uuid` poblado (los 25 Ventas
existentes no vienen de conversion de Cotizacion) — el resolver maneja correctamente el caso
comun de "solo se encuentra la Cotizacion, la Factura queda sin resolver" sin fabricar nada.

Re-disparable manualmente via `POST /api/v1/compras/requisiciones/{uuid}/sincronizar-trazabilidad/`
(boton "Sincronizar desde Proyecto" en el detalle) para cuando el Proyecto se asigna despues de
crear la requisicion, o cuando la Venta/Factura aparece mas tarde.

## 11. AI Tools

Sin tools nuevos en esta mision (no pedido explicitamente). Si se agrega un futuro `buscar_requisiciones`, debe registrarse en `apps/services/ai/tools/compras_tools.py`, `ToolKind.READ`, tenant-scoped — nunca WRITE auto-aprobado (`AUTO_APPROVED_KINDS`, ver `docs/mcp/ADR-MCP-001.md`).
