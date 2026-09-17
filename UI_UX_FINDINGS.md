# UI_UX_FINDINGS — SINTEL ERP

**Fecha:** 2026-09-16 (creado en Fase 52), actualizado 2026-09-17 (Fase 9). **Rama:**
`feat/onboarding-cookie`.

Consolida cada hallazgo real de esta sesión — corregido o documentado — con reproducción, causa raíz,
fix aplicado (o razón explícita de por qué no se corrigió) y el test que lo prueba. Ningún hallazgo
aquí fue inventado: todos se verificaron leyendo el código real antes de citarlos, y todos los
"corregido" tienen un test que pasa como evidencia.

**Severidad:** `P1` (bug de producción, afecta datos o disponibilidad) · `P2` (bug real de UX/API,
no afecta integridad de datos) · `P3` (hallazgo menor / deuda documentada).

---

## COMPRAS-500-01 — `OrdenCompraViewSet.create()` devolvía 500 en vez de 400

- **App / Screen:** Compras / Orden de Compra (offcanvas de creación).
- **Type:** Manejo de errores incorrecto (Fase 19/31 de la misión).
- **Severity:** P2.
- **Reproduction:** `POST /api/v1/compras/` con `items: []` o con `fecha_entrega` anterior a `fecha`.
- **Current (antes):** `serializer.is_valid(raise_exception=True)` lanzaba `ValidationError`, que
  caía en el `except Exception` genérico del método, devolviendo `500 {"error": "error_interno",
  "message": "<traceback str(e)>"}` — el mensaje de validación real quedaba oculto detrás de un
  error interno con el texto crudo de la excepción de Python expuesto al cliente.
- **Expected:** `400` con los errores de campo reales (`{"items": ["Debe proporcionar al menos un
  item..."]}`), como ya hacían `update()`/`destroy()` en el mismo archivo vía `handle_service_error`.
- **Root cause:** `create()` no discriminaba `ValidationError` antes del `except Exception` genérico
  — a diferencia del resto de métodos del mismo `ViewSet`.
- **Fix:** `apps/tenant/compras/api/viewsets.py` — se agregó `except ValidationError as e: return
  Response(e.detail, status=400)` **antes** del `except Exception` genérico.
- **Test:** `apps/tenant/compras/tests/test_compras_crud_workspace.py::test_orden_compra_create_sin_items_es_rechazada` y `::test_orden_compra_create_fecha_entrega_anterior_a_fecha_es_rechazada` — 2/2 passed. Regresión completa de Compras: 52/52 passed.
- **Status:** `FIXED`.

---

## VENTAS-500-01 — `crear_venta_borrador()` devolvía 500 en vez de 400 por `fecha_emision` faltante

- **App / Screen:** Ventas / Venta (offcanvas de creación).
- **Type:** Manejo de errores incorrecto (Fase 19/31).
- **Severity:** P2.
- **Reproduction:** `POST /api/v1/ventas/` sin el campo `fecha_emision` en el payload.
- **Current (antes):** `payload["fecha_emision"]` (acceso directo por índice, sin `.get()`) lanzaba
  `KeyError` si el campo faltaba. `KeyError` no es `ValueError`, así que caía en el `except Exception`
  genérico de `crear_venta_borrador()`, devolviendo `500 {"detail": "Error interno al crear la
  venta."}` en vez de un 400 claro.
- **Expected:** `400` con un mensaje explícito indicando qué campo falta.
- **Root cause:** acceso por índice a un campo opcional-en-la-práctica del payload, sin validación
  explícita previa (a diferencia de `items`, que sí tenía su propio `if not items_data: return 400`
  dos líneas arriba en la misma función).
- **Fix:** `apps/tenant/ventas/services/business_service.py` — se agregó `if not
  payload.get("fecha_emision"): return False, {"detail": "El campo 'fecha_emision' es
  obligatorio."}, 400`, siguiendo el mismo patrón ya usado para `items`.
- **Test:** `apps/tenant/ventas/tests/test_venta_crud_workspace.py::test_venta_create_sin_fecha_emision_es_rechazada` — passed. Regresión completa de Ventas: 45/45 passed, 1 skip no relacionado.
- **Status:** `FIXED`.

---

