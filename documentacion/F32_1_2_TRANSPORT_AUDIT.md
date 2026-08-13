# F32.1 + F32.2 — Auditoría del transporte HTTP/CSRF/JWT (congelar comportamiento actual)

**Fecha:** 2026-08-13 · Rama `feat/onboarding-cookie`.
**Alcance:** solo lectura. **0 archivos de código modificados.** Este
documento es la entrada de F32.3 (diseño del contrato `Core.Http`) y no
autoriza ningún cambio por sí mismo — exactamente el mismo criterio que
F31.0 aplicó al inventario de grillas.

---

## 1. Las 5 implementaciones reales (no 3)

La investigación previa (F31.1/F31.2) identificó "2 copias de `http.js` +
una tercera versión divergente". Esta auditoría, con lectura línea por
línea de cada archivo y su contexto de carga real, encuentra **5
implementaciones de transporte HTTP independientes**:

| # | Archivo | Contenido | Rol real |
|---|---|---|---|
| A | `apps/tenant/core/static/core/js/lib/http.js` | Único, verboso (logging extenso, coerción de `body.cliente`) | **Gana en producción** para todo `workspace.html` (ver §2) |
| B | `apps/tenant/core/static/js/http.js` | "v3.4 unificado" | Se carga primero en `tenant/base.html`, pero es sobreescrito por A |
| C | `apps/public/console/static/js/http.js` | **Byte-idéntico a B** | Misma versión "v3.4", duplicada en el árbol público |
| D | `apps/public/console/static/js/jwt-auth.js` | Único, completo (login/refresh/verify/getValidAccessToken) | SSoT real de JWT, cargado en ambos árboles vía ruta app-agnostic `js/jwt-auth.js` |
| E | `apps/tenant/core/static/tenant/core/auth/login.html` (inline `<script>`) | **Fetch crudo propio, sin usar A/B/C/D en absoluto** | Login real de tenant — **hallazgo nuevo, no documentado en F31** |

**E es el hallazgo más importante de esta fase.** La página de login
(`login.html`, HTML estático servido directo, no template Django) tiene
su propio cliente HTTP inline completo: `loadTenantInfo()` y `login()`
usan `fetch()` crudo con manejo de CSRF/JSON propio, sin cargar ni A, B,
C ni D. El login — el flujo más crítico de todo el sistema — no pasa por
ningún SSoT de transporte. Verificado interactuando con el login real en
un navegador (Browser pane): `POST /api/v1/core/auth/login/` y
`GET /api/v1/core/landing/info/` fallan con `net::ERR_BLOCKED_BY_CLIENT`
al intentarse desde las herramientas de navegador con IA de este entorno
(bloqueo de la propia plataforma sobre envío de credenciales via
automatización interactiva, no un bug de este código) — confirma que
`login.html` sí ejecuta sus propios `fetch()`, visibles en Network.

## 2. Orden de carga real -- confirmado, no inferido

`apps/tenant/core/templates/tenant/base.html` (líneas 125-134):
```
125  <script src="{% static 'js/jwt-auth.js' %}"></script>          <!-- D -->
129  <script src="{% static 'js/http.js' %}"></script>              <!-- B -->
132  {% block page_assets_body %}{% endblock page_assets_body %}
134  {% block extra_js %}{% endblock %}
```
`workspace.html` (que extiende `base.html`) rellena esos bloques con,
entre otros includes, `assets_core.html`:
```
9    <script src="{% static 'core/js/lib/http.js' %}"></script>     <!-- A -->
```
Como los bloques del hijo renderizan **después** del contenido fijo del
padre, **A se carga después de B y sobreescribe `window.http`**. B (la
versión "v3.4 unificado", la que suena a SSoT por su nombre y docstring)
**nunca es la que realmente ejecuta** en ninguna página de workspace
tenant. Esto ya estaba correctamente inferido en F31.1; esta auditoría lo
confirma leyendo el bloque exacto, no solo el comentario de A.

`apps/public/console/templates/console/base.html` (líneas 66-68) carga
D y C (no A) — la consola pública sí usa la versión "v3.4" como SSoT
real, porque no incluye `assets_core.html`. **Dos aplicaciones del mismo
código fuente (`http.js`), dos ganadores distintos**, dependiendo de qué
árbol de templates se está sirviendo.

