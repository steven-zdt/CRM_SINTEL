# FACTURAS-VENTAS-COMPRAS-01 — Reparacion de persistencia/listado + asociacion manual

Mision 2026-09-10. Ver tambien `docs/comercial/VENTAS_COMPRA_FACTURA_MANUAL_RELEASE.md`
(release gate de Ventas/Compras) y `docs/facturas/FACTURAS_HUB_BASELINE.md`/
`FACTURAS_HUB_ARCHITECTURE.md` (arquitectura previa del pipeline, sin cambios).

## Hallazgo real 1 — `upload-ubl` devolvia 500 en vez de 422

`FacturaBusinessService.guardar_desde_dto()` ya rechazaba (correctamente,
sin cambios de esta mision) documentos cuyo NIT no coincide ni con el
emisor ni con el receptor de la Empresa, lanzando `DjangoValidationError`.
El endpoint `upload_ubl()` (`apps/tenant/facturas/api/mixins/
factura_ubl_mixin.py`) no tenia ningun `except` especifico para esa
excepcion -- caia al `except Exception` generico y devolvia
`500 Internal Server Error` para lo que en realidad es un rechazo de
negocio valido, no un bug del servidor.

**Fix:** nuevo `except DjangoValidationError` antes del generico, retorna
`422` con `{"error": "validation_error", "message": "..."}`. Verificado en
vivo: mismo escenario, antes `500`, ahora `422` con mensaje claro.

## Hallazgo real 2 — el listado nunca se refrescaba tras subir un XML

La Factura SI se guardaba (confirmado con consultas directas a la base de
datos en cada paso de esta mision), pero la tabla visible
(`list_factura.html`, pestañas Ventas/Compras via HTMX) nunca se enteraba:

- `list_factura.html` escucha `hx-trigger="... facturaGuardada from:document"`
  en ambos paneles.
- El formulario "Importar Facturas XML" (`offcanvas_crear_factura.html`,
  subida batch por drag&drop) disparaba **`listaFacturasChanged`** en
  **`document.body`** sin `bubbles:true` -- nombre distinto y sin
  propagacion, nunca llegaba a nadie.
- El flujo HTMX de un solo archivo SI envia `HX-Trigger: listaFacturasChanged`
  desde el backend (4 sitios: `factura_ubl_mixin.py` x3, `viewsets.py` x1),
  pero **nadie escuchaba ese nombre tampoco** (confirmado por grep exhaustivo
  de `addEventListener` en todo `apps/tenant/facturas/static/`).

**Fix (2 cambios, sin tocar el backend):**
1. `offcanvas_crear_factura.html`: `document.dispatchEvent(new Event('facturaGuardada'))`
   (mismo evento/target que ya usan `facturas_editor.js`/`facturas_list.js`).
2. `list_factura.html`: `hx-trigger` de ambos paneles ampliado para aceptar
   tambien `listaFacturasChanged from:document` (cubre los 4 sitios del
   backend sin tocarlos, y cualquier consumidor futuro que use ese nombre).

Ambos son archivos de plantilla Django server-side -- sin cache de
`collectstatic`, el fix aplica sin reiniciar el contenedor.

## Hallazgo real 3 — 3 implementaciones distintas de la regla de naturaleza

Ver detalle completo en el commit de esta sesion / `business_service.py`.
Resumen: `FacturaBusinessService._resolver_naturaleza()` (SSoT real,
usada por `guardar_desde_dto()` y `preview_mail_ingestion()`) vs.
`apps/tenant/facturas/services/__init__.py::_determinar_naturaleza()`
(wrapper de compatibilidad que su propio docstring decia que delegaba
pero reimplementaba su propia comparacion con una TERCERA funcion de
normalizacion de NIT, `_norm_nit()`) -- usada por 2 management commands
de backfill/fix. Consolidado: `_determinar_naturaleza()` ahora SI delega
de verdad. `_norm_nit()` no se toco (sigue siendo correcta y usada
directamente por los management commands para su propio proposito).

`_resolver_naturaleza()` tambien se corrigio para no adivinar mas: antes
cualquier documento donde el emisor no fuera exactamente la empresa caia
por defecto a `COMPRA`, incluso con emisor vacio o con emisor==receptor==
empresa (autofactura). Ahora retorna `None` ("Revisar") en esos casos
ambiguos -- matriz completa probada en
`apps/tenant/facturas/tests/test_resolver_naturaleza_matrix.py` (13 tests).

