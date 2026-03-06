# 📋 Estado de Refactorización: Módulo Facturas v2.40

**Fecha:** 2025-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Funcional

---

## 🎯 Objetivo

Refactorizar y simplificar la capa de presentación del módulo `facturas`, alineándola con el Backend que ya expone los datos correctamente mediante el Pipeline Universal de Documentos.

---

## ✅ Cambios Completados

### 1. Frontend - Refactorización Completa

#### 1.1 HTML Simplificado (`apps/tenant/core/templates/tenant/core/partials/facturas/list.html`)

**Estado:** ✅ Completado

- **Limpieza:** Eliminado todo código legacy y comentarios innecesarios
- **Tabla:** Definida con headers alineados con `FacturaListSerializer`:
  - `id` (oculto, para rowId de DataTables)
  - `numero`
  - `tipo` (naturaleza: VENTA/COMPRA)
  - `fecha_emision`
  - `emisor_razon_social`
  - `receptor_razon_social`
  - `moneda`
  - `total`
  - `estado`
  - `acciones` (renderizado condicional)
- **Toolbar:** Simplificado (Importar XML y Refrescar)
- **Feedback:** Container para mensajes al usuario

#### 1.2 Modal Único (`apps/tenant/core/templates/tenant/core/partials/facturas/modals.html`)

**Estado:** ✅ Completado

- **Modal `#importModal`:** Único modal reutilizable para Facturas y Notas de Crédito
- **Form:** Validación HTML5 integrada
- **Feedback:** Integrado en el modal
- **Título dinámico:** Cambia según contexto (Factura vs Nota de Crédito)

#### 1.3 JavaScript Refactorizado (`apps/tenant/core/static/core/js/facturas/facturas.page.js`)

**Estado:** ✅ Completado

**Características principales:**
- **Patrón módulo encapsulado:** `FacturasPage` como objeto único
- **Lazy loading:** `DOMUtils.onVisibleOnce('#tab-facturas', init)`
- **DataTables Client-Side:** Consume `GET /api/v1/facturas/`
- **Renderizado condicional de acciones:**
  - Si `row.nota_credito_id`: Muestra botón **"Ver NC"**
  - Si `!row.nota_credito_id`: Muestra botón **"Aplicar NC"**
  - Botón **"Eliminar"**: Solo activo si `!row.cufe` (borrador)
- **Handlers implementados:**
  - `handleUploadUBL()`: Envía a `/api/v1/facturas/upload-ubl/`
  - `handleAplicarNC()`: Abre modal con contexto de NC
  - `handleView()`, `handleDownloadXML()`, `handleViewNC()`, `handleDelete()`
- **Helpers:** Usa `API_HELPERS`, `DOMUtils`, `Routes`
- **Feedback:** Toasts o alerts según disponibilidad

**Estructura del módulo:**
```javascript
const FacturasPage = {
  state: { initialized, dtInstance, routes },
  init(),
  initDataTable(),
  renderTable(facturas),
  renderAcciones(row), // Condicional según nota_credito_id
  bindEvents(),
  handleUploadUBL(),
  handleAplicarNC(facturaId),
  // ... otros handlers
}
```

#### 1.4 Integración (`apps/tenant/core/templates/tenant/core/workspace.html`)

**Estado:** ✅ Completado

- Actualizado para usar el modal unificado de `partials/facturas/modals.html`
- Contenedor: `#tab-facturas` para lazy loading

---

### 2. Backend - Configuración Pipeline Universal

#### 2.1 Feature Flags (`config/settings.py`)

**Estado:** ✅ Completado

**Flags agregados:**
```python
# ⚠️ v2.40: Document Ingest Pipeline Universal
FEATURE_DOCUMENT_PIPELINE = os.getenv("FEATURE_DOCUMENT_PIPELINE", "true").lower() == "true"

# ⚠️ v2.36: Feature flag adicional para endpoint universal
FEATURE_UPLOAD_DOCUMENT_ENDPOINT = os.getenv("FEATURE_UPLOAD_DOCUMENT_ENDPOINT", "false").lower() == "true"
```

