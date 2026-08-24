# Ciclo Comercial — Idempotencia (FASE COMERCIAL-04)

**Fecha:** 2026-08-24. **Estado:** Implementado. Corrige un bug de diseño
real encontrado en `COMERCIAL_01_AUDITORIA.md` §5-6, más allá de lo que
esa fase había anticipado.

```
misma venta + misma empresa = misma operación de facturación
                    (sin duplicados accidentales)
```

---

## 1. El descubrimiento que cambió el diseño

`COMERCIAL_01_AUDITORIA.md` §6 documentó un gap de idempotencia genérico
("un doble-click crea 2 Venta+Factura"). Al conectar el mecanismo elegido
(ver §2), se encontró algo más específico y más grave: **`POST /ventas/
{uuid}/procesar-facturar/` nunca promovía la `Venta` del URL** —
`VentaViewSet.procesar_facturar()` (`apps/tenant/ventas/api/
viewsets.py:108`) copiaba los datos de esa `Venta` (`self.get_object()`)
a un payload nuevo y llamaba a `procesar_y_facturar_venta()`, que
**siempre** creaba una `Venta`+`Factura` completamente independientes vía
`VentaCRUDService.crear_venta()`. La `Venta` original del URL nunca se
tocaba: quedaba `BORRADOR` para siempre, huérfana, mientras la que
realmente se facturó tenía un UUID distinto.

Esto no es "doble-click duplica" — es que **el flujo normal de un solo
click ya duplicaba, por diseño**, cada vez que se llamaba.

---

## 2. Decisión de diseño (usuario)

Dos preguntas resueltas explícitamente antes de implementar (ver
transcript de la sesión):

1. **Mecanismo:** Idempotency-Key HTTP fue la primera elección, pero al
   descubrirse §1, se re-evaluó: el `Venta.uuid` que ya viaja en el URL
   de `procesar-facturar/{uuid}/` es un ancla de idempotencia más natural
   que pedirle al frontend generar y enviar un header nuevo — **y
   corrige el bug de duplicación de diseño en el mismo cambio**. Elegido:
   usar `Venta.uuid`.
2. **Alcance:** corregir ahora (no solo documentar), dado que ya se había
   corregido un bug de atomicidad real en la misma sesión (COMERCIAL-01
   §5) siguiendo el mismo criterio de "encontrado con evidencia real →
   corregir".

---

## 3. Implementación

**`VentaBusinessService.procesar_y_facturar_venta()`**
(`apps/tenant/ventas/services/business_service.py:491`) — nuevo parámetro
opcional `venta_existente: Venta = None`, backward-compatible (todos los
call sites existentes, incluida la suite F23, no lo pasan y siguen
creando una `Venta` nueva sin cambios):

- `venta_existente.estado == FACTURADA_DIAN` → **replay idempotente**:
  retorna `(True, venta_existente, 200)` inmediatamente, sin ejecutar
  DSV, sin CUFE, sin XML, sin tocar Inventario. Cero efectos secundarios
  en un reintento.
- `venta_existente.estado == ANULADA` → rechazado, `(False, {...}, 400)`.
- `venta_existente.estado == BORRADOR` → el "Paso 3" (antes: siempre
  `VentaCRUDService.crear_venta()`) ahora es condicional: si hay
  `venta_existente`, se **promueve esa misma fila** (se le asigna
  `resolucion`/`numero_factura` y se reutiliza para el resto del flujo)
  en vez de crear una nueva. El resto del pipeline (DTO → CUFE → XML →
  firma → `crear_factura_desde_venta()` → `vincular_factura()` →
  `_generar_salida_inventario()`) no cambió.

**`VentaServiceMixin.service_procesar_y_facturar()`**
(`apps/tenant/ventas/services/api_mixins.py:24`) — nuevo parámetro
`venta_existente=None`, pasado directo al business service.

**`VentaViewSet.procesar_facturar()`**
(`apps/tenant/ventas/api/viewsets.py:108`) — ahora pasa
`venta_existente=venta` (la `Venta` ya resuelta por `self.get_object()`,
DSV-verificada por el ViewSet). **Segundo fix en el mismo cambio:** la
vista devolvía siempre `status.HTTP_201_CREATED` sin importar el
`status_code` real devuelto por el service — ahora usa `status_code`
directamente, así que un replay idempotente responde `200`, no `201`
(coherente con la semántica HTTP: `200` = "aquí está el recurso que ya
existía", `201` = "acabo de crearlo").

---

## 4. Qué NO cambió (alcance mínimo)

- `crear_venta_borrador()`/`POST /ventas/` — sin cambios, sigue creando
  una `Venta` `BORRADOR` nueva cada vez (correcto, es su propósito).
- El contrato DTO (`_construir_dto_factura()`) — sin cambios, sigue
  recibiendo el `payload` reconstruido por el ViewSet a partir de la
  `Venta`/`ItemVenta` existentes (mismo mecanismo de antes, no se leen
  los `ItemVenta` persistidos directamente dentro del business service).
- `crear_venta()` (`VentaCRUDService`) — sin cambios; el camino "crear
  Venta nueva" (`venta_existente=None`) sigue siendo el flujo de siempre.
- No se introdujo ningún `Idempotency-Key` HTTP nuevo, ni campo/tabla
  nueva en el modelo — el ancla ya existía (`Venta.uuid`), no hizo falta
  infraestructura adicional.

---

## 5. Verificación

- `manage.py check`: 0 issues.
- Suite nueva dedicada:
  `apps/tenant/ventas/tests/test_comercial_04_idempotencia.py` — 3 tests:
  promoción de la misma fila (no crea hermana), reintento sobre venta ya
  facturada (200, sin duplicar `Factura` ni `MovimientoInventario`), y
  rechazo de venta `ANULADA`.
- Regresión dirigida: `test_f23_venta_inventario.py`,
  `test_f23_venta_inventario_multitenant.py` (código, no ViewSet, del
  flujo "crear Venta nueva" — confirma que `venta_existente=None` no
  cambió comportamiento), `test_scope_ventas_facturas_f10.py`
  (`crear_factura_desde_venta()`, sin cambios, pero mismo pipeline).

Ver resultados exactos en el commit de esta fase.

---

## 6. Estado formal

**`COMERCIAL-04 = COMPLETED`.** El gap de idempotencia documentado en
COMERCIAL-01 §6 queda resuelto para el único punto de entrada real que
existe hoy (`POST /ventas/{uuid}/procesar-facturar/`) — no quedó como
diseño pendiente, se implementó en la misma fase por decisión explícita
del usuario tras confirmar el mecanismo correcto.
