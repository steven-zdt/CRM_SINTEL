# Refactorización Módulo de Cotizaciones v2.60

## 📋 Resumen Ejecutivo

Este documento describe la refactorización completa del módulo de Cotizaciones realizada en la versión 2.60, incluyendo la eliminación del campo `cliente_nombre_manual` y la simplificación del flujo de creación de cotizaciones.

**Fecha de Actualización:** 2026-01-XX  
**Versión:** 2.60  
**Estado:** ✅ Completado

---

## 🎯 Objetivos de la Refactorización

1. **Eliminación de `cliente_nombre_manual`**: Simplificar el modelo eliminando el campo de respaldo manual
2. **Obligatoriedad de Cliente de BD**: Garantizar que todas las cotizaciones estén vinculadas a un cliente existente en la base de datos
3. **Simplificación del Flujo**: Reducir la complejidad del código eliminando lógica condicional innecesaria
4. **Alineación con SSoT**: Asegurar que el cliente siempre provenga de la base de datos (Single Source of Truth)

---

## 🔄 Cambios Realizados

### 1. Modelo de Datos (`models.py`)

#### Eliminado:
- Campo `cliente_nombre_manual` del modelo `Cotizacion`
- Comentarios sobre "fallback" y "resiliencia" relacionados con nombre manual

#### Actualizado:
- `__str__()` ahora usa solo `self.cliente` o "Sin cliente"
- Comentarios actualizados para reflejar que el cliente es obligatorio

**Antes:**
```python
cliente_nombre_manual = models.CharField(max_length=255, blank=True, null=True)

def __str__(self):
    return f"{self.numero_cotizacion} - {self.cliente_nombre_manual or self.cliente}"
```

**Después:**
```python
# Campo eliminado completamente

def __str__(self):
    return f"{self.numero_cotizacion} - {self.cliente or 'Sin cliente'}"
```

---

### 2. Serializers (`api/serializers.py`)

#### Eliminado:
- Campo `cliente_nombre_manual` del `CotizacionSerializer`
- Lógica de validación condicional para nombre manual
- Referencias en `Meta.fields`
- Lógica de fallback en `get_cliente_display()`

#### Actualizado:
- `get_cliente_display()` ahora solo muestra el cliente de BD
- Validación simplificada: cliente es obligatorio
- `create()` ya no maneja `cliente_nombre_manual`

**Cambios Clave:**
```python
# ANTES: Campo opcional con fallback
cliente_nombre_manual = serializers.CharField(
    required=False,
    allow_null=True,
    allow_blank=True,
    max_length=255
)

# DESPUÉS: Campo eliminado completamente
# Solo se mantiene cliente (obligatorio)
```

---

### 3. Services (`services.py`)

#### Eliminado:
- Lógica para procesar `cliente_nombre_manual` en `crear_preforma()`
- Parámetro `cliente_nombre` del método

#### Actualizado:
- Validación estricta: cliente es obligatorio
- Mensajes de error más claros cuando falta el cliente

**Cambios Clave:**
```python
# ANTES:
cliente_nombre = datos.get('cliente_nombre_manual', '').strip()
cotizacion = Cotizacion.objects.create(
    cliente=cliente,
    cliente_nombre_manual=cliente_nombre if cliente_nombre else None,
    ...
)

# DESPUÉS:
# Cliente es obligatorio, no hay fallback
if not cliente:
    raise ValueError("Debe proporcionar un cliente de la base de datos.")
cotizacion = Cotizacion.objects.create(
    cliente=cliente,
    ...
)
```

---

### 4. ViewSets (`api/viewsets.py`)

#### Actualizado:
- Búsqueda ahora usa `cliente__razon_social__icontains` en lugar de `cliente_nombre_manual__icontains`

**Cambios Clave:**
```python
# ANTES:
queryset.filter(cliente_nombre_manual__icontains=search)

# DESPUÉS:
queryset.filter(cliente__razon_social__icontains=search)
```

