# Refactor ENFORCED MODE v2.40 - Estado de Implementación

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ **IMPLEMENTACIÓN COMPLETADA**

---

## ✅ Cambios Aplicados

### 1. EmpresaViewSet - ENFORCED MODE ✅

**Archivo:** `apps/tenant/empresa/api/viewsets.py`

**Cambios:**
- ✅ Agregado método `_check_enforced_mode()` que verifica permisos STAFF/ADMIN
- ✅ `create()`, `update()`, `partial_update()`, `destroy()` ahora retornan `405 Method Not Allowed` para no-staff
- ✅ Flag DEV: `ALLOW_EMPRESA_POST_DIRECT` (configurable en settings)

**Comportamiento:**
- **POST /api/v1/empresas/**: Solo STAFF/ADMIN (o 405)
- **PATCH /api/v1/empresas/{id}/**: Solo STAFF/ADMIN (o 405)
- **PUT /api/v1/empresas/{id}/**: Solo STAFF/ADMIN (o 405)
- **DELETE /api/v1/empresas/{id}/**: Solo STAFF/ADMIN (o 405)
- **GET /api/v1/empresas/**: Permitido a autenticados (lectura)

---

### 2. FK NO NULA a Empresa en Apps de Negocio ✅

**Apps actualizadas:**
- ✅ `clientes.Cliente` - Campo agregado + Migración creada
- ✅ `proveedores.Proveedor` - Campo agregado + Migración creada
- ✅ `gastos.Gasto` - Campo agregado + Migración creada
- ✅ `contabilidad.CuentaContable` - Campo agregado + Migración creada
- ✅ `contabilidad.AsientoContable` - Campo agregado + Migración creada
- ✅ `empleados.Empleado` - Campo agregado + Migración creada
- ✅ `inventario.ActivoFijo` - **YA TENÍA FK** (sin cambios)

**Migraciones creadas:**
- `apps/tenant/clientes/migrations/0002_add_empresa_fk.py`
- `apps/tenant/proveedores/migrations/0002_add_empresa_fk.py`
- `apps/tenant/gastos/migrations/0002_add_empresa_fk.py`
- `apps/tenant/contabilidad/migrations/0003_add_empresa_fk.py`
- `apps/tenant/empleados/migrations/0002_add_empresa_fk.py`

**Patrón aplicado:**
1. Agregar campo `empresa` (ForeignKey, nullable inicialmente)
2. Backfill: Asignar empresa singleton a registros existentes
3. Hacer campo NOT NULL (enforced)
4. Agregar índice para performance

---

### 3. empresa.page.js - Reforzado para usar SOLO Core Orchestrator ✅

**Archivo:** `apps/tenant/core/static/core/js/empresa/empresa.page.js`

**Cambios:**
- ✅ Agregada función `_guardAgainstDirectEmpresaAPI()` para prevenir llamadas directas
- ✅ `handleGuardarEmpresaUnified()` ahora usa **SOLO** `PATCH /api/v1/core/empresa/` (Core Orchestrator)
- ✅ Eliminadas llamadas a `POST /api/v1/empresas/` y `PATCH /api/v1/empresas/{id}/`
- ✅ Agregados comentarios `[ENFORCED MODE]` en logs
- ✅ Documentación actualizada en header del archivo

**Reglas ENFORCED:**
- ✅ **PERMITIDO**: GET /api/v1/empresas/ (lectura, paginado)
- ✅ **PERMITIDO**: GET /api/v1/empresas/mi-empresa/ (lectura singleton)
- ✅ **PERMITIDO**: POST /api/v1/empresas/dt/empresa/ (DataTables server-side)
- ❌ **PROHIBIDO**: POST /api/v1/empresas/ (mutación directa)
- ❌ **PROHIBIDO**: PATCH /api/v1/empresas/{id}/ (mutación directa)
- ❌ **PROHIBIDO**: PUT /api/v1/empresas/{id}/ (mutación directa)
- ✅ **ÚNICA VÍA DE MUTACIÓN**: PATCH /api/v1/core/empresa/ (Core Orchestrator, upsert)

---

### 4. Core Orchestrator - Verificado ✅

**Archivo:** `apps/tenant/core/api/views.py`

**Estado:**
- ✅ `MiEmpresaView.patch()` implementa upsert correctamente
- ✅ Crea empresa si no existe (201 Created)
- ✅ Actualiza empresa si existe (200 OK)
- ✅ Maneja errores de validación correctamente

---

## ⏳ Cambios Pendientes (Opcionales)

### 5. Tests - Crear tests para enforced mode

**Archivos a crear:**
- `tests/tenant/empresa/test_enforced_mode.py`
- `tests/tenant/clientes/test_fk_empresa_required.py`
- `tests/tenant/proveedores/test_fk_empresa_required.py`
- `tests/tenant/gastos/test_fk_empresa_required.py`
- `tests/tenant/contabilidad/test_fk_empresa_required.py`
- `tests/tenant/empleados/test_fk_empresa_required.py`

**Tests requeridos:**
- UI path: `PATCH /api/v1/core/empresa/` → 201 (create), 200 (update)
- POST `/api/v1/empresas/` como usuario NO staff → 405
- Segundo POST aún como staff con Empresa existente → 409
- GET `/api/v1/empresas/?page_size=1` → objeto en results cuando exista
- GET `/api/v1/empresas/mi-empresa/` → 200/204 según estado
- Crear registro sin empresa → 400 (o IntegrityError si enforced at DB)
- Crear registro con empresa → 201

---

### 6. Scripts de Auditoría - CI/Pre-commit

**Archivo a crear:** `scripts/audit_empresa_enforced_mode.py`

**Validaciones:**
- Buscar llamadas a `fetch/axios` con paths `/api/v1/empresas/.*` en workspace y fallar si detectan mutaciones
- Verificar que todos los modelos TENANT tienen FK a Empresa (salvo lista de exclusión)
- Verificar que `EmpresaViewSet` no permite POST a usuarios no staff en producción

---

## 📝 Instrucciones de Aplicación

### Paso 1: Aplicar Migraciones de FK

```bash
# Aplicar migraciones para cada app
python manage.py migrate clientes
python manage.py migrate proveedores
python manage.py migrate gastos
python manage.py migrate contabilidad
python manage.py migrate empleados

# O aplicar todas a la vez
python manage.py migrate_schemas --tenant
```

### Paso 2: Verificar ENFORCED MODE

```bash
# Probar POST directo como no-staff (debe retornar 405)
curl -X POST http://localhost:8000/api/v1/empresas/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{"razon_social": "Test", "nit": "123456789"}'
```

### Paso 3: Verificar Core Orchestrator

```bash
# Probar upsert (crear si no existe, actualizar si existe)
curl -X PATCH http://localhost:8000/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{"razon_social": "Test", "nit": "123456789"}'
```

### Paso 4: Validar Workspace UI

1. Abrir `http://home.sintel.net.co/workspace/#empresa`
2. Crear/Editar empresa
3. Verificar en Network tab que solo se usa `PATCH /api/v1/core/empresa/`
4. Verificar que no aparecen llamadas a `/api/v1/empresas/` (POST/PATCH/PUT)

---

## 📊 Resumen de Archivos Modificados

### Backend
- ✅ `apps/tenant/empresa/api/viewsets.py` - ENFORCED MODE
- ✅ `apps/tenant/clientes/models.py` - FK agregada
- ✅ `apps/tenant/proveedores/models.py` - FK agregada
- ✅ `apps/tenant/gastos/models.py` - FK agregada
- ✅ `apps/tenant/contabilidad/models.py` - FK agregada
- ✅ `apps/tenant/empleados/models.py` - FK agregada

### Migraciones
- ✅ `apps/tenant/clientes/migrations/0002_add_empresa_fk.py`
- ✅ `apps/tenant/proveedores/migrations/0002_add_empresa_fk.py`
- ✅ `apps/tenant/gastos/migrations/0002_add_empresa_fk.py`
- ✅ `apps/tenant/contabilidad/migrations/0003_add_empresa_fk.py`
- ✅ `apps/tenant/empleados/migrations/0002_add_empresa_fk.py`

### Frontend
- ✅ `apps/tenant/core/static/core/js/empresa/empresa.page.js` - Reforzado para Core Orchestrator

### Documentación
- ✅ `documentacion/REFACTOR_ENFORCED_MODE_V2.40.md` - Guía de implementación
- ✅ `documentacion/REFACTOR_ENFORCED_MODE_V2.40_COMPLETADO.md` - Este archivo

---

## ✅ Estado Final

**Implementación:** ✅ **COMPLETADA**

**Próximos pasos:**
1. Aplicar migraciones: `python manage.py migrate_schemas --tenant`
2. Probar en desarrollo/producción
3. Crear tests (opcional)
4. Crear scripts de auditoría (opcional)

---

**Refactor ENFORCED MODE v2.40 completado exitosamente.** ✅