## 3. Diferencia funcional crítica A vs B/C: uploads

Esta es la razón concreta -- no solo el riesgo abstracto -- por la que
F31 hizo bien en diferir esta consolidación:

- **A (`lib/http.js`)** maneja `FormData` explícitamente: elimina
  `Content-Type` para que el navegador agregue el boundary correcto,
  agrega `csrfmiddlewaretoken` al propio `FormData`, y tiene logging
  detallado por archivo.
- **B/C ("v3.4")** `httpFn()` hace `JSON.stringify(payload)`
  incondicionalmente para cualquier body no-GET. **Si `payload` es un
  `FormData`, `JSON.stringify()` lo serializa a `"{}"`** -- el archivo se
  pierde silenciosamente, sin error visible hasta que el backend rechace
  el campo requerido.

**31 archivos** en `apps/tenant/*/static/` usan `FormData` (grep
`FormData` sobre `apps/tenant/*/static/`), cubriendo al menos: bancos,
clientes, contabilidad (3 editores), cotizaciones (3), empleados (3),
empresa (2), facturas (2), gastos, inventario (5), perfil, proyectos.
**Promover B/C a "el" cliente sin antes portar el manejo de FormData de A
rompería uploads en al menos 11 apps.** Esto no es una hipótesis --  es
lectura directa del código de ambas versiones.

## 4. Dependencia oculta no documentada: `window.getCookie`

`lib/http.js` (A) tiene un side-effect adicional a `window.http`:
```js
window.getCookie = getCookie;
```
**3 de los 6 `*.api.js` que ya violan el contrato "solo URLs+métodos"
(F31.3) dependen de este export global sin saberlo**, en vez de leer la
cookie ellos mismos:

| Archivo | Cómo lee CSRF |
|---|---|
| `gastos.api.js` | `window.getCookie?.('csrftoken')` -- depende de A |
| `compras.api.js` | `window.getCookie?.('csrftoken')` -- depende de A |
| `ventas.api.js` | `w.getCookie ? w.getCookie('csrftoken') : null` -- depende de A |
| `empleados.api.js` | lee `[name=csrfmiddlewaretoken]` DOM o `document.cookie` directo -- propio |
| `cotizaciones.api.js` | regex sobre `document.cookie` -- propio |
| `dashboard.api.js` | `[name=csrfmiddlewaretoken]` DOM -- propio |

**Si A se elimina sin exportar `getCookie` desde el reemplazo, `gastos`,
`compras` y `ventas` pierden el CSRF token silenciosamente -- cada
escritura (POST/PATCH/DELETE) empezaría a fallar con 403.** B/C no
exportan `getCookie`. Este es exactamente el tipo de acoplamiento oculto
que un `grep` superficial de "quién importa http.js" no revela -- solo
aparece leyendo cada consumidor.

## 5. JWT: refresh vs no-refresh, inconsistente entre apps

`jwtAuth` (D) expone dos métodos: `getAccessToken()` (lectura directa de
`localStorage`, sin verificar expiración) y `getValidAccessToken()`
(verifica, refresca si hace falta, o lo obtiene desde sesión). Solo
`compras.api.js` usa el segundo (con fallback al primero si
`getValidAccessToken` no existiera). **Los otros 5 (`gastos`,
`empleados`, `cotizaciones`, `dashboard`, `ventas`) usan únicamente
`getAccessToken()` -- nunca refrescan.** Si el access token expira a
mitad de sesión, estas 5 apps envían un Bearer inválido; el resultado
depende de si `SessionAuthentication` cubre el fallback en
`BaseTenantViewSet` (Dual-Auth) o si `JWTAuthentication` corta la cadena
antes -- **no verificado en este pase, requiere prueba de navegador real
(F32.5)**, no inspección de código.

## 6. Confirmación del patrón JWT prohibido -- sigue en 0

Repetido de F31.3 con el mismo resultado: `grep -rn "jwtAuth\.token"
apps/` → **0 ocurrencias**. Todos los consumidores usan
`jwtAuth.getAccessToken()`/`getValidAccessToken()` (método), nunca
`jwtAuth.token` (propiedad inexistente). F32.4 no requiere ningún cambio
de código -- solo centralizar el *consumo* (que ya usa el método
correcto), no "arreglar" el patrón en sí.

