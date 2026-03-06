# Pruebas de Humo: Aplicar Nota Crédito desde Workspace

## Objetivo
Garantizar que el usuario pueda ingresar nota crédito a factura desde el modal en `workspace/#facturas` tabla facturas botón "Aplicar NC".

## Checklist de Pruebas

### 1. Verificación de UI - Botón "Aplicar NC"
- [ ] Abrir `workspace/#facturas`
- [ ] Verificar que la tabla de facturas se carga correctamente
- [ ] Verificar que facturas sin NC muestran botón "Aplicar NC" (verde, outline-success)
- [ ] Verificar que facturas con NC NO muestran "Aplicar NC" (muestran "Ver NC" en su lugar)
- [ ] Verificar que el botón tiene atributos `data-factura-id`, `data-factura-numero`, `data-factura-cufe`

### 2. Apertura del Modal
- [ ] Clic en "Aplicar NC" de una factura sin NC
- [ ] Verificar que el modal `#aplicarNCModal` se abre
- [ ] Verificar que muestra:
  - Factura seleccionada: [número]
  - CUFE: [cufe]
  - Campo de archivo XML
  - Checkbox "Previsualizar y validar" (marcado por defecto)
  - Botón "Guardar y aplicar"
  - Botón "Cancelar"

### 3. Preview Mode - Validación Exitosa
- [ ] Seleccionar archivo XML de Nota Crédito válida que referencia la factura seleccionada
- [ ] Clic en "Guardar y aplicar" (con preview activado)
- [ ] Verificar que:
  - Se muestra mensaje "Previsualización OK. Se aplicará a la factura seleccionada."
  - El botón muestra "Procesando..." durante el preview
  - No se cierra el modal aún

### 4. Preview Mode - Validación Fallida (Referencia Incorrecta)
- [ ] Seleccionar archivo XML de Nota Crédito que referencia OTRA factura
- [ ] Clic en "Guardar y aplicar" (con preview activado)
- [ ] Verificar que:
  - Se muestra advertencia: "La Nota Crédito referencia la factura [X] (CUFE: [Y]), pero seleccionaste [A] (CUFE: [B])."
  - El modal NO se cierra
  - El botón vuelve a "Guardar y aplicar"

### 5. Preview Mode - Archivo Inválido (No es NC)
- [ ] Seleccionar archivo XML que NO es Nota Crédito (ej: Invoice)
- [ ] Clic en "Guardar y aplicar" (con preview activado)
- [ ] Verificar que:
  - Se muestra error: "El archivo no es una Nota Crédito UBL 2.1."
  - El modal NO se cierra

### 6. Persistencia Exitosa
- [ ] Con preview exitoso, verificar que:
  - Se envía segundo POST a `/api/v1/facturas/upload-ubl/` (sin preview)
  - Se muestra mensaje de éxito: "Nota Crédito aplicada correctamente."
  - El modal se cierra automáticamente
  - La tabla se refresca automáticamente
  - Se muestra toast: "Nota Crédito aplicada correctamente"
  - La columna NC cambia de "No" a "Sí" (enlace)
  - El botón "Aplicar NC" desaparece y aparece "Ver NC"

### 7. Persistencia - Duplicado (CUDE)
- [ ] Intentar aplicar la misma Nota Crédito dos veces
- [ ] Verificar que:
  - Primer intento: 201 Created (éxito)
  - Segundo intento: 409 Conflict
  - Se muestra advertencia: "Esta Nota Crédito ya fue cargada (CUDE duplicado)."
  - El modal NO se cierra

### 8. Persistencia - Factura Ya Tiene NC
- [ ] Aplicar una Nota Crédito a una factura
- [ ] Intentar aplicar OTRA Nota Crédito a la misma factura
- [ ] Verificar que:
  - Se retorna 422 Unprocessable Entity
  - Error: "already_has_nc"
  - Mensaje: "La factura ya tiene una nota crédito asociada."