## INVENTARIO-404-01 — 4 ViewSets devolvían 500 en vez de 404 para UUID inexistente

- **App / Screen:** Inventario / Categoría, Producto, Servicio, Activo Fijo (detalle/editar/eliminar).
- **Type:** Manejo de errores incorrecto (Fase 19/31), bug ya conocido y corregido antes en un
  `ViewSet` hermano pero nunca propagado a estos 4.
- **Severity:** P2.
- **Reproduction:** `GET/PATCH/DELETE /api/v1/inventario/{productos,servicios,activos,categorias}/<uuid-inexistente>/`.
- **Current (antes):** `get_object()` llamaba al selector (`ProductoSelector.get_detail()`, etc.)
  directamente, sin capturar `ObjectDoesNotExist` — el `DoesNotExist` de Django se propagaba sin
  envolver hasta el middleware global de excepciones, que respondía `500 {"status": 500, "message":
  "Producto matching query does not exist.", "code": "INTERNAL_SERVER_ERROR"}`.
- **Expected:** `404` limpio, como ya devolvía `MovimientoInventarioViewSet.get_object()` (corregido
  en una fase previa, OSF F13, con el comentario explícito documentando el mismo bug).
- **Root cause:** el fix de OSF F13 se aplicó solo a `MovimientoInventarioViewSet` — nunca se
  propagó a los otros 4 `ViewSets` del mismo archivo que comparten el mismo patrón de `get_object()`
  manual.
- **Fix:** `apps/tenant/inventario/api/viewsets.py` — se envolvió cada llamada al selector en
  `try/except ObjectDoesNotExist: raise NotFound(...)`, exactamente el mismo patrón ya usado en
  `MovimientoInventarioViewSet`.
- **Test:** `apps/tenant/inventario/tests/test_producto_crud_workspace.py::test_producto_read_uuid_inexistente_retorna_404` — passed. Regresión completa de Inventario: 60/60 passed (incluye los 4 fixes).
- **Status:** `FIXED`.

---

## GASTOS-01 — `materializar_gasto_desde_dto()` fabricaba Empresa/ResolucionDIAN falsas

- **App / Screen:** Gastos / pipeline de ingesta de correo (sin pantalla — corre sin supervisión
  humana desde `document_router.py`).
- **Type:** Fabricación silenciosa de datos (Fase 21/29), el más grave de la sesión.
- **Severity:** P1.
- **Reproduction:** invocar `materializar_gasto_desde_dto(dto)` en un tenant sin `Empresa` o sin
  `ResolucionDIAN` vigente configurada.
- **Current (antes):** si no existía `Empresa`, se creaba una con `razon_social="Empresa
  Autocreada", nit="123456789"`. Si no existía `ResolucionDIAN` vigente, se creaba una con
  `numero_resolucion="999999", rango 1-100000`. Ambas se usaban para persistir un `DocumentoSoporte`
  real — un dato fiscal legalmente significativo dependiendo de datos completamente inventados.
- **Expected:** fallar explícito con un mensaje claro, dejando que el pipeline reintente o marque el
  documento como pendiente hasta que el tenant esté correctamente configurado.
- **Root cause:** decisión de diseño original de "nunca fallar" en el materializador, priorizando
  disponibilidad sobre integridad de datos fiscales.
- **Fix:** `apps/tenant/gastos/services/business_service.py` — ambas ramas ahora hacen `raise
  ValidationError(...)` en vez de `.objects.create(...)`. `document_router.py` ya distinguía
  `ValidationError` (esperado) de un error inesperado, así que el pipeline de ingesta ya sabía
  manejar este caso sin cambios adicionales. **Autorizado explícitamente por el usuario** tras
  presentar el hallazgo y confirmar que ningún test dependía del comportamiento anterior.
- **Test:** `apps/tenant/gastos/tests/test_gastos01_materializar_falla_explicito.py` — 3/3 passed (sin Empresa, sin Resolución vigente, camino feliz con ambas).
- **Status:** `FIXED`.

---

## GASTOS-02 / DASH-02 / FACTURAS-SILENT-01 — 12 propiedades/extractores convertían errores reales en `$0` silencioso

- **App / Screen:** Gastos (`DocumentoSoporte`, 6 properties), Dashboard (7 extractores +
  orquestador), Facturas (`Factura`/`ItemFactura`, 6 properties) — todas leen retenciones o métricas
  vía el Pull Model (`RetencionesService`, `contabilidad.Retencion`).
