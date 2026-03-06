# Paso 3: Interfaz HTMX y Offcanvas - COMPLETADO

**Fecha**: 2026-02-10  
**Objetivo**: Crear la experiencia de usuario modular con Offcanvas y HTMX.

---

## ✅ Cambios Implementados

### 1. Template Offcanvas Creado

**Archivo**: `apps/tenant/core/templates/tenant/core/partials/proveedores/proveedor_offcanvas.html`

✅ **Estructura Bootstrap 5 Offcanvas**:
- Componente `offcanvas offcanvas-end` con ancho responsivo (90% max-width: 800px)
- Header con título dinámico (Editar/Nuevo Proveedor)
- Body con formulario completo
- Footer con botones de acción (Cancelar/Guardar)

**Código implementado**:
```html
<div class="offcanvas offcanvas-end" tabindex="-1" id="offcanvas-proveedor" 
     aria-labelledby="offcanvas-proveedor-label" style="width: 90%; max-width: 800px;">
  <div class="offcanvas-header border-bottom bg-light">
    <h5 class="offcanvas-title" id="offcanvas-proveedor-label">
      <i class="bi bi-building me-2"></i>
      <span id="offcanvas-proveedor-titulo">
        {% if proveedor %}Editar Proveedor{% else %}Nuevo Proveedor{% endif %}
      </span>
    </h5>
    <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Cerrar"></button>
  </div>
  <div class="offcanvas-body">
    <!-- Formulario con HTMX -->
  </div>
</div>
```

---

### 2. Triggers HTMX Implementados

✅ **Atributos HTMX en el formulario**:
- `hx-post="/api/v1/proveedores/"`: Endpoint para crear/actualizar proveedor
- `hx-target="#grid-proveedores"`: Target para actualizar la tabla después del submit
- `hx-swap="none"`: No reemplaza contenido, solo dispara eventos para refrescar la tabla

**Código implementado**:
```html
<form id="form-proveedor" method="POST" onsubmit="return false;"
      hx-post="/api/v1/proveedores/" 
      hx-target="#grid-proveedores" 
      hx-swap="none">
  <!-- Campos del formulario -->
</form>
```

**Comportamiento**:
- Al hacer submit, HTMX envía POST a `/api/v1/proveedores/`
- Si hay un `id` en el hidden input, el backend detecta que es actualización (PATCH)
- Si no hay `id`, el backend crea un nuevo proveedor (POST)
- Después del submit exitoso, la tabla `#grid-proveedores` se refresca automáticamente

---

### 3. Contenedor de Feedback para UIManager

✅ **Contenedor de errores implementado**:
- `id="form-feedback"`: ID estándar para que UIManager maneje errores de validación 400
- Clases Bootstrap: `alert alert-danger d-none` (oculto por defecto)
- UIManager mostrará errores de validación en este contenedor

**Código implementado**:
```html
{# ⚠️ Paso 3: Contenedor de feedback para UIManager (manejo de errores 400) #}
<div id="form-feedback" class="alert alert-danger d-none mb-3" role="alert"></div>
```

**Funcionamiento con UIManager**:
- Cuando el backend retorna un error 400 (validación), UIManager detecta el contenedor `#form-feedback`
- UIManager muestra los errores de validación en este contenedor
- El contenedor se hace visible (`d-none` se remueve) y muestra los mensajes de error
- Los errores se formatean de manera legible para el usuario

---

### 4. ViewSet Actualizado

**Archivo**: `apps/tenant/proveedores/api/viewsets.py`

✅ **Template path actualizado**:
- Cambiado de `'tenant/core/partials/proveedores/offcanvas_form.html'` 
- A `'tenant/core/partials/proveedores/proveedor_offcanvas.html'`

**Código actualizado**:
```python
@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
def gestor_offcanvas(self, request):
    # ...
    template_name = 'tenant/core/partials/proveedores/proveedor_offcanvas.html'
    return Response(context, template_name=template_name)
```

---

## 📋 Checklist de Verificación

### Estructura Offcanvas
- [x] Componente Bootstrap 5 Offcanvas implementado
- [x] Header con título dinámico (Editar/Nuevo)
- [x] Body con formulario completo
- [x] Footer con botones de acción
- [x] Ancho responsivo (90% max-width: 800px)

### Triggers HTMX
- [x] `hx-post="/api/v1/proveedores/"` implementado
- [x] `hx-target="#grid-proveedores"` implementado
- [x] `hx-swap="none"` implementado
- [x] Formulario con `onsubmit="return false;"` para prevenir submit nativo

### Feedback y Errores
- [x] Contenedor `#form-feedback` implementado
- [x] Clases Bootstrap correctas (`alert alert-danger d-none`)
- [x] Compatible con UIManager para manejo de errores 400

### ViewSet
- [x] Template path actualizado en `gestor_offcanvas`
- [x] Contexto correcto pasado al template
- [x] TemplateHTMLRenderer configurado correctamente

### Testing
- [x] `python manage.py check` ejecutado sin errores
- [x] Template creado y accesible

---

## 🎯 Resultado Final

✅ **Todos los objetivos del Paso 3 completados**:
1. ✅ Template `proveedor_offcanvas.html` creado con estructura Bootstrap 5 Offcanvas
2. ✅ Triggers HTMX implementados (`hx-post`, `hx-target`, `hx-swap="none"`)
3. ✅ Contenedor de feedback `#form-feedback` para UIManager
4. ✅ ViewSet actualizado para usar el nuevo template

---

## 📝 Notas Técnicas

### Flujo de Interacción HTMX

1. **Usuario hace clic en "Nuevo Proveedor"**:
   - JavaScript carga el offcanvas vía HTMX: `GET /api/v1/proveedores/gestor-offcanvas/`
   - El ViewSet renderiza `proveedor_offcanvas.html` con contexto vacío
   - El offcanvas se muestra con formulario en blanco

2. **Usuario hace clic en "Editar Proveedor"**:
   - JavaScript carga el offcanvas vía HTMX: `GET /api/v1/proveedores/gestor-offcanvas/?id=123`
   - El ViewSet renderiza `proveedor_offcanvas.html` con contexto del proveedor
   - El offcanvas se muestra con formulario prellenado

3. **Usuario envía el formulario**:
   - HTMX intercepta el submit y envía POST a `/api/v1/proveedores/`
   - Si hay `id` en el hidden input, el backend detecta actualización (PATCH)
   - Si no hay `id`, el backend crea nuevo proveedor (POST)
   - Si hay errores 400, UIManager los muestra en `#form-feedback`
   - Si es exitoso, la tabla `#grid-proveedores` se refresca automáticamente

### Integración con UIManager

El contenedor `#form-feedback` es detectado automáticamente por UIManager cuando:
- El backend retorna un error 400 (Bad Request)
- UIManager busca el contenedor usando `errorContainerSelector: '#form-feedback'`
- Los errores de validación se formatean y muestran en el contenedor
- El contenedor se hace visible automáticamente

### Compatibilidad con Tabulator

El atributo `hx-target="#grid-proveedores"` apunta a la tabla Tabulator. Cuando el submit es exitoso:
- HTMX dispara el evento `htmx:afterRequest`
- JavaScript escucha este evento y llama a `table.replaceData()` para refrescar la tabla
- La tabla se actualiza con los datos más recientes del servidor

---

**Estado Final**: ✅ **Paso 3 completado - Interfaz HTMX y Offcanvas implementada**
