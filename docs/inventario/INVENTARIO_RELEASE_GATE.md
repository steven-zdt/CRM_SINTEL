# Inventario — Release Gate (misión de modernización integral, FASE 55-58)

**Fecha:** 2026-08-27

---

## Veredicto: `INVENTARIO = COMPLETED_WITH_DEFERRED`

No se declara `PRODUCTION_READY` porque quedan mejoras opcionales/menores
documentadas y no corregidas (ver abajo). No hay `BLOCKED_SAFE` — no queda
ningún bloqueo externo. No hay fallo de creación, inconsistencia de stock,
fuga de tenant, doble movimiento ni corrupción de Kardex activos. Sí se
encontraron y corrigieron 2 hallazgos que antes de esta misión SÍ calificaban
como bloqueantes reales (ver checklist).

---

## Checklist (FASE 57)

- [x] Categorías CRUD — completo, sin cambios necesarios.
- [x] Productos CRUD — completo, guard de borrado verificado con test real.
- [x] Servicios CRUD — completo, guard de borrado verificado con test real.
- [x] Activos CRUD — **corregido hoy**: guard de borrado (inactivar antes de
      borrar) no existía, ahora reutiliza `estado` (BAJA/VENDIDO permiten
      borrar, ACTIVO/MANTENIMIENTO lo bloquean).
- [x] Historial correctamente definido — confirmado que GET/POST sin
      UPDATE/DELETE es una regla de negocio válida (inmutabilidad), no un
      CRUD incompleto.
- [x] Kardex — `registrar_movimiento`/`actualizar_movimiento`/
      `eliminar_movimiento`/`registrar_movimiento_activo` con 19 tests
      nuevos reales (antes: 0 tests directos del motor).
- [x] Stock — invariante `entradas - salidas` confirmado con test real, sin
      cambios a la fórmula (sin evidencia de necesidad).
- [x] Costo promedio — drift de documentación corregido (es estático por
      decisión deliberada, nunca recalculado automáticamente; la doc previa
      afirmaba lo contrario). No se cambió el comportamiento.
- [x] Concurrencia — `select_for_update()` confirmado en
      `recalcular_stock_producto` y en las 5 transiciones de
      `TrasladoInventarioService`.
- [x] Idempotencia — `UniqueConstraint` por documento origen confirmado
      (Compras, Ventas, Facturas/NC, Traslados F21).
- [x] Tenant — 4 tests nuevos de aislamiento cross-schema real (Producto,
      Categoria, ActivoFijo) además del ya existente de Traslados.
- [x] Empresa — DSV confirmado en todos los métodos de `KardexService` (2
      métodos —`actualizar_movimiento`/`eliminar_movimiento`— no
      reverificaban `empresa_id` dentro del propio método; corregido con
      defensa en profundidad, sin explotabilidad real hoy).
- [x] Sede/Área — opcional donde aplica (Movimiento, Traslado), sin
      inventar campos donde no había evidencia de necesidad.
- [x] Permisos — **hallazgo CRÍTICO real corregido**: ver sección dedicada
      abajo.
- [x] Compras/Ventas/Facturas/Gastos/Contabilidad/Proyectos — las 7
      integraciones cross-app auditadas con evidencia de código real; 6
      confirmadas seguras sin cambios, 1 (Proyectos) con un gap de DSV
      corregido.
- [x] UI moderna / formularios — 8 bugs reales de frontend corregidos (ver
      `INVENTARIO_UI_GUIDE.md`).
- [x] Responsive — auditado, sin bugs reales.
- [x] Accesibilidad — `aria-label` agregado a los botones de icono de las 4
      tablas migradas.
- [x] Performance — 1 N+1 real corregido (`SERVICIO_LIST_FIELDS`
      incompleto).
- [x] Legacy auditado — `crud_service.py` completo (7 funciones, 266
      líneas, cero consumidores reales) + `inventario_list.js` (Tabulator
      legacy huérfano) eliminados. Endpoints `dt/` ya no existían (doc
      desactualizada, corregida).
- [x] Tests existentes saneados — 24 tests previos inventariados y
      confirmados válidos (ninguno duplicado/obsoleto); 41 tests nuevos
      agregados solo donde había gap real confirmado por grep.
- [x] Documentación — este documento + `INVENTARIO_BASELINE.md` +
      `INVENTARIO_END_TO_END.md` + `INVENTARIO_RELATION_MATRIX.md` +
      `INVENTARIO_UI_GUIDE.md`, más correcciones puntuales al `.agent/
      AUDITORIA_FLUJO_INVENTARIO.md` histórico (drift documentado, no
      reescrito).
