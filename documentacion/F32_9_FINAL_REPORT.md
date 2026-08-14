# F32.9 — Governance Revalidation & Release Gate — FINAL REPORT

**Estado final: COMPLETED**

Detalle paso a paso de cada sub-fase: `documentacion/F32_9_EXECUTION_STATUS.md`.
Este documento resume el resultado para lectura rapida.

## Resumen

F32.9 fue disenada como una fase de *revalidacion*, no de re-migracion: F32
ya habia cerrado el transporte HTTP/CSRF/JWT del frontend tenant (F32.1-8).
El objetivo de F32.9 era comprobar contractualmente ese cierre con un
metodo de busqueda DISTINTO al que F32 uso originalmente -- y encontro que
la auditoria de F32.6/F32.7 tenia un punto ciego real: solo buscaba
`window.http`/`w.http`, nunca `fetch()` nativo con headers manuales.

## Hallazgos reales (2, ambos corregidos)

1. **Regresion directa de F32.7**: `empleados/features/devengo_editor.js`
   referenciaba `w.getCookie('csrftoken')`, global eliminado en F32.7 junto
   con `lib/http.js`. No rompia en produccion (fallback a campo oculto ya
   existente lo cubria) pero era una referencia muerta silenciosa.
   Corregido a `Sintel.Core.Http.csrf()`.
2. **Violacion de contrato `*.api.js` nunca detectada**:
   `contabilidad/reporte/reporte.api.js` reimplementaba `fetch()` + JWT
   manual sin refresh (`Authorization: Bearer ${jwtAuth.getAccessToken()}`)
   -- el mismo patron de bug que F32.1 documento en los 6 archivos
   originales, pero en un 7o archivo que la auditoria original nunca
   encontro porque no usaba `window.http`. Migrado a `Sintel.Core.Http.get()`.

Ambos verificados: `manage.py check` PASS, spec E2E nuevo (`61-f329-*.spec.js`)
PASS, regresion completa (27/27 specs) PASS, governance re-confirmado PASS.

## Hallazgos preexistentes, documentados como DEFERRED (10, no corregidos)

10 archivos adicionales (`compras.utils.js`, `gastos.utils.js`,
`cotizaciones.ui.js` + 3 editors de cotizaciones, `empleado_editor.js`,
`cuentas_pagar_editor.js`, `asiento_cargar_desde_docs.js`,
`contabilidad.ui.js`) duplican CSRF (y en algunos casos JWT) via
`getHeaders()`/`getCookie()` propios + `fetch()` directo. Detalle completo
y razonamiento de la decision: `F32_9_EXECUTION_STATUS.md` §F32.9.4.

**Por que no se corrigieron:** ninguno formo parte del alcance original de
F32 (que solo migro consumidores de `window.http`/`w.http`) -- no son "un
remanente a medio migrar", son deuda arquitectonica preexistente que nunca
estuvo en el radar de F32. Corregirlos ahora seria abrir una nueva ronda de
migracion masiva, que la mision de esta sesion prohibe explicitamente
("NO volver a migrar HTTP/CSRF/JWT"). Ninguno esta roto en produccion (cada
uno tiene su propio CSRF funcional; la autenticacion via cookie de sesion
cubre el resto aunque no envien JWT explicito).

**Riesgo residual:** bajo. Son 10 archivos de un solo modulo cada uno (no
una libreria compartida reusada en decenas de lugares, que era el problema
real que F32 resolvio). Candidato natural para una micro-fase futura
("F32.10" o similar) si se decide cerrar tambien esta deuda.

## UX 401 (hallazgo de F32.8, retriage en F32.9.10)

`reason=401` se pierde en un redirect server-side intermedio
(`/login/` -> shell estatico). Confirmado: no afecta seguridad ni
funcionalidad (el bloqueo de la ruta protegida SI ocurre), solo el mensaje
"tu sesion expiro" no se muestra. **DEFERRED**, no bloqueante.

## Release Gate

| Criterio | Estado |
|---|---|
| `manage.py check` | PASS |
| `makemigrations --check` | PASS |
| `git diff --check` | PASS |
| Governance (`tools.organizational_governance.cli`) | **FINAL STATUS: PASS** (0 WARN, 0 FAIL, re-confirmado post-fixes) |
| `Sintel.Core.Http` = unico transporte | PASS (0 clientes HTTP de proposito general duplicados) |
| API Client Contract (24 `*.api.js`) | PASS (1 violacion real, corregida) |
| JWT Contract | PASS (0 usos de `jwtAuth.token`) |
| CSRF Contract | PASS (deuda documentada, no bloqueante) |
| FormData | PASS |
| Browser Validation (Playwright) | **PASS -- 27/27 specs** |
| Regresion | PASS |

**F32.9 = COMPLETED.**

## Riesgos

- Los 10 archivos DEFERRED (ver arriba) -- bajo riesgo, documentado.
- Perdida de `reason=401` en UX -- cosmetico, documentado.
- Suite pytest global no se corrio en esta fase (0 cambios backend
  relevantes) -- si una fase futura toca backend relacionado, correr
  `make test` en ese momento.

## Deuda pendiente

- 10 archivos DEFERRED (F32.9.4/9.7).
- UX `reason=401` (F32.9.10).
- El shell estatico independiente de `/dashboard/` sigue roto por un bug
  no relacionado (ya flagged, `task_8c73f54c`).
- El flujo "Edit Tenant" de la consola publica sigue bloqueado por un bug
  estructural no relacionado (ya flagged, `task_e7c1fa06`).

## Transicion

Por regla de la mision: `F32.9 = COMPLETED` => se inicia F33
(Shared UI / Design System) automaticamente. Ver
`documentacion/F33_SHARED_UI_INVENTORY.md` en adelante.
