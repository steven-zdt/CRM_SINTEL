# Skill: HTMX — SINTEL v3.16

**Carga cuando:** Crear o modificar templates con atributos `hx-*`, offcanvas HTMX, swaps OOB, polling, búsqueda activa.

> **Principio rector (Hypermedia Systems):** HTMX extiende HTML como hipermedia. El servidor devuelve HTML, no JSON. Las mutaciones de datos (POST/PATCH/DELETE) se hacen con Vanilla JS + Fetch — NO con `hx-post`/`hx-put`/`hx-delete`, porque el backend DRF espera JSON con JWT.

---

## 1. Atributos Core — Referencia Rápida

| Atributo | Propósito |
|---|---|
| `hx-get="<url>"` | GET al servidor, recibe HTML |
| `hx-target="#id"` | Elemento donde se inyecta la respuesta |
| `hx-swap="innerHTML"` | Estrategia de swap (ver tabla abajo) |
| `hx-trigger="click"` | Evento que dispara la petición |
| `hx-indicator="#spinner"` | Muestra spinner mientras carga |
| `hx-include="#otro"` | Incluye valores de otro elemento en el payload |
| `hx-vals='{"key":"val"}'` | Añade valores estáticos al payload |
| `hx-confirm="¿Seguro?"` | Confirmación nativa antes de enviar |
| `hx-push-url="true"` | Actualiza la URL del navegador (history) |
| `hx-select="#parte"` | Extrae solo una parte del HTML de respuesta |
| `hx-boost="true"` | Convierte links/forms normales en peticiones AJAX |

### Estrategias `hx-swap`

| Valor | Resultado |
|---|---|
| `innerHTML` | Reemplaza el contenido interno del target |
| `outerHTML` | Reemplaza el elemento completo |
| `beforeend` | Añade al final del target |
| `afterend` | Inserta después del target |
| `none` | No hace swap (solo side effects) |

---

## 2. Patrón SINTEL — Abrir Offcanvas con HTMX

### Botón crear
```html
<button class="btn btn-primary btn-sm"
        hx-get="/api/v1/<app>/render-offcanvas/crear/"
        hx-target="#offcanvas-container-<app>"
        hx-swap="innerHTML"
        hx-indicator="#spinner-<app>">
  <i class="bi bi-plus-lg me-1"></i>Nuevo
</button>
```

### Botón editar (desde Tabulator cellClick)
```javascript
// En la columna de acciones de Tabulator:
const uuid = cell.getRow().getData().uuid;
htmx.ajax('GET',
  `/api/v1/<app>/${uuid}/render-offcanvas/editar/`,
  { target: '#offcanvas-container-<app>', swap: 'innerHTML' }
);
```

### Container (al final del body del workspace tab)
```html
<div id="offcanvas-container-<app>"></div>
<span id="spinner-<app>" class="htmx-indicator">
  <span class="spinner-border spinner-border-sm"></span>
</span>
```

### JS: abrir offcanvas tras settle
```javascript
document.body.addEventListener('htmx:afterSettle', function(e) {
    const target = e.detail.target;
    if (target && target.id === 'offcanvas-container-<app>') {
        requestAnimationFrame(() => {
            const el = document.getElementById('offcanvas-<app>');
            if (el && window.UIManager?.handleOffcanvas) {
                window.UIManager.handleOffcanvas(el, 'show');
            }
        });
    }
});
```

---

## 3. OOB Swaps — Actualizar Múltiples Zonas

El servidor puede actualizar varios elementos en una sola respuesta HTML usando `hx-swap-oob`.

**Backend (Django template):**
```html
<!-- Respuesta principal -->
<div id="resumen-<app>">{{ resumen_html }}</div>

<!-- OOB: actualiza otro elemento sin ser el target directo -->
<div id="contador-global" hx-swap-oob="true">{{ total_registros }}</div>
<div id="badge-<app>" hx-swap-oob="innerHTML:#badge-<app>">
  <span class="badge bg-primary">{{ count }}</span>
</div>
```

