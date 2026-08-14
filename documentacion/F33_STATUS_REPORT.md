# F33 — Shared UI / Design System — STATUS REPORT

**Estado global: IN_PROGRESS** (no COMPLETED -- ver razonamiento al final)

**Actualizacion:** F33.13 (expansion controlada) avanzo de NOT_STARTED a
IN_PROGRESS con 2 batches reales ejecutados y verificados (commits
`a39fa8f`, `22373dd` -- 17 archivos tocados/eliminados en 7 apps (perfil,
compras, gastos, facturas, contabilidad, inventario, core),
ver seccion F33.13 abajo y `F33_APP_EXPANSION_MATRIX.md` para el detalle
completo).

## F33.0 — Inventario Shared UI: PASS

Escaneo real de las 17 apps tenant via agente de exploracion dedicado.
Detalle: `documentacion/F33_SHARED_UI_INVENTORY.md`. Hallazgo principal:
Offcanvas tenia 2 helpers "safe" independientes con adopcion comparable
(~25 vs ~22 archivos); Confirmaciones tenia 3 mecanismos coexistiendo;
Card KPI duplicada 7 veces; Badges de estado con 4+ convenciones para el
mismo semantico en 7 apps.

## F33.1 — Clasificar duplicados: PASS

`SHARED_EXISTING` / `DUPLICATE` / `APP_SPECIFIC` / `CANDIDATE_SHARED` /
`OBSOLETE` aplicado a los 12 hallazgos del inventario (mismo documento,
segunda mitad). Conclusion: Offcanvas y Confirmaciones no necesitaban
componente nuevo, solo consolidar el duplicado sobre el target ya
existente.

## F33.2-9 — Core UI Contract, Table, Offcanvas, Form, Estados,
Notificaciones, Filtros, Cards: PASS

`documentacion/F33_CORE_UI_CONTRACT.md`. De las 10 piezas conceptuales de
la mision original, 6 ya existian (Table=django-tables2, Notificaciones/
Confirm=UIManager, Offcanvas=mostrarOffcanvasSeguro) o no tenian evidencia
de duplicacion que las justificara (Form, ErrorState). Las 4 restantes se
implementaron como primitivas Django server-side minimas (no JS):
`sintel_kpi_card`, `sintel_empty_state` (templatetags), mas 2 partials
(`loading_state.html`, `filter_bar.html`) y un helper de wording
(`tables_i18n.empty_text`). Deliberadamente no se creo
`window.Sintel.Core.UI` como namespace nuevo.

## F33.4 — Offcanvas Contract: PASS (consolidacion real ejecutada)

`Sintel.Core.mostrarOffcanvasSeguro` extendido con `{action:'show'|'hide'}`
(retrocompatible, default `'show'`). `UIManager.handleOffcanvas` -- la
segunda implementacion independiente que el inventario encontro -- ahora
es un alias delgado que delega ahi. Verificado con spec E2E dedicado
(`62-f334-offcanvas-consolidation.spec.js`, show/hide via ambos puntos de
entrada) mas las 3 specs CRUD existentes que ya ejercitan offcanvas real.

## F33.10 — Migracion piloto: PASS

App elegida por evidencia (no preferencia): `empresa`, que tenia el
hallazgo mas completo y accionable del inventario -- 2 templates de modal
confirmados muertos (`modals.html`, `mailinbox_modals.html`) mas su propia
copia del snippet de fallback de offcanvas (`sintelAbrirOffcanvasEmpresa`).

Ejecutado: ambos modals muertos eliminados (una investigacion mas profunda
que la del inventario original confirmo que `mailinbox_modals.html`
tampoco estaba "vivo pero sin migrar" como decia el inventario -- el flujo
real ya usa un offcanvas server-rendered completamente distinto via
`MailInboxConfigViewSet.render_offcanvas`, corrigiendo la clasificacion a
`OBSOLETE`). El snippet local se redujo a un alias de una linea sobre el
helper ya consolidado.

## F33.11 — Validacion piloto: PASS

- `manage.py check`: PASS.
- Governance (`tools.organizational_governance.cli --report`): **FINAL
  STATUS: PASS** (0 WARN, 0 FAIL).
- Playwright, suite completa (29 specs, incluye los 2 nuevos de F33):
  **29/29 PASS.**
- Flujo real verificado con navegador: click en "Nueva Sede" abre el
  offcanvas correctamente via el helper consolidado.

## F33.12 — Impact Analysis: PASS (con hallazgo de cobertura del grafo)

`python -m tools.ekg.impact --path "offcanvas.helper.js" --offline`:

```
Total impacted (excluding target): 4
  assets_core.html -> workspace.html, assets_dashboard.html, assets_landing.html

Tests covering target or any impacted node: NONE FOUND
Aplicaciones tocadas: core, dashboard, landing
```

