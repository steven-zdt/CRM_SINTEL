# Cierre del Ciclo Fiscal — Validación Funcional vía API (FASE FISCAL-02B)

**Fecha:** 2026-08-24. **Estado:** Implementado y verificado. Expone
`ElectronicInvoiceApplicationService` como endpoints HTTP reales, con una
guarda de seguridad explícita para que `MockTransportAdapter` **nunca**
sea alcanzable desde un endpoint de producción sin una activación
consciente y reversible.

---

## 🔴 La trampa que esta fase evita

"Validación funcional" podía significar exponer los endpoints con
`MockTransportAdapter` como comportamiento por defecto — eso habría sido
peligroso: un usuario real llamando `POST /facturas/{uuid}/transmitir/`
recibiría `"tu factura fue ACEPTADA por la DIAN"` cuando **nada se
transmitió**, un riesgo real de inducir a error sobre el cumplimiento
fiscal de su empresa. Se preguntó explícitamente al usuario y se confirmó
la opción segura antes de escribir código.

---

## 1. Endpoints nuevos

`apps/tenant/facturas/api/viewsets.py`, `FacturaViewSet`:

- **`POST /api/v1/facturas/{uuid}/transmitir/`** — invoca
  `ElectronicInvoiceApplicationService.transmitir()`.
- **`POST /api/v1/facturas/{uuid}/reconciliar/`** — invoca
  `ElectronicInvoiceApplicationService.reconciliar()`.

Ambos retornan `{"factura": FacturaDetailSerializer, "resultado": {success,
status, track_id, response_code, response_message, errors},
"transmision": {transmission_id, environment, status, submitted_at,
responded_at} | null}` — la respuesta siempre expone `environment`
explícitamente, así que quien consuma la API nunca puede confundir un
resultado `TEST` con uno `PRODUCTION`.

DSV (empresa activa) y permisos (`IsTenantMember`, `IsTenantAdminOrReadOnly`
heredados de `FacturaViewSet`) aplican igual que en el resto de acciones
de este ViewSet. Idempotencia (400) y "sin transmisión previa" (404)
propagan directo desde el service, sin lógica duplicada en la vista.

---

## 2. La guarda de seguridad — `FISCAL_ALLOW_MOCK_TRANSPORT`

`FacturaViewSet._resolver_transporte_dian(request)`:

```python
mock_scenario = request.query_params.get("_mock_scenario")
if mock_scenario and getattr(settings, "FISCAL_ALLOW_MOCK_TRANSPORT", False):
    return MockTransportAdapter(scenario=mock_scenario)
return None  # -> el service usa NullTransportAdapter por defecto
```

**Dos condiciones, ambas explícitas, ninguna implícita:**
1. `settings.FISCAL_ALLOW_MOCK_TRANSPORT` — nueva variable de entorno,
   **`False` por defecto** (`config/settings.py`). Debe quedar `False` en
   cualquier despliegue de producción; solo se activa deliberadamente en
   desarrollo/QA.
2. `?_mock_scenario=` en el request — sin este parámetro, aunque el flag
   esté activo, se usa `NullTransportAdapter` igual.

**Probado explícitamente que la guarda no tiene fugas**: con el flag
apagado, pedir `?_mock_scenario=TEST_ACCEPTED` es **ignorado** — la
Factura termina en `ERROR_TRANSMISION` real (honesto), nunca en
`ACEPTADA` fingida (`test_mock_scenario_es_ignorado_sin_el_flag_de_settings`).

---

## 3. Limitación real documentada: `MockTransportAdapter` no tiene memoria entre requests

Cada llamada HTTP construye una instancia nueva de `MockTransportAdapter`
(vía `_resolver_transporte_dian()`) — su historial en memoria (`_historial`,
usado por `get_status()`) **no sobrevive entre dos requests separadas**.
Esto significa que `reconciliar()` vía API, después de un `transmitir()`
vía API con resultado `PENDING`, no puede "recordar" ese intento — el
`MockTransportAdapter` de la segunda llamada responde `"not_found"`
honestamente, en vez de inventar una respuesta.

**Se documenta como limitación real, no se resuelve con estado global**:
darle memoria compartida entre requests a un objeto de simulación (cache,
singleton a nivel de proceso) introduciría contaminación entre tests y
condiciones de carrera para un beneficio puramente cosmético del mock —
un adaptador real (`DIANAdapter`) no tiene este problema porque consulta
un sistema externo con memoria propia, no un objeto en el proceso Python.
`reconciliar()` con memoria real de un intento previo ya está probado
correctamente a nivel de servicio, con la misma instancia de adaptador,
en `FISCAL_02A_MOCK_TRANSPORT.md` §5 — esa es la prueba que importa.

---

## 4. Verificación

- `manage.py check`: 0 issues.
- Suite nueva: `apps/tenant/facturas/tests/test_fiscal_02b_api_transmision.py`
  — 7 tests: guarda de seguridad (sin flag → siempre honesto, mock
  ignorado explícitamente), camino feliz `ACEPTADO`/`RECHAZADO` vía HTTP
  real con el flag activo, idempotencia vía HTTP (segundo intento
  inmediato → 400), `reconciliar()` sin intento previo (404) y con
  adaptador sin memoria (limitación documentada en §3, no un fallo).
- Regresión: `test_api_facturas.py` (suite existente de `FacturaViewSet`)
  sigue en verde — los 2 endpoints nuevos no tocan ningún comportamiento
  existente.

---

## 5. Estado formal

**`FISCAL-02B = COMPLETED`.** Los 8 escenarios de validación funcional
quedan probados tanto a nivel de servicio (FISCAL-02A) como a nivel de
API real (esta fase), con la guarda de seguridad crítica verificada
explícitamente. Ningún endpoint puede fingir una transmisión DIAN real en
producción — la variable de entorno queda en `False` por defecto y debe
activarse a propósito.