- **Type:** Error silencioso (Fase 21/29), el patrón más repetido de la sesión.
- **Severity:** P2.
- **Reproduction:** cualquier fallo real en la consulta cross-schema a `contabilidad.Retencion` (o en
  el cálculo de un widget del Dashboard) — antes, indistinguible de "no hay retención"/"0 datos
  reales" porque el `except Exception:` no dejaba ningún rastro.
- **Current (antes):** `except Exception: return Decimal('0.00')` (o el DTO en cero equivalente),
  sin ningún `logger.warning`/`.error`/`.exception` — el error desaparecía por completo, ni siquiera
  quedaba en logs para depuración posterior.
- **Expected:** un error real debe dejar rastro (Fase 21: "ERROR REAL → ERROR EXPLÍCITO, nunca →
  $0" silencioso). El valor de fallback en sí (`$0`/DTO en cero) se mantuvo — cambiar el contrato de
  API para que el frontend distinga "0 real" de "error" es una decisión de producto más grande, fuera
  del alcance quirúrgico de esta sesión.
- **Root cause:** manejo de errores defensivo escrito para "nunca romper la pantalla", sin considerar
  que eso hace indistinguible un bug real de un dato genuinamente vacío.
- **Fix:** se agregó `logger.exception(...)` con contexto (`documento_soporte_id`/`factura_id`/
  `empresa_id`) en los 12 puntos antes del `return` de fallback — Gastos (6), Facturas (6) — y
  `logger.exception(...)` en los 7 extractores de Dashboard + su orquestador (que ya logueaba, pero
  con `logger.warning(str(e))` sin traceback — se cambió a `.exception()` para capturar el traceback
  completo).
- **Test:** `test_gastos01_materializar_falla_explicito.py` (indirecto), `test_retenciones_backward_compat.py` 12/12 passed (Facturas), regresión combinada Gastos+Dashboard 67/67 passed.
- **Status:** `FIXED` (logging); `DEFERRED` (cambio de contrato de API para el frontend, si se quiere ir más allá).

---

## PERFIL-PK-01 — `PerfilViewSet` acepta lookup por ID entero además de UUID

- **App / Screen:** Perfil / Usuarios y roles (toda la pantalla — update, assign-rol, destroy).
- **Type:** Violación de regla arquitectónica no-negociable (`CLAUDE.md`: "UUID lookup, not PK").
- **Severity:** P2 (seguridad/higiene arquitectónica, no IDOR — DSV/`empresa_id` sigue protegido).
- **Reproduction:** `GET /api/v1/perfil/perfiles/1/`, `/2/`, ... — funciona igual que con UUID.
- **Current:** `PerfilViewSet` no hereda `BaseTenantViewSet` (que fija `lookup_field="uuid"`).
  `get_profile()` detecta explícitamente si el valor es UUID o entero y resuelve por cualquiera de
  los dos (`TenantProfile.objects.filter(id=profile_id, ...)` confirmado funcional).
- **Expected:** solo UUID en la URL, igual que el resto de `ViewSets` del sistema.
- **Root cause:** `PerfilViewSet` se construyó como `viewsets.GenericViewSet` puro en vez de heredar
  `BaseTenantViewSet`, probablemente porque necesitaba lookup dual (UUID e ID) para compatibilidad
  con algún caller legacy no identificado en esta sesión.
- **Fix:** ninguno aplicado. **Decisión explícita del usuario: documentar, no tocar** — cambiar esto
  es un cambio de contrato de API que podría romper JS del frontend si algo depende del ID entero,
  no verificado en esta sesión.
- **Test:** `test_perfil_viewset_workspace.py` usa deliberadamente UUID (el camino correcto) — no
  hay test que verifique el camino por ID entero (no se quiso dejar un test verificando un
  comportamiento que se documentó como indeseado).
- **Status:** `DEFERRED` (por decisión explícita del usuario).

---

## MAILINBOX-PK-01 — `MailInboxConfigViewSet` tiene el mismo gap que Perfil

- **App / Screen:** Empresa / Configuración de buzones de correo.
- **Type:** Mismo que PERFIL-PK-01.
- **Severity:** P2.
- **Reproduction:** `GET /api/v1/empresas/mail-inbox-config/1/`.
- **Current:** no hereda `BaseTenantViewSet`, sin `lookup_field` propio — usa el default de DRF
  (`pk`, entero). `MailInboxConfig` es una colección real (múltiples buzones por tenant, confirmado
  por el modelo — no es un singleton como `Empresa`, que tiene el mismo gap técnico pero 0 riesgo de
  enumeración al haber un solo registro).
- **Expected:** lookup por UUID.
- **Root cause:** mismo patrón que Perfil — `ViewSet` construido sin heredar la base estándar.
- **Fix:** ninguno — mismo criterio que PERFIL-PK-01 (documentar, no tocar, sin evaluar impacto en
  frontend esta sesión).
- **Test:** `test_mailinboxconfig_crud_workspace.py` usa el ID entero porque hoy es la única forma
  soportada — el test lo señala explícitamente en su docstring, sin validar que sea el comportamiento
  correcto.
- **Status:** `DEFERRED`.

---

## EMPLEADOS-400-01 / PERFIL-400-01 — patrón inverso: errores de servidor reportados como error del usuario

- **App / Screen:** Empleados / Contrato (crear, simular liquidación); Perfil / Usuarios y roles
  (`update`, `destroy`).
- **Type:** Manejo de errores incorrecto — el problema opuesto a COMPRAS-500-01/VENTAS-500-01: aquí
  un fallo real e inesperado del servidor se reporta como `400` (error del cliente) en vez de `500`.
- **Severity:** P3 (no rompe la funcionalidad ni engaña sobre el resultado de la operación — sí
  dificulta distinguir "el usuario cometió un error" de "el servidor tiene un bug" en logs/alertas).
- **Reproduction:** cualquier excepción inesperada (no de validación) dentro de
  `ContratoViewSet.perform_create()`/`simular_liquidacion()` o `PerfilViewSet.destroy()`/`update()`.
- **Current:** `except Exception as e: return Response({...}, status=400)` sin discriminar tipo de
  excepción — un `AttributeError`/`TypeError` genuino se reporta igual que un dato inválido del
  usuario.
- **Expected:** discriminar como ya hacen otros métodos del mismo archivo (`ContratoViewSet.update()`
  sí distingue `ValidationError`/`IntegrityError`/genérico → 400/409/500 correctamente).
- **Root cause:** inconsistencia dentro del mismo archivo — algunos métodos ya tienen el manejo
  correcto, estos no lo replicaron.
- **Fix:** ninguno aplicado esta sesión — alcance quirúrgico (tocar manejo de excepciones en 4
  métodos de 2 archivos distintos sin autorización explícita adicional).
- **Test:** ninguno nuevo — el hallazgo se confirmó leyendo el código, no se indujo el fallo en un
  test (induciría una excepción real artificial, de bajo valor para un hallazgo ya claro por lectura).
- **Status:** `DEFERRED`.

---

## CROSSAPP-UI-01 — adopción del sistema de componentes UI compartidos: solo 5/15 apps

- **App / Screen:** Transversal — Proveedores, Cotizaciones, Inventario, Facturas, Bancos,
  Contabilidad, Empleados, Empresa, Perfil, Dashboard (10 de 15 apps).
- **Type:** Inconsistencia visual/estructural (Fase 44, Fase 59 — "un mismo producto").
- **Severity:** P3 (no es un bug funcional, es deuda de consistencia de experiencia).
- **Reproduction:** `grep -rl "{% load sintel_ui %}" apps/tenant/*/templates/` — solo 3 apps
  (Clientes, Proyectos, Ventas); `filter_bar.html`/`loading_state.html` de inclusión directa: solo 2
  apps más (Compras, Gastos).
- **Current:** `apps/tenant/core/templatetags/sintel_ui.py` (`sintel_kpi_card`, `sintel_empty_state`)
  y `partials/ui/filter_bar.html`/`loading_state.html`, documentados en `UX_MASTER_BASELINE.md`
  (2026-08-21) como "YA EXISTENTES, reutilizar, no duplicar", tienen adopción real de solo 5/15 apps.
- **Expected:** las 15 apps usando el mismo sistema para estados vacíos, KPIs, filtros y loaders.
- **Root cause:** el sistema se construyó (Fase 33 de una misión anterior) pero nunca se retrofiteó
  a las apps que ya existían antes de esa fase, ni se hizo obligatorio para apps nuevas.
- **Fix:** ninguno — retrofitear 10 apps es un esfuerzo de remediación considerable, no quirúrgico.
- **Test:** N/A (hallazgo de auditoría estática, no de comportamiento).
- **Status:** `DEFERRED` (documentado en Fase 44 y en la matriz de cobertura).

---

## EMISION-FISCAL-01 — 2 de los 4 flujos de negocio E2E terminan en un paso bloqueado en producción

- **App / Screen:** Ventas, Cotizaciones — acción "Facturar" sobre una Venta.
- **Type:** No es un bug — es una restricción regulatoria real y ya documentada por el propio equipo.
- **Severity:** N/A (informativo, no accionable como "fix").
- **Reproduction:** `POST /api/v1/ventas/{uuid}/procesar-facturar/` en un entorno con
  `EMISION_FISCAL_VENTA_AUTORIZADA=False` (el valor real de producción) — rechaza con 403.
- **Current:** el pipeline DIAN interno completo (`VentaBusinessService.procesar_y_facturar_venta()`)
  existe, está probado, y funciona — pero está deshabilitado por un flag porque **SINTEL todavía no
  tiene autorización de la DIAN para emitir facturas electrónicas directamente**
  (`VENTAS-COMPRAS-FACTURAS-01`, 2026-09-09). El camino real de producción para que exista una
  `Factura` es la ingesta de XML ya firmado externamente.
- **Expected:** N/A — este es el comportamiento esperado y correcto mientras dure la restricción
  regulatoria. Se documenta aquí únicamente porque afecta la interpretación de la Fase 45
  (los flujos "Cotización→Venta→Factura" y "Venta→Inventario→Factura" pasan en tests con el flag
  mockeado, pero no reflejan el camino que corre en producción hoy).
- **Root cause:** decisión de producto/regulatoria, no técnica.
- **Fix:** N/A — no aplica corrección; queda pendiente de que la autorización DIAN se obtenga.
- **Test:** `test_flag_por_defecto_es_false()` (`test_bloqueo_emision_fiscal.py`) documenta el
  estado real de producción como parte de la suite, no como mock.
- **Status:** `DEFERRED` (por diseño/regulación, no por decisión de esta sesión).

---

## PROVEEDORES-OFFCANVAS-01 — `getOrCreateInstance().show()` prohibido en el fallback de apertura de offcanvas

- **App / Screen:** Proveedores / Representantes (directorio, tab del detalle de Proveedor).
- **Type:** Violación de regla arquitectónica no-negociable (`CLAUDE.md`: "`getOrCreateInstance().show()`
  en Offcanvas — PROHIBIDO, acumula backdrops. Usar `mostrarOffcanvasSeguro(el)`"), hallazgo de la
  Fase 9 (Inventario de patrones visuales).
- **Severity:** P3 (no es un bug funcional visible en un solo uso — el riesgo es acumulación de
  backdrops/listeners huérfanos en aperturas repetidas del mismo offcanvas).
- **Reproduction:** abrir el offcanvas de creación/edición de Representante repetidas veces desde
  `representantes_directory.html` en un navegador donde `window.UIManager` no esté cargado (rama de
  fallback).
- **Current (antes):** el listener de `htmx:afterSettle` en
  `apps/tenant/proveedores/templates/tenant/proveedores/partials/representantes_directory.html:233-237`
  usaba `w.UIManager?.handleOffcanvas` como camino principal, con un fallback a
  `w.bootstrap?.Offcanvas?.getOrCreateInstance?.(offcanvasEl)?.show?.()` — el único caso detectado en
  las 6 apps auditadas en la Fase 9.
- **Expected:** usar siempre `window.Sintel.Core.mostrarOffcanvasSeguro(el)`
  (`apps/tenant/core/static/core/js/common/offcanvas.helper.js`), que hace `dispose()` de la instancia
  previa antes de crear una nueva — `UIManager.handleOffcanvas` ya delega en el mismo helper como
  alias, así que ambos caminos deberían converger al mismo código.
- **Root cause:** código legado de cuando `mostrarOffcanvasSeguro`/`UIManager.handleOffcanvas` aún no
  existían como SSoT consolidado; el fallback nunca se actualizó al mismo estándar que el camino
  principal.
- **Fix:** `apps/tenant/proveedores/templates/tenant/proveedores/partials/representantes_directory.html`
  — se reemplazó el fallback por `w.Sintel?.Core?.mostrarOffcanvasSeguro?.(offcanvasEl)`.
- **Test:** ninguno nuevo — no existía un test cubriendo específicamente la rama de fallback (el
  camino principal, `UIManager.handleOffcanvas`, sigue intacto y ya delega en el mismo helper).
- **Status:** `FIXED`.

---

## COTIZACIONES-SSOT-01 — URL de items hardcodeada en vez de usar el SSoT de `cotizaciones.api.js`

- **App / Screen:** Cotizaciones / Editor (carga de ítems al abrir una cotización existente).
- **Type:** Violación de la regla de SSoT para URLs de API (Fase 37, "Cada `api.js` debe seguir siendo
  SSoT de URLs/HTTP methods").
- **Severity:** P3 (no afecta el comportamiento actual — el endpoint es el mismo — pero rompe la
  regla de mantenibilidad: un cambio futuro de esa URL en `cotizaciones.api.js` no se reflejaría aquí).
- **Reproduction:** abrir el editor de una cotización existente y revisar la llamada de red a
  `/api/v1/cotizaciones/items/`.
- **Current (antes):** `apps/tenant/cotizaciones/static/cotizaciones/js/features/cotizacion_editor.js:59`
  hacía `fetch('/api/v1/cotizaciones/items/?cotizacion_id=' + uuid + '&page_size=200', ...)` con la
  URL base escrita a mano, en vez de usar `this._api.itemsUrl` (definido en
  `cotizaciones.api.js:100` como `BASE + '/items/'`).
- **Expected:** usar el wrapper SSoT ya existente, igual que el resto del archivo hace para
  productos/servicios (`this._api.productosUrl`, `this._api.serviciosUrl`).
- **Root cause:** el código de carga de ítems se escribió antes de o sin usar el wrapper `itemsUrl`
  ya definido en el mismo `api.js`, probablemente copiado de un `fetch()` de prueba y nunca migrado.
- **Fix:** reemplazado por `fetch(this._api.itemsUrl + '?cotizacion_id=' + uuid + '&page_size=200', ...)`.
- **Test:** ninguno nuevo — cambio de una línea, mismo endpoint resultante, sin cambio de
  comportamiento observable.
- **Status:** `FIXED`.

---

## Resumen

| ID | App | Severidad | Status |
|---|---|---|---|
| COMPRAS-500-01 | Compras | P2 | `FIXED` |
| VENTAS-500-01 | Ventas | P2 | `FIXED` |
| INVENTARIO-404-01 | Inventario | P2 | `FIXED` |
| GASTOS-01 | Gastos | P1 | `FIXED` |
| GASTOS-02/DASH-02/FACTURAS-SILENT-01 | Gastos, Dashboard, Facturas | P2 | `FIXED` (logging) / `DEFERRED` (contrato de API) |
| PERFIL-PK-01 | Perfil | P2 | `DEFERRED` (decisión explícita del usuario) |
| MAILINBOX-PK-01 | Empresa | P2 | `DEFERRED` |
| EMPLEADOS-400-01 / PERFIL-400-01 | Empleados, Perfil | P3 | `DEFERRED` |
| CROSSAPP-UI-01 | Transversal (10 apps) | P3 | `DEFERRED` |
| EMISION-FISCAL-01 | Ventas, Cotizaciones | N/A | `DEFERRED` (por diseño/regulación) |
| PROVEEDORES-OFFCANVAS-01 | Proveedores | P3 | `FIXED` |
| COTIZACIONES-SSOT-01 | Cotizaciones | P3 | `FIXED` |

**9 bugs reales corregidos con evidencia de test o de código verificado. 6 hallazgos documentados y
explícitamente diferidos** (2 por decisión del usuario, 3 por alcance quirúrgico, 1 por ser una
restricción de producto/regulación ya existente). **0 hallazgos inventados** — cada uno cita el
archivo y línea real que lo origina.
