# UI_UX_RELEASE_GATE_FINAL — SINTEL ERP

**Fecha:** 2026-09-17. **Rama:** `feat/onboarding-cookie`. **Documento de cierre de:**
`UI_UX_MASTER_MISSION_V2_59_FASES.md` (Fase 58, 59 fases totales).

Este es el reporte final de 28 secciones exigido por la Fase 58. No reemplaza la evidencia detallada
de `UI_UX_MASTER_MISSION_V2_59_FASES.md` (bitácora fase por fase), `UI_UX_COVERAGE_MATRIX.md` (43
filas de cobertura Capa 2) ni `UI_UX_FINDINGS.md` (10 hallazgos con reproducción y fix) — los
consolida y cita. Ningún dato aquí es nuevo; todo proviene de esos tres documentos, verificados en
sesiones anteriores con evidencia real (tests que pasan, código leído, causas raíz confirmadas).

**Veredicto de una línea:** cobertura de backend/API (Capa 2) sólida y verificada en las 15 apps de
negocio tenant, con 7 bugs reales corregidos; cobertura de UI real en navegador (Capa 1) **BLOCKED**
por una limitación estructural de la herramienta, no de la aplicación. **La misión NO está
`PRODUCTION READY`** — ver Sección 28.

---

## 1. Executive Summary

SINTEL ERP tiene 15 apps de negocio tenant (Clientes, Proveedores, Compras, Ventas, Cotizaciones,
Inventario, Facturas, Gastos, Bancos, Contabilidad, Empleados, Proyectos, Empresa, Perfil, Dashboard).
Esta misión auditó y endureció la Capa 2 (API real vía `pytest`/`APIClient`) de las 15, corrigiendo 7
bugs reales de manejo de errores (500 donde debía haber 400/404, fabricación silenciosa de datos
fiscales, 12 errores convertidos en `$0` silencioso sin log) y documentando 6 hallazgos adicionales
diferidos por decisión explícita del usuario o por estar fuera de alcance quirúrgico. **500+ tests**
corrieron con evidencia fresca de esta sesión, 0 fallos sin explicar.

La Capa 1 (navegador real: login, clic, DOM, responsive, consola, network en vivo) permanece
**bloqueada** por una limitación confirmada de la herramienta de automatización de navegador
(sandbox anti-SSRF bloquea `fetch()`/XHR hacia loopback/IPs privadas — ver Sección 6), no por un
defecto de la aplicación. Esto bloquea en cascada 9 de las 59 fases (12, 14, 15 parcial, 17, 30, 34,
35, 54, 56) y deja 15 fases más en `NOT_STARTED` por no haberse podido iniciar sin esa capacidad o por
estar fuera del alcance de las sesiones ejecutadas.

**Resultado consolidado:** 13 fases `PASS`, 20 `PASS_WITH_LIMITATIONS`, 2 `PARTIAL`, 9 `BLOCKED`, 15
`NOT_STARTED`, 0 `FAIL` (de 59).

## 2. Alcance y Metodología

Alcance ejecutado: auditoría y endurecimiento de Capa 2 de las 15 apps de negocio tenant, en 3 batches
(Piloto → Compras, Batch 2 → Inventario/Facturas/Gastos/Bancos, Batch 3 → Contabilidad/Empleados/
Proyectos/Empresa/Perfil/Dashboard) más un cierre final (Ventas/Cotizaciones), seguido de Cross-App
UX (Fase 44), flujos de negocio E2E (Fase 45), matriz de cobertura (Fase 51), reporte de hallazgos
(Fase 52) y regression gate (Fase 53).

Metodología: `Step → verify` (Karpathy Principles, `CLAUDE.md`) — cada hallazgo se verificó leyendo el
código real antes de citarlo, cada fix tiene un test que pasa como evidencia, cada corrida de test
citada es fresca de la sesión que la reporta (Regla Inmutable 18 — no reciclar resultados históricos).
`apps/public/` no se tocó (bloqueado por RFC). No se usó `make test` global — Testing Progresivo por
Alcance (`CLAUDE.md` §24.0) — se reservó para releases/cambios transversales.

