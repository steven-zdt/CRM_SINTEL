# Diagnóstico Actual JS Facturas

## Archivo analizado: `apps/tenant/core/static/core/js/facturas.ui.js`

### Endpoints Usados Actualmente

1. **Listar**: `GET /api/v1/facturas/` ✅ (correcto)
2. **Detalle**: 
   - Intenta `GET /api/v1/core/documentos/{id}/` (universal) ✅
   - Fallback a `GET /api/v1/facturas/{id}/` (legacy)
3. **XML**: 
   - Intenta `GET /api/v1/core/documentos/{id}/xml/` (universal) ✅
   - Fallback a `GET /api/v1/facturas/{id}/xml/` (legacy)
4. **Eliminar**: 
   - Intenta `DELETE /api/v1/core/documentos/{id}/` (universal) ✅
   - Fallback a `DELETE /api/v1/facturas/{id}/` (legacy)
5. **Upload**: `POST /api/v1/core/documentos/upload/?preview=true` ✅ (correcto, sin async)
6. **Persistir DTO**: `POST /api/v1/facturas/create-from-dto/` ✅ (existe)

### Helpers de Render Identificados

- `fmtMoney(v, cur)` - Formateo de dinero con Intl.NumberFormat
- `badgeNaturaleza(val)` - Badge para VENTA/COMPRA
- `twoLineParty(razon, nit)` - Render de emisor/receptor en dos líneas
- `shortHash(h)` - Truncar CUFE para mostrar
- `cufeCell(cufe, qrUrl)` - Celda completa de CUFE con botón copiar y QR
- `escapeHtml(text)` - Escapar HTML para XSS
- `actionsCell(factura)` - Botones de acciones (ver, XML, eliminar)

### Estructura de Filtros

- `buildFilters()` - Construye UI de filtros
- `currentFilters()` - Lee valores de filtros y mapea a query params:
  - `naturaleza` → `naturaleza`
  - `nit` → `nit`
  - `desde` → `fecha_emision__date__gte`
  - `hasta` → `fecha_emision__date__lte`

### Acciones Identificadas

- **Ver detalle** (`data-action="view"`) → `showFacturaDetail()`
- **Ver XML** (`data-action="xml"`) → `showFacturaXML()`
- **Eliminar** (`data-action="delete"`) → `confirmDeleteFactura()`

### Funciones de Importación

- `uploadDocumentoXML(formData, preview)` - Sube al endpoint universal
- `createFacturaFromDTO(dto, persistAnexos)` - Persiste DTO en app
- `importarFacturaDesdeXML(file, preview)` - Flujo completo: parse → persist
- `importarFacturaDesdeTexto(xmlText, preview)` - Importar desde texto pegado

### Problemas Identificados

1. ❌ **Mezcla de responsabilidades**: Todo en un solo archivo
2. ❌ **Uso de ES6 modules**: `import { getJSON, sendJSON }` - incompatible con patrón modular actual
3. ❌ **Fallbacks a endpoints legacy**: Aún intenta usar endpoints de facturas para XML/DELETE
4. ✅ **Ya usa endpoint universal**: Para upload está correcto
5. ✅ **Sin `?async=true`**: No se usa async en URLs
6. ⚠️ **Dependencia de http.js**: Usa `getJSON`/`sendJSON` que no están en `lib/http.js` (usa `http()`)

### Columnas de Tabla

1. número
2. naturaleza (badge)
3. emisor (twoLineParty)
4. receptor (twoLineParty)
5. emisión (fecha formateada)
6. subtotal (fmtMoney)
7. impuestos (fmtMoney)
8. total (fmtMoney, bold)
9. CUFE (cufeCell)
10. Acciones (actionsCell)

### Errores Canónicos Manejados

- 409: Duplicado
- 422: Validación
- 415: Tipo no soportado
- 400: Parsing/detección
- 401/403: Auth/permisos