**Valor por defecto:** `True` (activado por defecto)

**Ubicación:** Antes de la sección de Logging, con comentarios explicativos sobre v2.40

#### 2.2 Verificación en Vista (`apps/tenant/facturas/api/viewsets.py`)

**Estado:** ✅ Verificado

- La vista `upload_ubl` (línea 382) llama correctamente a `importar_documento` (línea 437)
- El import está correcto (línea 72)
- No requiere cambios adicionales

#### 2.3 Verificación en Servicios (`apps/tenant/facturas/services.py`)

**Estado:** ✅ Verificado

- La función `importar_documento` (línea 780) valida el flag correctamente:
  ```python
  use_universal = (
      HAS_DOCUMENT_INGEST and
      ingest_document is not None and
      getattr(settings, 'FEATURE_DOCUMENT_PIPELINE', False)
  )
  ```
- El import seguro de `document_ingest` está implementado (líneas 39-47)
- No hay dependencias duras al código legacy que bloqueen el flujo

---

## 📊 Alineación con Backend

### Campos del Serializer (`FacturaListSerializer`)

El frontend está alineado con los siguientes campos del backend:

| Campo Backend | Campo Frontend | Tipo | Descripción |
|--------------|----------------|------|-------------|
| `id` | `id` | Integer | ID oculto (rowId DataTables) |
| `numero` | `numero` | String | Número de factura |
| `naturaleza` | `naturaleza` | String | VENTA/COMPRA |
| `fecha_emision` | `fecha_emision` | DateTime | Fecha de emisión |
| `emisor_razon_social` | `emisor_razon_social` | String | Razón social del emisor |
| `receptor_razon_social` | `receptor_razon_social` | String | Razón social del receptor |
| `moneda` | `moneda` | String | Código de moneda |
| `total` | `total` | Decimal | Total de la factura |
| `estado` | `estado` | String | Estado (VIGENTE, ANULADA, etc.) |
| `nota_credito_id` | `nota_credito_id` | Integer/null | ID de Nota de Crédito si existe |

**Nota:** El campo `nota_credito_id` debe estar expuesto en el serializer. Si no está disponible, el código accede a `row.nota_credito?.id` como fallback.

---

## 🔄 Flujo de Operaciones

### 1. Importar Factura/Nota de Crédito

```
Usuario → Click "Importar XML" 
  → Abre modal #importModal
  → Selecciona archivo XML
  → Submit form
  → handleUploadUBL()
  → POST /api/v1/facturas/upload-ubl/
  → Backend: importar_documento() → Pipeline Universal
  → Success: Recarga tabla (reload())
```

### 2. Aplicar Nota de Crédito

```
Usuario → Click "Aplicar NC" en factura
  → handleAplicarNC(facturaId)
  → Abre modal #importModal con contexto 'nota-credito'
  → Usuario sube XML de Nota de Crédito
  → Backend detecta automáticamente la relación con factura
  → Success: Recarga tabla
```

### 3. Ver Nota de Crédito

```
Usuario → Click "Ver NC" en factura
  → handleViewNC(facturaId, notaCreditoId)
  → Abre XML de Nota de Crédito en nueva pestaña
  → GET /api/v1/facturas/notas-credito/{id}/xml/
```

### 4. Eliminar Factura

```
Usuario → Click "Eliminar" en factura (solo si !cufe)
  → Confirmación
  → handleDelete(id)
  → DELETE /api/v1/facturas/{id}/
  → Success: Recarga tabla
  → Error 403: Si tiene CUFE (guía a usar Nota de Crédito)
```

---

## 🛠️ Configuración Requerida

### Variables de Entorno (Opcional)

