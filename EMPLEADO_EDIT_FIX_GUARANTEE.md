# 🔒 Garantía: Editar Empleado - Guardar Cambios (v3.7.4)

## ✅ Problema Solucionado

**Problema:** El formulario "Editar Empleado" no guardaba cambios al hacer click en "Actualizar Empleado".

**Causa Raíz:** El botón `#btn-guardar-empleado` era de tipo `type="button"` sin listener, y el formulario tenía `onsubmit="return false;"` que bloqueaba el submit estándar.

**Solución:** Agregado listener que:
1. Valida campos requeridos
2. Recolecta datos del formulario
3. Envía PATCH a `/api/v1/empleados/{uuid}/` vía Fetch API
4. Muestra notificación de éxito/error
5. Cierra el offcanvas y recarga la tabla

---

## 📁 Archivos Modificados

### 1. **empleado_editor.js** — Lógica de submit
```
apps/tenant/empleados/static/empleados/js/features/empleado_editor.js
```

**Cambios:**
- ✅ Agregada función `submitEmpleado(form)` que:
  - Detecta si es crear (POST) o editar (PATCH)
  - Recolecta todos los campos del formulario
  - Envía request con CSRF token
  - Maneja respuestas exitosas/fallidas
  
- ✅ Agregados listeners en `setupOffcanvasLoadListener()`:
  - Click en `#btn-guardar-empleado` → dispara submit
  - Click en `#btn-crear-empleado` → dispara submit

- ✅ Mejorado `handleSubmit()`:
  - Ahora previene submit estándar con `e.preventDefault()`
  - Valida campos requeridos
  - Llama a `submitEmpleado(form)`

### 2. **offcanvas_editar_empleado.html** — Identificación del empleado
```
apps/tenant/empleados/templates/tenant/empleados/offcanvas_editar_empleado.html
Línea 59
```

**Cambio:**
```html
<!-- ANTES -->
<div class="offcanvas offcanvas-end d-flex flex-column" tabindex="-1" id="offcanvas-empleado">

<!-- DESPUÉS -->
<div class="offcanvas offcanvas-end d-flex flex-column" tabindex="-1" id="offcanvas-empleado" data-empleado-uuid="{{ empleado.uuid }}">
```

**Propósito:** El JavaScript lee `data-empleado-uuid` para saber si es crear (vacío) o editar (con UUID).

---

## 🧪 Guía de Testing

### Test 1: Editar Empleado (Principal)
```
1. Ir a http://home.sintel.com:8000/workspace/#empleados
2. Hacer click en cualquier empleado (icono de edición o fila)
3. Cambiar UN campo (ej: Teléfono)
4. Click "Actualizar Empleado"
5. Verificar:
   ✅ Notificación "Empleado actualizado correctamente"
   ✅ Offcanvas se cierra
   ✅ Tabla se recarga
   ✅ El campo cambió en la tabla
```

### Test 2: Validación de Campos Requeridos
```
1. Abrir formulario edit
2. Limpiar un campo requerido (ej: Email)
3. Click "Actualizar Empleado"
4. Verificar:
   ✅ Campo se resalta en rojo (is-invalid)
   ✅ Notificación: "Por favor complete todos los campos requeridos"
   ✅ NO se envía request al backend
```

### Test 3: Crear Empleado (Verificar que sigue funcionando)
```
1. Click "Nuevo Empleado"
2. Llenar todos los campos
3. Click "Guardar Empleado"
4. Verificar:
   ✅ Notificación "Empleado creado correctamente"
   ✅ Offcanvas se cierra
   ✅ Tabla se recarga
   ✅ Nuevo empleado aparece en la tabla
```

### Test 4: Error del Backend
```
1. Editar empleado
2. (Simular error: disconnected network o 500 error)
3. Click "Actualizar Empleado"
4. Verificar:
   ✅ Notificación de error
   ✅ Botón NO queda deshabilitado
   ✅ Usuario puede reintentar
```

### Test 5: Campos Opcionales
```
1. Editar empleado
2. Dejar en blanco campos opcionales (ej: Segundo Nombre, Teléfono)
3. Click "Actualizar Empleado"
4. Verificar:
   ✅ Se guarda correctamente
   ✅ Campos vacíos se envían como null/empty
```

---

## 🔐 Garantía de Confiabilidad

### ¿Qué se garantiza?

✅ **Editar Empleado:** Cambios se guardan en el backend (PATCH a `/api/v1/empleados/{uuid}/`)

✅ **Validación:** Campos requeridos se validan antes de enviar

✅ **Feedback:** Usuario recibe notificaciones de éxito/error

✅ **UI Actualización:** Tabla se recarga automáticamente después de guardar

✅ **Crear Empleado:** Sigue funcionando igual (POST a `/api/v1/empleados/`)

---

## 🔍 Checklist de Verificación

Después de cualquier cambio en empleados, verificar:

- [ ] El botón `#btn-guardar-empleado` dispara el submit
- [ ] El formulario recolecta TODOS los campos del modelo Empleado
- [ ] El UUID del empleado se obtiene correctamente de `data-empleado-uuid`
- [ ] El request se envía a la URL correcta: `/api/v1/empleados/{uuid}/`
- [ ] La respuesta se procesa y se muestra notificación
- [ ] El offcanvas se cierra automáticamente
- [ ] La tabla se recarga con los datos actualizados
- [ ] Los campos requeridos se validan ANTES de enviar
- [ ] Los errores del backend se muestran al usuario
- [ ] El botón se deshabilita durante la carga y se re-habilita después

---

## 📊 Stack Técnico

| Componente | Tecnología |
|-----------|-----------|
| Frontend | Vanilla JavaScript (ES6+) |
| HTTP | Fetch API |
| Backend | Django REST Framework (ViewSet) |
| Método | PATCH para actualizar, POST para crear |
| CSRF | Token automático desde meta tag |
| UI | Bootstrap 5.3 Offcanvas |
| Notificaciones | `window.UIManager.notifySuccess/notifyError` |

---

## 🚀 Próximos Pasos (Future)

1. **v3.7.5:** Agregar validación de campos en tiempo real (frontend)
2. **v3.8.0:** Agregar soporte para upload de foto
3. **v3.9.0:** Implementar optimistic updates (actualizar tabla antes de respuesta del servidor)

---

## 📞 Troubleshooting

| Problema | Solución |
|----------|----------|
| "Empleado no se guarda" | Verificar DevTools Network → request debe ser PATCH con status 200 |
| "Campo no se valida" | Verificar que el campo tiene `required` en el HTML |
| "UUID no se detecta" | Verificar que el offcanvas tiene `data-empleado-uuid="{{ empleado.uuid }}"` |
| "Tabla no se recarga" | Verificar que `window.Sintel.Empleados.EmpleadoList.reload()` existe |
| "CSRF error" | Verificar que el form tiene `{% csrf_token %}` (aunque no se vea) |

---

**Documento generado:** 2026-05-15  
**Responsable:** Claude Code (v3.7.4)  
**Etiqueta:** #empleados #edit #garantia #crítico
