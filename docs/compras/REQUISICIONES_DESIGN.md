# REQUISICIONES_DESIGN.md — Diseño (Fase 2)

**Basado en:** `REQUISITION_BASELINE.md` (Fase 1). Sin migraciones ni codigo en esta fase — solo diseño. Sin ejecucion de tests (plan §0.2).

**[Addendum 2026-09-26] Cotizacion de origen ahora es OBLIGATORIA al crear.** El diseño original (§7 mas abajo) trataba `RequisicionCotizacion`/`RequisicionFactura` como trazabilidad pura, opcional, sin efectos de negocio. Decision explicita del usuario: toda `RequisicionCompra` nueva debe nacer con una `Cotizacion` real vinculada (`tipo_relacion='ORIGEN'`, `es_principal=True`), validada y creada en la misma transaccion atomica que la requisicion (`RequisicionCompraBusinessService.crear_requisicion()`, `cotizacion_requerida`/`cotizacion_invalida` como nuevos codigos de error 422/400). El resto de §7 sigue vigente sin cambios: `vincular_cotizacion()`/`vincular_factura()` continuan existiendo para vincular cotizaciones/facturas ADICIONALES despues de creada, y siguen siendo opcionales/sin efectos de negocio. Ver `REQUISICIONES_RELEASE_GATE.md` para el detalle de implementacion.

---

## 1. Ubicacion del submodulo

`apps/tenant/compras/requisiciones/` — subpaquete Django dentro de la app existente `compras` (no una app Django nueva independiente), FSD completo propio:

```
apps/tenant/compras/requisiciones/
  __init__.py
  models.py
  migrations/
  services/
    __init__.py
    business_service.py
    crud_service.py
    selectors.py
    api_mixins.py
  api/
    __init__.py
    viewsets.py
    serializers.py
    urls.py
  tests/            # poblado solo en Fase 12
```

Razon: comparte tenant/empresa/sede con `compras`, se integra con `OrdenCompra` (FK cross-modelo dentro de la misma app Django evita import ciclico entre apps), y el plan (§14) exige agregar un campo a `compras.models.OrdenCompra` — mantenerlo en el mismo `app_label` (`tenant_compras`) simplifica la migracion de esa FK. Precedente: no hay en el proyecto un caso de "subpaquete con su propio `models.py`+migrations dentro de otra app" — se usara el patron estandar de Django (subpaquete con `apps.py` propio registrado como app independiente `tenant_compras_requisiciones` en `INSTALLED_APPS`/`TENANT_APPS`, exactamente igual que cualquier otra app de `apps/tenant/`) para no romper la convención "una app = un `app_label`" que el resto del proyecto sigue. Se confirmara el nombre de `app_label` (`tenant_compras_requisiciones`) al crear `apps.py` en Fase 3.

---

## 2. Modelo `RequisicionCompra`

Hereda `SedeAwareModel` (mismo patron que `OrdenCompra`/`RecepcionCompra` — sede obligatoria desde el inicio, tabla nueva sin datos historicos, sin necesidad de fase nullable→backfill→harden que sufrio `OrdenCompra`).

