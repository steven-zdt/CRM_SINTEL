# Fase 2: Orquestación Celery + Materialización e Idempotencia en Facturas

**Objetivo**: Enganchar `apps/tenant/facturas` al Servicio General de Ingesta XML (Fase 1), usando Celery (tenant-aware con `schema_context`), materializando solo datos necesarios (lista mínima), aplicando regla de naturaleza con SSoT empresa, y guardando anexos en `FacturaAnexos`.

**Fecha de implementación**: 2026-02-09

---

## Resumen de Cambios

### 1. Service Layer (`apps/tenant/facturas/services.py`)

**Nuevas funciones añadidas**:

- `_get_current_schema()`: Obtiene el schema_name del tenant actual
- `_b64_file(file_bytes)`: Codifica bytes a base64 string (ASCII-safe)
- `_resolver_naturaleza(emisor_nit, empresa_nit)`: Resuelve naturaleza (VENTA/COMPRA) usando SSoT
- `materializar_factura_desde_result(xml_result, persist_anexos=True)`: Materializa factura desde DTO canónico
- `importar_ubl_async(file_bytes)`: Encola tarea Celery y retorna task_id
- `consultar_tarea(task_id)`: Consulta estado de tarea Celery
- `importar_ubl_sync(file_bytes)`: Ruta síncrona (parsea y materializa directamente)

**Principios**:
- ✅ Service Layer Pattern: Lógica de negocio centralizada
- ✅ SSoT: Usa `get_empresa_emisor_data()` para obtener NIT empresa
- ✅ Idempotencia: Usa CUFE o número para evitar duplicados
- ✅ Lista mínima: Solo persiste campos esenciales, no blobs en Factura
- ✅ Anexos: Guarda XMLs en `FacturaAnexos` (OneToOne)

---

### 2. API Endpoints (`apps/tenant/facturas/api/viewsets.py`)

**Endpoints actualizados/añadidos**:

#### `POST /api/v1/facturas/upload-ubl/`

**Query params**:
- `async=true` (default): Encola tarea Celery y retorna `202 Accepted` con `{"task_id": str, "status": "queued"}`
- `async=false`: Parsea y materializa directamente, retorna `201/200` con datos de factura

**Body** (multipart/form-data):
- `file`: Archivo XML UBL

**Returns**:
- `202 Accepted`: Tarea encolada (async=true)
- `201 Created`: Factura creada (async=false)
- `200 OK`: Factura actualizada (async=false, idempotencia)
- `400 Bad Request`: Falta archivo XML
- `422 Unprocessable Entity`: Falta SSoT empresa

---

#### `GET /api/v1/facturas/ingest/{task_id}/status/`

**Path params**:
- `task_id`: ID de la tarea Celery (retornado por `upload_ubl?async=true`)

**Returns**:
- `202 Accepted`: Tarea aún procesando `{"task_id": str, "state": str}`
- `200 OK`: Tarea completada `{"task_id": str, "state": "SUCCESS", "result": dict}`
- `500 Internal Server Error`: Tarea falló `{"task_id": str, "state": "FAILURE", "error": str}`
- `404 Not Found`: Tarea no existe `{"error": "task_not_found"}`

---

#### `POST /api/v1/facturas/materialize/`

**Body** (application/json):
```json
{
    "dto": <DocumentoXML-serializado>,  // Resultado de ingest_status cuando state=SUCCESS
    "persist_anexos": true|false  // Opcional, default: true
}
```

**Returns**:
- `201 Created`: Factura creada `{"id": int, "numero": str, "naturaleza": str, "created": true}`
- `200 OK`: Factura actualizada `{"id": int, "numero": str, "naturaleza": str, "created": false}`
- `400 Bad Request`: Falta 'dto' en el cuerpo
- `422 Unprocessable Entity`: Falta SSoT empresa o DTO inválido
- `409 Conflict`: Duplicado o restricción violada
- `413 Payload Too Large`: XML/anexo excede tamaño permitido

---

## Flujo de Uso

### Flujo Async (Recomendado para Producción)

1. **Upload**: `POST /api/v1/facturas/upload-ubl/?async=true` → `202` + `task_id`
2. **Polling**: `GET /api/v1/facturas/ingest/{task_id}/status/` → `202` (procesando) o `200` (SUCCESS)
3. **Materializar**: `POST /api/v1/facturas/materialize/` con `dto` del resultado → `201/200`

### Flujo Sync (Útil para Desarrollo o XMLs Pequeños)

1. **Upload**: `POST /api/v1/facturas/upload-ubl/?async=false` → `201/200` (materializado directamente)

---

## Tests Implementados

### ✅ Tests Tenant-Aware

1. **`test_materializar_from_dto.py`** (6 tests):
   - `test_compra_vs_ssot`: Materializa factura COMPRA cuando emisor != empresa
   - `test_venta_vs_ssot`: Materializa factura VENTA cuando emisor == empresa
   - `test_idempotencia_por_cufe`: Idempotencia por CUFE (no duplica)
   - `test_idempotencia_por_numero`: Idempotencia por número cuando no hay CUFE
   - `test_sin_empresa_retorna_422`: Retorna 422 si falta SSoT empresa
   - `test_sin_anexos_no_guarda_factura_anexos`: No guarda FacturaAnexos si persist_anexos=False