**Desde ViewSet (HX-Trigger en lugar de OOB):**
```python
# Preferido en SINTEL: disparar evento y que el JS recargue Tabulator
response = Response(serializer.data, status=200)
response['HX-Trigger'] = 'lista<App>Changed'
return response
```

```javascript
// JS escucha el trigger y recarga la tabla
document.body.addEventListener('lista<App>Changed', function() {
    if (window.Sintel.<App>?.state?.table) {
        window.Sintel.<App>.state.table.replaceData();
    }
});
```

---

## 4. Headers de Respuesta HX-* (Server → Client)

| Header | Efecto en el cliente |
|---|---|
| `HX-Trigger: eventName` | Dispara evento JS en `document.body` |
| `HX-Trigger-After-Settle: eventName` | Dispara evento después del settle del DOM |
| `HX-Redirect: /url` | Redirige la página completa |
| `HX-Refresh: true` | Recarga la página completa |
| `HX-Reswap: innerHTML` | Sobreescribe la estrategia de swap |
| `HX-Retarget: #otro-id` | Sobreescribe el target del swap |

```python
# Múltiples eventos en un solo header (JSON array)
response['HX-Trigger'] = '{"lista<App>Changed": null, "mostrarToast": {"msg": "Guardado"}}'
```

---

## 5. Búsqueda Activa (Active Search)

```html
<input type="search"
       name="q"
       id="search-<app>"
       hx-get="/api/v1/<app>/?format=html"
       hx-target="#resultados-<app>"
       hx-trigger="keyup changed delay:300ms, search"
       hx-indicator="#spinner-search"
       placeholder="Buscar...">
```

> En SINTEL los listados principales usan Tabulator con búsqueda client-side. Usar este patrón solo para búsquedas auxiliares (autocomplete, selectores de vinculación).

---

## 6. Lazy Loading

```html
<!-- El contenido se carga cuando el elemento entra en viewport -->
<div hx-get="/api/v1/<app>/resumen/"
     hx-trigger="revealed"
     hx-swap="innerHTML"
     hx-target="this">
  <div class="spinner-border spinner-border-sm"></div>
</div>
```

---

## 7. Polling (Estado de proceso async)

```html
<!-- Consulta cada 2s hasta que el servidor devuelva hx-trigger="procesoTerminado" -->
<div id="estado-proceso"
     hx-get="/api/v1/<app>/estado-proceso/"
     hx-trigger="load, every 2s"
     hx-target="this"
     hx-swap="outerHTML">
  Procesando...
</div>
```

El servidor detiene el polling devolviendo HTML sin `hx-trigger="every 2s"`.

---

## 8. Endpoint Dual Django (HTML + JSON)

```python
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer

@action(
    detail=False,
    methods=['get'],
    renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
    url_path='render-offcanvas/crear'
)
def render_offcanvas_crear(self, request):
    empresa = self.get_empresa()
    return Response(
        {'empresa': empresa, 'modo': 'crear'},
        template_name='tenant/<app>/offcanvas_crear_<modelo>.html'
    )
```

---

## 9. CSRF con HTMX (Django)

HTMX envía el token CSRF automáticamente desde la cookie si se configura:

```javascript
// Configurar una sola vez al cargar la página (ej: en base.html)
document.addEventListener('htmx:configRequest', function(e) {
    const csrfToken = document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))?.split('=')[1];
    if (csrfToken) {
        e.detail.headers['X-CSRFToken'] = csrfToken;
    }
});
```

---

## 10. Destrucción Segura de Offcanvas (Evitar TypeError)

```javascript
document.body.addEventListener('htmx:beforeCleanupElement', function(e) {
    const el = e.detail.el;
    const offcanvasEl = el.classList.contains('offcanvas')
        ? el
        : el.querySelector('.offcanvas');
    if (offcanvasEl && window.UIManager?.destroyOffcanvas) {
        window.UIManager.destroyOffcanvas(offcanvasEl);
    }
});
```

---

## 11. Formularios HTMX — Regla Obligatoria

```html
<!-- onsubmit="return false;" OBLIGATORIO: evita submit nativo del browser -->
<form id="form-crear-<modelo>" method="POST" onsubmit="return false;">
  <!-- campos -->
</form>
<!-- Botón de submit FUERA del form, disparado por JS -->
<button id="btn-guardar-<modelo>" type="button" class="btn btn-primary">
  Guardar
</button>
```

