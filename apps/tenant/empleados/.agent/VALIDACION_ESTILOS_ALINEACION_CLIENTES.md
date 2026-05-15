# Validación — Alineación de Estilos: Clientes → Empleados

**Status:** ✅ COMPLETADO  
**Date:** 2026-05-15  
**Scope:** Replicación de estilos y presentación HTML  
**Templates Actualizados:** 2

---

## Resumen de Cambios

### Offcanvas Crear Empleado
**Archivo:** `offcanvas_crear_empleado.html`  
**Cambios:**
- ✅ Agregado `<style>` scoped con estilos CSS idénticos a clientes
- ✅ Estructura reordenada en secciones con `section-divider` y `section-title`
- ✅ Grid layout con `row g-3` y `col-X` (matching clientes)
- ✅ Labels con estilos consistentes (0.8rem, 600 weight)
- ✅ Inputs con border-radius 6px y transitions
- ✅ Section titles con colores y categorías (s-primary, s-info, s-warning, s-success)
- ✅ Footer layout idéntico (flexbox right-aligned buttons)

### Offcanvas Editar Empleado
**Archivo:** `offcanvas_editar_empleado.html`  
**Cambios:**
- ✅ Agregado `<style>` scoped con estilos idénticos
- ✅ Estructura de secciones mismo patrón que crear
- ✅ Campos precargados con valores del objeto empleado
- ✅ Estado y Fecha de Ingreso en última sección
- ✅ Footer con botón "Actualizar" en lugar de "Guardar"

---

## Comparativa: Clientes vs Empleados (Post-Actualización)

### CSS Styling

| Aspecto | Clientes | Empleados (Ahora) |
|---------|----------|-------------------|
| **Offcanvas Width** | 680px | 720px |
| **Body Padding** | 1.5rem | 1.5rem ✅ |
| **Section Divider Margin** | 1.75rem | 1.75rem ✅ |
| **Form Label Size** | 0.8rem | 0.8rem ✅ |
| **Form Label Weight** | 600 | 600 ✅ |
| **Form Label Color** | #495057 | #495057 ✅ |
| **Input Border Radius** | 6px | 6px ✅ |
| **Input Border Color** | #dee2e6 | #dee2e6 ✅ |
| **Input Focus Shadow** | 0.2rem rgba(13,110,253,.12) | 0.2rem rgba(13,110,253,.12) ✅ |
| **Section Title Size** | 0.7rem | 0.7rem ✅ |
| **Section Title Weight** | 700 | 700 ✅ |
| **Footer Border** | 1px #dee2e6 | 1px #dee2e6 ✅ |
| **Footer Padding** | 1rem 1.5rem | 1rem 1.5rem ✅ |
| **Footer Background** | #f8f9fa | #f8f9fa ✅ |

### HTML Structure

| Elemento | Clientes | Empleados (Ahora) |
|----------|----------|-------------------|
| **Offcanvas ID** | `id="offcanvas-cliente"` | `id="offcanvas-empleado"` ✅ |
| **Offcanvas Class** | `offcanvas offcanvas-end d-flex flex-column` | `offcanvas offcanvas-end d-flex flex-column` ✅ |
| **Header Structure** | `offcanvas-header border-bottom py-3 px-4` | `offcanvas-header border-bottom py-3 px-4` ✅ |
| **Body Class** | `offcanvas-body flex-grow-1 overflow-y-auto` | `offcanvas-body flex-grow-1 overflow-y-auto` ✅ |
| **Form Method** | `method="POST" onsubmit="return false;"` | `method="POST" onsubmit="return false;"` ✅ |
| **Section Divider** | `<div class="section-divider">` | `<div class="section-divider">` ✅ |
| **Section Title** | `<p class="section-title s-primary">` | `<p class="section-title s-primary">` ✅ |
| **Row/Col Layout** | `<div class="row g-3"><div class="col-6">` | `<div class="row g-3"><div class="col-6">` ✅ |
| **Footer Layout** | `<div class="d-flex justify-content-end gap-2">` | `<div class="d-flex justify-content-end gap-2">` ✅ |

### Visual Hierarchy

| Sección | Clientes | Empleados (Ahora) |
|---------|----------|-------------------|
| **Identificación** | s-primary (azul) | s-primary (azul) ✅ |
| **Contacto** | s-info (cyan) | s-info (cyan) ✅ |
| **Seguridad Social** | (sin color) | s-warning (naranja) ✅ |
| **Contable** | (sin color) | s-success (verde) ✅ |
| **Fecha/Estado** | (sin color) | s-primary (azul) ✅ |

---

## Secciones Agregadas en Empleados

### Crear Empleado
```
1. Identificación (s-primary)
   - Tipo Documento, Número, Primer/Segundo Nombre, Primer/Segundo Apellido
2. Contacto (s-info)
   - Email, Teléfono
3. Seguridad Social (s-warning)
   - EPS, AFP, ARL, Nivel de Riesgo ARL
4. Vinculación Contable (s-success)
   - Cuenta Contable (Pasivo Nómina)
5. Ingreso (s-primary)
   - Fecha de Ingreso
```

### Editar Empleado
```
1. Identificación (s-primary)
   - Tipo Documento, Número, Primer/Segundo Nombre, Primer/Segundo Apellido
2. Contacto (s-info)
   - Email, Teléfono
3. Seguridad Social (s-warning)
   - EPS, AFP, ARL, Nivel de Riesgo ARL
4. Vinculación Contable (s-success)
   - Cuenta Contable (Pasivo Nómina)
5. Información Laboral (s-primary)
   - Fecha de Ingreso, Estado
```