2. **`test_upload_async_flow.py`** (5 tests):
   - `test_async_flow_completo`: Flujo completo async (upload → status → materialize)
   - `test_sync_flow_directo`: Flujo sync directo (upload con async=false)
   - `test_upload_sin_archivo_retorna_400`: Upload sin archivo retorna 400
   - `test_status_task_no_existe_retorna_404`: Status de tarea inexistente retorna 404
   - `test_materialize_sin_dto_retorna_400`: Materialize sin DTO retorna 400

---

## Runbook de Verificación

### 1. Verificar Upload Async

```bash
# Subir XML (async=true)
curl -X POST "http://home.sintel.net.co/api/v1/facturas/upload-ubl/?async=true" \
  -H "Cookie: sessionid=..." \
  -F "file=@factura.xml"

# Respuesta esperada: 202 Accepted
# {
#   "task_id": "abc123...",
#   "status": "queued"
# }
```

### 2. Consultar Estado

```bash
# Consultar estado de tarea
curl -X GET "http://home.sintel.net.co/api/v1/facturas/ingest/{task_id}/status/" \
  -H "Cookie: sessionid=..."

# Respuesta esperada: 200 OK (cuando termine)
# {
#   "task_id": "abc123...",
#   "state": "SUCCESS",
#   "result": { ... }
# }
```

### 3. Materializar

```bash
# Materializar desde DTO
curl -X POST "http://home.sintel.net.co/api/v1/facturas/materialize/" \
  -H "Cookie: sessionid=..." \
  -H "Content-Type: application/json" \
  -d '{
    "dto": { ... },
    "persist_anexos": true
  }'

# Respuesta esperada: 201 Created
# {
#   "id": 123,
#   "numero": "FV-001",
#   "naturaleza": "VENTA",
#   "created": true
# }
```

### 4. Verificar Lista

```bash
# Listar facturas (no debe contener blobs)
curl -X GET "http://home.sintel.net.co/api/v1/facturas/?ordering=-fecha_emision" \
  -H "Cookie: sessionid=..."

# Verificar:
# - Naturaleza correcta (COMPRA/VENTA según SSoT)
# - Sin campos xml_raw, application_response_xml en lista
```

### 5. Verificar Detalle (Opcional)

```bash
# Detalle de factura (debe incluir anexos si están disponibles)
curl -X GET "http://home.sintel.net.co/api/v1/facturas/{id}/" \
  -H "Cookie: sessionid=..."

# Verificar:
# - Campos ubl_xml y application_response_xml presentes (si existen)
# - Datos desde FacturaAnexos
```

### 6. Verificar Logs

```bash
# Revisar logs (sin volcar XML completo)
tail -f logs/facturas.log | grep -E "(upload_ubl|materialize|naturaleza)"

# Verificar:
# - Sin 500 en importación
# - Logs claros en tenant.facturas.naturaleza
# - Logs claros en tenant.facturas.import
# - Sin volcar XML completo (solo hash/longitud)
```

---

## Criterios de Aceptación

### ✅ Completado

- ✅ `POST /facturas/upload-ubl/?async=true` encola y devuelve `202` + `task_id`
- ✅ `GET /facturas/ingest/{task_id}/status/` devuelve `SUCCESS` con DTO (o `202` mientras procesa)
- ✅ `POST /facturas/materialize/` guarda la factura con naturaleza correcta (SSoT) y anexos
- ✅ Lista no contiene blobs; detalle (opcional) sí
- ✅ Pruebas tenant-aware en verde
- ✅ Sin `500` en importación (ni por kwargs inesperados ni por blobs XL)

---

## Notas y Decisiones Clave

### Naturaleza

- ✅ Calculada en Service Layer de facturas usando SSoT (`get_empresa_emisor_data()`)
- ✅ Nunca confiar en el payload del cliente
- ✅ Regla: `emisor.nit == empresa.nit` → `VENTA`, si no → `COMPRA`

### Idempotencia

- ✅ Clave única: CUFE (si existe) o número
- ✅ Usa `update_or_create` para evitar duplicados

### Blobs

- ✅ Guardar en `FacturaAnexos` (OneToOne) — no como kwargs de Factura
- ✅ Lista mínima: No exponer blobs en `FacturaListSerializer`

### Errores

- ✅ Mapear a `409/413/422`; `500` solo inesperados
- ✅ Respuestas semánticas claras

### Rutas UI

- ✅ Relativas al tenant, sin host/protocolo
- ✅ `credentials: 'same-origin'` + CSRF donde aplique

### Celery

- ✅ Tareas tenant-aware con `schema_context(schema)` (ya cubierto en Fase 1)

---

## Próximos Pasos (Opcional)

1. **Integración UI**: Actualizar `facturas.page.js` para usar flujo async
2. **Polling automático**: Implementar polling en frontend cada 2-3s hasta SUCCESS
3. **Notificaciones**: Añadir notificaciones cuando la tarea termine
4. **Métricas**: Añadir métricas de tiempo de procesamiento

---

## Conclusión

La Fase 2 está **completamente implementada y probada**, lista para ser usada en producción. Todos los tests pasan y el código está libre de errores de linting. El sistema ahora usa el Servicio General de Ingesta XML (Fase 1) para parseo/validación/normalización, manteniendo las reglas de negocio (naturaleza VENTA/COMPRA) en el Service Layer de facturas.
