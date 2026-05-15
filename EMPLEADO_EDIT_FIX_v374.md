# 🔧 Fix: Editar Empleado - Guardar Cambios (v3.7.4 Hotfix)

## ✅ Problema Resuelto

**Errores 400/500 al guardar empleado:**
- "Bad Request" (400) en POST/PATCH
- "Internal Server Error" (500) en create
- Campos requeridos faltantes en request

**Causa:** Serializer requería campos que JavaScript no estaba enviando:
- `eps`, `afp`, `arl`, `nivel_riesgo_arl` (Seguridad Social)
- `estado`, `fecha_ingreso` (Información Laboral)

---

## 🔨 Solución Implementada

### 1. Recolectar TODOS los campos en `submitEmpleado()`

**Antes (Incompleto):**
```javascript
const data = {
    tipo_documento: form.querySelector('[name="tipo_documento"]')?.value,
    // ... solo algunos campos
    riesgo_arl: form.querySelector('[name="riesgo_arl"]')?.value,  // ❌ FALTA
    estado: form.querySelector('[name="estado"]')?.value,  // ❌ FALTA
};
```

**Después (Completo):**
```javascript
const data = {
    // ── Identificación ──
    tipo_documento: form.querySelector('[name="tipo_documento"]')?.value || '',
    numero_documento: form.querySelector('[name="numero_documento"]')?.value || '',
    // ... más campos

    // ── Seguridad Social (REQUERIDOS) ──
    eps: form.querySelector('[name="eps"]')?.value || '',
    afp: form.querySelector('[name="afp"]')?.value || '',
    arl: form.querySelector('[name="arl"]')?.value || '',
    nivel_riesgo_arl: form.querySelector('[name="nivel_riesgo_arl"]')?.value || 'I',

    // ── Información Laboral ──
    fecha_ingreso: form.querySelector('[name="fecha_ingreso"]')?.value || '',
    estado: form.querySelector('[name="estado"]')?.value || 'ACTIVO',
    fecha_retiro: form.querySelector('[name="fecha_retiro"]')?.value || null,
};
```

**Cambio clave:** Ahora recolecta TODOS los campos del serializer.

### 2. Mejorar manejo de errores de validación

**Antes:** Mostraba error genérico sin detalles
```javascript
const errorMsg = errorData.error || errorData.detail || 'Error al guardar el empleado';
```

**Después:** Parsea errores de campo y los muestra
```javascript
const fieldErrors = Object.entries(errorData)
    .map(([field, msgs]) => {
        const message = Array.isArray(msgs) ? msgs[0] : msgs;
        return `${field}: ${message}`;
    })
    .join('\n');
```

**Ejemplo de respuesta al usuario:**
```
Error: 
eps: This field is required.
estado: This field is required.
fecha_ingreso: This field is required.
```

---

## 🧪 Testing Recomendado

### Test 1: Crear Empleado (Principal)
```
1. Ir a http://home.sintel.com:8000/workspace/#empleados
2. Click "Nuevo Empleado"
3. Llenar TODOS los campos:
   ✅ Identificación (tipo_documento, numero_documento, nombres, apellidos)
   ✅ Contacto (email, telefono)
   ✅ Seguridad Social (eps, afp, arl, nivel_riesgo_arl)
   ✅ Información Laboral (fecha_ingreso, estado)
4. Click "Guardar Empleado"
5. Verificar:
   ✅ Notificación "Empleado creado correctamente" (SIN ERRORES)
   ✅ Offcanvas se cierra
   ✅ Tabla se recarga con el nuevo empleado
```

### Test 2: Editar Empleado
```
1. Click en un empleado (icono editar)
2. Cambiar UN campo (ej: Teléfono)
3. Click "Actualizar Empleado"
4. Verificar:
   ✅ Notificación "Empleado actualizado correctamente" (SIN ERRORES)
   ✅ Offcanvas se cierra
   ✅ Tabla se recarga
```

### Test 3: Validación en Tiempo Real
```
1. Abrir crear/editar empleado
2. Dejar en blanco un campo REQUERIDO (ej: email)
3. Click guardar
4. Verificar:
   ✅ Campo se resalta en rojo
   ✅ Notificación: "Por favor complete todos los campos requeridos"
   ✅ NO se envía request al backend
```

### Test 4: Error del Backend (Opcional)
```
1. Abrir DevTools Network
2. Crear empleado con documento duplicado
3. Verificar respuesta:
   ✅ Status 400 con detalle del error
   ✅ Mensaje parseable: "numero_documento: Already exists"
```

---

## 🔍 Checklist Post-Fix

- [x] submitEmpleado() recolecta TODOS los campos
- [x] Campos opcionales tienen default o null correcto
- [x] Seguridad Social (eps, afp, arl) se envían
- [x] Información Laboral (estado, fecha_ingreso) se envían
- [x] Errores de validación se parsean y muestran
- [x] CSRF token se incluye en headers
- [x] URL de endpoint es correcta (POST create, PATCH update)
- [x] Offcanvas se cierra automáticamente
- [x] Tabla se recarga al guardar

---

## 📊 Campos del Serializer EmpleadoDetailSerializer

| Campo | Tipo | Requerido | Default |
|-------|------|-----------|---------|
| `tipo_documento` | choice | ✅ | - |
| `numero_documento` | string | ✅ | - |
| `primer_nombre` | string | ✅ | - |
| `segundo_nombre` | string | ❌ | blank |
| `primer_apellido` | string | ✅ | - |
| `segundo_apellido` | string | ❌ | blank |
| `email` | email | ✅ | - |
| `telefono` | string | ❌ | blank |
| `eps` | choice | ✅ | - |
| `afp` | choice | ✅ | - |
| `arl` | choice | ✅ | - |
| `nivel_riesgo_arl` | choice | ❌ | `I` |
| `estado` | choice | ✅ | `ACTIVO` |
| `fecha_ingreso` | date | ✅ | - |
| `fecha_retiro` | date | ❌ | null |
| `cuenta_contable_uuid` | uuid | ❌ | null |

---

## 🚀 Próximos Pasos (v3.7.5+)

1. **Validación en tiempo real** de campos
2. **Preseleccionar valores por defecto** (nivel_riesgo_arl='I', estado='ACTIVO')
3. **Agregar helper tooltips** para campos complejos (EPS choices, ARL choices)
4. **Implementar optimistic updates** (actualizar tabla antes de respuesta)

---

**Documento:** Fix hotfix v3.7.4 (2026-05-15)  
**Cambio crítico:** Recolección completa de campos + mejor error parsing  
**Estado:** ✅ Listo para testing

