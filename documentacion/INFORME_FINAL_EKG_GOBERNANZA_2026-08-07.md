# Informe Final — Extensión del Enterprise Knowledge Graph (Motor de Impacto + Gobernanza)

**Fecha:** 2026-08-07 (actualizado el mismo día tras "continua con las fases faltantes" — ver §7)
**Alcance:** extender el pipeline EKG ya existente (`tools/ekg/`, piloto desplegado a las 17 apps tenant el 2026-08-04/05) con un motor de consultas de impacto y un primer conjunto de reglas de gobernanza automática — la prioridad que el usuario eligió del pedido original de "Gobernanza Automática mediante Grafo de Conocimiento". Extendido después (§7) a cobertura de `apps/public/`, sincronización en CI, un explorador visual y una capa de síntesis, cerrando las fases restantes del pedido original.
**Estado del Neo4j vivo al cierre de §1-6:** 2.533 nodos / 3.925 aristas (partió de 2.506 / 3.730). Grafo offline final (22 apps, §7): 2.843 nodos / 4.328 aristas.
**Tests:** 63/63 pasan (`tools/ekg/tests/`, 21 nuevos en §1-6 + 10 nuevos en §7).

---

## 1. Resumen ejecutivo

Se entregaron dos módulos nuevos (`impact.py`, `governance.py`) sobre la arquitectura ya probada del piloto EKG. En el proceso de construirlos — nunca aceptando una afirmación del grafo sin verificarla contra el código fuente real — se encontraron y corrigieron **5 bugs reales en el extractor** que llevaban desde el rollout inicial (2026-08-04) sin detectarse, todos con la misma causa raíz de fondo: el extractor asumía que una clase base o un target de FK vivía siempre en la misma app que quien la referenciaba, cuando en la práctica los patrones arquitectónicos centrales del proyecto (`SintelTenantBaseModel`, `BaseTenantViewSet`, FKs a `Empresa`) casi siempre cruzan app.

Cada bug se descubrió **porque una regla de gobernanza legítima producía un resultado absurdo** (ej. "ningún modelo del proyecto hereda de `SintelTenantBaseModel`") y se investigó hasta la causa raíz en vez de aceptarlo. Esa disciplina — no construir sobre datos sin verificar — es la misma que ya regía el resto del pipeline y se mantuvo sin excepción.

---

## 2. Qué se construyó

### 2.1 Motor de impacto (`tools/ekg/impact.py`)
Responde "¿qué se rompe si cambio esto?" dado un nodo de partida (nombre exacto o fragmento de ruta de archivo):
- Recorrido reverso sobre `IMPORTS/INHERITS/USES/CALLS/CONSUMES/REFERENCES` (dependientes).
- Recorrido hacia adelante sobre `EXPOSES/RENDERS` desde cada nodo ya impactado (lo que ese nodo produce).
- Pruebas que cubren el radio de impacto, apps tocadas, reglas (`AGENTS.md`/skills) y documentos (ADRs/auditorías) a revisar.
- Dos implementaciones (offline sobre los 17 dumps fusionados, y Cypher contra el Neo4j real) que deben coincidir — y de hecho **dos bugs de Cypher se encontraron exactamente por esa comparación** (recorrido `EXPOSES` no transitivo, y colisión de `DISTINCT` por nombres de visualización vacíos).
- CLI: `python -m tools.ekg.impact --offline --name <X>` / `--path <fragmento>` / `--live --name <X>`. Integrado en `Makefile` (`make ekg-impact NAME=...`).

### 2.2 Motor de gobernanza (`tools/ekg/governance.py`)
Cuatro reglas verificables **solo** con datos que el grafo ya extrae honestamente (sin inventar chequeos que no puede respaldar — ver su docstring para la lista explícita de lo que NO se implementó y por qué: DSV, permisos, `.only()`/`empresa_id`, Signals, N+1 — todos requieren análisis de flujo de control que este extractor estático no hace):

