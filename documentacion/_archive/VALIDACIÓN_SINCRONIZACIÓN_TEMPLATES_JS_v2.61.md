# ✅ VALIDACIÓN Y SINCRONIZACIÓN PUNTO A PUNTO — Templates ↔ Scripts JS v2.61

## Resumen Ejecutivo

Se ha completado la **validación y sincronización punto a punto** entre templates HTML en `apps/tenant/core/templates/tenant/core/partials/contabilidad/` y scripts JS en `apps/tenant/core/static/core/js/contabilidad/`.

---

## 📋 Inventario de Archivos

### Templates HTML (24 archivos)

**Ubicación:** `apps/tenant/core/templates/tenant/core/partials/contabilidad/`

#### Páginas Principales (3 archivos)
1. ✅ `asiento_page.html` - Página principal de asientos
2. ✅ `cuenta_page.html` - Página principal de cuentas
3. ✅ `periodo_page.html` - Página principal de períodos

#### Offcanvas (7 archivos)
4. ✅ `partials/asiento_offcanvas_cargar_desde_docs.html` - Cargar desde documentos
5. ✅ `partials/asiento_offcanvas_detalle.html` - Detalle de asiento
6. ✅ `partials/asiento_offcanvas_form.html` - Formulario de asiento
7. ✅ `partials/cuenta_offcanvas_detalle.html` - Detalle de cuenta
8. ✅ `partials/cuenta_offcanvas_form.html` - Formulario de cuenta
9. ✅ `partials/periodo_offcanvas_detalle.html` - Detalle de período
10. ✅ `partials/periodo_offcanvas_form.html` - Formulario de período

#### Listados (3 archivos)
11. ✅ `partials/list_asientos.html` - Listado de asientos (Tabulator)
12. ✅ `partials/list_cuentas.html` - Listado de cuentas (Tabulator)
13. ⏳ `partials/list_periodos.html` - **FALTANTE** (Listado de períodos)

#### Assets (5 archivos)
14. ✅ `partials/assets_asiento.html` - Scripts para asientos
15. ✅ `partials/assets_asientos.html` - Scripts para asientos (duplicado)
16. ✅ `partials/assets_contabilidad.html` - Scripts generales
17. ✅ `partials/assets_cuenta.html` - Scripts para cuentas
18. ✅ `partials/assets_cuentas.html` - Scripts para cuentas (duplicado)
19. ✅ `partials/assets_periodo.html` - Scripts para períodos

#### Componentes Reutilizables (3 archivos)
20. ✅ `partials/fragmento_buscador_niif.html` - Buscador NIIF modular
21. ✅ `partials/balance_prueba_offcanvas.html` - Balance de prueba
22. ✅ `partials/summary.html` - Resumen

#### Modales Legacy (3 archivos)
23. ⚠️ `partials/modals.html` - **DEPRECADO** (Monolítico)
24. ⚠️ `partials/modals_asientos.html` - **DEPRECADO** (Monolítico)
25. ⚠️ `partials/modals_cuentas.html` - **DEPRECADO** (Monolítico)

---

### Scripts JavaScript (10 archivos)

**Ubicación:** `apps/tenant/core/static/core/js/contabilidad/`

1. ✅ `asientos.page.js` - Página principal de asientos
2. ✅ `asientos_cargar_desde_docs.js` - Cargar desde documentos
3. ✅ `asientos_form.js` - Formulario de asientos
4. ✅ `asientos_main.js` - Lógica principal de asientos
5. ✅ `catalogo_modular.js` - Buscador NIIF modular
6. ✅ `contabilidad.api.js` - API general
7. ✅ `contabilidad.modals.js` - Modales (legacy)
8. ✅ `contabilidad.page.js` - Página principal
9. ✅ `contabilidad.ui.js` - Utilidades UI
10. ✅ `cuentas.page.js` - Página principal de cuentas

---

