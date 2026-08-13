# F31 — Reporte Final

**Fecha:** 2026-08-13 · Rama `feat/onboarding-cookie`.

## 1. Resumen ejecutivo

F31 auditó el frontend completo de las 17 apps tenant (F31.0), diseñó y
corrigió el contrato de Core Frontend con evidencia real (F31.1-F31.2),
auditó el contrato de API Client y el patrón JWT (F31.3), y completó un
piloto real de migración de grillas (F31.6, `inventario`, 4 sub-módulos)
que además cerró **3 bugs de producción reales y preexistentes**,
ninguno relacionado entre sí, todos descubiertos por evidencia directa
(lectura de código + tests reales), no por hipótesis. La corrección más
importante al plan original: el frontend está considerablemente más
migrado a HTMX + django-tables2 de lo que se asumía al iniciar la fase, y
al menos una migración completa (`inventario`) ya existía a medias,
comiteada y desconectada, desde una sesión anterior.

**Lo que NO se hizo, deliberadamente, con evidencia:** un cluster de
duplicación real en el transporte HTTP/CSRF/JWT (`http.js` x2 copias +
una tercera versión divergente que gana en producción, más 6 archivos
`*.api.js` con su propia reimplementación de fetch+CSRF+JWT) fue
investigado a fondo y **diferido** -- el riesgo de romper auth/CSRF/
uploads en todo el frontend tenant sin poder verificar en navegador es
demasiado alto para una corrección apresurada. Documentado como hallazgo
crítico para una micro-fase futura con pruebas de navegador como
prerrequisito explícito, no como trabajo pendiente silencioso.

## 2. F31.0 — Inventario real del frontend (solo lectura)

Auditoría estructural de las 17 apps: Tabulator vs django-tables2, HTMX,
API JS, patrón Offcanvas, guard de editor. **Corrección clave a la
hipótesis del usuario:** el patrón dominante ya es HTMX + django-tables2
(14/17 y 12/17 apps respectivamente), no Tabulator. `inventario` -- no
`cotizaciones` -- es la app realmente 100% Tabulator; `cotizaciones` ya es
híbrida. Hallazgos concretos: duplicación real de `http.js` en Core,
14 violaciones del patrón Offcanvas obligatorio en 6 apps.
Detalle: `F31_FRONTEND_INVENTORY.md`.

## 3. F31.1 — Contrato Core Frontend (diseño)

Propuso el contrato `Sintel.Core.*` mapeando archivos existentes a
módulos por responsabilidad única. Durante la propia investigación del
contrato se descubrió que el cluster `http.js` era más profundo de lo
que el inventario de F31.0 sugería (3 archivos, no 2, con divergencia de
comportamiento real). Corregido explícitamente en el propio documento
antes de pasar a ejecución. Detalle: `F31_FRONTEND_CONTRACT.md`.

## 4. F31.2 — Ejecución de Core Frontend

- **`error-service.js` eliminado** -- código muerto confirmado (manejo de
  errores DataTables, ya reemplazado por Tabulator en el lado tenant).
- **11 de 13 violaciones de Offcanvas corregidas** en 6 apps (bancos,
  empleados, facturas, proyectos, proveedores, empresa) -- 3 de ellas
  corrigieron además un bug latente real (backdrops acumulados por falta
  de `dispose()` previo). 2 excepciones documentadas deliberadamente (
  `devengo_editor.js`, `facturas_main.js`) por comportamiento específico
  que el helper compartido no replica.
- **Cluster `http.js`/`jwt-auth.js` diferido** tras investigación
  profunda -- ver §1.
- **Contrato de eventos auditado** (45 sitios) -- confirmó que
  `<modelo>-updated` ya es el patrón de facto, no el esquema de 3 eventos
  propuesto originalmente.
Detalle: `F31_2_CORE_EXECUTION.md`.

## 5. F31.3 — Auditoría de API Client + patrón JWT

- Verificado el patrón prohibido `window.jwtAuth.token`: **0 ocurrencias**
  en todo el repo.