## 7. Matriz de transporte (F32.2)

| Consumidor | Transporte | CSRF | JWT | Upload | Error handling | Destino recomendado |
|---|---|---|---|---|---|---|
| `gastos.api.js` | `fetch()` propio | `window.getCookie` (⚠️ dep. oculta de A) | `getAccessToken` (sin refresh) | no | propio | `Core.Http` |
| `compras.api.js` | `fetch()` propio | `window.getCookie` (⚠️ dep. oculta de A) | `getValidAccessToken` (con refresh) | no | propio | `Core.Http` |
| `empleados.api.js` | `fetch()` propio | DOM/cookie propio | `getAccessToken` (sin refresh) | no | propio | `Core.Http` |
| `cotizaciones.api.js` | `fetch()` propio | cookie regex propio | `getAccessToken` (sin refresh) | no | propio | `Core.Http` |
| `dashboard.api.js` | `fetch()` propio | DOM propio | `getAccessToken` (sin refresh) | no | propio | `Core.Http` |
| `ventas.api.js` | `fetch()` propio | `window.getCookie` (⚠️ dep. oculta de A) | `getAccessToken` (sin refresh) | no | propio | `Core.Http` |
| Resto (11 apps) | `window.http(...)` → A | A (cookie) | A (`getValidAccessToken`) | sí (11 apps con `FormData`) | A (401 no-crítico + redirect crítico) | ya en SSoT (A) |
| `login.html` (inline) | `fetch()` crudo propio | cookie propio | N/A (pre-login) | no | propio | **fuera de alcance de `Core.Http`** -- ver §8 |
| Consola pública | `window.http(...)` → B/C | meta-tag | D | no verificado en consola | propio (lanza `Error`) | ya en SSoT (B/C) para su árbol |

**Nota sobre `contabilidad` (8 `*.api.js`):** no auditados en detalle en
este pase -- F31.1 ya aceptó el patrón "1 api.js por sub-dominio" como
variante válida para esa app; su transporte subyacente no difiere del
resto (usan `window.http`), así que no son parte de los "6 violadores"
identificados en F31.3.

## 8. `login.html` -- decisión explícita, no un 7º archivo a migrar todavía

`login.html` es HTML estático (no template Django, sin `{% static %}`
para su propio script inline) servido antes de que exista sesión o
token -- estructuralmente **no puede** depender de `Core.Http` de la
misma forma que el resto (no hay CSRF de sesión previa en muchos casos,
no hay JWT). Se documenta como hallazgo, **no se migra en F32** salvo
que F32.5 (pruebas de navegador reales) revele un bug concreto en su
flujo -- mismo criterio de "no tocar sin poder verificar" que rigió toda
F31.

## 9. Uso de HTMX vs Session vs fetch directo (barrido rápido)

- **HTMX**: `ajax-setup-csrf.js` (confirmado no-muerto en F31.1) inyecta
  `X-CSRFToken` en todo request HTMX vía `htmx:configRequest` -- **no
  depende de ninguna de las 5 implementaciones anteriores**, es
  independiente y ya funciona correctamente para todos los paneles
  HTMX-only (la mayoría de los `*_list.js` migrados en F31.6/Grupo 2).
- **Session**: todas las 5 implementaciones envían cookies de sesión
  (`credentials: "same-origin"` en A/D-login, `"include"` en B/C) --
  Session sigue siendo el fallback universal vía `BaseTenantViewSet`
  Dual-Auth.
- **fetch directo sin CSRF/JWT**: no encontrado fuera de las 5
  implementaciones ya catalogadas (verificado con grep de `fetch(` en
  `apps/tenant/*/static/` cruzado contra los archivos ya listados -- los
  resultados adicionales son todos consumidores de alguna de los A-E, no
  clientes nuevos).

## 10. Qué NO se tocó en este pase

Ningún archivo de código fue modificado. `http.js` (A, B, C),
`jwt-auth.js` (D) y `login.html` (E) siguen exactamente como estaban.
Los 6 `*.api.js` violadores siguen sin cambios. Esta es la base de
evidencia para F32.3 (diseño del contrato `Core.Http`) y F32.5
(validación de navegador antes de tocar nada de esto).
