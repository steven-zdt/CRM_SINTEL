# Cierre del Ciclo Fiscal — Transporte Simulado + Persistencia (FASE FISCAL-02A)

**Fecha:** 2026-08-24. **Estado:** Implementado y verificado. Corrige el
rumbo de FISCAL-05 (`DIANAdapter` real, `SKELETON_NO_VERIFICADO`) por
decisión explícita del usuario: **no intentar integración real con la
DIAN todavía** — dejar la arquitectura completamente preparada y probada
en modo simulado, sin inventar WSDL/endpoints/credenciales.

```
🛒 Venta → 🧾 Factura → 📄 XML UBL → 🔐 CUFE → ✍️ Firma
        ↓
🧪 TRANSPORT TEST (MockTransportAdapter, cero conexión externa)
        ↓
📥 Respuesta simulada
        ↓
   🟢 ACEPTADO          🔴 RECHAZADO         🟡 AMBIGUO (timeout/error)
   environment=TEST     environment=TEST     environment=TEST
```

---

## 1. Qué cambia respecto a FISCAL-05

`DIANAdapter` (FISCAL-05) sigue existiendo, sin tocar, marcado
`SKELETON_NO_VERIFICADO` — no se elimina ni se completa. Esta fase agrega
un **segundo adaptador**, `MockTransportAdapter`, para que el desarrollo y
las pruebas del ERP no dependan de resolver primero el bloqueador de
credenciales DIAN reales:

```
                    FACTURAS
                        │
                        ▼
          ElectronicDocumentTransportPort
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
   MockTransportAdapter        DIANAdapter
   (FISCAL-02A, usar HOY)      (FISCAL-05, NO VERIFICADO)
```

Cuando existan credenciales reales, el cambio es **reemplazar el
adaptador inyectado**, no tocar `Factura`/`Venta`/`Inventario`/`Bancos`/
`Contabilidad`/UI/estados de negocio — exactamente el objetivo que el
usuario planteó.

---

## 2. `MockTransportAdapter` (`apps/tenant/core/dian/transport.py`)

Cinco escenarios controlables (`scenario` del constructor, o override por
documento vía `scenario_por_tracking_key={cufe: escenario}` para
configurar facturas distintas en un mismo test):

| Escenario | Comportamiento |
|---|---|
| `TEST_ACCEPTED` | `send()` retorna `ACEPTADO` (roundtrip exitoso) |
| `TEST_REJECTED` | `send()` retorna `RECHAZADO` (roundtrip exitoso, rechazo de negocio) |
| `TEST_PENDING` | `send()` retorna `PENDIENTE` — no mapea a un estado terminal, la Factura queda en `ENVIADA` |
| `TEST_TIMEOUT` | `send()` **lanza** `TimeoutError` — mismo tratamiento que un timeout real (FISCAL-04) |
| `TEST_CONNECTION_ERROR` | `send()` **lanza** `ConnectionError` — mismo tratamiento |

`get_status(tracking_key)` recupera el último resultado que `send()`
registró para ese `tracking_key` (historial en memoria, por instancia del
adaptador) — soporta `reconciliar()` (§4). `intentos(tracking_key)` cuenta
cuántas veces se llamó `send()` para ese documento — útil para verificar
idempotencia/reintentos en tests, sin inspeccionar la base de datos.

---

## 3. `TransmisionFactura` — historial completo, no solo el último estado

Nuevo modelo (`apps/tenant/facturas/models.py`, migración
`0035_transmisionfactura.py`) — una fila por cada llamada real a
`transport.send()`, complementando (no reemplazando) `Factura.estado`
(que sigue siendo el ancla de idempotencia real, FISCAL-03/04):

```python
transmission_id   # UUID propio, independiente del track_id del proveedor
environment       # TEST | PRODUCTION -- separado del status, no sufijos "_TEST"
status            # PENDIENTE | ACEPTADO | RECHAZADO | ERROR_TRANSMISION | AMBIGUO
submitted_at      # auto_now_add -- se fija en fase 1, antes de send()
responded_at      # se fija en fase 2, al recibir un resultado (o excepcion)
track_id          # del proveedor, si trae uno
response_code / response_message / raw_response
```

**Decisión de diseño explícita del usuario, aplicada literalmente:**
`environment` como campo separado, no estados con sufijo `_TEST` — el
enum de `Factura.Estado` (FISCAL-03) no se tocó, sigue siendo
`BORRADOR/ENVIADA/ACEPTADA/RECHAZADA/ERROR_TRANSMISION/ANULADA`, ya
suficientemente granular. `TransmisionFactura.Status` sí necesitó un
valor nuevo (`AMBIGUO`) que `Factura.Estado` no tiene ni necesita — un
`AMBIGUO` nunca es el estado de la Factura en sí (que se queda en
`ENVIADA`), es el resultado del INTENTO.