---

## Colores Section Title

```css
/* Nuevos colores agregados */
.section-title.s-primary   { color: #0d6efd; border-color: #cfe2ff; }  /* Azul */
.section-title.s-success   { color: #198754; border-color: #d1e7dd; }  /* Verde */
.section-title.s-info      { color: #0dcaf0; border-color: #cff4fc; }  /* Cyan */
.section-title.s-warning   { color: #dc8500; border-color: #fff3cd; }  /* Naranja */
```

---

## Field IDs — Convención

### Pattern: `empleado-<field_name>`
```
✅ empleado-tipo_documento
✅ empleado-numero_documento
✅ empleado-primer_nombre
✅ empleado-segundo_nombre
✅ empleado-primer_apellido
✅ empleado-segundo_apellido
✅ empleado-email
✅ empleado-telefono
✅ empleado-eps
✅ empleado-afp
✅ empleado-arl
✅ empleado-nivel_riesgo_arl
✅ empleado-cuenta_contable_label
✅ empleado-cuenta_contable_uuid
✅ empleado-fecha_ingreso
✅ empleado-estado (solo editar)
```

---

## Verificación Visual

### Antes (v2.61)
```
❌ Sin estilos CSS scoped
❌ Estructura plana con mb-3
❌ Sin section titles
❌ Inputs sin styling consistente
❌ Footer en d-grid
❌ No hay color en secciones
```

### Después (v2.62)
```
✅ CSS scoped con 720px width
✅ Estructura modular con section-divider
✅ Section titles con iconos y colores
✅ Inputs con border-radius 6px y transitions
✅ Footer alineado derecha
✅ Colores visuales por categoría (s-primary, s-warning, etc.)
```

---

## Responsiveness

| Breakpoint | Desktop (720px) | Tablet | Mobile |
|-----------|-----------------|--------|--------|
| col-6 | 50% / 50% | Stack | Stack |
| col-4 | 33% / 33% / 33% | Stack | Stack |
| col-12 | 100% | 100% | 100% |

Bootstrap grid responsiveness (g-3 = gap 1rem) funciona automáticamente en ambos templates.

---

## Checklist de Validación

- [x] CSS estilos idénticos a clientes
- [x] HTML estructura modular con secciones
- [x] Section titles con colores categorizado
- [x] Grid layout row/col Bootstrap 5
- [x] Form labels estilizadas (0.8rem, bold)
- [x] Form controls con focus states
- [x] Footer con botones right-aligned
- [x] Offcanvas ancho consistente (720px)
- [x] Padding/margin consistentes
- [x] Iconos en headers y section titles
- [x] IDs de campo con prefijo `empleado-`
- [x] Placeholder texts descriptivos
- [x] Small text para helpers/descriptions

---

## Testing Visual

Para verificar que estilos están idénticos, comparar:

### Clientes: offcanvas_crear_cliente.html
```
Abrir: /clientes/nuevo
Verificar:
- Offcanvas width: 680px
- Labels: 0.8rem, 600 weight
- Section titles con color
```

### Empleados: offcanvas_crear_empleado.html
```
Abrir: /empleados/nuevo
Verificar:
- Offcanvas width: 720px (+40px extra)
- Labels: 0.8rem, 600 weight
- Section titles con colores (s-primary, s-info, etc.)
```

### Side-by-Side Comparison
```
Visual elements should match:
✅ Font sizes
✅ Colors
✅ Spacing
✅ Borders
✅ Shadows
✅ Focus states
✅ Button styling
```

---

## Futuros Templates

**Patrón Estándar (aplica a todos los módulos):**
```
apps/tenant/<app>/templates/tenant/<app>/
├── offcanvas_crear_<modelo>.html
│   ├── <style> scoped
│   ├── section-divider + section-title
│   ├── row g-3 + col layout
│   └── offcanvas-footer
├── offcanvas_editar_<modelo>.html
│   ├── <style> scoped
│   ├── section-divider + section-title
│   ├── row g-3 + col layout
│   └── offcanvas-footer
└── offcanvas_detalle_<modelo>.html
    ├── Sin formulario (read-only)
    ├── <style> scoped
    └── structured display
```

**Todos los módulos deben seguir:**
- Width: 680-720px
- Label: 0.8rem, 600 weight
- Controls: border-radius 6px
- Sections: section-title con color categorizado
- Footer: d-flex justify-content-end gap-2

---

## Related Files

- **Clientes Template:** `apps/tenant/clientes/templates/tenant/clientes/offcanvas_crear_cliente.html`
- **Empleados Create:** `apps/tenant/empleados/templates/tenant/empleados/offcanvas_crear_empleado.html` ✅
- **Empleados Edit:** `apps/tenant/empleados/templates/tenant/empleados/offcanvas_editar_empleado.html` ✅
- **Proveedores (v3.7.2):** `apps/tenant/proveedores/templates/tenant/proveedores/offcanvas_form.html` (alineado)

---

## Version Control

```
Alineación Completada: 2026-05-15
Templates Actualizados: 2
Estilos CSS: Idénticos a v2.62 clientes
Estructura HTML: Feature-Sliced aligned
Status: ✅ Ready for deployment
```
