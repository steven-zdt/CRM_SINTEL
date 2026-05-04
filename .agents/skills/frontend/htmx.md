# Skill: HTMX — SINTEL v2.62

**Carga cuando:** Crear templates con hx-get/post, offcanvas HTMX, swap OOB.

---

## Patrones Canónicos de Templates

### Botón que abre Offcanvas (crear)
```html
<button class="btn btn-primary btn-sm"
        hx-get="/api/v1/<app>/render-offcanvas/crear/"
        hx-target="#offcanvas-container-<app>"
        hx-swap="innerHTML"
        hx-trigger="click">
  <i class="bi bi-plus-lg me-1"></i>Nuevo
</button>
```

### Botón que abre Offcanvas (editar, con id del objeto)
```html
<!-- En un template inline o JS -->
<button hx-get="/api/v1/<app>/{{ obj.id }}/render-offcanvas/editar/"
        hx-target="#offcanvas-container-<app>"
        hx-swap="innerHTML">
  Editar
</button>
```

### Contenedor HTMX para Offcanvas
```html
{# Containers al final del body del workspace tab #}
<div id="offcanvas-container-<app>"></div>
```

### HX-Trigger Response del Backend
```python
# En viewsets.py, tras una operación exitosa:
from django.http import HttpResponse

response = HttpResponse(status=200)
response['HX-Trigger'] = 'lista<App>Changed'
return response
```

```javascript
// En el JS del módulo, escuchar el trigger:
document.body.addEventListener('lista<App>Changed', function() {
    state.<app>Table.replaceData();
});
```

## Mostrar Offcanvas tras HTMX settle

```javascript
// Patrón para abrir offcanvas cuando HTMX inyecta el HTML
document.body.addEventListener('htmx:afterSettle', function(e) {
    const target = e.detail.target;
    if (target && target.id === 'offcanvas-container-<app>') {
        requestAnimationFrame(() => {
            const offcanvasEl = document.getElementById('offcanvas-<app>');
            if (offcanvasEl && window.UIManager?.handleOffcanvas) {
                window.UIManager.handleOffcanvas(offcanvasEl, 'show');
            } else if (offcanvasEl && window.bootstrap) {
                bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl).show();
            }
        });
    }
});
```

## Endpoint Dual (JSON + HTML)

```python
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer

@action(
    detail=False,
    methods=['get'],
    renderer_classes=[TemplateHTMLRenderer, JSONRenderer],
    url_path='render-offcanvas/crear'
)
def render_offcanvas_crear(self, request):
    context = {'empresa': self.get_empresa(), 'modo': 'crear'}
    return render_template_safe(context, 'tenant/<app>/offcanvas_crear.html', request=request)
```

## Formulario con submit HTMX (NO usar action/method nativo)

```html
<form id="form-<app>" method="POST" onsubmit="return false;">
  {# onsubmit="return false;" OBLIGATORIO para formularios HTMX #}
  <!-- campos -->
</form>
<!-- Botón fuera del form también funciona -->
<button id="btn-guardar-<app>" type="button" class="btn btn-primary">
  Guardar
</button>
```

## Rutas de Templates HTMX

```
tenant/<app>/templates/tenant/<app>/
    offcanvas_crear_<modelo>.html
    offcanvas_editar_<modelo>.html
    offcanvas_detalle_<modelo>.html
    assets_<app>.html       <- incluye los scripts JS de la app
```

## Reglas
- `hx-target` siempre apunta a un container `<div id="offcanvas-container-X">` vacío
- `hx-swap="innerHTML"` para reemplazar el contenido del container
- `htmx:afterSettle` para inicializar JS después del swap
- Formularios con `onsubmit="return false;"` para evitar submit nativo
- Nunca usar `hx-post` para mutaciones — hacerlas con `window.http()` desde JS
