# Skill: Vanilla JS — SINTEL v3.16

**Carga cuando:** Crear o modificar módulos JS, interacciones del DOM, validaciones de formularios, comunicación con la API.

---

## 1. Namespace Obligatorio — window.Sintel.<App>

Todo código JS DEBE estar encapsulado. Prohibido el scope global sin namespace.

```javascript
// static/<app>/js/<app>.main.js  (o features/<modelo>_list.js)
window.Sintel = window.Sintel || {};

window.Sintel.<App> = (function() {
    // Estado privado del módulo
    const state = {
        table: null,
        currentUuid: null,
    };

    // SSoT de selectores DOM — nunca strings mágicos dispersos
    const DOM = {
        grid:         '#grid-<modelo>',
        search:       '#search-<modelo>',
        container:    '#offcanvas-container-<app>',
        offcanvas:    '#offcanvas-<app>',
        btnNuevo:     '#btn-nuevo-<app>',
    };

    function init() {
        _initTable();
        _bindGlobalEvents();
    }

    function _initTable() { /* ... */ }
    function _bindGlobalEvents() { /* ... */ }

    // API pública del módulo
    return { init, state, DOM };
})();

// Punto de entrada — esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    window.Sintel.<App>.init();
});
```

---

## 2. Sintel.Core.Http — Cliente HTTP Unificado (F32, reemplaza window.http)

**F32 (2026-08-13):** `window.http`/`window.getCookie` (`core/js/lib/http.js`) y su
duplicado (`core/js/http.js`) fueron eliminados tras migrar sus 52
consumidores reales. `window.Sintel.Core.Http` (`core/js/lib/core-http.js`,
cargado globalmente via `assets_core.html`) es ahora el UNICO cliente HTTP
del frontend tenant. Inyecta JWT (con refresh automático vía
`jwtAuth.getValidAccessToken()`), CSRF (cookie `csrftoken`) y
`Content-Type` automáticamente. **Nunca lanza** en 4xx/5xx — siempre
retorna `{ok, status, data}` con `data` ya parseado (no un `Response` crudo,
no requiere `.json()`).

```javascript
// Uso general
const res = await window.Sintel.Core.Http.request(method, url, data);

// Atajos equivalentes
window.Sintel.Core.Http.get(url, opts);
window.Sintel.Core.Http.post(url, body, opts);
window.Sintel.Core.Http.put(url, body, opts);
window.Sintel.Core.Http.patch(url, body, opts);
window.Sintel.Core.Http.delete(url, opts);

// POST — crear
const res = await window.Sintel.Core.Http.post('/api/v1/<app>/', {
    nombre: 'Mi registro',
    sede: uuidSede,     // UUID string — NUNCA entero
});

// PATCH — editar
const res = await window.Sintel.Core.Http.patch(`/api/v1/<app>/${uuid}/`, {
    nombre: 'Nuevo nombre',
});

// DELETE
const res = await window.Sintel.Core.Http.delete(`/api/v1/<app>/${uuid}/`);

// GET (también disponible aunque Tabulator y HTMX lo manejan)
const res = await window.Sintel.Core.Http.get(`/api/v1/<app>/${uuid}/`);

// Respuesta — data ya viene parseada, sin .json()
if (res.ok) {
    const data = res.data;
    // ...
}

// Upload de FormData — método explícito, NUNCA pasar FormData a
// request()/post() esperando que se detecte solo (bug histórico real:
// una version anterior hacia JSON.stringify(FormData) -> "{}", corrompiendo
// el archivo en silencio). request() SI maneja FormData de forma segura si
// se le pasa directo (no la serializa), pero upload() es la forma explícita
// y preferida para uploads.
const formData = new FormData();
formData.append('file', fileInput.files[0]);
const res = await window.Sintel.Core.Http.upload('POST', '/api/v1/<app>/upload/', formData);
```

Contrato completo: `documentacion/F32_3_CORE_HTTP_CONTRACT.md`.

---

## 3. getHeaders() — Headers Manuales (solo si Sintel.Core.Http no aplica)

```javascript
function getHeaders() {
    const headers = { 'Content-Type': 'application/json' };

    // JWT desde el bridge de sesión (usar getValidAccessToken si es async-safe;
    // getAccessToken es sincrono pero NO refresca un token expirado)
    const token = window.jwtAuth?.getAccessToken?.();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // CSRF para Django — o usar window.Sintel.Core.Http.csrf()
    const csrf = document.cookie.split('; ')
        .find(r => r.startsWith('csrftoken='))?.split('=')[1];
    if (csrf) headers['X-CSRFToken'] = csrf;

    return headers;
}

// Uso directo con fetch (solo si Sintel.Core.Http no está disponible)
const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
});
```