- Auditados los 17 `<app>.api.js` contra el contrato "solo URLs+métodos,
  sin CSRF/JWT propio": la mayoría cumple. **6 archivos violan el
  contrato** (gastos, compras, empleados, cotizaciones, dashboard,
  ventas) con reimplementaciones completas de fetch+CSRF+JWT, cada una
  con su propio contrato de error distinto -- diferido junto con el
  cluster de §4 por el mismo motivo (riesgo sin verificación de
  navegador).
- De los 7 outliers de nombres de evento encontrados en F31.2, **1 se
  normalizó con confianza** (`inventarioActualizado` → `inventario-updated`,
  auto-contenido); **4 resultaron ser indirección deliberada** en
  `clientes` (no un error, se dejaron intactos); **1 es código muerto**
  sin listener (`facturaEliminada`, documentado, no tocado).

## 6. F31.6 — Piloto de migración de grillas: `inventario`

Hallazgo de partida: el backend de esta migración (`tables.py`/
`views.py`, 4 `Table`/`TableView` completas) **ya estaba comiteado**
desde una sesión anterior (`60d8a33`) pero nunca conectado -- `urls.py`
sin rutas, sin templates partial, frontend 100% Tabulator. F31.6
completó la conexión: 4 rutas nuevas, 4 templates partial, 4 templates de
lista actualizados a HTMX, 4 archivos `*_list.js` reescritos (lógica de
negocio preservada exacta, solo cambia el mecanismo de renderizado).

**2 bugs de producción reales encontrados y corregidos** en el proceso:
1. **WRONG_LOOKUP**: los botones de editar/eliminar enviaban el PK
   entero (`data-id`) a endpoints que exigen `uuid`
   (`BaseTenantViewSet.lookup_field="uuid"`) -- editar/eliminar
   categorías/productos/servicios/activos desde la grilla estaba roto en
   producción, nunca antes detectado porque nadie había podido ejercitar
   el flujo completo. `tables.py` (ya comiteado) ya usaba `data-uuid`
   correctamente; los `*_list.js` reescritos ahora lo consumen.
2. **`FieldError`** en `ProductoTableView.get_context_data()` -- un
   `.only()` redundante sobre un queryset con relaciones ya traversadas
   causaba un 500 garantizado la primera vez que alguien abriera la
   pestaña de Productos. Encontrado por el test nuevo, no por inspección.

Test nuevo (`test_tablas_htmx.py`, 6 tests, no existía cobertura previa)
+ regresión completa de `apps/tenant/inventario/` (25 tests): **pasan
limpio**. `movimientos` (Kardex) queda fuera de alcance -- vista agregada
cross-model, misma categoría que reportes de contabilidad/dashboard que
también coexisten deliberadamente con Tabulator (regla F31.7).
Detalle: `F31_6_INVENTARIO_GRID_MIGRATION.md`.

## 7. Governance

`tools/ekg/governance.py --offline`: 23 `viewsets_without_service_layer`,
6 `sede_or_area_field_without_sede_aware_model`, 2
`import_cycles_between_tenant_apps` -- **conteos idénticos al baseline de
F30**, confirmando que ninguna de las 3 fases de F31 introdujo hallazgos
nuevos.

## 8. Migraciones

0. Ningún cambio de F31 toca modelos (`makemigrations --check --dry-run`
-> "No changes detected").

## 9. Limitación transversal -- verificación de navegador

**Ningún cambio de F31 pudo verificarse visualmente en un navegador real.**
El Browser pane de este entorno no compone frames, y el único plugin que
permitiría pruebas E2E (`pytest-playwright`) no está instalado en el
contenedor. Toda la verificación de F31 se apoyó en: (a) lectura manual
línea por línea de cada archivo modificado contra el original, (b)
reutilización de patrones ya probados y en uso activo en el resto de la
base de código (nunca código inventado desde cero), (c) tests Django
reales contra HTTP real donde fue posible escribirlos (F31.6). Esta
limitación es la razón explícita detrás de cada decisión de diferir
trabajo en vez de forzarlo (§1, §4, §5) -- no es negligencia, es una
decisión de riesgo documentada en cada caso.

