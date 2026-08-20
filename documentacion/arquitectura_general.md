# Arquitectura General — SINTEL ERP

**Version:** 3.52.0
**Ultima actualizacion:** 2026-08-20 (DOC-M39) — FASE 33 (Shared UI / Design
System), continua EN PROGRESO -- no cerrada, documentado con evidencia por
que. Cubre el cierre del **Nivel 3** de la regresion incremental
(F33.15-B): las **16/16 apps de `apps/tenant/**`** quedan confirmadas
individualmente (nunca la suite completa durante el proceso, per
instruccion explicita del usuario) -- `bancos`, `perfil`, `ventas`,
`inventario`, `proveedores`, `compras`, `empleados`, `empresa`,
`proyectos`, `gastos`, `cotizaciones`, `clientes`, `contabilidad`,
`dashboard`, `core`, `facturas`. Hallazgos reales corregidos con
evidencia por app (lista completa en
`F33.15_TESTING_EXECUTION_STATUS.md`, seccion "STATUS FINAL: Nivel 3
COMPLETO"), entre los mas significativos:
- **`proyectos`** (3 bugs de produccion): guard de fase `CIERRE` muerto
  en `ProyectoDetailSerializer.validate()` (permitia editar datos
  generales de un proyecto cerrado); DSV faltante en
  `PresupuestoBusinessService.crear_item()` (documentado en su propio
  docstring pero nunca implementado); `NotNullViolation` por convertir
  a `None` un `CharField` no-nullable.
- **Descubrimiento arquitectonico (`Empresa` singleton por schema):**
  `UniqueConstraint` en `singleton_key` impide un segundo `Empresa`
  real por tenant -- invalida el patron de tests antiguos que creaban
  una "segunda empresa" para simular cross-tenant. Patron de reemplazo
  establecido: instancia `Empresa` sin persistir con `id` distinto
  para checks DSV que ocurren antes de cualquier persistencia.
- **`clientes`:** `CarteraViewSet.list()`/`kpis()` migraron a leer
  `Factura.naturaleza='VENTA'` (Pull Model, no la tabla `Cartera`
  legacy); FASE 4 anti-duplicidad (Zero Trust) reemplazo la
  idempotencia HTTP v2.61.4 original en `ClienteViewSet.create()`.
- **`contabilidad`:** `PeriodoContable.periodo` (`CharField(7)`,
  formato YYYY-MM) + `uuid` vs `id` en URLs de
  `ConfiguracionRetencionesViewSet`.
- **`core`:** endpoint universal de documentos real en
  `/api/v1/core/_apps/facturas/upload-document/` (no
  `/api/v1/documentos/upload/`, protegido por
  `FEATURE_UPLOAD_DOCUMENT_ENDPOINT`); `@override_settings(...)` como
  **decorador de clase no tiene efecto con `TenantTestCase`**
  (django_tenants) -- requiere `with override_settings(...):` por
  request; `IsTenantAdminOrReadOnly` exige `TenantProfile.rol`
  (schema tenant), no `TenantMembership.rol` (schema public) -- gap
  recurrente en multiples apps esta fase; 16 tests de workspace
  facturas (modal XML, `facturas.page.js`, `<th>Naturaleza</th>`
  inline) marcados skip documentado: reemplazados por la migracion
  FASE 5-BIS (Tabulator -> django-tables2+HTMX).
- **`facturas`:** `content_type` de XML nunca incluye `charset=utf-8`;
  204 No Content no lleva body (RFC 7231); detalle de factura expone
  metadatos (`has_ubl_xml`/`anexos_meta`), no XML crudo (FASE 6);
  mock de test apuntaba a un alias (`ingest_ubl_sync`) que produccion
  no usa (el real es `business_service.ingest_document`); `Empresa.nit`
  ahora requerido a nivel de modelo. Ademas: `async_mode` de
  `ingest_document()` (pipeline universal) documentado en su propio
  codigo como "FASE 5: placeholder para futuro" -- sin implementar,
  2 tests marcados skip en consecuencia. Un hallazgo de produccion (la
  rama activa del pipeline universal no capturaba excepciones de
  `ingest_document()`, solo la rama legacy inactiva lo hacia) se
  flageo aparte en vez de corregirse en esta pasada de saneamiento de
  tests -- corregido por separado en sesion independiente iniciada por
  el usuario a partir de esa sugerencia (`business_service.py`:
  try/except agregado alrededor de `ingest_document()`, retorna
  `{"error": "parse_error", ...}, 422`).
- Endpoint `factura-upload-ubl` (`POST /api/v1/facturas/upload-ubl/`,
  marcado `DEPRECATED` en su propio docstring desde antes de esta
  sesion) queda con cobertura parcial deliberadamente sin completar:
  decision ya documentada en sesion previa (F27/F28) de no invertir en
  un endpoint deprecado con cobertura de negocio real ya duplicada en
  otros archivos -- reconfirmada, no reabierta, en esta pasada.

34 archivos tocados (1 nuevo: `apps/tenant/core/tests/conftest.py`; 33
modificados, la gran mayoria tests, 2 de produccion en `proyectos`), 0
modelos nuevos, 0 migraciones. Detalle completo con evidencia
ANTES/DESPUES por app: `documentacion/F33.15_TESTING_EXECUTION_STATUS.md`.
Pendiente (fuera de esta sub-fase, per plan original): Nivel 4
(cross-cutting: `tests/api`, `tests/celery`, `tests/general`,
`tests/multitenant`, `tests/smoke`) y Nivel 5 (suite global 2064+ tests
como confirmacion final). Posterior a DOC-M38.

**Actualizacion previa:** 2026-08-16 (DOC-M38) — FASE 33 (Shared UI / Design
System), continua EN PROGRESO -- no cerrada, documentado con evidencia por
que. Cubre el cierre del Nivel 2 de la regresion incremental
(`apps/public/**`): 4 hallazgos reales corregidos con evidencia
(`PublicUserViewSet` sin `update()`/`destroy()` -> 500 en produccion;
prefijo de URL publico obsoleto en tests de `impuestos`; assertion
incorrecta sobre `FieldFile`; leak de `connection.schema_name` entre
tests por ser estado de sesion Postgres no transaccional). 61/61 tests
PASS en `accounts`/`core`/`impuestos`/`tenants`. Ademas, ante un nuevo
colapso total de Docker a mitad de sesion, se piloto con exito ejecucion
de pytest **local** (`venv/Scripts/python.exe` contra `db`/`redis`
dockerizados en `localhost`) por instruccion explicita del usuario,
confirmando viabilidad pero con ~9x mas lentitud que en contenedor.
Detalle completo: `documentacion/F33.15_TESTING_EXECUTION_STATUS.md`
§"F33.15-B Nivel 2 — `apps/public/**` por modulo: CERRADO". Posterior a
DOC-M37.

**Actualizacion previa:** 2026-08-16 (DOC-M37) — FASE 33 (Shared UI / Design
System), continua EN PROGRESO -- no cerrada, documentado con evidencia por
que. Cubre la auditoria directa del entorno Docker/WSL2 (F33.15-B, a
peticion explicita del usuario): diagnostico completo (ausencia de
`.wslconfig`, memoria dinamica de WSL2 hasta 50% de 11.8GB RAM total del
host, disco virtual sin compactacion automatica) + correccion real
aplicada (`.wslconfig` con memoria/CPU fijos, `sparseVhd`,
`autoMemoryReclaim`) + resultado: mejora parcial verificada (el motor ya
no colapsa siempre por completo), causa de fondo (inestabilidad
intermitente bajo I/O especifico de `TenantTestCase`) no eliminada.
Detalle completo: `documentacion/F33.15_TESTING_EXECUTION_STATUS.md`
§"F33.15-B — Auditoria del entorno Docker/WSL2: cierre consolidado".
Posterior a DOC-M36.

**F33.15-B (auditoria de entorno):** el usuario pidio explicitamente
"revisa el entorno docker audita y corrige" tras varios colapsos
recurrentes del motor de Docker Desktop durante la regresion de
`ConsoleBusinessLogicTests`. Auditoria directa (PowerShell, fuera de
los contenedores) encontro: **no existia `C:\Users\steve\.wslconfig`**
-- WSL2 operaba con limites dinamicos por defecto (memoria hasta 50%
de los 11.8GB de RAM total del host, coincide exactamente con el
`Total Memory: 5.692GiB` visto en `docker info` en diagnosticos
previos), sin `swap` explicito ni compactacion de disco virtual
(`docker_data.vhdx`, 15.35GB, sin `sparseVhd`). Espacio en disco de
Windows (134.92GB libres) descartado como causa. Exclusiones de
Windows Defender no verificables (requiere admin, fuera del alcance de
esta sesion) -- permanece como hipotesis no descartada.

**Correccion aplicada** (archivo de perfil de usuario, fuera del repo
git, no commiteable): `.wslconfig` con `memory=4GB`, `processors=6`,
`swap=2GB`, `sparseVhd=true`, `autoMemoryReclaim=gradual`. Verificado
con `docker info`: `CPUs: 6, Total Memory: 3.824GiB` tras aplicar con
`wsl --shutdown`.

**Resultado:** mejora real observada -- los colapsos posteriores dejaron
de ser SIEMPRE totales (antes tumbaban `db`/`redis`/`web` simultaneamente;
despues, en varios intentos, solo `web` se reinicio, o hubo corridas
exitosas completas verificadas, p.ej. un test de 156.49s con Docker
permaneciendo sano 44+ minutos). **La causa de fondo no se elimino por
completo**: `ConsoleBusinessLogicTests` siguio sin completarse de forma
confiable en intentos posteriores. Se descartaron 2 hipotesis
especificas por evidencia directa (mock mal dirigido -- el import es
local y se resuelve tras el patch, deberia funcionar; cold-start del
framework compartido en una misma sesion de pytest -- no lo evito, y
se identifico que cada invocacion de `pytest` es un proceso Python
nuevo que no comparte estado de "warmup" con invocaciones anteriores).

**Recomendaciones para el usuario** (fuera del alcance de esta
sesion): verificar/agregar exclusiones de Windows Defender para rutas
de Docker/WSL2 (requiere admin); considerar subir `memory=4GB` a `6GB`
si el uso del host lo permite; evaluar migrar los casos de
`TenantTestCase` que no requieren un schema real (servicios mockeados,
aserciones de permisos) a `TestCase` simple, reduciendo la superficie
de operaciones DDL costosas; reconsiderar si 11.8GB de RAM total es
suficiente para el flujo de trabajo completo de desarrollo.

**Actualizacion previa:** 2026-08-14 (DOC-M36) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre la mision autonoma de saneamiento de F33.15
(Testing): 3 bugs reales corregidos con evidencia (context processor
crasheando vistas del schema publico, provisioning innecesario de 30
schemas en un test, drift de aserciones de paginacion), 41 tests de
`console/` confirmados PASS, y un `BLOCKED_SAFE` real de entorno
documentado (2
reinicios automaticos de Docker, 1 con SIGKILL) que detiene la
continuacion de regresion pesada en esta sesion. Detalle completo:
`documentacion/F33.15_TESTING_EXECUTION_STATUS.md`. Posterior a DOC-M35.

**F33.15 (continuacion, mision autonoma):** siguiendo el punto de
partida dejado en DOC-M34 (causa raiz de `ConsoleAPIConsumptionTests`
sin resolver), se aplicaron 3 fixes independientes, cada uno medido e
investigado por separado (regla "no asumir causa unica"):

1. **`apps/tenant/core/context_processors.py`** -- `contexto_organizacional`
   esta registrado globalmente (unica config `TEMPLATES`), tambien se
   ejecuta en vistas del schema publico. `perfil.TenantProfile` esta en
   `TENANT_APPS` -- su tabla no existe en publico, y `user.tenant_profile`
   ahi lanzaba `ProgrammingError` real (no un `DoesNotExist` capturable),
   crasheando con 500 cualquier vista publica para un staff autenticado
   -- **bug de produccion real, no solo de tests**. Fix: guard con
   `connection.schema_name == get_public_schema_name()`. Resuelve los 5
   fallos de `ConsoleIsolationAndPermissionsTests` documentados en
   DOC-M34.

2. **`apps/public/console/tests/test_legacy_public_tenants_api.py`**
   (`ConsoleAPIConsumptionTests`) -- `test_tenants_api_pagination_follows_standard`
   creaba 30 tenants reales en un loop (`~79s/tenant` medido,
   `CREATE SCHEMA` + migraciones completas via `TenantMixin.save()`) --
   causa real del "cuelgue indefinido" observado en sesiones previas
   (mis propios timeouts cortaban el proceso a mitad de un
   `CREATE SCHEMA`, degradando Docker en la siguiente corrida). Fix:
   `.create()` en loop -> `.bulk_create()` (el endpoint probado solo lee
   filas de la tabla publica, no requiere schemas reales).

3. **Mismo archivo** -- al acelerar el test lo suficiente para que
   terminara, revelo un `AssertionError` real: el test asumia
   `page_size=25`/`max_page_size=100`, pero
   `apps/config/api/pagination.py::StandardResultsSetPagination` usa
   `20`/`200` -- drift nunca detectado porque el test jamas llegaba a
   ejecutar la aserción. Fix: docstring + asserts corregidos.

**Regresion confirmada:** `ConsoleIsolationAndPermissionsTests` (5/5),
`ConsoleAPIConsumptionTests` (6/6), `test_api_views.py` (34/34) -- 41
tests. `manage.py check` + governance PASS tras cada fix.

**`BLOCKED_SAFE` real, no fabricado como PASS:** al continuar hacia
`ConsoleBusinessLogicTests` (test ligero, mockeado, confirmado por
lectura de codigo que no es el causante), el contenedor `web` se
reinicio automaticamente 2 veces, la 2a con `exit: 137` (SIGKILL) sin
producir ningun output de pytest. `docker stats` en reposo: ~440MiB de
5.69GiB, sin evidencia de leak persistente -- patron de inestabilidad
intermitente del backend Docker Desktop/WSL2 bajo carga acumulada tras
horas de sesion continua, no un problema de codigo. Regla aplicada:
"maximo 1 reinicio por problema ambiental, no restart loop" -- se
detiene la ejecucion de mas suites pesadas en esta sesion. Pendiente:
`ConsoleBusinessLogicTests`, `ConsoleIntegrationTests`,
`ConsoleLegalDataTests`, `test_views.py`, regresion del resto de la
suite (2064 tests), F33.16 (E2E), F33.18 (Responsive), F33.19
(Performance), Release Gate -- todos requieren Docker estable,
recomendado reiniciar Docker Desktop/maquina host fuera de esta sesion.

**Actualizacion previa:** 2026-08-14 (DOC-M35) — FASE 33 (Shared UI / Design
System), continua EN PROGRESO -- no cerrada, documentado con evidencia por
que. Cubre F33.17 (Accesibilidad, primera pasada sobre componentes
modificados): 3 hallazgos reales corregidos en los primitivos Shared UI
(`aria-hidden` en iconos decorativos de `kpi_card.html`/`empty_state.html`,
`aria-label` en el boton icon-only de `filter_bar.html`), 0 hallazgos en
el modal/offcanvas/formularios revisados (ya delegan correctamente en
Bootstrap/SweetAlert2 nativos o ya tienen labels asociados). Cambios de
solo atributos ARIA, sin impacto visual ni funcional, verificados con
`Template().render()` + `manage.py check` + governance. Posterior a
DOC-M34.

**F33.17** (Accesibilidad, componentes modificados -- no un WCAG audit
completo): auditoria por lectura de codigo de `UIManager.confirm()`
(SweetAlert2, maneja foco/ARIA nativamente -- sin cambios),
`mostrarOffcanvasSeguro` (delega en `bootstrap.Offcanvas` nativo -- sin
cambios), un formulario offcanvas muestreado (`offcanvas_crear_cliente.html`,
12/12 inputs con `<label for="id">` correctamente asociado -- sin
cambios), y los 4 primitivos Shared UI de F33.6/F33.8/F33.9. Hallazgos
reales corregidos en 3 de los 4: `kpi_card.html`/`empty_state.html`
tenian un icono decorativo (`<i class="bi bi-...">`) sin
`aria-hidden="true"`; `filter_bar.html` tenia un boton de busqueda
icon-only dependiendo solo de `title="Buscar"` (no un sustituto
confiable de nombre accesible, WCAG 4.1.2) -- se agrego `aria-label`
explicito. `loading_state.html` ya seguia el patron correcto
(`role="status"` + `span.visually-hidden`), sin cambios. Los 3 fixes se
propagan automaticamente a las adopciones ya hechas (12+ sitios entre
Card KPI, Empty State y Filter Bar). **No cubierto en esta pasada:**
contraste de color real (solo inspeccion de clases, no medicion),
navegacion por teclado end-to-end, headers de tablas django-tables2.

**Actualizacion previa:** 2026-08-14 (DOC-M34) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.15 (Testing): coleccion de la suite
confirmada en 2064/0 errores, marker `pytest.mark.e2e` registrado, y un
hallazgo real de entorno documentado en detalle -- el motor de Docker
Desktop colapso
repetidamente al intentar correr la suite completa, causa raiz aislada
por lectura de codigo a `ConsoleAPIConsumptionTests` (creacion real de 2
tenants/schemas Postgres por test en `setUp()`) mas 5 tests que fallan
de forma genuina en `ConsoleIsolationAndPermissionsTests`. F33.15 queda
**PARCIAL**, no completada -- ver `F33_STATUS_REPORT.md` §F33.15 para el
diagnostico completo. Posterior a DOC-M33.

**F33.15** (Testing, consolidacion de la suite existente): `pytest
--collect-only` confirma **2064 tests, 0 errores de coleccion**,
verificando que ningun cambio de F33.13/F33.14 (frontend puro) rompio
la coleccion. Se registro el marker `e2e` (usado sin declarar en
`tests/e2e/test_workspace_facturas_forensics.py`, generaba
`PytestUnknownMarkWarning`) en `pytest.ini`.

**Bloqueo real de entorno, no de codigo:** la corrida completa de
`pytest` (2064 tests) no se pudo completar de forma confiable -- el
motor de Docker Desktop (backend WSL2) colapso repetidamente
(`500 Internal Server Error`, contenedores forzados a reiniciar) en 4+
intentos sucesivos, incluso tras descartar falta de memoria (se
detuvieron `neo4j`/`cloudflared`, sin cambio en el patron) y
acumulacion de schemas huerfanos (verificado con SQL directo: solo 3
schemas no-publicos en la base). Una corrida en modo verbose, matada
manualmente tras confirmar que el corte real ocurria en
`apps/public/console/tests/test_legacy_public_tenants_api.py`, aislo la
causa mas probable: `ConsoleAPIConsumptionTests.setUp()` crea 2 tenants
reales (`TenantClient.objects.create(...)`) por cada test -- operacion
DDL pesada (`CREATE SCHEMA` + migraciones completas) que se degrada bajo
la inestabilidad de I/O que el propio entorno ya arrastraba. La misma
corrida tambien confirmo, por ejecucion completa (no interrumpida), **5
fallos genuinos** en `ConsoleIsolationAndPermissionsTests` -- lectura de
`config/urls_public.py` (lineas 107-108) senala un posible conflicto de
enrutamiento (`console/urls.py` registra su propia ruta `impuestos/`
que shadowea `path('console/impuestos/', include('apps.public.impuestos.dashboard.urls_dashboard'))`)
como hipotesis no verificada por ejecucion.

**No se sigue reintentando la ejecucion masiva en esta sesion** --
instruccion explicita del usuario tras el patron de cuelgues repetidos:
documentar el hallazgo y continuar, no esperar indefinidamente una
respuesta que no llega. Detalle completo, incluyendo la ruta
recomendada para quien retome la investigacion (aislar
`ConsoleAPIConsumptionTests` en un entorno Docker sano con `-x` y
timeout largo): `documentacion/F33_STATUS_REPORT.md` §F33.15.

**Actualizacion previa:** 2026-08-14 (DOC-M33) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.14-E: auditoria evidence-based de Badges
de Estado (cierre del Batch 8, 0 migraciones -- no existe primitivo
previo y el unico candidato real tiene 3 variantes de color
inconsistentes), posterior a DOC-M32. **Cierra formalmente los "Batches
6-9" (Shared UI adoption)** del roadmap: F33.14-A a F33.14-E completos,
8 archivos/12 sitios migrados en
total, siguiente paso F33.15 (Testing).

**F33.14-E** (Badges de estado, cierre de Batch 8): auditoria de **179
metodos `render_*`** en los 13 `tables.py` de las apps tenant
(django-tables2, Fase 5-BIS). A diferencia de F33.14-A/B/C/D, no existe
ningun primitivo de badge compartido hoy (`sintel_ui.py` solo lo
menciona en un comentario docstring, sin `inclusion_tag` real) -- la
pregunta no es "adoptar un target ya construido", es "¿hay evidencia
suficiente para crear uno nuevo?".

**Hallazgo real, no migrado:** el patron booleano `render_activo`/
`render_activa` ("Activo"/"Inactivo") se repite en **7-8 sitios de 5
apps** (`clientes`, `contabilidad` x2, `empresa`, `inventario` x3,
`proveedores`) pero con **3 combinaciones de color inconsistentes para
"Inactivo"**: `bg-danger` (2 sitios), `bg-secondary` (5 sitios),
`bg-secondary-subtle`+borde (1 sitio) -- incluso **dentro de la misma
app** (`contabilidad` tiene `render_activa` con `bg-secondary` en un
metodo y `render_activo` con `bg-danger` en otro; `inventario` tiene 3
sitios con 2 estilos distintos entre si). Unificar mecanicamente
elegiria un color sin base de diseno -- requiere decision explicita
antes de crear cualquier helper compartido.

**Resto de badges (~50 sitios), confirmado NO duplicacion:** mapeos de
estado genuinamente especificos de cada dominio (`_BADGE_DIAN` en
facturas, `_BADGE_ESTADO` en ventas/compras/proyectos,
`_BADGE_TIPO_CUENTA`/`_BADGE_ESTADO_PERIODO`/`_BADGE_ESTADO_ASIENTO`/
`_BADGE_TIPO_RETENCION`/`_BADGE_TIPO_PLANTILLA` en contabilidad,
`_BADGE_ESTADO_EMPLEADO`/`_BADGE_TIPO_CONTRATO`/`_BADGE_ESTADO_CONTRATO`
en empleados, etc.) -- cada enum es distinto, cada combinacion de
icono+color es distinta, la estructura HTML difiere (algunos con `<i
class="bi ...">`, algunos con `badge-sm`, otros con `px-2 py-1`).
Confirma con lectura real de codigo la conclusion original documentada
en el batch 8 de `F33_APP_EXPANSION_MATRIX.md`.

**0 archivos de codigo modificados en esta sub-fase** -- crear un
primitivo de badge nuevo sin decision de diseno previa violaria la
prohibicion explicita de la mision F33 ("no crear mas infraestructura...
no UniversalComponent"). Detalle completo:
`documentacion/F33_14E_BADGES_ESTADO_INVENTORY.md`. Sin cambios de
codigo, no aplica ciclo `manage.py check`/governance/E2E.

**Actualizacion previa:** 2026-08-14 (DOC-M32) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.14-D: inventario evidence-based de
Filter/Search Bar en las apps tenant + adopcion controlada (2 archivos
migrados, 3 sitios), posterior a DOC-M31.

**F33.14-D** (Filter/search bar, mismo rigor que F33.14-A/B/C): auditoria
de **21 candidatos** (`keyup changed delay:400ms`) en las apps tenant.
Clasificacion: `SHARED_CANDIDATE`=2 (3 sitios), `DUPLICATE`=8 (2
sub-familias reales, 10 sitios), `KEEP` (patron "input bare", sin
wrapper ni boton)=13 (19 sitios). Detalle completo:
`documentacion/F33_14D_FILTER_BAR_INVENTORY.md`.

**Migrado:** `compras/compras_list.html` (1/1 sitio) y
`gastos/gastos_list.html` (2/2 sitios) -- los 3 eran el markup
byte-identico al target `filter_bar.html` (`input-group input-group-sm
w-auto` + `data-search-input`/`data-module` + boton
`data-action="search"`, creado en F33.8 pero sin consumidores hasta
ahora). La URL de cada boton se resuelve con `{% url ... as var %}`
(mismo patron ya usado en `empleados/partials/tabla_liquidacion_detalle.html`)
y se pasa como `search_url` al `{% include %}` -- misma resolucion de
URL que la version inline anterior, sin cambio de comportamiento.
Verificado con `Template().render()` (estructura byte-identica con una
URL de prueba; la resolucion real de `{% url %}` requiere contexto de
tenant/schema no disponible en un shell aislado).

**No migrado, con evidencia real:** una familia consistente de 4
archivos "icono-prefijo, sin boton" (`clientes/clientes_list.html`,
`proyectos/proyectos_list.html`, `ventas/list_ventas.html`,
`facturas/list_factura.html`) -- `input-group-text` con icono ANTES del
input en vez de un boton DESPUES, casi siempre con `hx-include` para
combinar con filtros activos por pestaña/estado; es la candidata mas
fuerte para una 2a variante del primitivo, pero requiere decision de
diseno explicita. `bancos/list_bancos.html` (2 sitios) tiene el wrapper
correcto pero **no tiene boton de busqueda en absoluto**. 
`proveedores/proveedores_list.html` (2 sitios) tiene wrapper y boton,
pero el boton dispara su propio `hx-get`+`hx-include` autosuficiente en
vez del handler JS `data-action="search"` del target. 13 archivos
(`contabilidad` x5, `empleados` x5 sitios, `empresa` x2 archivos,
`perfil`, `inventario` x4) usan un input `form-control` bare sin
wrapper `input-group` ni boton -- migrarlos anadiria elementos de UI que
hoy no existen, cambio de diseno real en 13 archivos, fuera del alcance
de "adopcion controlada".

`manage.py check` PASS, governance FINAL STATUS PASS. E2E: mismo
hallazgo de carrera de arranque del contenedor `web` que F33.14-C (la
primera verificacion post-restart con `manage.py check` via `docker
compose exec` no prueba que el puerto 8000 este escuchando en red) --
esta vez detectado y corregido ANTES de correr el suite completo
(esperando a que `curl` devolviera 200 en
`/static/tenant/core/auth/login.html`): **29/29 PASS** (4.7m), sin
fallos intermedios.

**Actualizacion previa:** 2026-08-14 (DOC-M31) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.14-C: inventario evidence-based de Loading
States en las apps tenant + adopcion controlada (2 archivos migrados, 3
sitios), posterior a DOC-M30.

**F33.14-C** (Loading states, mismo rigor que F33.14-A/B): auditoria de
**17 candidatos** (`spinner-border`) en las apps tenant. Clasificacion:
`SHARED_CANDIDATE`=2 (3 sitios), `DUPLICATE`=5 (2 sub-familias reales, 7
sitios), `KEEP` (spinner inline de boton/celda, no panel)=8 (15 sitios),
`KEEP` (overlay global)=2 (2 sitios). Detalle completo:
`documentacion/F33_14C_LOADING_STATE_INVENTORY.md`.

**Migrado:** `gastos/gastos_list.html` (2/2 sitios: paneles "gastos" y
"resoluciones") y `compras/compras_list.html` (1/1 sitio: panel "ordenes
de compra") -- los 3 eran el contenido inicial byte-identico de un panel
`hx-trigger="load"`, mismo caso de uso del partial `loading_state.html`
(creado en F33.6). Verificado con `Template().render()` antes de aplicar.

**No migrado, con evidencia real:** una familia "compacta py-4" con 2
sub-variantes internas inconsistentes entre si (`spinner-border-sm` +
`<span>` vs `spinner-border` normal + `<p>`) repetida en
`clientes/offcanvas_detalle_cliente.html` y `facturas/list_factura.html`
(x2) + `facturas/offcanvas_pendientes_factura.html` -- mismo patron de
inconsistencia interna que F33.14-B encontro en `proveedores`. Un
spinner JS-toggled por `data-spinner` con color propio en
`clientes/clientes_list.html` (mecanismo distinto al del target, mismo
tipo de hallazgo que el `data-empty-state` de F33.14-B). Un near-miss de
un solo sitio en `contabilidad/reporte_page.html` (le falta
`role="status"` + `span.visually-hidden`; migrarlo seria a la vez un
cambio visual -- quitar `text-primary opacity-50` -- y una mejora de
accesibilidad no solicitada). 8 archivos con spinners inline de
boton/celda de tabla (estado de envio de formulario via `innerHTML` de
JS, no el contenido inicial de un panel) en `contabilidad` y `empleados`.
2 overlays globales (`core/workspace.html`, indicador HTMX de toda la
app; `cotizaciones/editor_cotizacion.html`, overlay de pantalla completa
del editor) -- patron estructuralmente distinto, sin `entity` ni
contenedor de panel.

`manage.py check` PASS, governance FINAL STATUS PASS. E2E: la primera
corrida (post-reinicio preventivo del contenedor `web`) arrojo 18 fallos
`net::ERR_CONNECTION_REFUSED` -- el puerto 8000 aun no aceptaba
conexiones de red pese a que `manage.py check` via `docker compose exec`
ya habia pasado (ese comando corre dentro del contenedor, no prueba que
el servidor este escuchando en el puerto mapeado). Confirmado como
carrera de arranque del contenedor, no una regresion del cambio: los 11
tests que si alcanzaron a correr en esa misma corrida pasaron. Verificado
el puerto activo (`curl` 200 en `/static/tenant/core/auth/login.html`)
antes de re-correr: **29/29 PASS** (4.4m).

**Actualizacion previa:** 2026-08-14 (DOC-M30) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.14-B: inventario evidence-based de Empty
State en las 17 apps tenant + adopcion controlada (1 archivo migrado, 1
codigo muerto eliminado), posterior a DOC-M29.

**F33.14-B** (Empty State, mismo rigor que F33.14-A): auditoria de **8
candidatos** en las 17 apps tenant. Clasificacion: `SHARED_CANDIDATE`=1,
`DUPLICATE`=4 (2 sub-variantes reales), `KEEP`=2 (patron tabla `{% empty
%}`, estructuralmente incompatible), `OBSOLETE`=1. Detalle completo:
`documentacion/F33_14B_EMPTY_STATE_INVENTORY.md`.

**Migrado:** `clientes/clientes_list.html` (2/2 sitios,
`data-empty-state="contactos"`/`"cartera"`) -- markup byte-identico al
target, toggle JS por selector de atributo sin cambios. Verificado con
`Template().render()` antes de aplicar.

**Hallazgo colateral (codigo muerto, no una migracion):**
`clientes/contactos_list.html` resulto tener **0 referencias en todo el
repo** (ni `{% include %}`, ni vista Python) -- eliminado con evidencia,
no migrado.

**No migrado, con evidencia real (mismo patron que F33.14-A):** una
sub-variante "compacta" (`id` en vez de `data-attr`, tamano reducido)
aparece identica en `clientes/offcanvas_detalle_cliente.html` y
`proveedores/offcanvas_form.html`. Ademas, **`proveedores` tiene 2
archivos para el mismo concepto ("representantes") con 2 estilos de
empty-state `alert-info` que ni siquiera coinciden entre si**
(`representantes_directory.html` usa `bi-inbox`+parrafo separado,
`list_representantes.html` usa `bi-info-circle`+texto inline) -- una
inconsistencia real dentro de la propia app, documentada, no resuelta en
esta pasada. `bancos/offcanvas_detalle_extracto.html` y
`facturas/offcanvas_editar_factura.html` usan la clausula `{% empty %}`
de Django dentro de una fila de tabla (`<tr><td colspan="N">`) --
estructuralmente incompatible con el primitivo basado en `<div>`, no es
la misma duplicacion.

`manage.py check` PASS, governance FINAL STATUS PASS, E2E **29/29 PASS**
(contenedor `web` reiniciado preventivamente, limpio en el primer
intento).

**Actualizacion previa:** 2026-08-14 (DOC-M29) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.14-A: inventario evidence-based de Card
KPI en las 17 apps tenant + adopcion controlada (2 archivos migrados),
posterior a DOC-M28.

**F33.14-A** (Card KPI, inventario ANTES de tocar codigo -- regla
explicita de la mision): auditoria en 3 pasadas de precision creciente
sobre `apps/tenant/**/*.html` encontro **16 candidatos** (no los 7 que
declaraba el inventario original de F33.0). Clasificacion:
`SHARED_CANDIDATE`=3, `APP_SPECIFIC`=3, `DUPLICATE`=6, `KEEP`=4 (falsos
positivos -- circulos de avatar/foto, no metricas). Detalle completo:
`documentacion/F33_14A_CARD_KPI_INVENTORY.md`.

**Correccion real al inventario de F33.0:** de los "7 sitios copiados
verbatim" que F33.0 declaraba, la lectura completa de cada archivo
(no solo el grep de la firma superficial) encontro que **solo 3 son
realmente byte-identicos** al target `sintel_kpi_card` -- `clientes`,
`proyectos` (parcial) y `cotizaciones`. Los otros 4
(`ventas`/`gastos`/`facturas`) tienen personalizaciones visuales reales
(tamano de circulo distinto, acento de color de 3px, tipografia de
label en mayusculas, tamanos de fuente mixtos) que el grep original no
distinguio -- migrarlos habria violado la regla explicita del propio
`sintel_ui.py`: "no se cambia ningun pixel de lo que ya funciona".
`cotizaciones`, aunque byte-identico en markup, actualiza sus valores
por JavaScript via `id=` (`cotizaciones.table.js`) -- el primitivo
actual no acepta un parametro `id`, migrarlo habria roto el mecanismo
de actualizacion. Se encontraron ademas **2 implementaciones de KPI
card completamente independientes**, no detectadas en F33.0
(`compras/partials/tabla_compras.html`, estilo plano sin icono;
`inventario/partials/{tabla_activos,tabla_productos}.html`, estilo
"chip compacto" duplicado dos veces dentro de la misma app).

**Migrado (verificado sin riesgo):**
`clientes/partials/tabla_clientes.html` (6/6 cards) y
`proyectos/partials/tabla_proyectos.html` (4/6 cards -- las 2 restantes,
"Avance Prom." con color `purple` no estandar y "Cartera Total" con
font-size custom para un valor monetario largo, se dejan intactas por
ser personalizacion real). Verificado con `Template().render()` antes
de aplicar a los templates: output byte-identico al markup original.
`manage.py check` PASS, governance FINAL STATUS PASS, E2E **29/29 PASS**
(contenedor `web` reiniciado preventivamente, limpio en el primer
intento).

**Actualizacion previa:** 2026-08-14 (DOC-M28) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.13-B: cierre completo de `confirm()`
nativo en todo `apps/tenant/**` (bancos + un gap real detectado en el
grep de batch 5), posterior a DOC-M27.

**F33.13-B** (cierre de `confirm()` nativo, prioridad explicita:
auditoria completa antes de tocar codigo): `bancos.main.js` -- unico
sitio identificado como "modal-integrado" (batch 5 lo habia diferido
deliberadamente) -- se investigo primero quien abre el modal
(`confirmarEliminacion`), quien lo cierra (`ejecutarEliminacion` + boton
Cancelar nativo), sus consumidores externos (ninguno, confirmado por
grep repo-wide) y si era migrable al patron Core (si -- sin
comportamiento especifico de dominio bancario). Migrado a
`UIManager.confirm()`; el modal Bootstrap hand-rolled completo
(`#confirmarEliminarModalBancos`) eliminado de `list_bancos.html`.

**Hallazgo real durante la verificacion final (no en el codigo de
bancos, en la propia auditoria previa):** el grep usado en batch 5
(`confirm(['"]`, solo strings literales) tenia un gap -- no detectaba
`confirm(unaVariable)`. Un grep mas amplio encontro **3 sitios
adicionales no migrados**: `inventario/inventario_list.js`,
`inventario/movimientos_list.js`, `inventario/productos_list.js`.
Migrados los tres (ya en funciones/listeners `async`, swap directo). El
spec E2E `20-inventario-productos-crud.spec.js` (dependiente de
`page.once('dialog', ...)` para `productos_list.js`) se corrigio con el
mismo patron `.swal2-confirm` ya usado en batch 5 parte 2.

**Verificacion final repo-wide: 0 llamadas a `confirm()` nativo
restantes en todo `apps/tenant/**` (confirmado por grep), 0 specs E2E
dependientes del evento `dialog` de Playwright.** `manage.py check`
PASS, governance FINAL STATUS PASS, E2E **29/29 PASS** (contenedor `web`
reiniciado preventivamente antes de la corrida, limpio en el primer
intento -- incluye `63-f3310-empresa-pilot.spec.js`, flaky en corridas
anteriores de esta sesion, verde esta vez).

**Fuera de este cierre, documentado como trabajo futuro:**
`empleados_list.html`/`empleado_list.js` -- modal hand-rolled hermano al
de bancos, pero sin fallback `confirm()` nativo (su modal se abre
directamente sin condicional), por lo que nunca aparecio en ningun grep
de `confirm()` y no formaba parte de "cerrar el ultimo confirm()".
Tambien se flageo (sin investigar en esta pasada) una duplicacion real
entre `inventario_list.js` y `productos_list.js` -- misma logica de
eliminar-producto casi identica, ambos archivos vivos.

**Actualizacion previa:** 2026-08-14 (DOC-M27) — FASE 33 (Shared UI /
Design System), continua EN PROGRESO -- no cerrada, documentado con
evidencia por que. Cubre F33.13 batch 5 parte 2 (27 sitios adicionales
de `confirm()` nativo migrados) mas un hallazgo real de E2E encontrado y
corregido en el proceso, posterior a DOC-M26.

**F33.13 batch 5, parte 2** (confirm() nativo -> `UIManager.confirm()`,
resto de sitios aislados): migrados **27 sitios en 25 archivos, 8 apps**
(clientes, empleados, empresa, contabilidad, proyectos, proveedores,
inventario, facturas). Cada sitio auditado individualmente contra uso de
`bootstrap.Modal` antes de tocarlo (regla explicita: `confirm()` aislado
se reemplaza mecanicamente, `confirm()` integrado en modal vivo requiere
auditoria propia) -- ningun archivo de este batch resulto tener el
patron modal-integrado. `bancos.main.js:138` queda como **unico sitio de
`confirm()` nativo restante en todo `apps/tenant/**`**, confirmado
deliberadamente diferido (fallback de un modal Bootstrap hand-rolled
vivo, hallazgo #5c del inventario F33.0, requiere retirar el modal HTML
completo, no un swap de linea).

**Hallazgo real durante la verificacion (no ambiental, no cosmetico):**
2 specs E2E existentes (`10-clientes-crud.spec.js`,
`30-contabilidad-cuenta-crud.spec.js`) dependian de
`page.once('dialog', (dialog) => dialog.accept())` -- el patron de
Playwright para `window.confirm()` **nativo**. `UIManager.confirm()`
renderiza un modal SweetAlert2 real (DOM), no dispara el evento
`dialog` del navegador -- el handler quedaba inerte y el flujo de
eliminar nunca se completaba en el test (la fila permanecia visible tras
"eliminar"). Corregido en los 2 specs (clic real sobre `.swal2-confirm`
tras el boton eliminar), no en el codigo de produccion -- el
comportamiento nuevo es correcto/mejorado, el test asumia el mecanismo
viejo. Verificado que ningun otro spec comparte el patron contra un
archivo de este batch (`20-inventario-productos-crud.spec.js` usa el
mismo handler pero contra `productos_list.js`, no tocado, sigue
correcto).

Verificacion: `manage.py check` PASS, governance FINAL STATUS PASS. E2E:
2 corridas intermedias con fallos masivos (10 y 26 fallos) se
investigaron y confirmaron `AnonRateThrottle` agotado -- error `429`
literal en el texto de fallo de Playwright, mismo patron ya documentado
en el batch 2; el contenedor `web` se reinicio 2 veces mas en el proceso
para limpiar el cache en memoria (`LocMemCache`, no destructivo). Corrida
limpia final: **28/29 PASS** -- el unico fallo restante
(`63-f3310-empresa-pilot.spec.js`) es la flakiness de login()
pre-existente ya documentada en el propio comentario de
`tests/e2e/specs/_helpers.js`, no relacionada con este batch. Los 2
specs objetivo de la correccion pasaron limpiamente. Detalle completo:
`documentacion/F33_APP_EXPANSION_MATRIX.md`, `F33_STATUS_REPORT.md`.

**Actualizacion previa:** 2026-08-14 (DOC-M26) — FASE 33 (Shared UI / Design
System), continua EN PROGRESO -- no cerrada, documentado con evidencia por
que. Cubre F33.13 (expansion controlada, batches 1/2/4/5-parte1) y F33-R
(revalidacion y reconciliacion formal), ambas posteriores a DOC-M25.

**F33-R (revalidacion):** auditoria evidence-based (codigo/git/tests
reales, no solo documentacion) del estado real de F33.13+ contra lo
declarado en DOC-M25. Resultado: **F33-R = PASS** (auditoria completada
sin bloqueos), **F33 = IN_PROGRESS sin cambio** (Resultado B,
implementacion parcial confirmada por evidencia -- ni COMPLETED por
evidencia insuficiente en 8/29 items del release gate, ni FAIL porque
nada esta roto). Unico hallazgo real: discrepancia documental de conteo
(el batch 1 de F33.13 declaraba "13 archivos", `git show --stat`
confirma 11) -- corregida. `pytest --collect-only` ejecutado por primera
vez tras F33.13 (2064 tests, 0 errores de coleccion). Detalle completo:
`documentacion/F33R_EXECUTION_STATUS.md`, `F33R_FINAL_REPORT.md`,
`F33_RECONCILIATION_MATRIX.md`.

**F33.13 (expansion controlada, 4 batches ejecutados sobre el piloto
`empresa` de DOC-M25):**
- **Batch 1** (Offcanvas #12c/#12d restante): 11 archivos en 6 apps
  (perfil, compras, gastos, facturas, contabilidad x6, inventario)
  consolidados sobre `Sintel.Core.mostrarOffcanvasSeguro`, mismo patron
  del piloto. `empleados/devengo_editor.js` investigado y **revertido**
  tras detectar que su `setTimeout(0)` es un workaround deliberado (ya
  documentado en F31.2) a un bug real de timing de Bootstrap, no
  duplicacion evitable -- correccion de un error propio detectado a
  mitad de batch, no solo del codigo preexistente.
- **Batch 2** (codigo muerto con evidencia): 6 archivos eliminados -- 2
  modals de confirmar-eliminar sin consumidores JS (compras, gastos) + 4
  de 5 prototipos Tailwind huerfanos (`core/static/tenant/core/
  {contabilidad,empresa,perfil,facturas}/index.html`; el 5o,
  `dashboard/index.html`, se dejo intacto por estar alcanzado por
  trafico real via el redirect post-login).
- **Batch 4** (`ModalService`, diferido en el batch 2 por su carga
  global): eliminado tras confirmar 0 consumidores reales (grep +
  `tools/ekg/impact.py`), su `<script>` tag y documentacion obsoleta.
- **Batch 5, parte 1** (confirm() nativo -> `UIManager.confirm()`,
  subconjunto de menor riesgo): migrados los 2 unicos sitios donde toda
  la superficie de `confirm()` nativo de la app vive en un solo
  archivo/funcion (`ventas/resolucion_editor.js`, `perfil/
  perfil.modals.js`). `bancos.main.js` evaluado y diferido -- su
  `confirm()` es el fallback de un modal Bootstrap hand-rolled vivo
  (hallazgo #5c del inventario, mayor alcance que un simple swap).

Todos los batches verificados individualmente: `manage.py check` PASS,
governance FINAL STATUS PASS, E2E 29/29 (una corrida intermedia con 10
fallos durante el batch 2 se investigo -- `AnonRateThrottle` agotado tras
2 suites E2E seguidas en la misma sesion, confirmado por logs 429 del
contenedor `web`, no una regresion -- reinicio del contenedor limpio el
cache en memoria y la re-corrida confirmo 29/29).

**Pendiente, documentado con evidencia, no omision silenciosa:** batch
5b (~28 sitios de `confirm()` restantes en ~10 apps, incl. el patron
modal de bancos/empleados), batches 6-9 (adopcion de Card KPI/Empty
state/Badges/Filtros -- primitivas ya existen desde DOC-M25 pero
adopcion real = 0, requieren spot-check visual en navegador por app),
F33.15-19 (testing formal, accesibilidad, responsive, performance,
regresion final). Detalle completo:
`documentacion/F33_APP_EXPANSION_MATRIX.md`, `F33_STATUS_REPORT.md`.

**Actualizacion previa:** 2026-08-13 (DOC-M25) — FASE 33 (Shared UI / Design
System), EN PROGRESO -- no cerrada, documentado con evidencia por que.
F33.0-F33.1: inventario real de UI compartida en las 17 apps tenant (agente
de exploracion dedicado) mas clasificacion (SHARED_EXISTING/DUPLICATE/
APP_SPECIFIC/CANDIDATE_SHARED/OBSOLETE). Hallazgo principal: Offcanvas
tenia 2 helpers "safe" independientes con adopcion comparable (~25 vs ~22
archivos) -- la consolidacion de F31.2 habia quedado incompleta.
F33.2-F33.9: contrato de UI core diseñado deliberadamente minimo -- de 10
piezas conceptuales, 6 ya existian (Table=django-tables2, Notificaciones/
Confirm=UIManager, Offcanvas=mostrarOffcanvasSeguro) y no se creo
`window.Sintel.Core.UI` como namespace nuevo (seria indireccion sin valor);
las 4 restantes (Card KPI, EmptyState, Loading, Filtros) se implementaron
como primitivas Django server-side minimas, no componentes JS. F33.4:
consolidacion tecnica real de Offcanvas ejecutada -- `mostrarOffcanvasSeguro`
extendido con `{action:'show'|'hide'}` (retrocompatible), `UIManager.
handleOffcanvas` reducido a alias delgado que delega ahi. F33.10-11: piloto
ejecutado sobre `empresa` (elegido por evidencia, no preferencia) --
2 templates de modal confirmados muertos eliminados (una investigacion mas
profunda que la del inventario original reclasifico
`mailinbox_modals.html` de "vivo sin migrar" a "muerto": el flujo real ya
usa un offcanvas server-rendered completamente distinto), snippet de
fallback local reducido a un alias de una linea. Validado: `manage.py
check` PASS, governance FINAL STATUS PASS, **29/29 specs E2E PASS**
(incluye 2 nuevos: consolidacion de offcanvas + flujo real del piloto).
F33.12: impact analysis (`tools.ekg.impact`) corrido, con un hallazgo de
completitud del grafo documentado (no detecta cobertura de test real que
si existe). **F33.13 en adelante (expansion controlada a las otras ~13
apps con el mismo patron, accesibilidad, responsive, performance) NO se
ejecuto** -- decision de alcance explicita, no bloqueo: es del mismo orden
de magnitud que la expansion de 46 archivos de F32.7, no razonable de
comprimir en la cola de esta sesion sin repetir el mismo rigor de
verificacion individual por archivo. Detalle completo:
`documentacion/F33_SHARED_UI_INVENTORY.md`, `F33_CORE_UI_CONTRACT.md`,
`F33_STATUS_REPORT.md`.
**Actualizacion previa:** 2026-08-13 (DOC-M24) — FASE 32.9: revalidacion de
gobernanza y release gate de F32, con un metodo de busqueda deliberadamente
distinto al que F32.6/F32.7 usaron (`fetch()` nativo + `getHeaders()`
manual, no solo `window.http`/`w.http`) para comprobar contractualmente el
cierre, no volver a migrarlo. Encontro 2 hallazgos reales: una regresion
directa de F32.7 (`empleados/features/devengo_editor.js` referenciaba el
global `w.getCookie` que F32.7 elimino -- no rompia en produccion por un
fallback preexistente, pero era una referencia muerta; corregida a
`Sintel.Core.Http.csrf()`) y una violacion de contrato `*.api.js` nunca
detectada (`contabilidad/reporte/reporte.api.js` reimplementaba fetch+JWT
manual sin refresh, el mismo bug documentado en F32.1 para los 6 archivos
originales, en un 7o archivo que esa auditoria nunca alcanzo; migrado a
`Sintel.Core.Http`). Ambos corregidos y verificados (spec E2E nueva,
regresion completa 27/27, governance re-confirmado). Encontro tambien 10
archivos con el mismo patron de duplicacion (`getHeaders()`/`getCookie()`
propios + `fetch()` directo) que **no** se corrigieron -- documentados
como deuda preexistente DEFERRED, no un remanente a medio migrar (nunca
estuvieron en el alcance original de F32, corregirlos ahora habria sido
abrir una nueva ronda de migracion masiva). Release gate: **COMPLETED**
(`manage.py check`, `makemigrations --check`, `git diff --check`,
governance, contrato API/JWT/CSRF/FormData y validacion de navegador, todo
PASS). Detalle completo: `documentacion/F32_9_EXECUTION_STATUS.md`,
`F32_9_FINAL_REPORT.md`.
**Actualizacion previa:** 2026-08-13 (DOC-M23) — FASE 32: consolidacion del
transporte HTTP/CSRF/JWT del frontend tenant, cerrando el cluster de deuda
que F31 dejo explicitamente diferido (§5.2 mas abajo tiene el detalle
tecnico completo). F32.1-F32.5: auditoria exhaustiva (encontro 5
implementaciones HTTP reales, no las 3 asumidas originalmente, mas un bug
real de corrupcion silenciosa de `FormData` en la version "v3.4") y diseno
del contrato `Sintel.Core.Http` (F32.3), agregado de forma aditiva sin
tocar consumidores todavia (F32.4). F32.5 construyo infraestructura E2E
real desde cero en este entorno (sin acceso previo a browser automation
funcional ni credenciales) reutilizando un suite `@playwright/test`
existente pero nunca corrido, en vez de instalar herramientas redundantes
-- encontro y corrigio **6 bugs de produccion reales** en el proceso
(colision de IDs bancos/contabilidad, evento sin listener, WRONG_LOOKUP,
login flow real, etc). F32.6 migro los 6 `*.api.js` que reimplementaban
fetch+CSRF+JWT por su cuenta. F32.7 -- la fase con mayor desvio de alcance
real de la sesion -- descubrio en 3 pasadas de auditoria sucesivas
(cada grep "exhaustivo" previo resultaba insuficiente) que el patron
`window.http`/`w.http` (alias de `window` a `w` en la firma del IIFE,
extremadamente comun en este codebase) era la dependencia HTTP *de facto*
de casi todo el frontend tenant, no un residuo aislado: 46 archivos
adicionales en 10 apps. Migrados todos con el mismo patron mecanico
verificado por navegador real en cada lote; ambos duplicados de transporte
(`core/static/js/http.js` y `core/static/core/js/lib/http.js`) eliminados
tras confirmar cero consumidores vivos. F32.8 verifico con navegador real
los comportamientos cross-cutting (401 critico/no-critico, CSRF, JWT,
upload FormData) que ningun spec anterior probaba deliberadamente --
encontro y corrigio una carrera real en el propio arnes de pruebas
(bootstrap de sesion asincrono que enmascaraba la simulacion de sesion
expirada) y documento un hallazgo de UX menor (perdida del query param
`reason=401` en un redirect intermedio), sin corregirlo por estar fuera de
alcance de transporte. **Resultado: `Sintel.Core.Http` es el unico cliente
HTTP del frontend tenant.** Governance no re-verificado en esta pasada
(fase 100% frontend, sin cambios de modelos/servicios backend salvo el
hallazgo colateral de `ConfiguracionCotizacionViewSet` sin
`SintelDSVMixin`, flagged y corregido en sesion paralela, no por F32). 0
migraciones de base de datos. Detalle completo:
`documentacion/F32_1_2_TRANSPORT_AUDIT.md`, `F32_3_CORE_HTTP_CONTRACT.md`,
`F32_5_BROWSER_VALIDATION_STATUS.md`, `F32_6_TRANSPORT_MIGRATION_STATUS.md`,
`F32_7_TRANSPORT_CONSOLIDATION_AUDIT.md`, `F32_8_REGRESSION_MATRIX.md`.
**Actualizacion previa:** 2026-08-13 (DOC-M22) — FASE 31 (continuacion):
cierre de Grupo 2 (grillas residuales de Tabulator) mas un hallazgo
adicional. Antes de tocar Grupo 2, se encontro WIP huerfano sin commitear
en `empresa`/`proveedores`/`gastos`/`empleados` (mismo estilo y disciplina
que el resto de F31, de una sesion anterior) -- verificado exhaustivamente
(capa API sin cambios, `manage.py check`/`makemigrations` limpios, suite
completa de las 4 apps: 115/133 pasan, los 18 fallos confirmados
pre-existentes e independientes por reproduccion en aislamiento total) y
commiteado en 4 partes: 3 grillas nuevas en `empresa` (Area/Empresa/
MailInboxConfig, con un bug real de bucle de refresco infinito ~47 req/s
corregido), grilla Cuentas por Pagar en `proveedores` (nunca se
renderizaba en produccion), y namespacing de IDs duplicados en
`gastos`/`empleados`. Los 18 fallos pre-existentes se flagearon aparte
(`task_c3296519`), no se corrigieron en esta fase. Cierre real de Grupo 2:
`proveedores/proveedores_main.js` ya estaba resuelto; `empleados/
nomina_historial.js` es excepcion deliberada (drill-down anidado, misma
regla que el Kardex de F31.6); `ventas/resolucion_list.js` eliminado como
codigo muerto confirmado (0 referencias externas, la UI real ya vive en
un offcanvas server-rendered separado); `proyectos/nueva_tarea_list.js`
migrado (unico caso con parametros dinamicos, resuelto via `htmx.ajax()`
explicito en vez de `hx-trigger` estatico). Governance identico al
baseline de F30/F31 (0 hallazgos nuevos). 0 migraciones. Detalle completo:
`documentacion/F31_GRUPO2_GRID_MIGRATION.md`.
**Actualizacion previa:** 2026-08-13 (DOC-M21) — FASE 31: gobernanza y
modernizacion del frontend (alcance parcial, explicitamente documentado).
Audito el frontend completo de las 17 apps tenant (F31.0) -- **correccion
clave al plan original**: el patron dominante ya es HTMX +
django-tables2 (14/17 y 12/17 apps), no Tabulator; `inventario`, no
`cotizaciones`, es la app realmente 100% Tabulator. Diseno el contrato
Core Frontend (F31.1) y lo ejecuto parcialmente (F31.2): eliminado
`error-service.js` (codigo muerto), corregidas 11 de 13 violaciones del
patron Offcanvas obligatorio en 6 apps (3 de ellas con un bug latente
real de backdrops acumulados). Audito el contrato de API Client y el
patron JWT (F31.3): 0 usos del patron prohibido `window.jwtAuth.token`;
6 archivos `*.api.js` violan el contrato "solo URLs+metodos" con
reimplementaciones propias de fetch+CSRF+JWT, cada una con su propio
contrato de error. Completo un piloto real de migracion de grillas
(F31.6, `inventario`, 4 sub-modulos) -- el backend ya existia comiteado y
desconectado desde una sesion anterior (`60d8a33`); F31.6 lo conecto y en
el proceso encontro y corrigio **2 bugs de produccion reales**: un
WRONG_LOOKUP (botones enviaban PK entero a endpoints que exigen uuid) y
un `FieldError` que habria producido un 500 garantizado en la pestana de
Productos. **Diferido explicitamente, con evidencia, no como trabajo
pendiente silencioso**: un cluster real de duplicacion en el transporte
HTTP/CSRF/JWT (`http.js` x2 copias identicas + una tercera version
divergente que gana en produccion por orden de carga, mas los 6 `api.js`
ya mencionados) -- el riesgo de romper auth/CSRF/uploads en todo el
frontend tenant sin poder verificar en navegador (limitacion transversal
de este entorno: sin credenciales de tenant, sin `pytest-playwright`) es
demasiado alto para una correccion apresurada; requiere una micro-fase
futura con pruebas de navegador como prerrequisito. Governance identico
al baseline de F30 (0 hallazgos nuevos). 0 migraciones. Detalle completo:
`documentacion/F31_FINAL_REPORT.md`, `F31_FRONTEND_INVENTORY.md`,
`F31_FRONTEND_CONTRACT.md`, `F31_2_CORE_EXECUTION.md`,
`F31_6_INVENTARIO_GRID_MIGRATION.md`.
**Actualizacion previa:** 2026-08-12 (DOC-M20) — FASE 30: auditoria de
contratos publicos + regresion global controlada. Cerro los 3 hallazgos
que F29 dejo documentados sin corregir. **Hallazgo A** (workspace CRUD):
`test_workspace_crud_integration.py` sobreescribia `setUp()` reemplazando
la infraestructura de `SintelTenantTestCase` (perdia `HTTP_HOST`,
requerido por el middleware de tenant) -- eliminados los 3 `setUp()`
redundantes. **Hallazgo B** (`tenant_dashboard:index`): nombre nunca
registrado; el real es `tenant-dashboard-shell`
(`config/urls_tenant.py:140`) -- 2 call sites corregidos, sin crear el
namespace faltante (WRONG_TEST_CONTRACT, no PRODUCT_DECISION). **Hallazgo
C** (colision `user-list`/`user-detail`): dos routers DRF con el mismo
basename `"user"` en el mismo urlconf sin namespace; SSoT determinado con
evidencia (grep repo-wide, unicos 16 consumidores eran los propios tests)
-- `UserAdminViewSet` renombrado a `"admin-user"` (0 cambios de path
HTTP), 16 call sites actualizados. Al verificar contra el endpoint admin
real (antes enmascarado por la colision), confirmo exactamente la
sospecha de F29: 3 tests fallaban por primera vez por payloads sin
`password2` (auto-rellenado solo por el endpoint publico, no por el
admin) -- corregidos. **Bloqueador de infraestructura descubierto y
resuelto:** primera invocacion de `pytest` sin argumentos (== `make test`)
en todo el arco F21-F30 abordo con 10 errores de coleccion, 0 tests
ejecutados -- resueltos (`pytest.ini` `norecursedirs`, colision de modulo
`tests.py`/`tests/` en 2 apps resuelta con `git mv` tras confirmar 0
solapamiento de cobertura, y un export faltante en
`apps/tenant/empresa/services/__init__.py` que ademas **rompia en
produccion, silenciosamente, el 100% de las invocaciones** de
`/api/v1/core/mi-empresa/` via un `except Exception` generico -- **1 bug
de produccion preexistente descubierto y corregido**). Verificado:
`pytest --collect-only` -> 2053 tests, 0 errores (antes: 10 errores,
coleccion interrumpida). Regresion dirigida 100% verde en los 6 archivos
modificados. Regresion monolitica completa bloqueada por un limite de
recursos del entorno de desarrollo local (Docker Desktop, 5.7GB para todo
el stack) -- 3 interrupciones independientes a tamanos de lote
decrecientes, sin patron de fallo de codigo en comun; clasificado
`ENVIRONMENT`, documentado con causa raiz y accion de seguimiento
recomendada (no corregible desde dentro de los contenedores). Governance:
conteos identicos al baseline OCF ya triado (2026-08-08) -- 0 hallazgos
nuevos. 0 migraciones. Detalle completo: `documentacion/F30_FINAL_REPORT.md`,
`F30_FINDINGS.md`, `F30_URL_CONTRACT_MATRIX.md`, `F30_REGRESSION_REPORT.md`.
**Actualizacion previa:** 2026-08-11 (DOC-M19) — FASE 29: contratos de URL
y UUID en tests. Cerro los 2 hallazgos que F28 dejo abiertos y, en el
proceso, audito **todos** los usos de `reverse()`/`redirect()`/`resolve()`
del repo (~353 call sites, agente dedicado). **84 call sites corregidos en
19 archivos de test, 0 cambios de codigo de produccion.** Contrato UUID
(23 sites, 8 archivos): `reverse(..., kwargs={"pk"/args=[obj.id]})` contra
ViewSets con `BaseTenantViewSet.lookup_field="uuid"` corregido a `.uuid` --
descubrio ademas que el nombre `factura-xml` nunca existio (reales:
`factura-xml-ubl`/`factura-xml-app-response`, responden XML crudo, no
JSON) y que 2 tests usaban el campo deprecado `Factura.xml_content` en vez
de `FacturaAnexos.ubl_xml` (F26-003). Contrato URL `workspace` (24 sites, 4
archivos): el nombre real es `core_ui:workspace`
(`apps/tenant/core/urls_ui.py` declara `app_name = 'core_ui'`, incluido
sin `namespace=` explicito -- Django toma el `app_name` del modulo como
namespace) -- confirmado que NO es un bug de produccion (la ruta literal
`/workspace/` responde 302 en una peticion real), solo un contrato de
nombre mal invocado en tests; verificado empiricamente
(`test_workspace_page_loads` pasa 100% limpio tras el fix). Cluster LEGACY
`admin-tenants-*`/`admin-tenant-domains-*`/`admin-dt-tenants` (37 sites, 7
archivos): renombrado a los nombres reales post-refactor "Fase 5-BIS"
(`tenant-*`/`domain-*`/`console_api:dt_tenants`), confirmados con evidencia
antes de aplicar cada cambio. **3 hallazgos nuevos documentados, no
corregidos, cada uno con razon explicita**: `test_workspace_crud_integration.py`
sigue fallando por una causa distinta (usuario propio sin membership,
reemplaza al que `SintelTenantTestCase` ya provee); `tenant_dashboard:index`
nunca se registro (decision de producto pendiente, no de testing); colision
de nombre `user-list`/`user-detail` entre dos ViewSets (el fix toca
`config/urls_public.py`, produccion real, requiere validacion dedicada).
Test Impact Analysis: reutilizado `tools/ekg/impact.py` (0 herramientas
nuevas) -- limitacion real encontrada: `SintelTenantTestCase` no aparece en
el grafo (el extractor no cubre el arbol `tests/` de infraestructura).
Governance `FINAL STATUS: PASS`. 0 migraciones. Detalle completo:
`documentacion/F29_FINAL_REPORT.md`.
**Actualizacion previa:** 2026-08-11 (DOC-M18) — FASE 28: estabilizacion
del testing multi-tenant. Auditoria individual (agente dedicado, sin
asumir migracion automatica) de los 34 archivos con `TenantTestCase` crudo
documentados por F27: **11 MIGRATE_SAFE, 1 MIGRATE_WITH_FIX, 21
ALREADY_SAFE, 0 KEEP_INTENTIONAL, 1 UNKNOWN**. Migracion controlada
aplicada a los 12 que la necesitaban de verdad
(`TenantTestCase` -> `SintelTenantTestCase`), verificada empiricamente:
`test_facturas_list_naturaleza_api.py` pasa 100% limpio solo con el swap de
base class, confirmando que el diagnostico F27-003 (`SintelTenantTestCase`
fija `ROOT_URLCONF` de tenant, `TenantTestCase` crudo no) era correcto.
Corregido ademas un `SyntaxError` real encontrado en el archivo `UNKNOWN`
(`tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py` -- un
bloque de guard pegado sin indentar dentro de un metodo). La migracion
tambien **desenmascaro 2 hallazgos reales preexistentes** que antes
quedaban ocultos detras del `NoReverseMatch`: (a) varios tests pasan
`self.f.id` (PK entero) donde el ViewSet espera `self.f.uuid`
(`lookup_field = "uuid"`) -- bug de test, no de produccion; (b) el nombre
de URL `workspace` no resuelve via `reverse()` en **ningun** contexto,
reproducido incluso fuera de pytest con codigo de produccion intacto -- no
causado por F28 ni relacionado con `TenantTestCase`, la ruta literal
`/workspace/` si funciona en una peticion real (302). Ninguno de los 2 se
corrigio en este pase (indicacion explicita del usuario de no seguir
invirtiendo tiempo en la suite de facturas), documentados con evidencia
completa para una fase dedicada. Auditoria ligera de `compras` (primera app
de la expansion progresiva): **GREEN**, 0 archivos con `TenantTestCase`
crudo. Test Impact Analysis: **0 herramientas nuevas** -- reutilizado
`tools/ekg/impact.py` (Fase 12), dump de `facturas` regenerado (368 nodos,
430 edges, identico a F27). **0 tests nuevos creados.** Governance `FINAL
STATUS: PASS`. 0 migraciones de esquema. Alcance reducido declarado
explicitamente: no se re-ejecuto la suite completa de `facturas` (ya
corrida 2 veces sin cambio de fondo) ni la regresion global -- verificacion
quirurgica de los 13 archivos tocados (44 failed/7 passed/6 skipped,
desglosado y clasificado, no un numero sin explicar). Detalle completo:
`documentacion/F28_FINAL_REPORT.md`.
**Actualizacion previa:** 2026-08-11 (DOC-M17) — FASE 27: gobernanza y
optimizacion del sistema de testing. Inventario real de **toda** la suite del
repo (389 archivos, 2008 funciones `def test_`, verificado por comando, no
estimado): 138 archivos en `SintelTenantTestCase` (sin riesgo), 34 en
`TenantTestCase` crudo (candidatos de riesgo) -- detalle en
`documentacion/F27_TEST_INVENTORY.md`. **Hallazgo mas significativo**:
`django_tenants.test.cases.TenantTestCase` cambia el schema de PostgreSQL
pero **no** el `ROOT_URLCONF` de Django -- cualquier test que llame
`reverse("factura-...")` fuera de `self.client` falla con `NoReverseMatch`
(reproducido incluso via `manage.py shell`, fuera de pytest);
`SintelTenantTestCase` si lo resuelve
(`override_settings(ROOT_URLCONF=...)` + `set_urlconf(...)` en `setUp()`).
Esto explica la mayoria de los 31 fallos de la suite completa de `facturas`
(baseline real de esta fase: 31 failed/110 passed/4 skipped) -- **corrige el
diagnostico previo de DOC-M15/F26** que atribuia fallos similares a
"contaminacion de schema `test`". El test UBL pendiente desde F26
(`test_procesar_factura_xml_task`) se reprodujo en **aislamiento total**,
refutando esa misma hipotesis para ese caso puntual: la causa real era un
NIT de fixture que no coincidia con el XML -- corregido. Se investigo ademas
por que `test_importar_ubl_service.py` (uno de los "10 tests documentados,
no reescritos" de F26) seguia fallando tras corregir solo el shape de
respuesta: el parser real lee el NIT desde `PartyTaxScheme > CompanyID`, no
`PartyIdentification > ID` (estructura que usaban los fixtures) -- corregido,
**5/5 tests pasan**. `test_naturaleza_import_ubl.py` comparte ese mismo bug
mas 2 causas compuestas adicionales (mismo problema de `reverse()`, y falta
el parametro `async=false` contra un endpoint deprecado) -- documentado con
evidencia completa, no reescrito (cobertura real ya cubierta por el archivo
recien corregido). Duplicado byte-identico confirmado
(`tests/celery/test_tasks_import.py` == `tests/celery_tasks/test_tasks_import.py`)
-- eliminacion bloqueada por el clasificador de permisos de la sesion, no por
falta de evidencia. **Test Impact Analysis: no se construyo nada nuevo** --
`tools/ekg/impact.py` ya existia (Fase 12) y responde exactamente lo que F27
pedia; su dump de `facturas` estaba desactualizado, regenerado. **0 tests
nuevos creados** (resultado valido y preferido segun la propia regla de la
fase). **6 tests reales corregidos.** Governance `FINAL STATUS: PASS`. 0
migraciones. Alcance reducido declarado explicitamente: esta pasada se
concentro en `facturas`, no en las ~17 apps del repo -- ver
`documentacion/F27_EXECUTION_STATUS.md`.
**Actualizacion previa:** 2026-08-11 (DOC-M16) — Fix F26-006: idempotencia real
cuando el documento (Factura o NotaCredito) no trae CUFE/CUDE. `guardar_desde_dto()`
solo hacia el chequeo de idempotencia dentro de `if cufe:` -- si `identificadores`
venia vacio, `cufe` se resolvia a `""` (no `None`), esa rama se saltaba por completo,
y una segunda materializacion con el mismo numero chocaba contra la `UniqueConstraint`
de BD (`Factura.cufe`/`NotaCredito.cude`, ambos `unique=True`) con un `IntegrityError`
sin manejar. Fix quirurgico de 2 partes en `business_service.py`: **(1)** fallback de
idempotencia por `numero`+`empresa` cuando no hay CUFE (mismo criterio "ya existe" que
la rama por CUFE); **(2)** normalizacion `cufe or None` / `cude or None` al persistir,
restaurando la semantica real de `unique=True` + `null=True` (Postgres permite
multiples `NULL`, no multiples `""`). Requirio migracion `0033_alter_notacredito_cude.py`
(`NotaCredito.cude` no tenia `null=True`, a diferencia de `Factura.cufe`). Tests:
`test_idempotencia_por_numero` reescrito + 2 tests nuevos
(`test_dos_facturas_distintas_sin_cufe_no_chocan`,
`test_12_idempotencia_sin_cude_no_revienta`). Regresion de los 4 archivos de test
relacionados: **25/26 (96%)** -- el unico fallo (`test_ingesta_ubl.py::test_procesar_factura_xml_task`)
es un bug de test preexistente **no relacionado** (Empresa dummy con NIT que no
coincide con ninguna parte del XML de fixture, falla antes de llegar al codigo tocado
por este fix) -- **corrige el diagnostico previo de DOC-M15**, que atribuia este mismo
fallo a contaminacion de schema compartido entre archivos `TenantTestCase`; verificado
ahora que el test falla identico incluso corrido completamente solo. Governance
`FINAL STATUS: PASS`. Detalle completo: `documentacion/F26-006_FIX_REPORT.md`.
**Actualizacion previa:** 2026-08-11 (DOC-M15) — FASE 26: auditoria y simplificacion
de `apps/tenant/facturas` bajo el principio "el XML UBL/DIAN es fuente de datos, no
el modelo de datos de SINTEL". Investigo individualmente los 18 tests historicos
fallando (no solo "por que fallan" sino reproduccion real + lectura del codigo de
produccion que cada uno ejercita): **8/18 corregidos** con evidencia
ANTES(FAIL)/DESPUES(PASS) real (3 causas distintas en `test_materializar_from_dto.py` --
parametro `persist_anexos` inexistente, DTO sin envolver en `{"dto": ...}` que
`materializar_desde_result()` exige, capa de parseo de prefijo/consecutivo mal
asumida; `.decode()` innecesario en `test_ingesta_ubl.py` violando el contrato
`bytes` de `ingest_document()`; fixture XML incompleta en
`test_nota_credito_pipeline.py::test_5_factura_inexistente_error`), **10/18
documentados como CONTRATO CAMBIADO** (`test_importar_ubl_service.py`,
`test_naturaleza_import_ubl.py`: esperan un shape de respuesta de preview
`{"preview": bool, "factura": {...}}` que el pipeline universal actual ya no
produce -- ahora es `{"persisted": bool, "dto": {...}}`, y el calculo de
`naturaleza` durante preview fue removido deliberadamente al hacer el pipeline
agnostico de dominio -- no reescritos por prudencia, con evidencia completa en
`documentacion/F26_FINDINGS.md`). Auditoria exhaustiva de campos de `facturas`
(agente dedicado + grep real de consumidores en todo el repo, ver
`documentacion/F26_FACTURAS_FIELD_INVENTORY.md`) encontro y corrigio 2 defectos
reales de produccion: **`MANUAL_EDITABLE_FIELDS` incluia `'orden_compra'`, un campo
fantasma que `Factura` nunca tuvo** (riesgo real de `ValueError`/500 en un PATCH
nunca disparado en produccion, ahora eliminado de la lista), y **`Factura.xml_file_path`
eliminado** (0 consumidores confirmados en todo el repo, 0 datos historicos
verificados en las 3 empresas del entorno antes de aplicar la migracion
`0032_remove_factura_xml_file_path.py`). Hallazgo real nuevo documentado pero no
corregido (fuera de alcance -- requiere logica de negocio nueva, no simplificacion):
`guardar_desde_dto()` no tiene una ruta real de idempotencia cuando el documento no
trae CUFE (`cufe=""` choca contra la `UniqueConstraint` con un `IntegrityError` sin
manejar). **82/83 tests (98.8%) en la regresion consolidada final** (F21-F25 +
DOC-M14 + los 3 archivos de test corregidos en F26, 83 tests reales) -- el unico
fallo es un artefacto de infraestructura de testing (`TenantTestCase` reutiliza el
schema `"test"` compartido entre archivos dentro de una misma corrida larga, y
`Empresa` es un singleton real por schema; confirmado reproduciendo el error
`ValidationError: {'singleton_key': [...]}` directamente), no una regresion de F26.
**1 migracion nueva** (remove-only, verificada segura). Governance `FINAL STATUS:
PASS` sostenido. Conclusion de la auditoria: `apps/tenant/facturas` ya cumplia
mayormente el principio "XML es fuente, no modelo" antes de F26 -- la
sobre-persistencia real encontrada fue puntual (1 campo), no sistemica.
**Actualizacion previa:** 2026-08-10 (DOC-M14) — Devoluciones reales: NotaCredito ->
ItemNotaCredito -> ENTRADA_DEVOLUCION. Cierra la brecha DEFERRED declarada desde F23
(`F23_FACTURAS_BASELINE.md` S3, reafirmada en F24/F25): `NotaCredito` era documento
de solo cabecera, sin forma de generar `ENTRADA_DEVOLUCION` por producto. Investigacion
previa a la implementacion encontro que el gap real era menor al documentado: el
pipeline universal (`apps/services/document_parser/xml_parser/parser.py`) ya extraia
`CreditNoteLine` hacia `dto["items"]` (mismo shape que los items de Factura);
`ENTRADA_DEVOLUCION` ya vivia en `KardexService.TIPOS_ENTRADA` y ya estaba mapeado en
`ExtractorInventario` (F22, sin cambios) con `ReglaContable` seedeada. El unico gap
real era que `guardar_desde_dto()` no consumia esos items para la rama NC. Ahora crea
`ItemNotaCredito` por linea (resolviendo `Producto` por codigo, items sin match se
omiten sin bloquear la NC) y dispara `KardexService.registrar_movimiento(ENTRADA_DEVOLUCION)`
por cada item resuelto (costo desde `Producto.costo_promedio`, sede heredada de la
factura original, idempotente via el mismo `UniqueConstraint` de `MovimientoInventario`).
100% retrocompatible: una NC sin items en el DTO se sigue creando exactamente igual
que antes. Sin UI de creacion manual (NC sigue siendo import-only, como Factura). Sin
validacion "cantidad devuelta <= cantidad vendida" (sin FK confiable
`ItemFactura -> ItemVenta`; la NC en DIAN ya es la autorizacion legal). **5/5 tests
nuevos, 64/64 en regresion consolidada con el circuito F21-F25** (52 min). **Hallazgo
de esta fase:** 18 tests preexistentes de `facturas` (`test_materializar_from_dto.py`,
`test_importar_ubl_service.py`, `test_naturaleza_import_ubl.py`, `test_ingesta_ubl.py`,
mas `test_5_factura_inexistente_error`) fallan igual con y sin este cambio (confirmado
revirtiendo temporalmente con `git stash`) — deuda tecnica preexistente, documentada
aqui pero no corregida (fuera del alcance de esta feature).
**Actualizacion previa:** 2026-08-10 (DOC-M13) — cierre de FASE 25 (Auditoria Enterprise
Transversal de Atomicidad, Rollback, Idempotencia y Retry), alcance real en
`documentacion/F25_FINAL_REPORT.md`. Cierra por completo el hallazgo `F24-003` (DEFERRED):
de los ~25 sitios detectados por escaneo AST con el mismo patron de atomicidad que F23/F24
corrigieron (`@transaction.atomic` + `except` que retorna sin `raise` ni
`transaction.set_rollback(True)`), F25 clasifico cada uno individualmente leyendo su codigo
real. Encontro **1 bug real nuevo** (fuera del alcance original de F24-003, dentro del
alcance extendido de F25 a `gastos`): `GastoBusinessService.procesar_gasto()` creaba el
`DocumentoSoporte` y luego un loop de `RetencionesService.crear_retencion()` (escrituras
crudas sin savepoint propio) — si la retencion N fallaba tras la N-1 ya creada, el documento
y la primera retencion quedaban comprometidos pese a reportar error; corregido igual que
F23/F24 con `transaction.set_rollback(True)`, con evidencia ANTES(FAIL)/DESPUES(PASS)
real. Los **13 candidatos restantes** (compras/ventas/facturas) resultaron
`SAFE_BY_DESIGN`/`FALSE_POSITIVE` — cada uno tiene una unica escritura real delegada a otro
metodo `@transaction.atomic` (savepoint independiente, auto-revertido ante cualquier
excepcion interna sin importar el `except` externo) — y **no se modificaron** (regla
explicita: no tocar codigo solo para silenciar el AST). El caso mas notable:
`FacturaBusinessService.guardar_desde_dto()` (5 `except`, el conteo mas alto) resulto ser el
mas seguro de todos, porque su secuencia real de escrituras no tiene ningun manejo local de
excepciones que pudiera absorberlas. **59/59 tests en regresion consolidada final
F21+F22+F23+F24+F25** (`documentacion/F25_REGRESSION_REPORT.md`). **0 migraciones nuevas.**
Governance `FINAL STATUS: PASS` sostenido. Tambien confirmo (sin cambios necesarios):
idempotencia de retry HTTP/Celery ya cubierta por el mecanismo existente
(`UniqueConstraint`+CUFE), y proteccion de stock/asiento concurrente ya cubierta por
`select_for_update()`/`UniqueConstraint` respectivamente.
**Actualizacion previa:** 2026-08-10 (DOC-M12) — cierre de FASE 24 (Auditoria E2E Enterprise del
circuito F21+F22+F23), alcance real en `documentacion/F24_FINAL_REPORT.md`. F24 no agrega
funcionalidad de negocio nueva: construye 12 tests E2E reales que ninguna fase anterior habia
ejercitado juntos (Compra hasta Asiento, Venta hasta Asiento, Compra+Venta con reconciliacion de
stock, multi-item, multi-sede, multi-tenant con DSV real de UUID cruzado, idempotencia contable por
doble corrida, periodo cerrado, traslado sin asiento externo) y corrige 2 defectos reales
preexistentes que esos escenarios expusieron: (1) **HIGH** — el mismo patron de atomicidad que F23
encontro en `ventas` existia tambien en `RecepcionCompraBusinessService.confirmar_recepcion()`
(compras): al procesar varios `RecepcionCompraItem` en un loop dentro de un unico
`@transaction.atomic`, si el item N fallaba validacion despues de que el item N-1 ya hubiera
escrito su `MovimientoInventario` real, Django confirmaba esa escritura igual porque el `except` no
relanzaba ni forzaba `transaction.set_rollback(True)` — corregido igual que F23 corrigio su propio
caso. (2) **MEDIUM** — `validar_periodo_abierto()` (`contabilidad/integracion/validadores.py`)
referenciaba `periodo.nombre`, un campo que no existe en `PeriodoContable` (el real es
`periodo.periodo`, `YYYY-MM`), enmascarando el mensaje de "periodo cerrado" real detras de un
`AttributeError` — la proteccion en si nunca fallo (el extractor seguia rechazando la
contabilizacion), solo el diagnostico; corregido con el nombre de campo correcto. **57/57 tests en
regresion consolidada final F21+F22+F23+F24** (`documentacion/F24_REGRESSION_REPORT.md`). **0
migraciones nuevas.** Governance `FINAL STATUS: PASS` sostenido. **Deuda DEFERRED declarada**
(`documentacion/F24_FINDINGS.md` F24-003): el mismo patron de atomicidad detectado por escaneo AST
en otros 25 sitios de `compras`/`ventas`/`facturas`, no verificado ni corregido individualmente por
proporcionalidad de alcance — recomendada una auditoria dedicada fuera de una fase de negocio
especifica. Devoluciones/despacho parcial/reverso por anulacion siguen DEFERRED sin cambios (F24
solo confirmo, via auditoria, que ese estado sigue correctamente documentado).
**Actualizacion previa:** 2026-08-10 (DOC-M11) — cierre de FASE 23 (Venta -> Inventario -> Kardex
-> Costo de Venta -> Contabilidad), alcance real en `documentacion/F23_FINAL_REPORT.md`. Cierra la
ultima brecha declarada por F22 (nota DOC-M10 abajo): `SALIDA_VENTA` no tenia datos reales porque
`ventas`/`facturas` nunca llamaban a `KardexService`. Ahora
`VentaBusinessService.procesar_y_facturar_venta()` genera `MovimientoInventario(SALIDA_VENTA)`
real por cada `ItemVenta` con producto (excluye servicios), en el momento en que la Venta pasa a
`FACTURADA_DIAN`, reutilizando `KardexService.registrar_movimiento()` sin duplicar nada — costo
tomado de `Producto.costo_promedio` (nunca `precio_unitario`/`precio_venta`), sede propagada desde
el mismo parametro `sede_id` que ya usa `Factura.sede` (`OrganizationalContext`, sin nuevo campo en
`Venta`), idempotencia via el mismo `UniqueConstraint` de `MovimientoInventario` que F21 establecio
(documento origen = `ItemVenta`, no `Venta`, mismo criterio de granularidad de F21).
`ExtractorInventario` (F22, **sin cambios**) detecta estos movimientos automaticamente — 0
modificaciones a `apps/tenant/contabilidad/`. **Hallazgo destacado:** se encontro y corrigio un bug
real preexistente de atomicidad en `procesar_y_facturar_venta()` — el metodo esta decorado
`@transaction.atomic` pero su propio `try/except` capturaba toda excepcion sin volver a lanzarla,
por lo que Django nunca revertia escrituras parciales (`Venta`/`Factura`) en caso de error; F23 lo
expuso en la practica (primer punto de fallo real despues de escrituras) y lo corrigio con
`transaction.set_rollback(True)`. **9/9 tests nuevos pasan, 45/45 en regresion consolidada
F21+F22+F23** (`documentacion/F23_TEST_MATRIX.md`). **0 migraciones nuevas.** **Reducciones de
alcance declaradas** (`documentacion/F23_FINAL_REPORT.md` §5): devoluciones (`ENTRADA_DEVOLUCION`
desde `NotaCredito`) DEFERRED — `NotaCredito` no tiene lineas de producto/cantidad, crear esa
granularidad requeriria un modelo nuevo fuera del alcance minimo; reverso de inventario por
anulacion no aplica (`anular_venta()` rechaza estructuralmente cualquier venta ya facturada, no
existe el escenario); despacho/entrega parcial no existe en el modelo `Venta`/`ItemVenta`.
**Actualizacion previa:** 2026-08-10 (DOC-M10) — cierre de FASE 22 (Integracion Contable Real de
Inventario), alcance real en `documentacion/F22_FINAL_REPORT.md`. Cierra la ultima brecha
declarada por F21 (nota DOC-M9 abajo, §6.3): `ExtractorInventario.extraer_pendientes()` estaba
deshabilitado (`return []`) — ahora implementado real: `MovimientoInventario -> ExtractorInventario
-> TransaccionEconomica -> Contabilizador -> AsientoContable`, modelo Pull puro (0 imports de
`inventario` hacia `contabilidad`, verificado por grep). No se creo contrato nuevo: `TipoTransaccion`
(`dtos.py`) ya tenia los 5 valores de inventario sin usar, y `seed_reglas_contables.py` ya tenia
las `ReglaContable` seedeadas para 4 de los 5 — F22 los activo, no los inventó. Registrado en
`extractores/__init__.py` y `backfill_contabilidad.py` (`EXTRACTORES_DISPONIBLES['inventario']`).
Traslados entre sedes (`TRASLADO_SALIDA`/`TRASLADO_ENTRADA`) quedan deliberadamente excluidos de
la extraccion (transferencia interna, sin impacto economico externo — confirmado contra el
codigo, no asumido). **20/20 tests nuevos pasan, 19/19 de F21 confirmados sin regresion**
(`documentacion/F22_TEST_MATRIX.md`). **0 migraciones nuevas** (ningun modelo se modifico — todos
los campos que Contabilidad necesitaba ya existian desde F21). **Reducciones de alcance
declaradas** (`documentacion/F22_FINAL_REPORT.md` §21-22): `SALIDA_VENTA` sin datos reales
todavia (`ventas`/`facturas` no generan ese `MovimientoInventario` — brecha preexistente, no de
F22); movimientos de `ActivoFijo` fuera de alcance (dominio distinto); sin tarea Celery nueva
(mismo patron manual que `gastos`/`facturas`/`nomina`); sin reglas de gobernanza `ACC-INV-*`
nuevas (evaluadas una por una, ninguna aporta verificacion real no cubierta ya por el sistema de
tipos, el `UniqueConstraint` de BD, o el clasificador de dependencias existente).
**Actualizacion previa:** 2026-08-09 (DOC-M9) — cierre de FASE 21 (Compras -> Recepcion -> Inventario -> Sede -> Kardex -> Traslados -> Contabilidad), alcance real en `documentacion/F21_FINAL_REPORT.md`. Cierra la brecha `compras -> inventario` que F15-F20 (nota DOC-M8 abajo) habia documentado como pendiente: `OrdenCompra -> RecepcionCompra -> RecepcionCompraItem -> MovimientoInventario`, via `KardexService.registrar_movimiento()` extendido (no duplicado) con `sede_id`/idempotencia (`documento_origen_*` + `UniqueConstraint` condicional, mismo patron que `AsientoContable`). Agrega `TrasladoInventario` (nuevo, `inventario`) — flujo SOLICITADO->APROBADO->EN_TRANSITO->RECIBIDO/CANCELADO entre 2 `Sede`, resuelto via `StockPorSedeSelector` (stock por sede calculado en lectura, sin persistir un campo nuevo en `Producto`). `RecepcionCompra` adopta `SedeAwareModel` (extension del piloto de `compras`, ver §3.2/§3.6) — 1 finding real de gobernanza (`ORG-017`) resuelto registrando la decision en la allowlist, no suprimiendo la regla. **16/16 tests reales pasan** (`documentacion/F21_TEST_MATRIX.md`). **Contabilidad NO se toco**: se audito el extractor de inventario (`apps/tenant/contabilidad/integracion/extractores/inventario.py`) y se confirmo que ya estaba deshabilitado antes de F21 (`extraer_pendientes()` retorna `[]` incondicionalmente, sin ningun mecanismo real de contabilizacion) — deuda preexistente, documentada, no una regresion de esta fase (ver §6.3). **Reducciones de alcance declaradas** (`documentacion/F21_ORGANIZATIONAL_DECISIONS.md`): sin frontend/HTMX (2 ViewSets nuevos son API-only), `TrasladoInventario` limitado a 1 producto por operacion (sin `TrasladoInventarioItem` multi-item).
**Actualizacion previa:** 2026-08-09 (DOC-M8) — cierre de FASE 15-20 (Integracion Inter-App + Contexto Empresa/Sede/Area), alcance real en `documentacion/F15_F20_FINAL_REPORT.md`. Se extendio `tools/organizational_governance/` (no se creo un segundo motor) con `dependencies.py`: grafo real de 368 aristas de import inter-app entre las 17 apps, clasificadas (`ALLOWED`/`CONTROLLED`/`PUSH_CONTROLLED`/`PULL`/`FORBIDDEN`/`UNKNOWN`) y verificadas contra codigo fuente real — la primera version del clasificador marco 10 aristas legitimas como `FORBIDDEN`, corregido tras leer cada una (documentado como proceso en `F15_INTEGRATION_BASELINE.md` §3, no solo como resultado). 8 ciclos de dependencia detectados y explicados (ninguno es un `ImportError` real, por el patron de imports locales del proyecto). Motor de gobernanza ahora con **10 reglas** (+`ORG-010`, +`ORG-017`), **33/33 tests**, `FINAL STATUS: PASS`. **0 migraciones de esquema nuevas** — decision explicita registrada (`F17_SEDE_ROLLOUT_STATUS.md`): la necesidad de negocio para las apps pendientes ya se analizo y descarto en FASE 10 anterior, y el propio pedido de esta fase prohibe migracion masiva sin esa necesidad demostrada. 2 brechas funcionales reales documentadas (no fabricadas): `compras` no genera `MovimientoInventario` al recibir una orden; no existe operacion de traslado de inventario entre sedes. **Advertencia explicita:** los documentos `F20_COLOMBIAN_GOVERNANCE.md`/`COLOMBIA_COMPLIANCE_TRACEABILITY.md` son cobertura tecnica verificada por lectura de codigo, NO certificacion de cumplimiento legal colombiano (DIAN/Decreto 2420/Ley 1581) — ninguna cita normativa especifica fue investigada ni verificada contra fuente autoritativa en esta sesion.
**Actualizacion previa:** 2026-08-09 (DOC-M7) — cierre de FASE 13 (Knowledge Graph Organizacional) + FASE 14 (Gobernanza Automatica). `tools/organizational_governance/` (paquete nuevo, independiente de `tools/ekg/`): grafo real (165 entidades, 220 relaciones) + motor de gobernanza con 8 reglas (23/23 tests), 0 findings.
**Actualizacion previa:** 2026-08-09 (DOC-M6) — sincronizacion tras cerrar el plan de consolidacion OCF/OSF completo (FASE 0-12). Trabajo de OCF/OSF commiteado (5 commits, `0295932`..`34fc020`); 2 bugs reales encontrados y corregidos.
**Actualizacion previa:** 2026-08-09 (DOC-M5) — pasada de validacion completa contra codigo real (conteo directo de apps/migraciones/modelos/tests/endpoints/namespaces JS) que corrigio numeros internamente contradictorios en §2.2/§9/§12 y establecio el estado real de OCF/OSF contra codigo (agente de investigacion dedicado). Detalle completo en el historial de este documento.
**Fuente canonica:** `documentacion/arquitectura_general.md`
**Reglas de desarrollo:** `AGENTS.md` (raiz del proyecto)
**Estado actual del proyecto:** `MEMORY.md` (raiz del proyecto)
**Modo de Proyecto:** EN DESARROLLO (Development Mode)

> Antes de modificar cualquier app, leer `AGENTS.md` completo y el documento `.agent/AUDITORIA_FLUJO_*.md` de esa app. Este documento describe la infraestructura global, no la logica interna de cada app.

---

## 1. Vision y Core Tecnologico del Proyecto

SINTEL es un ERP SaaS multi-tenant para gestion contable y facturacion electronica en Colombia. Cada empresa (tenant) opera en un esquema PostgreSQL aislado, compartiendo la misma infraestructura de servidores. El sistema implementa Feature-Sliced Design (FSD) con Service Layer estricto, autenticacion Dual-Auth (JWT + Session) y frontend sin build step.

**Dominio de negocio principal:** facturacion electronica DIAN (XML, envio, estados), contabilidad NIIF PYMES, nomina colombiana, inventario con Kardex, gastos operativos, cotizaciones comerciales, proyectos, CRM basico y dashboard ejecutivo.

### 1.1. Stack Backend

| Tecnologia | Version | Rol |
|---|---|---|
| Python | 3.12 | Lenguaje principal |
| Django | 5.0–5.1 | Framework web |
| Django REST Framework | 3.16–3.17 | APIs JSON (ViewSets, Serializers, Routers) |
| django-tenants | 3.9–3.10 | Aislamiento multi-tenant por esquemas PostgreSQL |
| PostgreSQL | 15+ | Base de datos relacional |
| Celery | 5.3–6.0 | Tareas asincronas y procesamiento en segundo plano |
| Redis | 5.0–6.0 | Broker de Celery y cache |
| WhiteNoise | 6.x | Servicio de archivos estaticos en produccion |
| djangorestframework-simplejwt | 5.3–6.0 | Tokens JWT (access 15 min, refresh 7 dias, HS256) |
| anthropic | 0.40–1.0 | SDK para agentes IA especializados (Asistente Contable) |
| drf-spectacular | 0.29–0.30 | Generacion de schema OpenAPI |
| django-filter | 25.1+ | Filtros query para APIs |
| djangorestframework-mcp | — | **[DOC-M5, nuevo, no documentado antes]** Expone ViewSets decorados con `@mcp_viewset()` como herramientas MCP en `/mcp/` (`config/settings.py:73,105`; montado en `config/urls_public.py:117` y `config/urls_tenant.py:166`). Compatible con `mcp-remote` (STDIO transport). |
| django-cors-headers | — | **[DOC-M5, nuevo]** CORS para subdominios dinamicos de `sintel.net.co` (`config/settings.py`, `SHARED_APPS`) |
| psycopg (binary) | 3.1–4.0 | Adaptador PostgreSQL (psycopg3) |
| pandas | 2.0–3.0 | Procesamiento ETL y datos masivos |
| lxml | 5.2.1 | Parsing XML/HTML (facturas electronicas DIAN) |
| Pillow | 10.3.0 | Procesamiento de imagenes |

### 1.2. Stack Frontend

| Tecnologia | Version | Rol |
|---|---|---|
| HTMX | 1.9.10 | Server-driven UI, carga dinamica de fragmentos HTML |
| Bootstrap | 5.3.2 | Sistema de diseno UI, Offcanvas para modales laterales |
| django-tables2 | 2.7.x | **Patron actual para grillas nuevas** — tablas server-rendered + HTMX, reemplaza Tabulator progresivamente (ver §4.6) |
| Tabulator | 6.2.5 | Grillas de datos reactivas con paginacion remota client-side — **en migracion, no usar en modulos nuevos** (ver §4.6) |
| Vanilla JS ES6+ | — | Modulos por namespace `window.Sintel.<App>` |
| Bootstrap Icons + Font Awesome | — | Iconografia |

**No hay build step.** Todas las librerias se cargan via CDN. No existe Webpack, Vite ni compilacion de frontend. Alpine.js esta disponible via CDN pero no es parte del estandar aprobado.

**Migracion de grillas (Tabulator → django-tables2+HTMX), estado real verificado 2026-08-07:** 13 de ~17 apps tenant ya tienen `tables.py` (`bancos`, `clientes`, `compras`, `contabilidad`, `empleados`, `empresa`, `facturas`, `gastos`, `inventario`, `perfil`, `proveedores`, `proyectos`, `ventas`). Solo `cotizaciones` y `dashboard` siguen exclusivamente en Tabulator. Varias apps con `tables.py` conservan Tabulator vivo en vistas puntuales no migradas (`contabilidad`: `pendiente_list.js`/`libro_diario_list.js`/reportes; `inventario`: 6 sitios; `clientes`: `clientes.cartera.js`; `ventas`: `resolucion_list.js`) — coexistencia deliberada, no regresion. Ver nota DOC-M4 en §4.6 para el detalle completo y la discrepancia encontrada con el estado que describia `MEMORY.md` antes de esta validacion.

### 1.3. Infraestructura

| Componente | Tecnologia |
|---|---|
| Contenedores | Docker + Docker Compose |
| Servidor WSGI | Gunicorn (produccion) / `runserver` (desarrollo, ver `docker-compose.yaml`) |
| Proxy inverso | Nginx — sirve `/static/` y `/media/` directamente desde `/app/staticfiles`, `/app/media` (bind mount de solo lectura) y reenvia todo lo demas a `web:8000` |
| DNS interno | Windows Server 2022 wildcard `*.sintel.net.co → 192.168.2.15` |
| Autenticacion asimetrica | HS256 JWT via variable de entorno `JWT_SECRET_KEY` |

**Politica de cache de estaticos (Nginx), fijada 2026-08-06:** `/static/` usa `Cache-Control: "no-cache, public, no-transform"` (revalidacion condicional obligatoria via ETag/Last-Modified, sin `expires`) — **no** `expires 30d` como `/media/`. Un `expires 30d` sobre `/static/` estuvo vigente hasta el hallazgo C4/C7 de la Auditoria Enterprise 2026-08-06: cualquier fix de JS/CSS quedaba invisible para navegadores que ya hubieran cargado el archivo anterior, durante 30 dias, sin importar cuantos reinicios del contenedor `web` se hicieran. `nginx.conf` se hornea en la imagen en build-time (no es un volumen montado) — un cambio ahi requiere `docker compose build nginx && docker compose up -d nginx`, no solo un restart.

### 1.4. Directorio `config/` — Nucleo de Configuracion

El directorio `config/` es el nucleo de configuracion del proyecto. Toda la orquestacion de URLs, settings y tareas asincronas pasa por aqui.

| Archivo | Responsabilidad |
|---|---|
| `settings.py` | SSoT de toda la configuracion Django (SHARED_APPS, TENANT_APPS, JWT, Celery, etc.) — 911 lineas |
| `urls_public.py` | ROOT_URLCONF — dominio admin mapea al esquema public |
| `urls_tenant.py` | TENANT_URLCONF — subdominios mapean al esquema tenant |
| `api_urls.py` | SSoT de TODAS las rutas API REST (`/api/v1/...`). Registros resilientes con try/except por app |
| `public_api_urls.py` | Rutas API del esquema publico |
| `celery.py` | Configuracion Celery + autodiscovery de tasks |
| `well_known.py` | Endpoints `.well-known` (DIAN, OAuth) |

### 1.5. Resolucion de Tenant por Hostname

```
request → TenantMiddleware → hostname match → set schema PostgreSQL

admin.sintel.net.co   →  public schema    →  urls_public.py
empresa.sintel.net.co →  tenant schema    →  urls_tenant.py
192.168.2.15       →  public (fallback) →  soporte IP en DEBUG
```

---

## 2. Inventario de Apps

### 2.1. Esquema Public (`SHARED_APPS`) — 5 apps activas

| App | App Label | Modelos | Migraciones | Responsabilidad |
|---|---|---|---|---|
| `apps/public/accounts/` | `accounts` | User, DeletionAudit | 2 | Modelo `User` global (AbstractUser), gestion de usuarios |
| `apps/public/tenants/` | `tenants` | Client, Domain, TenantMembership, FailedTenantTask | 2 | Registro de tenants, dominios, invitaciones OTT |
| `apps/public/impuestos/` | `impuestos` | TipoImpuesto, TarifaIVA, ConceptoRetencion, CodigoTributario, ActividadEconomica, DocumentoFuente, IngestaLog, NormaTributaria, ContribuyenteTipo, RegimenRenta, ResponsabilidadRUT, PerfilTributario | 1 | Catalogo DIAN, tarifas, normativas tributarias |
| `apps/public/console/` | `console` | ConsoleActionLog | 4 | Consola admin: crear tenants, gestionar membresias, JWT bridge |
| `apps/public/core/` | `core` (public) | (sin modelos) | — | Middleware de resolucion de tenant, infraestructura compartida |

**Total public models: 19** — **[DOC-M5, corregido]** recuento anterior (17) subestimaba `impuestos` (12 modelos reales, no 11). Total migraciones public: 2+2+1+4 = **9** (antes: 8; `console` paso de 3 a 4 migraciones).

### 2.2. Esquema Tenant (`TENANT_APPS`) — 17 apps registradas, 15 con modelos de negocio

**[DOC-M5, corregido 2026-08-09]** `TENANT_APPS` (`config/settings.py`) tiene 17 entradas `apps.tenant.*`. Este documento tenia tres numeros distintos y mutuamente contradictorios para "apps de negocio" (14 en este encabezado, 16 filas en la tabla, 13 en la tabla de metricas §12) — ninguno era correcto. El numero real: **15 apps con modelos de negocio concretos** (todas las filas de abajo excepto `core`, que solo aporta las clases base abstractas) + `core` + `landing` (sin `models.py`, ver §2.3) = 17 apps registradas.

| App | App Label | Modelos | Migraciones | Responsabilidad |
|---|---|---|---|---|
| `apps/tenant/core/` | `core` | SintelTenantBaseModel, SedeAwareModel (ambas abstractas) | 0 | UI Shell, bridge cross-schema, onboarding, auth JWT |
| `apps/tenant/empresa/` | `empresa` | Empresa, MailInboxConfig, Sede, Area | 9 | Datos fiscales, logo, sedes y areas del tenant |
| `apps/tenant/perfil/` | `perfil` | Departamento, TenantProfile (+ RolTenant, AlcanceOrganizacional como `TextChoices`, no modelos) | 8 | Roles y perfiles de usuario dentro del tenant |
| `apps/tenant/facturas/` | `facturas` | Factura, ItemFactura, NotaCredito, ItemNotaCredito, MailIngestionRun, MailInboxState, FacturaAnexos, FacturaImpuesto | 33 | Facturacion electronica DIAN (XML, envio, estados) |
| `apps/tenant/contabilidad/` | `contabilidad` | CatalogoMaestroNIIF, CuentaContable, TipoComprobante, AsientoContable, MovimientoContable, PeriodoContable, ReglaContable, TarifaImpuesto, ConfiguracionRetenciones, Retencion, PlantillaContable, LineaPlantilla, ImpuestoDocumento | 16 | PUC NIIF, asientos, extractores Pull, agente IA, Motor de Plantillas |
| `apps/tenant/gastos/` | `gastos` | ResolucionDIAN, DocumentoSoporte | 22 | Gastos operativos, documentos soporte, retenciones |
| `apps/tenant/inventario/` | `inventario` | CategoriaItem, Producto, Servicio, ActivoFijo, MovimientoInventario, TrasladoInventario (F21), HistorialServicio (+ TimeStampedModel abstract) | 11 | Productos, servicios, activos fijos, Kardex unificado, traslado de stock entre sedes (F21) |
| `apps/tenant/empleados/` | `empleados` | Empleado, Contrato, Devengo, ResolucionDIAN, TransmisionNominaDIAN, LiquidacionPrestacion | 13 | Nomina colombiana, devengos, contratos, liquidaciones |
| `apps/tenant/cotizaciones/` | `cotizaciones` | Cotizacion, CotizacionItem (+ Producto y Servicio propios) | 5 | Cotizaciones comerciales, vinculacion con facturas |
| `apps/tenant/clientes/` | `clientes` | Cliente, ContactoCliente, Cartera | 8 | CRM basico, terceros clientes, cartera, retenciones |
| `apps/tenant/proveedores/` | `proveedores` | Proveedor, CuentasPagar, Representante | 18 | Terceros proveedores, cartera unificada, documentos soporte |
| `apps/tenant/proyectos/` | `proyectos` | Proyecto, AsignacionPersonal, PedidoProyecto, ItemPedido, ItemPresupuestoProyecto, TareaCorta, TareaDiariaProyecto | 20 | Gestion de proyectos, presupuesto, tareas cortas |
| `apps/tenant/dashboard/` | `dashboard` | SnapshotMetricaDiaria | 3 | Dashboard ejecutivo, metricas consolidadas |
| `apps/tenant/bancos/` | `bancos` | CuentaBancaria, ExtractoBancario, TransaccionBancaria | 5 | Estados de cuenta bancarios, conciliacion manual via UUID soft-references |
| `apps/tenant/compras/` | `compras` | PlantillaOrdenCompra, OrdenCompra (hereda `SedeAwareModel`, ver §3.2/ADR-003), ItemOrdenCompra, RecepcionCompra (F21, hereda `SedeAwareModel`), RecepcionCompraItem (F21) | 8 | Ordenes de compra a proveedores + Recepcion de Compras -> Inventario (F21, ver `documentacion/F21_RECEPCION_INVENTARIO.md`) |
| `apps/tenant/ventas/` | `ventas` | ResolucionFacturacion, Venta, ItemVenta | 3 | Ordenes de venta y su puente hacia `facturas` (agregada 2026-06-17, ver `.agent/ARQUITECTURA_VENTAS.md`) |

**Nota (`ResolucionDIAN` duplicado):** `gastos` y `empleados` tienen cada una su propia clase `ResolucionDIAN` — son dos modelos distintos, no un bug de referencia cruzada (hallazgo confirmado durante la auditoria EKG 2026-08-07, ver `documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md` §4.1).

**Total tenant models: 71 concretos + 3 abstractos** (`SintelTenantBaseModel`, `SedeAwareModel`, `TimeStampedModel`) — **[DOC-M9, 2026-08-09]** +3 sobre el conteo DOC-M5 (67) por los modelos nuevos de F21: `RecepcionCompra`, `RecepcionCompraItem` (`compras`), `TrasladoInventario` (`inventario`). **[DOC-M14, 2026-08-10]** +1 (`ItemNotaCredito`, `facturas`) — la fila de esta seccion no se habia actualizado hasta esta pasada de validacion (2026-08-11), aunque la tabla de metricas de §12 si lo reflejaba desde DOC-M14.
**Total migraciones: 191 (182 tenant + 9 public)** — **[DOC-M9, 2026-08-09]** +2 sobre el conteo DOC-M5 (177 tenant) por las migraciones de F21. **[DOC-M14 a DOC-M16]** +3 adicionales (`0031_itemnotacredito`, `0032_remove_factura_xml_file_path`, `0033_alter_notacredito_cude`), verificado por conteo directo de archivos (`find apps/tenant -path '*/migrations/*.py' -not -name '__init__.py'` = 182; `apps/public` = 9) durante esta pasada de validacion (2026-08-11) — la fila de esta seccion tampoco se habia actualizado desde DOC-M9 hasta ahora. Todas aplicadas en los 3 schemas de tenant reales (`migrate_schemas --tenant`), `makemigrations --check` limpio.

### 2.3. Apps de Infraestructura Tenant (sin modelos de negocio)

**[DOC-M5, corregido 2026-08-09]** Esta tabla listaba `apps/tenant/mail/` y `apps/tenant/mailinbox/`, que **no existen como directorios** en el repositorio actual (verificado, `ls apps/tenant/`) y nunca estuvieron en `TENANT_APPS`. Los modelos de correo viven hoy dentro de `facturas` (`MailIngestionRun`, `MailInboxState`) y `empresa` (`MailInboxConfig`) — ver tabla de §2.2. `apps/tenant/api/` tampoco es una app Django registrada (no tiene `apps.py` ni aparece en `TENANT_APPS`) — es una carpeta de codigo compartido (permisos DRF centrales, `BaseTenantViewSet`), no una "app de infraestructura" en el sentido de django-tenants.

| App | Registrada en `TENANT_APPS` | Responsabilidad |
|---|---|---|
| `apps/tenant/landing/` | Si | Pagina publica estatica del tenant — sin `models.py` |
| `apps/tenant/api/` | No (carpeta de codigo compartido) | `BaseTenantViewSet`, `BaseServiceMixin`, permisos DRF centrales |

---

## 3. Capa de Datos e Infraestructura Multi-Tenant (Zero-Trust)

### 3.1. Division de Esquemas PostgreSQL

| Esquema | Apps | Contenido |
|---|---|---|
| `public` | `SHARED_APPS` | Usuarios globales (`accounts.User`), registro de tenants (`tenants.Client`), catalogo DIAN (`impuestos`), consola admin (`console`) |
| Tenant (uno por empresa) | `TENANT_APPS` | Todos los datos de negocio del tenant: facturas, contabilidad, empleados, inventario, etc. |

Los esquemas tenant estan completamente aislados a nivel de base de datos. Una consulta en el esquema de "Empresa A" nunca puede acceder a los datos de "Empresa B" por disenio del ORM.

### 3.2. Modelo Base Obligatorio — `SintelTenantBaseModel`

**SSoT:** `apps/tenant/core/models.py`

Todos los modelos del esquema tenant heredan de `SintelTenantBaseModel`, nunca de `models.Model`. Este modelo base inyecta automaticamente:

| Campo | Tipo | Detalle |
|---|---|---|
| `empresa` | `ForeignKey('empresa.Empresa', PROTECT)` | Clave de particion — filtra al tenant actual |
| `created_at` | `DateTimeField(auto_now_add=True)` | Timestamp de creacion, indexado |
| `updated_at` | `DateTimeField(auto_now=True)` | Timestamp de ultima modificacion, indexado |

**Indices declarados en `SintelTenantBaseModel.Meta`:** `[empresa]` y `[empresa, -created_at]`. **Correccion (2026-08-07, verificado durante ADR-003):** Django NO fusiona estos indices con el `Meta.indexes` propio de un modelo concreto cuando este ultimo declara el suyo — verificado empiricamente (`Model._meta.indexes`) en `OrdenCompra` y `PlantillaOrdenCompra`, ninguno de los dos hereda estos dos indices pese a heredar el campo `empresa`. Cualquier modelo que declare su propio `Meta.indexes` debe repetirlos explicitamente ahi si los necesita.

**Proteccion en `save()`:** el modelo base lanza `ValueError` si `empresa_id` es `None`, evitando registros huerfanos por error de programacion.

**Extension opcional — `SedeAwareModel` (ADR-003, `docs/ADR-003-contexto-organizacional-sede-area.md`):** mixin abstracto que hereda de `SintelTenantBaseModel` y agrega `sede`/`area` (Contexto Organizacional Empresa->Sede->Area). Opt-in, no reemplaza `SintelTenantBaseModel` — piloto: `apps/tenant/compras/models.py:OrdenCompra` y, desde F21, `RecepcionCompra` (misma app, extension del piloto ya aprobado, no una app nueva adoptando el mixin — ver `documentacion/F21_ORGANIZATIONAL_DECISIONS.md` §1). La lista de adopcion autorizada es una allowlist cerrada verificada por gobernanza (`tools/organizational_governance/rules.py:_SEDE_AWARE_MODEL_ALLOWLIST`, regla `ORG-017`) — cualquier modelo nuevo que herede `SedeAwareModel` sin estar en esa lista falla el `--report` de gobernanza hasta que la decision se documente y se registre ahi.

### 3.3. Regla Zero-Trust de Consultas

Toda consulta ORM en apps tenant debe filtrar por `empresa_id`. Las siguientes practicas estan prohibidas:

- Usar `.all()` sin filtro de empresa
- Usar `.filter()` sin encadenar `.only()` o `.defer()`
- Acceder a `obj.fk.campo` sin `select_related()` previo (problema N+1)

**Patron obligatorio en ViewSets:**

```
queryset = Model.objects.none()   # nivel de clase
get_queryset() → .filter(empresa_id=...).only(campos).select_related(...)
```

### 3.4. UUID como Lookup Field

`BaseTenantViewSet` (`apps/tenant/api/base.py`) define `lookup_field = "uuid"`. Todos los ViewSets tenant heredan este valor. Las PKs enteras nunca se exponen en URLs publicas de la API.

### 3.5. Seguridad y Autenticacion (Dual-Auth)

**SSoT de autenticacion:** `BaseTenantViewSet` en `apps/tenant/api/base.py`.

`authentication_classes = [JWTAuthentication, SessionAuthentication]` — heredado por todos los ViewSets. Prohibido sobrescribir en ViewSets hijos.

DRF evalua JWT primero (header `Authorization: Bearer`). Si falla, usa Session (cookie). Esto permite que el mismo endpoint sirva a clientes API y al workspace del navegador.

**Bridge Session → JWT:** `GET /api/v1/core/auth/from-session/`

**Endpoints de token:**

| Endpoint | Metodo | Accion |
|---|---|---|
| `/api/token/` | POST | Obtener par access/refresh |
| `/api/token/refresh/` | POST | Renovar access token |
| `/api/token/verify/` | POST | Verificar validez de token |

**Parametros JWT (`config/settings.py`):** access 15 min, refresh 7 dias, ROTATE=True, BLACKLIST=True, algoritmo HS256.

### 3.6. Roles y Permisos

**SSoT de roles:** `TenantProfile.rol` en `apps/tenant/perfil/models.py`

| Rol | Capacidades |
|---|---|
| `ADMIN` | CRUD completo, asignar roles, configuracion de empresa |
| `OPERADOR` | Lectura + escritura segun app |
| `VISOR` | Solo lectura |

**SSoT de permisos:** `apps/tenant/api/permissions.py` — unica fuente para importar permisos en todo el proyecto.

| Permiso | Descripcion |
|---|---|
| `IsTenantMember` | Verifica membresia activa en el tenant. Obligatorio en todo ViewSet |
| `IsTenantAdminOrReadOnly` | Lectura para autenticados; escritura solo para ADMIN |
| `IsTenantProfileOperadorOrAdmin` | Requiere ADMIN u OPERADOR |
| `HasTenantRole` | Generico — el ViewSet declara `required_roles` |

**Auto-creacion de perfil:** al hacer login, si el usuario no tiene `TenantProfile` en el tenant actual, se crea automaticamente con rol `VISOR`.

**Alcance organizacional (ADR-003, 2026-08-07 — fundamentos + piloto `compras`, ver
`docs/ADR-003-contexto-organizacional-sede-area.md`):** `TenantProfile.alcance`
(`EMPRESA`/`SEDE`/`AREA`, default `EMPRESA`) es un campo nuevo, **ortogonal** a `rol` — no lo
reemplaza. Un perfil con `alcance=SEDE`/`AREA` solo puede operar sobre sus `sedes_asignadas`/
`areas_asignadas`. "ADMIN GLOBAL" no es un valor de `alcance`: es el
staff/superuser de Django del esquema publico, fuera de `TenantProfile`.

**[DOC-M6, 2026-08-09 — distinguir dos mecanismos que no son lo mismo, ya commiteados]** Tras
ADR-003 (piloto `compras`), el proyecto interno Organizational Context/Scope Framework (OCF/OSF —
ADR-004 y **ADR-005**, ver §7) extendio el *filtrado* por alcance a mas apps, pero **no** de la
misma forma que el piloto original — distincion verificada y consolidada tras el plan de FASE 0-12
de `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`:
- La clase de permiso `HasOrganizationalScope` (`apps/tenant/api/permissions.py`) sigue aplicada
  **solo** a `OrdenCompraViewSet` y a `apps/tenant/core/api/contexto.py` — rollout deliberadamente
  no extendido a las demas apps hasta resolver una asimetria real encontrada durante la
  consolidacion: `HasOrganizationalScope` deniega objetos con `sede_id=None`, mientras que el
  filtrado de listas de las 6 apps de abajo trata esos mismos registros como visibles (100% de los
  historicos de esas apps tienen `sede=NULL`) — ver `documentacion/OSF_TECHNICAL_AUDIT.md` §4.
- `SedeAwareModel` (el mixin de modelo) sigue heredado **solo** dentro de `compras`
  (`OrdenCompra`, y desde F21 tambien `RecepcionCompra` — ver §2.2) — decision confirmada, no
  pendiente: el rollout a las demas apps usa un patron mas liviano (siguiente punto) en vez de
  migracion de esquema, ver ADR-005. La adopcion esta cerrada por una allowlist verificada por
  gobernanza (`ORG-017`, ver §3.2) — no basta con heredar el mixin en un modelo nuevo, hay que
  registrar la decision.
- Lo que si se extendio: **filtrado consciente de alcance a nivel de selector/business-service**
  (`OrganizationalScope.filter()` / `filter_by_scope()` / `filter_by_scope_null_safe()`, en
  `apps/tenant/core/services/organizational_scope.py` y `organizational_filters.py`) — presente en
  `compras`, `cotizaciones`, `empleados`, `facturas`, `gastos`, `inventario`, `proyectos`. `ventas`
  usa el mecanismo hermano `OrganizationalContext.resolve()` (no `OrganizationalScope`) para
  defaultear la `sede` de la `Factura` que genera, nunca desde el payload del cliente — ver
  `documentacion/VENTAS_FACTURAS_AUDIT.md`.
- **Dos bugs reales de aislamiento encontrados y corregidos durante la consolidacion** (FASE 7):
  las acciones HTMX `render_offcanvas_detalle`/`render_offcanvas_editar` de `compras`
  (`apps/tenant/compras/api/viewsets.py`) resolvian el objeto con `get_object_or_404()` en vez de
  `self.get_object()`, bypaseando `HasOrganizationalScope` por completo — corregido agregando
  `self.check_object_permissions(request, instance)` explicito. Y `BaseServiceMixin.
  handle_service_error()` (`apps/tenant/api/mixins.py`, compartido por **todo** el proyecto, no
  solo `compras`) no tenia un caso para `rest_framework.exceptions.PermissionDenied` y devolvia
  `500` en vez de `403` cuando `HasOrganizationalScope` denegaba un `update()`/`destroy()` — la
  escritura ya estaba bloqueada en ambos casos (no era una fuga de seguridad), pero el codigo de
  estado era incorrecto. Ambos corregidos, verificados con 20/20 tests reales pasando
  (`documentacion/FASE7_AISLAMIENTO_ORGANIZACIONAL.md`).
- Estos modulos `organizational_*.py` de `apps/tenant/core/services/`, junto con el resto del
  trabajo de OCF/OSF (modelos, migraciones, tests, los 2 fixes de arriba), **ya estan commiteados**
  — 5 commits (`0295932` OCF core, `120d17e` piloto compras, `c63b35e` scope en 6 apps, `1d19d8f`
  tests, `34fc020` ADRs/documentacion), verificado con `git log`. Detalle completo en
  `documentacion/FASE11_CONSOLIDACION_GIT.md`.

**Frontend JWT:**

```javascript
// CORRECTO:
const token = window.jwtAuth?.getAccessToken?.();

// PROHIBIDO — la propiedad .token no existe:
window.jwtAuth.token
```

---

## 4. Patron de Arquitectura del Backend (Service Layer Unificada)

### 4.1. Feature-Sliced Design (FSD) — Un Ecosistema por Modelo

Cada app tenant implementa un ecosistema completo e independiente por modelo de dominio.

```
apps/tenant/<app>/
  models.py
  services/
    __init__.py          — Re-exporta clases principales (imports explicitos, sin wildcards)
    crud_service.py      — SOLO persistencia DB (@transaction.atomic)
    business_service.py  — Reglas de negocio + Double Semantic Verification (IDOR)
    selectors.py         — QuerySets read-only con .only(), LIST_FIELDS/DETAIL_FIELDS
    api_mixins.py        — <Modelo>ServiceMixin inyectado en ViewSet (hereda BaseServiceMixin)
    services.py          — Facade estable (re-exporta desde business_service)
  api/
    viewsets.py          — Hereda BaseTenantViewSet + ServiceMixin
    serializers.py
    urls.py
  templates/tenant/<app>/
    offcanvas_crear_<modelo>.html
    offcanvas_editar_<modelo>.html
    offcanvas_detalle_<modelo>.html
    list_<modelo>.html
    partials/
  static/<app>/js/
    <app>.api.js                   — SSoT de todas las URLs de endpoint
    features/
      <modelo>_list.js             — Grilla Tabulator
      <modelo>_editor.js           — Formularios Offcanvas
  .agent/
    AUDITORIA_FLUJO_*.md           — Flujo especifico de la app (leer antes de modificar)
    docs/
    skills/
```

### 4.2. Flujo Unidireccional (Obligatorio)

```
ViewSet → ServiceMixin → BusinessService (DSV + reglas) → CRUDService (DB) → Response JSON / HTMX OOB
```

El ViewSet es un enrutador HTTP puro. Toda logica de negocio vive en el Service Layer. Los modelos no contienen logica de negocio. Los Serializers solo realizan validacion sintactica y de tipos.

### 4.3. Responsabilidades por Capa

| Capa | Archivo | Responsabilidad |
|---|---|---|
| ViewSet | `api/viewsets.py` | Ingesta HTTP, delegacion a ServiceMixin, respuesta |
| Serializer | `api/serializers.py` | Validacion sintactica y de tipos, serializacion de salida |
| ServiceMixin | `services/api_mixins.py` | Inyecta `get_qs_list()`, `get_qs_detail()`, `service_crear_*()`. Hereda `BaseServiceMixin` |
| BusinessService | `services/business_service.py` | DSV, reglas de dominio, calculos, idempotencia |
| CRUDService | `services/crud_service.py` | Persistencia DB unica (`@transaction.atomic`) |
| Selector | `services/selectors.py` | QuerySets de lectura con `.only()`, `LIST_FIELDS`, `DETAIL_FIELDS` |

### 4.4. BaseServiceMixin — Mixin Canonico (v3.10.1)

**SSoT:** `apps/tenant/api/mixins.py`

Todos los ServiceMixins heredan de `BaseServiceMixin` que provee:
- `_get_empresa_id_seguro()` — extrae `empresa_id` de forma Zero-Trust (nunca desde `request.user.perfil`)
- `get_empresa()` / `get_empresa_id()` — helpers de contexto
- `NormalizationMixin` — `normalize_data()` en serializers para validacion de entrada

**Prohibido:** usar `request.user.perfil` en serializers directamente. Causa `AttributeError` en GET list. Usar `_get_empresa_id()` helper.

### 4.5. Double Semantic Verification (DSV)

Toda mutacion en `business_service.py` valida que los FKs del payload pertenezcan al tenant actual (`empresa_id`). Esta verificacion es la defensa principal contra ataques IDOR (Insecure Direct Object Reference) a nivel de aplicacion.

La DSV verifica:
1. Que el recurso objetivo exista en el tenant
2. Que todos los FKs referenciados en el payload pertenezcan al mismo tenant
3. Que el usuario autenticado tenga membresia activa

### 4.6. Frontend — Patron de Modulos JS

**Namespace por app:** `window.Sintel.<App>`

**[DOC-M5]** Verificado 2026-08-09 via `grep -ohE "window\.Sintel\.[A-Za-z]+" apps/tenant/*/static/*/js/**/*.js` — la tabla anterior (10 namespaces) omitia 5 namespaces reales:

| Namespace activo | App |
|---|---|
| `window.Sintel.Bancos` | bancos |
| `window.Sintel.Compras` | compras |
| `window.Sintel.Contabilidad` | contabilidad |
| `window.Sintel.Core` | core |
| `window.Sintel.Cotizaciones` | cotizaciones |
| `window.Sintel.Dashboard` | dashboard |
| `window.Sintel.Empleados` | empleados |
| `window.Sintel.Empresa` | empresa |
| `window.Sintel.Gastos` | gastos |
| `window.Sintel.Inventario` | inventario (Productos.Editor, Activos.List, etc.) |
| `window.Sintel.Perfil` | perfil |
| `window.Sintel.Proveedores` | proveedores |
| `window.Sintel.Clientes` | clientes |
| `window.Sintel.Proyectos` | proyectos |
| `window.Sintel.Ventas` | ventas |

Ademas existen 3 sub-namespaces no listados aqui por ser especificos de una feature, no de una app completa: `window.Sintel.ProyectosPresupuesto`, `window.Sintel.Representante` (proveedores), `window.Sintel.TareasDiarias` (proyectos).

Archivos por rol:

| Archivo | Responsabilidad |
|---|---|
| `<app>.api.js` | SSoT de todas las URLs y consumo de endpoints. Sin logica de UI |
| `features/<modelo>_list.js` | Grilla Tabulator (columnas compactas apiladas, KPI strips) o, en el patron actual, solo delegacion de eventos de fila sobre el panel HTMX server-rendered (ver dos patrones abajo) |
| `features/<modelo>_editor.js` | Ciclo de vida del Offcanvas (crear/editar/detalle), listeners de formulario con guard `data-editor-initialized` |

**Dos patrones de grilla coexisten (migracion en curso, ver §1.2):**

**A) django-tables2 + HTMX (patron actual, usar en modulos nuevos).** La grilla es server-rendered: `tables.py` define una `django_tables2.Table`, la vista HTML retorna el fragmento ya paginado/ordenado, y el panel se auto-carga y recarga via atributos HTMX declarativos — sin JS de terceros ni estado de grilla en el cliente.

```html
<div id="<modelo>-panel"
     hx-get="{% url '<app>:<modelo>-tabla' %}"
     hx-trigger="load, <modelo>-updated from:body"
     hx-target="this"
     hx-swap="innerHTML"
     hx-boost="true"></div>
```

- El JS del modulo (`features/<modelo>_list.js`) NO inicializa la grilla — solo delega eventos de fila (`d.querySelector('#<modelo>-panel').addEventListener('click', ...)`, filtrando por clases `.btn-editar-*`/`.btn-eliminar-*`) y expone `window.<Modelo>List.reload()` que dispara `document.body.dispatchEvent(new CustomEvent('<modelo>-updated'))` — el UNICO mecanismo correcto para forzar una recarga tras crear/editar/eliminar.
- **Prohibido:** un listener generico (`htmx:afterSettle` u otro) que refresque MULTIPLES paneles a la vez cuando esos mismos paneles viven dentro del contenedor que observa — causa un bucle de retroalimentacion infinito (incidente real: Auditoria Enterprise 2026-08-06, hallazgo C7, ~47 peticiones/segundo sostenidas en las 4 tablas de `empresa`; ver `documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md` Fase 4). Cada tabla se refresca a si misma via su propio evento `<modelo>-updated`, nunca via un orquestador que reaccione a swaps ajenos.
- **IDs de contenedor/panel deben llevar namespace de app** (`gastos-resoluciones-panel`, no `resoluciones-panel`) cuando el nombre generico del modelo puede repetirse en otro modulo coexistente en el mismo Workspace — el Workspace monta los ~15 modulos simultaneamente en una sola pagina, y `getElementById`/`querySelector` siempre resuelven al primer match del DOM (incidente real: Auditoria Enterprise 2026-08-06, hallazgo C6, colision entre `gastos_list.html` y `empleados_list.html`).

**B) Tabulator (patron legacy, en migracion — no usar en modulos nuevos).** Todas las grillas Tabulator usan `TabulatorFactory.create()` definido en `apps/tenant/core/static/core/js/common/tabulator.factory.js`. Inyecta JWT automaticamente y espera respuesta DRF paginada: `{ count, next, previous, results: [] }`.

**Patron de refresh de tabla Tabulator:** Siempre usar `table.replaceData()` (no `setData()` sin args). Diferir con `setTimeout(() => tbl.replaceData(), 50)` cuando se llama desde un click handler de Tabulator para evitar `Event Target Lookup Error`.

> **[DOC-M4, 2026-08-07]** Validacion directa del codigo (no solo documentacion cruzada) encontro que la migracion esta mas avanzada de lo que `MEMORY.md` describia: 13 de ~17 apps tenant ya tienen `tables.py` — incluyendo `inventario`, `proveedores`, `empresa`, `proyectos`, `clientes`, `perfil`, que `MEMORY.md` listaba como "pendientes" de Fase 5-BIS. Lo que SI sigue pendiente en esas apps es la limpieza de sitios Tabulator puntuales aun vivos dentro de modulos ya migrados (ver §1.2). Antes de asumir que una app necesita migrarse desde cero, verificar si ya tiene `tables.py` — `grep -l "import django_tables2" apps/tenant/*/tables.py`.

**Guard de inicializacion en editors:** Para prevenir doble-inicializacion cuando MutationObserver + htmx:afterSwap disparan simultaneamente:
```javascript
if (form.dataset.editorInitialized === 'true') return;
form.dataset.editorInitialized = 'true';
```

**HTMX (Offcanvas):** Los Offcanvas se cargan via `hx-get` apuntando a `render-offcanvas/crear/`. El backend retorna HTML parcial. Usar siempre `mostrarOffcanvasSeguro(el)` que limpia backdrops acumulados antes de llamar `show()`.

**Helpers globales de infraestructura:** `apps/tenant/core/static/core/js/common/` — disponibles en todo el tenant.

| Helper | Archivo |
|---|---|
| `UIManager` | `ui-manager.js` — notificaciones, manejo de errores 400, offcanvas |
| `TabulatorFactory` | `tabulator.factory.js` — creacion de grillas con JWT auto-inyectado |
| `Sintel.Core.Http` | `core/js/lib/core-http.js` — cliente HTTP unico (F32), retorna `{ok, status, data}`, nunca lanza en 4xx/5xx, JWT con refresh, CSRF, `upload()` explicito para FormData |

### 4.7. Procesamiento Asincrono

Las tareas masivas, calculos sobre datos historicos e integraciones de terceros se despachan a workers Celery via `.delay()`. Toda tarea define politicas de reintentos (`max_retries`). Al agotar reintentos, el payload se inserta en un registro `FailedTenantTask` para observabilidad y reencola manual.

---

## 5. Aislamiento Cross-Schema y Gobernanza de Datos

### 5.1. Core Membership Bridge

**SSoT del bridge:** `apps/tenant/core/services/membership.py`

Las apps tenant **no pueden** importar directamente desde `apps.public.*`. El bridge es la unica interfaz autorizada para consultar datos del esquema publico.

| Operacion del Bridge | Descripcion |
|---|---|
| `check_membership(user, empresa)` | Verifica membresia activa. Retorna `TenantMembership` o `None` |
| `check_membership_exists(user, empresa)` | Retorna `bool` para verificacion rapida |
| `check_admin_membership(user, empresa)` | Verifica membresia con rol ADMIN |
| `check_primary_admin(empresa)` | Retorna el `TenantMembership` del administrador primario |
| `get_user_role(user, empresa)` | Retorna el string del rol o `None` |
| `get_primary_domain(empresa)` | Retorna el dominio primario del tenant |
| `verify_invitation(token)` | Valida token de invitacion |

**Excepcion:** Solo `apps/tenant/core/` y `apps/tenant/api/` (permisos centrales) pueden importar desde `apps.public`. Ninguna otra app tenant tiene esta autorizacion.

### 5.2. Reglas de Aislamiento de Assets (CSS/JS)

Todos los archivos `.html` y `.js` deben residir dentro del nucleo de la app a la que pertenecen.

| Tipo | Ruta obligatoria |
|---|---|
| Templates tenant | `apps/tenant/<app>/templates/tenant/<app>/` |
| JS estatico tenant | `apps/tenant/<app>/static/<app>/js/` |
| Templates public | `apps/public/<app>/templates/<app>/` |
| JS estatico public | `apps/public/<app>/static/<app>/js/` |
| Helpers globales (excepcion controlada) | `apps/tenant/core/static/core/js/common/` |

Cada app define un template `assets_<app>.html` que centraliza la inclusion de sus scripts y estilos. Prohibidos: scripts compartidos entre modelos no relacionados, templates monoliticos, referencias cruzadas de assets entre apps.

**Helper global `offcanvas.helper.js` (FE-A5, PLAN_UNICO_CORRECCIONES.md Fase 5):** `apps/tenant/core/static/core/js/common/offcanvas.helper.js` expone `window.Sintel.Core.mostrarOffcanvasSeguro(elOrId)` — SSoT que reemplaza las 16 reimplementaciones locales encontradas en la auditoria 2026-07-26. Se carga globalmente desde `assets_core.html`, antes de cualquier modulo. Todo codigo nuevo que abra un Bootstrap Offcanvas debe usar este helper en vez de reimplementar el patron dispose+create.

**Estado dual de `http.js` (FE-M4) — RESUELTO en F32 (2026-08-13).** El cluster de deuda de transporte HTTP/CSRF/JWT que F31 dejo explicitamente diferido (2 copias identicas de `http.js` + una tercera version divergente ganando en produccion por orden de carga, mas 6 `*.api.js` con su propia reimplementacion de fetch+CSRF+JWT) se cerro por completo en F32 ("Frontend Transport Consolidation & Browser Validation", F32.1-F32.8). Resultado: `window.Sintel.Core.Http` (`core/js/lib/core-http.js`) es ahora el **unico** cliente HTTP del frontend tenant. Los 3 archivos `http.js`/duplicados se eliminaron (`core/static/js/http.js` y `core/static/core/js/lib/http.js`, confirmado sin consumidores vivos via grep exhaustivo antes de cada borrado); los 52 consumidores reales (6 `*.api.js` que reimplementaban fetch por su cuenta + 46 archivos adicionales que delegaban en el `http.js` viejo) se migraron uno por uno, cada migracion verificada con navegador real (Playwright contra `qaisotest.sintel.net.co`) antes de commitear. El riesgo que F31 señalo como bloqueante (romper auth/CSRF/uploads sin poder verificar en navegador) se resolvio construyendo infraestructura E2E real en la misma fase (F32.5) en vez de aplazarlo mas. Contrato completo: `documentacion/F32_3_CORE_HTTP_CONTRACT.md`. Auditoria y migracion detalladas: `F32_1_2_TRANSPORT_AUDIT.md`, `F32_6_TRANSPORT_MIGRATION_STATUS.md`, `F32_7_TRANSPORT_CONSOLIDATION_AUDIT.md`, `F32_8_REGRESSION_MATRIX.md`.

### 5.3. Prohibiciones de Gobernanza

| Regla | Detalle |
|---|---|
| Sin emojis en `.py` | Causan `SyntaxError` → Django 500 |
| `SintelTenantBaseModel` obligatorio | Todos los modelos tenant lo heredan; nunca `models.Model` directamente |
| `empresa_id` en toda query | Sin `.all()` ni `.filter()` sin empresa |
| `.only()` obligatorio | Toda queryset especifica campos |
| Sin Signals para logica de negocio | Todo en Service Layer |
| Sin `.py` nuevos fuera del Service Layer | Requiere autorizacion explicita del usuario |
| `apps/public/` bloqueado | Requiere RFC + etiqueta `needs-admin-approval` |
| UUID como lookup field | `BaseTenantViewSet` expone UUID; nunca PKs enteras en URLs |
| FK a `perfil.TenantProfile` | Nunca FK a `settings.AUTH_USER_MODEL` desde modelos tenant |
| `parseInt()` sobre UUID | PROHIBIDO — `parseInt("9abc...",10)=9` corrompe UUID a entero parcial |
| `getOrCreateInstance().show()` HTMX | PROHIBIDO — acumula backdrops; usar `mostrarOffcanvasSeguro(el)` |
| `setData()` sin args en Tabulator | Usar `replaceData()` para forzar nuevo fetch del servidor |
| `py_compile` hook | PostToolUse hook valida toda edicion `.py`. Corregir antes de continuar |
| `if settings.DEBUG:` en autorizacion | PROHIBIDO — nunca condicionar una verificacion de permiso/membresia/rol al valor de `DEBUG`. Incidente real: los 5 permisos SSoT de `apps/tenant/api/permissions.py` mas 3 `get_permissions()` de ViewSets tenian `if settings.DEBUG: return True`, desactivando por completo la verificacion de pertenencia al tenant en cualquier instancia con `DEBUG=True` — causa raiz de una fuga completa de datos entre tenants (Auditoria Enterprise 2026-08-06, hallazgo C1, ver `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`). Verificado limpio (`grep DEBUG apps/tenant/api/permissions.py` sin resultados) el 2026-08-07 |
| Comentarios `{# #}` multilinea en templates Django | PROHIBIDO — el motor de plantillas de Django no reconoce `{#`/`#}` si abarcan mas de una linea; el bloque completo se renderiza como texto HTML literal visible al usuario. Usar `{% comment %}...{% endcomment %}` para comentarios multilinea, o colapsar a una sola linea. Hallazgo transversal confirmado en 9 archivos / 10 bloques preexistentes (ver M1 en `documentacion/PLAN_PRUEBASUI_PRIVADAS.md`) mas 3 instancias nuevas introducidas y corregidas durante la Auditoria Enterprise 2026-08-06 (Fases 3 y 4 de `documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md`) |
| Nombre de carpeta en `dependencies` de migraciones | PROHIBIDO — usar el `app_label` real (`grep label apps/tenant/<app>/apps.py`), no el nombre de carpeta. 10 de 17 apps tenant sobre-escriben `label` (ver `.agents/skills/backend/django-tenant.md`). Incidente real: migracion `0020` de `proyectos` referenciaba `('proyectos', ...)` en vez de `('tenant_proyectos', ...)`, bloqueando `migrate_schemas` — y por tanto el arranque de `web` — para todo el proyecto. Ver `apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` (FIX v3.10.5). Mejor practica: dejar que `makemigrations` genere `dependencies` automaticamente |

### 5.4. Principios de Idempotencia

Toda operacion de mutacion (creacion/actualizacion) o ingesta de datos debe ser idempotente. La base de datos respalda esto mediante constraints unicos. Los servicios manejan conflictos via Silent Success o Upsert.

---

## 6. Capa de Integracion Contable Centralizada (Modelo Pull)

### 6.1. Principio Fundamental

Ningun asiento contable se crea directamente desde apps fuente. El `Contabilizador` de `contabilidad` extrae activamente los documentos pendientes. Las apps fuente no conocen ni importan desde `contabilidad`.

**Patron Push (PROHIBIDO):** app fuente llama funcion de contabilidad.
**Patron Pull (OBLIGATORIO):** extractor de contabilidad lee app fuente.

### 6.2. Desacoplamiento Contable Completo (v3.10.2)

**Estado:** COMPLETADO — 2026-05-28

Los campos `cuenta_contable_uuid` / `cuenta_*_uuid` fueron **eliminados de todos los modelos de negocio**. Contabilidad es la unica propietaria de mapeos PUC. Las apps fuente son ahora Pure Pull.

| App | Campos Eliminados | Migracion |
|---|---|---|
| proveedores | `codigo_contable`, `cuenta_contable_uuid` | 0007 |
| clientes | `cuenta_contable_uuid` | 0007 |
| inventario | `cuenta_inventario_uuid`, `cuenta_costo_uuid`, `cuenta_ingreso_uuid`, `cuenta_activo_uuid`, `cuenta_depreciacion_uuid` | 0009 |
| facturas | `cuenta_contable_uuid` | 0026 |
| gastos | `cuenta_gasto_uuid` | 0020 |
| empleados | `cuenta_contable_uuid` (Devengo) | 0010 |

**Total:** 15 campos eliminados, 6 apps, 30 archivos modificados. `0 referencias` en codigo vivo.

### 6.3. Paquete de Integracion

**Ruta:** `apps/tenant/contabilidad/integracion/`

| Modulo | Responsabilidad |
|---|---|
| `dtos.py` | DTOs inmutables (`@dataclass(frozen=True)`) — contrato entre apps fuente y Contabilizador |
| `contabilizador.py` | Orquestador unico — valida, resuelve cuentas, construye y persiste asientos atomicamente |
| `resolver.py` | Mapea (`tipo_transaccion` + `concepto`) a codigo PUC via `ReglaContable` por tenant |
| `validadores.py` | Validators stateless — cuadratura, periodo abierto, documento origen existe |
| `excepciones.py` | Jerarquia `ContabilidadError` y subclases |
| `extractores/base.py` | `AbstractExtractor` — interfaz comun |
| `extractores/gastos.py` | `ExtractorGastos` — extrae `DocumentoSoporte` pendientes (sin `cuenta_gasto_uuid`) |
| `extractores/inventario.py` | `ExtractorInventario` — implementado real desde F22 (antes deshabilitado). Extrae `MovimientoInventario` con `producto` no nulo cuyo `tipo` este en `ENTRADA_COMPRA`/`SALIDA_VENTA`/`ENTRADA_AJUSTE`/`SALIDA_BAJA`/`SALIDA_CONSUMO`/`ENTRADA_DEVOLUCION` (mapeados a `TipoTransaccion` ya existente en `dtos.py`, sin crear contrato nuevo). `TRASLADO_SALIDA`/`TRASLADO_ENTRADA` y movimientos de `ActivoFijo` quedan deliberadamente excluidos. Registrado en `EXTRACTORES_DISPONIBLES` de `backfill_contabilidad.py`. **[DOC-M11, F23]** `SALIDA_VENTA` ya tiene datos reales — `VentaBusinessService.procesar_y_facturar_venta()` genera esos movimientos, el extractor los detecta sin ningun cambio propio. 20/20 tests F22 + 9/9 tests F23 reales (`documentacion/F22_TEST_MATRIX.md`, `F23_TEST_MATRIX.md`) |
| `extractores/facturas.py` | `ExtractorFacturas` — extrae `Factura` ACEPTADA pendientes (sin `cuenta_contable_uuid`) |
| `extractores/nomina.py` | `ExtractorNomina` — extrae todos los `Devengo` no anulados (sin filtro por cuenta) |

**Nota v3.10.2:** Los extractores ya no usan `cuenta_hint` desde modelos origen. Las cuentas se resuelven exclusivamente via `ReglaContable` segun `tipo_transaccion` y `concepto`. El filtro `cuenta_contable_uuid__isnull=False` fue eliminado de `ExtractorNomina`.

### 6.4. DTOs — Contrato Inmutable

Los DTOs son frozen dataclasses que encapsulan el contexto economico del documento origen:

- `TransaccionEconomica` — envelope principal con tipo, fecha, tercero (snapshot), lineas y documento origen
- `LineaTransaccion` — concepto, monto y lado del asiento (`'DEBE'` o `'HABER'`)
- `ImpuestoLinea` — tipo, valor y lado (impuestos van siempre a `'HABER'`)
- `TerceroSnapshot` — snapshot del tercero sin FK (inmutable en el tiempo)
- `DocumentoOrigen` — app_label, modelo, id para idempotencia

El campo `empresa_id` no va dentro del DTO — lo inyecta el `Contabilizador` desde su contexto. La idempotencia se garantiza via constraint UNIQUE sobre `documento_origen` en `AsientoContable`.

### 6.5. Numero de Asiento — Formato Canonico

| Tipo | Formato |
|---|---|
| Normal | `ASI-{YYYYMMDD}-{UUID8}` |
| Reversal | `RVER-{YYYYMMDD}-{UUID8}` |

El numero lo genera exclusivamente el `Contabilizador._construir_asiento()`. Prohibido que el caller externo lo provea.

### 6.6. APP_ORIGEN_PREFIJOS — SSoT de Codigos PUC

**SSoT:** `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS`

Todos los codigos PUC de vinculacion contable para todas las apps de negocio se obtienen exclusivamente desde este diccionario. Prohibido hardcodear prefijos en apps fuente.

| App | Ejemplos de prefijos autorizados |
|---|---|
| `facturas` | `1305`, `4135`, `4175`, `2365`, `2368`, `240805` |
| `clientes` | `1305`, `1375`, `4135`, `413505`, `413510` |
| `gastos` | `233505`, `51`, `6`, `2365`, `240810` |
| `empleados` | `5105`, `5110`, `2370`, `25`, `51` |
| `inventario` | `143505`, `1435`, `6135`, `4135`, `51`, `15` |
| `proveedores` | `2205`, `2335`, `2365`, `2805`, `280505` |

### 6.7. Retenciones — ADR-001 Pull Model

**SSoT:** `docs/ADR-001-retention-pull-model.md`

El modelo `Retencion` vive en `contabilidad`. Las apps fuente nunca almacenan montos de retencion directamente. Para crear o consultar retenciones se usa `RetencionesService` de `apps/tenant/contabilidad/services/retenciones_service.py`.

**Endpoints de retenciones:**

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/contabilidad/retenciones/obtener-por-tercero/` | GET | Configuracion de retencion para un NIT dado |
| `/api/v1/contabilidad/retenciones/obtener-por-documento/` | GET | Retenciones de un documento origen |
| `/api/v1/contabilidad/retenciones/` | GET / POST | Listado y creacion |

### 6.8. Activacion de Extractores

Los extractores se invocan exclusivamente desde management commands o tareas Celery periodicas. Nunca desde ViewSets ni Signals.

```bash
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
```

---

## 7. Decisiones Arquitectonicas Relevantes (ADRs)

> **Nota de gobernanza (2026-08-08):** esta tabla tenia una numeracion ADR duplicada — `ADR-002`
> y `ADR-003` se usaban aqui para dos decisiones tecnicas antiguas (nunca formalizadas en su
> propio archivo `docs/ADR-NNN-*.md`), mientras que esos mismos numeros ya estaban en uso por
> archivos reales y activamente referenciados en codigo (`docs/ADR-002-public-schema-api-dual-registration.md`,
> `docs/ADR-003-contexto-organizacional-sede-area.md`). Verificado por grep: **cero** referencias
> de codigo usan "ADR-002"/"ADR-003" con el significado antiguo — todas (docenas, en
> `apps/tenant/api/`, `apps/tenant/compras/`, `apps/tenant/core/services/organizational_*.py`,
> comentarios de tests) usan el significado nuevo. Resuelto conservando los 4 archivos
> `docs/ADR-NNN-*.md` existentes sin renombrar (son la convencion activa) y retirando el prefijo
> "ADR-NNN" de las 2 decisiones antiguas sin archivo propio (quedan documentadas como decisiones
> tecnicas historicas, no como ADRs numerados) — ver "Organizational Scope Framework, Fase 1" en
> `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`.

| ADR | Titulo | Estado | Fecha | Documento |
|---|---|---|---|---|
| ADR-001 | Retencion Pull Model (v3.7.1) — Contabilidad owns Retencion | ACCEPTED | 2026-05-13 | `docs/ADR-001-retention-pull-model.md` |
| ADR-002 | Registro Dual de Endpoints en Schemas Publico y Tenant | ACCEPTED | 2026-06-09 | `docs/ADR-002-public-schema-api-dual-registration.md` |
| ADR-003 | Contexto Organizacional (Empresa -> Sede -> Area) — Fundamentos + piloto `compras` | ACCEPTED (alcance parcial, ver nota DOC-M5 en §3.6) | 2026-08-07 | `docs/ADR-003-contexto-organizacional-sede-area.md` |
| ADR-004 | Organizational Context Framework (OCF) — Modelo de Diseño | ACCEPTED (parcialmente implementado, ver Adenda 2026-08-09 en el propio archivo) | 2026-08-07 (adenda 2026-08-09) | `docs/ADR-004-organizational-context-framework-diseno.md` |
| ADR-005 | Organizational Scope Framework (OSF) — Contrato Independiente y Rollout sin Migracion de Esquema | ACCEPTED (parcialmente implementado) | 2026-08-09 | `docs/ADR-005-organizational-scope-framework.md` |

> **[DOC-M6, 2026-08-09] ADR-004/ADR-005 y el plan de consolidacion OCF/OSF — cerrado, verificado
> y commiteado.** El proyecto de consolidacion OCF/OSF (`documentacion/
> ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md`, 12 fases, FASE 0-12) audito codigo real (no solo
> `MEMORY.md`) linea por linea, con ejecucion real de tests (no solo lectura), y cerro con
> **🟢 ORGANIZATIONAL BASELINE**: Codigo + Tests + ADR + Documentacion + Git alineados y
> verificados. `docs/ADR-004-*.md` gano una "Adenda 2026-08-09" que actualiza su Estado a ACCEPTED
> (parcial) y documenta 2 divergencias reales entre lo diseñado y lo construido (`OrganizationalScope`
> NO se construye a partir de `OrganizationalContext`, contrario al diagrama original;
> `OrganizationalSelector` como clase nunca se construyo — su rol lo cumplen funciones puras +
> metodos de las dataclasses). `docs/ADR-005-organizational-scope-framework.md` (nuevo) formaliza
> 2 decisiones arquitectonicas reales tomadas explicitamente con el usuario durante el proyecto OSF
> (independencia de `OrganizationalScope` respecto a `OrganizationalContext`; `filter_by_scope_null_safe()`
> como patron de rollout SIN migracion de esquema para las 6 apps con `sede` historicamente en NULL).
> Durante la consolidacion se encontraron y **corrigieron** 2 bugs reales de aislamiento (ver §3.6).
> **Ya esta commiteado**: 5 commits (`0295932`..`34fc020`, ver `documentacion/FASE11_CONSOLIDACION_GIT.md`)
> — el ultimo commit del repositorio es `34fc020`, no `371f19d` como indicaba la version anterior de
> este documento. Detalle completo: `documentacion/OCF_TECHNICAL_AUDIT.md`,
> `documentacion/OSF_TECHNICAL_AUDIT.md`, `documentacion/ORGANIZATIONAL_CONTRACT.md`,
> `documentacion/ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` (cierre). **Pendiente, fuera de esta
> consolidacion por decision explicita** (no por omision): FASE 13/14 del plan (extension del
> Knowledge Graph EKG con capas organizacionales + gobernanza automatica) — ver justificacion en
> `ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` §9.

**Decisiones tecnicas historicas (anteriores a la convencion `docs/ADR-NNN-*.md`, sin archivo dedicado propio):**
- **Desacoplamiento Contable Total** (2026-05-28, COMPLETED) — Eliminacion de `cuenta_*_uuid` en
  apps fuente. Impacto: Contabilidad es la unica propietaria de mapeos PUC; las apps fuente son
  Pure Pull (zero coupling); los extractores resuelven cuentas exclusivamente via `ReglaContable`.
  El checklist de esta refactorizacion no quedo formalizado en un documento aparte (referencia
  rota a `REFACTORIZAR_DESACOPLAMIENTO_CONTABLE_FRAMEWORK.md` retirada en Fase 9, DOC-A4 — el
  archivo nunca existio).
- **TareaCorta.cliente FK PROTECT → SET_NULL** (2026-05-29, APPLIED) — permite eliminacion de
  clientes inactivos sin bloquear por tareas cortas historicas asociadas.

---

## 8. Ecosistema de Agentes de Inteligencia Artificial

### 8.1. Principio de Diseno

El asistente IA es un metodo de entrada rapida para lineas de asiento contable en el flujo Manual On-Demand. La validacion local (cuadratura, nivel 6, `TipoComprobante`) es siempre la fuente de verdad final. La IA nunca persiste datos sin confirmacion explicita del usuario.

### 8.2. Agentes Especializados por Dominio

| Agent ID | App Label | Conocimiento NIIF Colombia | Modelo |
|---|---|---|---|
| `FacturacionAgent` | `facturas` | CxC (1305), IVA generado (240805), Retefuente (2365xx), ReteICA (2368xx), Ingresos (4135xx) | `claude-haiku-4-5-20251001` |
| `GastosAgent` | `gastos` | CxP Proveedor (2335xx), IVA descontable (240810), Retefuente (2365xx), Gastos operativos (51xx) | `claude-haiku-4-5-20251001` |
| `NominaAgent` | `empleados` | Salarios (5105xx), Aportes seguridad social (2370xx), Obligaciones laborales (25xx) | `claude-haiku-4-5-20251001` |
| `InventarioAgent` | `inventario` | Inventario (1435xx), CMV (6135xx), Ingresos (4135xx) | `claude-haiku-4-5-20251001` |

### 8.3. Flujo del Orquestador

```
POST /api/v1/contabilidad/pendientes/asistente-ia/
    |
    +-- AsistenteIAInputSerializer.validate()
    |
    +-- ContabilidadBusinessService.sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)
    |       +-- filtrar_cuentas_por_app_origen(qs, app_label) → cuentas nivel-6 del tenant
    |       +-- anthropic.messages.create(model='claude-haiku-4-5-20251001', ...)
    |       +-- Validar cuenta: nivel==6, activa==True, empresa_id (DSV)
    |       +-- Validar cuadratura: |Sum(Debe) - Sum(Haber)| < 0.01
    |
    +-- Response({ lineas: [{cuenta_codigo, cuenta_nombre, debe, haber, descripcion}, ...] })
```

### 8.4. Configuracion y Compliance

| Variable de entorno | Descripcion | Obligatoria |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key del tenant Anthropic | Si |

**Regla critica:** Prohibido persistir asientos desde la IA sin confirmacion explicita del usuario. El boton "Generar Asiento" siempre requiere cuadratura local < 0.01.

### 8.5. Agentes de Codigo (Claude Code)

El archivo `AGENTS.md` es el contexto primario para cualquier agente de codigo. El archivo `MEMORY.md` en la raiz del proyecto es la fuente canonica del estado actual, decisiones arquitectonicas recientes (ADRs) y progreso activo.

Regla para agentes de codigo: al iniciar cualquier sesion o tarea nueva, leer `MEMORY.md` primero, luego `AGENTS.md`, luego el `.agent/AUDITORIA_FLUJO_*.md` de la app objetivo.

---

## 9. Endpoints API REST

**SSoT de endpoints:** `config/api_urls.py` — **[DOC-M5, corregido]** 203 lineas, 17 modulos montados con try/except resiliente por app (antes reportado como "149 lineas, 14 modulos" — desactualizado; la tabla de abajo tambien omitia `bancos` por completo, ya corregido).

| Prefijo | App | Modelos Principales |
|---|---|---|
| `/api/v1/empresas/` | empresa | Empresa, Sede, Area |
| `/api/v1/facturas/` | facturas | Factura, ItemFactura, NotaCredito |
| `/api/v1/contabilidad/` | contabilidad | CuentaContable, AsientoContable, Retencion, ReglaContable, PlantillaContable |
| `/api/v1/inventario/` | inventario | Producto, Servicio, ActivoFijo, MovimientoInventario, HistorialServicio, CategoriaItem, TrasladoInventario (F21, `/inventario/traslados/`) |
| `/api/v1/perfil/` | perfil | TenantProfile |
| `/api/v1/dashboard/` | dashboard | Metricas consolidadas |
| `/api/v1/core/` | core | Auth bridge, onboarding, configuraciones globales, contexto organizacional (`/core/contexto/`) |
| `/api/v1/empleados/` | empleados | Empleado, Contrato, Devengo, ResolucionDIAN |
| `/api/v1/gastos/` | gastos | DocumentoSoporte, ResolucionDIAN |
| `/api/v1/bancos/` | bancos | CuentaBancaria, ExtractoBancario, TransaccionBancaria |
| `/api/v1/proveedores/` | proveedores | Proveedor, CuentasPagar, Representante |
| `/api/v1/clientes/` | clientes | Cliente, ContactoCliente, Cartera |
| `/api/v1/cotizaciones/` | cotizaciones | Cotizacion, CotizacionItem |
| `/api/v1/proyectos/` | proyectos | Proyecto, TareaCorta, AsignacionPersonal |
| `/api/v1/compras/` | compras | OrdenCompra, ItemOrdenCompra, PlantillaOrdenCompra, RecepcionCompra (F21, `/compras/recepciones/`) |
| `/api/v1/ventas/` | ventas | Venta, ItemVenta, ResolucionFacturacion |
| `/api/v1/impuestos/` (public) | impuestos | Catalogo DIAN |

**`/mcp/` (nuevo, DOC-M5):** endpoint separado (no en `api_urls.py`, montado directo en `config/urls_public.py`/`config/urls_tenant.py`) que expone ViewSets decorados con `@mcp_viewset()` como herramientas MCP — ver §1.1.

**Formato de respuesta paginada (estandar DRF):**
```json
{ "count": 100, "next": "...", "previous": "...", "results": [...] }
```

**Lookup field:** todas las URLs usan UUID: `/api/v1/<app>/{uuid}/`

---

## 10. Indice General de Fuentes de Verdad

### 10.1. Documentos de Referencia Global

| SSoT | Ruta | Descripcion |
|---|---|---|
| Arquitectura global | `documentacion/arquitectura_general.md` | Este documento |
| Reglas de desarrollo | `AGENTS.md` | Reglas estrictas e inmutables para todo el proyecto |
| Estado del proyecto | `MEMORY.md` (raiz) | Estado actual, ADRs activos, progreso en curso |
| Rutas API | `config/api_urls.py` | Unica fuente de verdad para endpoints REST |
| Settings | `config/settings.py` | Configuracion Django, JWT, Celery, SHARED/TENANT_APPS |
| Codigos PUC por app | `apps/tenant/contabilidad/services/selectors.py:APP_ORIGEN_PREFIJOS` | Prefijos autorizados por app de negocio |
| Roles de tenant | `apps/tenant/perfil/models.py:TenantProfile.rol` | ADMIN / OPERADOR / VISOR |
| Permisos DRF | `apps/tenant/api/permissions.py` | Unica fuente para importar permisos en ViewSets |
| Autenticacion | `apps/tenant/api/base.py:BaseTenantViewSet` | Dual-Auth centralizado (JWT + Session) |
| BaseServiceMixin | `apps/tenant/api/mixins.py:BaseServiceMixin` | Mixin canonico para todos los ServiceMixins |
| Modelo base tenant | `apps/tenant/core/models.py:SintelTenantBaseModel` | Herencia obligatoria para todos los modelos tenant |
| Bridge cross-schema | `apps/tenant/core/services/membership.py` | Unica interfaz autorizada para consultar esquema public |
| ADR Retenciones | `docs/ADR-001-retention-pull-model.md` | Contabilidad owns Retencion, Pull Model |
| ADR Dual-Registration API Publica | `docs/ADR-002-public-schema-api-dual-registration.md` | Endpoints accesibles desde `home.sintel.net.co` — registro dual public/tenant |
| Auditoria Enterprise UI (2026-08-06) | `documentacion/PLAN_PRUEBASUI_PRIVADAS.md` | Informe de auditoria via UI real, 23 hallazgos clasificados; marcadores `[CORREGIDO]` indican los ya remediados |
| Remediacion Fase 1 (Criticos Seguridad) | `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md` | Detalle 10-secciones de C1/C2/C3 + hallazgo de onboarding |
| Remediacion Fases 2-8 | `documentacion/REMEDIACION_FASES2-8_AUDITORIA_ENTERPRISE.md` | Detalle 10-secciones de C4/C5/C6/C7, onboarding, regresion y documentacion |
| Consolidacion OCF/OSF (2026-08-09) | `documentacion/ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md` | Indice maestro de las 12 fases (auditoria de codigo real, ADR-004/005, matriz de cobertura de 17 apps, piloto `compras`, `facturas`, `Ventas->Facturas`, rollout controlado, consolidacion git) — enlaza los 12 documentos de detalle. Cierre: `documentacion/ORGANIZATIONAL_SCOPE_BASELINE_FINAL.md` |
| Knowledge Graph Organizacional + Gobernanza Automatica (2026-08-09) | `documentacion/F13_F14_FINAL_REPORT.md` | `tools/organizational_governance/` (grafo + motor de reglas, independiente de `tools/ekg/`) — estado fase por fase en `documentacion/F13_F14_EXECUTION_STATUS.md`, findings en `documentacion/GOVERNANCE_REMEDIATION_PLAN.md` |
| Integracion Inter-App + Empresa/Sede/Area (2026-08-09) | `documentacion/F15_F20_FINAL_REPORT.md` | Grafo de dependencias inter-app (`dependencies.py`), matriz de obligatoriedad organizacional (`ORGANIZATIONAL_FIELD_MATRIX.md`), estado de rollout por app (`F17_SEDE_ROLLOUT_STATUS.md`), procesos de negocio colombianos (`F18_COLOMBIAN_BUSINESS_FLOWS.md`) — cobertura tecnica, no certificacion legal (`COLOMBIA_COMPLIANCE_TRACEABILITY.md`) |
| Compras -> Recepcion -> Inventario -> Sede -> Kardex -> Traslados -> Contabilidad (F21, 2026-08-09) | `documentacion/F21_FINAL_REPORT.md` | Cierra la brecha `compras->inventario`: `RecepcionCompra`/`RecepcionCompraItem` (`documentacion/F21_RECEPCION_INVENTARIO.md`), `TrasladoInventario` entre sedes (`documentacion/F21_TRASLADOS_SEDES.md`), decisiones de alcance organizacional (`F21_ORGANIZATIONAL_DECISIONS.md`), 16/16 tests reales (`F21_TEST_MATRIX.md`), estado fase por fase (`F21_EXECUTION_STATUS.md`) |
| Integracion Contable Real de Inventario (F22, 2026-08-10) | `documentacion/F22_FINAL_REPORT.md` | Activa `ExtractorInventario` (Pull real, antes deshabilitado): matriz de movimientos y contrato contable (`documentacion/F22_ACCOUNTING_CONTRACT.md`), flujo operativo (`F22_INVENTORY_ACCOUNTING.md`), auditoria de inventario/extractor (`F22_INVENTARIO_BASELINE.md`, `F22_EXTRACTOR_INVENTARIO_BASELINE.md`), analisis de backfill historico (`F22_HISTORICAL_BACKFILL_ANALYSIS.md`), 20/20 tests reales + 19/19 F21 sin regresion (`F22_TEST_MATRIX.md`), estado fase por fase (`F22_EXECUTION_STATUS.md`) |
| Venta -> Inventario -> Kardex -> Costo -> Contabilidad (F23, 2026-08-10) | `documentacion/F23_FINAL_REPORT.md` | Cierra la brecha `ventas->inventario`: contrato Venta->Inventario (`documentacion/F23_SALE_INVENTORY_CONTRACT.md`), politica del evento de salida (`F23_INVENTORY_ISSUE_POLICY.md`), auditoria de ventas/facturas (`F23_VENTAS_BASELINE.md`, `F23_FACTURAS_BASELINE.md`), bug de atomicidad real encontrado y corregido en `procesar_y_facturar_venta()`, 9/9 tests reales + 45/45 en regresion consolidada F21+F22+F23 (`F23_TEST_MATRIX.md`), estado fase por fase (`F23_EXECUTION_STATUS.md`) |

### 10.2. Documentos de Auditoria por App (SSoT por modulo)

> **Regla (AGENTS.md §16):** antes de modificar cualquier app, leer su documento de auditoria.

| App | Ruta | SSoT de auditoria |
|---|---|---|
| `core` (tenant) | `apps/tenant/core/` | `apps/tenant/core/.agent/AUDITORIA_FLUJO_CORE.md` |
| `empresa` | `apps/tenant/empresa/` | `apps/tenant/empresa/.agent/AUDITORIA_EMPRESA.md` |
| `perfil` | `apps/tenant/perfil/` | `apps/tenant/perfil/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `facturas` | `apps/tenant/facturas/` | `apps/tenant/facturas/.agent/AUDITORIA_FLUJO_COMPLETO_FACTUR.md` |
| `contabilidad` | `apps/tenant/contabilidad/` | `apps/tenant/contabilidad/.agent/AUDITORIA_COMPLETA_CONTABILIDAD.md` |
| `gastos` | `apps/tenant/gastos/` | `apps/tenant/gastos/.agent/AUDITORIA_FLUJO_COMPLETO_GASTOS.md` |
| `inventario` | `apps/tenant/inventario/` | `apps/tenant/inventario/.agent/AUDITORIA_FLUJO_INVENTARIO.md` |
| `empleados` | `apps/tenant/empleados/` | `apps/tenant/empleados/.agent/AUDITORIA_FLUJO_EMPLEADOS.md` |
| `cotizaciones` | `apps/tenant/cotizaciones/` | `apps/tenant/cotizaciones/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `clientes` | `apps/tenant/clientes/` | `apps/tenant/clientes/.agent/AUDITORIA_FLUJO_CLIENTES.md` |
| `proveedores` | `apps/tenant/proveedores/` | `apps/tenant/proveedores/.agent/AUDITORIA_FLUJO_COMPLETO_PROVE.md` |
| `proyectos` | `apps/tenant/proyectos/` | `apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `dashboard` | `apps/tenant/dashboard/` | `apps/tenant/dashboard/.agent/` |
| `bancos` | `apps/tenant/bancos/` | `apps/tenant/bancos/.agent/AUDITORIA_FLUJO_COMPLETO.md` |
| `compras` | `apps/tenant/compras/` | `apps/tenant/compras/.agent/AUDITORIA_FLUJO_COMPRAS.md` |
| `ventas` | `apps/tenant/ventas/` | `apps/tenant/ventas/.agent/ARQUITECTURA_VENTAS.md` |
| `landing` | `apps/tenant/landing/` | `apps/tenant/landing/.agent/AUDITORIA_FLUJO_LANDING.md` |

### 10.3. Cobertura de Tests

> **[DOC-M5, recontado 2026-08-09; DOC-M6 nota de estado]** Tabla recontada por conteo directo de `apps/tenant/<app>/tests/test_*.py` + `tests/tenant/<app>/test_*.py`. El conteo anterior (2026-08-03, tabla de abajo la reemplaza) esta muy desactualizado — el trabajo de Contexto/Alcance Organizacional (§7) y otras fases agregaron un numero grande de tests nuevos. Los tests de OCF/OSF especificamente (las suites `test_organizational_*.py`/`test_scope_*_fN.py` citadas en la columna de aislamiento) **ya estan commiteados** (commit `1d19d8f`, ver §7) — 53/53 (core) y 20/20 (compras) confirmados pasando por ejecucion real. Los tests nuevos de OTRAS lineas de trabajo (Auditoria Enterprise, EKG) siguen sin commitear. No incluye suites cross-cutting no atribuibles a una sola app (`tests/api`, `tests/celery*`, `tests/general`, `tests/multitenant`, `tests/smoke`, etc.) — el total real de archivos `test_*.py` en todo el repositorio (excluyendo `venv/`) era **401** al momento del conteo DOC-M5 (2026-08-09, antes de esta sincronizacion; no se re-conto tras los commits porque commitear no cambia el numero de archivos en disco).

| App | Archivos de Test (in-app + centralizado) | `test_multitenant_isolation*.py` / `test_cross_tenant*.py`? |
|---|---:|---|
| core | 63 | — |
| facturas | 45 [DOC-M14: +1, `test_devolucion_nota_credito.py`] | Parcial (`test_multitenant_isolation_tabla_html.py`) |
| empresa | 29 | — |
| empleados | 13 | Parcial (`test_multitenant_isolation_tablas_html.py`, nuevo) |
| gastos | 13 [DOC-M13: +1, F25 `test_f25_procesar_gasto_atomicidad.py`] | ✅ Completo (`test_multitenant_isolation.py`) |
| dashboard | 12 | — |
| contabilidad | 14 [DOC-M12: +2, F24 `test_f24_e2e_circuito_completo.py`, `test_f24_e2e_multitenant_dsv.py`] [DOC-M10: +3, F22 `test_f22_extractor_inventario_{mapping,integration,multitenant}.py`] | ✅ Nuevo (`test_multitenant_isolation.py`); +2 tests reales de 2 schemas F22/F24 |
| clientes | 8 | — |
| perfil | 6 | — |
| inventario | 9 [DOC-M9: +1, F21 `test_f21_traslado_inventario.py`] | Parcial (1 test real de 2 schemas, `test_no_se_puede_trasladar_a_sede_de_otro_tenant`, F21) |
| landing | 20 | — |
| cotizaciones | 7 | — |
| proveedores | 6 | — |
| proyectos | 8 | — |
| bancos | 6 | ✅ Completo (`test_multitenant_isolation.py` + `test_cross_tenant_isolation.py`) |
| compras | 6 [DOC-M12: +1, F24 `test_f24_confirmar_recepcion_atomicidad.py`] [DOC-M9: +1, F21 `test_f21_recepcion_compra.py`] | Parcial (`test_multitenant_isolation_tabla_html.py`; +1 test real de 2 schemas `test_orden_de_otro_tenant_no_se_puede_recibir`, F21) |
| ventas | 4 [DOC-M11: +2, F23 `test_f23_venta_inventario{,_multitenant}.py`] | ✅ (`test_multitenant_isolation.py`); +1 test real de 2 schemas F23 |
| **Total atribuido por app** | **269** [DOC-M14: 268 + 1] | **4 completos / 3 parciales de 17 apps** |

---

## 11. Comandos Esenciales

```bash
# Docker
make up                  # Levantar servicios (web:8000, db:5432, redis:6379, celery)
make down                # Detener
make logs                # Tail logs del contenedor web
make shell               # Shell en el contenedor web

# Migraciones multi-tenant
make migrate-tenants     # Todos los esquemas tenant
make migrate-shared      # Esquema public
make makemigrations      # Crear migraciones
make check-migrations    # Verificar pendientes

# Migraciones manuales (dentro del container)
docker compose exec web python manage.py migrate_schemas --shared
docker compose exec web python manage.py migrate_schemas

# Calidad de codigo
make audit               # ruff + bandit + django check
make ruff                # Lint + autofix (line-length 100, py3.12)
make bandit              # Escaneo de seguridad
make dj-check            # Django system check

# Tests
make test                # Todos los tests (pytest)
make test-file FILE="path/to/test.py"  # Un archivo especifico
make smoke               # Suite de smoke tests

# Contabilidad
python manage.py seed_reglas_contables
python manage.py poblar_catalogo_niif
python manage.py backfill_asientos_gastos [--dry-run] [--empresa-id N]

# Tenant
make crear-empresa NOMBRE="Acme" DOMINIO="acme" EMAIL="admin@acme.com"
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py ensure_public_domains

# Validacion pre-PR (obligatorio)
python -m py_compile <archivo.py>
python manage.py check
```

---

## 12. Metricas del Proyecto (v3.52.0 — 2026-08-20, DOC-M39)

**[DOC-M39]** F33.15-B Nivel 3 (cierre completo, 16/16 apps
`apps/tenant/**`) no toca modelos ni migraciones -- 34 archivos de
codigo: 1 nuevo (`apps/tenant/core/tests/conftest.py`, fixture `tenant`
faltante) y 33 modificados (2 de produccion en `proyectos` --
`api/serializers.py`, `services/presupuesto_service.py` -- el resto
tests). Ninguna fila de esta tabla cambia.

**[DOC-M38]** F33.15-B Nivel 2 no toca modelos ni migraciones -- 5
archivos de codigo modificados: 1 fix de produccion
(`apps/public/accounts/api/public_viewsets.py`, +35 lineas: `update()`
y `destroy()`) y 4 archivos de test corregidos
(`apps/config/tests/base_public.py`,
`apps/public/tenants/tests/test_api_tenants.py`,
`apps/public/impuestos/tests/test_api_impuestos.py`,
`apps/public/impuestos/tests/test_api_ingesta.py`,
`apps/public/impuestos/tests/test_templates.py`). 0 archivos nuevos, 0
migraciones. Ninguna fila de esta tabla cambia.

**[DOC-M37]** F33.15-B (auditoria de entorno) no toca modelos,
migraciones NI codigo de aplicacion -- auditoria de infraestructura
Windows/WSL2/Docker Desktop fuera del repositorio. 1 archivo de
configuracion creado fuera del repo git (`C:\Users\steve\.wslconfig`,
perfil de usuario, no commiteable). 0 documentos nuevos (hallazgos
documentados como seccion nueva en
`F33.15_TESTING_EXECUTION_STATUS.md` existente). 0 archivos de test
nuevos. Ninguna fila de esta tabla cambia.

**[DOC-M36]** F33.15 (continuacion) no toca modelos ni migraciones --
2 archivos de codigo (`apps/tenant/core/context_processors.py`,
`apps/public/console/tests/test_legacy_public_tenants_api.py`) mas 1
documento nuevo (`F33.15_TESTING_EXECUTION_STATUS.md`) y 1 documento
nuevo (`F33.15_TEST_MATRIX.md`). 0 archivos de test E2E nuevos.
Ninguna fila de esta tabla cambia.

**[DOC-M35]** F33.17 no toca modelos ni migraciones -- 3 archivos HTML
(atributos ARIA unicamente, `apps/tenant/core/templates/tenant/core/partials/ui/`)
mas 0 documentos nuevos (hallazgos documentados directamente en
`F33_STATUS_REPORT.md`/`arquitectura_general.md`, sin inventario
separado dado el alcance acotado de esta pasada). 0 archivos de test
E2E nuevos. Ninguna fila de esta tabla cambia.

**[DOC-M34]** F33.15 no toca modelos ni migraciones -- 1 archivo de
configuracion (`pytest.ini`, marker `e2e` registrado) mas 0 archivos de
codigo de aplicacion modificados (el hallazgo de fallos/cuelgues en
`test_legacy_public_tenants_api.py` quedo documentado, no corregido en
esta sub-fase). Coleccion de tests confirmada en 2064/0 errores
(sin cambio respecto al baseline). Ninguna fila de esta tabla cambia.

**[DOC-M33]** F33.14-E no toca modelos, migraciones NI codigo de
aplicacion -- auditoria pura (13 `tables.py` leidos, 0 modificados) mas
1 documento de inventario nuevo
(`F33_14E_BADGES_ESTADO_INVENTORY.md`). 0 archivos de test E2E nuevos
(no aplico corrida, sin cambios de codigo). Ninguna fila de esta tabla
cambia.

**[DOC-M32]** F33.14-D no toca modelos ni migraciones -- solo frontend
(HTML: 2 archivos migrados a `filter_bar.html`, sin cambios de codigo
Python -- el partial ya existia desde F33.8) mas 1 documento de
inventario nuevo (`F33_14D_FILTER_BAR_INVENTORY.md`) y 0 archivos de
test E2E nuevos (se reutilizo la suite existente, 29/29 PASS). Ninguna
fila de esta tabla cambia.

**[DOC-M31]** F33.14-C no toca modelos ni migraciones -- solo frontend
(HTML: 2 archivos migrados a `loading_state.html`, sin cambios de codigo
Python -- el partial ya existia desde F33.6) mas 1 documento de
inventario nuevo (`F33_14C_LOADING_STATE_INVENTORY.md`) y 0 archivos de
test E2E nuevos (se reutilizo la suite existente, 29/29 PASS). Ninguna
fila de esta tabla cambia.

**[DOC-M30]** F33.14-B no toca modelos ni migraciones -- solo frontend
(HTML: 1 archivo migrado a `sintel_empty_state`, sin cambios de codigo
Python -- el templatetag ya existia desde F33.6; 1 archivo eliminado
como codigo muerto confirmado) mas 1 documento de inventario nuevo
(`F33_14B_EMPTY_STATE_INVENTORY.md`) y 0 archivos de test E2E nuevos.
Ninguna fila de esta tabla cambia.

**[DOC-M29]** F33.14-A no toca modelos ni migraciones -- solo frontend
(HTML: 2 archivos migrados a `sintel_kpi_card`, sin cambios de codigo
Python -- el templatetag ya existia desde F33.9) mas 1 documento de
inventario nuevo (`F33_14A_CARD_KPI_INVENTORY.md`) y 0 archivos de test
E2E nuevos (se reutilizo la suite existente). Ninguna fila de esta tabla
cambia.

**[DOC-M28]** F33.13-B no toca modelos ni migraciones -- solo frontend
(JS: `bancos.main.js` + 3 archivos de inventario migrados a
`UIManager.confirm()`; HTML: modal completo eliminado de
`list_bancos.html`) mas 1 archivo de test E2E corregido
(`20-inventario-productos-crud.spec.js`, 0 tests nuevos -- correccion de
supuesto desactualizado, mismo patron que DOC-M27). Ninguna fila de esta
tabla cambia.

**[DOC-M27]** F33.13 batch 5 parte 2 no toca modelos ni migraciones --
solo frontend (JS: 25 archivos con 27 sitios de `confirm()` nativo
migrados a `UIManager.confirm()`) mas 2 archivos de test E2E corregidos
(`10-clientes-crud.spec.js`, `30-contabilidad-cuenta-crud.spec.js`, 0
tests nuevos -- correccion de un supuesto de test desactualizado, no
cobertura nueva). Ninguna fila de esta tabla cambia.

**[DOC-M26]** F33.13 (batches 1/2/4/5-parte1) y F33-R (revalidacion) no
tocan modelos ni migraciones -- solo frontend (JS: 11 archivos
consolidados sobre `mostrarOffcanvasSeguro`, 2 archivos migrados de
`confirm()` nativo a `UIManager.confirm()`, `ModalService` eliminado;
HTML: 2 templates modificados, 4 shells Tailwind huerfanos + 1 modal
service eliminados) mas 3 documentos de reconciliacion nuevos
(`F33R_EXECUTION_STATUS.md`, `F33R_FINAL_REPORT.md`,
`F33_RECONCILIATION_MATRIX.md`) y 0 archivos de test E2E nuevos (se
reutilizo la suite existente, sin crear tests por cuota). Ninguna fila
de esta tabla cambia.

**[DOC-M25]** F33 (Shared UI, en progreso) no toca modelos ni migraciones
-- solo frontend (JS: helper de offcanvas extendido, alias en UIManager;
2 templates HTML eliminados por codigo muerto confirmado, 1 modificado;
Python: 1 templatetags module nuevo con 2 tags, 1 helper de wording, 3
partials HTML nuevos) mas 2 archivos de test E2E nuevos
(`tests/e2e/specs/62-f334-*.spec.js`, `63-f3310-*.spec.js`). Ninguna fila
de esta tabla cambia.

**[DOC-M24]** F32.9 (Governance Revalidation) no toca modelos ni
migraciones -- solo 2 archivos de frontend (JS: `reporte.api.js`,
`devengo_editor.js`) mas 1 archivo de test E2E nuevo
(`tests/e2e/specs/61-f329-reporte-api-migration.spec.js`). Ninguna fila de
esta tabla cambia.

**[DOC-M23]** F32 (Frontend Transport Consolidation) no toca modelos ni
migraciones -- solo archivos de frontend (JS/HTML: 2 archivos eliminados,
`core/static/js/http.js` y `core/static/core/js/lib/http.js`; ~55 archivos
modificados para delegar en `Sintel.Core.Http`) mas 8 archivos de tests E2E
nuevos (`tests/e2e/specs/50-*.js` a `60-*.js`). Ninguna fila de esta tabla
cambia.

**[DOC-M22]** F31 (continuacion, Grupo 2) no toca modelos ni migraciones
-- solo archivos de frontend (JS/HTML) y capa de lectura (selectors.py:
parametros `search`/`estado` nuevos en selectores existentes de
`empresa`/`proveedores`/`proyectos`, sin cambios de esquema). Ninguna fila
de esta tabla cambia.

**[DOC-M21]** F31 no toca modelos ni migraciones -- solo archivos de
frontend (JS/HTML) y 2 archivos de codigo de produccion Python sin
cambios de esquema (`apps/tenant/inventario/urls.py`,
`apps/tenant/inventario/views.py` -- fix de un FieldError preexistente,
sin tocar modelos). Ninguna fila de esta tabla cambia.

**[DOC-M20]** F30 no toca modelos ni migraciones -- solo 2 archivos de
codigo de produccion sin cambios de esquema (rename de basename de router,
export faltante) y archivos de test (5 corregidos, 2 renombrados/movidos
por colision de modulo, 0 nuevos). Ninguna fila de esta tabla cambia.

**[DOC-M19]** F29 no toca modelos ni migraciones -- solo corrige nombres de
URL y valores de lookup en 19 archivos de test. Ninguna fila de esta tabla
cambia.

**[DOC-M18]** F28 no toca modelos ni migraciones -- solo normaliza base
classes de test (12 archivos) y corrige 1 `SyntaxError`. Ninguna fila de
esta tabla cambia.

**[DOC-M17]** F27 no toca modelos, migraciones ni codigo de produccion --
solo archivos de test (2 corregidos, 0 nuevos, 0 eliminados). Ninguna fila
de esta tabla cambia. Ver `documentacion/F27_TEST_INVENTORY.md` para el
inventario real de tests de todo el repo (389 archivos, 2008 funciones
`def test_`), numero mayor y mas preciso que la fila "Archivos de test
(atribuidos por app)" de abajo, que solo cuenta tests explicitamente
atribuidos a una app de negocio, no la suite completa incluyendo `tests/`.

**[DOC-M5]** Esta tabla estaba etiquetada `v3.10.4 — 2026-05-29` y nunca se habia vuelto a tocar en pases de validacion posteriores (DOC-A1 a DOC-M4) — de ahi que tuviera numeros distintos e inconsistentes con el resto del documento (ver §2.2). Recontada 2026-08-09 con la misma metodologia del resto de este pase (conteo directo sobre codigo, no sobre documentacion previa). **[DOC-M9]** Modelos tenant, migraciones y archivos de test actualizados con la contribucion real de F21 (2 modelos en `compras`, 1 en `inventario`; 2 migraciones; 2 archivos de test). **[DOC-M10]** F22 no agrega modelos ni migraciones (0 cambios de esquema); solo archivos de test (+3, `contabilidad`) y la fila de Pure Pull Model (el extractor de inventario paso de deshabilitado a activo). **[DOC-M11]** F23 tampoco agrega modelos ni migraciones (0 cambios de esquema); solo archivos de test (+2, `ventas`). **[DOC-M12]** F24 tampoco agrega modelos ni migraciones (0 cambios de esquema); solo archivos de test (+3: `compras` +1, `contabilidad` +2) y 2 correcciones de codigo existente (`compras/services/business_service.py`, `contabilidad/integracion/validadores.py`, ver `F24_FINDINGS.md`). **[DOC-M13]** F25 tampoco agrega modelos ni migraciones (0 cambios de esquema); solo 1 archivo de test (+1, `gastos`) y 1 correccion de codigo existente (`gastos/services/business_service.py`, ver `F25_FINDINGS.md` F25-001). **[DOC-M14]** Devoluciones reales agrega 1 modelo tenant nuevo (`ItemNotaCredito`, `facturas`) y 1 migracion (`0031_itemnotacredito.py`); 1 archivo de test (+1, `facturas`). **[DOC-M15]** F26 no agrega modelos nuevos (elimina 1 campo, `Factura.xml_file_path`, sin afectar el conteo de modelos); 1 migracion nueva (`0032_remove_factura_xml_file_path.py`, remove-only); 0 archivos de test nuevos (corrige 3 archivos existentes: `test_materializar_from_dto.py`, `test_ingesta_ubl.py`, `test_nota_credito_pipeline.py`); 2 correcciones de codigo de produccion (`facturas/models.py`: campo fantasma `orden_compra` removido de `MANUAL_EDITABLE_FIELDS`, campo `xml_file_path` eliminado). **[DOC-M16]** Fix F26-006 no agrega modelos (solo relaja `NotaCredito.cude` a `null=True`); 1 migracion nueva (`0033_alter_notacredito_cude.py`, aditiva); 0 archivos de test nuevos (agrega 1 test a `test_materializar_from_dto.py` y 1 a `test_nota_credito_pipeline.py`, reescribe 1 existente); 1 correccion de codigo de produccion (`facturas/services/business_service.py`: idempotencia por numero + normalizacion `cufe`/`cude` a `None`). El resto de filas no se re-verifico en esta pasada.

| Metrica | Cantidad |
|---|---|
| Apps publicas activas | 5 |
| Apps tenant registradas (`TENANT_APPS`) | 17 (15 con modelos de negocio + `core` + `landing`, ver §2.2/§2.3) |
| Modelos publicos | 19 |
| Modelos tenant | 71 concretos + 3 abstractos [DOC-M14: 70+1, `ItemNotaCredito`] |
| Total migraciones | 191 (182 tenant + 9 public) [DOC-M16: 190+1, `0033_alter_notacredito_cude` -- aditiva, `null=True` en `NotaCredito.cude`] |
| Endpoints API (prefijos en `api_urls.py`) | 17 modulos (16 tenant + 1 public) + endpoint `/mcp/` separado |
| Archivos de test (atribuidos por app) | 269 [DOC-M14: 268+1] (401 en todo el repo, excluyendo `venv/` — total de repo no re-verificado en esta pasada) |
| Dependencias Python | 20+ |
| Namespaces JS activos | 15 (`window.Sintel.*`) + 3 sub-namespaces de feature |
| Campos contables eliminados (v3.10.2) | 15 en 6 apps |
| Apps con Pure Pull Model contable | 6 (Proveedores, Clientes, Inventario, Facturas, Gastos, Empleados) — "Pure Pull" describe el desacoplamiento de campos `cuenta_*_uuid` (§6.2). **[DOC-M10]** Actualizado: el extractor de `inventario` ya esta activo (F22, ver §6.3), a diferencia de la nota DOC-M9 que aplicaba antes del cierre de esta fase |
| Django system check | ✅ Limpio, verificado por ejecucion real en el cierre de F22 (`docker compose exec web python manage.py check` → `System check identified no issues`) |
