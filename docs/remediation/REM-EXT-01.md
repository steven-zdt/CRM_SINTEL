# REM-EXT-01 — Transmisión real DIAN de facturas de venta

**Estado:** BLOCKED (EXTERNAL_DEPENDENCY)
**Prioridad:** P0/P1 (severidad real), pero bloqueado por dependencia externa
**App involucrada:** `facturas`
**Fecha:** 2026-08-28

## Hallazgo

Confirmado de nuevo en esta sesión (agente de controles internos): ningún
archivo del sistema contiene una llamada HTTP/SOAP real al webservice de
la DIAN. Existe un adaptador SOAP real y bien escrito
(`apps/tenant/core/dian/adapters.py`, `DIANAdapter`, usa `zeep`), pero el
propio módulo se autodeclara explícitamente **"NO VERIFICADO CONTRA EL
AMBIENTE REAL DE LA DIAN"** — WS-Security no implementado, `DIAN_WSDL_URL_
HABILITACION`/`PRODUCCION` sin configurar en ningún entorno, `get_status()`
sin implementar. Por defecto el sistema usa `NullTransportAdapter`
(honesto: no simula una transmisión que no ocurrió).

## Por qué es EXTERNAL_DEPENDENCY, no un bug de código

Cerrar esto requiere, como mínimo:

1. Credenciales/certificado digital real de un tenant en producción
   habilitado ante la DIAN.
2. URL real del WSDL de habilitación/producción de la DIAN para ese
   tenant.
3. Completar la implementación de WS-Security en `DIANAdapter`.
4. Verificar contra el ambiente de habilitación de la DIAN (no
   simulable sin acceso real).

Ninguno de estos 4 insumos existe dentro de este repositorio ni puede
generarse por código. **No se intenta cerrar con código inventado** —
regla explícita del plan (§EXT-01: *"NO intentar cerrar con código
inventado... Mientras no existan: mantener TEST/MOCK. No declarar
DIAN_CONNECTED."*).

## Estado actual (correcto, se mantiene)

- `NullTransportAdapter` como default — honesto, no finge.
- `MockTransportAdapter` disponible solo si
  `settings.FISCAL_ALLOW_MOCK_TRANSPORT=True` explícito Y el request trae
  `?_mock_scenario=` explícito — nunca implícito, nunca en producción por
  accidente.
- CUFE/UBL2.1/XAdES-EPES técnicamente correctos y verificados línea por
  línea (auditoría previa) — la infraestructura está lista para cuando
  existan los insumos externos.

## Acción recomendada

Determinar si hay tenants reales en producción que requieran emisión
electrónica legalmente válida ante la DIAN. Si los hay, este es el ítem de
mayor prioridad real de todo el sistema — pero su cierre depende
enteramente de obtener los insumos externos listados arriba, no de más
trabajo de código dentro de este repositorio.

## Governance

N/A — sin cambio de código, correctamente bloqueado.
