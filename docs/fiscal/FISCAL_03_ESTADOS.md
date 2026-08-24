# Cierre del Ciclo Fiscal — Estados Reales (FASE FISCAL-03)

**Fecha:** 2026-08-24. **Estado:** Implementado con alcance acotado por
decisión explícita del usuario (ver §2). Complementa
`DIAN_TRANSPORT_AUDIT.md` (FISCAL-01) y `FISCAL_02_CONTRATO_TRANSPORTE.md`
(FISCAL-02).

```
BORRADOR → ENVIADA → { ACEPTADA | RECHAZADA | ERROR_TRANSMISION }
                              ↕ (RECHAZADA/ERROR_TRANSMISION → ENVIADA, reintento)
        ANULADA (excepción, desde cualquier estado no terminal)
```

---

## 1. Por qué el diagrama del plan no se implementó literalmente

El plan pide `BORRADOR → GENERADA → FIRMADA → ENVIADA → ACEPTADA`. La
arquitectura real (confirmada en FISCAL-01) construye y firma el XML
**síncronamente, antes de que la fila `Factura` exista** — no hay ningún
punto del código donde una `Factura` persistida esté "generada pero no
firmada": para cuando `crear_factura_desde_venta()`/`guardar_desde_dto()`
la crean, el XML ya fue construido y ya pasó por `XadesSignerService`.
Agregar los estados `GENERADA`/`FIRMADA` al modelo hoy crearía dos
estados que ningún flujo real dejaría nunca fijos en la base — exactamente
el tipo de infraestructura especulativa que esta sesión ha evitado
consistentemente. `BORRADOR` ya cubre correctamente "existe pero no se ha
intentado transmitir".

**Sí se agregó lo que faltaba con evidencia real:** `ERROR_TRANSMISION`,
justificado porque `ElectronicDocumentTransportPort.send()` (FISCAL-02)
ya puede devolver ese `status` hoy (`NullTransportAdapter`), y no había
ningún estado de `Factura` donde aterrizara — sin este estado, un intento
de transmisión que falla antes de obtener respuesta de la DIAN quedaría
indistinguible de un `RECHAZADA` real (que implica que la DIAN sí
respondió) o de un `ENVIADA` colgado indefinidamente.

---

## 2. Decisión de alcance (usuario)

Se preguntó explícitamente si `FacturaViewSet.cambiar_estado()` (el
endpoint genérico, hoy sin ninguna restricción — hallazgo de FISCAL-01
§4) debía **bloquear** el ajuste manual de `ACEPTADA`/`RECHAZADA`/
`ERROR_TRANSMISION`, reservándolos para un futuro pipeline de transmisión
real. **Decisión: no restringir.** Razón operativa real: mientras no
existe transporte real (Escenario C), el mecanismo legítimo para reflejar
el estado DIAN verdadero es que un administrador lo sincronice a mano
consultando el portal de la DIAN — bloquear el endpoint eliminaría esa
capacidad sin ofrecer ningún reemplazo funcional todavía.

**Consecuencia de diseño:** la matriz de transiciones (§3) se construyó
como una **fuente de verdad documentada y lista para usarse**, no como un
guardia activo sobre el endpoint existente. `cambiar_estado()` sigue
exactamente como estaba.

---

## 3. `FacturaBusinessService.TRANSICIONES_VALIDAS`

(`apps/tenant/facturas/services/business_service.py`, junto a
`validar_transicion_automatica()`) — mismo patrón ya usado en
`PeriodoNominaBusinessService.TRANSICIONES_VALIDAS` (Nómina, misma
sesión):

```python
TRANSICIONES_VALIDAS = {
    'BORRADOR':          {'ENVIADA', 'ANULADA'},
    'ENVIADA':           {'ACEPTADA', 'RECHAZADA', 'ERROR_TRANSMISION', 'ANULADA'},
    'ACEPTADA':          {'ANULADA'},
    'RECHAZADA':         {'ENVIADA', 'ANULADA'},          # reintento de envio
    'ERROR_TRANSMISION': {'ENVIADA', 'ANULADA'},           # reintento de envio
    'ANULADA':           set(),                            # terminal
}
```

`validar_transicion_automatica(factura, estado_destino)` lanza
`DRFValidationError` con un mensaje explícito (`"No se puede pasar de X a
Y. Transiciones válidas desde X: [...]"`) si la transición no está en el
mapa; no hace nada si es válida. **No se invoca desde ningún punto de
código todavía** — queda lista para que `FISCAL-05` (procesamiento de la
respuesta de transmisión real) la use cuando el `TransmissionResult` de
`ElectronicDocumentTransportPort.send()` (FISCAL-02) determine el
`estado_destino` real.

---

## 4. Verificación

- `manage.py check`: 0 issues.
- Migración `0034_alter_factura_estado.py` (aditiva, `AlterField` sobre
  `choices`, sin tocar datos existentes) aplicada a los 3 schemas tenant
  reales (`home`, `shelltest1`, `qaisotest`, vía `migrate_schemas`).
- Suite nueva, pura (sin DB): `apps/tenant/facturas/tests/
  test_fiscal_03_estados.py` — 7 tests cubriendo cada transición válida
  del mapa, el rechazo de un salto directo `BORRADOR→ACEPTADA`, que
  `ANULADA` es terminal, que `RECHAZADA`/`ERROR_TRANSMISION` permiten
  reintentar, y que el mensaje de error es legible. **7/7 PASS en 3.10s**.

---

## 5. Estado formal

**`FISCAL-03 = COMPLETED_WITH_DEFERRED`.** Estado nuevo (`ERROR_TRANSMISION`)
y matriz de transiciones reales completos y verificados. La aplicación
activa de la matriz sobre `cambiar_estado()` queda diferida por decisión
explícita del usuario (no un olvido) — la matriz ya existe y está lista
para conectarse en `FISCAL-05` sin rediseño adicional.