| Regla | Resultado final |
|---|---|
| `models_not_inheriting_tenant_base` | **0** (era 7, todos falsos positivos de los bugs #1/#3/#4 abajo) |
| `js_outside_own_app_static_path` | **0** — limpio, confirmado real, no vacuo |
| `templates_outside_own_app_path` | **0** — ídem |
| `viewsets_without_service_layer` | **23 candidatos** → triage manual completo en §4 |

CLI: `python -m tools.ekg.governance --offline`. Integrado en `Makefile` (`make ekg-governance`).

---

## 3. Bugs reales encontrados y corregidos en `tools/ekg/extract_python.py`

Los 5 comparten la misma causa raíz de fondo (resolución "misma-app-siempre" en vez de resolver vía los imports reales del archivo) y se corrigieron reutilizando el patrón ya correcto que `resolve_model_target()` usaba para FKs con string `"app_label.Modelo"`.

| # | Bug | Impacto antes del fix | Corregido con |
|---|---|---|---|
| 1 | `INHERITS` cross-app nunca se resolvía para Modelos | **Ningún modelo tenant del proyecto (~62 modelos, 17 apps) aparecía heredando `SintelTenantBaseModel`** en el grafo | `_build_import_map()` + `_resolve_cross_app_base_folder()` |
| 2 | Mismo bug, para ViewSets (`BaseTenantViewSet`, `SintelDSVMixin`) | Ningún ViewSet aparecía heredando su base real | Mismo mecanismo, aplicado a `extract_viewsets()` |
| 3 | Nodos `ViewSet` reales nunca marcaban `external: False` explícito | Un ViewSet real podía "des-resolverse" a stub según el orden de fusión entre apps | Explicitar `external: False` en la creación real, igual que ya hacía `extract_models()` |
| 4 | Clases `TextChoices`/`IntegerChoices`/`Choices` se extraían como si fueran `Model` | `perfil.RolTenant` (un enum de roles) aparecía como "modelo que no hereda la base" | Guard `_NON_MODEL_BASE_NAMES` en `extract_models()` |
| 5 | `resolve_model_target()` (FKs/`Meta.model`) tenía el mismo blindspot que #1, pero para referencias bare (identificador importado, no string) | 4 apps (`empleados`, `inventario`, `proveedores`, `proyectos`) creaban **cada una su propio placeholder mal ubicado** para `Empresa` en vez de resolver al único nodo real `Model:empresa.Empresa` | Mismo mecanismo de resolución vía imports, aplicado también a `resolve_model_target()` |

**Metodología de verificación en los 5 casos:** extracción fresca desde el código fuente actual (nunca confiar en un dump JSON que pudiera estar desactualizado), lectura directa del archivo fuente antes de aceptar cualquier hallazgo como real, test de regresión nuevo por cada fix (21 tests nuevos en total), y regeneración + recarga de los 17 dumps y del Neo4j vivo después de cada corrección — incluyendo limpieza manual de 4 nodos huérfanos que el `MERGE` idempotente nunca elimina por sí solo tras un cambio de id.

---

## 4. Triage manual completo de los 23 hallazgos de `viewsets_without_service_layer`

Ningún hallazgo se reportó como "confirmado" sin leer su código fuente real.

### 4.1 Hallazgos reales (5) — sin ningún mixin de Service Layer, directo ni heredado
| ViewSet | Nota |
|---|---|
| `ResolucionDIANViewSet` (`apps/tenant/empleados/api/viewsets.py:1630`) | Existe una clase homónima en `gastos` que **sí** tiene `ResolucionServiceMixin` — son dos clases distintas, no el mismo bug repetido |
| `ConfiguracionRetencionesViewSet` (`contabilidad`) | Solo `SintelDSVMixin, BaseTenantViewSet` |
| `ItemFacturaViewSet` (`facturas`) | Solo `BaseTenantViewSet` |
| `NotaCreditoViewSet` (`facturas`) | Solo `BaseTenantViewSet` |
| `DepartamentoViewSet` (`perfil`) | Solo `BaseTenantViewSet` |

*(Sus facades `*CoreViewSet` correspondientes heredan correctamente esta misma condición — no son hallazgos independientes.)*

### 4.2 Falsos positivos del extractor (8) — el mixin de servicio existe y tiene el nombre correcto, pero vive fuera de `services/`
| ViewSet | Mixin real | Ubicación real (no escaneada por `extract_services()`) |
|---|---|---|
| `LibroDiarioViewSet` | `ContabilidadServiceMixin` | `apps/tenant/contabilidad/api/viewsets.py:118` |
| `PerfilViewSet` | `PerfilServiceMixin` | `apps/tenant/perfil/api/mixins.py:8` |
| `ProyectoViewSet` (+ `ProyectoCoreViewSet`) | `ProyectoServiceMixin` | `apps/tenant/proyectos/api/mixins.py:11` |

**Hallazgo colateral, no corregido:** `proyectos` tiene **dos clases** llamadas `ProyectoServiceMixin` — una en `api/mixins.py` (la que el ViewSet realmente importa y usa) y otra en `services/api_mixins.py` (correctamente ubicada, pero sin usar). Vale la pena que alguien del equipo revise esta duplicación de nombre.

**No corregido en esta sesión:** extender `extract_services()` (o agregar un paso nuevo) para también escanear `api/mixins.py`/`api/viewsets.py` en busca de clases con forma de `BaseServiceMixin`.

### 4.3 Excepciones deliberadas y documentadas (2) — no son violaciones
`EmpresaViewSet` y `MailInboxConfigViewSet` (`apps/tenant/empresa/api/viewsets.py`) heredan `viewsets.ModelViewSet` directo, sin pasar por `BaseTenantViewSet`. El docstring de `EmpresaViewSet` documenta explícitamente su propio reemplazo manual: Session-Auth + CSRF, y modo "ENFORCED: POST/PATCH/PUT/DELETE solo STAFF/ADMIN". `empresa` está documentado en otro lugar como el módulo "REFERENCIA GOLDEN" del proyecto — todo indica una decisión revisada, no un descuido.

### 4.4 Excepciones probables, no verificadas línea por línea (4)
`CoreAuthViewSet`, `CoreLinksViewSet`, `DashboardSectionsViewSet`, `LandingViewSet` — heredan `ViewSet` plano (no `ModelViewSet`), consistente con ser endpoints de infraestructura/utilidad (emisión de tokens, enlaces estáticos, listado de secciones, página pública) que no son CRUD por diseño. No se leyó el cuerpo completo de cada uno.

### 4.5 Posible código muerto, no una cuestión de Service Layer (1)
`BaseViewSet` (`apps/tenant/inventario/api/viewsets.py:40`) — cero subclases encontradas en todo el archivo (`grep "BaseViewSet)"` sin resultados). Candidato para el backlog de código muerto, no para esta regla.

### 4.6 Facades `*CoreViewSet` restantes
`CatalogoMaestroNIIFCoreViewSet`, `ConfiguracionCotizacionCoreViewSet`, `EmpresaCoreViewSet`, `ItemFacturaCoreViewSet`, `MailInboxConfigCoreViewSet`, `MovimientoContableCoreViewSet`, `NotaCreditoCoreViewSet`, `ProyectoCoreViewSet` — todas heredan correctamente (vía `INHERITS` transitivo, ya verificado) su ViewSet tenant real; su estado depende enteramente de a cuál de las categorías 4.1–4.5 pertenezca ese padre.

---

## 5. Qué NO se hizo (explícito, no oculto)

- **Extender `extract_services()`** para cerrar los 8 falsos positivos de §4.2 — caracterizado y documentado, no implementado (fuera del alcance ya ampliado de esta sesión).
- **Verificar línea por línea** los 4 "probables legítimos" de §4.4 y confirmar `BaseViewSet` como código muerto real (§4.5) antes de eliminarlo.
- **El resto de las 10 fases** del pedido original de gobernanza: dashboard de métricas, sincronización continua en CI/pre-commit, cobertura de `apps/public/`/`apps/services/`, modelado de `contabilidad/integracion/` (el motor Pull Model), nodos a nivel de función, GraphRAG/embeddings. Todo permanece en el Roadmap de `PILOT_REPORT.md` (ítems 2-11), sin tocar.
- **Reglas de gobernanza que requieren análisis de flujo de control** (DSV, permisos por endpoint, `.only()`/`empresa_id` en querysets, N+1, Signals) — declaradas explícitamente como no-implementables con el extractor estático actual, no simuladas ni inventadas.

---

## 6. Archivos entregados/modificados esta sesión (§1-6)

**Nuevos:** `tools/ekg/impact.py`, `tools/ekg/governance.py`, `tools/ekg/tests/test_impact.py`, `tools/ekg/tests/test_governance.py`, este informe.
**Modificados:** `tools/ekg/extract_python.py` (5 fixes), `tools/ekg/tests/test_extract_python.py` (+4 tests), `tools/ekg/tests/test_build_graph.py` (+1 test), `tools/ekg/PILOT_REPORT.md` (bitácora completa), `Makefile` (`ekg-impact`, `ekg-governance`), los 17 dumps en `tools/ekg/out/*.json`, y el Neo4j vivo (recargado 3 veces, una limpieza manual de nodos huérfanos).

**Validación (§1-6):** `python -m pytest tools/ekg/tests/ -q` → 53 passed. `python manage.py check` → 0 errores.

---

## 7. Continuación el mismo día: fases restantes del pedido original ("continua con las fases faltantes")

El usuario preguntó directamente si el pedido original de gobernanza (10 fases) ya estaba ejecutado. Respuesta honesta en su momento: solo la Fase 6 (motor de impacto) estaba completa; Fases 1/3/4/5/7 parciales; Fase 2 preexistente; Fases 8/9/10 sin empezar. Esta sección cierra esas fases restantes, con el mismo criterio de todo el informe: nada se documenta como hecho sin verificarlo contra datos reales.

### 7.1 Fase 1 (extensión): cobertura de `apps/public/*`
5 apps nuevas (`accounts`, `tenants`, `impuestos`, `console`, `core`), 22 apps en total. Requirió separar `app_name` (namespace de ids) de `folder_name` (ruta real en disco) en todos los extractores — `apps/public/core` y `apps/tenant/core` comparten nombre de carpeta pero son apps distintas; sin esta separación, colisionaban en un único `Application:core` al fusionar. Detectado y corregido antes de generar cualquier reporte. `impact.py`/`governance.py`/`platform.py` fusionan las 22 apps por defecto desde este cambio.

**Bug de scope encontrado y corregido en el mismo paso:** las 2 reglas de `governance.py` que son tenant-only (herencia de `SintelTenantBaseModel`, uso de Service Layer) marcaban 19 modelos y 24 ViewSets del schema público como violaciones — ninguno es un hallazgo real, es la regla equivocada aplicada al schema equivocado (`arquitectura_general.md` Sec 3.2/4.2 nunca extiende esas reglas a `apps/public/`). Corregido con `_tenant_app_ids()`/`_belongs_to_tenant_app()`; el conteo tenant-only (0 modelos / 23 ViewSets) no cambió al agregar las apps públicas, confirmando que el fix no oculta ni infla nada.

### 7.2 Fase 8 (sincronización continua): job de CI
Job nuevo `ekg-graph-health` en `.github/workflows/ci-quality-gate.yml`, separado del gate principal (`test-and-quality`) para que un problema de extracción del EKG nunca bloquee un PR no relacionado. En cada PR/push a `main`/`develop`: extracción dry-run de las 22 apps, `tools.ekg.validate` por app tenant (falla dura si hay `dangling_edges`), y `tools.ekg.governance --offline` (informativo, `continue-on-error: true` hasta depurar/suprimir los hallazgos ya triageados en §4). Los tests de `tools/ekg/tests/` no necesitaron ningún cambio de CI — ya corrían dentro del job `pytest` genérico existente. Verificado localmente contra `compras` (tenant) y `public_core` (público) con los mismos argumentos exactos del workflow antes de darlo por cerrado.

### 7.3 Fase 9 (visualización): explorador HTML navegable
`tools/ekg/export_html.py` / `make ekg-explorer` genera un único archivo HTML autocontenido y offline (`tools/ekg/out/graph_explorer.html`) — sin servidor, sin CDN, sin red. Permite buscar cualquier nodo por nombre/ruta, filtrar por los 14 labels con datos reales, ver sus propiedades completas, y navegar cada relación entrante/saliente con un clic (`location.hash`, funciona con atrás/adelante del navegador). El propio explorador declara en su barra lateral lo que el grafo **no** modela (tareas Celery, eventos/signals, permisos por endpoint) en vez de omitirlo en silencio.

**Bug real encontrado y corregido verificando en un navegador real** (no la vista previa aislada de la herramienta — confirmado sirviendo el archivo con `python -m http.server` e inspeccionando `document.scripts`/el DOM directamente): varias propiedades `body` de nodos `Rule`/`Document` son texto de `AGENTS.md` citado literalmente, incluyendo ejemplos de código con `<script>` literal. Insertar el JSON del grafo directamente dentro del `<script>` de la página permitía que la primera subcadena `</script` cerrara la etiqueta real antes de tiempo — el navegador mostraba el resto del JSON/markdown como texto plano en vez de ejecutar la interfaz. Corregido escapando `"</"` a `"<\/"` en el JSON embebido; test de regresión en `tools/ekg/tests/test_export_html.py` que verifica que sobrevive exactamente un `</script>` en el HTML final, usando una app real (`core`) cuyo contenido `Rule` se confirma (por el propio test) que contiene `</` — no un fixture sintético que pasaría igual sin el fix.

### 7.4 Fase 10 (plataforma enterprise): CLI unificado de síntesis
`tools/ekg/platform.py` / `make ekg-summary` / `make ekg-dossier NAME=...` — explícitamente **no** un motor de análisis nuevo ni un dashboard web: casi todas las preguntas de ejemplo del pedido original ("quién usa este modelo", "qué rompe este cambio", "qué pruebas/ADR aplican") ya las responde `impact_of_offline()`; la única brecha real era "ejecutar impact.py y governance.py juntos y leer la respuesta en un solo lugar". Dos adiciones genuinamente nuevas, ambas proxies directos sobre datos que el grafo ya tiene:
- **`compliance_summary()`**: porcentaje de cumplimiento por regla de `governance.py`, sobre la población *aplicable* (ej. modelos tenant con `defined_in` real, excluyendo placeholders y nodos del schema público) — no "todos los nodos con ese label". Etiquetado explícitamente como proxy sobre 4 reglas verificables, no un score certificado de arquitectura.
- **`decoupled_apps()`**: apps sin ninguna arista cross-app de acoplamiento (`IMPORTS/INHERITS/USES/CALLS/CONSUMES/REFERENCES`) en ningún sentido.

**Otro bug real encontrado y corregido antes de confiar en el primer resultado:** `apps/tenant/api/` aparecía como "desacoplado" — pero es un falso resultado por falta de datos, no un hallazgo real: esa app nunca se extrae como una de las 22 apps (solo aparece como stub externo, ej. `ViewSet:api.BaseTenantViewSet`), y un stub externo nunca recibe una arista `BELONGS_TO` real, así que ninguna arista de acoplamiento se le atribuye jamás — pese a que `BaseTenantViewSet` tiene 45 aristas `INHERITS` reales apuntándole en todo el proyecto. Corregido excluyendo del cálculo las Applications `external: True`. Resultado final, ya verificado: los 5 módulos de `apps/public/*` son el único hallazgo genuino — no tienen ninguna arista estática que los conecte con una app tenant, lo cual es plausible dado que el patrón Bridge (AGENTS.md Sec 17) usa una llamada de servicio en tiempo de ejecución en vez de un import estático; esto se reporta como observación a nivel de grafo, no verificado contra el comportamiento en runtime.

**Resultado de cumplimiento sobre el grafo completo (22 apps):** `models_not_inheriting_tenant_base` 100% (69/69), `js_outside_own_app_static_path` / `templates_outside_own_app_path` 100% cada una, `viewsets_without_service_layer` 70.9% (56/79) — los mismos 23 hallazgos de §4, ahora expresados como porcentaje.

### 7.5 Qué sigue sin hacerse (igual que §5, sin cambios)
`apps/services/*` sigue completamente fuera de alcance. Extender `extract_services()` para cerrar los 8 falsos positivos de §4.2 sigue sin implementarse. Las reglas que requieren análisis de flujo de control (DSV, permisos por endpoint, `.only()`/`empresa_id`, N+1, Celery, eventos/signals) siguen declaradas explícitamente como no-implementables con el extractor estático actual — nunca simuladas.

### 7.6 Archivos nuevos/modificados en esta continuación
**Nuevos:** `tools/ekg/export_html.py`, `tools/ekg/platform.py`, `tools/ekg/tests/test_export_html.py`, `tools/ekg/tests/test_platform.py`, `.claude/launch.json` (config de dev-server local para verificar el explorador en un navegador real).
**Modificados:** `tools/ekg/extract_python.py`/`extract_js.py`/`extract_docs.py`/`build_graph.py` (split `app_name`/`folder_name`/`schema_root`), `tools/ekg/impact.py` (`PUBLIC_APPS`), `tools/ekg/governance.py` (`_tenant_app_ids`/`_belongs_to_tenant_app`), `.github/workflows/ci-quality-gate.yml` (job `ekg-graph-health`), `Makefile` (`ekg-explorer`, `ekg-summary`, `ekg-dossier`), `tools/ekg/PILOT_REPORT.md`, `MEMORY.md`.

**Validación final:** `python -m pytest tools/ekg/tests/ -q` → **63 passed**. Verificación manual en navegador real (servidor HTTP local) del explorador HTML: búsqueda, filtro por categoría, panel de detalle y navegación por clic en relaciones, todo confirmado funcionando contra el grafo real de 2.843 nodos / 4.328 aristas.