---

### 5. Admin (`admin.py`)

#### Eliminado:
- `cliente_nombre_manual` de `search_fields`
- Campo del `fieldset` "Datos del Cliente"
- Lógica de fallback en `get_cliente_display()`

#### Actualizado:
- `search_fields` ahora busca en `cliente__razon_social` y `cliente__numero_documento`
- `get_cliente_display()` muestra solo el cliente de BD

---

### 6. Frontend - JavaScript (`cotizacion_modals.js`)

#### Eliminado:
- Referencias a `cliente_nombre_manual` en comentarios
- Lógica para enviar `cliente_nombre_manual` en el payload
- Referencias en `showEdit()` y `showDetail()`

#### Actualizado:
- `showEdit()` ahora muestra `cliente_display` (solo lectura)
- `showDetail()` usa solo `cliente_display`
- Payload de creación/edición simplificado

**Cambios Clave:**
```javascript
// ANTES:
formData.cliente_nombre_manual = modalElement.querySelector('#cliente_nombre_manual')?.value || '';

// DESPUÉS:
// Cliente se envía solo como ID numérico
formData.cliente = clienteIdNumero;
```

---

### 7. Frontend - Templates (`modals.html`)

#### Eliminado:
- Botón "Ingresar nombre manual"
- Contenedor `#container-cliente-manual`
- Input `#cliente_nombre_manual` del modal de creación
- Campo editable de cliente en modal de edición

#### Actualizado:
- Modal de creación: solo select de clientes (obligatorio)
- Modal de edición: campo de cliente solo lectura (muestra `cliente_display`)

**Cambios Clave:**
```html
<!-- ANTES: Campo manual opcional -->
<div id="container-cliente-manual" class="d-none">
  <input id="cliente_nombre_manual" name="cliente_nombre_manual" />
</div>

<!-- DESPUÉS: Eliminado completamente -->
<!-- Solo select de clientes de BD -->
```

---

## 📊 Impacto en el Flujo de Usuario

### Creación de Cotización

**Antes:**
1. Usuario selecciona cliente de BD (opcional)
2. Usuario puede activar "Ingresar nombre manual"
3. Sistema acepta cotización con cliente de BD o nombre manual

**Después:**
1. Usuario **debe** seleccionar cliente de BD (obligatorio)
2. No hay opción de nombre manual
3. Sistema valida que el cliente exista antes de crear

### Edición de Cotización

**Antes:**
1. Usuario puede editar nombre manual del cliente
2. Campo editable permite cambios

**Después:**
1. Cliente se muestra como solo lectura
2. No se puede cambiar el cliente (debe crear nueva cotización)

---

## 🔒 Reglas de Negocio Actualizadas

### 1. Cliente Obligatorio
- ✅ Todas las cotizaciones **deben** tener un cliente de la base de datos
- ✅ No se aceptan cotizaciones sin cliente
- ✅ Validación en frontend y backend

### 2. Integridad Referencial
- ✅ Relación FK con `Cliente` es obligatoria
- ✅ Si un cliente se elimina, la cotización mantiene la referencia (SET_NULL)
- ✅ El sistema muestra "Sin cliente" si la referencia es null

### 3. Búsqueda y Filtrado
- ✅ Búsqueda ahora se realiza sobre `cliente__razon_social`
- ✅ Búsqueda también incluye `cliente__numero_documento`
- ✅ No hay búsqueda por nombre manual (campo eliminado)

---

## 🧪 Validaciones Implementadas

### Backend (Serializer)
```python
# Cliente es obligatorio
if not cliente_id:
    raise serializers.ValidationError({
        "cliente": _("Debe seleccionar un cliente de la base de datos.")
    })

# Validar que el cliente pertenezca a la empresa
cliente_obj = Cliente.objects.get(id=cliente_id, empresa=empresa)
```

### Backend (Service)
```python
# Validación estricta en crear_preforma()
if not cliente:
    raise ValueError("Debe proporcionar un cliente de la base de datos. El campo cliente es obligatorio.")
```

