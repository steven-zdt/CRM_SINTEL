# 🧹 PURGA DE CÓDIGO REDUNDANTE Y ALINEACIÓN API-JS — v2.61

## Resumen Ejecutivo

Se ha completado el análisis de **purga de código redundante y alineación API-JS**. Se identificaron redundancias, endpoints sin consumidor JS, y código muerto. Se proporciona plan quirúrgico de limpieza.

---

## 📊 Análisis de Redundancias Identificadas

### 1. Validaciones Duplicadas en API vs Services

**Ubicación:** `apps/tenant/contabilidad/api/viewsets.py` vs `apps/tenant/contabilidad/services/`

**Problema:**
- ViewSet `CuentaContableViewSet.create()` (línea 131-162) valida y delega a `create_cuenta()`
- ViewSet `AsientoContableViewSet.create()` (línea 467-501) valida y delega a `create_asiento()`
- Pero también hay validaciones en `cuentas_service.py` y `asientos_service.py`

**Redundancia:**
```python
# En viewsets.py (línea 141-143)
try:
    data = request.data.copy()
    resultado = create_cuenta(data)  # ← Service también valida

# En services/cuentas_service.py
def create_cuenta(data):
    # Validaciones redundantes aquí
    codigo = (data.get('codigo') or '').strip()
    nombre = (data.get('nombre') or '').strip()
    tipo = (data.get('tipo') or '').strip()
```

**Acción:** Mover todas las validaciones a `services/` y dejar ViewSet limpio (solo delegación).

### 2. Endpoints sin Consumidor JS

**Endpoints Identificados:**

| Endpoint | ViewSet | Consumidor JS | Estado |
|----------|---------|---------------|--------|
| `POST /api/v1/contabilidad/cuentas-contables/` | create() | ✅ cuentas.page.js | ✅ |
| `PATCH /api/v1/contabilidad/cuentas-contables/{id}/` | update() | ✅ cuentas.page.js | ✅ |
| `DELETE /api/v1/contabilidad/cuentas-contables/{id}/` | destroy() | ✅ cuentas.page.js | ✅ |
| `POST /api/v1/contabilidad/cuentas-contables/dt/cuentas-contables` | datatables() | ⚠️ DataTables legacy | ⚠️ DEPRECADO |
| `POST /api/v1/contabilidad/asientos-contables/` | create() | ✅ asientos.page.js | ✅ |
| `PATCH /api/v1/contabilidad/asientos-contables/{id}/` | update() | ✅ asientos.page.js | ✅ |
| `DELETE /api/v1/contabilidad/asientos-contables/{id}/` | destroy() | ✅ asientos.page.js | ✅ |
| `POST /api/v1/contabilidad/asientos-contables/dt/asientos-contables` | datatables() | ⚠️ DataTables legacy | ⚠️ DEPRECADO |
| `POST /api/v1/contabilidad/asientos-contables/aprobar/` | aprobar() | ⏳ FALTANTE | ❌ |
| `GET /api/v1/contabilidad/asientos-contables/balance-prueba/` | balance_prueba() | ⏳ FALTANTE | ❌ |
| `GET /api/v1/contabilidad/asientos-contables/documentos-sin-asiento/` | documentos_sin_asiento() | ✅ asientos_cargar_desde_docs.js | ✅ |
| `POST /api/v1/contabilidad/asientos-contables/crear-desde-documentos/` | crear_desde_documentos() | ✅ asientos_cargar_desde_docs.js | ✅ |
| `POST /api/v1/contabilidad/asientos-contables/importar-desde-excel/` | importar_desde_excel() | ⏳ FALTANTE | ❌ |
| `GET /api/v1/contabilidad/catalogo-maestro/` | list() | ✅ catalogo_modular.js | ✅ |
| `GET /api/v1/contabilidad/catalogo-maestro/?search=` | list() | ✅ catalogo_modular.js | ✅ |

**Endpoints Deprecados (DataTables Legacy):**
- `POST /api/v1/contabilidad/cuentas-contables/dt/cuentas-contables` - Reemplazado por Tabulator
- `POST /api/v1/contabilidad/asientos-contables/dt/asientos-contables` - Reemplazado por Tabulator

**Endpoints sin Consumidor JS:**
- `POST /api/v1/contabilidad/asientos-contables/importar-desde-excel/` - Necesita JS
- `POST /api/v1/contabilidad/asientos-contables/aprobar/` - Necesita JS
- `GET /api/v1/contabilidad/asientos-contables/balance-prueba/` - Necesita JS

### 3. Scripts JS Huérfanos

**Análisis de Scripts en `apps/tenant/core/static/core/js/contabilidad/`:**

