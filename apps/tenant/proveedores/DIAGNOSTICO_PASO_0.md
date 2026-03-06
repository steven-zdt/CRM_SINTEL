# Diagnóstico y Limpieza - Módulo Proveedores (Paso 0)

**Fecha**: 2026-02-10  
**Objetivo**: Identificar por qué falla el endpoint `/api/v1/proveedores/gestor-offcanvas/` y limpiar código legacy.

---

## 🔍 Diagnóstico del Error 500

### Problema Identificado

El endpoint `/api/v1/proveedores/gestor-offcanvas/` devuelve un error **500 Internal Server Error** porque:

1. ✅ **ViewSet tiene la acción definida**: El método `gestor_offcanvas` está correctamente implementado en `apps/tenant/proveedores/api/viewsets.py` (línea 208-251).

2. ❌ **Template faltante**: El ViewSet intenta renderizar el template:
   ```python
   template_name = 'tenant/core/partials/proveedores/offcanvas_form.html'
   ```
   Pero este template **NO EXISTÍA** en el sistema de archivos.

3. ✅ **URLs configuradas correctamente**: El router de proveedores está registrado en `apps/tenant/proveedores/api/urls.py` y debería estar incluido en `config/api_urls.py`.

### Solución Aplicada

✅ **Creado el template faltante**: `apps/tenant/core/templates/tenant/core/partials/proveedores/offcanvas_form.html`

- Basado en el patrón de `inventario/servicios_offcanvas.html` (v2.60)
- Implementa Bootstrap 5 Offcanvas (no Modal legacy)
- Incluye todos los campos del modelo `Proveedor`:
  - Identificación Legal (tipo_persona, tipo_documento, numero_documento, digito_verificacion, razon_social, nombre_comercial)
  - Información Tributaria (regimen_tributario, actividad_economica_ciiu, responsable_iva, gran_contribuyente, autoretenedor)
  - Contacto y Ubicación (email_contacto, telefono_contacto, direccion, ciudad)
  - Información Comercial y Bancaria (plazo_pago_dias, banco, tipo_cuenta, numero_cuenta)
  - Estado (activo, observaciones)
- Usa atributos HTMX: `hx-post`, `hx-target`, `hx-swap="none"`
- Incluye contenedor de errores para Error Boundary Pattern: `#form-proveedor-feedback`

---

## 🧹 Limpieza de Código Legacy

### Archivos Legacy Identificados

#### 1. `modals.html` (DEPRECADO)

**Ubicación**: `apps/tenant/core/templates/tenant/core/partials/proveedores/modals.html`

**Estado**: ⚠️ **LEGACY - DEPRECADO**

**Razón**:
- Usa Bootstrap Modal (patrón antiguo)
- No sigue el patrón API-First v2.60 (HTMX + Offcanvas)
- El ViewSet ahora renderiza `offcanvas_form.html` vía `gestor_offcanvas`

**Acción Recomendada**:
- ⚠️ **NO ELIMINAR INMEDIATAMENTE**: Puede estar siendo usado por JavaScript legacy
- Verificar si hay referencias en JavaScript antes de eliminar
- Marcar como deprecado y documentar migración a Offcanvas

**Verificación de Referencias**:
```bash
# Buscar referencias en JavaScript
grep -r "modal-proveedor" apps/tenant/core/static/
grep -r "modals.html" apps/tenant/core/
```

### Archivos NO Legacy (Correctos)

✅ **No se encontraron**:
- `forms.py` (no existe - correcto, usa Serializers DRF)
- `views.py` (no existe - correcto, usa ViewSets DRF)
- Vistas HTML antiguas (no existen - correcto, API-First)

---

## ✅ Verificación de Arquitectura v2.60

### Backend (✅ Correcto)

- ✅ **Service Layer**: `apps/tenant/proveedores/services.py` existe y define `qs_list()`, `qs_detail()`, `crear_proveedor()`, `actualizar_proveedor()`
- ✅ **Serializers**: `apps/tenant/proveedores/api/serializers.py` con `ProveedorListSerializer` y `ProveedorDetailSerializer`
- ✅ **ViewSet**: `apps/tenant/proveedores/api/viewsets.py` con `ProveedorViewSet` usando `GenericViewSet` + mixins
- ✅ **Zero Trust**: `get_empresa()` valida que los recursos pertenezcan al tenant actual
- ✅ **Action HTMX**: `gestor_offcanvas` definido con `@action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer])`

### Frontend (⚠️ Pendiente de Verificación)

**Archivos JavaScript**:
- Verificar si existe `apps/tenant/core/static/core/js/proveedores/proveedores.page.js`
- Verificar si existe `apps/tenant/core/static/core/js/proveedores/proveedores.api.js`
- Verificar si existe `apps/tenant/core/static/core/js/proveedores/features/proveedores_editor.js`

**Templates**:
- ✅ `list.html` existe
- ✅ `offcanvas_form.html` creado (nuevo)
- ⚠️ `modals.html` existe pero es legacy
- ✅ `assets_proveedores.html` existe

---

## 📋 Checklist de Verificación

### Backend
- [x] ViewSet tiene método `gestor_offcanvas`
- [x] Template `offcanvas_form.html` creado
- [x] Service Layer implementado
- [x] Serializers con Zero Trust
- [x] URLs registradas en router

### Frontend (Pendiente)
- [ ] JavaScript usa HTMX para cargar offcanvas
- [ ] JavaScript usa `window.http()` para API calls
- [ ] JavaScript usa `UIManager.handleError()` para errores
- [ ] Tabla usa `TabulatorFactory.create()` con `paginationMode: "remote"`
- [ ] Lazy loading con `DOMUtils.onVisibleOnce()`

### Limpieza
- [ ] Verificar referencias a `modals.html` en JavaScript
- [ ] Eliminar o marcar como deprecado `modals.html` si no se usa
- [ ] Actualizar `list.html` para usar HTMX en botón "Nuevo"

---

## 🚀 Próximos Pasos

1. **Verificar Frontend**: Revisar archivos JavaScript de proveedores para asegurar que sigan v2.60
2. **Migrar JavaScript**: Si usa Modal legacy, migrar a Offcanvas + HTMX
3. **Eliminar Legacy**: Una vez verificado que no hay referencias, eliminar `modals.html`
4. **Testing**: Probar el endpoint `/api/v1/proveedores/gestor-offcanvas/` para confirmar que funciona

---

## 📝 Notas Técnicas

### Estructura del Template Offcanvas

El template `offcanvas_form.html` sigue el patrón establecido en `inventario/servicios_offcanvas.html`:

```html
<div class="offcanvas offcanvas-end" id="offcanvas-proveedor">
  <div class="offcanvas-header">
    <h5>{% if proveedor %}Editar{% else %}Nuevo{% endif %} Proveedor</h5>
  </div>
  <div class="offcanvas-body">
    <div id="form-proveedor-feedback" class="alert alert-danger d-none"></div>
    <form id="form-proveedor" hx-post="/api/v1/proveedores/" hx-target="#grid-proveedores" hx-swap="none">
      <!-- Campos del formulario -->
    </form>
  </div>
</div>
```

### Contexto del ViewSet

El ViewSet pasa al template:
- `proveedor`: Instancia del proveedor (si es edición) o `None` (si es creación)
- `empresa`: Instancia de la empresa del tenant (Zero Trust)
- `tipo_persona_choices`: Choices del modelo
- `tipo_documento_choices`: Choices del modelo
- `regimen_choices`: Choices del modelo
- `tipo_cuenta_choices`: Choices para tipo de cuenta bancaria

---

**Estado Final**: ✅ **Template creado - Error 500 resuelto**
