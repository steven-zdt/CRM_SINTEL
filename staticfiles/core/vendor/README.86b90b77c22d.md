# Vendor Resources - Recursos Locales

Este directorio contiene recursos de terceros (vendor) que se sirven localmente en lugar de desde CDNs externos.

## ⚠️ Arquitectura v2.60: Resiliencia y Aislamiento

Para evitar dependencias de CDNs externos y mejorar la resiliencia del sistema, los recursos críticos deben servirse localmente.

## Recursos Recomendados para Implementación Local

### 1. Tabulator Tables v6.2.5
- **CSS**: `tabulator_bootstrap5.min.css`
- **JS**: `tabulator.min.js`
- **Descarga**: https://unpkg.com/tabulator-tables@6.2.5/dist/
- **Uso en templates**: 
  ```html
  <link href="{% static 'core/vendor/tabulator_bootstrap5.min.css' %}" rel="stylesheet">
  <script src="{% static 'core/vendor/tabulator.min.js' %}"></script>
  ```

### 2. HTMX v1.9.10
- **JS**: `htmx.min.js`
- **Descarga**: https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js
- **Uso en templates**:
  ```html
  <script src="{% static 'core/vendor/htmx.min.js' %}"></script>
  ```

### 3. SweetAlert2 v11
- **JS**: `sweetalert2.all.min.js`
- **Descarga**: https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js
- **Uso en templates**:
  ```html
  <script src="{% static 'core/vendor/sweetalert2.all.min.js' %}"></script>
  ```

### 4. Notyf v3
- **CSS**: `notyf.min.css`
- **JS**: `notyf.min.js`
- **Descarga**: https://cdn.jsdelivr.net/npm/notyf@3/dist/
- **Uso en templates**:
  ```html
  <link href="{% static 'core/vendor/notyf.min.css' %}" rel="stylesheet">
  <script src="{% static 'core/vendor/notyf.min.js' %}"></script>
  ```

## Pasos para Implementación Local

1. **Descargar archivos**:
   ```bash
   # Ejemplo para Tabulator
   curl -o apps/tenant/core/static/core/vendor/tabulator_bootstrap5.min.css https://unpkg.com/tabulator-tables@6.2.5/dist/css/tabulator_bootstrap5.min.css
   curl -o apps/tenant/core/static/core/vendor/tabulator.min.js https://unpkg.com/tabulator-tables@6.2.5/dist/js/tabulator.min.js
   ```

2. **Actualizar templates**:
   - Reemplazar URLs de CDN por `{% static 'core/vendor/...' %}`
   - Eliminar atributos `onerror` de fallback (ya no son necesarios)

3. **Verificar**:
   - Ejecutar `python manage.py collectstatic`
   - Verificar que los archivos se sirven correctamente

## Ventajas de Implementación Local

- ✅ **Resiliencia**: No depende de CDNs externos
- ✅ **Rendimiento**: Archivos servidos desde el mismo dominio (sin CORS)
- ✅ **Control**: Versiones fijas, sin cambios inesperados
- ✅ **Privacidad**: No se envían peticiones a terceros
- ✅ **Offline**: Funciona sin conexión a Internet (después de la primera carga)

## Nota

Los templates actuales usan fallbacks automáticos a CDNs alternativos. Una vez implementados los recursos locales, se recomienda actualizar los templates para usar recursos locales como primera opción y mantener CDNs como fallback.