---

## 4. Recolección de Datos de Formulario — Reglas Críticas

```javascript
function collectData(form) {
    const fd = new FormData(form);

    return {
        // Strings normales
        nombre:       (fd.get('nombre') || '').trim(),
        descripcion:  fd.get('descripcion') || '',

        // UUID de FK — NUNCA parseInt() ni conversión numérica
        // parseInt("9abc-...", 10) = 9  ← corrupción silenciosa (AGENTS.md §27)
        sede:         fd.get('sede_uuid') || null,
        cliente:      fd.get('cliente_uuid') || null,

        // Booleanos desde checkbox
        activo:       fd.get('activo') === 'on' || fd.get('activo') === 'true',

        // Números
        monto:        parseFloat(fd.get('monto')) || 0,
        consecutivo:  parseInt(fd.get('consecutivo'), 10) || null,
    };
}
```

---

## 5. Comunicación entre Módulos — CustomEvents

Los módulos se comunican mediante eventos DOM. Prohibido llamar funciones de otro módulo directamente.

```javascript
// Emisor (editor.js) — después de guardar exitosamente
document.body.dispatchEvent(new CustomEvent('<modelo>Guardado', {
    detail: { uuid: savedUuid }
}));

// Receptor (list.js) — escucha y reacciona
document.body.addEventListener('<modelo>Guardado', function(e) {
    state.table?.replaceData();
    // Opcional: resaltar la fila recién guardada
    // const uuid = e.detail?.uuid;
});

// Trigger del backend (HX-Trigger header) — también llega aquí
document.body.addEventListener('lista<App>Changed', function() {
    state.table?.replaceData();
});
```

---

## 6. DOM Shield — Protección de ForeignKeys en Formularios

Cuando un formulario tiene un `<select>` visible para búsqueda/display y un `<input hidden>` para el valor real, eliminar el `name` del select antes de enviar.

```javascript
function applyDomShield(form) {
    // Selectores visibles de display — solo muestran texto, no envían valor
    const displaySelects = form.querySelectorAll('[data-display-only]');
    displaySelects.forEach(s => s.removeAttribute('name'));
}

// Restaurar si se reutiliza el formulario
function restoreDomShield(form) {
    form.querySelectorAll('[data-display-only]').forEach(s => {
        s.setAttribute('name', s.dataset.fieldName);
    });
}
```

---

## 7. Manejo de Errores UI

```javascript
async function guardar(data, uuid) {
    try {
        const method = uuid ? 'PATCH' : 'POST';
        const url    = uuid ? `/api/v1/<app>/${uuid}/` : `/api/v1/<app>/`;
        const res    = await window.Sintel.Core.Http.request(method, url, data);

        if (res.ok) {
            document.body.dispatchEvent(new CustomEvent('<modelo>Guardado'));
            return true;
        }

        // DRF validation errors (400) — res.data ya viene parseado
        if (res.status === 400) {
            const errors = res.data;
            window.UIManager?.handleError(
                { data: errors },
                { contexto: '[<App>:Guardar]' }
            );
        } else {
            window.UIManager?.notifyError({
                data: { detail: `Error ${res.status}: No se pudo guardar.` }
            });
        }
        return false;

    } catch (err) {
        console.error('[<App>:Guardar]', err);
        window.UIManager?.notifyError({
            data: { detail: 'Error de conexión. Intente de nuevo.' }
        });
        return false;
    }
}
```

---

## 8. Reglas Estrictas

| Regla | Detalle |
|---|---|
| `window.Sintel.<App>` | Todo código en namespace — prohibido global sin encapsular |
| `window.Sintel.Core.Http` | Para todas las peticiones con auth — nunca fetch desnudo en producción (F32) |
| UUID sin `parseInt` | `fd.get('campo_uuid') || null` — nunca conversión numérica (AGENTS.md §27) |
| `source="relacion.campo"` | En serializers Django: punto, no `__` (AGENTS.md §30) |
| CustomEvents | Comunicación entre módulos — nunca llamar métodos del módulo vecino |
| `replaceData()` | Recargar Tabulator — nunca destruir/recrear la instancia |
| `cloneNode(true)` | Para añadir listener a botón que puede tener listener previo |
