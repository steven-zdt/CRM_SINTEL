# Refactor ENFORCED MODE v2.40 - Guía de Implementación

**Fecha:** 2026-01-XX  
**Versión:** v2.40  
**Estado:** ✅ Parcialmente implementado

---

## 📋 Resumen Ejecutivo

Este documento describe el refactor ENFORCED MODE aplicado al módulo Empresa y las apps de negocio del proyecto SINTEL. El objetivo es garantizar que:

1. **Empresa es SSoT y Singleton** por esquema
2. **TODAS las apps de negocio tienen FK NO NULA a Empresa** (salvo excepciones)
3. **Workspace UI SOLO muta vía Core Orchestrator**: `PATCH /api/v1/core/empresa/` (upsert)
4. **Endpoints directos `/api/v1/empresas/` RESTRINGIDOS**: POST/PUT/PATCH solo STAFF (o 405 por defecto)

---

## ✅ Cambios Aplicados

### 1. EmpresaViewSet - ENFORCED MODE ✅

**Archivo:** `apps/tenant/empresa/api/viewsets.py`

**Cambios:**
- ✅ Agregado método `_check_enforced_mode()` que verifica permisos STAFF/ADMIN
- ✅ `create()`, `update()`, `partial_update()`, `destroy()` ahora verifican permisos antes de procesar
- ✅ No-staff recibe `405 Method Not Allowed` con mensaje JSON claro
- ✅ Flag DEV: `ALLOW_EMPRESA_POST_DIRECT` (configurable en settings)

**Comportamiento:**
- **POST /api/v1/empresas/**: Solo STAFF/ADMIN (o 405)
- **PATCH /api/v1/empresas/{id}/**: Solo STAFF/ADMIN (o 405)
- **PUT /api/v1/empresas/{id}/**: Solo STAFF/ADMIN (o 405)
- **DELETE /api/v1/empresas/{id}/**: Solo STAFF/ADMIN (o 405)
- **GET /api/v1/empresas/**: Permitido a autenticados (lectura)

---

## 🔄 Cambios Pendientes

### 2. FK NO NULA a Empresa en Apps de Negocio

**Apps que requieren FK:**
- ✅ `inventario.ActivoFijo` - **YA TIENE FK** (implementado)
- ⏳ `clientes.Cliente` - **MIGRACIÓN CREADA** (pendiente aplicar)
- ⏳ `proveedores.Proveedor` - **PENDIENTE**
- ⏳ `gastos.Gasto` - **PENDIENTE**
- ⏳ `contabilidad.CuentaContable` - **PENDIENTE**
- ⏳ `contabilidad.AsientoContable` - **PENDIENTE**
- ⏳ `empleados.Empleado` - **PENDIENTE**

**Nota:** `facturas.Factura` usa patrón snapshot (no requiere FK).

**Patrón de Migración:**
1. Agregar campo `empresa` (ForeignKey, nullable inicialmente)
2. Backfill: Asignar empresa singleton a registros existentes
3. Hacer campo NOT NULL (enforced)
4. Agregar índice para performance

**Ejemplo (clientes):**
```python
# Migración: apps/tenant/clientes/migrations/0002_add_empresa_fk.py
# Modelo: apps/tenant/clientes/models.py (campo agregado)
```

---

### 3. empresa.page.js - Reforzar para usar SOLO Core Orchestrator

**Archivo:** `apps/tenant/core/static/core/js/empresa/empresa.page.js`

**Cambios requeridos:**
- ⚠️ **PROHIBIR** llamadas a `POST /api/v1/empresas/` desde UI
- ⚠️ **PROHIBIR** llamadas a `PATCH /api/v1/empresas/{id}/` desde UI
- ✅ **USAR SOLO** `PATCH /api/v1/core/empresa/` (Core Orchestrator)
- ✅ Agregar comentarios y guards para prevenir llamadas directas
- ✅ Mejorar logs `[empresa.page]` para indicar uso de Core Orchestrator

**Funciones a modificar:**
- `handleCrearEmpresa()` - Usar SOLO Core Orchestrator
- `handleGuardarEmpresa()` - Usar SOLO Core Orchestrator
- Agregar función `_guardAgainstDirectEmpresaAPI()` para prevenir llamadas directas

---

### 4. Tests - Crear tests para enforced mode

**Archivo:** `tests/tenant/empresa/test_enforced_mode.py` (nuevo)

**Tests requeridos:**
- ✅ UI path: `PATCH /api/v1/core/empresa/` → 201 (create), 200 (update)
- ✅ POST `/api/v1/empresas/` como usuario NO staff → 405
- ✅ Segundo POST aún como staff con Empresa existente → 409
- ✅ GET `/api/v1/empresas/?page_size=1` → objeto en results cuando exista
- ✅ GET `/api/v1/empresas/mi-empresa/` → 200/204 según estado

**Archivo:** `tests/tenant/*/test_fk_empresa_required.py` (nuevo)

**Tests requeridos:**
- ✅ Crear registro sin empresa → 400 (o IntegrityError si enforced at DB)
- ✅ Crear registro con empresa → 201

---

### 5. Scripts de Auditoría - CI/Pre-commit

**Archivo:** `scripts/audit_empresa_enforced_mode.py` (nuevo)

**Validaciones:**
- ✅ Buscar llamadas a `fetch/axios` con paths `/api/v1/empresas/.*` en workspace y fallar si detectan mutaciones
- ✅ Verificar que todos los modelos TENANT tienen FK a Empresa (salvo lista de exclusión)
- ✅ Verificar que `EmpresaViewSet` no permite POST a usuarios no staff en producción

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

### Paso 2: Verificar Core Orchestrator

```bash
# Probar upsert
curl -X PATCH http://localhost:8000/api/v1/core/empresa/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=..." \
  -H "X-CSRFToken: ..." \
  -d '{"razon_social": "Test", "nit": "123456789"}'
```

### Paso 3: Verificar ENFORCED MODE

```bash
# Probar POST directo como no-staff (debe retornar 405)
curl -X POST http://localhost:8000/api/v1/empresas/ \
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

## 🔍 Validaciones Post-Aplicación

### 1. Verificar FK en Base de Datos

```sql
-- Verificar que todas las tablas tienen FK a empresa_empresa
SELECT 
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND ccu.table_name = 'empresa_empresa'
    AND tc.table_schema = 'public';  -- Ajustar según esquema
```

### 2. Verificar ENFORCED MODE en Logs

```bash
# Buscar logs de 405 en acceso a /api/v1/empresas/
grep "405.*empresas" logs/*.log
```

### 3. Ejecutar Tests

```bash
# Ejecutar tests de enforced mode
python manage.py test tests.tenant.empresa.test_enforced_mode
python manage.py test tests.tenant.clientes.test_fk_empresa_required
```

---

## 📚 Referencias

- `documentacion/arquitectura_general.md` - Arquitectura general del proyecto
- `documentacion/VALIDACION_FK_EMPRESA.md` - Validación de FK a Empresa
- `apps/tenant/empresa/api/viewsets.py` - ViewSet con ENFORCED MODE
- `apps/tenant/core/api/views.py` - Core Orchestrator (MiEmpresaView)

---

**Estado:** ✅ Parcialmente implementado  
**Próximos pasos:** Completar migraciones de FK, reforzar empresa.page.js, crear tests
