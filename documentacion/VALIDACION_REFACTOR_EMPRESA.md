# Validación Post-Aplicación: Refactor Módulo Empresa

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Cambios aplicados

---

## ✅ Cambios Aplicados

### 1. Core Orchestrator (`apps/tenant/core/api/views.py`)
- ✅ Eliminados campos legacy del PATCH
- ✅ Implementado upsert (crea si no existe, actualiza si existe)
- ✅ Solo campos canónicos: `razon_social`, `nit`, `dv`, `direccion`, `telefono`, `email_contacto`, `regimen_tributario`, `website`, `moneda`

### 2. Service Layer (`apps/tenant/empresa/impl/empresa_service.py`)
- ✅ Eliminadas referencias a campos legacy en `get_empresa()` y `update_empresa()`
- ✅ Solo campos canónicos en DTOs

---

## 🧪 Pruebas Manuales

### Prueba 1: Core Orchestrator - Crear Empresa (Upsert)

**Endpoint:** `PATCH /api/v1/core/empresa/`

**Sin empresa existente:**
```bash
curl -X PATCH http://home.sintel.com/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{
    "razon_social": "Mi Empresa Test",
    "nit": "900123456",
    "dv": "1",
    "direccion": "Calle Test 123",
    "telefono": "1234567890",
    "email_contacto": "test@example.com",
    "regimen_tributario": "NO_RESPONDE",
    "moneda": "COP"
  }'
```

**Resultado esperado:**
- Status: `201 Created`
- Body: DTO con empresa creada + branding

**Con empresa existente:**
```bash
curl -X PATCH http://home.sintel.com/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{
    "razon_social": "Mi Empresa Actualizada",
    "telefono": "9876543210"
  }'
```

**Resultado esperado:**
- Status: `200 OK`
- Body: DTO con empresa actualizada + branding

---

### Prueba 2: API Empresa - Listar (Paginado)

**Endpoint:** `GET /api/v1/empresas/?page_size=1`

```bash
curl -X GET "http://home.sintel.com/api/v1/empresas/?page_size=1" \
  -H "Accept: application/json" \
  -H "Cookie: sessionid=..."
```

**Resultado esperado:**
```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

O si existe empresa:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "razon_social": "...",
      "nit": "...",
      "dv": "...",
      "direccion": "...",
      "telefono": "...",
      "email_contacto": "..."
    }
  ]
}
```

**Validar:**
- ✅ Formato paginado DRF (`{count, results, next, previous}`)
- ✅ Sin campos legacy en `results`

---

### Prueba 3: API Empresa - Mi Empresa (Singleton)

**Endpoint:** `GET /api/v1/empresas/mi-empresa/`

**Sin empresa:**
```bash
curl -X GET http://home.sintel.com/api/v1/empresas/mi-empresa/ \
  -H "Accept: application/json" \
  -H "Cookie: sessionid=..."
```

**Resultado esperado:**
- Status: `204 No Content`
- Body: vacío

**Con empresa:**
```bash
curl -X GET http://home.sintel.com/api/v1/empresas/mi-empresa/ \
  -H "Accept: application/json" \
  -H "Cookie: sessionid=..."
```

**Resultado esperado:**
- Status: `200 OK`
- Body: DTO completo con campos canónicos (sin legacy)

---

### Prueba 4: API Empresa - Crear (POST)

**Endpoint:** `POST /api/v1/empresas/`

```bash
curl -X POST http://home.sintel.com/api/v1/empresas/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{
    "razon_social": "Nueva Empresa",
    "nit": "800123456",
    "dv": "2",
    "direccion": "Calle Nueva 456",
    "telefono": "5551234567",
    "email_contacto": "nueva@example.com",
    "regimen_tributario": "NO_RESPONDE",
    "moneda": "COP"
  }'
```

**Resultado esperado (primera vez):**
- Status: `201 Created`
- Body: DTO completo

