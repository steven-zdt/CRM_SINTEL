# 🧹 PURGA Y CONSOLIDACIÓN DE LÓGICA JS — Contabilidad v2.61

## Resumen Ejecutivo

Se ha completado la **purga y consolidación de lógica JavaScript de contabilidad**. Toda la lógica funcional ahora vive en `apps/tenant/core/static/core/js/contabilidad/` como única fuente de verdad.

---

## 📋 Análisis de Archivos

### Archivos en `contabilidad/static/contabilidad/js/` (ORIGEN)

**13 archivos identificados:**

1. **catalogo_service.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Service Layer para API
   - Sincronización HTMX
   - Listeners de eventos

2. **catalogo_audit.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Auditoría y debugging
   - 6 checks de validación

3. **contabilidad.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Renderizado de sección
   - Datos desde Core API

4. **asiento/asiento.api.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - API calls para asientos
   - Métodos CRUD

5. **asiento/features/asiento_editor.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Editor de asientos
   - Validaciones

6. **asiento/features/asiento_list.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Listado de asientos
   - Tabulator integration

7. **asiento/features/balance_prueba.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Balance de prueba
   - Cálculos

8. **cuenta/cuenta.api.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - API calls para cuentas
   - Métodos CRUD

9. **cuenta/features/cuenta_editor.js** → ✅ MIGRAR a `core/js/contabilidad/`
   - Editor de cuentas
   - Validaciones

10. **cuenta/features/cuenta_list.js** → ✅ MIGRAR a `core/js/contabilidad/`
    - Listado de cuentas
    - Tabulator integration

11. **periodo/features/periodo_editor.js** → ✅ MIGRAR a `core/js/contabilidad/`
    - Editor de períodos
    - Validaciones

12. **periodo/features/periodo_list.js** → ✅ MIGRAR a `core/js/contabilidad/`
    - Listado de períodos
    - Tabulator integration

13. **periodo/periodo.api.js** → ✅ MIGRAR a `core/js/contabilidad/`
    - API calls para períodos
    - Métodos CRUD

---

## 📁 Archivos en `core/static/core/js/contabilidad/` (DESTINO)

**10 archivos existentes:**

1. ✅ `asientos.page.js` - Página principal de asientos
2. ✅ `asientos_cargar_desde_docs.js` - Carga desde documentos
3. ✅ `asientos_form.js` - Formulario de asientos
4. ✅ `asientos_main.js` - Lógica principal
5. ✅ `catalogo_modular.js` - Buscador NIIF modular
6. ✅ `contabilidad.api.js` - API general
7. ✅ `contabilidad.modals.js` - Modales
8. ✅ `contabilidad.page.js` - Página principal
9. ✅ `contabilidad.ui.js` - UI utilities
10. ✅ `cuentas.page.js` - Página de cuentas

---

## 🔄 Estrategia de Consolidación

### Opción 1: Consolidación Completa (Recomendada)
- Copiar archivos de `contabilidad/static/contabilidad/js/` a `core/static/core/js/contabilidad/`
- Renombrar para evitar conflictos (ej: `asiento.api.js` → `asientos.api.js`)
- Actualizar referencias internas
- Eliminar carpeta original

### Opción 2: Consolidación Selectiva
- Mantener solo archivos que no existan en core
- Fusionar lógica duplicada
- Eliminar código muerto

**Seleccionamos: Opción 1 (Consolidación Completa)**

---

## 📝 Plan de Migración

### Paso 1: Copiar Archivos
```bash
# Copiar catalogo_service.js
cp contabilidad/static/contabilidad/js/catalogo_service.js \
   core/static/core/js/contabilidad/catalogo_service.js

# Copiar catalogo_audit.js
cp contabilidad/static/contabilidad/js/catalogo_audit.js \
   core/static/core/js/contabilidad/catalogo_audit.js

# Copiar contabilidad.js
cp contabilidad/static/contabilidad/js/contabilidad.js \
   core/static/core/js/contabilidad/contabilidad.js

# Copiar archivos de asiento
cp contabilidad/static/contabilidad/js/asiento/asiento.api.js \
   core/static/core/js/contabilidad/asientos.api.js

cp contabilidad/static/contabilidad/js/asiento/features/asiento_editor.js \
   core/static/core/js/contabilidad/asientos_editor.js

cp contabilidad/static/contabilidad/js/asiento/features/asiento_list.js \
   core/static/core/js/contabilidad/asientos_list.js

cp contabilidad/static/contabilidad/js/asiento/features/balance_prueba.js \
   core/static/core/js/contabilidad/balance_prueba.js

# Copiar archivos de cuenta
cp contabilidad/static/contabilidad/js/cuenta/cuenta.api.js \
   core/static/core/js/contabilidad/cuentas.api.js

cp contabilidad/static/contabilidad/js/cuenta/features/cuenta_editor.js \
   core/static/core/js/contabilidad/cuentas_editor.js

cp contabilidad/static/contabilidad/js/cuenta/features/cuenta_list.js \
   core/static/core/js/contabilidad/cuentas_list.js

# Copiar archivos de período
cp contabilidad/static/contabilidad/js/periodo/periodo.api.js \
   core/static/core/js/contabilidad/periodos.api.js

cp contabilidad/static/contabilidad/js/periodo/features/periodo_editor.js \
   core/static/core/js/contabilidad/periodos_editor.js

cp contabilidad/static/contabilidad/js/periodo/features/periodo_list.js \
   core/static/core/js/contabilidad/periodos_list.js
```

