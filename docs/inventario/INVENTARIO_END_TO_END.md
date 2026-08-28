# Inventario — Flujo End-to-End y Hallazgos Reales (FASE 51-53, consolidado)

**Fecha:** 2026-08-27
**Método:** lectura y edición directa de código real + suite de tests local
(venv, sin Docker para pytest) contra un tenant de test real (`TenantTestCase`,
schema PostgreSQL real por test class) — no navegador (misma limitación de
entorno documentada en la misión de Cotizaciones de esta sesión: el sandbox
de Claude Browser no puede resolver `*.sintel.net.co`).

---

## Escenario Producto (FASE 51)

```
Categoría (opcional)
   ↓
Producto (CREATE, activo=True por defecto)
   ↓
KardexService.registrar_movimiento(ENTRADA_COMPRA/AJUSTE/DEVOLUCION)
   ↓
stock_actual recalculado atómicamente (select_for_update)
   ↓
KardexService.registrar_movimiento(SALIDA_VENTA/BAJA/CONSUMO)
   ↓
stock_actual recalculado de nuevo (rechaza si stock insuficiente)
   ↓
UPDATE Producto (PATCH)
   ↓
DELETE (solo si activo=False)
```

Verificado con tests reales nuevos (`test_kardex_service.py`,
`test_crud_permissions.py::TestProductoCRUD`): entradas incrementan stock,
salidas lo decrementan, stock insuficiente se rechaza sin crear el
movimiento, cantidad ≤0 se rechaza, tipo inválido se rechaza, producto
inactivo no admite movimientos, producto de otra empresa se rechaza. DELETE
de un producto activo se rechaza (400); inactivo se permite (204).

## Escenario Activo Fijo (FASE 52)

```
ActivoFijo (CREATE, estado=ACTIVO por defecto)
   ↓
KardexService.registrar_movimiento_activo(ASIGNACION_RESPONSABLE)  -- no cambia estado
   ↓
KardexService.registrar_movimiento_activo(TRASLADO_MANTENIMIENTO) -- estado -> MANTENIMIENTO
   ↓
KardexService.registrar_movimiento_activo(RETORNO_MANTENIMIENTO)  -- estado -> ACTIVO
   ↓
KardexService.registrar_movimiento_activo(SALIDA_BAJA_ACTIVO)     -- estado -> BAJA
   ↓
DELETE (solo permitido si estado en {BAJA, VENDIDO} -- corregido esta mision)
```

**Hallazgo real corregido**: antes de esta misión, `ActivoFijoServiceMixin.
service_activo_destroy()` borraba incondicionalmente, sin el mismo guard que
Producto/Servicio ya tenían (bloquear borrado de un ítem "en uso"). Un
activo en estado `ACTIVO` o `MANTENIMIENTO` podía borrarse por error,
perdiendo en CASCADE todo su historial de Kardex. Corregido reutilizando el
propio campo `estado` del modelo (sin inventar uno nuevo): solo se permite
borrar si `estado` es `BAJA` o `VENDIDO`. Tests reales:
`TestActivoFijoDestroyGuard` (4 tests, los 4 estados).

Relación contable: `ActivoFijo` no almacena cuentas contables (Pure Pull,
v3.10.2 confirmado vigente) — Contabilidad resuelve la cuenta de
depreciación vía `ExtractorInventario` + `ReglaContable` + prefijo `'51'`
en `APP_ORIGEN_PREFIJOS['inventario']`.

## Escenario Servicio (FASE 53)

```
Servicio (CREATE)
   ↓
HistorialServicio (registro de prestación -- inmutable, sin UPDATE/DELETE propios)
   ↓
vincular_proyecto (soft-ref opcional, con DSV real desde esta misión)
   ↓
[Factura/Venta si corresponde -- fuera de este módulo]
```

**Hallazgo real corregido — bug de fecha (mismo patrón que
`Cotizacion.fecha_emision` en la misión anterior)**: `HistorialServicio.
fecha_registro = models.DateField(default=timezone.now)` — `timezone.now`
devuelve un `datetime`, no un `date`. El valor quedaba en memoria como
`datetime` hasta el próximo `refresh_from_db()`, lo que rompía la respuesta
de la API justo después de un `POST /historial-servicios/` con
`AssertionError: Expected a date, but got a datetime` (500 real,
descubierto por el test nuevo `test_admin_can_create_historial`, no por
inspección de código). Corregido con un helper `_hoy()` (`timezone.now().
date()`) + migración `0012_alter_historialservicio_fecha_registro.py`,
aplicada a los 3 schemas reales (`home`/`qaisotest`/`shelltest1`, verificado
0 filas existentes en los 3 antes de aplicar — sin riesgo de dato).

**Hallazgo real corregido — DSV faltante en `vincular_proyecto`**: el
endpoint `HistorialServicioViewSet.vincular_proyecto` grababa
`proyecto_uuid`/`proyecto_nombre` sin verificar que el proyecto existiera o
perteneciera al tenant (a diferencia del endpoint equivalente en
`ProyectoViewSet`, que sí valida). Corregido agregando la misma validación.
Durante la corrección se encontró y arregló un bug de implementación propio
(intento inicial usaba `.exists()` sobre `qs_detail()`, que en realidad
devuelve una instancia o `None`, no un queryset — corregido a `is None`).

**Determinado, no inventado**: `HistorialServicio` expone GET/POST pero no
PUT/PATCH — confirmado que es una regla de negocio válida (inmutabilidad
del registro de prestación de servicio, mismo criterio que un asiento
contable), no un CRUD incompleto. No se agregó UPDATE/DELETE.

## Hallazgo de seguridad real — CRÍTICO — permisos de Movimiento (FASE 30/43)

`MovimientoInventarioViewSet.partial_update()` y `.destroy()` sobreescriben
los métodos equivalentes de `BaseViewSet` (que sí llaman
`_check_enforced_mode()` antes de proceder) **sin volver a aplicar ese
guard**. `IsTenantAdminOrReadOnly.has_permission()` delega la verificación
real al propio ViewSet cuando detecta el método `_check_enforced_mode`
(patrón ENFORCED MODE de todo el módulo) — así que, sin el guard local,
**no había ninguna verificación de rol en PATCH/DELETE de movimientos**: un
usuario VISOR u OPERADOR podía editar o eliminar cualquier movimiento de
Kardex (mutando `stock_actual` en el proceso), algo que ningún otro
endpoint mutante del módulo permite.

Encontrado por los tests nuevos `test_visor_cannot_update_movimiento` /
`test_visor_cannot_delete_movimiento` (fallaban con 200/204 en vez del 405
esperado). Corregido agregando `self._check_enforced_mode(request)` al
inicio de ambos métodos, mismo patrón que el resto del módulo.

## Qué NO se pudo verificar visualmente

Mismo límite de entorno documentado en la misión de Cotizaciones de esta
sesión: el navegador sandbox no puede resolver `*.sintel.net.co`. Toda la
verificación de esta misión es a nivel de servicio/API real (tests
`TenantTestCase` contra un schema PostgreSQL real, no mocks) + lectura de
código real del frontend — no clics reales de UI.
