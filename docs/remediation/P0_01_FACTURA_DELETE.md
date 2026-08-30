# P0-01 — Facturas sin hard-delete destructivo

**Estado:** VERIFIED
**App propietaria:** `facturas`
**Fecha:** 2026-08-28 (corregido) / 2026-08-28 (re-verificado, esta pasada)

## Hallazgo

`FacturaViewSet.destroy()` permitía eliminar físicamente cualquier
`Factura` sin importar su estado — incluyendo facturas `ACEPTADA` con
CUFE reconocido por la DIAN y con `AsientoContable` ya extraído por
Contabilidad. Un `DELETE` dejaba el asiento contable huérfano
(`documento_origen_id` apuntando a una fila que ya no existe) y
destruía evidencia fiscal/documental sin dejar rastro.

## Causa raíz

Ausencia de guard de estado en el Service Layer:
`FacturaCRUDService.eliminar()` se invocaba directamente desde
`FacturaServiceMixin.service_eliminar()` sin ninguna validación previa
de negocio.

## Corrección (capa propietaria: `facturas`)

Ver matriz completa de estados en `P0_01_FACTURA_DELETE_MATRIX.md`.

- `FacturaBusinessService.eliminar_factura()` (nuevo, `@transaction.atomic`):
  bloquea el `DELETE` salvo `factura.estado == BORRADOR`. Reutiliza el
  mecanismo de anulación YA EXISTENTE (`cambiar_estado()` →
  `TRANSICIONES_VALIDAS`, alcanza `ANULADA` desde todo estado no
  terminal) como única vía sancionada para "eliminar" una factura con
  impacto — no se creó un estado ni un mecanismo nuevo.
- `FacturaServiceMixin.service_eliminar()`: ahora llama a
  `eliminar_factura()` en vez de al CRUD directo.
- `FacturaViewSet.destroy()`: captura `ValidationError` → HTTP 400 (antes
  cualquier excepción no capturada caía al handler genérico → 500,
  ocultando el motivo real detrás de un error de servidor).

## Preservación de trazabilidad

La anulación (`ANULADA`) **no borra la factura** — conserva: número,
CUFE, XML/documento origen, relaciones a `ItemFactura`, `Retencion`,
`ImpuestoDocumento`, `TransmisionFactura`, y el vínculo a `Venta`
(`factura_asociada`). Solo `BORRADOR` (sin CUFE, nunca transmitida) se
elimina físicamente — exactamente el caso sin ningún impacto documental.

## Impacto cross-app verificado (no modificado automáticamente — regla del plan)

Anular una `Factura ACEPTADA` **no dispara** una reversa automática de:

- `AsientoContable` (Contabilidad) — permanece como fue extraído.
- `MovimientoInventario` (Inventario) — permanece.
- Conciliación bancaria (Bancos) — no se toca.

Esto es una decisión de alcance explícita, no un descuido: implementar
la reversa automática cross-app requeriría diseñar el contrato de
reversa en cada dominio propietario (`Contabilizador.reversar_asiento()`
ya existe como patrón, pero activarlo automáticamente desde `facturas`
violaría la regla de capa propietaria si se hace sin que Contabilidad lo
exponga como un servicio explícito para este trigger). Documentado como
deuda pendiente, no como parte de este hallazgo P0.

## Alineación normativa (verificada contra fuente oficial, no contra documentación del proyecto)

Per §4 del programa de remediación P0, se registra la base normativa que
justifica NO permitir hard-delete de facturas con impacto, y se marca
explícitamente qué queda fuera de lo que este código puede certificar.

