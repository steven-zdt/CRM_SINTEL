# REM-EXT-02 — Transmisión real DSPNE (nómina electrónica)

**Estado:** BLOCKED (EXTERNAL_DEPENDENCY)
**Prioridad:** P0/P1 (severidad real), pero bloqueado por dependencia externa
**App involucrada:** `empleados` (nómina electrónica DIAN/DSPNE)
**Fecha:** 2026-08-28

## Hallazgo

Mismo patrón que REM-EXT-01: el pipeline de generación del documento de
nómina electrónica (XML, firma, numeración) está implementado, pero no
existe transmisión real hacia el servicio DSPNE (Documento Soporte de Pago
de Nómina Electrónica) de la DIAN. No hay credenciales, certificado digital
de producción, ni URL de habilitación/producción configuradas en ningún
entorno de este repositorio.

## Por qué es EXTERNAL_DEPENDENCY, no un bug de código

Igual que EXT-01, cerrar esto requiere insumos que no pueden generarse por
código:

1. Certificado digital real de un tenant habilitado ante la DIAN para
   nómina electrónica.
2. Credenciales/URL real del ambiente de habilitación/producción DSPNE.
3. Verificación contra el ambiente de habilitación de la DIAN (no
   simulable sin acceso real).

## Estado actual (correcto, se mantiene)

- El sistema no finge una transmisión que no ocurrió — igual disciplina de
  honestidad que en `facturas` (adaptador Null por defecto, mock solo
  explícito y no-producción).
- La generación/estructura del documento en sí no se audita como GAP
  aquí — este hallazgo es específicamente sobre el último eslabón
  (transmisión real), no sobre la generación del XML.

## Acción recomendada

Igual que EXT-01: determinar si hay tenants reales en producción que
requieran nómina electrónica legalmente válida ante la DIAN. Si los hay,
el cierre depende enteramente de obtener los insumos externos listados
arriba — no de más trabajo de código dentro de este repositorio. **No se
intenta cerrar con código inventado**, por instrucción explícita del plan.

## Governance

N/A — sin cambio de código, correctamente bloqueado.