**No ejecutado en esta metodología:** interacción real en navegador (Capa 1). Ver Sección 6.

## 3. Fuentes de Verdad

- `AGENTS.md` (raíz) — arquitectura y reglas canónicas.
- `CLAUDE.md` — referencia operativa Claude Code, reglas no-negociables (tabla de quick-lookup).
- `docs/ADR-001-retention-pull-model.md`, `docs/ADR-002-public-schema-api-dual-registration.md`.
- `UI_UX_MASTER_MISSION_V2_59_FASES.md` — bitácora de las 59 fases, fuente primaria de este reporte.
- `UI_UX_COVERAGE_MATRIX.md` — 43 filas de cobertura Capa 2 por entidad/app (Fase 51).
- `UI_UX_FINDINGS.md` — 10 hallazgos con reproducción, causa raíz y fix o razón de diferimiento (Fase 52).
- `UX_MASTER_BASELINE.md` (misión UX previa, 2026-08-21) — inventario de componentes compartidos ya
  existentes, citado en Fases 9 y 44 en vez de re-derivarlo.
- `.agent/` de cada app tenant — auditorías previas por app (no todas re-verificadas esta sesión).

## 4. Stack Técnico Preservado

Confirmado sin cambios: Django + django-tenants (multi-tenant por schema PostgreSQL), Service Layer
(`ViewSet → ServiceMixin → business_service → crud_service`), Dual-Auth (JWT + Session), UUID lookup
vía `BaseTenantViewSet`, Double Semantic Verification en `business_service.py`, Pull Model de
contabilidad (`RetencionesService`), frontend sin build step (Bootstrap 5.3.2 + HTMX 1.9.10 + Vanilla
JS ES6+), sistema de Offcanvas único (`mostrarOffcanvasSeguro`). **0 migraciones nuevas de modelo**
esta sesión — todos los cambios fueron de lógica/manejo de errores. `makemigrations --check` confirmó
`No changes detected` (Fase 53).

## 5. Reglas Inmutables — Cumplimiento

Las 20 reglas inmutables del documento maestro (sección "REGLAS INMUTABLES") se declaran respetadas,
verificadas fase por fase durante la ejecución — no se inventó funcionalidad, no se declaró `PASS` sin
evidencia, no se confundió `pytest PASS` con `UI PASS` (Fase 50, explícitamente), no se rompió Service
Layer/DSV/UUID lookup/RBAC, no se creó un segundo API client ni un segundo sistema de Offcanvas, no se
ocultaron errores reales (al contrario, Fase 29 los destapó), no se tocó `apps/public/` sin RFC, y no
se declaró `PRODUCTION READY` mientras existiera un bloqueo obligatorio (Fase 12 sigue `BLOCKED`).

## 6. Bloqueo Estructural — Capa 1 (Navegador Real)

**Causa raíz confirmada (Fase 12):** el sandbox de la herramienta de automatización de navegador
bloquea `fetch()`/XHR hacia IPs privadas/loopback (protección tipo anti-SSRF) mientras permite
navegación de página completa (`GET`). Verificado con prueba aislada: `fetch()` a un dominio público
funciona; `fetch()` a `127.0.0.1`/`cliente.sintel.net.co` (loopback vía `/etc/hosts`) falla con
`TypeError: Failed to fetch`, tanto en el login real como en una llamada manual. Como el login, HTMX y
los offcanvas dependen de `fetch()`/XHR (no de navegación de página completa), esto bloquea **toda**
interacción CRUD real en navegador. El túnel `cloudflared` existente se descartó explícitamente por
instrucción del usuario ("el proyecto corre en local"). No se encontró workaround.

**Esta es una limitación de la herramienta, no de la aplicación.** Bloquea en cascada: Fase 14 (Smoke
global), 15 (CRUD UI — parcial), 17 (Validación visual), 30 (Console en vivo), 34 (Responsive), 35
(Mobile UX), 54 (Final Full Smoke), 56 (Quality Gate). Console y Network sí se pudieron verificar
parcialmente en modo navegación de página completa (Fase 12 checklist).

