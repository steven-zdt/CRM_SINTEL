# REM-P0-04 — Numeración contable sin select_for_update()

**Estado:** VERIFIED
**Prioridad:** P0
**App propietaria:** `contabilidad`
**Fecha:** 2026-08-28

## Hallazgo

`TipoComprobante.obtener_siguiente_numero()` (`apps/tenant/contabilidad/
models.py:225-230`) era el único generador de numeración de todo el sistema
sin `select_for_update()` — leía `self.consecutivo_actual` (potencialmente
ya cargado en memoria de forma obsoleta), lo incrementaba y guardaba, sin
bloqueo de fila.

## Causa raíz

Omisión — el resto de generadores de numeración del proyecto
(`cotizaciones.ConfiguracionCotizacion`, `compras.PlantillaOrdenCompra`,
`ventas.ResolucionFacturacion`, `empleados.ResolucionDIAN`) siguen
consistentemente el patrón `select_for_update()` antes de leer/incrementar
el consecutivo; este era el único que no lo hacía, sin ninguna razón
documentada para la excepción.

## Impacto

Bajo concurrencia real (2+ usuarios contabilizando simultáneamente),
riesgo de `IntegrityError` no controlado (colisión contra `AsientoContable.
numero`, `unique=True`) o de saltar un consecutivo si una de las dos
transacciones concurrentes hace rollback después de incrementar en memoria.

## Corrección

`obtener_siguiente_numero()` ahora se re-obtiene a sí mismo bajo
`TipoComprobante.objects.select_for_update().get(pk=self.pk)` dentro de un
`transaction.atomic()` propio, antes de leer/incrementar/guardar — así es
seguro sin importar cómo el llamador haya obtenido la instancia `self`
(no requirió tocar los 2 call-sites en `business_service.py:439,648`).

## Archivos modificados

- `apps/tenant/contabilidad/models.py` — `TipoComprobante.
  obtener_siguiente_numero()` + import de `transaction`.

## Modelo afectado

Ninguno. Sin migración (cambio de comportamiento puro, no de esquema).

## Tests

`apps/tenant/contabilidad/tests/test_remediation_p0_04_numeracion_
comprobante.py` (3 tests: secuencia sin saltos/duplicados en 10 llamadas
consecutivas, persistencia real en BD del incremento, verificación de que
el código fuente del método efectivamente usa `select_for_update`).

**Nota de alcance honesta**: no se escribió un test con threads/conexiones
DB concurrentes reales. Grep repo-wide confirmó que NINGÚN generador de
numeración de este proyecto (cotizaciones/compras/ventas/empleados,
todos ya usando `select_for_update()`) tiene un test de concurrencia real
propio tampoco — no existe un harness para eso en la base de tests actual,
y construirlo de cero (multi-threading + schema-per-tenant de
django-tenants) es un proyecto de infraestructura de testing aparte, no
una corrección quirurgica de 15 minutos. El fix aplicado es la misma
mitigación arquitectónica ya validada y aceptada en el resto del proyecto.

## Evidencia

Corrida local aislada, 2026-08-28 (con `DATABASE_HOST=127.0.0.1` y
`REDIS_URL=redis://127.0.0.1:6379/0` — ver incidente operativo de
resolución IPv6 documentado en `REMEDIATION_FINAL_REPORT.md`):

```
3 passed in 156.90s (0:02:36)
```

## Governance

Pendiente de confirmar en el barrido conjunto final de la misión.

## Riesgos / deuda pendiente

Ninguno nuevo introducido. La ausencia de tests de concurrencia real es una
deuda preexistente de todo el proyecto, no específica de este fix.