| Campo | Tipo | Notas |
|---|---|---|
| `uuid` | UUIDField unique | PK publica |
| `empresa` | heredado de SedeAwareModel | |
| `sede` | FK Sede PROTECT, NOT NULL | heredado, endurecido igual que OrdenCompra |
| `area` | FK Area SET_NULL, null=True | heredado de SedeAwareModel si ya expone `area` opcional (verificar en Fase 3 la firma real de `SedeAwareModel` antes de redeclarar) |
| `numero_documento` | CharField(50), db_index | `REQ-000001` formato propio (ver §3) |
| `fecha_solicitud` | DateField, default hoy | |
| `fecha_necesidad` | DateField | `CheckConstraint(fecha_necesidad >= fecha_solicitud)` |
| `solicitante` | FK `perfil.TenantProfile` PROTECT | quien solicita |
| `responsable_aprobacion` | FK `perfil.TenantProfile` SET_NULL, null=True | asignado al enviar a aprobacion; puede quedar null si no hay flujo de aprobador especifico (rol admin aprueba) |
| `tipo` | CharField choices | `BIEN` / `SERVICIO` / `MIXTO` |
| `prioridad` | CharField choices | `BAJA` / `MEDIA` / `ALTA` / `URGENTE` |
| `estado` | CharField choices, default BORRADOR, db_index | ver maquina de estados §4 |
| `justificacion` | TextField | obligatorio a nivel de negocio (validado en BusinessService, no NOT NULL en BD porque BORRADOR permite ir completando) |
| `observaciones` | TextField, blank | |
| `proyecto` | FK `tenant_proyectos.Proyecto`, SET_NULL, null=True, blank=True | 0..1 directa opcional (la mayoria de requisiciones tendran 0 o 1 proyecto; para el caso raro de N proyectos se usa `RequisicionProyecto` junction — decision: **campo directo cubre el caso comun (>95% esperado), junction solo si Fase 7 confirma necesidad real de N:N**, evita sobre-ingenieria) |
| `moneda` | CharField(3), default 'COP' | |
| `subtotal_estimado`, `impuestos_estimados`, `total_estimado` | DecimalField(15,2) | calculados desde items en CRUDService, igual que OrdenCompra |
| `centro_costo` | **NO SE CREA** | DEFERRED — ver Baseline §2. Ningun campo nuevo; se usa `proyecto` como agrupador |

Constraints:
- `UniqueConstraint(['empresa', 'numero_documento'])`
- `CheckConstraint(fecha_necesidad__gte=F('fecha_solicitud'))`
- `CheckConstraint(subtotal_estimado__gte=0)`, idem impuestos/total (via `MinValueValidator` + posible CheckConstraint DB, igual patron que OrdenCompra)

Indices: `['empresa', 'estado']`, `['empresa', 'fecha_solicitud']`, `['empresa', 'sede']` (repetir explicito — hallazgo documentado en `models.py` de compras: `Meta.indexes` propio NO fusiona con el de la clase abstracta).

## 3. Numeracion

Propia, simple: `REQ-{consecutivo:06d}` (ej. `REQ-000001`), sin plantilla configurable (a diferencia de OrdenCompra/Cotizacion, que soportan multiples perfiles de numeracion por decision de negocio ya tomada en esos dominios — Requisicion no tiene ese requisito en el plan, no se agrega esa complejidad sin pedido explicito). Campo `consecutivo` IntegerField + asignacion atomica:

```python
with transaction.atomic():
    ultimo = RequisicionCompra.objects.select_for_update().filter(
        empresa_id=empresa_id
    ).aggregate(Max('consecutivo'))['consecutivo__max'] or 0
    nuevo_consecutivo = ultimo + 1
```
Mismo patron ya usado por `OrdenCompraSelector.get_siguiente_consecutivo()` (Max+1) combinado con `select_for_update()` para la carrera de concurrencia (igual criterio que `_dsv_y_asignar_plantilla`).

## 4. Maquina de estados

```
BORRADOR → PENDIENTE_APROBACION → APROBADA → EN_PROCESO_COMPRA → PARCIALMENTE_ATENDIDA → ATENDIDA
              ↓                      ↓
          RECHAZADA              CANCELADA
    (BORRADOR tambien puede → CANCELADA directamente)
```