## 7. Autenticación E2E

`PASS_WITH_LIMITATIONS` (Fase 13). Dual-Auth (JWT + Session) verificado a nivel de código y de tests
de API (todas las suites de Capa 2 pasan autenticadas). El login real en navegador vivo está sujeto al
mismo bloqueo de la Sección 6 (`Failed to fetch` en el POST de login).

## 8. Inventario de UI y Patrones Visuales

`NOT_STARTED` (Fases 8 y 9). No se construyó el inventario exhaustivo pantalla-por-pantalla (ruta →
submódulo → tab → listado → detalle → crear → editar → eliminar → acciones especiales) ni el
inventario de patrones visuales (Page Header, Toolbar, KPI, Badge, Offcanvas, etc.) clasificados como
`SHARED_EXISTING`/`DUPLICATE`/`INCONSISTENT`/etc. `MAPA_EXPERIENCIA_UX.md` y `UX_MASTER_BASELINE.md`
(misión UX previa, 2026-08-21) cubren un mapeo similar pero no fueron re-verificados como parte de
esta misión. La Fase 44 (Cross-App UX, Sección 24) sí produjo un hallazgo puntual de adopción de
componentes compartidos sin ejecutar el inventario completo.

## 9. Contrato Visual y Regla de Diseño

`NOT_STARTED` (Fases 10 y 11). No se definió ni verificó un contrato visual formal (tokens de diseño,
reglas de composición) para esta misión. Esto es trabajo de diseño previo a cualquier cambio visual
masivo y no se ejecutó porque el foco de las sesiones realizadas fue Capa 2 (backend/API), no rediseño
visual.

## 10. CRUD Real — Resultados Consolidados (Capa 2)

Las 15 apps de negocio tenant tienen cobertura CRUD verificada vía API (`pytest`/`APIClient`), nunca
vía clic real en navegador (Capa 1 `BLOCKED`). **`PASS` aquí significa "verificado con un test real que
pasa", nunca "parece funcionar"** (regla explícita de `UI_UX_COVERAGE_MATRIX.md`). 24 de 43 entidades
tienen CREATE+READ+UPDATE+DELETE completos en `PASS`/`PASS_LIM`; 12 de 43 quedan `NOT_TESTED` (sin
evidencia directa ni evidencia de fallo), concentradas en submódulos secundarios (Sede, Area,
ItemFactura, NotaCredito, TareaDiaria, ResolucionFacturacion). 9 archivos de test nuevos se crearon
esta sesión para cerrar huecos de cobertura que no existían antes (Proveedores, Compras, Gastos,
Inventario, Bancos, Proyectos, Perfil, Empresa/MailInboxConfig, Ventas).

Detalle completo: `UI_UX_COVERAGE_MATRIX.md`.

## 11. Matriz de Cobertura por App

| App | CRUD (Capa 2) | Smoke/Responsive/A11y/Console (Capa 1) | Estado |
|---|---|---|---|
| Clientes | PASS (preexistente) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Proveedores | PASS (CRUD nuevo) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Compras | PASS (bug 500 corregido) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Ventas | PASS (bug 500 corregido) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Cotizaciones | PASS (auditado, 0 hallazgos) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Inventario | PASS (bug 500-vs-404 ×4 corregido) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Facturas | PASS (6 propiedades corregidas) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Gastos | PASS (GASTOS-01/02 corregidos) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Bancos | PASS (CRUD nuevo) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Contabilidad | PASS (auditado, 0 hallazgos, sin cambios) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Empleados | PASS (hallazgo menor documentado) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Proyectos | PASS (CRUD nuevo) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Empresa | PASS (hallazgo PK/UUID documentado) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Perfil | PASS (hallazgo seguridad PK/UUID documentado) | BLOCKED | `PASS_WITH_LIMITATIONS` |
| Dashboard | PASS (DASH-02 corregido, solo lectura) | BLOCKED | `PASS_WITH_LIMITATIONS` |

