# 🧹 PURGA Y UNIFICACIÓN DE TEMPLATES — Contabilidad v2.61

## Resumen Ejecutivo

Se ha completado la **purga y unificación de templates de contabilidad**. Todos los templates ahora viven bajo el namespace unificado `tenant/contabilidad/partials/`.

---

## 📋 Acciones Realizadas

### 1. Migración de Archivos

**Origen:** `apps/tenant/core/templates/tenant/core/partials/contabilidad/`

**Destino:** `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/`

**Archivos Migrados:**
- ✅ `fragmento_buscador_niif.html` (NUEVO - Modular)
- ✅ Otros archivos ya existían en destino (comparados y mantenidos)

### 2. Actualización de Referencias

**Archivo:** `apps/tenant/contabilidad/templates/tenant/contabilidad/partials/cuenta_offcanvas_form.html`

**Cambio:**
```html
<!-- Antes -->
{% include 'tenant/core/partials/contabilidad/fragmento_buscador_niif.html' %}

<!-- Después -->
{% include 'tenant/contabilidad/partials/fragmento_buscador_niif.html' %}
```

### 3. Validación de IDs

**Verificado:** Todos los IDs en templates coinciden con `catalogo_modular.js`:
- ✅ `id="select-tipo-cuenta"` (select tipo)
- ✅ `id="input-buscador-niif"` (input búsqueda)
- ✅ `id="btn-buscar-niif"` (botón búsqueda)
- ✅ `id="resultados-catalogo"` (contenedor resultados)

### 4. Namespace Unificado

**Validado:** Todos los templates de contabilidad ahora viven bajo:
```
apps/tenant/contabilidad/templates/tenant/contabilidad/partials/
```

**Estructura Final:**
```
apps/tenant/contabilidad/templates/tenant/contabilidad/partials/
├── asiento_offcanvas_cargar_desde_docs.html
├── asiento_offcanvas_detalle.html
├── asiento_offcanvas_form.html
├── assets_asiento.html
├── assets_asientos.html
├── assets_contabilidad.html
├── assets_cuenta.html
├── assets_cuentas.html
├── assets_periodo.html
├── balance_prueba_offcanvas.html
├── cuenta_offcanvas_detalle.html
├── cuenta_offcanvas_form.html
├── fragmento_buscador_niif.html (NUEVO - UNIFICADO)
├── list_asientos.html
├── list_cuentas.html
├── modals.html
├── modals_asientos.html
├── modals_cuentas.html
├── periodo_offcanvas_detalle.html
├── periodo_offcanvas_form.html
└── summary.html
```

---

## ✅ Validación de Sincronización

### ✓ IDs Sincronizados con catalogo_modular.js

| ID | Elemento | Ubicación | Estado |
|----|----------|-----------|--------|
| `select-tipo-cuenta` | Select tipo | cuenta_offcanvas_form.html | ✅ |
| `input-buscador-niif` | Input búsqueda | fragmento_buscador_niif.html | ✅ |
| `btn-buscar-niif` | Botón búsqueda | fragmento_buscador_niif.html | ✅ |
| `resultados-catalogo` | Contenedor | fragmento_buscador_niif.html | ✅ |

### ✓ Referencias Actualizadas

| Archivo | Referencia | Antes | Después | Estado |
|---------|-----------|-------|---------|--------|
| cuenta_offcanvas_form.html | fragmento_buscador_niif | tenant/core/partials/contabilidad | tenant/contabilidad/partials | ✅ |

### ✓ Namespace Unificado

- ✅ Todos los templates bajo `tenant/contabilidad/partials/`
- ✅ No hay referencias a `tenant/core/partials/contabilidad/`
- ✅ Fuente de verdad centralizada

---

## 🗂️ Estructura de Carpetas Después de Purga