`TRANSICIONES_VALIDAS` (mismo patron que `CotizacionService`, dict `{estado_actual: [estados_validos_siguientes]}`):
```python
TRANSICIONES_VALIDAS = {
    'BORRADOR': ['PENDIENTE_APROBACION', 'CANCELADA'],
    'PENDIENTE_APROBACION': ['APROBADA', 'RECHAZADA'],
    'APROBADA': ['EN_PROCESO_COMPRA', 'CANCELADA'],
    'EN_PROCESO_COMPRA': ['PARCIALMENTE_ATENDIDA', 'ATENDIDA', 'CANCELADA'],
    'PARCIALMENTE_ATENDIDA': ['ATENDIDA', 'CANCELADA'],
    'ATENDIDA': [],
    'RECHAZADA': [],
    'CANCELADA': [],
}
```
`RECHAZADA` requiere `motivo` obligatorio (mismo patron ya construido esta sesion para `Cotizacion.RECHAZADA` — reutilizar la misma UX: campo de texto obligatorio en el modal de rechazo). `EN_PROCESO_COMPRA`/`PARCIALMENTE_ATENDIDA`/`ATENDIDA` son transiciones derivadas automaticamente por `recalcular_estado()` cuando se crean/aprueban OrdenCompra ligadas — nunca las dispara el usuario manualmente (analogo a como `RecepcionCompra` deriva el estado PARCIAL/RECIBIDA de `OrdenCompra` sin accion manual directa del usuario sobre ese campo).

## 5. `RequisicionCompraItem`

| Campo | Tipo |
|---|---|
| `uuid` | UUIDField unique |
| `requisicion` | FK CASCADE |
| `descripcion` | CharField(255) |
| `item_inventario_uuid` | UUIDField null=True (soft-ref, mismo patron que `ItemOrdenCompra`) |
| `tipo_item` | CharField choices `BIEN`/`SERVICIO` |
| `cantidad_solicitada` | Decimal(12,2), `MinValueValidator(0.01)` |
| `unidad_medida` | CharField(20), default 'UND' |
| `valor_unitario_estimado` | Decimal(15,2) |
| `porcentaje_iva` | Decimal(5,2), default 0 |
| `valor_iva_estimado`, `subtotal_estimado`, `total_estimado` | Decimal(15,2), calculados en CRUDService |
| `cantidad_aprobada` | Decimal(12,2), default 0 — igual a solicitada al aprobar salvo ajuste explicito |
| `cantidad_ordenada` | Decimal(12,2), default 0 — acumulado desde `ItemOrdenCompra` generados |
| `cantidad_cancelada` | Decimal(12,2), default 0 |
| `observaciones` | TextField, blank |

Propiedad calculada `cantidad_pendiente = cantidad_aprobada - cantidad_ordenada - cantidad_cancelada` (mismo patron que `ItemOrdenCompra.cantidad_pendiente`). `CheckConstraint(cantidad_ordenada + cantidad_cancelada <= cantidad_aprobada)` — bloquea a nivel BD el sobre-ordenamiento (plan: "nunca permitir ordenar mas de lo aprobado sin politica explicita" — aqui la politica explicita es: no se permite, punto, sin flag de excepcion en esta primera version; agregar `COMPRA_URGENTE` es un caso de header, no de item, ver §7).

## 6. `RequisicionDocumento`

| Campo | Tipo |
|---|---|
| `uuid` | UUIDField unique |
| `requisicion` | FK CASCADE |
| `tipo` | CharField choices: `COTIZACION`/`FACTURA`/`PROYECTO`/`ORDEN_INTERNA`/`DOCUMENTO_SOPORTE`/`OTRO` |
| `nombre` | CharField(255) |
| `numero_referencia` | CharField(100), blank — placeholder para documentos externos aun no reconciliados (ej. `"FE-12345"`) |
| `documento_uuid` | UUIDField, null=True — soft-ref al UUID real una vez reconciliado (Factura/Cotizacion/Proyecto/OrdenCompra reales) |
| `archivo` | FileField, blank — mismo storage privado que `Proyecto.documentos_storage` (`PRIVATE_MEDIA_ROOT`, nunca MEDIA_ROOT publico) |
| `descripcion` | TextField, blank |
| `created_at` | heredado |