### Frontend (JavaScript)
```javascript
// Validación antes de enviar
if (!clienteId || clienteId.trim() === '') {
    w.SintelFeedback.warning('Debe seleccionar un cliente de la lista');
    return;
}
```

---

## 📝 Migraciones

### Migración de Eliminación
Se creó una migración para eliminar el campo `cliente_nombre_manual`:
- **Archivo:** `0005_remove_cotizacion_cliente_nombre_manual.py`
- **Acción:** `RemoveField` para `cliente_nombre_manual`

**⚠️ IMPORTANTE:** Las migraciones históricas que crearon el campo se mantienen intactas para preservar el historial.

---

## 🎨 Cambios en la UI/UX

### Modal de Creación
- ✅ Select de clientes más prominente
- ✅ Mensaje claro: "Seleccione un cliente de la base de datos"
- ✅ Validación visual antes de permitir crear

### Modal de Edición
- ✅ Campo de cliente en solo lectura
- ✅ Muestra `cliente_display` (razón social)
- ✅ Mensaje: "El cliente no se puede modificar"

### Tabla de Cotizaciones
- ✅ Columna "Cliente" muestra siempre `cliente_display`
- ✅ Búsqueda funciona sobre razón social y número de documento

---

## 🔍 Archivos Modificados

### Backend
1. `apps/tenant/cotizaciones/models.py`
2. `apps/tenant/cotizaciones/api/serializers.py`
3. `apps/tenant/cotizaciones/services.py`
4. `apps/tenant/cotizaciones/api/viewsets.py`
5. `apps/tenant/cotizaciones/admin.py`
6. `apps/tenant/cotizaciones/migrations/0005_remove_cotizacion_cliente_nombre_manual.py`

### Frontend
7. `apps/tenant/core/static/core/js/cotizaciones/cotizacion_modals.js`
8. `apps/tenant/core/templates/tenant/core/partials/cotizaciones/modals.html`

---

## ✅ Checklist de Validación

- [x] Campo `cliente_nombre_manual` eliminado del modelo
- [x] Serializer actualizado (campo eliminado, validación simplificada)
- [x] Service actualizado (sin lógica de nombre manual)
- [x] ViewSet actualizado (búsqueda corregida)
- [x] Admin actualizado (search_fields y fieldsets)
- [x] JavaScript actualizado (sin referencias al campo)
- [x] Templates actualizados (campos eliminados)
- [x] Migración creada para eliminar el campo
- [x] Validaciones implementadas (frontend y backend)
- [x] Documentación actualizada

---

## 🚀 Próximos Pasos

1. **Testing**: Ejecutar pruebas de regresión para validar el flujo completo
2. **Migración de Datos**: Si existen cotizaciones con `cliente_nombre_manual`, considerar migración de datos
3. **Documentación de Usuario**: Actualizar manuales de usuario si es necesario
4. **Monitoreo**: Verificar que no haya errores en producción después del despliegue

---

## 📚 Referencias

- **Arquitectura General**: `documentacion/arquitectura_general.md`
- **Configuración y Numeración**: `documentacion/COTIZACIONES_CONFIGURACION_Y_NUMERACION.md`
- **Editor v2.40**: `documentacion/COTIZACIONES_EDITOR_V2.40.md`
- **Implementación DNA Dinámico**: `documentacion/RESUMEN_IMPLEMENTACION_DNA_DINAMICO.md`

---

## 📞 Soporte

Para preguntas o problemas relacionados con esta refactorización, consultar:
- **Documentación Técnica**: `documentacion/`
- **Código Fuente**: `apps/tenant/cotizaciones/`
- **Tests**: `apps/tenant/cotizaciones/tests/` (si existen)

---

**Última Actualización:** 2026-01-XX  
**Versión del Documento:** 1.0  
**Autor:** Sistema de Documentación Automática v2.60