No se agregaron `GENERADA`/`FIRMADA`/`PENDIENTE_ENVIO` como estados
persistidos (ni en `Factura` ni en `TransmisionFactura`) — se reafirma la
razón ya documentada en `FISCAL_03_ESTADOS.md` §1: la arquitectura real
construye y firma el XML síncronamente, antes de que exista la fila
`Factura` — ningún flujo real dejaría esos estados fijos en la base.

---

## 4. `reconciliar()` — la pieza que faltaba en FISCAL-04

FISCAL-04 dejó explícitamente fuera de alcance la reconciliación de un
`AMBIGUO` porque `ElectronicDocumentTransportPort` no tenía `get_status()`
y no había ningún adaptador contra el cual probarla. Ahora existe:

`ElectronicInvoiceApplicationService.reconciliar(factura, transport)` —
consulta `transport.get_status(factura.cufe)`, y si trae una respuesta
definitiva, aplica la transición de `Factura.estado` (vía la misma
`validar_transicion_automatica()` de FISCAL-03) y actualiza el registro
`TransmisionFactura` existente (no crea uno nuevo — es la resolución del
mismo intento, no un reintento). Si nunca hubo un intento previo, lanza
`ValueError` explícito.

`DIANAdapter.get_status()` (FISCAL-05) también se implementó, pero
honestamente: retorna `"not_supported"` porque la operación real de
consulta DIAN no está confirmada — no se inventó una segunda llamada SOAP
sin WSDL real contra el cual validarla.

---

## 5. Idempotencia y reintentos, probados de punta a punta

- **Reintento inmediato bloqueado**: sigue siendo `TRANSICIONES_VALIDAS`
  (FISCAL-03) quien lo impide — sin cambios, `TransmisionFactura` no es
  un segundo guardián, solo el registro de auditoría.
- **Reintento legítimo genera una fila nueva, no sobreescribe**: probado
  explícitamente — dos llamadas a `transmitir()` (una `RECHAZADA`, luego
  un reintento exitoso) producen **2** filas `TransmisionFactura`, cada
  una con su propio `submitted_at`/`status` — la historia completa queda
  trazable.
- **`intentos()` del mock** permite verificar en tests que `send()` se
  llamó exactamente el número de veces esperado, sin depender de
  inspeccionar la base de datos.

---

## 6. Verificación

- `manage.py check`: 0 issues.
- Migración `0035_transmisionfactura.py` aplicada a los 3 schemas tenant
  reales.
- Suites nuevas, todas verdes:
  - `apps/tenant/core/tests/test_dian_mock_transport.py` (puro, sin DB) —
    9 tests: los 5 escenarios, override por documento, `get_status()`
    (con y sin historial previo), conteo de intentos.
  - `apps/tenant/facturas/tests/test_fiscal_02a_persistencia_transmision.py`
    (con DB) — 6 tests: creación/cierre de `TransmisionFactura` en los 3
    desenlaces (ACEPTADO/RECHAZADO/AMBIGUO), `reconciliar()` exitoso,
    `reconciliar()` sin intento previo (`ValueError`), historial de
    reintentos (2 filas, no 1 sobreescrita).
  - Regresión: `test_fiscal_04_idempotencia_transmision.py` (9 tests,
    FISCAL-04) sigue en verde — el cambio de `transmitir()` es aditivo
    (agrega la clave `"transmision"` al dict de retorno; nada existente
    se modificó).

---

## 7. Qué queda explícitamente fuera de alcance (no un olvido)

Del checklist original del usuario para "FISCAL-02B — pruebas
funcionales completas de escenarios simulados": los 8 escenarios pedidos
(aceptada, rechazada, pendiente, timeout, error, reintento, idempotencia,
consulta de estado) **ya quedaron cubiertos en esta misma fase** — no fue
necesaria una fase separada. Lo que sigue realmente pendiente:

- **`RealDIANAdapter` / completar `DIANAdapter`** — bloqueado por WSDL/
  credenciales reales, sin cambios respecto a FISCAL-05.
- **FISCAL-03 (extraer transporte común para Nómina)** — el transporte ya
  vive en `core.dian` (terreno neutral desde NÓMINA-03/FISCAL-02), listo
  para que `empleados` lo reutilice cuando construya su propio pipeline
  DSPNE — no requiere trabajo adicional de extracción, ya está en el
  lugar correcto.
- **UI de estado fiscal** (FISCAL-06 original) — sin tocar.

---

## 8. Estado formal

**`FISCAL-02A = COMPLETED`.** Arquitectura de transporte completamente
preparada y probada en modo simulado, sin ninguna conexión externa, sin
inventar WSDL/endpoints/credenciales. Migración a `DIANAdapter` real
queda como el único paso pendiente, y por diseño no requiere tocar nada
más que la inyección del adaptador en
`ElectronicInvoiceApplicationService`.
