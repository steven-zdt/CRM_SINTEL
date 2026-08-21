# UX_MASTER_BASELINE — Transformacion UX/UI de SINTEL

Mision: transformar progresivamente la interfaz y experiencia de
usuario del ERP, presentando las 16 apps independientes como un unico
sistema empresarial coherente -- sin alterar la arquitectura tecnica
(Service Layer, DSV, OCF, multitenant) ni las reglas de negocio.

**Fecha:** 2026-08-21. **Rama:** `feat/onboarding-cookie`.

---

## FASE 0 — Baseline frontend

### Stack tecnico confirmado

- **Sin build step.** Bootstrap 5.3.2 (CDN), Bootstrap Icons 1.11.1
  (CDN), Font Awesome 6.4.0 (CDN), HTMX 1.9.10, Tabulator 6.2.5
  (legacy, en migracion a django-tables2+HTMX segun
  `PLAN_UNICO_CORRECCIONES.md` FASE 5-BIS), Notyf (notificaciones
  toast).
- **JS:** modulos vanilla ES6 namespaced bajo `window.Sintel.*`, sin
  framework SPA. `apps/tenant/core/static/core/js/workspace.js` es el
  orquestador del shell (tabs, nav, logout).
- **Layout actual:** `workspace.html` (342 lineas) es un SPA-like
  shell -- las 16 apps se inyectan como `<section id="tab-X"
  style="display:none">` dentro de una sola pagina, alternadas por
  JS via `data-tab`/hash de URL (`#empresa`, `#facturas`, etc.), no
  hay navegacion real de pagina (sin recarga completa al cambiar de
  app).
- **CSS:** `workspace.css` con custom properties (`--brand`, `--muted`,
  `--border`, etc.) ya establecidas -- sistema de color coherente
  reutilizable, no hace falta crear uno nuevo.

### Componentes UI compartidos YA EXISTENTES (reutilizar, no duplicar)

`apps/tenant/core/templates/tenant/core/partials/ui/`:
- `empty_state.html` -- estado vacio estandar
- `filter_bar.html` -- barra de filtros estandar
- `kpi_card.html` -- tarjeta de KPI estandar
- `loading_state.html` -- estado de carga estandar

Mas `_base_offcanvas.html` (offcanvas base) y
`window.Sintel.Core.mostrarOffcanvasSeguro()` (helper JS obligatorio
para abrir offcanvas, ver `AGENTS.md` §26). Estos ya son el resultado
de un trabajo previo de "Shared UI / Design System" (FASE 33 de la
mision anterior, ver `arquitectura_general.md` DOC-M25 en adelante).

### Contexto organizacional -- YA existe un selector parcial

El navbar superior YA tiene un boton "Cambiar de sede" con menu
desplegable (confirmado renderizado: "Sede Principal QA" / "centro"
como opciones), y un menu de cuenta mostrando el email del usuario
(`admin@home.com`) con acceso a "Perfil" y "Cerrar sesion". Esto
cubre parcialmente la FASE 4 de la mision (contexto visual
Empresa/Sede/Area/Usuario) -- falta mostrar Empresa y Area de forma
explicita junto a Sede, pero el patron de selector desplegable ya
esta establecido y debe reutilizarse, no reinventarse.

### Navegacion -- ANTES de esta pasada

`<ul id="nav">` era una lista plana de 15 items (14 apps + Mi Perfil)
sin agrupacion conceptual, en el orden en que historicamente se fue
agregando cada modulo (Dashboard, Empresa, Proyectos, Facturas,
Contabilidad, Inventario, Clientes, Ventas, Proveedores, Compras,
Empleados, Cotizaciones, Gastos, Bancos, [separador], Mi Perfil) --
sin relacion con el flujo de negocio real ni con categorias que un
usuario nuevo pueda reconocer.

### Hallazgo real encontrado durante el baseline: resaltado de item activo roto

`workspace.js` alternaba la clase CSS `.active` en el link de
navegacion clickeado (`classList.add('active')`/`remove('active')`),
pero `workspace.css` **nunca definio ninguna regla para `.active`**
-- solo estiliza `[aria-current="page"]`. Resultado: el usuario nunca
veia resaltado visualmente en que seccion estaba parado dentro del
sidebar, viola directamente el principio UX central de la mision
("¿Donde estoy?"). Corregido en esta misma pasada (ver FASE 3).

### `.agent/` docs de cada app (fuente de negocio real)

Cada app tiene su propio `.agent/AUDITORIA_FLUJO_*.md` -- ya usados
extensivamente en las 2 misiones de auditoria de codigo previas de
esta sesion. Son la fuente primaria de "que hace cada app" para el
mapa de experiencia (FASE 1), evitando re-descubrir reglas de negocio
ya documentadas.

### Registro / Home publico (`home.sintel.net.co` en este entorno de desarrollo)

Confirmado: en este entorno de desarrollo local, `home.sintel.net.co`
es literalmente el dominio de un TENANT real (schema `home`), no solo
el dominio publico generico -- resuelto via `/etc/hosts` local. El
flujo real de entrada:
1. `apps/public/core.PublicIndexView` (`public/core/index.html`) --
   landing page de marketing en el dominio raiz `sintel.net.co`.
2. Registro/activacion via `apps.public.tenants` (OTT, One-Time
   Token) -- consumido en `apps/tenant/core/api/viewsets.py`.
3. Tras activacion, el usuario entra directo al `workspace.html` de
   su tenant -- **no existe hoy ninguna pantalla de onboarding
   guiado con checklist de progreso** (el ejemplo de la mision
   "✅ Cuenta 🟡 Empresa ⚪ Equipo..." es una funcionalidad nueva a
   construir, no algo que ya exista y haya que mejorar).