| Norma | Artículo/sección | Vigencia | Fuente oficial | Regla implementada | Estado de verificación |
|---|---|---|---|---|---|
| Código de Comercio (Decreto 410 de 1971) | Art. 60 | Vigente, reforzado por Ley 962 de 2005 Art. 28 | [leyes.co/codigo_de_comercio/60.htm](https://leyes.co/codigo_de_comercio/60.htm) | Los libros y papeles contables deben conservarse mínimo **10 años** desde el cierre/último asiento — ninguna eliminación física de un documento con valor contable/probatorio puede ocurrir antes de ese plazo | **Verificado**: `eliminar_factura()` bloquea el `DELETE` físico para todo estado con impacto (todo salvo `BORRADOR`); no hay ningún mecanismo de purga automática por antigüedad en el código actual — el requisito de los 10 años no se ve amenazado porque el sistema simplemente no borra documentos con impacto, sin límite de tiempo |
| Resolución DIAN 000165 de 2023 (Anexo Técnico de Factura Electrónica v1.9, vigente desde mayo 2024) | Íntegra — regula generación/transmisión/validación/expedición/recepción de la factura electrónica | Vigente al momento de esta auditoría, con modificaciones posteriores (ej. Resolución 0008 de 2024) no revisadas exhaustivamente aquí | [dian.gov.co — Resolución 000165](https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000165%20de%2001-11-2023.pdf) | El CUFE, el XML firmado y el documento de origen se preservan íntegros al anular (no se regeneran ni se destruyen) | **PROFESSIONAL_REVIEW_REQUIRED** — este código preserva los artefactos técnicos (CUFE, XML, firma) pero **no certifica** que el proceso completo de generación/transmisión/validación cumpla con el Anexo Técnico vigente en su totalidad, ni con las modificaciones posteriores a la Resolución 000165 no revisadas en esta pasada. Ver también `documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md` y el EXTERNAL_DEPENDENCY ya documentado en `docs/remediation/REM-EXT-01.md` sobre transmisión real DIAN |
| Ley 1314 de 2009 / Decreto 2420 de 2015 (marco normativo contable NIIF Colombia) | General | Vigente | — | La preservación del documento fiscal como soporte del registro contable es consistente con el principio de que todo asiento debe tener soporte documental verificable | **PROFESSIONAL_REVIEW_REQUIRED** — la correspondencia exacta entre este código y las NIIF aplicables (pyme vs. plenas según el tenant) no fue evaluada por un contador; el código no distingue el marco NIIF del tenant |

**No se afirma "cumplimiento legal" por tener este código implementado** —
per §4, esta tabla documenta correspondencia entre norma y comportamiento
de código verificado, no una certificación de cumplimiento integral, que
excede el alcance de una auditoría de código.

## Tests (DB-level, no solo HTTP)

`apps/tenant/facturas/tests/test_remediation_p0_01_delete_guard.py` — 6
tests, cada uno confirma **estado real de BD** además del código HTTP
(`Factura.objects.filter(id=...).exists()` / `refresh_from_db()`), no
solo el status code:

1. `BORRADOR` → `DELETE` → 204 + fila ausente en BD.
2. `ENVIADA` → `DELETE` → 400 + fila **presente** en BD.
3. `ACEPTADA` → `DELETE` → 400 + fila presente.
4. `RECHAZADA` → `DELETE` → 400 + fila presente.
5. `ANULADA` → `DELETE` → 400 + fila presente.
6. `ACEPTADA` → anulación vía `cambiar-estado` → 200 + `factura.estado == ANULADA` tras `refresh_from_db()`.

## Evidencia

Corrida local (previa, re-confirmada sin cambios de código en esta
pasada): 12/12 PASS (6 nuevos + 6 regresión `test_scope_facturas_f11.py`),
1735.23s.

## Antes / Después

| | Antes | Después |
|---|---|---|
| `DELETE` sobre factura `ACEPTADA` | 204, fila eliminada físicamente, asiento contable huérfano | 400, fila intacta |
| `DELETE` sobre factura `BORRADOR` | 204, fila eliminada | 204, fila eliminada (sin cambio — comportamiento correcto ya existía) |
| Manejo de excepción en `destroy()` | Caía a 500 genérico | 400 con mensaje explicando el motivo |

## Riesgos / deuda pendiente

Reversa automática cross-app de `AsientoContable`/`MovimientoInventario`
al anular una factura `ACEPTADA` — no implementada, requiere diseño
dedicado en la capa propietaria de cada dominio (Contabilidad,
Inventario), fuera del alcance mínimo de este hallazgo P0.