| Script | Consumidor HTML | Estado |
|--------|-----------------|--------|
| `asientos.page.js` | `asiento_page.html` | ✅ |
| `asientos_form.js` | `asiento_offcanvas_form.html` | ✅ |
| `asientos_cargar_desde_docs.js` | `asiento_offcanvas_cargar_desde_docs.html` | ✅ |
| `asientos_main.js` | ⏳ FALTANTE | ❌ HUÉRFANO |
| `cuentas.page.js` | `cuenta_page.html` | ✅ |
| `periodos.page.js` | `periodo_page.html` | ✅ |
| `periodos_form.js` | `periodo_offcanvas_form.html` | ✅ |
| `catalogo_modular.js` | `fragmento_buscador_niif.html` | ✅ |
| `contabilidad.api.js` | ⏳ FALTANTE | ❌ HUÉRFANO |
| `contabilidad.modals.js` | `modals.html` (deprecado) | ⚠️ DEPRECADO |
| `contabilidad.page.js` | `contabilidad_page.html` | ⏳ VERIFICAR |
| `contabilidad.ui.js` | ⏳ FALTANTE | ❌ HUÉRFANO |

**Scripts Huérfanos:**
- `asientos_main.js` - No tiene consumidor HTML
- `contabilidad.api.js` - No tiene consumidor HTML
- `contabilidad.ui.js` - No tiene consumidor HTML

### 4. Código Muerto Identificado

**En `viewsets.py`:**
- Línea 1076: `MovimientoContable.objects.all()` - Viola regla de `.only()`
- Línea 250-355: Endpoint `datatables()` para cuentas - DataTables legacy (deprecado)
- Línea 590-691: Endpoint `datatables()` para asientos - DataTables legacy (deprecado)

**En `services.py`:**
- Línea 37-43: Importaciones no usadas (verificar)

---

## 🎯 Plan de Purga Quirúrgica

### Fase 1: Limpieza de Validaciones (CRÍTICA)

**Acción 1.1:** Mover todas las validaciones a `services/`
```python
# Antes (en viewsets.py)
def create(self, request, *args, **kwargs):
    try:
        data = request.data.copy()
        resultado = create_cuenta(data)  # Service valida

# Después (en viewsets.py)
def create(self, request, *args, **kwargs):
    ok, reason = self._check_enforced_mode(request)
    if not ok:
        return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    resultado = create_cuenta(request.data.copy())  # Service valida TODO
    # Serializar y retornar
```

**Acción 1.2:** Consolidar validaciones en `services/cuentas_service.py`
- Mover validación de `codigo`, `nombre`, `tipo` a función `_validate_cuenta_data()`
- Mover validación de `tipo` a función `_validate_tipo_cuenta()`
- Reutilizar en `create_cuenta()` y `update_cuenta()`

### Fase 2: Eliminar Endpoints Deprecados (ALTA)

**Acción 2.1:** Eliminar endpoints DataTables legacy
- ❌ Eliminar `CuentaContableViewSet.datatables()` (línea 250-355)
- ❌ Eliminar `AsientoContableViewSet.datatables()` (línea 590-691)
- ✅ Reemplazados por Tabulator en `asientos.page.js` y `cuentas.page.js`

**Acción 2.2:** Eliminar `contabilidad.modals.js`
- ❌ Eliminar archivo `apps/tenant/core/static/core/js/contabilidad/contabilidad.modals.js`
- ❌ Eliminar templates: `modals.html`, `modals_asientos.html`, `modals_cuentas.html`
- ✅ Reemplazados por offcanvas HTMX

### Fase 3: Eliminar Scripts Huérfanos (MEDIA)

**Acción 3.1:** Eliminar scripts sin consumidor HTML
- ❌ `asientos_main.js` - No tiene consumidor HTML
- ❌ `contabilidad.api.js` - No tiene consumidor HTML
- ❌ `contabilidad.ui.js` - No tiene consumidor HTML

**Verificar antes de eliminar:**
- Buscar referencias en otros scripts
- Buscar referencias en templates
- Buscar referencias en `assets_*.html`

### Fase 4: Consolidar Lógica de Búsqueda (MEDIA)

**Acción 4.1:** Centralizar búsqueda en `catalogo_modular.js`
- Consolidar lógica de búsqueda NIIF
- Eliminar búsqueda duplicada en otros scripts
- Usar `window.CatalogoModular.buscar()` desde otros módulos

### Fase 5: Eliminar Código Muerto (BAJA)

**Acción 5.1:** Limpiar `viewsets.py`
- ❌ Línea 1076: Cambiar `MovimientoContable.objects.all()` a `.only()`
- ❌ Eliminar comentarios innecesarios
- ❌ Eliminar `print()` statements (si existen)

**Acción 5.2:** Limpiar `services.py`
- ❌ Eliminar importaciones no usadas
- ❌ Eliminar funciones comentadas
- ❌ Eliminar `try-except` vacíos

---

## ✅ Validación de Alineación API-JS

### Mapeo Actual (Después de Purga)