**Hallazgo secundario (no corregido en esta pasada, informativo):**
`config/urls_public.py` registra `path('', PublicIndexView...)` en la
linea 70 Y `include('apps.public.tenants.urls')` en la linea 98
(que a su vez define su propio `path("", LandingPageView...)`) --
dado que Django resuelve el primer patron que matchea, la
`LandingPageView` de `apps.public.tenants` para la ruta raiz nunca es
alcanzable (queda shadowed). Los sub-paths (`/select/`, `/activate/`)
de ese mismo modulo SI funcionan. Candidato a limpieza en una fase
posterior de FASE 12 (codigo muerto de rutas) -- no se toca aqui por
no ser parte del alcance actual (nav restructuring).

---

## FASE 3 — Navegacion empresarial (IMPLEMENTADO en esta pasada)

Se reagrupo `<ul id="nav">` en 5 secciones conceptuales, siguiendo el
ejemplo literal de la mision, adaptado a los 15 items reales del
sistema:

| Grupo | Items |
|---|---|
| 🏠 Inicio | Dashboard |
| 🚀 Configuración | Mi perfil, Mi empresa, Equipo (Empleados) |
| 🤝 Relaciones | Clientes, Proveedores |
| 📦 Operación | Inventario, Cotizaciones, Proyectos, Gastos, Compras, Ventas |
| 💳 Finanzas | Facturas, Bancos, Contabilidad |

**Archivos tocados:**
- `apps/tenant/core/templates/tenant/core/workspace.html` --
  reestructuracion del `<ul id="nav">`. **Ningun `data-tab`/`href` se
  modifico** -- mismos 15 items, mismo `data-tab` exacto en cada uno,
  solo se agregaron 5 `<li class="nav-section-header">` como
  separadores visuales y se reordenaron los items dentro de sus
  nuevos grupos. Cero riesgo de romper el JS existente (que busca
  `#nav a[data-tab]` como descendiente, sin importar el anidamiento).
- `apps/tenant/core/static/tenant/core/css/workspace.css` -- agregada
  la regla `.nav-section-header` (11px, mayusculas, color
  `var(--muted)`, mismo lenguaje visual que `.brand h2` ya
  establecido) -- 2 reglas nuevas, ~14 lineas.
- `apps/tenant/core/static/core/js/workspace.js` -- **corregido el
  bug de resaltado de item activo**: las 3 llamadas a
  `classList.add/remove('active')` se cambiaron a
  `setAttribute('aria-current','page')`/`removeAttribute('aria-current')`,
  reutilizando la regla CSS `[aria-current="page"]` que YA existia
  pero nunca se activaba. Mejora de accesibilidad (semantica ARIA
  correcta) Y de UX (el resaltado ahora si funciona) en el mismo
  cambio, sin agregar CSS nuevo.

### Verificacion realizada

- **`manage.py shell`:** el template `tenant/core/workspace.html`
  parsea sin `TemplateSyntaxError`.
- **`django.test.Client(SERVER_NAME='home.sintel.net.co')` +
  `force_login()`** (tecnica estandar de Django, sin conocer ni
  ingresar ninguna contraseña real) sobre un usuario staff existente
  del tenant `home`: `GET /workspace/` responde `200`, y el HTML
  renderizado contiene exactamente la estructura de navegacion
  agrupada esperada, con los 15 `data-tab`/`href` intactos.
- **Contenido de `workspace.css` servido** (verificado 2 veces, antes
  y despues de `collectstatic` + reinicio del contenedor `web`):
  contiene la regla `.nav-section-header` con los valores correctos.
- **Verificacion visual en el Browser pane de esta sesion: NO
  concluyente.** La consola del navegador muestra
  `net::ERR_BLOCKED_BY_CLIENT` en las peticiones a los recursos
  estaticos de `home.sintel.net.co:8000` -- el propio sandbox del
  navegador de esta herramienta bloquea esas peticiones (comportamiento
  tipo ad-blocker), y esto se confirmo que **afecta a TODO
  `workspace.css`, incluyendo reglas preexistentes nunca tocadas**
  (`.brand h2`, `.ws-shell{display:grid}` tampoco se aplican en este
  navegador sandboxeado) -- no es un efecto de este cambio especifico.
  **Se recomienda verificacion visual manual en un navegador real**
  (Chrome/Edge normal del usuario) antes de considerar este cambio
  desplegado con confianza visual completa -- la evidencia estatica
  (contenido servido correcto, HTML renderizado correcto, JS sin
  errores de sintaxis en ejecucion) es solida, pero no reemplaza un
  vistazo visual humano.

---

## Estado de la mision UX

Esta es la PRIMERA pasada de una mision de transformacion de gran
escala (37 fases segun el prompt original, cubriendo Home/Onboarding,
las 16 apps, sistema visual, iconografia, formularios, tablas,
responsive, accesibilidad). Dado el alcance y que este es un cambio
**visible en produccion** (a diferencia de las 2 misiones de auditoria
de codigo backend anteriores en esta sesion, que eran solo eliminacion
de codigo muerto sin riesgo visual), se entrega este primer incremento
concreto y verificable (navegacion agrupada + fix de resaltado activo)
y se documenta el hallazgo real (ruta shadowed en `urls_public.py`,
ausencia de onboarding guiado) antes de continuar con mas fases, para
que el usuario pueda revisar el resultado visualmente.

**Siguiente paso propuesto (no ejecutado aun):** FASE 2 (Home/
Onboarding) -- construir la pantalla de progreso de configuracion
inicial descrita en la mision (checklist Cuenta/Empresa/Equipo/
Clientes/Proveedores/Inventario), que hoy no existe.