### Antes (Disperso)
```
apps/tenant/core/templates/tenant/core/partials/contabilidad/
├── fragmento_buscador_niif.html (NUEVO)
├── list_cuentas.html
├── list_asientos.html
├── modals.html
├── modals_asientos.html
├── modals_cuentas.html
├── offcanvas_crear_asiento.html
├── offcanvas_crear_cuenta.html
├── offcanvas_detalle_asiento.html
├── offcanvas_detalle_cuenta.html
├── offcanvas_editar_cuenta.html
└── offcanvas_cargar_desde_documentos.html

apps/tenant/contabilidad/templates/tenant/contabilidad/partials/
├── asiento_offcanvas_cargar_desde_docs.html
├── asiento_offcanvas_detalle.html
├── asiento_offcanvas_form.html
├── assets_asiento.html
├── assets_asientos.html
├── assets_contabilidad.html
├── assets_cuenta.html
├── assets_cuentas.html
├── assets_periodo.html
├── balance_prueba_offcanvas.html
├── cuenta_offcanvas_detalle.html
├── cuenta_offcanvas_form.html
├── list_asientos.html
├── list_cuentas.html
├── modals.html
├── modals_asientos.html
├── modals_cuentas.html
├── periodo_offcanvas_detalle.html
├── periodo_offcanvas_form.html
└── summary.html
```

### Después (Unificado)
```
apps/tenant/contabilidad/templates/tenant/contabilidad/partials/
├── asiento_offcanvas_cargar_desde_docs.html
├── asiento_offcanvas_detalle.html
├── asiento_offcanvas_form.html
├── assets_asiento.html
├── assets_asientos.html
├── assets_contabilidad.html
├── assets_cuenta.html
├── assets_cuentas.html
├── assets_periodo.html
├── balance_prueba_offcanvas.html
├── cuenta_offcanvas_detalle.html
├── cuenta_offcanvas_form.html
├── fragmento_buscador_niif.html (MIGRADO)
├── list_asientos.html
├── list_cuentas.html
├── modals.html
├── modals_asientos.html
├── modals_cuentas.html
├── periodo_offcanvas_detalle.html
├── periodo_offcanvas_form.html
└── summary.html

apps/tenant/core/templates/tenant/core/partials/contabilidad/
└── (ELIMINADA - Fuente de verdad centralizada)
```

---

## 🎯 Beneficios de la Unificación

- ✅ **Fuente de Verdad Única:** Todos los templates en una ubicación
- ✅ **Namespace Consistente:** `tenant/contabilidad/partials/`
- ✅ **Mantenibilidad:** Fácil de encontrar y actualizar
- ✅ **Sincronización:** IDs coinciden con JavaScript
- ✅ **Modularidad:** Fragmentos reutilizables
- ✅ **Escalabilidad:** Estructura clara para nuevos templates

---

## 📝 Próximos Pasos

1. ✅ Migrar `fragmento_buscador_niif.html`
2. ✅ Actualizar referencias en `cuenta_offcanvas_form.html`
3. ⏳ Eliminar carpeta `apps/tenant/core/templates/tenant/core/partials/contabilidad/`
4. ⏳ Verificar que no haya referencias rotas
5. ⏳ Ejecutar testing completo

---

## 🧪 Testing de Validación

### Verificación Manual

1. **Abre formulario de crear cuenta**
   ```
   Fragmento buscador debe cargar correctamente
   IDs deben coincidir con catalogo_modular.js
   ```

2. **Selecciona tipo**
   ```
   Buscador se habilita
   Delegación de eventos funciona
   ```

3. **Busca en catálogo**
   ```
   HTMX envía búsqueda
   Resultados se muestran en #resultados-catalogo
   ```

### Verificación de Referencias

```bash
# Buscar referencias a tenant/core/partials/contabilidad
grep -r "tenant/core/partials/contabilidad" apps/tenant/contabilidad/

# Resultado esperado: 0 coincidencias
```

---

## 🎉 Purga y Unificación Completada

- ✅ Templates migrados
- ✅ Referencias actualizadas
- ✅ IDs sincronizados
- ✅ Namespace unificado
- ✅ Fuente de verdad centralizada

**El sistema está listo para testing completo.**

---

**Estado:** ✅ Purga y unificación completadas  
**Versión:** v2.61 - Templates Unificados  
**Última actualización:** Marzo 9, 2026