## 7. Junction tables (trazabilidad, no reinterpretacion)

**Correccion de auto-auditoria (antes de escribir codigo):** el diseño inicial proponia 3 junction
tables (`RequisicionCotizacion`, `RequisicionFactura`, `RequisicionOrdenCompra`). Al llegar a
implementar se detecto que `RequisicionOrdenCompra` seria redundante: `OrdenCompra.requisicion`
(FK real, §8) YA modela la relacion 1 requisicion : N ordenes con `related_name='ordenes_compra'`
navegable en ambos sentidos — agregar una tabla de union paralela para el mismo hecho viola la
Regla de Oro ("¿YA EXISTE? -> reusar, no duplicar") y crea riesgo de desincronizacion entre la FK
real y la tabla de bookkeeping. **Se elimina `RequisicionOrdenCompra` del diseño.** Solo quedan:

`RequisicionCotizacion`, `RequisicionFactura` — mismo shape:
```python
uuid, requisicion (FK CASCADE), documento_origen (FK real al modelo correspondiente, PROTECT),
tipo_relacion (CharField, ej. 'CONTEXTO'/'ORIGEN'/'EVIDENCIA'), es_principal (BooleanField),
observacion (TextField blank), created_at
```
Uso: vinculos de contexto/trazabilidad manual (usuario adjunta desde la UI) a objetos **reales ya
existentes** (con FK PROTECT real, navegables con `select_related` para el timeline de
trazabilidad) — nunca disparan ningun efecto de negocio. Se distinguen de `RequisicionDocumento`
(§6): ese es para evidencia/archivos con referencia blanda (`documento_uuid` nullable, incluye el
caso de documentos externos aun no reconciliados) mientras que estas junction tables son enlaces
firmes a un registro real que ya existe.

`COMPRA_URGENTE` / `COMPRA_EXCEPCIONAL`: campo `es_excepcional` (BooleanField default False) + `motivo_excepcion` (TextField) en `OrdenCompra` (no en Requisicion) — permite crear una OC sin requisicion asociada solo si `es_excepcional=True` y `motivo_excepcion` no vacio, validado en `OrdenCompraBusinessService`, auditado (queda en el registro de la orden, visible en UI). Por defecto `requisicion` seguira siendo opcional a nivel BD durante la fase de transicion (§9) y se volvera obligatoria salvo excepcion una vez completado el backfill.

## 8. Cambios en `apps/tenant/compras/models.py::OrdenCompra`

Agregar (Fase 3, migracion propia dentro de `compras`, no de `requisiciones`, para minimizar dependencias cruzadas de import):
```python
requisicion = models.ForeignKey(
    'tenant_compras_requisiciones.RequisicionCompra',
    on_delete=models.PROTECT,   # nunca borrar una requisicion con ordenes generadas
    null=True, blank=True,      # FASE A: nullable (ver §9)
    related_name='ordenes_compra',
    verbose_name=_('Requisicion de Origen'),
)
es_excepcional = models.BooleanField(default=False)
motivo_excepcion = models.TextField(blank=True)
```
Regla de negocio implementada (BusinessService, no CheckConstraint — cruza estados de 2 tablas):
`requisicion` es **opcional** al crear una OC en esta mision (ver correccion de alcance en §9 —
exigirla ya mismo romperia sin aviso el flujo/UI "Nueva Orden" existente, que aun no ofrece
seleccionarla). La regla real que SI se aplica: si una orden tiene `requisicion_id` asignado, solo
puede pasar a `APROBADA` cuando `requisicion.estado == 'APROBADA'` **o** `orden.es_excepcional and
orden.motivo_excepcion`. Ordenes sin requisicion vinculada (la mayoria, hoy) no se ven afectadas
por esta regla — cero regresion. Implementado en
`OrdenCompraBusinessService.cambiar_estado_orden_compra()`, junto al bloque DSV opcional de
`requisicion` en `crear_orden_compra()`.