```
JS Script                    → HTML Template                      → API Endpoint
─────────────────────────────────────────────────────────────────────────────────
asientos.page.js            → asiento_page.html                  → GET /asientos/
asientos_form.js            → asiento_offcanvas_form.html        → POST/PATCH /asientos/
asientos_cargar_desde_docs.js → asiento_offcanvas_cargar_desde_docs.html → GET /documentos-sin-asiento/
cuentas.page.js             → cuenta_page.html                   → GET /cuentas/
periodos.page.js            → periodo_page.html                  → GET /periodos/
periodos_form.js            → periodo_offcanvas_form.html        → POST/PATCH /periodos/
catalogo_modular.js         → fragmento_buscador_niif.html       → GET /catalogo-maestro/
```

### Endpoints Necesarios (Después de Purga)

**CRUD Básico:**
- ✅ `GET /api/v1/contabilidad/cuentas-contables/` - List
- ✅ `POST /api/v1/contabilidad/cuentas-contables/` - Create
- ✅ `PATCH /api/v1/contabilidad/cuentas-contables/{id}/` - Update
- ✅ `DELETE /api/v1/contabilidad/cuentas-contables/{id}/` - Delete
- ✅ `GET /api/v1/contabilidad/asientos-contables/` - List
- ✅ `POST /api/v1/contabilidad/asientos-contables/` - Create
- ✅ `PATCH /api/v1/contabilidad/asientos-contables/{id}/` - Update
- ✅ `DELETE /api/v1/contabilidad/asientos-contables/{id}/` - Delete

**Acciones Específicas:**
- ✅ `GET /api/v1/contabilidad/asientos-contables/documentos-sin-asiento/` - Cargar desde docs
- ✅ `POST /api/v1/contabilidad/asientos-contables/crear-desde-documentos/` - Crear desde docs
- ✅ `GET /api/v1/contabilidad/catalogo-maestro/` - Búsqueda NIIF

**Endpoints a Crear (Consumidor JS Faltante):**
- ⏳ `POST /api/v1/contabilidad/asientos-contables/{id}/aprobar/` - Necesita JS
- ⏳ `GET /api/v1/contabilidad/asientos-contables/balance-prueba/` - Necesita JS
- ⏳ `POST /api/v1/contabilidad/asientos-contables/importar-desde-excel/` - Necesita JS

---

## 📋 Checklist de Purga

### Fase 1: Limpieza de Validaciones
- [ ] Crear función `_validate_cuenta_data()` en `cuentas_service.py`
- [ ] Crear función `_validate_tipo_cuenta()` en `cuentas_service.py`
- [ ] Mover validaciones de `create_cuenta()` a funciones auxiliares
- [ ] Mover validaciones de `update_cuenta()` a funciones auxiliares
- [ ] Limpiar `viewsets.py` - dejar solo delegación

### Fase 2: Eliminar Endpoints Deprecados
- [ ] Eliminar `CuentaContableViewSet.datatables()`
- [ ] Eliminar `AsientoContableViewSet.datatables()`
- [ ] Eliminar `contabilidad.modals.js`
- [ ] Eliminar `modals.html`, `modals_asientos.html`, `modals_cuentas.html`

### Fase 3: Eliminar Scripts Huérfanos
- [ ] Verificar referencias de `asientos_main.js`
- [ ] Verificar referencias de `contabilidad.api.js`
- [ ] Verificar referencias de `contabilidad.ui.js`
- [ ] Eliminar scripts huérfanos

### Fase 4: Consolidar Lógica de Búsqueda
- [ ] Centralizar búsqueda NIIF en `catalogo_modular.js`
- [ ] Eliminar búsqueda duplicada en otros scripts

### Fase 5: Eliminar Código Muerto
- [ ] Limpiar `viewsets.py` - eliminar comentarios
- [ ] Limpiar `services.py` - eliminar importaciones no usadas
- [ ] Limpiar `services.py` - eliminar funciones comentadas

---

## 📊 Impacto de la Purga

| Métrica | Antes | Después | Reducción |
|---------|-------|---------|-----------|
| **Líneas en viewsets.py** | 1148 | ~800 | -30% |
| **Endpoints DataTables** | 2 | 0 | -100% |
| **Scripts Huérfanos** | 3 | 0 | -100% |
| **Archivos Monolíticos** | 4 | 0 | -100% |
| **Validaciones Duplicadas** | Sí | No | -100% |

---

## 🎉 Resultado Esperado

**Después de la purga:**
- ✅ API limpia - solo delegación a services
- ✅ Services consolidados - toda la lógica centralizada
- ✅ JS modular - cada script tiene consumidor HTML
- ✅ Endpoints alineados - cada endpoint tiene consumidor JS
- ✅ Código muerto eliminado - sin comentarios, prints, try-except vacíos
- ✅ Flujo único: JS → API → Service → DB

---

**Estado:** ✅ Análisis completado - Plan de purga definido  
**Versión:** v2.61 - Purga de Código Redundante  
**Última actualización:** Marzo 9, 2026
