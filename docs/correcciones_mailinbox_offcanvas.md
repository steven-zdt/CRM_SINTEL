# Correcciones: MailInboxConfig Offcanvas - Error 500 y Sincronización

**Fecha:** 2024  
**Módulo:** `apps/tenant/empresa`  
**Versión:** v2.60

## Resumen

Se corrigieron múltiples problemas relacionados con el offcanvas de configuración de buzones de correo (`MailInboxConfig`), incluyendo errores 500, problemas de sincronización con HTMX, y mejoras en el manejo de errores.

## Problemas Identificados

### 1. Error 500: `ImproperlyConfigured: Returned a template response with no template_name attribute`

**Causa:**  
El decorador `@action` usaba `renderer_classes=[TemplateHTMLRenderer]`, pero el método retornaba HTML directamente usando `render_to_string()` sin especificar `template_name` en la respuesta.

**Solución:**  
- Eliminado `renderer_classes=[TemplateHTMLRenderer]` del decorador
- Cambiado `Response` por `HttpResponse` para retornar HTML directamente
- Aplicado el mismo cambio en todos los bloques de manejo de errores

**Archivo:** `apps/tenant/empresa/api/viewsets.py`

```python
# Antes (problemático)
@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], ...)
def render_offcanvas(self, request: Request, *args, **kwargs) -> Response:
    html = render_to_string(...)
    return Response(html, content_type='text/html')

# Después (corregido)
@action(detail=False, methods=['get'], ...)
def render_offcanvas(self, request: Request, *args, **kwargs) -> Response:
    html = render_to_string(...)
    from django.http import HttpResponse
    return HttpResponse(html, content_type='text/html')
```

### 2. Problema con QuerySet en `render_offcanvas`

**Causa:**  
`self.get_queryset()` no manejaba correctamente la acción `render_offcanvas`, causando problemas al obtener la configuración.

**Solución:**  
- Usar `MailInboxConfig.objects.all()` directamente en lugar de `self.get_queryset()`
- django-tenants ya aplica el filtro por esquema automáticamente
- Agregado logging para diagnóstico

**Archivo:** `apps/tenant/empresa/api/viewsets.py`

```python
# Antes (problemático)
instance = self.get_queryset().only(...).get(id=config_id)

# Después (corregido)
base_qs = MailInboxConfig.objects.all()
instance = base_qs.only(...).get(id=config_id)
```

### 3. Error: "Contenedor de errores no encontrado"

**Causa:**  
Cuando ocurría un error 500, HTMX no podía cargar el HTML del offcanvas, por lo que `error_handler.html` no estaba disponible en el DOM. El `error_injector.js` intentaba mostrar el error pero no encontraba el contenedor.

**Solución:**  
- Mejorado `error_injector.js` para buscar el contenedor de errores en múltiples ubicaciones:
  1. DOM principal
  2. Contenedor HTMX (`#offcanvas-container-mailinbox`)
  3. Offcanvas cargado (`#offcanvas-mailinbox`)
  4. Crear contenedor temporal si no existe
  5. Usar `SintelFeedback` o `alert` como último recurso

**Archivo:** `apps/tenant/core/static/core/js/error_injector.js`

### 4. Sincronización con `htmx:afterSettle`

**Causa:**  
El JavaScript intentaba inicializar el offcanvas antes de que HTMX terminara de renderizar el contenido.

**Solución:**  
- Migrado de `htmx:afterSwap` a `htmx:afterSettle` para garantizar que el DOM esté completamente actualizado
- Mejorada la búsqueda del offcanvas en múltiples ubicaciones
- Agregada prevención de inicialización duplicada usando `dataset.eventsInitialized`

**Archivo:** `apps/tenant/core/static/core/js/mailinbox/mailinbox_offcanvas.js`

## Cambios en Archivos

### 1. `apps/tenant/empresa/api/viewsets.py`

**Cambios principales:**
- Eliminado `renderer_classes=[TemplateHTMLRenderer]` del decorador `@action`
- Cambiado `Response` por `HttpResponse` en todos los retornos
- Usar `MailInboxConfig.objects.all()` directamente en lugar de `self.get_queryset()`
- Agregado logging detallado para diagnóstico
- Mejorado manejo de errores con HTML estructurado que incluye `error_handler.html`

