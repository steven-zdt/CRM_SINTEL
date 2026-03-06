# Smoke Tests - Facturas DataTables Server-Side

**Fecha**: 2024-12-19  
**Módulo**: Facturas  
**Arquitectura**: v2.37 (DataTables server-side POST + CSRF)

---

## ✅ Pre-requisitos Verificados

### 1. Configuración Backend
- [x] `apps/tenant/facturas/api/datatables.py` existe y usa `DataTableSpec`/`DataTableServer`
- [x] `apps/tenant/facturas/api/urls.py` expone `path("dt/facturas/", facturas_dt, name="facturas_dt")`
- [x] `FacturaListDTSerializer` existe en `serializers.py` con campos mínimos
- [x] `fields_map` alineado con columnas frontend (0-6)
- [x] `search_fields` configurados: `["numero", "emisor_razon_social", "receptor_razon_social", "cufe"]`
- [x] `base_qs` optimizado con `only()` para campos mínimos

### 2. Configuración Frontend
- [x] `list.html` tiene estructura canónica (thead limpio, tbody vacío)
- [x] `facturas.table.js` inicializa DataTables con `serverSide: true`, `processing: true`
- [x] `ajax POST` configurado con `X-CSRFToken` y `withCredentials: true`
- [x] Columnas definidas con `data` y `name` alineadas con backend
- [x] `window.initDataTable_FACTURAS()` exportado
- [x] `window.reloadDT_FACTURAS()` exportado
- [x] `facturas.page.js` invoca `initDataTable_FACTURAS()` tras montar vista
- [x] Router configurado: `#facturas` → `initFacturasPage`
- [x] Assets cargados en `assets_facturas.html` en orden correcto

### 3. Integración
- [x] `workspace.html` incluye `assets_facturas.html`
- [x] Router carga módulo al navegar a `#facturas`
- [x] Sin errores de sintaxis (linter)

---

## 🧪 Pruebas Manuales (Smoke Tests)

### Test 1: Carga Inicial de la Tabla
**Objetivo**: Verificar que la tabla se carga correctamente al navegar a `#facturas`

**Pasos**:
1. Abrir `/workspace/#facturas` en el navegador
2. Verificar que aparece el spinner de "Processing..."
3. Verificar que la tabla se renderiza con datos

**Resultado Esperado**:
- ✅ Tabla visible con columnas: Número, Emisión, Naturaleza, Emisor, Receptor, Total, CUFE, Acciones
- ✅ Spinner visible durante carga inicial
- ✅ Datos cargados en la tabla
- ✅ Sin errores en consola del navegador

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 2: Paginación
**Objetivo**: Verificar que la paginación funciona correctamente

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Esperar a que cargue la tabla
3. Hacer clic en "Siguiente" o cambiar el tamaño de página (10, 25, 50)

**Resultado Esperado**:
- ✅ Nueva petición POST a `/api/v1/facturas/dt/facturas/` con parámetros `start` y `length`
- ✅ Tabla se actualiza con nuevos datos
- ✅ Sin recargar la página completa

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 3: Ordenamiento
**Objetivo**: Verificar que el ordenamiento funciona correctamente

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Hacer clic en el header de una columna ordenable (ej: "Emisión", "Número")
3. Verificar que se envía parámetro `order` en la petición POST

**Resultado Esperado**:
- ✅ Nueva petición POST con `order[0][column]` y `order[0][dir]`
- ✅ Tabla se reordena según la columna seleccionada
- ✅ Indicador visual de orden (↑/↓) en el header

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 4: Búsqueda Global
**Objetivo**: Verificar que la búsqueda global funciona correctamente

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Escribir un término en el campo de búsqueda de DataTables
3. Verificar que se envía parámetro `search[value]` en la petición POST

**Resultado Esperado**:
- ✅ Nueva petición POST con `search[value]` y `search[regex]`
- ✅ Tabla filtra resultados según el término de búsqueda
- ✅ Búsqueda aplicada solo en campos permitidos (`search_fields`)

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 5: Botón Refrescar
**Objetivo**: Verificar que el botón "Refrescar" recarga la tabla sin cambiar de página

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Hacer clic en el botón "Refrescar" (🔄)
3. Verificar que se ejecuta `dt.ajax.reload(null, false)`

**Resultado Esperado**:
- ✅ Nueva petición POST a `/api/v1/facturas/dt/facturas/`
- ✅ Tabla se recarga manteniendo la página actual
- ✅ Sin recargar la página completa

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 6: Acciones - Ver Detalle
**Objetivo**: Verificar que el botón "Ver" abre el modal de detalle

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Hacer clic en el botón "Ver" (👁️) de una factura
3. Verificar que se abre el modal con los detalles

**Resultado Esperado**:
- ✅ Modal se abre con datos de la factura
- ✅ Sin errores en consola
- ✅ Tabla no se recarga (solo se abre el modal)

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 7: Acciones - Ver XML
**Objetivo**: Verificar que el botón "Ver XML" muestra el XML de la factura

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Hacer clic en el botón "Ver XML" (📄) de una factura
3. Verificar que se muestra el XML en un modal o nueva pestaña