---

## 12. `hx-on::` — Scope de Eventos (CRITICO)

> **Incidente 2026-06-01:** Cambiar `hx-on::after-request` a `hx-on::after-settle` en botones
> rompió la apertura de offcanvas porque los dos eventos disparan en elementos distintos.

### 12.1 Tabla: dónde dispara cada evento en HTMX 1.9.x

| Evento HTMX | Dispara en | `hx-on::` en botón/form | `document.addEventListener` |
|---|---|---|---|
| `htmx:beforeRequest` | elemento iniciador | ✅ funciona | ✅ funciona |
| `htmx:afterRequest` | elemento iniciador (post-swap) | ✅ funciona | ✅ funciona |
| `htmx:afterSwap` | elemento iniciador | ✅ funciona | ✅ funciona |
| `htmx:afterSettle` | elemento **target** (el div receptor) | ❌ NO llega al botón | ✅ funciona |
| `htmx:beforeCleanupElement` | elemento que se va a eliminar | N/A | ✅ funciona |

**Regla:** `hx-on::` en el botón/form solo captura eventos que se disparan en ESE elemento.
`htmx:afterSettle` se dispara en el `hx-target`, no en el iniciador → `hx-on::after-settle` en un botón no funciona.

### 12.2 Patrón correcto según contexto

**A) Abrir offcanvas desde botón (template)** — usar `after-request`:
```html
<!-- ✅ CORRECTO: after-request dispara en el botón, después del swap sincrónico -->
<button hx-get="/api/v1/<app>/render-offcanvas/crear/"
        hx-target="#offcanvas-container-<app>"
        hx-swap="innerHTML"
        hx-on::after-request="if(event.detail.successful){ sintelAbrirOffcanvas('offcanvas-<app>'); }">
  Nueva Sede
</button>

<!-- ❌ ROTO en HTMX 1.9.x: after-settle dispara en el target, no en el botón -->
<button hx-on::after-settle="sintelAbrirOffcanvas('offcanvas-<app>')">
```

> **Por qué `after-request` funciona:** en HTMX 1.9.x, el swap `innerHTML` se ejecuta
> **síncronamente** dentro del handler de respuesta, antes de disparar `afterRequest`.
> Cuando `afterRequest` llega al botón, el DOM ya tiene el HTML inyectado.

**B) Inicializar JS tras swap (módulo editor)** — usar `document.addEventListener`:
```javascript
// ✅ CORRECTO: escuchar en document captura afterSettle via bubbling desde el target
document.addEventListener('htmx:afterSettle', function(e) {
    if (e.detail.target.id !== 'offcanvas-container-<app>') return;
    initFormEvents();
});

// ❌ INCORRECTO: afterSwap en el mismo elemento inicia antes de que el DOM esté estable
document.addEventListener('htmx:afterSwap', ...);
```

### 12.3 Resumen de la regla

```
hx-on::after-request  → en botón/form  ✅  (el swap ya ocurrió de forma síncrona)
hx-on::after-settle   → en botón/form  ❌  (dispara en target, no llega al botón)
document.addEventListener('htmx:afterSettle', ...) → siempre ✅ (bubbling desde target)
```

---

## 13. Reglas SINTEL

| Regla | Detalle |
|---|---|
| `hx-get` sí | Para cargar HTML de offcanvas, partials, resúmenes |
| `hx-post`/`hx-put`/`hx-delete` NO | Las mutaciones van por `window.http()` con JWT + JSON |
| `hx-target` | Siempre apunta a container vacío `#offcanvas-container-X` |
| `hx-swap="innerHTML"` | Estándar para offcanvas y partials |
| `hx-on::after-request` en botón | Abrir offcanvas post-swap (ver §12) |
| `document.addEventListener('htmx:afterSettle')` | Inicializar JS en editors/módulos |
| `htmx:beforeCleanupElement` | Destruir instancias Bootstrap antes de remover DOM |
| `HX-Trigger` | Header preferido para notificar cambios al frontend |