**Hallazgo, no bloqueante:** el grafo EKG no detecta cobertura de test
para este cambio, pero SI existe (specs 62/63, mas las 3 specs CRUD
existentes que ejercitan offcanvas real) -- el grafo solo indexa
referencias `{% static %}`/imports estaticos, no llamadas JS a funciones
cross-archivo (`mostrarOffcanvasSeguro()` invocado desde ~25 archivos de
features no aparece como arista). Gap de completitud del grafo, documentado
para una fase futura de EKG, no una falta real de cobertura.

## F33.13 — Expansion controlada: **IN_PROGRESS** (2 batches ejecutados con evidencia)

Detalle completo: `documentacion/F33_APP_EXPANSION_MATRIX.md`.

**Batch 1 (Offcanvas #12c/#12d, commit `a39fa8f`):** 11 archivos en 6 apps
(perfil, compras, gastos, facturas, contabilidad x6, inventario)
consolidados sobre `Sintel.Core.mostrarOffcanvasSeguro`, mismo patron ya
probado en el piloto empresa. Verificado con grep repo-wide (0
instanciaciones crudas de `bootstrap.Offcanvas` restantes salvo el propio
helper y 2 excepciones deliberadamente preservadas -- `devengo_editor.js`
por un workaround real de timing de Bootstrap ya documentado en F31.2, y
`facturas_main.js:66` por su contrato de 3 funciones separadas, tambien
documentado en F31.2). `manage.py check` PASS, governance PASS, E2E 29/29.

**Batch 2 (OBSOLETE con evidencia, commit `22373dd`):** 6 archivos
eliminados -- 2 modals de confirmar-eliminar sin consumidores JS
(compras, gastos) + 4 de los 5 prototipos Tailwind huerfanos (el 5o,
`dashboard/index.html`, se dejo intacto por estar alcanzado por trafico
real via el redirect post-login y por estar ya modificado por otra sesion
concurrente). `manage.py check` PASS, governance PASS, E2E 29/29 (una
corrida intermedia con 10 fallos se investigo y se confirmo ambiental --
`AnonRateThrottle` agotado tras 2 suites seguidas, no una regresion; ver
matriz para el detalle completo con evidencia de logs).

**Batch 4 (ModalService, commits `6feccaa`+`68bfacd`):** eliminado
`core/js/helpers/modal-service.js` (0 consumidores confirmados por grep
+ Impact Analysis), su `<script>` tag en `assets_core.html`, y la
entrada obsoleta en `helpers/README.md`. Diferido en el batch 2 por su
carga global (mayor blast radius); ejecutado ahora con su propio ciclo
de verificacion completo. `manage.py check` PASS, governance PASS, E2E
29/29 (corrida completa, contenedor Playwright fresco).

**Batches 5-9 (Confirm nativo->UIManager, Cards KPI, Empty states,
Badges de estado, Filtros) — pendientes**, documentados con evidencia en
la matriz junto con su motivo de diferimiento (escala comparable a F32.7,
o requieren spot-check visual en navegador por app, no solo grep
mecanico). No son omision silenciosa -- son decisiones de alcance
explicitas para no violar la regla "nunca refactor masivo + migracion
masiva en la misma operacion".

## F33.14-19 — Governance rules, Accesibilidad, Responsive, Performance,
Tests, Regresion final: **NOT_STARTED**

Accesibilidad, Responsive y Performance (F33.15-17) requieren su propia
auditoria real (lectura de markup para aria/contraste/teclado, pruebas de
`resize_window` en mobile/tablet, deteccion de listeners/requests
duplicados) -- no se hicieron pasadas superficiales para "marcar la
casilla"; genuinamente no se ejecutaron.

**Esto NO es un bloqueo (`BLOCKED_SAFE`)** -- no hay ningun impedimento
tecnico, de permisos, ni de credenciales. Es una decision de alcance:
la evidencia y la infraestructura para continuar existen completas
(inventario, contrato, helper consolidado y verificado, piloto validado,
2 batches de expansion ya ejecutados), lo que falta es tiempo de ejecucion
adicional del mismo patron ya probado.

## Conclusion

**F33 no se declara COMPLETED.** Los criterios de exito de la mision
("componentes realmente compartidos consolidados" en plural -- mas de un
piloto --, "responsive validado", "accessibility validado") genuinamente
no se cumplen todavia. Lo que SI esta completo y verificado con evidencia
real (no solo documentado): inventario, clasificacion, contrato, la
consolidacion tecnica de Offcanvas (el hallazgo de mayor severidad) ahora
extendida a las 6 apps con violaciones reales (no solo el piloto), 4
primitivas UI nuevas, 6 archivos de codigo muerto eliminados con
evidencia, y el piloto original real ejecutado + validado con navegador +
governance + regresion completa.

**Siguiente paso recomendado (no ejecutado todavia):** batches 3-9 de
F33.13 (documentados en `F33_APP_EXPANSION_MATRIX.md` con su motivo de
diferimiento cada uno), seguidos de F33.15-17 (accesibilidad, responsive,
performance -- auditorias reales, no listas de verificacion superficiales).