**Resultado Esperado**:
- ✅ XML se muestra correctamente
- ✅ Sin errores en consola
- ✅ Endpoint `/api/v1/facturas/{id}/xml/` se llama correctamente

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 8: Acciones - Eliminar
**Objetivo**: Verificar que el botón "Eliminar" elimina la factura y recarga la tabla

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Hacer clic en el botón "Eliminar" (🗑️) de una factura
3. Confirmar la eliminación en el modal
4. Verificar que la tabla se recarga automáticamente

**Resultado Esperado**:
- ✅ Modal de confirmación se abre
- ✅ Al confirmar, se envía DELETE a `/api/v1/facturas/{id}/`
- ✅ Tabla se recarga automáticamente con `window.reloadDT_FACTURAS()`
- ✅ Factura eliminada ya no aparece en la tabla

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 9: Importar Factura (Parse-Only)
**Objetivo**: Verificar que el modal de importar funciona correctamente

**Pasos**:
1. Navegar a `/workspace/#facturas`
2. Hacer clic en el botón "Importar (parse-only)"
3. Seleccionar un archivo XML UBL 2.1
4. Hacer clic en "Previsualizar" o "Guardar desde DTO"

**Resultado Esperado**:
- ✅ Modal se abre correctamente
- ✅ Al previsualizar, se muestra el DTO sin persistir
- ✅ Al guardar, se persiste la factura y la tabla se recarga
- ✅ Endpoint `/api/v1/core/documentos/upload/` se llama correctamente

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 10: Verificación de Red (DevTools)
**Objetivo**: Verificar que todas las peticiones usan POST y CSRF

**Pasos**:
1. Abrir DevTools → Network
2. Navegar a `/workspace/#facturas`
3. Realizar acciones (paginación, ordenamiento, búsqueda)
4. Verificar las peticiones en la pestaña Network

**Resultado Esperado**:
- ✅ Todas las peticiones a `/api/v1/facturas/dt/facturas/` son POST
- ✅ Header `X-CSRFToken` presente en todas las peticiones
- ✅ `withCredentials: true` configurado
- ✅ Respuesta JSON con contrato DataTables: `{ draw, recordsTotal, recordsFiltered, data }`
- ✅ Sin peticiones GET para cargar la tabla principal

**Resultado Real**: ⏳ Pendiente de ejecución

---

### Test 11: Manejo de Errores
**Objetivo**: Verificar que los errores se manejan correctamente

**Pasos**:
1. Simular un error en el backend (ej: desconectar base de datos)
2. Navegar a `/workspace/#facturas`
3. Verificar que se muestra un mensaje de error

**Resultado Esperado**:
- ✅ Mensaje de error visible en `#facturas-list-feedback`
- ✅ Tabla no se rompe (mantiene estructura)
- ✅ Error visible en consola del navegador

**Resultado Real**: ⏳ Pendiente de ejecución

---

## 📊 Resumen de Pruebas

| Test | Estado | Notas |
|------|--------|-------|
| Test 1: Carga Inicial | ⏳ Pendiente | - |
| Test 2: Paginación | ⏳ Pendiente | - |
| Test 3: Ordenamiento | ⏳ Pendiente | - |
| Test 4: Búsqueda Global | ⏳ Pendiente | - |
| Test 5: Botón Refrescar | ⏳ Pendiente | - |
| Test 6: Acciones - Ver | ⏳ Pendiente | - |
| Test 7: Acciones - XML | ⏳ Pendiente | - |
| Test 8: Acciones - Eliminar | ⏳ Pendiente | - |
| Test 9: Importar Factura | ⏳ Pendiente | - |
| Test 10: Verificación de Red | ⏳ Pendiente | - |
| Test 11: Manejo de Errores | ⏳ Pendiente | - |

**Total**: 0/11 completadas

---

## 🔍 Verificaciones Técnicas

### Backend
```bash
# Verificar que el endpoint existe
curl -X POST http://localhost:8000/api/v1/facturas/dt/facturas/ \
  -H "X-CSRFToken: <token>" \
  -H "Cookie: csrftoken=<token>" \
  -d '{"draw":1,"start":0,"length":10}'
```

### Frontend
```javascript
// Verificar que las funciones están disponibles
console.log(typeof window.initDataTable_FACTURAS); // "function"
console.log(typeof window.reloadDT_FACTURAS); // "function"
```

---

## 📝 Notas

- Todas las pruebas deben ejecutarse en un entorno con datos de prueba
- Verificar que el usuario tenga permisos para acceder a `/workspace/#facturas`
- Verificar que haya al menos una factura en la base de datos para las pruebas
- Las pruebas de red requieren DevTools abierto

---

## ✅ Criterios de Aceptación (DoD)

- [x] `list.html` usa canon DataTables (thead limpio, tbody vacío, sin JS inline)
- [x] `facturas.table.js` con `serverSide:true`, `processing:true`, POST + CSRF
- [x] Backend `/dt/facturas/` devuelve contrato DataTables estándar
- [x] `urls.py` expone `/api/v1/facturas/dt/facturas/` (POST)
- [x] `facturas.page.js` inicializa la tabla al montar la vista
- [ ] **Pendiente**: Todas las pruebas manuales pasan
- [ ] **Pendiente**: Sin errores en consola del navegador
- [ ] **Pendiente**: Sin errores en logs del servidor

---

**Última actualización**: 2024-12-19