## 9. Migracion en fases (nunca backfill inventado)

- **FASE A** (Fase 3 de esta mision): `requisicion` nullable en BD. Ordenes existentes quedan con `requisicion=NULL` — **no se les asigna ninguna requisicion retroactiva** (no hay evidencia real para reconstruir esa relacion; inventarla violaria "nunca invenar relaciones historicas").
- **FASE B/C/D** (fuera de alcance de esta mision, quedan documentadas como **DEFERRED**): backfill solo si aparece evidencia real futura; bloqueo de nuevas ordenes sin requisicion solo cuando el negocio decida activarlo; NOT NULL solo al final. Esta mision entrega FASE A funcional y usable end-to-end (crear requisicion → aprobarla → generar OC desde ella), sin forzar retroactividad.

## 10. Service Layer — metodos (`business_service.py`)

`crear_requisicion`, `actualizar_requisicion` (solo BORRADOR), `enviar_a_aprobacion`, `aprobar_requisicion`, `rechazar_requisicion` (motivo obligatorio), `cancelar_requisicion`, `vincular_cotizacion`, `vincular_factura`, `vincular_proyecto` (si se decide exponer set/clear del FK directo en vez de junction — Fase 4 decide segun uso real), `crear_orden_desde_requisicion` (pseudoflujo ya detallado en el plan §20, reutiliza `OrdenCompraBusinessService.crear_orden_compra` internamente en vez de duplicar la logica DSV de plantilla/proveedor), `recalcular_estado` (deriva EN_PROCESO_COMPRA/PARCIALMENTE_ATENDIDA/ATENDIDA desde el agregado de items).

Historial append-only: `RequisicionHistorialEstado` (mismo shape que `CotizacionHistorialEstado`, reutilizado como plantilla directa).

## 11. API

Base `/api/v1/compras/requisiciones/`. CRUD estandar + acciones: `enviar-aprobacion/`, `aprobar/`, `rechazar/`, `cancelar/`, `crear-orden/`, `ordenes/` (GET, lista OC generadas), `documentos/` (GET/POST), `historial/` (GET). `estado` en `read_only_fields` de todos los serializers de escritura (mismo fix ya aplicado a OrdenCompra por CO-3 — no repetir ese bug).

## 12. Frontend

Nueva sub-pestaña `#subtab-requisiciones` en `compras_list.html` (mismo `nav-pills`/HTMX-lazy patron que `#subtab-ordenes`/`#subtab-plantillas`). Detalle con secciones Cabecera/Justificacion/Items/Cotizaciones/Documentos/Facturas/Ordenes generadas/Historial, timeline de trazabilidad Requisicion→Proyecto/Cotizacion→OrdenCompra→Recepcion→Inventario/Factura→CxP (solo lectura, agregando lo que ya exponen los selectors existentes de cada dominio via API, sin duplicar datos).

## 13. Fuera de alcance / DEFERRED explicito

- `centro_costo` como entidad — DEFERRED (Baseline §2).
- Backfill retroactivo de `OrdenCompra.requisicion` en ordenes historicas — DEFERRED.
- `NOT NULL` en `OrdenCompra.requisicion` — DEFERRED (depende de decision de negocio futura).
- Nuevo AI tool `buscar_requisiciones` — DEFERRED, no pedido explicitamente en esta mision; se documenta el constraint (READ-only, tenant-scoped) para cuando se pida.
- `RequisicionProyecto` N:N junction — DEFERRED hasta evidencia real de necesidad (se usa FK directa 0..1 por defecto).

---

**Siguiente paso (Fase 3):** crear `apps/tenant/compras/requisiciones/` (app Django + `apps.py`, `models.py` segun este diseño, migraciones), registrar en `TENANT_APPS`, agregar migracion de `OrdenCompra.requisicion`/`es_excepcional`/`motivo_excepcion` en `compras`. Sin ejecutar tests.