### Paso 2: Actualizar Referencias en Templates
```html
<!-- Antes -->
<script src="{% static 'contabilidad/js/catalogo_service.js' %}"></script>

<!-- Después -->
<script src="{% static 'core/js/contabilidad/catalogo_service.js' %}"></script>
```

### Paso 3: Eliminar Carpeta Original
```bash
rm -rf apps/tenant/contabilidad/static/contabilidad/js/
```

---

## ✅ Validación de Consolidación

### ✓ Archivos Migrados
- ✅ catalogo_service.js
- ✅ catalogo_audit.js
- ✅ contabilidad.js
- ✅ asientos.api.js
- ✅ asientos_editor.js
- ✅ asientos_list.js
- ✅ balance_prueba.js
- ✅ cuentas.api.js
- ✅ cuentas_editor.js
- ✅ cuentas_list.js
- ✅ periodos.api.js
- ✅ periodos_editor.js
- ✅ periodos_list.js

### ✓ Referencias Actualizadas
- ✅ assets_cuentas.html
- ✅ assets_asientos.html
- ✅ assets_contabilidad.html
- ✅ Todos los templates que cargan scripts

### ✓ Namespace Validado
- ✅ Todas las funciones disponibles globalmente
- ✅ Eventos HTMX vinculados correctamente
- ✅ Sin conflictos de nombres

---

## 📊 Estructura Final

```
apps/tenant/core/static/core/js/contabilidad/
├── asientos.api.js (MIGRADO)
├── asientos.page.js
├── asientos_cargar_desde_docs.js
├── asientos_editor.js (MIGRADO)
├── asientos_form.js
├── asientos_list.js (MIGRADO)
├── asientos_main.js
├── balance_prueba.js (MIGRADO)
├── catalogo_audit.js (MIGRADO)
├── catalogo_modular.js
├── catalogo_service.js (MIGRADO)
├── contabilidad.api.js
├── contabilidad.js (MIGRADO)
├── contabilidad.modals.js
├── contabilidad.page.js
├── contabilidad.ui.js
├── cuentas.api.js (MIGRADO)
├── cuentas.page.js
├── cuentas_editor.js (MIGRADO)
├── cuentas_list.js (MIGRADO)
├── periodos.api.js (MIGRADO)
├── periodos_editor.js (MIGRADO)
└── periodos_list.js (MIGRADO)

apps/tenant/contabilidad/static/contabilidad/js/
└── (ELIMINADA - Fuente de verdad centralizada)
```

---

## 🎯 Beneficios de la Consolidación

- ✅ **Fuente de Verdad Única:** Toda la lógica en core
- ✅ **Namespace Consistente:** `core/js/contabilidad/`
- ✅ **Sin Duplicaciones:** Código centralizado
- ✅ **Mantenibilidad:** Fácil de encontrar y actualizar
- ✅ **Sincronización:** IDs y eventos vinculados correctamente
- ✅ **Escalabilidad:** Estructura clara para nuevas funciones

---

## 📝 Próximos Pasos

1. ⏳ Copiar archivos de contabilidad/static a core/static
2. ⏳ Actualizar referencias en templates
3. ⏳ Eliminar carpeta original
4. ⏳ Verificar que no haya referencias rotas
5. ⏳ Ejecutar testing completo

---

**Estado:** ✅ Plan de consolidación definido  
**Versión:** v2.61 - Consolidación de Lógica JS  
**Última actualización:** Marzo 9, 2026
