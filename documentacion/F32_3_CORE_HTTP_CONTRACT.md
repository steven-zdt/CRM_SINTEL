# F32.3 — Contrato único `window.Sintel.Core.Http`

**Fecha:** 2026-08-13 · Diseño únicamente -- **0 código nuevo en este
documento**. Construido directamente sobre la evidencia de
`F32_1_2_TRANSPORT_AUDIT.md`, no sobre una reconstrucción teórica.

---

## 1. Objetivo

Una sola implementación que reemplace A (`lib/http.js`) y B/C (`http.js`
"v3.4") sin perder ninguna de las capacidades reales que hoy están
repartidas entre ambas -- en particular las que B/C **no tiene** y que
harían perder funcionalidad real si se promoviera tal cual (uploads,
redirect en 401 crítico, `getCookie` público).

## 2. Superficie del contrato

```
window.Sintel.Core.Http = {
  request(method, url, body, opts?)   // primitiva base
  get(url, params?)
  post(url, body?)
  put(url, body?)
  patch(url, body?)
  delete(url)
  upload(url, formData)               // explícito, no inferido por tipo de body
  csrf()                               // reemplaza window.getCookie('csrftoken')
  normalizeError(response, data)       // un solo formato de error en todo el frontend
}
```

**Decisión de diseño clave, tomada por la evidencia, no por preferencia
estética:** `upload()` es un método **separado**, no una detección
automática de `body instanceof FormData` dentro de `post()`. La versión
B/C ya demostró el riesgo de la detección implícita silenciosa
(`JSON.stringify()` de un `FormData` produce `"{}"` sin error) -- un
método explícito hace que un consumidor que necesita subir un archivo no
pueda "olvidarlo" ni el linter/type-check (si algún día se adopta)
pueda dejarlo pasar en silencio.

## 3. Comportamiento por responsabilidad

### CSRF (`csrf()`)
Cookie-based (`csrftoken`), no meta-tag. Motivo: **es lo que el 100% del
tráfico real usa hoy** (A gana en tenant, y el meta-tag de B/C no está
presente en la mayoría de las plantillas tenant -- adoptar meta-tag
significaría CSRF vacío en todos esos casos hasta agregar el tag en cada
template). `csrf()` se expone también como `window.getCookie` (alias,
marcado `@deprecated`) durante una ventana de transición, porque 3
`*.api.js` (`gastos`, `compras`, `ventas`) dependen de ese global hoy
(§4 del audit) -- eliminarlo de golpe sin antes migrar esos 3 archivos
rompe CSRF ahí silenciosamente. El alias se retira solo después de que
F32.6 confirme que los 3 ya llaman a `Core.Http` directamente.

### JWT
Siempre `jwtAuth.getValidAccessToken()` (con refresh), nunca
`getAccessToken()` a secas -- corrige la inconsistencia real encontrada
en §5 del audit (5 de 6 `*.api.js` no refrescaban). `jwtAuth` (D) no se
toca; `Core.Http` solo cambia *cómo lo consume*, tal como F32.4 ya
establece que no hace falta "arreglar" JWT, solo centralizarlo.

### Uploads (`upload()`)
Porta exactamente el comportamiento ya probado de A: sin `Content-Type`
explícito (el navegador arma el boundary), `csrfmiddlewaretoken`
agregado al propio `FormData` además del header `X-CSRFToken` (algunos
endpoints Django tradicionales lo esperan en el body, no solo el header
-- comportamiento ya presente en A, se preserva tal cual sin
re-justificarlo).

### Manejo de 401 (dentro de `request()`)
Porta la lista de "módulos no críticos" de A (`/api/v1/gastos/`,
`/api/v1/clientes/`, `/api/v1/proveedores/`, `/api/v1/inventario/`) que
retornan `{ok:false,status:401,data}` para manejo local, vs el resto que
redirige a `/login/?reason=401&next=...`. **Esta lista pasa a ser
configurable/extensible** (no hardcodeada como en A) para que agregar un
módulo no-crítico futuro no requiera tocar el archivo core -- pero el
comportamiento *default* para cualquier URL no listada explícitamente
sigue siendo "redirigir", igual que hoy, para no cambiar comportamiento
observable sin decisión explícita.

### `normalizeError()`
Unifica los 3 formatos de error ya en uso hoy, sin inventar uno nuevo:
`data.detail` (string), `data.non_field_errors` (array), y errores por
campo (`{campo: [...]}`, aplanados a texto) -- exactamente lo que
`buildError()` de B/C ya hace bien; se porta esa lógica, no se
reescribe.

### Errores de red (`fetch()` lanza)
B/C ya maneja esto correctamente con `try/catch` alrededor de `fetch()`
devolviendo `{ok:false, status:0, data:{detail: err.message}}` -- **A no
lo hace** (un `fetch()` que lanza -- ej. `ERR_BLOCKED_BY_CLIENT`, DNS,
CORS -- se propaga como excepción no capturada). Se porta el
`try/catch` de B/C. Esto es directamente relevante al hallazgo de
`ERR_BLOCKED_BY_CLIENT` de esta misma sesión (§1 del audit) -- con este
manejo, un bloqueo de red no rompe el flujo de la página, solo retorna
un error manejable.

## 4. Lo que NO cambia

- `window.jwtAuth` (D) -- intacto, ya es el SSoT correcto de JWT.
- `ajax-setup-csrf.js` (HTMX) -- intacto, independiente y ya funcional.
- Los 6 `*.api.js` -- **no se tocan en F32.3**. Su migración a
  `Core.Http` es F32.6, después de F32.5 (validación de navegador).
- `login.html` -- explícitamente fuera de alcance (§8 del audit).
- La firma pública que ya consumen los `*_list.js`/`*_editor.js`
  migrados: `window.http(method, url, body)` sigue existiendo como alias
  de `Core.Http.request` para no romper ~50+ archivos que ya lo llaman
  así -- el contrato nuevo se **añade**, no reemplaza la firma que ya
  funciona, hasta que F32.6/F32.7 confirme con pruebas reales que es
  seguro retirar el alias.

## 5. Siguiente paso

Este documento es solo diseño. La implementación de `Core.Http` (código
real) **no se escribe todavía** -- por la misma regla que rigió F31:
nada de esto se activa sin pruebas de navegador reales que confirmen que
el comportamiento portado es idéntico al de A en producción (F32.5).
