# REM-P0-01 — Hard-delete de Facturas sin restricciones

**Estado:** VERIFIED (2026-08-28)
**Prioridad:** P0
**App propietaria:** `facturas`
**Fecha:** 2026-08-28

## Hallazgo

`FacturaViewSet.destroy()` (`apps/tenant/facturas/api/viewsets.py:532-625`,
política "v2.95") permitía eliminación física incondicional de cualquier
`Factura`, sin importar su `estado` — incluida una factura electrónica con
`cufe` ya reconocido por la DIAN (`estado='ACEPTADA'`). El propio código
documentaba la decisión explícitamente: *"No hay validaciones que bloqueen
la eliminación por vínculos contables o documentos relacionados."*

## Causa raíz

Decisión de producto histórica (v2.95) priorizando "depuración operativa sin
restricciones" sobre integridad fiscal/contable — no fue un bug de
implementación accidental, fue una política deliberada que la auditoría
empresarial de esta sesión (`documentacion/auditoria_empresarial/
BUSINESS_GAP_MATRIX.md`) reclasificó como riesgo real: el extractor de
Contabilidad (`apps/tenant/contabilidad/integracion/extractores/
facturas.py:52,71`) solo extrae facturas en `estado='ACEPTADA'` — borrar una
de esas deja el `AsientoContable` ya generado huérfano (`documento_origen_id`
apuntando a una fila inexistente).

## Impacto

Pérdida irreversible de trazabilidad fiscal/contable si se ejercía el DELETE
sobre una factura no-BORRADOR. Para una factura DIAN aceptada, además un
riesgo de cumplimiento (un documento electrónico aceptado no se "borra", se
corrige con Nota Crédito/Débito o se anula preservando el registro).

## Corrección

Bloquear el hard-delete salvo cuando `factura.estado == Estado.BORRADOR`
(único estado con evidencia real de que no hay extracción contable posible:
nunca fue `ENVIADA`, no tiene `cufe` aceptado). Para cualquier otro estado,
la vía sancionada es la anulación ya existente (`cambiar_estado` →
`ANULADA`, alcanzable desde todo estado no terminal según
`TRANSICIONES_VALIDAS`, `business_service.py:73-80`) — no se creó ningún
estado nuevo (no hizo falta migración).

La validación se colocó en la capa de negocio (`FacturaBusinessService.
eliminar_factura()`), no en `crud_service` (que por convención propia de
esta app es DML puro) ni solo en el ViewSet — siguiendo el patrón
ViewSet→Mixin→BusinessService→CRUDService del resto del proyecto.

## Archivos modificados

- `apps/tenant/facturas/services/business_service.py` — nuevo método
  `FacturaBusinessService.eliminar_factura()`: valida estado, delega a
  `FacturaCRUDService.eliminar()` si es válido.
- `apps/tenant/facturas/services/api_mixins.py` — `service_eliminar()` ahora
  llama a `FacturaBusinessService.eliminar_factura()` en vez de
  `FacturaCRUDService.eliminar()` directo; import de `FacturaCRUDService`
  removido (ya no usado en este archivo).
- `apps/tenant/facturas/api/viewsets.py` — `destroy()`: docstring corregida
  (ya no afirma "sin restricciones"), agregada rama `except ValidationError`
  ANTES del `except Exception` genérico (que si no, habría convertido el
  bloqueo en un 500 engañoso en vez de un 400 con el mensaje real).

## Modelo afectado

Ninguno — `Factura.Estado.ANULADA` ya existía como estado válido. Sin
migración.

## Tests

Nuevo archivo `apps/tenant/facturas/tests/test_remediation_p0_01_delete_guard.py`
(6 tests: delete en BORRADOR permitido; delete en ENVIADA/ACEPTADA/
RECHAZADA/ANULADA rechazado con 400; anulación vía `cambiar-estado` sigue
funcionando para una factura ACEPTADA). Se buscó primero un test existente
que cubriera `destroy()` — se encontró
`test_scope_facturas_f11.py::test_alcance_sede_no_puede_eliminar_factura_de_otra_sede`,
que crea una factura en BORRADOR pero falla antes por scope de sede (404) —
no requiere actualización, sigue pasando sin cambios (verificado en la misma
corrida).

## Governance

`manage.py check` y `makemigrations --check --dry-run` — pendiente de
confirmar en el barrido conjunto de P0 (ver `REMEDIATION_EXECUTION_STATUS.md`).

## Evidencia

```
apps/tenant/facturas/tests/test_remediation_p0_01_delete_guard.py .... [6/6 PASSED]
apps/tenant/facturas/tests/test_scope_facturas_f11.py .................. [6/6 PASSED]
12 passed in 1735.23s (0:28:55)
```
Corrida local completa (venv, sin Docker), 2026-08-28. Los 6 tests
preexistentes de `test_scope_facturas_f11.py` (incluido el único que ya
ejercitaba `destroy()`) siguen pasando sin modificación — confirma cero
regresión.

## Riesgos / deuda pendiente (explícitamente fuera del alcance mínimo de este fix)

- **No se implementó reversa automática de `AsientoContable`/
  `MovimientoInventario` al transicionar una factura ACEPTADA a `ANULADA`.**
  El mecanismo real de reversa (`Contabilidad.integracion.contabilizador.
  Contabilizador.reversar_asiento()`) existe y es correcto, pero conectarlo
  requeriría que `facturas` localice los asientos por
  `documento_origen_app='facturas'`/`documento_origen_id=factura.id` (no
  existe hoy un selector/InterApp API de solo-lectura para eso desde fuera
  de `contabilidad`) y decidir el punto de disparo (¿automático al anular,
  o una acción explícita separada?). Esto es un hallazgo real pero distinto
  al de este ítem (que era específicamente "el DELETE no debe ser posible")
  — se deja documentado aquí para una misión de remediación futura, no se
  improvisó una integración cross-app nueva sin verificación completa.
- La política v2.95 sigue permitiendo hard-delete de facturas `BORRADOR`
  con notas de crédito asociadas (`FacturaCRUDService.eliminar()` intenta
  borrar la NC primero) — un `BORRADOR` no debería tener NC real asociada
  en la práctica (las NC se generan sobre facturas ya emitidas), así que
  este caso se considera de riesgo teórico, no se tocó.