## Hallazgo real 4 — el buscador de facturas mostraba mal el tercero en COMPRA

`buscar-para-movimiento` (reutilizado para el buscador de asociacion
manual, no se creo un endpoint nuevo) solo buscaba/mostraba
`receptor_razon_social` bajo el nombre "cliente" -- correcto para VENTA,
incorrecto para COMPRA (el tercero relevante ahi es el EMISOR/proveedor).
Corregido: busca en ambos lados (emisor+receptor+numero+CUFE) y calcula
`tercero`/`nit` segun la `naturaleza` real de cada fila. Campo `cliente`
se conserva por compatibilidad con el consumidor existente (Inventario).

## Evidencia end-to-end (HTTP real, mismo checkout, 2026-09-10)

| Paso | Resultado |
|---|---|
| `POST upload-ubl` XML COMPRA (emisor 900555777, receptor 901123299) | `201`, `naturaleza=COMPRA` |
| `GET buscar-para-movimiento?naturaleza=COMPRA` | `200`, `tercero="Proveedor E2E Test SAS"` (emisor, correcto) |
| `POST /compras/{uuid}/vincular-factura/` (factura COMPRA real) | `200`, `factura_uuid`/`factura_numero` en la respuesta |
| Repetir la misma asociacion | `409 orden_ya_vinculada` (idempotente, no duplica) |
| `POST upload-ubl` XML VENTA (emisor 901123299, receptor 900777999) | `201`, `naturaleza=VENTA` |
| `GET buscar-para-movimiento?naturaleza=VENTA` | `200`, `tercero="Cliente E2E Test SAS"` (receptor, correcto) |
| `POST /ventas/{uuid}/vincular-factura/` con factura de naturaleza COMPRA | `422 naturaleza_incorrecta` (rechazado) |
| `POST /ventas/{uuid}/vincular-factura/` con factura VENTA real | `200`, `estado=FACTURADA_DIAN`, `factura_uuid` presente |

Auditoria de datos existentes (FASE 32/33, antes de cerrar):
`COUNT Factura=7` (`VENTA=2`, `COMPRA=5`, `sin naturaleza=0`),
`ItemFactura=32`, `0` facturas con `empresa_id` huerfano -- ninguna
Factura persistida quedaba invisible por un filtro incorrecto.

## Restricciones respetadas

- No se creo ninguna Factura desde Ventas/Compras (`EMISION_FISCAL_VENTA_AUTORIZADA`
  sigue en `False`, sin tocar).
- No se duplico `_resolver_naturaleza()` ni el parser XML.
- No se creo un segundo endpoint de busqueda (se reutilizo/corrigio
  `buscar-para-movimiento`).
- `window.Sintel.Core.Http` sigue siendo el unico transporte HTTP del
  frontend -- los metodos nuevos (`vincularFactura`, `buscarFacturas*`)
  en `ventas.api.js`/`compras.api.js` lo reutilizan, no crean fetch propio.
- `mostrarOffcanvasSeguro` sin cambios -- los widgets nuevos viven dentro
  de offcanvas ya existentes, no se creo un mecanismo de apertura nuevo.
- `manage.py check` limpio, `makemigrations --check` limpio (1 migracion
  nueva real: `OrdenCompra.factura_asociada`, justificada porque Compras
  no tenia NINGUN campo de vinculo a Factura -- ver commit de la sesion
  anterior).

## Limitaciones conocidas (PASS_WITH_LIMITATIONS, no PASS ciego)

- **No se pudo verificar visualmente en navegador** (screenshot real):
  el asistente no puede autenticar una sesion de navegador sin escribir
  una contraseña (regla absoluta), y el intento de "impersonar" una
  sesion valida server-side fue rechazado por el stack de autenticacion
  del tenant por una razon no diagnosticada del todo (ver conversacion
  de la sesion) -- toda la evidencia de esta mision es HTTP/DB real, no
  screenshots. El usuario debe confirmar visualmente en su propia sesion.
- El "Todas" (Ventas+Compras combinadas en un solo listado cronologico)
  de la mision anterior FACTURAS-UI-CRONO-01 sigue sin construir -- la UI
  actual sigue siendo 2 pestañas separadas (Ventas/Compras), no un
  listado unico. Fuera del alcance estricto de esta mision (que pedia
  reparar persistencia+listado+asociacion, no rediseñar la UI).
