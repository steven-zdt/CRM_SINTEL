# 📊 Estado de Implementación: Estándar DataTables + API + Logging

**Fecha:** 2026-01-19  
**Versión del Estándar:** 1.0

## ✅ Estado Actual

### 1. Helper Reutilizable DataTables ✅ **COMPLETADO**

- **Archivo:** `apps/shared/datatable.py`
- **Clases:** `DataTableSpec`, `DataTableServer`
- **Estado:** ✅ Creado y funcional
- **Tests:** ✅ 4/4 pasan (`tests/public/shared/test_datatable_helper.py`)

**Características del Helper:**
- ✅ Lee parámetros desde `request.data` (POST)
- ✅ Whitelist de columnas/orden (`fields_map`)
- ✅ Búsqueda global limitada a campos permitidos (`search_fields`)
- ✅ Paginación estilo DataTables `[start:start+length]`
- ✅ Contrato estándar: `{draw, recordsTotal, recordsFiltered, data}`
- ✅ Soporte para `extra_filter` (filtros adicionales por módulo)

**Dependencias Verificadas:**
```bash
✅ Helper importable: OK
✅ DataTableSpec creation: OK
✅ DataTableServer creation: OK
✅ Métodos del helper: OK
```

---

### 2. Endpoints DataTables Existentes ⚠️ **PENDIENTE MIGRACIÓN**

#### 2.1 Tenants (`/api/admin/v1/dt/tenants/`)

- **Archivo:** `apps/public/tenants/api_admin/datatables.py`
- **Método actual:** `GET` ❌ (debe ser `POST`)
- **Estado:** ⚠️ Usa implementación manual (no usa helper)
- **URLs:** `apps/public/tenants/api_admin/urls.py` línea 20
- **Tests:** `tests/public/tenants/test_datatables_tenants.py` (espera GET)

**Cambios necesarios:**
- [ ] Cambiar `def get()` → `def post()`
- [ ] Migrar a usar `DataTableServer` + `DataTableSpec`
- [ ] Crear `TenantListSerializer` con campos mínimos
- [ ] Actualizar QuerySet con `only()`/`select_related()`

#### 2.2 Impuestos (`/api/public/v1/impuestos/dt/*/`)

- **Archivo:** `apps/public/impuestos/api/datatables.py`
- **Método actual:** `GET` ❌ (debe ser `POST`)
- **Endpoints:**
  - `/dt/tipos/` (TipoImpuesto)
  - `/dt/tarifas-iva/` (TarifaIVA)
  - `/dt/conceptos-retencion/` (ConceptoRetencion)
  - `/dt/codigos-tributarios/` (CodigoTributario)
  - `/dt/actividades-economicas/` (ActividadEconomica)

**Cambios necesarios:**
- [ ] Cambiar `BaseDataTablesView.get()` → `post()`
- [ ] Migrar a usar `DataTableServer` + `DataTableSpec`
- [ ] Crear serializadores de lista (campos mínimos)
- [ ] Actualizar QuerySets con `only()`

---

### 3. Templates JavaScript ⚠️ **PENDIENTE ACTUALIZACIÓN**

#### 3.1 Tenants (`list.html`)

- **Archivo:** `apps/public/console/templates/console/pages/tenants/list.html`
- **Línea 172:** `type: "GET"` ❌ (debe ser `"POST"`)
- **Estado:** ⚠️ Ya incluye CSRF token, pero usa GET

**Cambios necesarios:**
- [ ] Cambiar `type: "GET"` → `type: "POST"`
- [ ] Verificar que CSRF token se envía correctamente en POST

#### 3.2 Impuestos (`tipos_list.html`)

- **Archivo:** `apps/public/impuestos/templates/console/pages/impuestos/tipos_list.html`
- **Línea 55:** `type: "GET"` ❌ (debe ser `"POST"`)
- **Estado:** ⚠️ Usa GET

**Cambios necesarios:**
- [ ] Cambiar `type: "GET"` → `type: "POST"`
- [ ] Verificar CSRF token