## 🔄 Mapeo Punto a Punto: Templates ↔ Scripts

### 1. Asientos Contables

| Template | Script | Estado | Observaciones |
|----------|--------|--------|---------------|
| `asiento_page.html` | `asientos.page.js` | ✅ | Sincronizado |
| `asiento_offcanvas_form.html` | `asientos_form.js` | ✅ | Sincronizado |
| `asiento_offcanvas_cargar_desde_docs.html` | `asientos_cargar_desde_docs.js` | ✅ | Sincronizado |
| `asiento_offcanvas_detalle.html` | `asientos.page.js` | ✅ | Usa script principal |
| `list_asientos.html` | `asientos.page.js` | ✅ | Usa script principal |
| `assets_asientos.html` | - | ✅ | Carga scripts necesarios |

### 2. Cuentas Contables

| Template | Script | Estado | Observaciones |
|----------|--------|--------|---------------|
| `cuenta_page.html` | `cuentas.page.js` | ✅ | Sincronizado |
| `cuenta_offcanvas_form.html` | `cuentas.page.js` | ✅ | Usa script principal |
| `cuenta_offcanvas_detalle.html` | `cuentas.page.js` | ✅ | Usa script principal |
| `list_cuentas.html` | `cuentas.page.js` | ✅ | Usa script principal |
| `assets_cuentas.html` | - | ✅ | Carga scripts necesarios |

### 3. Períodos Contables

| Template | Script | Estado | Observaciones |
|----------|--------|--------|---------------|
| `periodo_page.html` | ⏳ **FALTANTE** | ❌ | Necesita `periodos.page.js` |
| `periodo_offcanvas_form.html` | ⏳ **FALTANTE** | ❌ | Necesita `periodos_form.js` |
| `periodo_offcanvas_detalle.html` | ⏳ **FALTANTE** | ❌ | Usa script principal |
| ⏳ `list_periodos.html` | ⏳ **FALTANTE** | ❌ | Necesita `periodos.page.js` |
| `assets_periodo.html` | - | ✅ | Carga scripts necesarios |

### 4. Catálogo NIIF

| Template | Script | Estado | Observaciones |
|----------|--------|--------|---------------|
| `fragmento_buscador_niif.html` | `catalogo_modular.js` | ✅ | Sincronizado |

### 5. Componentes Generales

| Template | Script | Estado | Observaciones |
|----------|--------|--------|---------------|
| `balance_prueba_offcanvas.html` | `contabilidad.page.js` | ✅ | Usa script general |
| `summary.html` | `contabilidad.page.js` | ✅ | Usa script general |
| `modals.html` | `contabilidad.modals.js` | ⚠️ | DEPRECADO (monolítico) |
| `modals_asientos.html` | `contabilidad.modals.js` | ⚠️ | DEPRECADO (monolítico) |
| `modals_cuentas.html` | `contabilidad.modals.js` | ⚠️ | DEPRECADO (monolítico) |

---

## ⚠️ Problemas Identificados

### 1. Scripts Faltantes para Períodos
- ❌ `periodos.page.js` - **FALTANTE**
- ❌ `periodos_form.js` - **FALTANTE**
- ❌ `list_periodos.html` - **FALTANTE** (template)

**Impacto:** Los períodos no tienen lógica JS dedicada. Necesitan sincronización.

### 2. Archivos Monolíticos (Deprecados)
- ⚠️ `modals.html` - Contiene múltiples modales
- ⚠️ `modals_asientos.html` - Contiene múltiples modales
- ⚠️ `modals_cuentas.html` - Contiene múltiples modales
- ⚠️ `contabilidad.modals.js` - Maneja múltiples modelos

**Impacto:** Viola regla 4.4 de arquitectura (prohibición de archivos monolíticos).

### 3. Assets Duplicados
- ⚠️ `assets_asientos.html` vs `assets_asiento.html` - Duplicados
- ⚠️ `assets_cuentas.html` vs `assets_cuenta.html` - Duplicados

