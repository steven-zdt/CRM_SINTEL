# COTIZACIONES_STATE_MACHINE — máquina de estados (COTIZACIONES-01)

Fecha: 2026-09-08.

## Contexto

Tres auditorías previas del módulo (`.agent/AUDITORIA_FLUJO_COMPLETO.md`,
`documentacion/audits/cotizaciones/MATRIZ_ESTADOS_COTIZACION.md`,
`docs/cotizaciones/COTIZACIONES_RELEASE_GATE.md`, todas antes de esta misión)
confirmaron con evidencia real que el campo `estado` de `Cotizacion` era
**decorativo**: existía en el modelo, se mostraba con badges de color en la
UI, pero era editable vía `PATCH` genérico sin ninguna validación de
transición, y no existía ningún endpoint de negocio (`enviar`, `aprobar`,
etc.). Esta misión cierra ese gap.

**Nombres reales de estado** (verificados en `models.py`, no inventados):
`BORRADOR`, `ENVIADA`, `ACEPTADA`, `CANCELADA` — la misión original asumía
`BORRADOR/ENVIADA/APROBADA/ARCHIVADA`, que no existen en este dominio.
Decisión del usuario: construir la máquina sobre los 4 estados reales, sin
migración de datos ni renombrado.

## Transiciones válidas

Única fuente de verdad: `CotizacionService.TRANSICIONES_VALIDAS`
(`apps/tenant/cotizaciones/services/business_service.py`).

```python
TRANSICIONES_VALIDAS = {
    BORRADOR:  {ENVIADA, CANCELADA},
    ENVIADA:   {BORRADOR, ACEPTADA, CANCELADA},
    ACEPTADA:  set(),   # terminal
    CANCELADA: set(),   # terminal
}
```

```
BORRADOR ──enviar──> ENVIADA ──aceptar──> ACEPTADA (terminal)
   │                    │  │
   │                    │  └─volver_a_borrador──> BORRADOR
   └──cancelar──> CANCELADA <──cancelar──┘
                  (terminal)
```

**Rechazadas explícitamente** (verificado con test): `BORRADOR→ACEPTADA`
(no se puede saltar ENVIADA), cualquier transición desde `ACEPTADA` o desde
`CANCELADA` (ambos son terminales — ACEPTADA para no alterar en silencio una
propuesta ya aprobada por el cliente; CANCELADA para no reactivar una
cotización descartada sin crear una nueva).

## Autoridad de la transición

- **Siempre en backend.** `estado` fue removido de `allowed_fields` en
  `CotizacionService.actualizar_cotizacion()` — un `PATCH {"estado": "..."}`
  genérico ya no tiene ningún efecto (se ignora en silencio, coherente con
  el resto de `allowed_fields`).
- Única vía: `CotizacionService.cambiar_estado(instance, nuevo_estado)`,
  con `select_for_update()` sobre la fila de la Cotización (serializa
  transiciones concurrentes — mismo patrón que `generar_codigo_unico()`).
- **Idempotente** (mandato §10): repetir la transición actual (ej. `enviar`
  dos veces sobre algo ya `ENVIADA`) no es un error — devuelve la cotización
  tal cual. Solo una transición a un estado *distinto* no permitido por la
  tabla es rechazada (`ValidationError`, 400).

## Endpoints (`CotizacionViewSet`, `apps/tenant/cotizaciones/api/viewsets.py`)

| Endpoint | Transición | Permiso |
|---|---|---|
| `POST /api/v1/cotizaciones/{uuid}/enviar/` | → ENVIADA | ADMIN (mismo binario que el resto del módulo) |
| `POST /api/v1/cotizaciones/{uuid}/volver-a-borrador/` | → BORRADOR | ADMIN |
| `POST /api/v1/cotizaciones/{uuid}/aceptar/` | → ACEPTADA | ADMIN |
| `POST /api/v1/cotizaciones/{uuid}/cancelar/` | → CANCELADA | ADMIN |
| `POST /api/v1/cotizaciones/{uuid}/convertir-a-venta/` | (no cambia estado de Cotizacion) | ADMIN |

No se usaron los nombres literales `aprobar`/`archivar` del mission brief
original porque no corresponden al dominio real (`aceptar`/`cancelar` sí).

## Cotización → Venta

Ver `docs/cotizaciones/COTIZACIONES_INTEGRATIONS.md` para el mapa completo.
Resumen: `CotizacionService.convertir_a_venta()`, solo permitido desde
`ACEPTADA`, idempotente (constraint `unique=True` en `Venta.cotizacion_uuid`
+ guard explícito en el service — una sola Venta por Cotización, click
repetido devuelve la misma). Requiere que la cotización tenga cliente e
items; los items se copian como snapshot (descripción/cantidad/precio/IVA)
sin vincular producto/servicio de Inventario (ver limitación documentada en
`COTIZACIONES_INTEGRATIONS.md` — catálogos no unificados).

## Verificación

`apps/tenant/cotizaciones/tests/test_state_machine.py` — 13 tests: cada
transición válida, cada transición rechazada, idempotencia, estado
inválido, y que `PATCH` genérico ya no cambia `estado`.
`apps/tenant/cotizaciones/tests/test_convertir_a_venta.py` — 7 tests:
conversión exitosa (con verificación de totales/items), idempotencia
(3 llamadas = 1 sola Venta), rechazo desde BORRADOR/ENVIADA, rechazo sin
cliente/sin items, aislamiento cross-tenant.
