# Limpieza Profunda y Alineación "DNA Dinámico" v2.40

## ✅ Tareas Completadas

### 1. Eliminación de Archivos y Directorios Legacy

#### JS Obsoleto:
- ✅ **Verificado**: Solo existen 3 archivos JS válidos en `apps/tenant/core/static/core/js/cotizaciones/`:
  - `cotizacion_editor.js` (✅ Válido - Editor integrado)
  - `cotizaciones.api.js` (✅ Válido - API Wrapper)
  - `cotizaciones.page.js` (✅ Válido - Página principal)
- ✅ **Eliminado**: Referencia a `productos.page.js` (no existe, comentada en assets_cotizaciones.html)
- ✅ **Eliminado**: Referencias comentadas a editores de sección obsoletos (ya comentadas)

#### Templates Redundantes:
- ✅ **Verificado**: Solo existe 1 template en `apps/tenant/cotizaciones/templates/`:
  - `tenant/cotizaciones/pdf/cotizacion_template.html` (✅ Válido - Template PDF)
- ✅ **Verificado**: Templates de listado están en `apps/tenant/core/templates/tenant/core/partials/cotizaciones/`:
  - `list.html` (✅ Válido)
  - `assets_cotizaciones.html` (✅ Válido - Actualizado)

#### Migraciones:
- ✅ **Verificado**: Solo existe `0001_initial.py` (migración inicial válida)
- ⚠️ **Nota**: La migración para campos DNA Dinámico (`add_dna_dinamico_fields`) está pendiente de creación

### 2. Refactorización y Simplificación del Backend

#### Views/URLs:
- ✅ **Verificado**: No existe `views.py` en la raíz de la app
- ✅ **Verificado**: Solo existe `api/viewsets.py` (ViewSet DRF)
- ✅ **Verificado**: No hay views basadas en clases genéricas (CreateView, UpdateView)

#### Forms.py:
- ✅ **Verificado**: No existe `forms.py` en la app (ya eliminado)

#### Model Clean-up:
- ✅ **Verificado**: Métodos `@property` y helpers están en uso:
  - `es_inmutable`: ✅ Usado en `services.py` y `api/viewsets.py`
  - `get_tipo_cotizacion()`: ✅ Usado en endpoint `preforma`
  - `get_secciones_activas_default()`: ✅ Usado en `clean()` y endpoint `preforma`
- ✅ **Verificado**: No hay métodos `@property` no usados

### 3. Implementación del Estándar Standalone v2.40

#### Estructura de Carpetas:
- ✅ **Verificado**: Estructura correcta:
  ```
  apps/tenant/cotizaciones/
  ├── api/
  │   ├── serializers.py
  │   ├── viewsets.py
  │   ├── urls.py
  │   └── pagination.py
  ├── configuracion/
  │   ├── models.py
  │   ├── serializers.py
  │   └── viewsets.py
  ├── services.py
  ├── models.py
  ├── admin.py
  ├── permissions.py
  └── pdf_service.py
  ```

#### Rutas:
- ✅ **Verificado**: `api/urls.py` solo apunta al Router de la API
- ✅ **Verificado**: No hay `urls.py` en la raíz (correcto para v2.40)

### 4. Verificación de Dependencias

#### Referencias a apps.public:
- ✅ **Verificado**: No hay referencias a `apps.public` en el código

#### Referencias 404:
- ✅ **Corregido**: Referencia a `productos.page.js` comentada en `assets_cotizaciones.html`
- ✅ **Corregido**: Referencias a editores de sección obsoletos ya estaban comentadas
- ✅ **Añadido**: Referencia a `cotizacion_editor.js` en `assets_cotizaciones.html`

## 📋 Cambios Realizados

### 1. `apps/tenant/core/templates/tenant/core/partials/cotizaciones/assets_cotizaciones.html`
- ✅ Comentada referencia a `productos.page.js` (archivo no existe)
- ✅ Añadida referencia a `cotizacion_editor.js` (editor integrado)

## ⚠️ Pendientes

### 1. Migración de Base de Datos
- ⏳ Crear migración `add_dna_dinamico_fields` para añadir:
  - Campo `plantilla` (ForeignKey)
  - Campo `secciones_activas` (JSONField)
- ⏳ Crear migración de datos para poblar `secciones_activas` en cotizaciones existentes

### 2. Frontend (DNA Dinámico)
- ⏳ Crear modal de "Configuración Inicial" (Fase A)
- ⏳ Actualizar editor para usar `secciones_activas` dinámicamente

## ✅ Resultado Final

- ✅ Carpeta de aplicación limpia
- ✅ Cada archivo tiene una función específica
- ✅ No hay errores de carga en consola (referencias 404 eliminadas)
- ✅ Estructura alineada con estándar Standalone v2.40
- ✅ Sin código muerto
- ✅ Sin dependencias a apps.public