---

### 4. Tests Existentes ⚠️ **PENDIENTE ACTUALIZACIÓN**

#### 4.1 `test_datatables_tenants.py`

- **Archivo:** `tests/public/tenants/test_datatables_tenants.py`
- **Líneas:** 39, 78, 89 usan `authenticated_client.get()` ❌
- **Estado:** ⚠️ Tests esperan GET, deben actualizarse a POST

**Cambios necesarios:**
- [ ] Cambiar `get()` → `post()` en tests
- [ ] Actualizar parámetros: `data=params` (POST body)

---

### 5. Configuración DRF (Paginación) ✅ **OK**

- **Archivo:** `config/settings.py` línea 252
- **Clase:** `StandardResultsSetPagination` (PageNumberPagination)
- **Estado:** ✅ Configurado
- **Nota:** Helper DataTables usa slice `[start:start+length]` (no DRF pagination)

---

### 6. Logging ⚠️ **PENDIENTE**

#### 6.1 Desarrollo
- **Estado:** ❌ No configurado
- **Requerido:** `django.server` en WARNING

#### 6.2 Producción (Gunicorn)
- **Archivo:** `infra/docker/app/gunicorn.conf.py`
- **Estado:** ⚠️ Sin formato personalizado (access log incluye query)
- **Requerido:** `%(U)s` (path sin query), omitir `%(q)s`

---

### 7. Documentación ⚠️ **PENDIENTE**

- **Archivo:** `documentacion/arquitectura_general.md`
- **Capítulo:** "Estándar de Listados y APIs" ❌ (no existe)
- **Estado:** ⚠️ Pendiente crear capítulo con regla de arquitectura

---

## 📋 Checklist de Aplicación

### Backend (Django/DRF)

- [x] Helper `DataTableServer` creado (`apps/shared/datatable.py`)
- [x] Tests del helper pasan (4/4)
- [ ] `TenantDataTablesView` migrado a POST + helper
- [ ] `BaseDataTablesView` (impuestos) migrado a POST + helper
- [ ] Serializadores de lista creados (campos mínimos)
- [ ] QuerySets optimizados (`only()`/`select_related()`)

### Frontend (JavaScript/Templates)

- [ ] Template `list.html` (tenants) actualizado a POST
- [ ] Template `tipos_list.html` actualizado a POST
- [ ] Otros templates DataTables actualizados a POST

### Tests

- [x] Tests del helper creados y pasan
- [ ] `test_datatables_tenants.py` actualizado a POST
- [ ] Tests de impuestos actualizados a POST

### Configuración

- [x] DRF paginación configurada (aunque helper no la usa)
- [ ] Logging dev configurado (`django.server` WARNING)
- [ ] Logging prod configurado (Gunicorn sin query)

### Documentación

- [ ] Capítulo "Estándar de Listados y APIs" creado
- [ ] Regla de arquitectura documentada

---

## 🎯 Resumen de Aplicación

### ✅ Completado (1/7 secciones)
1. ✅ **Helper Reutilizable:** Creado, funcional, con tests

### ⚠️ Pendiente (6/7 secciones)
2. ⚠️ **Endpoints:** Migrar de GET → POST + usar helper
3. ⚠️ **Templates:** Cambiar `type: "GET"` → `"POST"`
4. ⚠️ **Tests:** Actualizar tests a POST
5. ⚠️ **Serializadores:** Crear serializadores mínimos
6. ⚠️ **Logging:** Configurar dev/prod
7. ⚠️ **Documentación:** Crear capítulo de estándar

---

## 📝 Notas

- El helper está **listo para usar**, pero los endpoints actuales aún no lo usan
- Los tests existentes esperan GET, deben actualizarse después de migrar endpoints
- La migración requiere cambios coordinados en backend y frontend (GET → POST)

---

**Última actualización:** 2026-01-19  
**Helper version:** 1.0  
**Estado general:** ⚠️ **Parcial (Helper listo, migración pendiente)**