**Resultado esperado (segunda vez - singleton violation):**
- Status: `409 Conflict`
- Body: `{"error": "singleton_violation", "detail": "Ya existe una empresa en este tenant."}`

---

### Prueba 5: Workspace UI - Crear/Editar Empresa

**URL:** `http://home.sintel.com/workspace/#empresa`

**Pasos:**
1. Abrir el workspace en el tab "Empresa"
2. Hacer clic en "Crear Empresa"
3. Llenar formulario con datos válidos:
   - NIT: `900123456`
   - Razón Social: `Empresa Test`
   - Dirección: `Calle Test 123`
   - Teléfono: `1234567890`
   - Email: `test@example.com`
4. Hacer clic en "Crear"

**Validar:**
- ✅ Modal se cierra después de crear
- ✅ Tabla se actualiza con la nueva empresa
- ✅ No aparecen errores de campos legacy en consola
- ✅ Botón "Editar" se habilita automáticamente

**Editar:**
1. Hacer clic en "Editar"
2. Modificar algún campo (ej: teléfono)
3. Hacer clic en "Guardar Cambios"

**Validar:**
- ✅ Cambios se guardan correctamente
- ✅ Tabla se actualiza
- ✅ No aparecen errores

---

## 🔍 Validación de Código

### Verificar que no haya referencias a campos legacy

```bash
# Buscar campos legacy en Core Orchestrator
grep -r "tipo_contribuyente_clase\|tipo_contribuyente_segmento\|regimen_renta_codigo\|responsabilidades_rut_codigos\|actividad_economica" apps/tenant/core/api/views.py

# Buscar campos legacy en Service Layer
grep -r "tipo_contribuyente_clase\|tipo_contribuyente_segmento\|regimen_renta_codigo\|responsabilidades_rut_codigos\|actividad_economica" apps/tenant/empresa/impl/empresa_service.py
```

**Resultado esperado:** Sin coincidencias (o solo en comentarios/documentación)

---

## ✅ Checklist de Validación

- [ ] Core Orchestrator PATCH crea empresa si no existe (201)
- [ ] Core Orchestrator PATCH actualiza empresa si existe (200)
- [ ] GET /api/v1/empresas/ retorna formato paginado DRF
- [ ] GET /api/v1/empresas/mi-empresa/ retorna 204 si no hay empresa
- [ ] GET /api/v1/empresas/mi-empresa/ retorna 200 con DTO si hay empresa
- [ ] POST /api/v1/empresas/ crea empresa (201)
- [ ] POST /api/v1/empresas/ retorna 409 si ya existe (singleton)
- [ ] Workspace UI crea empresa correctamente
- [ ] Workspace UI edita empresa correctamente
- [ ] No aparecen errores de campos legacy en logs/consola
- [ ] No hay referencias a campos legacy en código (excepto comentarios)

---

## 📝 Notas

- Los campos legacy eliminados fueron:
  - `tipo_contribuyente_clase`
  - `tipo_contribuyente_segmento`
  - `regimen_renta_codigo`
  - `responsabilidades_rut_codigos`
  - `actividad_economica`

- Los campos canónicos mantenidos son:
  - `razon_social`
  - `nit`
  - `dv`
  - `direccion`
  - `telefono`
  - `email_contacto`
  - `regimen_tributario`
  - `logo`
  - `website`
  - `moneda`

---

## 🚀 Próximos Pasos (Opcional)

Si se requiere agregar FK a Empresa en otras apps de negocio:
1. Crear migración para agregar FK (nullable)
2. Crear data migration para backfill
3. (Opcional) Migración para hacer FK not null

Apps candidatas:
- `clientes.Cliente`
- `proveedores.Proveedor`
- `gastos.Gasto`
- `facturas.Factura`
- `contabilidad.CuentaContable`
- `contabilidad.AsientoContable`
- `empleados.Empleado`