- [x] Governance — `manage.py check` limpio, `makemigrations --check`
      limpio tras aplicar la migración nueva, 1 migración generada y
      aplicada a los 3 tenants reales (verificado 0 filas afectadas antes
      de aplicar), gobernanza EKG ejecutada (hallazgos preexistentes de
      todo el repo, ninguno introducido por esta misión — ver abajo).

---

## Hallazgo real más importante: bypass de permisos en Movimientos de Kardex (CRÍTICO)

`MovimientoInventarioViewSet.partial_update()` y `.destroy()`
sobreescribían los métodos de `BaseViewSet` que sí aplican
`_check_enforced_mode()` (el guard "solo ADMIN puede mutar"), sin volver a
llamar ese guard. Como `IsTenantAdminOrReadOnly.has_permission()` delega la
verificación real al propio ViewSet cuando detecta ese método (patrón
ENFORCED MODE usado en todo el módulo), el resultado neto era que **PATCH y
DELETE sobre un movimiento de Kardex no tenían ninguna verificación de rol**
— cualquier usuario autenticado del tenant (VISOR, OPERADOR) podía editar o
eliminar movimientos, mutando `stock_actual` en el proceso.

Encontrado por 2 tests nuevos (`test_visor_cannot_update_movimiento`,
`test_visor_cannot_delete_movimiento`) que fallaban con 200/204 en vez del
405 esperado — no se detectó por inspección de código, se detectó porque el
test ejercitó el camino real. Corregido agregando el guard faltante a
ambos métodos, mismo patrón que el resto del módulo.

## Otros 2 hallazgos reales encontrados por los tests nuevos (no por auditoría estática)

1. **`HistorialServicio.fecha_registro = DateField(default=timezone.now)`**
   — mismo anti-patrón (y mismo fix) que `Cotizacion.fecha_emision` en la
   misión de Cotizaciones de esta sesión: `timezone.now` devuelve un
   `datetime`, no un `date`, rompiendo la respuesta de la API justo después
   de crear (`AssertionError` real, 500). Corregido con un helper `_hoy()`
   + migración `0012`, aplicada a los 3 tenants reales (0 filas afectadas).
2. **Bug propio introducido y corregido en la misma pasada**: al agregar la
   validación DSV a `vincular_proyecto` (ver `INVENTARIO_RELATION_MATRIX.md`),
   el primer intento asumía que `qs_detail()` de Proyectos devolvía un
   queryset (`.exists()`); en realidad devuelve una instancia o `None`
   (`.first()` interno). El test nuevo lo detectó en el primer run;
   corregido antes de considerar el fix completo.

## Governance EKG — hallazgos preexistentes, no introducidos por esta misión

`python -m tools.ekg.governance --offline` reporta 3 categorías de fallo
repo-wide (23 ViewSets sin Service Layer detectado, 6 modelos con
sede/área sin marcador "sede-aware", 2 ciclos de import entre apps
core/empresa/perfil). Los 3 son preexistentes y abarcan apps no tocadas por
esta misión (`core`, `contabilidad`, `perfil`, `empresa`, `facturas`,
`proyectos`, `empleados`, además de la propia `inventario` en el primer
ítem — pero como `BaseViewSet`, la clase base abstracta, no un ViewSet
concreto con queries directas). Ninguno se originó en los cambios de hoy;
no se tocó código fuera de `apps/tenant/inventario/` salvo la validación
DSV puntual en `HistorialServicioViewSet` (que sí pasa por Service Layer).

---

## Deuda documentada explícitamente (no inventada, no cerrada)

- **Doble endpoint `vincular_proyecto`**: el de Inventario ahora valida DSV
  igual que el de Proyectos, pero siguen siendo 2 endpoints separados para
  la misma operación. No se consolidaron — cambiar cuál endpoint usa el
  frontend real es una decisión de producto fuera de esta auditoría.
- **`item_service.py` sin DSV en producto/servicio de items de Cotización**
  (hallazgo de la misión anterior, repetido aquí por relevancia): si algún
  día se conecta el catálogo de Inventario al picker de ítems de
  Cotización, esa integración deberá agregar DSV explícito.
- **Fricciones de UX menores no corregidas**: campo `cliente_referencia`
  fantasma en el payload de movimientos, sin campo de búsqueda dedicado en
  algunas grillas — documentadas en `INVENTARIO_UI_GUIDE.md`, no críticas.
- **`api_mixins.py` sigue concentrando los 6 Service Mixins en un solo
  archivo** (en vez de uno por modelo) — asimetría de organización, no un
  bug funcional; DEUDA-05 de la doc histórica quedó parcialmente resuelta
  (`IngestaService` sí se separó) pero esta parte no.