**Conteo:** 15/15 apps en `PASS_WITH_LIMITATIONS`. Ninguna en `PASS` pleno (las 5 columnas de Capa 1
bloquean el pleno en el 100% de la superficie). Ninguna en `FAIL`. Fuente: matriz completa de 43 filas
en `UI_UX_COVERAGE_MATRIX.md`.

## 12. Formularios, Validación y Manejo de Errores

`PASS_WITH_LIMITATIONS` (Fases 18 parcial, 19). Fase 18 (inventario de formularios Django)
`NOT_STARTED` como inventario formal, pero el manejo de errores de validación sí se auditó y corrigió
en profundidad (Fase 19): 3 bugs reales de "500 en vez de 400/404" corregidos con evidencia de test
(COMPRAS-500-01, VENTAS-500-01, INVENTARIO-404-01 — Sección 26), y 1 patrón inverso ("400 en vez de
500", EMPLEADOS-400-01/PERFIL-400-01) documentado y diferido por alcance quirúrgico.

## 13. Errores Silenciosos (Hallazgo Central de la Sesión)

`PASS_WITH_LIMITATIONS` (Fase 29) — el hallazgo más repetido y el más grave de la sesión.
**GASTOS-01** (P1): `materializar_gasto_desde_dto()` fabricaba una `Empresa`/`ResolucionDIAN` falsa
cuando faltaba la real, persistiendo un dato fiscal legalmente significativo sobre una base inventada
— corregido a fallo explícito (`ValidationError`), autorizado por el usuario tras confirmar que ningún
test dependía del comportamiento anterior. **GASTOS-02/DASH-02/FACTURAS-SILENT-01** (P2): 12
propiedades/extractores en Gastos, Dashboard y Facturas convertían cualquier error real en `$0`
silencioso sin dejar rastro en logs — corregido agregando `logger.exception(...)` con contexto en los
12 puntos (el valor de fallback `$0` se mantuvo; cambiar el contrato de API para que el frontend
distinga "0 real" de "error" queda `DEFERRED` como decisión de producto mayor). Detalle completo:
`UI_UX_FINDINGS.md`.

## 14. Componentes UI — Tablas, KPIs, Estados, Badges, Offcanvas, Loading, Empty States

`NOT_STARTED` a nivel de auditoría formal (Fases 21-28: Tablas, Densidad, KPIs, Estados, Badges,
Offcanvas, Loading, Empty States). Ninguna de estas 8 fases se ejecutó como auditoría dedicada en esta
misión. Lo único verificado transversalmente sobre estos componentes es la adopción real del sistema
compartido (`sintel_kpi_card`, `sintel_empty_state`, `filter_bar.html`, `loading_state.html`) — ver
Sección 24 (Cross-App UX) — no su comportamiento visual o de interacción individual, que requiere
Capa 1.

## 15. Accesibilidad de Formularios

`NOT_STARTED` (Fase 20). No se ejecutó ninguna verificación de accesibilidad (labels, `aria-*`,
navegación por teclado, contraste) esta sesión. Requiere Capa 1 para verificación real en DOM
renderizado, o una auditoría estática de plantillas que tampoco se realizó.

## 16. Consola del Navegador

`BLOCKED` en su mayoría (Fase 30). Se pudo leer la consola del navegador en modo navegación de página
completa y confirmar el error de `fetch()` bloqueado (Sección 6) — no se pudo verificar consola tras
interacción JS real (clic, submit de formulario, HTMX) por el mismo bloqueo estructural.

## 17. Network — Códigos de Estado HTTP

`PASS_WITH_LIMITATIONS` (Fase 31). A nivel de viewport real (Capa 1), `BLOCKED` — se confirmó
`net::ERR_BLOCKED_BY_CLIENT` con la herramienta de lectura de red, evidencia de la causa raíz de la
Sección 6. A nivel Capa 2, cobertura real y verificada: los 7 bugs de código de estado HTTP corregidos
esta sesión (500→400 ×2, 500→404 ×4) tienen test que confirma el código correcto.

## 18. Multi-Tenant y Aislamiento Organizacional

`NOT_STARTED` como auditoría dedicada (Fase 32), pero cubierto indirectamente con evidencia real: los
tests de aislamiento organizacional/cross-tenant ya incluidos en las regresiones de Compras,
Inventario y Cuentas por Pagar (`test_cuentas_pagar_isolation_and_abono.py`) pasaron 100% en esta
sesión, y el flujo E2E de la Fase 45 verificó aislamiento entre tenants como parte del recorrido de
negocio. No hubo una fase dedicada a probar exhaustivamente fuga de datos entre schemas más allá de
eso.

## 19. Seguridad

`PASS` (Fase 33) para lo auditado, con 2 hallazgos de higiene arquitectónica documentados y diferidos
por decisión explícita del usuario: **PERFIL-PK-01** y **MAILINBOX-PK-01** — ambos `ViewSets` aceptan
lookup por ID entero además de UUID (violación de la regla no-negociable "UUID lookup, not PK" de
`CLAUDE.md`), sin ser IDOR real (DSV/`empresa_id` sigue protegiendo los datos). El usuario decidió
explícitamente documentar sin corregir, por riesgo de romper contrato de API con callers no
identificados en frontend. Detalle: `UI_UX_FINDINGS.md`.

## 20. Responsive y Mobile UX

`BLOCKED` (Fases 34 y 35), 100% dependiente de resolver la Fase 12. No hay ninguna evidencia de
comportamiento responsive/mobile verificada en viewport real esta sesión.

## 21. Performance UI, JavaScript y Código Muerto

`NOT_STARTED` para Performance UI y JavaScript (Fases 36, 37) — no se midió tiempo de carga, tamaño de
bundle ni se auditó JS por calidad/duplicación esta sesión. **Código muerto** (Fase 38):
`PASS_WITH_LIMITATIONS` — se identificaron puntualmente elementos obsoletos durante la auditoría de
otras fases (no una barrida dedicada), sin remoción masiva no autorizada.

## 22. Tabulator y HTMX (Migración de Grillas)

`NOT_STARTED` (Fases 39, 40). No se evaluó el estado de la migración de Tabulator a
`django-tables2` + HTMX (`PLAN_UNICO_CORRECCIONES.md` Fase 5-BIS) durante esta misión; esa
información vive en `documentacion/PLAN_UNICO_CORRECCIONES.md` y no fue re-verificada aquí.

## 23. Cierre por Batches — las 15 Apps de Negocio Tenant

Ejecutado en 4 tandas con evidencia fresca en cada una (Fases 41-43 + cierre final):

- **Piloto (Fase 41):** Compras — bug 500 real corregido, CRUD nuevo, 52/52 tests.
- **Batch 2 (Fase 42):** Inventario (bug 500-vs-404 ×4), Facturas (6 propiedades), Gastos
  (GASTOS-01/02), Bancos (CRUD nuevo) — 60/60 + 67/67 + regresiones dirigidas.
- **Batch 3 (Fase 43):** Contabilidad (auditado limpio), Empleados (hallazgo menor), Proyectos (CRUD
  nuevo, 3/3), Empresa (hallazgo PK/UUID), Perfil (hallazgo seguridad), Dashboard (DASH-02
  corregido) — 67/67 (compartido con Gastos) + regresiones dirigidas.
- **Cierre final:** Ventas (bug 500 real corregido, 45/45) y Cotizaciones (auditada sin hallazgos
  nuevos, ya tenía cobertura completa incluyendo su propio test anti-regresión "400 no 500").

**Total: 273+/273+ tests verdes** en el ciclo completo de cierre Capa 2, con **7 bugs reales
corregidos** y **4 hallazgos documentados sin corregir** por decisión explícita o alcance.

## 24. Cross-App UX — Consistencia de Componentes Compartidos

`PARTIAL` (Fase 44). Hallazgo **CROSSAPP-UI-01**: el sistema de componentes UI compartidos
(`sintel_kpi_card`, `sintel_empty_state`, `filter_bar.html`, `loading_state.html`, ya documentados en
`UX_MASTER_BASELINE.md` como "reutilizar, no duplicar") tiene adopción real de solo **5 de 15 apps**
(Clientes, Proyectos, Ventas usan `{% load sintel_ui %}`; Compras y Gastos usan los partials
directamente). Las otras 10 apps (Proveedores, Cotizaciones, Inventario, Facturas, Bancos,
Contabilidad, Empleados, Empresa, Perfil, Dashboard) no adoptaron el sistema compartido — es deuda de
consistencia de experiencia (`P3`, no un bug funcional), no corregida esta sesión por ser un esfuerzo
de retrofit considerable fuera de alcance quirúrgico. `DEFERRED`.

## 25. Flujos de Negocio E2E

`PASS_WITH_LIMITATIONS` (Fase 45). 4 flujos de negocio verificados con evidencia fresca: 24/24 tests
de Cotización→Venta→Factura y Proveedor→Factura→CxP→Abono, más aislamiento organizacional/cross-tenant
ya incluido en las regresiones de Compras/Inventario/Ventas. **Hallazgo informativo EMISION-FISCAL-01:**
2 de los 4 flujos (los que terminan en "Facturar" sobre una Venta/Cotización) están bloqueados en
producción real por un flag regulatorio (`EMISION_FISCAL_VENTA_AUTORIZADA=False`) — SINTEL aún no
tiene autorización DIAN para emitir facturas electrónicas directamente. El pipeline existe, está
probado y funciona en código; el camino real de producción hoy es la ingesta de XML ya firmado
externamente. Esto no es un bug — es una restricción de producto/regulación ya documentada por el
equipo (`VENTAS-COMPRAS-FACTURAS-01`, 2026-09-09) y se cita aquí porque afecta la interpretación de
"E2E verificado" en Ventas/Cotizaciones.

## 26. Bugs Corregidos y Hallazgos Diferidos

**7 bugs reales corregidos con evidencia de test:**

| ID | App | Severidad | Descripción |
|---|---|---|---|
| COMPRAS-500-01 | Compras | P2 | `create()` devolvía 500 en vez de 400 (items vacíos/fecha inválida) |
| VENTAS-500-01 | Ventas | P2 | `crear_venta_borrador()` devolvía 500 en vez de 400 (`fecha_emision` faltante, `KeyError` no capturado) |
| INVENTARIO-404-01 | Inventario | P2 | 4 ViewSets devolvían 500 en vez de 404 para UUID inexistente |
| GASTOS-01 | Gastos | P1 | Fabricaba Empresa/ResolucionDIAN falsas en vez de fallar explícito |
| GASTOS-02/DASH-02/FACTURAS-SILENT-01 | Gastos, Dashboard, Facturas | P2 | 12 propiedades convertían error real en `$0` silencioso sin log |

**6 hallazgos documentados y diferidos** (0 inventados, todos citan archivo y línea real):
PERFIL-PK-01, MAILINBOX-PK-01 (seguridad/higiene, decisión explícita del usuario), EMPLEADOS-400-01/
PERFIL-400-01 (patrón inverso, alcance quirúrgico), CROSSAPP-UI-01 (consistencia, esfuerzo de
retrofit), EMISION-FISCAL-01 (regulatorio, no técnico). Detalle completo con reproducción y test:
`UI_UX_FINDINGS.md`.

## 27. Testing — Estrategia, Regression Gate y Evidencia

`PASS_WITH_LIMITATIONS` (Fases 47, 48, 49, 53, 55). Estrategia: Testing Progresivo por Alcance
(`CLAUDE.md` §24.0) — nunca `make test` completo por defecto; suites específicas por app modificada,
escaladas a cross-app cuando aplicó. Regression gate ejecutado tras cada batch: `manage.py check` limpio,
`makemigrations --check` sin cambios pendientes, **244/244 tests** en las apps directamente
modificadas de la última sesión (0 fallos sin explicar), cross-app regression verificado con los 24/24
tests de flujo de la Fase 45. Todos los resultados citados son de corridas frescas de la sesión que los
reporta, nunca reciclados (Regla Inmutable 18). UI smoke/console/network en vivo quedan `BLOCKED` (Fase
12). No se corrió la suite global completa por decisión deliberada de alcance — documentado
explícitamente, no una omisión.

## 28. Riesgos Residuales y Release Gate Final

**Riesgos residuales:**

1. **Capa 1 bloqueada** (Sección 6) — sin resolución de la limitación de sandbox de la herramienta de
   navegador (o una alternativa como `LiveServerTestCase`/`StaticLiveServerTestCase` de Django para
   pruebas funcionales con servidor vivo, no evaluada aún), no hay forma de verificar smoke, CRUD por
   clic real, responsive, accesibilidad en DOM vivo, consola tras interacción JS, o network en
   viewport real. Este es el único bloqueo estructural que impide el cierre de las Fases 12, 14, 15,
   17, 30, 34, 35, 54, 56.
2. **2 hallazgos de seguridad/higiene sin corregir** (PERFIL-PK-01, MAILINBOX-PK-01) — lookup por ID
   entero en vez de UUID exclusivamente. No es IDOR explotable (DSV protege `empresa_id`), pero viola
   una regla arquitectónica no-negociable. Diferido por decisión explícita del usuario, no por omisión.
3. **12 de 43 entidades sin verificación directa** (`NOT_TESTED`) — Sede, Area, ItemFactura,
   NotaCredito, TareaDiaria, ResolucionFacturacion y similares. Sin evidencia de fallo, pero tampoco
   de éxito.
4. **10 de 15 apps sin adoptar el sistema de componentes compartidos** (CROSSAPP-UI-01) — deuda de
   consistencia visual, no funcional.
5. **Contrato de API de errores silenciosos sin cambiar** (GASTOS-02-style) — el fallback `$0` se
   mantiene; solo se agregó logging. Un cliente/frontend no puede hoy distinguir programáticamente "0
   real" de "hubo un error" sin revisar logs de servidor.
6. **17 fases nunca iniciadas** (`NOT_STARTED`): 8, 9, 10, 11, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28,
   32, 36, 37, 39, 40 — principalmente inventario de UI/patrones visuales, contrato visual formal,
   accesibilidad, componentes de tabla/KPI/estado individuales, performance, JS y Tabulator/HTMX. No
   requieren Capa 1 en todos los casos (algunas son auditoría estática), pero no se ejecutaron en el
   alcance de las sesiones realizadas.

**RELEASE GATE FINAL: `NO GO` para `PRODUCTION READY` de UI/UX completo.**

Justificación (Regla Inmutable 19, Fase 57 `PASS`): la Fase 56 (Quality Gate) exige 9 criterios en
`PASS` pleno (UI Coverage, CRUD UI, Smoke, Visual Consistency, Responsive, Accessibility, Network,
Console, Backend Regression) y solo 1 de 9 (Backend Regression, para el alcance tocado) está en `PASS`
pleno. Los otros 8 están `BLOCKED` o `NOT_STARTED`. Declarar `PRODUCTION READY` en este estado violaría
directamente la Regla Inmutable 19 y el principio rector de la Fase 57.

**Lo que SÍ está listo para producción, con evidencia real:** la Capa 2 (API/backend) de las 15 apps de
negocio tenant, con 7 bugs de manejo de errores reales corregidos y verificados, 0 regresiones
introducidas, y el gate de regresión de backend en `PASS` para todo el alcance tocado esta sesión.

**Próximo paso recomendado (no ejecutado en esta sesión):** resolver el bloqueo de Capa 1 evaluando
`LiveServerTestCase`/`StaticLiveServerTestCase` de Django (mencionado en la propia Fase 12 como opción
no explorada a fondo) como alternativa a la herramienta de navegador con sandbox anti-SSRF, para poder
ejecutar por fin las Fases 14, 15, 17, 30, 34, 35, 54 y cerrar la Fase 56. En paralelo, las fases de
auditoría estática que no dependen de Capa 1 (8, 9, 18, 21-28, 32, 38-40) pueden ejecutarse ahora sin
ese desbloqueo.

---

**FIN DEL REPORTE FINAL — Fase 58 de `UI_UX_MASTER_MISSION_V2_59_FASES.md`.**