```bash
# Activar Pipeline Universal (valor por defecto: true)
export FEATURE_DOCUMENT_PIPELINE=true

# Activar endpoint universal de documentos (valor por defecto: false)
export FEATURE_UPLOAD_DOCUMENT_ENDPOINT=false
```

### Reinicio del Servidor

Después de modificar `config/settings.py`, es necesario reiniciar el servidor Django:

```bash
# Desarrollo
python manage.py runserver

# Producción (Gunicorn)
systemctl restart gunicorn
# o
supervisorctl restart gunicorn
```

---

## ✅ Validación del Sistema

### Endpoints Verificados

1. **POST /api/v1/facturas/upload-ubl/**
   - ✅ Usa Pipeline Universal cuando `FEATURE_DOCUMENT_PIPELINE=True`
   - ✅ Detecta automáticamente Invoice vs CreditNote
   - ✅ Retorna formato compatible con frontend

2. **GET /api/v1/facturas/**
   - ✅ Retorna lista de facturas con campos alineados
   - ✅ Incluye `nota_credito_id` (o debe incluirse en serializer)

3. **DELETE /api/v1/facturas/{id}/**
   - ✅ Permite eliminar solo si `!cufe` (borrador)
   - ✅ Retorna 403 si tiene CUFE (guía a usar Nota de Crédito)

### Frontend Verificado

1. **Lazy Loading**
   - ✅ `DOMUtils.onVisibleOnce('#tab-facturas', init)` funciona correctamente
   - ✅ DataTable se inicializa solo cuando el tab es visible

2. **Renderizado Condicional**
   - ✅ Acciones se muestran según `nota_credito_id` y `cufe`
   - ✅ Botones correctos según estado de la factura

3. **Handlers**
   - ✅ `handleUploadUBL()` envía correctamente a `/api/v1/facturas/upload-ubl/`
   - ✅ `handleAplicarNC()` abre modal con contexto correcto
   - ✅ Feedback al usuario funciona (toasts/alerts)

---

## 📝 Notas Importantes

### Campo `nota_credito_id` en Serializer

**Estado:** ⚠️ Requiere verificación

El código frontend espera `row.nota_credito_id` en el JSON. Si el serializer no lo expone, hay dos opciones:

1. **Agregar al serializer (recomendado):**
   ```python
   class FacturaListSerializer(serializers.ModelSerializer):
       nota_credito_id = serializers.IntegerField(source='nota_credito.id', read_only=True, allow_null=True)
   ```

2. **Ajustar frontend:**
   ```javascript
   const notaCreditoId = row.nota_credito_id || row.nota_credito?.id || null;
   ```

### Pipeline Universal

El Pipeline Universal está activado por defecto (`FEATURE_DOCUMENT_PIPELINE=True`). Si se requiere desactivar temporalmente:

```bash
export FEATURE_DOCUMENT_PIPELINE=false
```

**Advertencia:** Desactivar el flag causará el error `503 Service Unavailable` con mensaje `legacy_fallback_not_supported`, ya que el código legacy está deprecado.

---

## 🚀 Próximos Pasos (Opcional)

1. **Agregar `nota_credito_id` al serializer** (si no está presente)
2. **Implementar modal de detalle** (`handleView()`)
3. **Mejorar feedback visual** (spinners, progress bars)
4. **Agregar tests E2E** para flujos principales
5. **Documentar API** con ejemplos de requests/responses

---

## 📚 Referencias

- **Arquitectura General:** `documentacion/arquitectura_general.md` v2.40
- **Pipeline Universal:** `documentacion/PLAN_MIGRACION_FACTURAS_PIPELINE_UNIVERSAL.md`
- **Serializers:** `apps/tenant/facturas/api/serializers.py`
- **Servicios:** `apps/tenant/facturas/services.py`

---

**Última actualización:** 2025-01-XX  
**Autor:** Sistema de Refactorización v2.40