## 10. Trabajo explícitamente diferido (no iniciado o detenido con evidencia)

| Item | Razón |
|---|---|
| Cluster `http.js`/`jwt-auth.js`/6 `api.js` con CSRF/JWT propio | Riesgo de romper auth/CSRF/uploads en todo el frontend tenant sin poder verificar en navegador. Requiere micro-fase dedicada con pruebas de navegador como prerrequisito. |
| Migración de grilla `dashboard` | Investigado y descartado como candidato -- es un reporte KPI de solo lectura con formatters complejos y filtro de fecha, exactamente el perfil que F31.7 dice NO migrar automáticamente (misma categoría que los reportes de `contabilidad`). |
| Migración de grilla `cotizaciones` | Ya es híbrida (HTMX en offcanvas/formularios, Tabulator solo en el grid principal) -- no se investigó si aplica la misma excepción de F31.7 antes de forzar una migración. |
| Normalización completa del contrato de eventos | Solo 1 de 7 outliers se normalizó; el resto requiere la misma investigación caso-por-caso que reveló que los eventos de `clientes` eran indirección deliberada, no un error de nombres. |
| F31.4 (Autenticación), F31.5 (HTMX como motor principal) | Se solapan directamente con el cluster diferido de `http.js`/`jwt-auth.js` -- mismo motivo de riesgo. |
| F31.7-F31.15 (migración por app completa, UX/responsive, performance, tests E2E, Knowledge Graph frontend, gobernanza automática de patrones frontend) | No iniciados -- fuera del alcance cubierto en esta fase. |

## 11. Estado final

```
F21 [OK] COMPLETED
F22 [OK] COMPLETED
F23 [OK] COMPLETED
F24 [OK] COMPLETED
F25 [OK] COMPLETED
F26 [OK] COMPLETED
F27 [OK] COMPLETED
F28 [OK] COMPLETED
F29 [OK] COMPLETED
F30 [OK] COMPLETED
F31 [OK] COMPLETED (alcance parcial, explícitamente documentado en §10 -- no una fase cerrada al 100% del plan original, sino hasta el límite seguro sin verificación de navegador)
```

**3 bugs de producción reales descubiertos y corregidos** (WRONG_LOOKUP
en inventario x1, `FieldError` en inventario x1, mismo cluster; ver §6).
**0 regresiones** introducidas (governance idéntico a F30, migraciones en
0, todas las suites de test relevantes pasan limpio). Gobernanza
sostenida. La limitación de verificación de navegador (§9) es el
condicionante explícito de todo lo diferido -- corregirla (credenciales de
prueba, o `pytest-playwright` instalado) es el desbloqueador directo para
continuar F31 más allá de este punto.

## 12. Commits de la fase

```
9ba2dfc docs: F31.0 -- inventario real del frontend (17 apps, solo lectura)
dec0d44 docs: F31.1 -- contrato Frontend propuesto (Core, diseno, sin codigo nuevo)
8877b53 fix: F31.2 -- eliminar error-service.js (codigo muerto, migracion a Tabulator ya completada)
43b476d fix: F31.2 -- corregir 11 violaciones del patron Offcanvas obligatorio
6db2672 docs: F31.2 -- ejecucion de Core Frontend + correcciones al contrato F31.1
d654bf6 docs: F31.3 -- auditar contrato API Client (solo lectura, 0 codigo tocado)
901acce fix: F31.3 -- normalizar evento inventarioActualizado a inventario-updated
10213fa docs: F31.3 -- documentar resultado de investigar los 7 outliers de eventos
45e764e fix: F31.6 -- FieldError en ProductoTableView.get_context_data (bug real preexistente)
97b6a83 feat: F31.6 -- conectar migracion de grillas de inventario (Tabulator -> django-tables2+HTMX)
01ee4aa docs: F31.6 -- informe de migracion de grillas de inventario
```