**Método modificado:** `render_offcanvas()`

### 2. `apps/tenant/core/static/core/js/mailinbox/mailinbox_offcanvas.js`

**Cambios principales:**
- Migrado de `htmx:afterSwap` a `htmx:afterSettle`
- Mejorada búsqueda del offcanvas en múltiples ubicaciones
- Agregada prevención de inicialización duplicada
- Eliminada inicialización automática prematura en `DOMContentLoaded`

**Funciones modificadas:**
- `initOffcanvasEvents()`
- Listener de `htmx:afterSettle`

### 3. `apps/tenant/core/static/core/js/error_injector.js`

**Cambios principales:**
- Mejorada función `showError()` para buscar contenedor de errores en múltiples ubicaciones
- Agregada creación de contenedor temporal si no existe
- Agregado fallback a `SintelFeedback` o `alert` como último recurso

**Función modificada:** `showError()`

## Mejoras Adicionales

### 1. Zero Waste

- `render_offcanvas` usa `.only()` para cargar solo campos necesarios del formulario
- `get_queryset()` optimiza según la acción (list, retrieve, etc.)

### 2. Aislamiento de Tenant

- Verificado que django-tenants maneja automáticamente el aislamiento por esquema
- No se requiere filtrado manual por tenant
- `MailInboxConfig.objects.all()` ya está filtrado por esquema

### 3. Manejo de Errores

- Todos los errores retornan HTML válido con `error_handler.html` incluido
- Logging detallado para diagnóstico
- Mensajes de error estructurados para `error_injector.js`

## Verificación

### Checklist de Garantía Técnica

- ✅ **Aislamiento:** django-tenants maneja automáticamente el aislamiento por esquema
- ✅ **Zero Waste:** Solo se cargan campos necesarios con `.only()`
- ✅ **Manejo de Errores:** Todos los errores retornan HTML válido
- ✅ **Sincronización HTMX:** Usa `htmx:afterSettle` para garantizar DOM actualizado
- ✅ **Error Injector:** Busca contenedor de errores en múltiples ubicaciones

## Pruebas Recomendadas

1. **Crear nueva configuración:**
   - Abrir offcanvas sin ID
   - Verificar que el formulario se carga correctamente
   - Verificar que `error_handler.html` está disponible

2. **Editar configuración existente:**
   - Abrir offcanvas con ID válido
   - Verificar que los datos se cargan correctamente
   - Verificar que el formulario se pre-llena

3. **Manejo de errores:**
   - Intentar editar configuración con ID inexistente
   - Verificar que se muestra mensaje de error en el offcanvas
   - Verificar que `error_injector.js` encuentra el contenedor

4. **Sincronización HTMX:**
   - Verificar que el offcanvas se inicializa después de `htmx:afterSettle`
   - Verificar que no hay warnings de "Offcanvas no encontrado"
   - Verificar que los eventos se inicializan correctamente

## Notas Técnicas

### Por qué usar `HttpResponse` en lugar de `Response`

Cuando usas `render_to_string()` y retornas HTML directamente, no necesitas `TemplateHTMLRenderer`. `TemplateHTMLRenderer` está diseñado para renderizar templates automáticamente, pero en este caso ya estamos renderizando el template manualmente.

Usar `HttpResponse` es más directo y evita el problema de `template_name` requerido por `TemplateHTMLRenderer`.

### Por qué usar `htmx:afterSettle` en lugar de `htmx:afterSwap`

- `htmx:afterSwap`: Se dispara inmediatamente después de que HTMX inserta el contenido en el DOM
- `htmx:afterSettle`: Se dispara después de que HTMX termina de actualizar el DOM, incluyendo animaciones y transiciones de Bootstrap

Para Bootstrap Offcanvas, es crucial usar `afterSettle` porque las animaciones pueden no estar completas cuando se dispara `afterSwap`.

## Referencias

- [Django REST Framework - Renderers](https://www.django-rest-framework.org/api-guide/renderers/)
- [HTMX Events](https://htmx.org/reference/#events)
- [Bootstrap Offcanvas](https://getbootstrap.com/docs/5.3/components/offcanvas/)
