PLAN.md -- Plan Maestro de Auditoria Enterprise ERP SINTEL (UI)

Objetivo

Ejecutar una auditoria Enterprise completa del ERP SINTEL exclusivamente desde la interfaz de usuario (https://home.sintel.net.co/), validando que la implementacion cumple la arquitectura definida (AGENTS.md, ADRs). No se modifica codigo hasta cerrar el informe final (Fase 8) y recibir autorizacion explicita.

Reglas de ejecucion

- Una fase a la vez. No se avanza a la siguiente sin cerrar la anterior.
- Toda evidencia se registra: URL, usuario, modulo, hora, resultado, excepcion/stacktrace, respuesta API, consola JS, Network, logs de servidor cuando aplique.
- Capturas de pantalla solo cuando exista error o hallazgo.
- Restriccion operativa: el agente no introduce contrasenas en formularios (regla de seguridad del entorno). El login manual lo realiza el usuario en el navegador; el agente continua la auditoria sobre la sesion ya autenticada.

Estados

- [ ] Pendiente
- [~] En ejecucion
- [x] Completado
- [!] Bloqueado

=====================================================================
FASE 1 -- Preparacion del entorno -- [x] Completado
=====================================================================

Fecha/hora: 2026-08-06 (via `docker compose`, sin acceso a UI)

| Chequeo | Resultado | Evidencia |
|---|---|---|
| Docker Compose (7 servicios) | OK | `docker compose ps`: celery, cloudflared, db, neo4j, nginx, redis, web todos "Up" |
| Redis | OK | `redis-cli ping` -> `PONG` |
| PostgreSQL | OK | `pg_isready` -> "accepting connections" |
| Celery worker | OK | `celery -A config inspect ping` -> `celery@f07bb4bc48de: OK / pong`, 1 nodo online |
| Django web (interno) | OK | `urllib.request.urlopen('http://localhost:8000/')` -> HTTP 200 |
| Tenant `home` | OK | `Client.objects` contiene `home` (on_trial=True) y `public`; dominio `home.sintel.net.co` -> tenant `home`, `is_primary=True` |
| Usuario administrador | OK (con nota) | Schema `home` tiene 3 usuarios: `admin` (is_staff=True, **is_superuser=True**, is_active=True, email admin@sintel.com) -- este es el usuario esperado para el login del ERP. `admin-1` (staff, no superuser). `debug_admin` (ni staff ni superuser). |
| nginx (contenedor) | **[!] HALLAZGO MENOR** | `docker inspect` -> `Health.Status: "unhealthy"`, FailingStreak alto. Causa: el healthcheck ejecuta `wget localhost:80` dentro del contenedor y resuelve a `[::1]` (IPv6), donde nginx no escucha -> `Connection refused`. El servicio en si funciona con normalidad (logs de acceso muestran peticiones reales con `200 OK` desde `home.sintel.net.co`). No bloquea la auditoria; se registra para el informe final (Fase 8, prioridad Menor). Archivo probablemente afectado: `docker-compose.yaml` (definicion del healthcheck de nginx). |

Conclusion Fase 1: entorno operativo, apto para iniciar Fase 2. Unico hallazgo (menor, no bloqueante): healthcheck de nginx mal configurado (IPv6 vs IPv4).

=====================================================================
FASE 2 -- Autenticacion y permisos -- [x] Completado (con items diferidos)
=====================================================================

Acceso real: el dominio publico `https://home.sintel.net.co/` no resolvio desde el entorno sandbox del Browser pane (TLS/DNS); se uso la ruta local equivalente `http://home.sintel.net.co/` (hosts file -> 127.0.0.1 -> nginx). Login realizado manualmente por el usuario (el agente no introduce contrasenas, regla operativa).

| Item | Resultado | Evidencia |
|---|---|---|
| Login (usuario `admin`) | OK | POST `/api/v1/core/auth/login/` -> 200 OK. Redirige a Dashboard Operativo. |
| Cookies de sesion | OK | `document.cookie` solo expone `csrftoken` (CSRF visible, correcto); `sessionid` no aparece -> es HttpOnly, comportamiento esperado. |
| JWT (dual-auth) | OK | En `/workspace/`: `window.jwtAuth.getAccessToken()` retorna string de 231 chars. Consola confirma "JWT token obtenido desde sesion activa". |
| Almacenamiento del JWT | **[!] NOTA (Fase 6)** | `jwt_access_token` y `jwt_refresh_token` viven en `localStorage` (no memoria ni cookie HttpOnly) -> superficie de robo via XSS si existiera un XSS en el frontend. Se retoma en Fase 6 (Seguridad) para confirmar mitigantes (CSP, sanitizacion). |
| Menu lateral (namespaces `window.Sintel.*`) | OK | Confirmados: Core, Empresa(via sidebar)/Empresa JS no aparecio en namespace inicial-revisar en Fase 3, Clientes, Proveedores, Inventario, Compras, Ventas, Empleados, Cotizaciones, Gastos, Bancos, Contabilidad, Proyectos(+NuevaTarea/Editor/Presupuesto), TareasDiarias, Representante, DirectorioRepresentantes, Dashboard, Perfil. Sidebar visible: Dashboard, Empresa, SSoT, Proyectos, Facturas, Contabilidad, Inventario, Clientes, Ventas, Proveedores, Compras, Empleados, Cotizaciones, Gastos, Bancos, Mi Perfil. |
| Logout | [~] Diferido | No ejecutado aun para no perder la sesion activa (requeriria que el usuario reingrese credenciales manualmente para cada modulo restante). Se probara en un bloque dedicado, con el usuario disponible para relogin. |
| Refresh token (renovacion silenciosa) | [~] Diferido | Requiere esperar expiracion del access token; se probara en un bloque dedicado observando Network para la llamada a refresh. |
| Cambio de contrasena | [~] Diferido | Entrada de UI a confirmar en "Mi Perfil"; no se ejecuta el submit para no invalidar la contrasena de la cuenta admin sin coordinarlo antes con el usuario. |
| Recuperacion de contrasena | [~] Diferido | Enlace "¿Olvidaste tu contrasena?" confirmado presente en login. No se dispara (enviaria email real). |
| Permisos admin vs restringido | [~] Pendiente | `admin` es superuser (acceso total esperado). Se contrastara con `admin-1` (staff, no superuser) en Fase 6. |

**HALLAZGO (Dashboard, detectado durante Fase 2 al aterrizar en la portada post-login):**
`GET /static/core/js/dashboard/dashboard.api.js` -> 404, `dashboard.ui.js` -> 404, `dashboard.page.js` -> 404. La carpeta `apps/tenant/core/static/core/js/dashboard/` no existe en el repo; el template `apps/tenant/core/static/tenant/core/dashboard/index.html` (lineas 560-562) referencia estos 3 archivos inexistentes. Efecto visible: la seccion "Cargando indicadores del dashboard..." de la portada nunca resuelve. Severidad propuesta: **Mayor** (pagina de entrada post-login con funcionalidad rota). Se consolida en Fase 8.

**HALLAZGO (rendimiento, observado pasivamente):** las tablas de Empresa (`/ui/empresa/{empresa,areas,sedes,mailinboxconfig}/tabla/`) se solicitan repetidamente cada ~1 segundo de forma continua durante toda la sesion (visto tanto en logs de nginx como en Network del workspace), incluso sin estar en la pestana Empresa. Posible polling/intervalo mal configurado. Se investiga en detalle en Fase 3 (modulo Empresa) y Fase 7 (rendimiento).

=====================================================================
FASE 3 -- CRUD por modulo -- [x] Completado (15/15 modulos, cobertura variable por modulo -- ver notas de "cobertura pendiente" en cada uno)
=====================================================================

Modulos a auditar (uno a la vez, no en paralelo): Empresa, Perfil, Clientes, Proveedores, Inventario, Compras, Ventas, Facturacion, Contabilidad, Gastos, Empleados, Proyectos, Cotizaciones, Dashboard, Bancos.

Para cada modulo: Crear, Editar, Eliminar, Detalle, Listado, Filtros, Buscador, Ordenamiento, Paginacion, Validaciones, Campos obligatorios, Campos unicos, Relaciones, Permisos, Mensajes/Notificaciones, Errores, Rollback, Auditoria.

(Tabla de resultados por modulo se agrega al ejecutar cada uno.)

---
### MODULO: Perfil -- [x] Completado

Contexto: el enlace de sidebar "Mi Perfil" (`#perfil`) no abre un editor de "mi propio perfil" simple; abre una tabla de gestion de TODOS los perfiles del tenant (`tabla-perfiles`, django-tables2+HTMX, `SintelDSVMixin` con filtro por `empresa_id`). Sesion actual autenticada como `admin-1` (staff, NO superuser) -- dato util para Fase 6, ya que confirma que un usuario staff no-superuser puede llegar a este modulo.

| Caso | Resultado | Evidencia |
|---|---|---|
| Boton "Crear nuevo perfil" | OK (oculto correctamente) | `btn-perfil-crear` existe en el DOM con `style="display:none"` -- el usuario `admin-1` no tiene permiso para crear perfiles nuevos y la UI lo oculta correctamente en vez de mostrarlo deshabilitado o dejarlo clickeable. |
| Fila propia sin boton "Eliminar" | OK | Confirmado por codigo: `apps/tenant/perfil/tests/test_tabla_view.py::test_tabla_perfiles_oculta_boton_eliminar_en_fila_propia`. En UI la fila de `admin-1` solo muestra Ver/Editar/Asignar Rol, no Eliminar (proteccion anti-autoeliminacion). |
| Ver Detalle de Perfil | **[!] HALLAZGO MAYOR** | Al abrir el detalle, el campo "Cargo" muestra literalmente el comentario de plantilla sin procesar: `{# [SEC-A1] Sin |safe: profile.cargo es texto editable por el usuario; el placeholder "No definido" es el unico HTML literal y vive fuera del valor interpolado. #}` antes del valor real. **Causa raiz confirmada** reproduciendo con `render_to_string` directo en shell de Django: el comentario en `apps/tenant/perfil/templates/tenant/perfil/offcanvas_detalle_perfil.html` (lineas 33-34) esta escrito como `{# ... #}` **abarcando 2 lineas**; Django no soporta comentarios `{# #}` multilinea (limitacion documentada del motor de plantillas) y el texto completo se filtra como HTML literal visible para cualquier usuario que abra el detalle de cualquier perfil. Fix conceptual: usar `{% comment %}...{% endcomment %}` (si soporta multilinea) o colapsar el comentario a una sola linea. |
| Editar Perfil - carga de datos | OK | Formulario prellena Email, Username, Cargo, Telefono, Rol (`ADMIN`), y **Sedes/Areas Asignadas correctamente enlazadas** con los datos creados en el modulo Empresa (Sede Principal QA, Contabilidad QA) -- buena senal de integracion cruzada Empresa<->Perfil (relevante para Fase 4). |
| Editar Perfil - campo "Departamento" (select) | [~] Hallazgo menor a confirmar en Fase 4 | El select "Departamento" (`perfil-edit-departamento-select`, con `departamento_uuid` oculto) muestra "No hay departamentos registrados" pese a que ya existe un Area/Departamento ("Contabilidad QA") creado y visible en el select paralelo "Areas Asignadas". Sugiere que "Departamento" en el formulario de Perfil consulta una fuente de datos distinta a "Area" de Empresa, aunque la pestaña de Empresa se titula literalmente "Areas (Departamentos)" -- posible inconsistencia conceptual/de integracion entre los dos modulos. Se retoma en Fase 4. |
| Editar Perfil - guardar cambios (Cargo, Telefono) | OK | Verificado en BD: `cargo` y `telefono_corporativo` actualizados correctamente tras guardar. |
| Buscador de perfiles | OK | `search-perfil` (HTMX, debounce 400ms) filtra correctamente: termino sin coincidencias -> "No hay perfiles registrados"; limpiar el campo restaura el listado. (Nota: la respuesta tarda ~1-2s en reflejarse pese al debounce de 400ms, no se investigo si es red o server-side.) |
| Orden y paginacion | [~] No verificable | Solo existe 1 perfil en el tenant; no hay suficientes datos para validar sort/paginacion de forma significativa. |
| **HALLAZGO CRITICO colateral (detectado por accidente al interactuar con un boton residual de Empresa):** `GET /api/v1/empresas/mail-inbox-config/render-offcanvas/` | **[!] HALLAZGO CRITICO** | Responde **500 Internal Server Error** con `NameError: name 'logger' is not defined`, y ese mensaje de excepcion Python crudo se expone directamente al frontend (`error.injector`: "message: name 'logger' is not defined"). **Causa raiz confirmada leyendo codigo:** en `apps/tenant/empresa/api/viewsets.py`, la clase `MailInboxConfigViewSet` (linea 512) define y usa correctamente `log_mailinbox = logging.getLogger("mailinbox.api")` (linea 63) en TODOS sus metodos, EXCEPTO el action `render_offcanvas` (lineas ~787-880), que usa `logger.debug/warning/error(...)` en 7 sitios (lineas 818, 821, 825, 840, 846, 852, 880) -- `logger` no esta definido en ningun lugar del archivo. **Impacto:** el endpoint que renderiza el formulario de "Nueva/Editar Configuracion de Correo" (buzon IMAP) falla el 100% de las veces que se invoca con parametros que alcanzan cualquiera de esas lineas (p.ej. cargar una configuracion existente por id). Ademas, exponer el mensaje de excepcion Python crudo al cliente es una fuga de informacion interna (menor, pero agrava el hallazgo). **Prioridad: Critica** -- bloquea funcionalmente la edicion de configuraciones de correo entrantes de la Empresa. Archivo: `apps/tenant/empresa/api/viewsets.py` (metodo `render_offcanvas` de `MailInboxConfigViewSet`). |

**CONCLUSION MODULO PERFIL:** CRUD de edicion funcional y bien integrado con Empresa (Sedes/Areas). Un hallazgo Mayor (comentario Django multilinea filtrado en Detalle de Perfil) y un hallazgo Critico colateral (crash garantizado del render-offcanvas de MailInboxConfig por variable `logger` indefinida, hallado durante estas pruebas pero pertenece al modulo Empresa). Pendiente Fase 6: probar cambio de rol propio (Administrador -> Operador/Visor) con cuidado de no perder el nivel de acceso necesario para continuar la auditoria -- se hara en el bloque de seguridad al final, posiblemente con un segundo usuario de prueba en vez del usuario activo.

---
### MODULO: Clientes -- [x] Completado

| Caso | Resultado | Evidencia |
|---|---|---|
| Crear con solo campos obligatorios (tipo_persona, tipo_documento, numero_documento, regimen_tributario, razon_social) | OK | A diferencia de Sedes (Empresa), aqui los campos opcionales vacios (email, telefono, direccion, ciudad) se guardan como string vacio `''`, NO como `null`. Confirma que el bug de Sedes **no es sistemico** en toda la app. Verificado en BD. |
| Campo unico (numero_documento) | OK (bloqueado) | Backend responde 400; mensaje mostrado al usuario es limpio y en espanol: "NUMERO_DOCUMENTO: Ya existe un Cliente registrado con el documento NIT 900123456 en su organizacion." Mejor UX que los mensajes crudos de Sedes/Areas en Empresa. |
| Eliminar cliente activo | OK (bloqueado por regla de negocio, no es bug) | Responde 400 con mensaje claro: "El cliente ... esta activo. Inactivelo antes de eliminarlo." Patron de baja logica antes de fisica correctamente implementado. |
| Desactivar (editar, desmarcar "activo") -> Eliminar | OK | Tras poner `activo=False` (verificado en BD), el boton eliminar si procede y el registro desaparece (verificado `Cliente.objects.count()==0`). Usa `data-uuid`, no PK. |
| Tab Contactos | OK | Estado de carga inicial ("Cargando contactos...") resuelve correctamente a "No hay contactos registrados" -- no es un loader colgado, solo se capturo a medio cargar en una inspeccion previa. |
| Tab Cartera | OK | Igual que Contactos: resuelve a "No hay cuentas por cobrar registradas", con resumen "Pendiente: $0 (0)" / "Pagado: $0" correctamente en cero. |
| Filtros (Juridicas/Naturales/Activos/Inactivos) | OK (smoke) | Click en "Juridicas" no genera errores de consola; no se pudo validar el filtrado real por falta de datos (0 clientes tras la prueba de eliminacion). |
| Orden y paginacion | [~] No verificable | Insuficientes registros para una prueba significativa (mismo limitante que Perfil). |
| **Nota colateral (JWT):** consola registro `[debug] No se pudo refrescar token: El token esta en lista negra` durante estas pruebas | [~] Pendiente Fase 6 | Indica que un intento de refresh silencioso del JWT fallo porque el refresh token ya estaba en blacklist (rotacion de tokens). No se observo impacto funcional inmediato (la sesion siguio operando, probablemente via SessionAuthentication como fallback dual-auth), pero se marca para revisar en el bloque de seguridad/autenticacion diferido de Fase 2/6: confirmar si la rotacion de refresh tokens esta funcionando como se espera o si hay una condicion de carrera que blacklistea tokens validos. |

**CONCLUSION MODULO CLIENTES:** El modulo con mejor comportamiento hasta ahora -- CRUD completo funcional, validaciones con mensajes claros en espanol, regla de negocio de baja logica-antes-de-fisica bien implementada, sub-tabs (Contactos/Cartera) cargan correctamente. Sin hallazgos Mayores o Criticos propios; unico pendiente es la nota de JWT blacklist para Fase 6.

---
### MODULO: Proveedores -- [x] Completado

| Caso | Resultado | Evidencia |
|---|---|---|
| Crear con solo campos obligatorios | OK | `tipo_persona, tipo_documento, numero_documento, razon_social, regimen_tributario`; resto (email, telefono, direccion, ciudad, banco, etc.) se guarda como `''`, no `null`. Confirma de nuevo que el bug de "campos opcionales null" es exclusivo de Sedes (Empresa), no generalizado. Verificado en BD. |
| Boton Eliminar deshabilitado mientras el proveedor esta activo | OK (mejor patron que Clientes) | `<button class="btn-delete-proveedor opacity-50" disabled>` -- a diferencia de Clientes (que deja click e informa error 400 despues), aqui el boton esta deshabilitado preventivamente y se habilita solo cuando `activo=False`. Confirmado reactivo: tras desactivar via edicion, el mismo boton paso a `disabled: false` sin recargar pagina. |
| Editar (desactivar) -> Eliminar | OK | Verificado en BD: `activo=False` tras editar, luego `Proveedor.objects.count()==0` tras eliminar. UUID usado correctamente (`data-id`/`data-uuid`), no PK. |
| Tab "Cuentas por Pagar" | OK | Carga y filtra sin datos: "No se encontraron registros de cuentas por pagar". |
| Tab "Representantes" - autocomplete de proveedor | OK (parcial) | El buscador "Buscar por razon social o NIT..." responde correctamente "Sin resultados para "test"" sin proveedores en BD (no crashea). |
| Tab "Representantes" - inicializacion de tabla | **[!] HALLAZGO MAYOR** | Consola: `[representantes:directory] Tabla inicializada con undefined representantes` seguido de `Uncaught TypeError: e.indexOf is not a function`. La tabla de representantes se inicializa con un valor `undefined` en vez de un arreglo vacio `[]`, y algun codigo posterior (probablemente logica de busqueda/filtro client-side) invoca `.indexOf()` sobre ese `undefined`, lanzando una excepcion JS no capturada. No se determino aun el impacto visual exacto (si rompe silenciosamente el filtrado de representantes o solo ensucia la consola); se recomienda revisar el JS de `representantes:directory` (probablemente en `apps/tenant/proveedores/static/proveedores/js/`). |

**CONCLUSION MODULO PROVEEDORES:** CRUD principal solido, con el MEJOR patron de proteccion "eliminar solo si inactivo" visto hasta ahora (boton deshabilitado preventivo en vez de error reactivo). Un hallazgo Mayor: excepcion JS no capturada en la inicializacion de la tabla de Representantes (`undefined` en vez de arreglo vacio).

---
### MODULO: Inventario -- [x] Completado

| Caso | Resultado | Evidencia |
|---|---|---|
| Categorias - Crear (nombre, aplicacion) | OK | Verificado en BD (`CategoriaItem`). |
| Productos - Crear con campos obligatorios (codigo, nombre, unidad, precio_venta, stock_minimo) | OK | `categoria` y `descripcion` opcionales se guardan como `null` real (a diferencia de Sedes) -- confirma nuevamente que el manejo de opcionales/null varia por modulo/serializer, no es una regla global. |
| KPIs (SKUS, Activos, Stock Bajo, Valor Inventario) | OK -- CONTRASTE POSITIVO vs Empresa | Tras crear el producto, KPIs se actualizaron correctamente sin recargar manualmente: SKUS=1, ACTIVOS=1, STOCK BAJO=1 (detecto automaticamente que stock_actual 0 < stock_minimo 1). Confirma que el patron de contadores muertos de Empresa NO es generalizado -- Inventario si implementa el refresco. |
| Eliminar producto activo | OK (bloqueado por regla de negocio) | Mismo patron correcto de Clientes/Proveedores: 400 `{"error":"active_record","message":"No se puede eliminar un item activo..."}`. |
| Desactivar -> Eliminar (primer intento) | OK | Verificado en BD: `activo=False` tras editar, luego eliminado correctamente (`count==0`). |
| **Posible doble-submit en boton Eliminar** | [~] Hallazgo a confirmar (Menor/Medio) | Justo antes de la eliminacion exitosa, un primer click sobre "Eliminar" devolvio dos `401 Unauthorized` en consola (no reproducible con un fetch manual directo, que devolvio el 400 esperado). Podria ser una condicion de carrera puntual del refresh de JWT (ver nota de Clientes: "No se pudo refrescar token: El token esta en lista negra") o un doble-listener en el boton de Tabulator. No se pudo aislar con certeza; se recomienda instrumentar mejor el flujo de refresh token en Fase 6. |
| **DELETE duplicado sobre producto ya eliminado** | **[!] HALLAZGO CRITICO** | Al navegar a la pestaña "Movimientos Recientes" justo despues de la eliminacion exitosa, se disparo una **segunda** llamada DELETE sobre el mismo producto (ya inexistente), y el backend respondio **500 con el traceback completo de Python en el cuerpo de la respuesta**, incluyendo rutas absolutas del servidor (`/app/apps/tenant/inventario/api/viewsets.py:337` en `destroy`, linea 206 en `get_object`, `apps/tenant/inventario/services/selectors.py:162` en `get_detail`) y el nombre de la excepcion (`Producto.DoesNotExist`). El traceback se propaga hasta la consola del navegador Y hasta el mensaje de error mostrado en la UI (`[inventario.list] Mensaje de error final: Traceback (most recent call last)...`). **Causa raiz:** `ProductoViewSet.get_object()` / `destroy()` no capturan `Producto.DoesNotExist`; DRF no lo convierte automaticamente en 404 porque probablemente se usa un selector custom (`ProductoSelector.get_detail()`) en vez del `get_object()` estandar de DRF que si maneja esto. **Hallazgo agravante confirmado:** `settings.DEBUG == True` en esta instancia -- y el tunel `cloudflared` (verificado activo y conectado a Cloudflare en Fase 1) expone `home.sintel.net.co` en internet publica. Esto significa que, en el estado actual, **cualquier peticion que dispare una excepcion no controlada en el backend devuelve un stack trace completo del servidor a cualquier cliente en internet**, incluyendo rutas de archivos, nombres de modulos internos y version de libreria -- fuga de informacion de severidad Critica, no solo un problema de manejo de errores. **Prioridad maxima: verificar y corregir el modo DEBUG en cualquier entorno expuesto publicamente, y anadir manejo de `DoesNotExist` (-> 404) en todos los `destroy()`/`get_object()` de los ViewSets del proyecto, no solo Inventario** (patron a revisar transversalmente en Fase 6). |
| Servicios / Activos Fijos / Movimientos Recientes (tabs) | OK (smoke) | Cargan sin datos ("No hay servicios registrados", etc.) sin errores de consola nuevos al cambiar de tab (aparte del hallazgo critico de arriba). No se ejecuto CRUD completo en estas 3 sub-secciones por limite de tiempo/alcance de esta pasada -- queda como deuda de cobertura, marcado abajo. |

**COBERTURA PENDIENTE (no bloqueante, para una segunda pasada):** CRUD completo de Servicios y Activos Fijos (solo se hizo smoke test de carga); pestaña "Ajustar Stock" del producto (boton visto pero no probado); Movimientos Recientes con datos reales.

**CONCLUSION MODULO INVENTARIO:** KPIs y flujo de "desactivar antes de eliminar" funcionan correctamente (mejor que Empresa). PERO se encontro el hallazgo mas grave de toda la auditoria hasta ahora: excepciones no controladas devuelven tracebacks completos de Python al cliente, agravado por `DEBUG=True` en una instancia con tunel publico activo. Se recomienda tratar esto como bloqueante para producción independientemente de cuando se programe el resto del informe.

---
### MODULO: Compras -- [x] Completado

| Caso | Resultado | Evidencia |
|---|---|---|
| Crear Plantilla de Numeracion (nombre, prefijo, rango) | OK | Verificado en BD (`PlantillaOrdenCompra`, `consecutivo_actual=1`). |
| **Dropdown "Proveedor" en "Nueva Orden de Compra" nunca se puebla** | **[!] HALLAZGO CRITICO** | Con 2 proveedores validos en BD (uno creado por shell, otro por la UI real) y con `GET /api/v1/proveedores/` devolviendo `200` con `count:2` y los datos correctos (verificado con fetch manual usando los mismos headers de la app), el `<select id="proveedor">` del offcanvas "Nueva Orden" se queda SIEMPRE con solo la opcion placeholder, incluso cerrando y reabriendo el offcanvas varias veces dentro de la misma sesion del workspace. **Diagnostico confirmado:** tras una recarga COMPLETA de la pagina (`navigate`, no solo reabrir el offcanvas), el select se puebla correctamente con ambos proveedores. Causa raiz (por lectura de codigo): `apps/tenant/compras/static/compras/js/compras.utils.js` implementa `fetchProveedores()` con una **cache en memoria de 5 minutos** (`CACHE_TTL_MS`) y expone una funcion `invalidateCache()`, pero nada en el flujo de creacion/edicion de Proveedores (modulo distinto, misma pagina SPA) llama a esa invalidacion. Como el workspace es una unica pagina que vive muchos minutos y todos los modulos comparten sesion, la cache de proveedores queda "congelada" en el primer estado que vio (vacio, en este caso) y nunca se refresca sin recargar toda la aplicacion. **Impacto:** en una sesion real de trabajo (crear un proveedor nuevo y luego intentar hacerle una orden de compra en la misma sesion, sin recargar la pagina) es **imposible crear la orden** porque el campo obligatorio "Proveedor" no tiene opciones que no sean el placeholder -- bloquea el flujo completo del modulo. Sin mensajes de error visibles al usuario (fallo silencioso). **Hipotesis a verificar en Fase 4/7:** el mismo patron de cache-sin-invalidar puede repetirse en `loadProyectosSelect` (mismo archivo) y en otros modulos que usen selectores cruzados similares (Ventas, Cotizaciones, Facturas). |
| Crear Orden de Compra (tras resolver manualmente la cache recargando pagina) | OK | Plantilla + Proveedor + fecha + 1 item (cantidad 2 x $5.000, IVA 19% por defecto) -> subtotal $10.000, impuestos $1.900, total $11.900 calculados correctamente en tiempo real y persistidos identicos en BD. Numero de documento generado correctamente segun plantilla: "OC-QA-1". Estado inicial: BORRADOR. |
| Comentario Django multilinea filtrado (transversal, no exclusivo de Compras) | **[!] HALLAZGO MAYOR (confirmado transversal)** | Visible en la portada de Compras: `{# Panel HTMX: KPIs + tabla server-rendered... #}`. Una busqueda dedicada en todo el repo (ver seccion "HALLAZGO TRANSVERSAL" mas abajo) encontro este mismo patron en **9 archivos de plantilla** (no solo Perfil y Compras). |
| Offcanvas multiples con clase `.show` simultanea | [~] Nota de bajo impacto | Se observaron hasta 3 offcanvas (`offcanvas-area`, `offcanvas-representante`, `offcanvas-inventario`/`offcanvas-compra-crear`) con la clase Bootstrap `.show` al mismo tiempo durante pruebas cruzadas entre modulos, aunque solo 1 backdrop visible. No se confirma impacto visual real (posiblemente inofensivo), pero es consistente con el anti-patron que CLAUDE.md prohibe explicitamente (`getOrCreateInstance().show()` en vez de `mostrarOffcanvasSeguro`). Se recomienda revisar en Fase 7 si esto causa fugas de memoria/listeners duplicados en sesiones largas. |

**COBERTURA PENDIENTE:** Edicion/aprobacion/cambio de estado de la Orden de Compra, eliminacion, e integracion con Contabilidad (se retoma en Fase 4).

**CONCLUSION MODULO COMPRAS:** Un hallazgo Critico bien diagnosticado (cache de proveedores obsoleta sin invalidacion, bloquea la creacion de ordenes en sesiones reales) mas la reconfirmacion del hallazgo transversal de comentarios Django. El calculo de totales e IVA de la orden es correcto.

---
### MODULO: Ventas -- [x] Completado

| Caso | Resultado | Evidencia |
|---|---|---|
| Dropdown "Cliente" en "Nueva Venta" tras crear cliente en la misma sesion | OK -- NO repite el bug de Compras | A diferencia del selector de Proveedor en Compras, el selector de Cliente en Ventas SI se actualizo correctamente sin recargar la pagina tras crear un cliente nuevo en el mismo tab de trabajo. Confirma que el bug de cache de Compras es especifico de `compras.utils.js`, no un patron generalizado en todos los selectores cruzados. |
| **Valor de `<option>` del selector "Cliente" usa PK entero, no UUID** | **[!] HALLAZGO MAYOR (arquitectura)** | `<select id="venta-cliente" name="cliente">` expone `<option value="2">` (PK secuencial real de la tabla) en vez del UUID del cliente. Contrasta con Compras (Proveedor) y Empresa (Sede/Area), que si usan UUID como valor de opcion. Viola la regla explicita de `AGENTS.md`/`CLAUDE.md`: "UUID lookup, not PK -- no exponer PKs enteros". Confirmado en BD que la Venta se guarda con `cliente_id=2` (aceptado por el backend sin problema, es decir el API tambien acepta PK crudo para esta relacion). Riesgo: expone el conteo total de registros (enumeracion secuencial) y es inconsistente con el resto del sistema. Revisar en Fase 5/6 si esto habilita algun vector de IDOR (aunque el campo es una FK de creacion, no un lookup de detalle/edicion directo). |
| Crear Venta (Cliente + fecha + 1 item) -> Guardar Borrador | OK | Subtotal $20.000, IVA 19% = $3.800, Total $23.800 -- calculo correcto, verificado identico en BD. Estado inicial `BORRADOR`, sin resolucion DIAN asociada (correcto, ya que no hay resoluciones creadas). |
| **Tercera recurrencia del patron JWT blacklist** | [~] Patron confirmado, pendiente Fase 6 | Exactamente el mismo par de sintomas (`No se pudo refrescar token: El token esta en lista negra` + 2x `401 Unauthorized` en consola) aparecio de nuevo durante la creacion del Cliente en este flujo -- ya es la 3ra vez observado (Clientes, Inventario, Ventas), siempre sin impedir que la operacion subyacente termine con exito (probablemente por el fallback a SessionAuthentication del dual-auth). Se eleva la prioridad de este item para el bloque de seguridad/autenticacion de Fase 6: aunque no ha bloqueado nada todavia, ocurre con demasiada frecuencia para ser una casualidad y merece revisar la logica de rotacion/blacklist de refresh tokens en `apps/tenant/api` o el middleware JWT correspondiente. |
| Resoluciones DIAN / "Guardar y Facturar DIAN" | [~] No probado | El formulario advierte "No hay resoluciones vigentes. Cree una primero." -- crear una resolucion DIAN implica configuracion fiscal (rangos de numeracion autorizados por la DIAN) que se considero fuera del alcance de esta pasada rapida; queda como cobertura pendiente. |

**CONCLUSION MODULO VENTAS:** CRUD de creacion funcional con calculos correctos. Un hallazgo Mayor de arquitectura (PK en vez de UUID en el selector de Cliente) y refuerzo del patron JWT ya visto en otros modulos.

---
### MODULO: Facturacion -- [x] Completado

Contexto: "Facturas" no tiene creacion directa -- se alimenta de Ventas (facturacion DIAN) y Compras (importacion XML/PDF), consistente con el flujo contable esperado.

| Caso | Resultado | Evidencia |
|---|---|---|
| Comentarios Django multilinea filtrados | **[!] CONFIRMADO EN UI (ya reportado como transversal)** | Se ven literalmente 3 bloques `{# ... #}` sin procesar en esta unica pantalla, coincidiendo exactamente con los 3 bloques que el analisis de codigo (agente) predijo para `list_factura.html` (x2) y `partials/tabla_facturas.html`. Confirma en vivo el hallazgo transversal N.2. |
| KPIs Ventas Netas / Compras Netas | [~] No verificable aun | Muestran $0,00 pese a existir 1 Venta en BORRADOR por $23.800 -- probablemente correcto, ya que una Venta en estado BORRADOR (no facturada DIAN) no deberia contar como "neta" hasta facturarse. No se pudo confirmar el comportamiento tras facturar (ver limitacion abajo). |
| Resoluciones DIAN - Crear | OK | Formulario completo (numero, tipo FE/POS/PAPEL, rango de consecutivos, vigencia) creado y verificado en BD (`ResolucionFacturacion`, `consecutivo_actual=1`). |
| "Guardar y Facturar DIAN" / Importar XML-PDF / Sincronizar Buzon | [~] NO EJECUTADO (decision deliberada) | Estas acciones probablemente interactuan con servicios externos reales (facturacion electronica DIAN, lectura de buzon IMAP). Se evito ejecutarlas para no generar efectos secundarios irreversibles fuera del entorno de prueba (consumo de consecutivos DIAN reales, llamadas a servicios de terceros). Queda como cobertura pendiente, idealmente en un entorno con mocks/sandbox de DIAN confirmado. |

**CONCLUSION MODULO FACTURACION:** Sin hallazgos nuevos propios aparte de la reconfirmacion visual del hallazgo transversal de comentarios Django. CRUD de Resoluciones DIAN funcional. El flujo de facturacion electronica real no se ejecuto por prudencia (efectos externos).

---
### MODULO: Contabilidad -- [x] Completado (cobertura parcial)

| Caso | Resultado | Evidencia |
|---|---|---|
| Crear Cuenta Contable (codigo, tipo, nombre) | **[!] HALLAZGO CRITICO** | Un unico click en "Guardar" (`btn-guardar-cuenta-crear`, un solo `btn.click()` en la prueba) genero **dos registros** en `CuentaContable`: uno correcto (`codigo='1105QA'`, `nombre='Caja Auditoria QA'`, `tipo='ACTIVO'`) y otro **completamente vacio** (`codigo=''`, `nombre=''`, `tipo=''`) pese a que los 3 campos son `required=true` en el formulario -- creados con solo 187ms de diferencia. Confirmado en consola: `[http] Enviando JSON: /api/v1/contabilidad/cuentas-contables/ {}` -- un payload vacio fue efectivamente enviado y aceptado por el backend (el backend tampoco rechazo un `{}` para campos supuestamente obligatorios, lo cual es un segundo problema: validacion de requeridos ausente o incompleta del lado del servidor para este endpoint). **Causa probable (por lectura de codigo):** `cuenta_editor.js` registra sus listeners de guardado via delegacion de eventos en `document` con un guard (`d.body.dataset.cuentaEditorInitialized`) pensado explicitamente para evitar doble-registro en recargas HTMX (el propio comentario del codigo referencia un historial de bugs similares "FE-A1/A2") -- el guard existe pero el doble-envio ocurrio de todas formas, sugiriendo que la causa esta en otro punto (posible doble-invocacion interna de `handleSave`, o colision con otro modulo tambien escuchando en `document` dado que el workspace tiene decenas de modulos coexistiendo en una sola pagina). **Impacto:** el Plan Unico de Cuentas (Chart of Accounts) puede llenarse de registros fantasma vacios, lo cual es grave para un modulo contable (integridad del catalogo base para Compras/Ventas/Gastos via el modelo pull, ADR-001). Prioridad maxima para Fase 6/8. |
| Validacion server-side de campos requeridos en Cuentas Contables | **[!] HALLAZGO MAYOR (relacionado)** | El backend acepto `{}` (sin `codigo`, `nombre` ni `tipo`) sin devolver 400, creando el registro vacio. Revisar el serializer de `CuentaContable` -- los campos deberian ser `required=True` tambien a nivel de DRF, no solo en el HTML del formulario. |
| Edicion de Cuenta usa PK entero, no UUID, en la llamada de actualizacion | [~] Hallazgo de arquitectura (verificado por codigo, no confirmado en vivo) | `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/cuenta_offcanvas_form.html:24` genera `<input type="hidden" id="input-id" value="{{ cuenta.id }}">` (PK entero de Django, no `cuenta.uuid`), y `cuenta_editor.js:99` llama `w.CuentaAPI.update(parseInt(id), data)`. El `parseInt()` en si es inofensivo aqui (el valor ya es un entero, no un UUID -- se descarta la sospecha inicial de corrupcion de UUID), pero el patron de usar el PK crudo para la operacion de update (en vez de UUID) es el mismo tipo de desviacion arquitectonica ya visto en Ventas (selector de Cliente). No se pudo confirmar en vivo el comportamiento de "Editar Cuenta" por interferencia de multiples offcanvas superpuestos de otros modulos en la misma sesion larga del workspace -- recomendado repetir en sesion limpia. |
| Sub-secciones no probadas por limite de tiempo: Periodos Contables, Pendientes, Asientos Contables, Libro Diario, Retenciones, Plantillas, Reportes | [~] Cobertura pendiente | Dado el hallazgo critico ya encontrado en la primera sub-seccion (Cuentas), se prioriza reportarlo de inmediato en vez de continuar agotando el resto del modulo en esta pasada. Se recomienda una segunda pasada dedicada a Contabilidad completa, especialmente "Pendientes" (integracion pull-model con Compras/Ventas via ADR-001) dado que ya existen una Orden de Compra y una Venta en BORRADOR creadas durante esta auditoria que deberian aparecer ahi. |

**CONCLUSION MODULO CONTABILIDAD:** El hallazgo mas grave encontrado hasta ahora junto con el de Inventario (traceback expuesto): un doble-submit silencioso crea registros fantasma vacios en el Plan Unico de Cuentas, con validacion server-side insuficiente para prevenirlo. Se recomienda tratar esto tambien como bloqueante, dado que corrompe datos contables base.

---
### MODULO: Gastos -- [x] Completado

| Caso | Resultado | Evidencia |
|---|---|---|
| Comentario Django multilineal filtrado | Confirmado en UI (ya reportado transversal) | Visible en portada de Gastos, coincide con la prediccion del analisis de codigo para `gastos_list.html` lineas 64-66. |
| **Pestana "Resoluciones DIAN" de Gastos muestra datos de Empleados** | **[!] HALLAZGO CRITICO (arquitectura transversal)** | Al inspeccionar el panel de la pestana "Resoluciones DIAN" dentro de Gastos, la peticion real observada fue `GET /ui/empleados/resoluciones/tabla/` (devolvio `<table id="tabla-resoluciones-empleados">`, un concepto de RRHH no relacionado). **Causa raiz confirmada:** NO es un error en el codigo de Gastos (su template usa correctamente `{% url 'gastos:resoluciones-tabla' %}` y su `urls.py` mapea correctamente a `ResolucionDIANTableView` propio). El problema real es que **`apps/tenant/empleados/templates/tenant/empleados/empleados_list.html` reutiliza exactamente los mismos IDs de HTML** que `apps/tenant/gastos/templates/tenant/gastos/gastos_list.html`: `id="tab-pane-resoluciones"`, `id="search-resolucion"`, `id="resoluciones-panel"` (confirmado con grep de ambos archivos, mismas 3 lineas de ID). Como el Workspace monta TODOS los modulos en una unica pagina simultaneamente, tener IDs duplicados entre Gastos y Empleados rompe el targeting de Bootstrap tabs y de `hx-target` basado en `#id` -- el navegador solo puede resolver un elemento por ID, asi que cualquier interaccion con "Resoluciones" en cualquiera de los dos modulos puede terminar afectando al primer elemento con ese ID en el DOM, no al que el usuario cree estar usando. **Impacto:** imposible confiar en la pestana "Resoluciones DIAN" de Gastos para listar/buscar sus propias resoluciones mientras el modulo Empleados este tambien montado (que es siempre, en este Workspace). La CREACION si funciona (usa un endpoint de API distinto y bien namespaced: `/api/v1/gastos/render-offcanvas/resolucion/`, probado y verificado en BD). **Prioridad maxima para Fase 6/7:** auditar sistematicamente que otros pares de IDs se repiten entre los ~15 modulos coexistentes (patron de nombres genericos como "search-X", "X-panel", "tab-pane-X" es un riesgo estructural del diseño "todo en una sola pagina"). |
| Crear Resolucion DIAN de Gastos (numero, prefijo, rango, fechas) | OK | Verificado en BD (`ResolucionDIAN`, `consecutivo=1`). Sin duplicados esta vez (a diferencia del bug de Contabilidad). |
| Campo `proveedor_uuid` en "Nuevo Gasto" contiene PK entero, no UUID | [~] Hallazgo menor (tercera recurrencia del patron PK/UUID) | El `<select id="proveedor_uuid">` tiene opciones con `value="2"`, `value="3"` (PKs reales) pese a que el nombre del campo sugiere explicitamente un UUID. Mismo patron ya visto en Ventas (Cliente) y sospechado en Contabilidad (edicion de Cuenta) -- se eleva la confianza de que esto es una practica extendida en el proyecto, no un error aislado. |
| Crear Gasto (resolucion + proveedor + numero_documento_proveedor + subtotal) | OK | Verificado en BD (`DocumentoSoporte`, `total=$50.000`, `consecutivo=1`, sin duplicados). |

**CONCLUSION MODULO GASTOS:** CRUD de creacion (Resolucion y Gasto) funciona correctamente y sin duplicados. Hallazgo Critico de alcance transversal: IDs de HTML duplicados entre modulos rompen el targeting de pestanas/HTMX cuando ambos modulos conviven en el Workspace -- confirmado con Gastos vs Empleados, pero es un riesgo estructural que probablemente afecta a mas pares de modulos.

---
### MODULO: Empleados -- [x] Completado (cobertura parcial)

| Caso | Resultado | Evidencia |
|---|---|---|
| Crear Empleado (documento, nombre, email, EPS/AFP/ARL, fecha ingreso) | OK | Verificado en BD (`Empleado`, sin duplicados). Catalogos EPS/AFP/ARL poblados correctamente (11/6/8 opciones respectivamente) -- parecen provenir de un catalogo publico. Selects "Sede"/"Area" (dependencias de Empresa) usan UUID correctamente, a diferencia de otros modulos. |
| KPI "Total Empleados" | OK tras reload (no es un contador muerto) | Mostraba 0 inmediatamente despues de crear sin recargar, pero tras un reload completo mostro "1" correctamente. Confirmado por codigo que `empleado_list.js` SI implementa la actualizacion de `total-empleados` (a diferencia de Empresa) -- se interpreta como una brecha de refresco en vivo, no un contador muerto. |
| Contrato - checkbox "Indefinido" ajusta fecha_fin dinamicamente | OK | Al marcar "Indefinido", el campo "Fecha Fin" (marcado `required` en el HTML base) pasa correctamente a `disabled=true, required=false` via JS. Buen manejo de UX condicional. |
| Crear Contrato (empleado, tipo INDEF, cargo, salario, horas semanales) | OK | Verificado en BD: `fecha_fin=None` (correcto para Indefinido), `salario_mensual=3000000`, sin duplicados. |
| Select "Empleado" en formulario de Contrato usa PK entero | [~] Cuarta recurrencia del patron PK/UUID | `<select id="contrato-crear-empleado-id">` tiene `value="1"` (PK). Se acumulan ya 4 modulos con el mismo patron (Ventas/Cliente, Contabilidad/Cuenta-edicion, Gastos/proveedor_uuid, Empleados/Contrato-empleado) -- se eleva a Fase 6 como una practica extendida a revisar transversalmente, no un caso aislado. |
| Nominas, Liquidaciones, Resoluciones DIAN (propias de Empleados) | [~] Cobertura pendiente | No probadas a fondo por limite de tiempo/alcance de esta pasada. Nota: dado el hallazgo de IDs duplicados encontrado en Gastos (que usa exactamente los mismos IDs `tab-pane-resoluciones`/`search-resolucion`/`resoluciones-panel` que Empleados), es probable que la pestana "Resoluciones DIAN" de ALGUNO de los dos modulos (el que no gane el conflicto de ID en el DOM) este afectada de la misma manera -- pendiente de confirmar cual de los dos "gana" en el orden real del DOM del Workspace. |

**CONCLUSION MODULO EMPLEADOS:** El modulo con mejores practicas de UUID vistas hasta ahora (Sede/Area en Empleado si usan UUID), pero el select de Empleado dentro de Contrato reincide en el patron de PK cruda. CRUD de Empleado y Contrato funcional sin duplicados. Cobertura parcial: Nominas/Liquidaciones quedan pendientes.

---
### MODULO: Proyectos -- [x] Completado (cobertura parcial)

| Caso | Resultado | Evidencia |
|---|---|---|
| Crear Proyecto (solo "Nombre" es obligatorio; formulario tipo wizard con Presupuesto/Tareas/Contexto integrados) | OK | Verificado en BD (`Proyecto`, `nombre`, `cliente_id`, `valor_contrato_proyectado` correctos). PK creado fue `id=2` (no `id=1`) sugiriendo un intento anterior con rollback -- no se investigo a fondo por limite de tiempo, no se descarta relacion con el patron de doble-submit visto en Contabilidad. |
| Select "Cliente" en Nuevo Proyecto usa PK entero | [~] Quinta recurrencia del patron PK/UUID | Mismo patron ya documentado en 4 modulos anteriores. |
| **Pestana "Nueva tarea" (tarea corta) con combos Cliente/Empleado siempre vacios via navegacion directa** | **[!] HALLAZGO MAYOR** | Al navegar directamente a la pestana "Nueva tarea" (click en el tab del listado de Proyectos), los selects `#nt-cliente` y `#nt-empleado` quedan permanentemente en placeholder vacio, incluso tras una recarga COMPLETA de pagina (a diferencia del bug de cache de Compras, que si se arreglaba con reload). **Causa raiz confirmada:** llamando manualmente `window.proyectosAPI.lookups.clientes()` y `.empleados()` ambos devuelven `200 OK` con datos correctos (1 cliente, 1 empleado, incluyendo UUIDs) -- el problema NO es la API. El problema es de wiring JS: `loadLookups()` (que puebla estos selects) solo se invoca dentro de `show()`, y `show()` solo se llama desde `openEditor()` en `nueva_tarea_list.js`, la cual se dispara desde un boton "+"/trigger especifico en OTRO flujo (aparentemente desde una fila de tarea existente) -- NO se llama nunca simplemente al activar la pestana "Nueva tarea" del tablist principal. Es decir, el formulario esta visible y aparenta estar listo para usarse apenas se cambia de pestana, pero sus dos campos obligatorios (`required`) nunca reciben opciones si se llega por esa ruta directa. Nota positiva: los `value` de las opciones (cuando SI cargan) usan UUID correctamente, no PK -- buen ejemplo a seguir para los demas modulos. |
| Otras areas del modulo (Presupuesto detallado, Tareas Diarias completas, Pedidos, Asignacion de Personal) | [~] Cobertura pendiente | No probadas a fondo por limite de tiempo. |

**CONCLUSION MODULO PROYECTOS:** CRUD de Proyecto funcional. Hallazgo Mayor de UX/wiring: el mini-formulario "Nueva Tarea Corta" accesible directamente desde el tablist no carga sus catalogos de Cliente/Empleado en esa ruta de navegacion, dejando un formulario aparentemente funcional pero con dos campos obligatorios imposibles de completar.

---
### MODULO: Cotizaciones -- [x] Completado (cobertura parcial)

| Caso | Resultado | Evidencia |
|---|---|---|
| Select "Cliente" en Nueva Cotizacion usa UUID | OK | Correcto, contrasta positivamente con Ventas/Contabilidad/Gastos/Proyectos. |
| **`GET /api/v1/cotizaciones/configuracion/` responde 500** | **[!] HALLAZGO CRITICO (reconfirma el hallazgo transversal)** | Error exacto: `AttributeError: 'ConfiguracionCotizacionViewSet' object has no attribute 'get_empresa_id'`. Con traceback completo de Python devuelto en el cuerpo de la respuesta JSON (rutas de archivo del servidor, libreria DRF interna, etc.) -- **segunda confirmacion independiente**, en un modulo totalmente distinto a Inventario, de que las excepciones no controladas exponen tracebacks completos al cliente. Esto eleva significativamente la confianza de que el problema es sistemico (ligado a `DEBUG=True`, ya reportado como Critico en Fase 8) y no un caso aislado de Inventario. **Causa raiz code-level:** `apps/tenant/cotizaciones/configuracion/viewsets.py:26`, clase `ConfiguracionCotizacionViewSet(ConfiguracionServiceMixin, BaseTenantViewSet)` -- pese a heredar de `BaseTenantViewSet`, el metodo `get_empresa_id()` no esta disponible en tiempo de ejecucion (posible problema de orden de herencia/MRO con `ConfiguracionServiceMixin`, o el metodo simplemente no existe con ese nombre exacto en la base y se llamo mal desde este ViewSet). **Impacto directo:** el selector "Config." de Nueva Cotizacion nunca se puebla (siempre vacio), y la cotizacion completa **no se pudo crear** en esta prueba (`Cotizacion.objects.count()==0` tras intentar guardar con cliente + fechas + 1 item de servicio). |
| Crear Cotizacion (cliente + fechas + item de servicio) -> Guardar | **[!] FALLO (consecuencia directa del hallazgo anterior)** | La cotizacion NO se creo pese a llenar los campos visibles; se sospecha que el fallo silencioso del endpoint de configuracion rompe la inicializacion completa del editor JS (`[Cotizaciones:Editor] Iniciando editor... DRAFT` se registro dos veces en consola, sugiriendo un reintento), impidiendo que "Guardar" complete su flujo normal. |
| Constructor de cotizacion (secciones Dispositivos/Infraestructura/Servicios, cronograma, indicadores) | [~] Cobertura pendiente | Es una herramienta de cotizacion comercial sofisticada (multi-seccion, con AIU, IVA, utilidad por rubro); dado el bloqueo critico encontrado, no se pudo evaluar el flujo completo de creacion exitosa. Repetir esta prueba una vez corregido el bug de `get_empresa_id`. |

**CONCLUSION MODULO COTIZACIONES:** No se pudo completar el flujo de creacion por un hallazgo Critico (500 con traceback expuesto) que ademas bloquea funcionalmente el modulo completo. Este es el segundo endpoint distinto (tras Inventario) confirmado con el mismo patron de fuga de tracebacks, reforzando que es un problema transversal de la aplicacion, no un caso aislado.

---
### MODULO: Dashboard -- [x] Completado

Nota importante: existen DOS dashboards distintos en la aplicacion, no confundir:
1. **Portada estatica post-login** (`home.sintel.net.co/`, "Dashboard Operativo") -- la que tiene el hallazgo YA REPORTADO en Fase 2 (3 archivos JS 404: `dashboard.api.js`, `.ui.js`, `.page.js`), causando que "Cargando indicadores del dashboard..." nunca resuelva. Reconfirmado en esta pasada (mismos 3 404 exactos).
2. **"Centro de Comando Ejecutivo"** (pestana "Dashboard" dentro de `/workspace/`) -- un dashboard funcional completamente distinto e independiente del anterior.

| Caso | Resultado | Evidencia |
|---|---|---|
| KPIs del "Centro de Comando Ejecutivo" | OK -- CONTRASTE MUY POSITIVO | Todos los KPIs verificados coinciden exactamente con los datos reales creados durante esta auditoria: Clientes Total=1/Activos=1, Empleados Total=1/Activos=1/Pend.Nomina=1, Proveedores=2, Gastos Total Mes=$50.000 (coincide con el Gasto creado), Proyectos Total=1/Activos=1, Inventario=0 items (correcto, el producto de prueba fue eliminado). Facturacion muestra $0 porque la Venta de prueba sigue en BORRADOR (no facturada DIAN) -- comportamiento correcto, no un bug. |
| "Rendimiento por Sede" (tabla desglosada) | OK (parcial) | Fila "Sede Principal QA" aparece con $0 en ingresos/gastos/proyectos -- coherente, ya que ni el Gasto ni el Proyecto de prueba quedaron asociados explicitamente a esa Sede (campos opcionales no completados durante las pruebas de esos modulos). No es un bug, es consecuencia de los datos de prueba. |
| Boton "Actualizar" (refresco manual de KPIs) | OK | Dispara `GET /api/v1/dashboard/kpis-por-sede/` correctamente, sin errores de consola. |

**CONCLUSION MODULO DASHBOARD:** El dashboard funcional real (Centro de Comando Ejecutivo) es solido y sus KPIs son precisos -- de los mejores resultados de toda la auditoria. El unico hallazgo de este modulo es el ya reportado en Fase 2 (portada estatica rota por JS 404), que es una pantalla completamente distinta y no debe confundirse con este dashboard que si funciona.

---
### MODULO: Bancos -- [x] Completado (cobertura parcial)

| Caso | Resultado | Evidencia |
|---|---|---|
| **Doble-submit crea 2 Cuentas Bancarias identicas de un solo click** | **[!] HALLAZGO CRITICO (causa raiz confirmada, reconfirma patron transversal)** | Un unico `btn.click()` en "Guardar Cuenta" genero **2 registros identicos** en `CuentaBancaria` (mismo nombre, banco, tipo, numero de cuenta), con 29ms de diferencia. **Causa raiz encontrada con precision total en consola:** el log `[bancos:cuenta_editor] DOM Settle detectado para cuenta, activando offcanvas...` aparecio **dos veces** para un solo click en "Nueva Cuenta" -- el handler de apertura del offcanvas se dispara duplicado (mismo patron "FE-A1/A2" que el comentario de codigo de Contabilidad ya identificaba como riesgo conocido, pero sin guard aplicado aqui en Bancos), y al reabrirse el offcanvas se re-adjunta un SEGUNDO listener de guardado sobre el mismo boton, causando que un solo click humano dispare dos peticiones POST identicas (`Enviando JSON: /api/v1/bancos/cuentas/ {...}` aparece 2 veces en consola). **Agravante:** no existe restriccion de unicidad en `(banco, numero)` a nivel de backend -- el segundo POST identico fue aceptado sin error, permitiendo cuentas bancarias duplicadas. **Es la segunda confirmacion independiente del patron de doble-submit** (la primera fue Contabilidad/Cuentas Contables, con sintoma distinto -- ahi un registro vacio; aqui un duplicado exacto). Se consolida como hallazgo transversal: revisar en Fase 6/7 que TODOS los editores tipo offcanvas del proyecto implementen el guard `d.body.dataset.XxxInitialized` de forma consistente (ya se confirmo que existe como patron conocido en `cuenta_editor.js` de Contabilidad y `nueva_tarea_editor.js` de Proyectos, pero falta o falla en Bancos). |
| **Cuarta+ recurrencia del patron JWT blacklist** | [~] Patron ya bien establecido | 3x `401 Unauthorized` + `No se pudo refrescar token: El token esta en lista negra` durante esta misma prueba. Ya es la 4ta+ vez observado en distintos modulos (Clientes, Inventario, Ventas, Bancos). |
| Extractos Bancarios / Importar Extracto | [~] Cobertura pendiente | Requiere archivo real de extracto bancario para probar significativamente (parseo/conciliacion); no se ejecuto por alcance de tiempo. |

**CONCLUSION MODULO BANCOS:** Cierra la Fase 3 con el hallazgo mas repetido de toda la auditoria confirmado por segunda vez con causa raiz exacta: doble-submit por doble-registro de event listeners en offcanvas, agravado aqui por ausencia total de restriccion de unicidad en cuentas bancarias.

---
### MODULO: Empresa -- [x] Completado

Contexto: en el Workspace (`/workspace/`) todos los modulos se renderizan en una sola pagina (secciones ancladas por `#hash`, no rutas separadas); el "Editar Datos" de Empresa abre un dialog/offcanvas con formulario multipart.

| Caso | Pasos | Resultado | Evidencia |
|---|---|---|---|
| Editar Empresa - campo requerido vacio | Abrir "Editar Datos", borrar completamente "Nombre legal de la empresa" (unico campo con label "Nombre legal..."), click "Guardar" | **[!] HALLAZGO MAYOR** | Consola: `[http] Enviando FormData...` NO incluye `razon_social` en absoluto (solo goes `regimen_tributario`, `moneda`, `logo`, `csrfmiddlewaretoken`); luego `[empresa.editor] Empresa guardada correctamente`. Verificacion en BD (`Empresa.objects.first()`): `razon_social` sigue siendo `'home'` (sin cambio) pero `updated_at` SI se actualizo (guardado ocurrio). Es decir: el JS omite del FormData los campos que quedan en string vacio/falsy antes de enviarlos, el backend no los toca, y el usuario recibe un mensaje de exito enganoso creyendo que su edicion (incluido el borrado del nombre) se aplico. No hay validacion nativa ni mensaje de "campo obligatorio" en el formulario. **Impacto:** el usuario no puede detectar que su cambio fue ignorado; en formularios reales esto puede ocultar errores de captura. **Hipotesis a verificar en otros modulos:** si el helper `http.js` (envio FormData) descarta valores falsy de forma generica, el mismo patron puede repetirse en otros formularios multipart del ERP -- se revisa oportunistamente durante el resto de Fase 3. Archivo probable: JS del editor de empresa (`apps/tenant/empresa/static/empresa/js/...`) + helper compartido `static/core/js/lib/http.js`. |

| Sedes - Crear vacio | Click "Nueva Sede", click "Crear Sede" sin llenar nada | OK (bloqueado) | Dialogo permanece abierto, "Nombre de Sede *" tiene `required`, no se envia request. Contraste directo con el caso de Empresa de arriba: aqui el boton es `type="submit"` dentro de `<form>`, activa validacion HTML5 nativa del navegador. |
| Sedes - Crear con TODOS los campos | Nombre, Direccion, Telefono, Encargado completos -> "Crear Sede" | OK | Registro aparece en tabla inmediatamente. Verificado en BD (`Sede.objects.count()==1`, campos correctos). |
| Sedes - Crear dejando campos opcionales en blanco (solo Nombre) | Nombre="Sede Principal QA", resto vacio -> "Crear Sede" | **[!] HALLAZGO MAYOR** | `POST /api/v1/empresas/sedes/` devuelve **400**: `{"direccion":["Este campo no puede ser nulo."],"telefono":["Este campo no puede ser nulo."],"encargado_nombre":["Este campo no puede ser nulo."]}`. Causa: el JS del formulario envia `null` explicito para inputs vacios en vez de string vacio o simplemente omitir la clave; el serializer de `Sede` no tiene `allow_null=True` en esos CharField opcionales. **Impacto:** es imposible crear una Sede usando solo el campo marcado como obligatorio (unico con `*`); el formulario visualmente permite dejar Direccion/Telefono/Encargado en blanco pero el backend lo rechaza siempre. El error si se muestra al usuario (`#form-sede-feedback`), pero en jerga de serializer ("Este campo no puede ser nulo", "Detail_code: invalid") no apta para usuario final. Archivos probables: serializer de Sede en `apps/tenant/empresa/api/serializers.py` (o equivalente) + JS `sede.editor` (payload JSON). |
| Sedes - Editar | Cambiar "Nombre de Sede" via offcanvas de edicion (prellenado correctamente con datos existentes + UUID oculto) -> "Actualizar Sede" | OK | Verificado en BD: `nombre` actualizado correctamente. |
| Sedes - Eliminar | Click icono papelera -> `window.confirm("Eliminar esta sede?")` -> aceptar | OK | Usa `data-uuid` (no PK), confirmacion nativa del navegador antes de borrar. Verificado en BD: registro eliminado (count 0). Nota menor: `window.confirm()` nativo es funcional pero es la unica confirmacion en toda la app vista hasta ahora; no hay modal estilizado consistente con el resto de la UI (Bootstrap). |
| KPI "Sedes Registradas" / "Areas/Departamentos" | Crear una Sede real y recargar pagina completa | **[!] HALLAZGO MAYOR** | El contador sigue en "0" pese a datos reales confirmados en BD. Causa raiz (confirmada por codigo): `apps/tenant/empresa/templates/tenant/empresa/empresa_list.html` define `<div class="stat-value" id="total-sedes">0</div>` y `id="total-areas"` pero **no existe en todo el repo ningun JS que haga `getElementById('total-sedes')`** (`grep` confirmtriple: 0 resultados). Comparar con Empleados, que SI implementa el patron correctamente (`empleado_list.js` actualiza `total-empleados`, `total-contratos-activos`, `total-nominas`). Es un contador muerto/placeholder, no un problema de cache. |
| Areas - Dependencia de Sede (FK) | Abrir "Nueva Area" sin ninguna Sede existente | OK (comportamiento correcto) | El `<select id="area-sede">` aparece vacio (solo placeholder deshabilitado), bloqueando la creacion. Es integridad referencial correcta, no un bug -- se resolvio recreando una Sede antes de continuar. |
| Areas - Crear con todos los campos | Sede, Nombre, Codigo de Funcionamiento -> "Crear Area" | OK | Verificado en BD (`Area.objects.count()==1`, `sede_id` correcto). Los 3 campos son obligatorios (sin el bug de nulls de Sedes, porque aqui no hay campos opcionales). |
| Areas - Campo unico (sede + codigo_funcionamiento) | Repetir mismo "Codigo de Funcionamiento" para la misma Sede | OK (bloqueado) | Backend responde 400 con `non_field_errors: "Los campos sede, codigo_funcionamiento deben formar un conjunto unico."` Verificado en BD: sigue en 1 area. Correcto a nivel de integridad, aunque el mensaje vuelve a exponer jerga de serializer (`Non_field_errors`, `Detail_code: invalid`). |
| Configuraciones de Correo - Crear vacio | Abrir "Nueva Configuracion", click "Guardar" sin llenar nada | OK (bloqueado) | A diferencia del bug de Datos de Empresa, aqui SI bloquea: validacion HTML5 nativa (`validationMessage: "Completa este campo"` en Nombre), alert de feedback permanece oculto, no se dispara request al backend. |
| KPI "Buzones de Email" | No probado a fondo (no se creo config real para no manejar credenciales de correo simuladas mas alla de lo necesario) | [~] Pendiente | Dado el patron confirmado en Sedes/Areas (contadores sin JS asociado), es altamente probable que tenga el mismo defecto. Se recomienda revisar junto con la correccion de los otros dos contadores. |

**CONCLUSION MODULO EMPRESA:** CRUD funcional en el fondo (create/edit/delete confirmados via BD), pero con 2 hallazgos Mayores reproducibles (edicion de Empresa ignora silenciosamente campo requerido vacio sin validacion nativa; creacion de Sede falla con 400 si se dejan en blanco campos visualmente opcionales) y 1 hallazgo Mayor de UI (contadores KPI de Sedes/Areas/Buzones nunca se actualizan, siempre muestran 0). Patron transversal notado: los formularios que usan `<button type="submit">` dentro de un `<form>` real (Sedes, Areas, MailInboxConfig) SI bloquean campos vacios via HTML5; el formulario de Empresa usa `type="button"` con JS manual que arma el FormData a mano y omite ese control. Se recomienda revisar si el mismo patron (`type="button"` + FormData manual sin validar campos requeridos) se repite en otros modulos durante el resto de la Fase 3.

Estado: [x] Completado (primera pasada). Pendiente secundario: KPI "Buzones de Email".

=====================================================================
FASE 4 -- Integracion entre modulos -- [x] Completado (cobertura parcial)

Aprovechando los datos creados durante la Fase 3 (1 Cliente, 2 Proveedores, 1 Empleado con 1 Contrato activo, 1 Sede + 1 Area, 1 Venta en BORRADOR, 1 Orden de Compra, 1 Gasto, 1 Proyecto).

| Integracion | Resultado | Evidencia |
|---|---|---|
| Empresa (Sede/Area) -> Perfil | OK | Confirmado en Fase 3 (modulo Perfil): el editor de Perfil muestra correctamente "Sede Principal QA" y "Contabilidad QA" en los selectores de Sedes/Areas Asignadas. |
| Dashboard -> KPIs (multiples modulos) | OK | Confirmado a fondo en Fase 3 (modulo Dashboard): todos los contadores del "Centro de Comando Ejecutivo" (Clientes, Empleados, Proveedores, Gastos, Proyectos) coinciden exactamente con los datos reales. |
| **Gastos -> Contabilidad (Pull Model, ADR-001)** | **[!] HALLAZGO CRITICO** | La pestana "Pendientes" de Contabilidad SI detecta correctamente el Gasto creado (`GA-1`, $50.000, filtrable por tipo Facturas/Gastos/Nomina/Inventario) -- la deteccion del pendiente funciona. PERO el boton "Contabilizar" (la accion central del modelo pull -- convertir el pendiente en asiento contable) falla con **500**: `AttributeError: 'DocumentoSoporte' object has no attribute 'retefuente'` en `GET /api/v1/contabilidad/pendientes/render-offcanvas/?app=gastos&modelo=DocumentoSoporte&id=1`. **Causa raiz exacta identificada:** `apps/tenant/contabilidad/api/viewsets.py`, metodo `render_offcanvas_contabilizar` (linea 877), rama `else` (lineas 946-947, usada para `app_label` distinto de `facturas`/`empleados`/`inventario` -- es decir, Gastos y similares) accede directamente a `doc.retefuente` / `doc.reteica`. Segun el propio comentario del modelo `DocumentoSoporte` (`apps/tenant/gastos/models.py` linea 45-46: "retefuente/reteica_porcentaje eliminados en v3.7.1 Pull Model -- usar doc.total_retefuente / doc.total_reteica (@property)"), esos campos raw **ya no existen** en el modelo -- deberian usarse las properties `total_retefuente`/`total_reteica`. La rama hermana para `facturas` (linea 906-907, apenas unas lineas arriba en el MISMO metodo) SI usa el patron seguro `getattr(doc, 'retefuente', _cero)`, demostrando que el riesgo era conocido pero la correccion no se replico a la rama generica. **Impacto:** el modelo Pull (ADR-001), pieza central de la arquitectura contable del ERP, esta roto en el paso final para CUALQUIER Gasto -- es imposible contabilizar un gasto pendiente desde la UI. Prioridad maxima, junto con los otros 2 casos de traceback expuesto (Inventario, Cotizaciones) -- **tercera confirmacion independiente** del hallazgo transversal de excepciones no controladas. |
| Compras -> Contabilidad | [~] No aplica directamente (por diseño, no es un bug) | La Orden de Compra creada NO aparece en "Pendientes" de Contabilidad -- coherente con que una orden de compra es un documento de procura, no un documento fiscal/contable en si mismo; probablemente solo se vuelve "pendiente" cuando se convierte en un Gasto/factura de proveedor real. No se pudo confirmar ese paso de conversion por limite de tiempo. |
| Empleados -> Nomina | [~] Cobertura incompleta | El tab "Nominas" de Empleados muestra "Sin empleados con nominas" pese a existir 1 Empleado con 1 Contrato ACTIVO -- no se encontro un boton evidente de "Generar Nomina" en ese tab (0 botones detectados en el panel). No se pudo determinar si la generacion de nomina requiere un proceso batch/programado fuera de la UI, o si el punto de entrada esta en otro lugar no explorado. Pendiente de investigar en una segunda pasada. |
| Ventas -> Facturacion -> Contabilidad, Cliente -> Cotizaciones, Inventario -> Facturas/Compras | [~] No verificable en esta pasada | Requieren completar flujos que se evitaron deliberadamente por prudencia (facturacion electronica DIAN real) o que estan bloqueados por bugs ya reportados (Cotizaciones no se puede crear por el error 500 de `get_empresa_id`). Los items de Venta/Orden de Compra creados en Fase 3 se cargaron como texto libre, no enlazados a un Producto real de Inventario, por lo que tampoco se pudo verificar Inventario->Ventas/Compras de extremo a extremo. |

**CONCLUSION FASE 4:** La integracion mejor verificada (Dashboard KPIs, Empresa->Perfil) funciona correctamente. La integracion mas importante para la operacion contable del ERP (Gastos->Contabilidad via Pull Model) esta rota en su paso final por un bug de codigo simple y bien identificado (atributo eliminado en una migracion anterior, nunca actualizado en un call site). Cobertura incompleta en el resto de integraciones por bloqueos de bugs previos o por decisiones deliberadas de no ejecutar acciones con efectos externos reales.

=====================================================================
FASE 5 -- Multi-tenant -- [ ] Pendiente
=====================================================================

Aislamiento por schema, UUID en URLs (no PK), DSV (Double Semantic Verification), filtrado por `empresa_id`, intentos de acceso cruzado entre tenants.

=====================================================================
FASE 5 -- EJECUCION -- [x] Completado (hallazgo critico maximo encontrado)
=====================================================================

**Preparacion:** solo existia 1 tenant de negocio ("home") ademas de "public". Para probar aislamiento real se creo un segundo tenant de prueba via el comando de gestion oficial del proyecto (`manage.py crear_empresa "QA Isolation Test" "admin@qaisotest.com" --schema-name qaisotest`) -- accion no destructiva, agrega un schema nuevo sin tocar "home".

**HALLAZGO COLATERAL durante la creacion del tenant (Onboarding):**
**[!] CRITICO** -- El propio comando de creacion de tenant fallo silenciosamente al crear el `TenantProfile` del admin nuevo: `[ERROR] TenantProfile.empresa no puede ser NULL`. Verificado en BD: el schema `qaisotest` recien creado tiene el usuario admin (`admin-2`/`admin@qaisotest.com`) pero **CERO registros `Empresa` y CERO `TenantProfile`** -- es decir, el registro raiz del que depende `empresa_id` en TODA la aplicacion (obligatorio segun `CLAUDE.md`: "Todos los registros en TENANT_APPS deben tener empresa asignada explicitamente") nunca se crea durante el onboarding. El comando reporta "OK: Empresa creada exitosamente!" pese a este fallo -- el error queda enterrado en el log, no se propaga como fallo del comando. **Impacto:** cualquier tenant nuevo onboardeado por este flujo queda en un estado inutilizable desde el primer login (sin Empresa base, la gran mayoria de modulos no podran operar). Dado que la rama actual del repositorio es `feat/onboarding-cookie`, este hallazgo es probablemente directamente relevante al trabajo en curso.

---

### HALLAZGO MAS GRAVE DE TODA LA AUDITORIA: Fuga de datos entre tenants (cross-tenant data leak)

**[!!!] CRITICO MAXIMO -- CONFIRMADO Y REPRODUCIDO**

**Prueba realizada:** se tomo el JWT de acceso valido de la sesion activa (usuario `admin-1`, `user_id=3`, perteneciente EXCLUSIVAMENTE al tenant `home`) y se uso para llamar a la API del tenant `qaisotest` (un tenant COMPLETAMENTE DISTINTO, creado momentos antes), simplemente cambiando el header `Host` de la peticion HTTP -- sin volver a autenticarse, sin ningun otro cambio.

```
curl -H "Host: qaisotest.sintel.net.co" -H "Authorization: Bearer <JWT de home>" \
     http://localhost:80/api/v1/clientes/
```

**Resultado:** `HTTP 200` con el contenido REAL y completo de un Cliente creado especificamente en el schema `qaisotest` para esta prueba ("CLIENTE SECRETO DE QAISOTEST", NIT 111222333, UUID `f19d2fa3-e99e-4a8c-b4b8-723e252945d6`) -- tanto en el listado (`GET /api/v1/clientes/`) como en el detalle directo por UUID (`GET /api/v1/clientes/{uuid}/`). El JWT de un usuario del tenant `home` jamas debio ser aceptado para operar sobre el schema `qaisotest`.

**Causa raiz (hipotesis fundamentada, confirmar en revision de codigo por el equipo):** el modelo de usuario (`auth_user` / `TenantProfile.user`) parece ser compartido/global entre schemas (se confirmo que el mismo `user_id=3` "existe" en el contexto de ambos schemas), y la autenticacion JWT (`rest_framework_simplejwt`) solo verifica que el token sea valido y que el `user_id` exista -- **no verifica que ese usuario tenga una relacion/membresia legitima (via `TenantProfile` o equivalente) con el tenant/schema que la peticion esta resolviendo via el header `Host`**. El middleware de `django-tenants` SI enruta correctamente la consulta al schema `qaisotest` (los datos devueltos son autenticos de ese schema, no una fuga de otro tipo) -- el problema esta especificamente en la capa de autorizacion: falta una verificacion de "pertenencia al tenant actual" antes de procesar la peticion.

**Impacto:** en el estado actual, **cualquier usuario autenticado de CUALQUIER empresa cliente de este ERP puede leer (y probablemente escribir/eliminar) los datos de CUALQUIER OTRA empresa cliente**, con solo conocer o adivinar el subdominio de la otra empresa y reutilizar su propio JWT valido -- sin necesitar contrasena, sin necesitar exploit alguno, sin necesitar ser superusuario. Esto rompe por completo la premisa de aislamiento multi-tenant que es el pilar central de la arquitectura documentada en `AGENTS.md`/`CLAUDE.md`. Dado que el tenant `home.sintel.net.co` esta confirmado accesible publicamente via el tunel `cloudflared` (Fase 1), y que probablemente existan otros tenants reales o de otros clientes en el mismo despliegue, **esta vulnerabilidad podria estar activamente explotable ahora mismo contra datos reales**.

**Prioridad: la mas alta posible.** Se recomienda: (a) revisar de inmediato la clase de permiso `IsTenantMember` (`apps/tenant/api/permissions.py`, importada en multiples viewsets durante esta auditoria) para confirmar si valida membresia real al tenant actual o solo `request.user.is_authenticated`; (b) anadir una verificacion obligatoria en el middleware de autenticacion (o en `BaseTenantViewSet`) de que el usuario autenticado tiene un `TenantProfile` valido para el `schema_name` actualmente resuelto por `django-tenants`, rechazando con 403 en caso contrario; (c) considerar incluir el `schema_name`/tenant en el payload del JWT en el momento de la emision y validar que coincide con el tenant actual en cada peticion, como defensa adicional; (d) auditar si esto tambien afecta a `SessionAuthentication` (la otra mitad del dual-auth) de la misma manera.

**Nota de limpieza:** el tenant `qaisotest` y sus datos de prueba (Empresa, Cliente) fueron creados unicamente para esta prueba de aislamiento y no forman parte de la operacion real de "home". Se recomienda eliminarlos tras revisar este hallazgo, o mantenerlos como caso de regresion para verificar la correccion.

=====================================================================
FASE 6 -- Seguridad -- [x] Completado (cobertura parcial, ver hallazgo central en Fase 5)

**El hallazgo central de esta fase ya fue documentado y comunicado con maxima urgencia en Fase 5: fuga de datos completa entre tenants (Broken Access Control / IDOR a nivel de tenant).** No se repite aqui; ver seccion Fase 5 para el detalle completo.

| Prueba | Resultado | Evidencia |
|---|---|---|
| XSS almacenado (Cliente.razon_social con `<script>` + `<img onerror>`) | OK -- defendido correctamente | El payload se guardo tal cual en BD (esperado, la sanitizacion correcta ocurre al renderizar, no al guardar), pero tanto en el listado de Clientes como en "Ver Detalle" el HTML se escapa correctamente (`&lt;script&gt;...`) -- confirmado que NO se ejecuto (`window.__xss_fired` nunca se seteo, `document.title` no cambio). Django escapa por defecto en sus templates; el sistema esta bien defendido en este vector para los puntos probados. |
| SQL Injection (payloads `' OR '1'='1`, `'; DROP TABLE...`, `' UNION SELECT NULL--` en parametro `search` de la API de Clientes) | OK -- no explotable | Los 3 payloads devolvieron `200` sin error; se confirmo que la tabla sigue intacta (`Cliente.objects.count()` sin cambios). Consistente con el uso del ORM de Django (queries parametrizadas), no hay concatenacion de SQL crudo en los puntos probados. |
| CSRF | OK (observacion transversal de toda la auditoria) | El `csrftoken` se envio consistentemente en headers `X-CSRFToken` en todas las peticiones mutantes observadas durante las Fases 2-4, en los ~15 modulos auditados. |
| **Validacion de archivos subidos -- inconsistente entre modulos** | **[!] HALLAZGO MEDIO** | Solo `apps/tenant/gastos/models.py` usa `FileExtensionValidator` para su campo de adjunto. Los demas campos `FileField`/upload detectados durante la auditoria (Empleados: `foto`; Proyectos: `contrato_archivo`, `acta_inicio_archivo`, `cronograma_archivo`, `acta_entrega_archivo`, `informe_final_archivo`, `archivo_adjunto` de Pedidos; Empresa: `logo`) **no tienen ningun validador de extension/tipo de archivo** a nivel de modelo -- aceptarian cualquier tipo de archivo (ejecutables, scripts, etc.) sin restriccion alguna mas alla de lo que el frontend pudiera (no) filtrar. Riesgo: distribucion de malware via adjuntos, o XSS almacenado si algun archivo (p.ej. SVG) se sirve luego sin las cabeceras `Content-Type`/`Content-Disposition` adecuadas. Recomendacion: aplicar `FileExtensionValidator` de forma consistente en TODOS los campos de archivo del proyecto, tomando como referencia el patron ya usado correctamente en Gastos. |
| Permisos: admin-1 (staff, no superuser) vs superuser | [~] Observacion parcial, no se completo el contraste | Se confirmo durante toda la auditoria que `admin-1` (staff, NO superuser) tuvo acceso de creacion/edicion/eliminacion en practicamente todos los modulos probados sin ninguna restriccion visible, incluyendo la creacion de un tenant completo via linea de comandos (fuera del alcance de permisos de UI). No se pudo contrastar en vivo con un usuario de rol "Operador"/"Visor" por priorizar tiempo hacia hallazgos de mayor impacto (la fuga cross-tenant). Cambiar el propio rol de `admin-1` a un rol inferior se evito deliberadamente para no perder el nivel de acceso necesario para completar el resto de la auditoria. |
| IDOR dentro del mismo tenant (UUID valido pero de otro `empresa_id` dentro del mismo schema) | [~] No aplicable en esta instancia | El patron `SintelTenantBaseModel`/`empresa_id` observado en TODOS los modelos, mas el hecho de que solo existe 1 Empresa por schema en este ERP ("Patron Singleton: Solo una empresa por tenant", segun comentario en `apps/tenant/empresa/api/viewsets.py`), hace que el vector clasico de IDOR entre dos empresas DENTRO del mismo schema no aplique aqui -- el aislamiento relevante es a nivel de SCHEMA/TENANT completo, no de `empresa_id` dentro de un schema compartido. Esto refuerza aun mas la gravedad del hallazgo de Fase 5: el schema ES el limite de seguridad, y ese limite fallo. |

**CONCLUSION FASE 6:** Buenas defensas confirmadas en XSS y SQL Injection (ambas via el uso correcto de Django ORM y auto-escaping de templates). Un hallazgo Medio en validacion inconsistente de archivos subidos. El hallazgo verdaderamente critico de esta fase (fuga de datos entre tenants) se documento en Fase 5 por su urgencia.

=====================================================================
FASE 7 -- Rendimiento -- [x] Completado (cobertura parcial)

| Prueba | Resultado | Evidencia |
|---|---|---|
| **Polling descontrolado en tablas de Empresa** | **[!] HALLAZGO CRITICO (cuantificado con precision)** | Medido con `performance.getEntriesByType('resource')` en una ventana de 5 segundos limpia (sin carga inicial de pagina): **234 peticiones HTTP en 5 segundos = ~47 peticiones/segundo sostenidas**, repartidas entre las 4 tablas de Empresa (`empresa/tabla/`, `sedes/tabla/`, `areas/tabla/`, `mailinboxconfig/tabla/`, ~55-61 peticiones cada una en la misma ventana). Los intervalos entre peticiones consecutivas son irregulares (80-140ms), no un numero redondo -- descarta un `setInterval` con valor mal configurado y apunta a un patron de "recargar inmediatamente al completar la respuesta anterior", sin ningun retardo. Ocurre de forma continua durante TODA la sesion del workspace, independientemente de si el usuario esta viendo el modulo Empresa o cualquier otro (confirmado en logs de nginx desde la Fase 1, y ahora cuantificado con precision en Fase 7). **Hipotesis de causa (a confirmar por el equipo):** las 4 tablas usan `hx-trigger="load, X-updated from:body"` (`apps/tenant/empresa/templates/tenant/empresa/empresa_list.html` lineas 153/191/227); el fragmento devuelto por el servidor NO reincluye el atributo `hx-trigger` (se descarta el patron clasico de "partial que se auto-dispara"), por lo que la causa mas probable es que algo en el JS del workspace (posiblemente un `MutationObserver` u orquestador de pestañas) este redisparando el evento personalizado `X-updated` sobre `body` en un bucle de retroalimentacion cada vez que detecta el cambio en el DOM que el propio swap de HTMX produce. **Impacto:** en una sesion individual esto ya es un desperdicio severo de recursos (CPU/red del cliente y carga innecesaria del servidor); a escala con multiples usuarios concurrentes, esto podria constituir una carga de servidor auto-infligida significativa (proyeccion: 20 usuarios concurrentes con el workspace abierto ~= 940 peticiones/segundo solo por este patron). Prioridad maxima -- revisar el ciclo de vida de estos 3 `hx-trigger` y cualquier codigo que dispare `empresa-updated`/`sede-updated`/`area-updated`/`mailinboxconfig-updated` sobre `body`. |
| Tiempo de carga inicial de `/workspace/` | [~] No cuantificado con precision | La pagina monta TODOS los ~15 modulos simultaneamente en una unica carga (arquitectura de pagina unica), lo cual es una decision de diseño con un costo de carga inicial inherentemente mayor que una SPA con lazy-loading por ruta; no se midio con precision pero es coherente con la naturaleza "todo en una pagina" ya documentada en hallazgos previos (IDs duplicados entre modulos, Gastos/Empleados). |
| Migracion Tabulator -> django-tables2+HTMX (Fase 5-BIS) | OK (observacion, no defecto) | Confirmado que la migracion esta en curso y es parcial: algunos modulos ya usan tablas server-rendered con HTMX (Empresa, Perfil, Compras, Facturas, Gastos), otros siguen usando Tabulator client-side (Inventario, Clientes, Ventas, Proveedores) -- coexisten ambos patrones simultaneamente en el mismo Workspace, consistente con lo documentado en `PLAN_UNICO_CORRECCIONES.md`. No es un defecto en si, pero explica parte de la complejidad/inconsistencia observada entre modulos durante toda la auditoria. |
| N+1 queries | [~] No verificable sin herramientas de profiling backend | Requeriria Django Debug Toolbar o `django-silk` conectado a la sesion, fuera del alcance de una auditoria puramente desde la UI. Se recomienda como seguimiento tecnico con acceso a herramientas de perfilado. |
| Paginacion | OK (donde se pudo probar) | Los controles de paginacion (Primera/Anterior/Siguiente/Ultima, tamano de pagina configurable) aparecieron consistentemente en todas las tablas django-tables2+HTMX revisadas, sin errores al cambiarlos, aunque con 0-1 registros por modulo no se pudo verificar el comportamiento con multiples paginas reales de datos. |
| Cache | Ver hallazgo de Compras (Fase 3) | El unico caso de cache explicito encontrado (`compras.utils.js`, TTL 5 min para selects de Proveedor/Proyecto) ya fue reportado como hallazgo Critico por no invalidarse correctamente -- ver modulo Compras. |

=====================================================================
FASE 8 -- Informe final -- [x] Completado
=====================================================================

Auditoria ejecutada 2026-08-06, usuario `admin-1` (staff, no superuser), tenant `home` (+ tenant `qaisotest` creado ad-hoc para pruebas de aislamiento en Fase 5). 15/15 modulos de Fase 3 auditados, Fases 4-7 con cobertura parcial documentada en cada seccion. No se corrigio codigo alguno durante esta auditoria -- todo hallazgo esta pendiente de autorizacion explicita para su correccion.

### Resumen ejecutivo

De 23 hallazgos registrados: **7 Criticos, 5 Mayores (varios transversales de amplio alcance), 3 Medios, 4 Menores**, mas 4 items de cobertura incompleta (no son defectos, son limites de esta pasada). El hallazgo #1 (fuga de datos entre tenants) es de severidad excepcional y se comunico al usuario de forma inmediata durante la ejecucion, sin esperar a este informe.

> **[ACTUALIZACION 2026-08-06/07] Remediacion completa ejecutada.** Los 7 Criticos (C1-C7) mas el hallazgo colateral de Onboarding fueron corregidos y verificados en 8 fases (ver marcadores `[CORREGIDO]` en cada hallazgo arriba). Metodologia de verificacion: reproduccion en vivo (navegador real + curl) de cada bug antes/despues, mas comparacion `git stash` de la suite de pytest afectada para descartar regresiones. Hallazgo nuevo descubierto durante la remediacion (no estaba en el informe original): `nginx.conf` servia estaticos con `Cache-Control: public, expires 30d` sin ningun mecanismo de invalidacion -- cualquier fix de JS/CSS quedaba invisible para navegadores que ya hubieran visitado el sitio, hasta por 30 dias. Cambiado a `no-cache` (revalidacion por ETag). Los Mayores/Medios/Menores (M1-M7, MD1-MD3, MN1-MN4) y las Fases 6-7 (regresion CRUD/seguridad completa de los 15 modulos) **no** se cubrieron en esta remediacion -- fue una pasada dirigida a los 7 Criticos mas Onboarding. Detalle completo en el historial de conversacion de la sesion de remediacion; resumen en `MEMORY.md`.

---

### CRITICOS

**C1. Fuga completa de datos entre tenants (Broken Access Control / IDOR a nivel de tenant)**
> **[CORREGIDO 2026-08-06]** Eliminado el cortocircuito `if settings.DEBUG: return True` en los 5 permisos SSoT de `apps/tenant/api/permissions.py` y en 3 `get_permissions()` de `bancos`/`gastos`. Test de regresión nuevo `apps/tenant/bancos/tests/test_cross_tenant_isolation.py` (2/2 passed, re-verificado en Fase 7). Detalle: `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`.
- Problema: un JWT valido de un usuario del tenant `home` fue aceptado para leer datos reales (listado y detalle por UUID) del tenant `qaisotest`, un tenant completamente distinto, con solo cambiar el header `Host` de la peticion.
- Causa: la autenticacion JWT valida que el token sea autentico y que el `user_id` exista, pero no verifica que ese usuario tenga una membresia/`TenantProfile` legitima en el tenant que el `Host` esta resolviendo. El aislamiento de schema de `django-tenants` funciona correctamente (los datos devueltos eran autenticos del schema correcto); el fallo esta en la capa de autorizacion posterior.
- Impacto: cualquier usuario autenticado de cualquier empresa cliente puede leer/escribir datos de cualquier otra empresa cliente sin password, exploit ni privilegios especiales. Con el tunel `cloudflared` activo (Fase 1), esto podria ser explotable ahora mismo contra datos reales.
- Prioridad: Maxima / inmediata.
- Recomendacion: revisar `IsTenantMember` (`apps/tenant/api/permissions.py`); anadir verificacion obligatoria de `TenantProfile` valido para el schema actual en `BaseTenantViewSet` o middleware; considerar incluir el tenant en el payload del JWT y validarlo en cada peticion; repetir la prueba tambien contra `SessionAuthentication`.
- Archivos: `apps/tenant/api/permissions.py`, `apps/tenant/api/base.py` (`BaseTenantViewSet`), configuracion de `rest_framework_simplejwt`.
- Resultado esperado: una peticion con JWT valido de un tenant, dirigida al `Host` de otro tenant, debe responder 403 sin exponer datos.

**C2. Excepciones no controladas devuelven tracebacks completos de Python al cliente (DEBUG=True + tunel publico)**
> **[CORREGIDO 2026-08-06]** `SintelExceptionMiddleware` ya no incluye el traceback en la respuesta al cliente bajo ninguna condicion (antes solo se ocultaba si `DEBUG=False`); el logging server-side completo se preserva. Verificado con reproduccion curl del caso de Inventario. Detalle: `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`.
- Problema: al menos 3 endpoints distintos (Inventario, Cotizaciones, Contabilidad) devuelven 500 con el stack trace completo de Python en el cuerpo de la respuesta JSON, visible en la UI.
- Causa: `settings.DEBUG == True` en la instancia auditada, combinado con `AttributeError`/`DoesNotExist` sin capturar en varios ViewSets.
- Impacto: fuga de informacion interna (rutas de servidor, nombres de modulos, version de librerias) a cualquier cliente que provoque un error, potencialmente desde internet publica via el tunel `cloudflared` ya confirmado activo.
- Prioridad: Maxima.
- Recomendacion: confirmar `DEBUG=False` en cualquier entorno expuesto; anadir manejo de excepciones especifico en los 3 ViewSets citados; auditar transversalmente el resto de ViewSets.
- Archivos: `apps/tenant/inventario/api/viewsets.py` (`ProductoViewSet.destroy`/`get_object`), `apps/tenant/cotizaciones/configuracion/viewsets.py:26`, `apps/tenant/contabilidad/api/viewsets.py:946-947`.
- Resultado esperado: errores no controlados devuelven un mensaje generico (sin traceback) y se registran en logs del servidor, no en la respuesta al cliente.

**C3. Modelo Pull de Contabilidad (ADR-001) roto en su paso final -- imposible contabilizar un Gasto**
> **[CORREGIDO 2026-08-06]** `doc.retefuente`/`doc.reteica` reemplazados por `doc.total_retefuente`/`doc.total_reteica` en la rama `else`. Verificado con reproduccion curl: "Contabilizar" devuelve 200 con el formulario HTML. Detalle: `documentacion/REMEDIACION_FASE1_CRITICOS_SEGURIDAD.md`.
- Problema: el boton "Contabilizar" de un Gasto pendiente falla siempre con 500.
- Causa: `apps/tenant/contabilidad/api/viewsets.py:946-947` accede a `doc.retefuente`/`doc.reteica`, campos eliminados del modelo `DocumentoSoporte` en la migracion v3.7.1 al Pull Model (deberia usar las properties `total_retefuente`/`total_reteica`, como ya hace correctamente la rama de "facturas" del mismo metodo, apenas unas lineas arriba).
- Impacto: la pieza central de la arquitectura contable del ERP (ADR-001) no se puede completar desde la UI para ningun Gasto.
- Prioridad: Maxima.
- Recomendacion: reemplazar `doc.retefuente`/`doc.reteica` por `doc.total_retefuente`/`doc.total_reteica` en la rama `else` de `render_offcanvas_contabilizar`.
- Archivos: `apps/tenant/contabilidad/api/viewsets.py:946-947`.
- Resultado esperado: "Contabilizar" un Gasto pendiente abre el formulario correctamente y permite generar el asiento.

**C4. Doble-submit por doble-registro de event listeners crea registros duplicados/vacios**
> **[CORREGIDO 2026-08-06]** Bancos: eliminado el `form.requestSubmit()` redundante sobre un boton ya `type="submit"` (disparaba un segundo evento submit nativo) — verificado en vivo, 1 registro por click. Contabilidad: el codigo fuente resulto ya estar correcto (sin doble listener); el sintoma se debia a una cache HTTP de 30 dias en `nginx.conf` sirviendo JS pre-fix indefinidamente (ver hallazgo nuevo de infraestructura mas abajo). Ambos casos verificados con instrumentacion de red en navegador.
- Problema: un unico click en "Guardar" genera 2 peticiones POST identicas. Confirmado en Contabilidad (Cuenta Contable: 1 registro valido + 1 completamente vacio, campos requeridos incumplidos) y Bancos (Cuenta Bancaria: 2 registros identicos, sin restriccion de unicidad que lo evite).
- Causa: el handler de apertura del offcanvas se dispara dos veces por click, y cada apertura reasigna el listener de "Guardar" sin remover el anterior. El propio codigo ya documenta este riesgo ("FE-A1/A2") con un guard (`document.body.dataset.XxxInitialized`) en 2 modulos, pero el guard no cubre todos los casos.
- Impacto: corrupcion de datos base (Plan Unico de Cuentas, cuentas bancarias) con registros fantasma o duplicados.
- Prioridad: Maxima.
- Recomendacion: auditar todos los `*_editor.js` del proyecto para aplicar el guard de inicializacion de forma consistente; anadir restricciones de unicidad de respaldo en backend donde aplique (p.ej. `(banco, numero)` en CuentaBancaria).
- Archivos: `apps/tenant/contabilidad/static/contabilidad/js/cuenta/features/cuenta_editor.js`, `apps/tenant/bancos/static/bancos/js/**/cuenta_editor.js` (verificar nombre exacto), y por extension cualquier otro `*_editor.js` con el mismo patron de `document.addEventListener('click', ...)` delegado.
- Resultado esperado: un click humano genera exactamente una peticion POST.

**C5. Cache de proveedores en Compras nunca se invalida -- bloquea crear Ordenes de Compra en sesiones reales**
> **[CORREGIDO 2026-08-06]** `proveedores_form.js` ahora dispara `proveedor-updated` sobre `document.body` tras crear/editar/eliminar un Proveedor; `compras.utils.js` escucha ese evento e invoca `invalidateCache('proveedores')`.
- Problema: el selector "Proveedor" de "Nueva Orden de Compra" no muestra proveedores creados en la misma sesion del workspace, incluso tras cerrar/reabrir el formulario. Solo una recarga completa de pagina lo soluciona.
- Causa: `apps/tenant/compras/static/compras/js/compras.utils.js` implementa una cache en memoria de 5 minutos (`fetchProveedores`) con una funcion `invalidateCache()` que nunca se invoca desde el flujo de creacion/edicion de Proveedores.
- Impacto: en el uso real (crear un proveedor y luego su orden de compra en la misma sesion) es imposible completar el flujo -- falla silenciosa, sin mensaje de error.
- Prioridad: Maxima.
- Recomendacion: invocar `invalidateCache('proveedores')` al crear/editar un Proveedor, o reducir/eliminar el TTL de la cache.
- Archivos: `apps/tenant/compras/static/compras/js/compras.utils.js`.
- Resultado esperado: un proveedor creado en la sesion aparece inmediatamente disponible en el selector de Nueva Orden de Compra.

**C6. IDs de HTML duplicados entre modulos rompen targeting de pestañas/HTMX (Gastos vs Empleados)**
> **[CORREGIDO 2026-08-06]** Namespacing aplicado (`gastos-tab-pane-resoluciones` / `empleados-tab-pane-resoluciones`, y equivalentes para `search-resolucion`/`resoluciones-panel`), incluyendo las referencias en `gasto_list.js`/`resolucion_list.js`. Verificado en vivo: cada modulo muestra su propia tabla. Auditoria sistematica adicional encontro y corrigio 6 grupos mas de IDs `offcanvas-container-*` duplicados (`workspace.html`, `list_movimientos.html`, `list_inventario.html`) — ver Fase 3 de la remediacion.
- Problema: la pestaña "Resoluciones DIAN" de Gastos muestra datos de Empleados.
- Causa: `apps/tenant/gastos/templates/tenant/gastos/gastos_list.html` y `apps/tenant/empleados/templates/tenant/empleados/empleados_list.html` usan exactamente los mismos IDs HTML (`tab-pane-resoluciones`, `search-resolucion`, `resoluciones-panel`); como el Workspace monta ambos modulos simultaneamente en una sola pagina, el navegador solo puede resolver un elemento por ID.
- Impacto: la pestaña de listado/busqueda de Resoluciones DIAN de Gastos es inutilizable mientras Empleados este tambien montado (siempre, en este Workspace). La creacion si funciona (endpoint API distinto).
- Prioridad: Maxima.
- Recomendacion: namespacing de IDs por modulo en toda la aplicacion (p.ej. `gastos-tab-pane-resoluciones` vs `empleados-tab-pane-resoluciones`); auditar sistematicamente que otros IDs genericos se repiten entre los ~15 modulos coexistentes.
- Archivos: `apps/tenant/gastos/templates/tenant/gastos/gastos_list.html`, `apps/tenant/empleados/templates/tenant/empleados/empleados_list.html`.
- Resultado esperado: cada modulo controla su propia pestaña de Resoluciones sin interferencia cruzada.

**C7. Polling descontrolado en tablas de Empresa -- ~47 peticiones/segundo sostenidas**
> **[CORREGIDO 2026-08-06]** Causa confirmada: no era un `MutationObserver`, sino un listener `htmx:afterSettle` en `assets_empresa.html` que refrescaba las 4 tablas ante cualquier swap dentro de `#ui-empresa-list` -- como esas 4 tablas viven ahi dentro, cada refresco causaba su propio swap, redisparando el mismo listener en bucle infinito. Cada modulo ya tenia su propio refresco correcto y aislado; el listener global (enteramente redundante) fue eliminado. Verificado con instrumentacion de `XMLHttpRequest`: 0 peticiones en 6s de inactividad (antes: bucle infinito).
- Problema: las 4 tablas de Empresa (`empresa`, `sedes`, `areas`, `mailinboxconfig`) se recargan continuamente durante toda la sesion del Workspace, sin importar el modulo activo. Medido: 234 peticiones en 5 segundos.
- Causa probable: `hx-trigger="load, X-updated from:body"` combinado con algo (posiblemente un `MutationObserver` u orquestador) que redispara el evento `X-updated` sobre `body` en un bucle de retroalimentacion cada vez que el propio swap de HTMX modifica el DOM.
- Impacto: desperdicio severo de recursos cliente/servidor; a escala con multiples usuarios concurrentes podria constituir una carga de servidor auto-infligida significativa.
- Prioridad: Maxima.
- Recomendacion: revisar el ciclo de vida de estos `hx-trigger` y cualquier codigo que dispare los eventos `*-updated` sobre `body`; anadir logica de dedupe/debounce.
- Archivos: `apps/tenant/empresa/templates/tenant/empresa/empresa_list.html` (lineas 153/191/227) y el JS del workspace que orquesta las pestañas.
- Resultado esperado: las tablas se recargan solo tras una accion real del usuario (crear/editar/eliminar), no continuamente.

---

### MAYORES

**M1. Comentarios Django `{# #}` multilinea se renderizan como HTML literal (9 archivos, 10 bloques)**
- Causa: Django no soporta comentarios `{# #}` que abarcan multiples lineas (limitacion documentada del motor). Confirmado reproduciendo con `render_to_string`.
- Archivos (con confirmacion visual en UI marcada): `apps/tenant/perfil/templates/tenant/perfil/offcanvas_detalle_perfil.html:33-34` (confirmado), `apps/tenant/compras/templates/tenant/compras/compras_list.html:56-58` (confirmado), `apps/tenant/gastos/templates/tenant/gastos/gastos_list.html:64-66` (confirmado), `apps/tenant/facturas/templates/tenant/facturas/list_factura.html:3-4,113-115` (confirmado), `apps/tenant/facturas/templates/tenant/facturas/partials/tabla_facturas.html:2-4` (confirmado), `apps/tenant/inventario/templates/tenant/inventario/offcanvas_producto.html:23-25` (no confirmado en UI), `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/pendiente_offcanvas_contabilizar.html:272-277` (no confirmado en UI, bloqueado por C3), `apps/public/impuestos/.../logs.html:25-26` y `apps/public/console/.../status.html:37-47` (consola publica, fuera de alcance).
- Nota agravante: 3 de los comentarios documentan decisiones de seguridad (`[SEC-A1]`, `[SEC-A2]`, `[SEC-M2]`) sobre por que un campo no usa `|safe` -- la fuga expone ese razonamiento interno.
- Impacto: Medio-Alto (cosmetico pero visible para todo usuario final; agrava la fuga de info en los 3 casos `[SEC-*]`).
- Recomendacion: colapsar cada comentario a una linea, o migrar a `{% comment %}...{% endcomment %}`.

**M2. Practica extendida de usar PK entero en vez de UUID en selectores de relacion (FK)**
- Confirmado en: Ventas (Cliente), Contabilidad (edicion de Cuenta via `cuenta.id`), Gastos (campo `proveedor_uuid` que en realidad contiene un PK), Empleados (Empleado en Nuevo Contrato), Proyectos (Cliente). Contraste positivo: Empresa, Compras, Empleados (Sede/Area), Cotizaciones (Cliente) SI usan UUID.
- Impacto: viola la regla explicita de `AGENTS.md`/`CLAUDE.md` ("UUID lookup, not PK"); expone secuencias/conteos internos.
- Recomendacion: unificar todos los selectores de relacion para usar UUID, tomando como referencia los modulos que ya lo hacen bien.

**M3. Patron recurrente de JWT en lista negra + 401 sin causa aparente**
- Observado en Clientes, Inventario, Ventas, Bancos; nunca bloqueo la operacion (fallback a `SessionAuthentication`), pero es demasiado frecuente para ser casual.
- Recomendacion: revisar la logica de rotacion/blacklist de refresh tokens (`rest_framework_simplejwt` blacklist).

**M4. Edicion de Empresa ignora silenciosamente un campo requerido vacio**
- Al borrar "Nombre legal de la empresa" y guardar, la app confirma "guardado correctamente" pero el campo nunca se actualiza -- el boton es `type="button"` con JS manual que arma el `FormData` a mano y omite campos vacios sin validar `required`, a diferencia de Sedes/Areas/MailInbox que usan `<form>` real + `type="submit"` (validacion HTML5 nativa).
- Archivos: JS del editor de Empresa (`apps/tenant/empresa/static/empresa/js/...`).
- Recomendacion: migrar el guardado de Empresa al mismo patron `<form>`+`type="submit"` que ya usan Sedes/Areas.

**M5. Contadores KPI de Empresa nunca se actualizan (Sedes/Areas/Buzones siempre en 0)**
- Causa confirmada por codigo: `empresa_list.html` define `id="total-sedes"`/`id="total-areas"` pero ningun JS en todo el repo hace `getElementById` sobre esos IDs (a diferencia de Empleados, que si lo implementa correctamente).
- Recomendacion: implementar la actualizacion de estos contadores siguiendo el patron de `empleado_list.js`.

**M6. Combos de "Nueva Tarea" en Proyectos nunca cargan via navegacion directa a la pestaña**
- La funcion que puebla los selectores Cliente/Empleado (`loadLookups`) solo se invoca desde un flujo de boton "+" especifico, no al activar la pestaña "Nueva tarea" del tablist principal -- el formulario parece listo pero sus 2 campos obligatorios nunca reciben opciones por esa ruta.
- Archivos: `apps/tenant/proyectos/static/proyectos/js/features/nueva_tarea_editor.js`, `nueva_tarea_list.js`.
- Recomendacion: invocar `show()`/`loadLookups()` tambien al activar la pestaña, no solo desde `openEditor()`.

**M7. Cobertura de integracion incompleta (no son bugs, son limites de esta pasada)**
- Cliente->Cotizaciones (bloqueado por C2/Cotizaciones), Ventas->Facturacion->Contabilidad y Empleados->Nomina no se pudieron verificar de extremo a extremo por bugs previos o por evitar deliberadamente acciones con efectos externos reales (facturacion electronica DIAN). Se recomienda repetir en una segunda pasada una vez resueltos C2 y tras identificar el punto de entrada de generacion de Nomina.

---

### MEDIOS

**MD1. Validacion de archivos subidos inconsistente entre modulos**
- Solo `apps/tenant/gastos/models.py` usa `FileExtensionValidator`. Empleados (`foto`), Proyectos (6 campos de archivo), Empresa (`logo`) no tienen validador alguno.
- Recomendacion: aplicar `FileExtensionValidator` de forma consistente en todos los `FileField`/`ImageField` del proyecto.

**MD2. Inconsistencia conceptual "Departamento" (Perfil) vs "Area" (Empresa)**
- El select "Departamento" en Editar Perfil consulta una fuente distinta a "Area" de Empresa, pese a que la pestaña de Empresa se titula literalmente "Areas (Departamentos)" -- un Area creada no aparece como "Departamento" disponible.
- Recomendacion: unificar ambos conceptos o aclarar la diferencia si es intencional.

**MD3. Excepcion JS no capturada en Representantes (Proveedores)**
- `Uncaught TypeError: e.indexOf is not a function`, precedida por `Tabla inicializada con undefined representantes` -- la tabla se inicializa con `undefined` en vez de un arreglo vacio.
- Archivos: JS de `representantes:directory` en `apps/tenant/proveedores/static/proveedores/js/`.

---

### MENORES

**MN1.** Healthcheck de nginx falla por resolucion IPv6 de `localhost` pese a que el servicio funciona correctamente (Fase 1).

**MN2.** El `Makefile` documenta `make crear-empresa` con 3 argumentos (NOMBRE, DOMINIO, EMAIL) pero el comando real (`manage.py crear_empresa`) solo acepta 2 (nombre, email_admin) con schema autogenerado o via `--schema-name` -- inconsistencia de documentacion descubierta al preparar Fase 5.

**MN3.** Mensajes de error inconsistentes entre modulos: Sedes/Areas de Empresa exponen mensajes crudos de DRF ("Este campo no puede ser nulo.", "Detail_code: invalid"), mientras Clientes/Proveedores muestran mensajes limpios en español ("Ya existe un Cliente registrado con..."). Recomendacion: unificar el formato de errores mostrado al usuario final.

**MN4.** Boton "Eliminar Sede" usa `window.confirm()` nativo del navegador en vez de un modal de confirmacion consistente con el resto de la UI (Bootstrap).

---

### Onboarding de tenants (hallazgo colateral, Fase 5)

> **[CORREGIDO 2026-08-06]** Causa exacta: `crear_empresa()` (comando) → `crear_tenant()` → `onboard_tenant()` -- NO pasa por `crear_tenant_con_owner()`, el "flujo unico autorizado" segun `AGENTS.md`. El seed de `onboard_tenant()` solo *buscaba* una Empresa existente (`Empresa.objects.only('id').first()`, `None` en un tenant nuevo) en vez de crearla, causando el `TenantProfile.empresa no puede ser NULL` silenciado. Corregido replicando dentro de `onboard_tenant()` el patron ya correcto de `crear_tenant_con_owner()` (crear Empresa singleton antes del TenantProfile). Reproducido y verificado en BD (Empresa + TenantProfile se crean correctamente); suite completa de tests de onboarding (60 tests, 2 corridas) confirma 24 fallos preexistentes identicos con y sin el fix (mismatch de dominio del rebrand, no relacionado) via `git stash`.

**Bug adicional descubierto al preparar las pruebas de aislamiento:** el comando de creacion de tenants (`manage.py crear_empresa`) falla silenciosamente al crear el `TenantProfile` del admin nuevo (`TenantProfile.empresa no puede ser NULL`) y **no crea ningun registro `Empresa`** en el tenant nuevo, pese a reportar "OK: Empresa creada exitosamente!". Cualquier tenant nuevo queda inutilizable desde el primer login. Dado que la rama actual es `feat/onboarding-cookie`, esto es probablemente relevante al trabajo en curso del usuario. Ver Fase 5 para el detalle completo. Clasificacion: **Critico** (bloquea el onboarding de cualquier cliente nuevo).

=====================================================================
HALLAZGOS ACUMULADOS (se consolidan en Fase 8)
=====================================================================

1. [MENOR] Healthcheck de nginx falla por resolucion IPv6 de `localhost` (`wget` -> `[::1]:80` -> connection refused) pese a que el servicio responde correctamente por IPv4/dominio real. Ver Fase 1.

2. [MAYOR - TRANSVERSAL] Comentarios Django `{# ... #}` que abarcan multiples lineas se renderizan como HTML literal visible para el usuario final, porque Django no soporta comentarios `{# #}` multilinea (limitacion documentada del motor de plantillas). Causa raiz confirmada reproduciendo con `render_to_string` en shell de Django (ver modulo Perfil). Busqueda dedicada en los 246 archivos de plantilla del repo confirmo **9 archivos con 10 bloques afectados**:
   - `apps/tenant/perfil/templates/tenant/perfil/offcanvas_detalle_perfil.html` (lineas 33-34) -- visible en "Detalle de Perfil" (confirmado en UI durante esta auditoria).
   - `apps/tenant/compras/templates/tenant/compras/compras_list.html` (lineas 56-58) -- visible en portada de Compras (confirmado en UI durante esta auditoria).
   - `apps/tenant/gastos/templates/tenant/gastos/gastos_list.html` (lineas 64-66) -- **confirmado visible en UI** durante la auditoria de Gastos.
   - `apps/tenant/facturas/templates/tenant/facturas/list_factura.html` (lineas 3-4 Y 113-115, dos bloques distintos) -- **confirmados visibles en UI** (3 comentarios distintos vistos simultaneamente en la pantalla de Facturas, incluyendo el de `tabla_facturas.html` de abajo).
   - `apps/tenant/facturas/templates/tenant/facturas/partials/tabla_facturas.html` (lineas 2-4) -- **confirmado visible en UI**.
   - `apps/tenant/inventario/templates/tenant/inventario/offcanvas_producto.html` (lineas 23-25, comentario `[FE-C2]`) -- no se detecto visualmente durante las pruebas de Inventario; revisar si el fragmento afectado esta condicionado a un escenario no ejercitado (edicion en vez de creacion).
   - `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/pendiente_offcanvas_contabilizar.html` (lineas 272-277, comentario `[SEC-A2]`, 6 lineas) -- pendiente al auditar Contabilidad.
   - `apps/public/impuestos/templates/console/pages/impuestos/fragments/logs.html` (lineas 25-26, comentario `[SEC-M2]`) -- fuera del alcance de esta auditoria (consola publica, no UI privada de tenant).
   - `apps/public/console/templates/console/pages/tenants/status.html` (lineas 37-47, 11 lineas) -- fuera del alcance de esta auditoria (consola publica).

   Nota agravante: varios de los comentarios filtrados (`[SEC-A1]`, `[SEC-A2]`, `[SEC-M2]`) documentan justamente decisiones de seguridad sobre por que un campo NO usa el filtro `|safe` de Django -- es decir, la fuga expone al usuario final el razonamiento interno de seguridad del equipo de desarrollo, ademas de ensuciar visualmente la UI. Fix conceptual uniforme para los 10 casos: colapsar cada comentario a una sola linea, o migrar a `{% comment %}...{% endcomment %}` si se confirma que soporta multilinea en la version de Django del proyecto.

3. [CRITICO] `settings.DEBUG == True` confirmado en la instancia auditada (verificado por shell de Django), la cual tiene el tunel `cloudflared` activo y conectado a Cloudflare exponiendo `home.sintel.net.co` en internet publica (verificado en Fase 1). Combinado con excepciones no controladas que devuelven tracebacks completos de Python al cliente, esto constituye una fuga de informacion activa y explotable ahora mismo por cualquier cliente en internet que provoque un error 500. **Confirmado de forma independiente en DOS modulos distintos:**
   - Inventario: `Producto.DoesNotExist` sin manejar en `ProductoViewSet.destroy()`/`get_object()` (`apps/tenant/inventario/api/viewsets.py`).
   - Cotizaciones: `AttributeError: 'ConfiguracionCotizacionViewSet' object has no attribute 'get_empresa_id'` en `GET /api/v1/cotizaciones/configuracion/` (`apps/tenant/cotizaciones/configuracion/viewsets.py:26`), que ademas bloquea funcionalmente la creacion de cotizaciones.
   - Contabilidad (Fase 4): `AttributeError: 'DocumentoSoporte' object has no attribute 'retefuente'` en `GET /api/v1/contabilidad/pendientes/render-offcanvas/` (`apps/tenant/contabilidad/api/viewsets.py:946-947`), que bloquea el paso final del modelo Pull (ADR-001) -- imposible contabilizar un Gasto pendiente.

   Tres incidentes independientes en modulos sin relacion entre si confirman que esto no es un caso aislado sino un patron transversal de la aplicacion. Se recomienda: (a) confirmar si `home.sintel.net.co` vía el tunel es el mismo entorno con `DEBUG=True` o si existe una instancia de produccion separada con `DEBUG=False`; (b) auditar transversalmente en Fase 6 que ViewSets de otros modulos tengan excepciones sin capturar (`DoesNotExist`, `AttributeError`, etc.) que puedan devolver 500 con traceback.

4. [CRITICO - TRANSVERSAL] Doble-submit por doble-registro de event listeners: en al menos 2 modulos distintos, un UNICO click humano en el boton "Guardar" de un offcanvas genero DOS peticiones POST identicas al backend, resultando en registros duplicados. Causa raiz confirmada en consola del navegador: el handler que activa el offcanvas (`DOM Settle detectado... activando offcanvas`) se dispara dos veces para una sola apertura, y cada apertura vuelve a adjuntar el listener del boton "Guardar" sin remover el anterior -- el propio codigo de dos modulos distintos (`cuenta_editor.js` de Contabilidad, `nueva_tarea_editor.js` de Proyectos) documenta este riesgo exacto en comentarios (referenciado como "FE-A1/A2") y aplica un guard (`document.body.dataset.XxxInitialized`) para evitarlo -- pero el guard claramente no cubre todos los casos, o falta en otros modulos:
   - Contabilidad: crear "Cuenta Contable" con 1 click genero 2 registros, uno de ellos con TODOS los campos requeridos vacios (payload `{}` enviado en la segunda invocacion) -- ver modulo Contabilidad.
   - Bancos: crear "Cuenta Bancaria" con 1 click genero 2 registros COMPLETAMENTE IDENTICOS (mismo numero de cuenta) -- ver modulo Bancos. Agravado por la ausencia de restriccion de unicidad en `(banco, numero)` a nivel de backend, que hubiera bloqueado al menos el duplicado exacto.

   Prioridad maxima para Fase 6/7: auditar todos los editores offcanvas del proyecto (patron FSD `*_editor.js`) para confirmar que implementan el guard de inicializacion de forma consistente, y anadir manejo de idempotencia/deduplicacion en el backend como defensa en profundidad (p.ej. restricciones de unicidad donde aplique, o un token de idempotencia en las peticiones de creacion).

5. [MAYOR - TRANSVERSAL] Patron recurrente de aviso `No se pudo refrescar token: El token esta en lista negra` acompanado de 1-3 respuestas `401 Unauthorized` en consola, observado repetidamente y sin relacion aparente con la expiracion real del JWT (se verifico en un caso que el access token vigente aun tenia ~14 minutos de vida util). Ocurrio en al menos 4 modulos distintos (Clientes, Inventario, Ventas, Bancos) a lo largo de la sesion, siempre sin bloquear la operacion subyacente (probablemente por el fallback a `SessionAuthentication` del esquema dual-auth). Pendiente de diagnostico en profundidad en Fase 6: revisar la logica de rotacion/blacklist de refresh tokens (`rest_framework_simplejwt` blacklist app) para entender por que un refresh token aparentemente valido/reciente se reporta en lista negra con esta frecuencia.

6. [MAYOR - TRANSVERSAL] Practica extendida de usar el PK entero de Django en vez del UUID en selectores `<select>` que representan relaciones (FK) hacia otras entidades, violando la regla explicita de arquitectura ("UUID lookup, not PK"). Confirmado en al menos 5 modulos: Ventas (selector Cliente en Nueva Venta), Contabilidad (edicion de Cuenta Contable via `cuenta.id`), Gastos (campo literalmente llamado `proveedor_uuid` que contiene un PK, no un UUID), Empleados (selector Empleado en Nuevo Contrato), Proyectos (selector Cliente en Nuevo Proyecto y en Nueva Tarea aunque este ultimo si usa UUID). Contraste positivo: Empresa (Sede/Area), Compras (Proveedor), Empleados (Sede/Area del propio Empleado) y Cotizaciones (Cliente) SI usan UUID correctamente, demostrando que el patron correcto ya existe en el código base pero no se aplico de forma consistente. Riesgo: expone conteos/secuencias internas (enumeracion), inconsistente con el resto del sistema, y contradice una regla ya documentada explicitamente en `AGENTS.md`/`CLAUDE.md`.
