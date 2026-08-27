# Matriz de Estados — Cotizacion (FASE 12/13)

**Fecha:** 2026-08-26
**Fuente:** `apps/tenant/cotizaciones/models.py::Cotizacion.Estado` + grep exhaustivo de todo el árbol Python de la app en busca de asignaciones/transiciones reales.

## Estados reales (choices tal como están en el código)

```python
class Estado(models.TextChoices):
    BORRADOR = 'BORRADOR', _('Borrador')
    ENVIADA = 'ENVIADA', _('Enviada')
    ACEPTADA = 'ACEPTADA', _('Aceptada')
    CANCELADA = 'CANCELADA', _('Cancelada')
```

Default: `BORRADOR`.

## Hallazgo central: no existe máquina de estados

Grep exhaustivo confirma que la **única** asignación de `estado` en todo el código Python de la app es `estado=Cotizacion.Estado.BORRADOR` en `CotizacionService.crear_preforma()` (creación). No existe ningún endpoint, `@action`, método de servicio, ni lógica alguna que transicione una Cotización a `ENVIADA`, `ACEPTADA` o `CANCELADA`.

El campo SÍ está en `allowed_fields` de `CotizacionService.actualizar_cotizacion()` — es decir, es técnicamente escribible vía `PATCH {"estado": "..."}` directo a la API, **sin ninguna validación de transición**. Cualquier valor entre los 4 choices es aceptado sin importar el estado actual.

El frontend (`editor_cotizacion.html`, `cotizaciones.table.js`) solo **lee** `estado` para pintar badges de color — nunca lo envía en el payload de guardado. Es decir, hoy es **imposible cambiar el estado desde la UI real**, aunque la API lo permitiría si se le pidiera directamente.

## Matriz por estado (según lo que el código REALMENTE permite hoy, no lo que el nombre del estado sugeriría)

| Estado | Puede crear | Puede editar (cabecera+items) | Puede eliminar | Puede enviar | Puede aceptar | Puede rechazar | Puede convertir | Puede facturar (vía bridge manual) |
|---|---|---|---|---|---|---|---|---|
| `BORRADOR` | N/A (es el estado inicial) | Sí (sin restricción) | Sí, si no tiene Factura vinculada (fix FASE 5, ver `CRUD_COMPLETE_REPORT.md`) | Sin implementación | Sin implementación | Sin implementación | No existe conversión (ver hallazgo FASE 17-19) | Sí (bridge manual, independiente del estado) |
| `ENVIADA` | — | **Sí (sin restricción real)** — el nombre sugeriría bloqueo, el código no lo aplica | Sí, mismo chequeo que arriba | — | — | — | — | Sí, mismo bridge |
| `ACEPTADA` | — | **Sí (sin restricción real)** — mismo hallazgo | Sí, mismo chequeo | — | — | — | — | Sí, mismo bridge |
| `CANCELADA` | — | **Sí (sin restricción real)** — mismo hallazgo, contraintuitivo para un estado terminal | Sí, mismo chequeo | — | — | — | — | Sí, mismo bridge |

**Nota de lectura:** las columnas "puede editar" están marcadas "Sí (sin restricción real)" en los 4 estados porque literalmente no hay código que las diferencie — no es que el negocio haya decidido que todos los estados son editables, es que la restricción nunca se implementó. Esto se documenta aquí como un GAP explícito, no como un diseño validado.

## Decisión de esta auditoría: no se construyó una máquina de estados nueva

Por la Regla #1 de la misión ("no inventar") y la ausencia total de evidencia de negocio sobre qué transiciones deberían existir, sus disparadores, o sus efectos secundarios (¿"ENVIADA" debería enviar un email? ¿"ACEPTADA" debería generar algo?), **no se implementó ninguna transición de estado, endpoint de envío/aceptación/rechazo, ni bloqueo de edición por estado** en esta pasada. Inventar esa lógica sin evidencia violaría directamente la Regla #1.

**Lo que sí se puede afirmar con evidencia:** el campo `estado` hoy es decorativo (solo UI, solo lectura desde el frontend) y potencialmente peligroso si se usa directamente contra la API (permite marcar `CANCELADA` una cotización y seguir editándola/facturándola sin ninguna advertencia).

**Recomendación para una fase posterior (no ejecutada aquí, requiere decisión de negocio explícita):** si el dominio real necesita una máquina de estados, debe diseñarse con el dueño de negocio antes de codificar — esta auditoría solo deja el diagnóstico, consistente con el resto de la misión REL de este mismo día (ver `docs/integration/CROSS_APP_FINDINGS.md`, mismo patrón aplicado a la ausencia de máquina de estados en Facturas FISCAL-03).
