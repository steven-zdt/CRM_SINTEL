# Cierre del Ciclo Fiscal — DIANAdapter (FASE FISCAL-05)

**Fecha:** 2026-08-24. **Estado:** Implementado como skeleton **NO
VERIFICADO** — decisión explícita del usuario tras confirmar que no hay
WSDL real ni credenciales de habilitación disponibles en este entorno
(ver `DIAN_TRANSPORT_AUDIT.md` §6). No confundir con "completo" — ver §3.

---

## 🔴 Advertencia — leer antes de usar en cualquier entorno real

`DIANAdapter` (`apps/tenant/core/dian/adapters.py`) se construyó con
**conocimiento público general** del Anexo Técnico de Factura Electrónica
de la DIAN (servicio `WcfDianCustomerServices`, operación `SendBillSync`,
documento en ZIP+base64) — **no fue validado contra el WSDL real ni
contra el ambiente de habilitación**. La advertencia completa, con la
lista exacta de riesgos conocidos sin resolver, está en el docstring del
módulo — léela antes de tocar este código.

**No usar en producción sin, en orden:** obtener el WSDL real vigente +
credenciales de habilitación → implementar la autenticación WS-Security
real (hoy no implementada, ver §2) → validar `send()` contra el ambiente
de pruebas DIAN real → revisar cada nombre de operación/campo contra el
Anexo Técnico vigente a la fecha.

---

## 1. Decisión que llevó a este resultado

El usuario pidió explícitamente implementar la transmisión real. Se
verificó dos veces antes de escribir código: (1) ¿DIAN directo o
proveedor tecnológico? → **directo**; (2) ¿hay WSDL/credenciales reales
para compartir? → **no**. Con esa confirmación, se construyó el
**skeleton marcado como no verificado** (la opción que ya se había
ofrecido en `NOMINA_DIAN_CONTRATO_COMPARTIDO.md` §2 y no se había tomado
hasta ahora) — código real, estructurado, testeable, pero honesto sobre
lo que falta validar.

---

## 2. Qué SÍ está implementado y probado

- **`DIANAdapter.send(document)`** — implementa
  `ElectronicDocumentTransportPort` (FISCAL-02) completo.
- **Empaquetado del documento**: ZIP en memoria + base64, tal como el
  Anexo Técnico describe para `SendBillSync` — probado
  (`test_empaqueta_el_attached_document_en_zip_base64`).
- **Parseo defensivo de respuesta**: `IsValid=True/False/ausente` →
  `ACEPTADO`/`RECHAZADO`/`ERROR_TRANSMISION` (nunca inventa un estado
  sobre un shape no reconocido) — 3 tests dedicados.
- **Propagación correcta de excepciones de red**: `send()` **no atrapa**
  excepciones durante la llamada SOAP real — se propagan hacia
  `ElectronicInvoiceApplicationService.transmitir()` (FISCAL-04), que las
  trata como transmisión `AMBIGUA` (no inventa un resultado, no
  reintenta a ciegas). Probado explícitamente
  (`test_excepcion_de_red_durante_send_se_propaga_no_se_traga`) — esta es
  la integración crítica con FISCAL-04, verificada.
- **Configuración ausente = error limpio, sin intento de conexión**: sin
  `DIAN_WSDL_URL_HABILITACION`/`DIAN_WSDL_URL_PRODUCCION` configurados,
  `send()` retorna `ERROR_TRANSMISION` inmediatamente, sin tocar la red.
- **Inyección de dependencias para tests** (`_client_factory`): permite
  probar toda la lógica del adaptador sin `zeep` instalado ni un WSDL
  real disponible.

## 2.1. Qué NO está implementado (riesgos reales, no una lista genérica)

- **Autenticación WS-Security**: `_client()` construye un `zeep.Client`
  "desnudo" — el mecanismo real de autenticación de la DIAN
  (UsernameToken vs certificado X.509 en el header SOAP) no está
  confirmado ni implementado. Una llamada real fallaría en autenticación
  tal como está escrito hoy.
- **Endpoint exacto**: `DIAN_WSDL_URL_HABILITACION`/`_PRODUCCION` quedan
  vacíos por defecto — nadie puede asumir una URL sin verificarla contra
  documentación DIAN vigente (las URLs han cambiado en actualizaciones
  normativas pasadas).
- **Nombre/parámetros exactos de la operación**: `SendBillSync(fileName=...,
  contentFile=...)` es la forma documentada públicamente, no confirmada
  contra el WSDL real vigente.

---

## 3. Settings declarados (ninguno con valor real todavía)

Se aprovechó esta fase para declarar explícitamente en `config/
settings.py` **todas** las variables DIAN que el código ya leía
implícitamente vía `getattr(settings, 'X', default)` sin declaración
formal (`DIAN_CERT_P12`, `DIAN_CERT_PASSWORD`, `DIAN_TIP_AMB`,
`DIAN_PROVIDER_ID`, `DIAN_SOFTWARE_ID`, `DIAN_SOFTWARE_PIN`,
`DIAN_CL_TECN`, `DIAN_AUTHORIZATION_ID`, `DIAN_CUSTOMIZATION_ID`,
`DIAN_PROFILE_ID`) más las 2 nuevas para el adaptador
(`DIAN_WSDL_URL_HABILITACION`, `DIAN_WSDL_URL_PRODUCCION`) — antes eran
invisibles para cualquiera que buscara "qué configurar" sin leer el
código fuente de cada servicio. Se documentó también, con nota explícita,
que `DIAN_API_KEY`/`DIAN_API_URL_TEST`/`_PRODUCTION`/`DIAN_AMBIENTE` (ya
existentes) solo las consume el `DIANService` muerto (FISCAL-01 §2) — se
dejaron sin tocar por compatibilidad, no se usan en el pipeline real.

---

## 4. Dependencias nuevas

`requirements.txt`: `zeep>=4.2,<5.0` (cliente SOAP, importado
perezosamente solo cuando `send()` se invoca sin `_client_factory`
inyectado — no rompe nada si no está instalado, ver `test_sin_wsdl_
configurado...`) y `cryptography>=42.0,<44.0` (hallazgo adicional:
`XadesSignerService` ya la importaba desde antes de esta sesión pero
nunca estuvo declarada en `requirements.txt` — habría fallado con
`ImportError` si alguna vez se hubiera configurado un certificado real).

---

## 5. Verificación realizada (y sus límites)

- `manage.py check`: 0 issues.
- Suite nueva, pura (sin DB, sin red, sin `zeep` real):
  `apps/tenant/core/tests/test_dian_adapter.py` — 7 tests. **12/12 PASS
  en 0.43s** junto con la suite de FISCAL-02.
- **Lo que esta suite NO prueba** (no puede probarlo, honestamente): que
  la llamada SOAP real funcione contra la DIAN, que la autenticación sea
  correcta, que el shape de la respuesta real coincida con lo asumido en
  `_parsear_respuesta()`. Eso requiere el ambiente de habilitación real
  — bloqueado, ver §1.

---

## 6. Estado formal

**`FISCAL-05 = SKELETON_NO_VERIFICADO`** (estado distinto de
`COMPLETED` deliberadamente — no declarar como cerrado algo que no se
puede cerrar sin acceso real a la DIAN). La lógica interna del adaptador
(empaquetado, parseo, propagación de errores, integración con FISCAL-04)
está completa y probada. La conexión real a la DIAN — lo único que
importa para que esto sirva en producción — sigue bloqueada por falta de
WSDL/credenciales verificables, documentado explícitamente, no oculto
detrás de un "PASS" engañoso.
