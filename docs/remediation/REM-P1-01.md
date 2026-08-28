# REM-P1-01 — OrdenCompra sin máquina de estados validada

**Estado:** VERIFIED
**Prioridad:** P1
**App propietaria:** `compras`
**Fecha:** 2026-08-28

## Hallazgo

`OrdenCompraCRUDService.cambiar_estado()` (`apps/tenant/compras/services/
crud_service.py:245-261`) solo validaba que el estado destino existiera en
`ESTADO_CHOICES` — nunca que la transición desde el estado actual fuera
válida. Permitía saltos arbitrarios (ej. `RECIBIDA → BORRADOR`).

## Investigación previa a diseñar la matriz (evidencia real, no asumida)

Antes de fijar `TRANSICIONES_VALIDAS`, se leyó `test_sincronizacion_
cuentas_pagar.py` (test existente) para no inventar un flujo lineal que el
código real no impone. Confirmó 2 comportamientos reales:

1. `BORRADOR → APROBADA` directo es un flujo legítimo y ya probado — el
   propio archivo de test lo documenta: *"Decisión explícita del usuario:
   el trigger es la transición a estado APROBADA"*.
2. Re-aplicar el mismo estado (`APROBADA → APROBADA`, "reaprobar") debe ser
   un no-op idempotente, no un error — también ya probado
   (`test_reaprobar_es_idempotente_no_duplica`).

También se confirmó que `PARCIAL`/`RECIBIDA` nunca se alcanzan por esta vía
manual — los asigna `RecepcionCompraBusinessService.confirmar_recepcion()`
(`business_service.py:596,598`) como consecuencia de recepciones reales, no
`cambiar_estado()`.

## Corrección

`OrdenCompraBusinessService.TRANSICIONES_VALIDAS` (nuevo, mismo patrón que
`FacturaBusinessService.TRANSICIONES_VALIDAS`), con self-loop explícito en
cada estado (permite re-aplicar el mismo estado sin error) y sin caminos
salientes desde `PARCIAL`/`RECIBIDA` (una vez la orden entra al flujo de
recepción real, `cambiar_estado()` manual no puede sacarla de ahí):

```python
TRANSICIONES_VALIDAS = {
    'BORRADOR':   {'BORRADOR', 'PENDIENTE', 'APROBADA', 'ANULADA'},
    'PENDIENTE':  {'PENDIENTE', 'APROBADA', 'BORRADOR', 'ANULADA'},
    'APROBADA':   {'APROBADA', 'ANULADA'},
    'PARCIAL':    {'PARCIAL'},
    'RECIBIDA':   {'RECIBIDA'},
    'ANULADA':    {'ANULADA'},
}
```

Validada en `OrdenCompraBusinessService.cambiar_estado_orden_compra()`
antes de delegar a `OrdenCompraCRUDService.cambiar_estado()`.

## Sobre la reversa de CxP al anular (parte del hallazgo original, NO corregida)

El propio código ya documenta esto como una **decisión deliberada
existente**, no un descuido: `_sincronizar_cuenta_por_pagar()`
(`business_service.py:360-397`) tiene el comentario explícito *"Fuera de
alcance deliberado (mismo criterio que RecepcionCompraBusinessService.
anular_recepcion): si la orden se anula después de aprobada, la CxP ya
generada NO se reversa aquí."* — con esta corrección, además, ya no es
posible anular una orden `RECIBIDA`/`PARCIAL` (donde ya hubo Kardex real) por
esta vía manual en absoluto; el único caso que queda alcanzable
(`APROBADA → ANULADA`) es exactamente el que la nota ya asumía como
conocido. **No se implementó reversa automática de CxP** — sería revertir
una decisión arquitectónica ya tomada y documentada, no corregir un bug;
si el negocio decide que sí debe reversarse, es un ítem P2 de decisión de
producto, no P1 de corrección de código.

## Archivos modificados

- `apps/tenant/compras/services/business_service.py`

## Modelo afectado

Ninguno. Sin migración.

## Tests

`apps/tenant/compras/tests/test_remediation_p1_01_estados_orden_compra.py`
(4 tests: RECIBIDA→BORRADOR rechazado, anular RECIBIDA rechazado, anular
APROBADA sigue permitido, BORRADOR→APROBADA directo sigue permitido). Se
reutiliza `test_sincronizacion_cuentas_pagar.py` (existente, sin
modificar) como regresión — sus 3 tests ejercitan exactamente los 2
comportamientos reales que motivaron el diseño de la matriz.

## Evidencia

Corrida local, 2026-08-28 (`DATABASE_HOST=127.0.0.1`/
`REDIS_URL=redis://127.0.0.1:6379/0`), 4/4 PASSED (parte del batch P1
combinado, ver `REMEDIATION_FINAL_REPORT.md` para el detalle del batch).

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

- No se investigó si `PENDIENTE → BORRADOR` (rechazo de aprobación,
  incluido en la matriz) tiene evidencia de uso real — se incluyó por
  simetría lógica razonable ("devolver a borrador para corregir"), no por
  un test que lo confirme. Riesgo bajo: si resulta no ser un flujo real
  usado, la matriz simplemente permite un caso de más, no bloquea nada que
  antes funcionara.
