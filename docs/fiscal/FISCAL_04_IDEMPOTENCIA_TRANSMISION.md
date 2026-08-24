# Cierre del Ciclo Fiscal — Idempotencia de Transmisión (FASE FISCAL-04)

**Fecha:** 2026-08-24. **Estado:** Implementado. Completa el orquestador
`ElectronicInvoiceApplicationService` que el plan nombró en su diagrama
de arquitectura (FISCAL-01), conectando FISCAL-02 (contrato) + FISCAL-03
(estados) en el único punto real donde la idempotencia importa: el
momento de intentar transmitir.

```
Factura #123 (BORRADOR)
        ↓ fase 1 (transaccion propia, se confirma YA)
   ENVIADA
        ↓ transport.send() -- fuera de cualquier transaccion
   ¿timeout?  → sí → ENVIADA queda firme, resultado "ENVIADA_AMBIGUA",
                      reintento inmediato BLOQUEADO por FISCAL-03
   ¿respuesta real? → sí → fase 2 (transaccion propia):
                            ACEPTADA | RECHAZADA | ERROR_TRANSMISION
```

---

## 1. La idempotencia real no es un mecanismo nuevo — es FISCAL-03 aplicado

El plan pide protección contra "doble clic, retry, timeout, reenvío". No
se construyó ningún `Idempotency-Key`, tabla nueva, ni campo de
deduplicación — **el propio `Factura.estado`, ya persistido, es el ancla**,
exactamente como en `COMERCIAL-04` (`Venta.uuid` como ancla, no un header
nuevo). `TRANSICIONES_VALIDAS` (FISCAL-03) ya define que `'ENVIADA'` no
tiene a `'ENVIADA'` entre sus destinos válidos — así que un segundo intento
de `transmitir()` sobre una `Factura` que ya está `ENVIADA` es rechazado
por `validar_transicion_automatica()` sin ningún código adicional
dedicado a "detectar duplicados". Esta fase solo tenía que **conectar**
esa validación al único punto real de envío, que no existía todavía.

---

## 2. El problema del timeout — resuelto con 2 transacciones, no 1

`ElectronicInvoiceApplicationService.transmitir()`
(`apps/tenant/facturas/services/electronic_invoice_service.py`) usa
**dos bloques `transaction.atomic()` separados**, no uno solo:

- **Fase 1** (idempotencia + marcar `ENVIADA`): se confirma en su propia
  transacción, **antes** de llamar `transport.send()`.
- **Fase 2** (aplicar el resultado real): otra transacción propia,
  **después** de que `transport.send()` retorne.

**Por qué no un solo `@transaction.atomic` envolviendo todo:** si
`transport.send()` lanza una excepción (timeout, conexión caída — el
escenario exacto que el plan describe: *"Factura #123 → enviada → timeout
→ ¿se envió realmente?"*) dentro de una única transacción, Django
revertiría **también** la escritura de `ENVIADA`, dejando la `Factura` de
vuelta en `BORRADOR` — como si nunca se hubiera intentado nada. Eso es
peligroso: si la DIAN sí recibió el documento antes de que la conexión se
cortara, un reintento posterior (viendo `BORRADOR`) lo reenviaría,
generando una segunda transmisión real de un documento fiscal. Con las 2
fases separadas, un timeout dentro de `transport.send()` deja la `Factura`
firme en `ENVIADA` — y `FISCAL-03` bloquea automáticamente cualquier
reintento hasta que alguien reconcilie el estado real.

**No se inventa un resultado.** Ante una excepción de `transport.send()`,
el método retorna `status="ENVIADA_AMBIGUA"` (no `ERROR_TRANSMISION`,
deliberadamente) — `ERROR_TRANSMISION` significa "sabemos que falló antes
de llegar a la DIAN"; una excepción de red no nos da esa certeza. Ningún
estado nuevo se agregó al modelo para esto — `ENVIADA_AMBIGUA` es solo el
`status` que retorna el `TransmissionResult` de esta llamada, la
`Factura` en sí queda simplemente en `ENVIADA` (estado real ya existente).

---

## 3. Qué queda explícitamente fuera de alcance (no un olvido)

- **Reconciliación real de un `ENVIADA` ambiguo** — requeriría una
  operación de "consultar estado" contra el proveedor real (`GetStatus`
  o equivalente), que `ElectronicDocumentTransportPort` no define (solo
  `send()`, según FISCAL-02). Agregarla ahora, sin un adaptador real
  contra el cual verificarla, sería infraestructura especulativa — queda
  documentada como extensión natural del puerto para cuando exista un
  adaptador real.
- **Persistencia estructurada de `track_id`/fecha de envío** — el plan
  lo asigna explícitamente a FISCAL-05 ("Respuesta"). Esta fase sí
  persiste `raw_response` en `FacturaAnexos.application_response_xml`
  (campo ya existente, reutilizado, sin migración nueva) cuando el
  resultado trae contenido, pero no agrega columnas nuevas para
  `track_id`/`response_code` — eso es FISCAL-05.
- **UI** — FISCAL-06, sin tocar en esta fase.

---

## 4. Verificación

- `manage.py check`: 0 issues.
- Suite nueva: `apps/tenant/facturas/tests/
  test_fiscal_04_idempotencia_transmision.py` — 9 tests: doble-envío
  bloqueado desde `ENVIADA`/`ACEPTADA`, excepción de transporte preserva
  `ENVIADA` (no revierte a `BORRADOR`), reintento inmediato tras timeout
  bloqueado, camino feliz con `NullTransportAdapter` (termina en
  `ERROR_TRANSMISION`, honesto), reintento legítimo desde
  `ERROR_TRANSMISION` permitido, rechazo de facturas de naturaleza
  `COMPRA`, rechazo sin XML firmado sin corromper el estado, y
  persistencia condicional de `raw_response`.

---

## 5. Estado formal

**`FISCAL-04 = COMPLETED_WITH_DEFERRED`.** La protección de idempotencia
pedida por el plan está implementada y verificada en el único punto real
donde aplica. Reconciliación activa de estados ambiguos y persistencia
estructurada de metadatos de respuesta quedan para FISCAL-05, con la
razón documentada, no como alcance perdido.