### 9. Persistencia - Factura Referenciada No Existe
- [ ] Crear XML de NC que referencia factura inexistente
- [ ] Aplicar a cualquier factura (el preview puede pasar si el XML es válido pero la factura no existe)
- [ ] Verificar que:
  - Se retorna 422 Unprocessable Entity
  - Error: "missing_invoice"
  - Mensaje: "La factura referenciada no existe en este tenant."

### 10. Preview Desactivado
- [ ] Desmarcar checkbox "Previsualizar y validar"
- [ ] Seleccionar archivo XML de NC
- [ ] Clic en "Guardar y aplicar"
- [ ] Verificar que:
  - NO se ejecuta preview
  - Se envía directamente POST para persistir
  - El flujo continúa normalmente

### 11. Validación de Campos Ocultos
- [ ] Abrir modal "Aplicar NC"
- [ ] Verificar en DevTools que los campos ocultos tienen valores:
  - `#nc-factura-id-hidden` = ID de la factura
  - `#nc-factura-numero-hidden` = número de la factura
  - `#nc-factura-cufe-hidden` = CUFE de la factura

### 12. Manejo de Errores de Red
- [ ] Desconectar internet
- [ ] Intentar aplicar NC
- [ ] Verificar que:
  - Se muestra error apropiado
  - El botón vuelve a estado normal
  - El modal NO se cierra

### 13. Cancelar Modal
- [ ] Abrir modal "Aplicar NC"
- [ ] Clic en "Cancelar" o X
- [ ] Verificar que:
  - El modal se cierra
  - No se envía ninguna petición
  - Los campos se limpian

### 14. Ver NC Después de Aplicar
- [ ] Aplicar NC exitosamente
- [ ] Clic en "Ver NC" (enlace en columna NC o botón en Acciones)
- [ ] Verificar que:
  - Se abre modal de detalle de Nota Crédito
  - Muestra número, CUDE, totales, motivo, referencia a factura
  - Enlace "Ver XML" funciona y apunta a `/api/v1/notas-credito/{id}/xml/`

### 15. Verificación de Endpoints
- [ ] Verificar que `/api/v1/facturas/upload-ubl/?preview=true` retorna DTO sin persistir
- [ ] Verificar que `/api/v1/facturas/upload-ubl/` (sin preview) persiste correctamente
- [ ] Verificar que `/api/v1/notas-credito/{id}/xml/` retorna XML completo
- [ ] Verificar que listas de facturas incluyen `has_nc` y `nota_credito_id`
- [ ] Verificar que listas NO incluyen `xml_content`

## Archivos a Verificar

1. **Template**: `apps/tenant/core/templates/tenant/core/workspace.html`
   - Modal `#aplicarNCModal` existe
   - Formulario `#form-aplicar-nc` existe
   - Campos: `#nc-file`, `#nc-preview`, `#nc-feedback`

2. **JavaScript**: `apps/tenant/landing/static/tenant/landing/workspace/facturas.page.js`
   - Función `abrirModalAplicarNC()` existe
   - Función `previewNC()` existe
   - Función `persistNC()` existe
   - Handler de click en `.link-aplicar-nc` está conectado
   - Handler de submit del formulario está conectado

3. **Backend**: `apps/tenant/facturas/api/viewsets.py`
   - Endpoint `upload_ubl` maneja `?preview=true`
   - Detecta `creditnote.ubl21` correctamente
   - Retorna DTO con `referencia.numero` y `referencia.cufe`

## Notas de Implementación

- El preview usa el mismo endpoint que la persistencia pero con `?preview=true`
- El pipeline canónico (`apps/services/xml_ingest`) detecta automáticamente el tipo de documento
- La validación client-side compara `dto.referencia` con la factura seleccionada
- La idempotencia se maneja por CUDE en el backend
- La relación 1:1 se valida en `guardar_nota_credito_desde_dto`