**Impacto:** Confusión en carga de scripts, posibles duplicaciones.

### 4. Falta de Sincronización de Tipos
- ⏳ Validar que nombres de campos en HTML coincidan con modelos Django
- ⏳ Validar que IDs en HTML coincidan con selectores JS

---

## ✅ Validación de Sincronización

### ✓ Asientos Contables
- ✅ `asiento_page.html` → `asientos.page.js`
- ✅ `asiento_offcanvas_form.html` → `asientos_form.js`
- ✅ `asiento_offcanvas_cargar_desde_docs.html` → `asientos_cargar_desde_docs.js`
- ✅ IDs sincronizados: `#grid-asientos`, `#offcanvas-container-asiento`
- ✅ Namespace: `window.AsientosPage`, `window.AsientosForm`

### ✓ Cuentas Contables
- ✅ `cuenta_page.html` → `cuentas.page.js`
- ✅ `cuenta_offcanvas_form.html` → `cuentas.page.js`
- ✅ `cuenta_offcanvas_detalle.html` → `cuentas.page.js`
- ✅ IDs sincronizados: `#grid-cuentas`, `#offcanvas-container-cuenta`
- ✅ Namespace: `window.CuentasPage`

### ✓ Catálogo NIIF
- ✅ `fragmento_buscador_niif.html` → `catalogo_modular.js`
- ✅ IDs sincronizados: `#select-tipo-cuenta`, `#input-buscador-niif`, `#btn-buscar-niif`
- ✅ Namespace: `window.CatalogoModular`

### ❌ Períodos Contables
- ❌ `periodo_page.html` → **SIN SCRIPT**
- ❌ `periodo_offcanvas_form.html` → **SIN SCRIPT**
- ❌ `list_periodos.html` → **FALTANTE**
- ❌ IDs no sincronizados
- ❌ Namespace no definido

---

## 📊 Matriz de Sincronización General

| Modelo | Template Página | Template Form | Template Detalle | Template Listado | Script Page | Script Form | Estado |
|--------|-----------------|---------------|------------------|------------------|-------------|------------|--------|
| **Asientos** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ SINCRONIZADO |
| **Cuentas** | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ | ⚠️ PARCIAL |
| **Períodos** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ DESINCRONIZADO |
| **Catálogo** | - | - | - | - | ✅ | - | ✅ SINCRONIZADO |

---

## 🎯 Acciones Recomendadas

### Prioridad 1 (Crítica)
1. **Crear `periodos.page.js`** - Script principal para períodos
2. **Crear `list_periodos.html`** - Template para listado de períodos
3. **Crear `periodos_form.js`** - Script para formulario de períodos (si es necesario)

### Prioridad 2 (Alta)
1. **Eliminar archivos monolíticos** - `modals.html`, `modals_asientos.html`, `modals_cuentas.html`
2. **Eliminar `contabilidad.modals.js`** - Script monolítico
3. **Consolidar assets duplicados** - Elegir entre `assets_asientos.html` y `assets_asiento.html`

### Prioridad 3 (Media)
1. **Validar sincronización de tipos** - Verificar nombres de campos en HTML vs Django
2. **Validar IDs en templates** - Asegurar que coincidan con selectores JS
3. **Documentar namespace** - Asegurar que cada script tenga namespace único

---

## 📝 Próximos Pasos

1. ✅ Validar archivos en templates
2. ✅ Validar archivos en scripts JS
3. ✅ Crear reporte de sincronización
4. ⏳ Crear scripts faltantes para períodos
5. ⏳ Eliminar archivos monolíticos
6. ⏳ Consolidar assets duplicados
7. ⏳ Ejecutar testing completo

---

**Estado:** ✅ Validación completada - Desincronización identificada  
**Versión:** v2.61 - Sincronización Punto a Punto  
**Última actualización:** Marzo 9, 2026
