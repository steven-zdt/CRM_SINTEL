# ✅ Corrección Inmutabilidad Gasto v2.61.4

## 📋 Resumen del Cambio

**Solicitado por usuario:** "la accion de inmutabilidad solo debe aplicar para el modelo gasto pero solo a su submodelo Documento soporte"

**Cambio realizado:**
- ✅ **DocumentoSoporte**: INMUTABLE ✓ (evidencia legal DIAN, Art. 1.6.1.4.12 DR 1625 de 2016)
- ✅ **Gasto**: MUTABLE en campos específicos ✓ (reclasificación contable)

---

## 🔧 Cambios Implementados

### 1. GastoViewSet - Permitir PUT/PATCH

**Archivo:** `apps/tenant/gastos/api/viewsets.py`

#### Cambio 1.1: Agregar UpdateModelMixin
```python
# ANTES (v2.40)
class GastoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):

# DESPUÉS (v2.61.4)
class GastoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,  # ⚠️ NEW: Permite PUT/PATCH
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
```

#### Cambio 1.2: Permitir HTTP methods PUT/PATCH
```python
# ANTES (v2.40)
http_method_names = ['get', 'post', 'delete', 'head', 'options']  # Bloqueaba PUT/PATCH

# DESPUÉS (v2.61.4)
http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']  # ⚠️ PUT/PATCH permitidos
```

#### Cambio 1.3: Implementar update() - PUT Completo
```python
def update(self, request, *args, **kwargs):
    """
    PUT /api/v1/gastos/{id}/
    
    ⚠️ v2.61.4: PERMITE EDICIÓN CONTROLADA de Gasto.
    - CAMPOS MUTABLES: centro_costo, categoria_contable, periodo, descripcion, observaciones
    - CAMPOS INMUTABLES: documento_soporte (toda su referencia)
    
    VALIDACIÓN CRITICAL: Se rechaza cualquier intento de modificar DocumentoSoporte.
    """
    # Validaciones:
    # 1. Si intenta editar 'documento_soporte' → 400 Bad Request
    # 2. Si intenta editar campos de DocumentoSoporte indirectamente → 400 Bad Request
    # 3. Si intenta editar campos no permitidos → 400 Bad Request
    # 4. Solo actualiza: centro_costo, categoria_contable, periodo, descripcion, observaciones
    # 5. Retorna: 200 OK con objeto actualizado
```

#### Cambio 1.4: Implementar partial_update() - PATCH Parcial
```python
def partial_update(self, request, *args, **kwargs):
    """
    PATCH /api/v1/gastos/{id}/
    
    ⚠️ v2.61.4: PERMITE EDICIÓN PARCIAL de Gasto.
    - Mismo comportamiento que PUT pero para actualizaciones parciales
    """
    # Mismas validaciones que update()
    # Permite actualizar solo los campos especificados
```

---

## ✨ Separación de Responsabilidades

### DocumentoSoporte (INMUTABLE)
✅ Implementado como **evidencia legal DIAN**

Campos que NO pueden editarse una vez creados:
```
- resolucion_dian, prefijo, consecutivo
- fecha
- vendedor_nit, vendedor_nombre, vendedor_dirección, vendedor_teléfono
- numero_factura_proveedor
- subtotal, retefuente, retefuente_porcentaje
- reteica, reteica_porcentaje, total
- adjunto, activo, anulado, fecha_anulacion
```

### Gasto (MUTABLE)
✅ Implementado como **contenedor de clasificación contable**

Campos que PUEDEN editarse (PUT/PATCH):
```
✓ centro_costo        (reclasificación de centro de costos)
✓ categoria_contable  (reclasificación de categoría)
✓ periodo            (ajuste de período contable)
✓ descripcion        (texto adicional)
✓ observaciones      (texto adicional)
```

---

## 🛡️ Validaciones Implementadas

### En update() y partial_update():

1. **Rechazo de documento_soporte**
   ```python
   if 'documento_soporte' in request.data:
       → 400 Bad Request: "El Documento Soporte es inmutable"
   ```

2. **Rechazo de campos de DocumentoSoporte**
   ```python
   immutable_ds_fields = [
       'resolucion_dian', 'prefijo', 'consecutivo', 'fecha',
       'vendedor_nit', 'vendedor_nombre', 'vendedor_direccion',
       'subtotal', 'retefuente', 'reteica', 'total', ...
   ]
   
   for field in immutable_ds_fields:
       if field in request.data:
           → 400 Bad Request: "El campo {field} pertenece al Documento Soporte (inmutable)"
   ```

3. **Rechazo de campos no permitidos**
   ```python
   mutable_fields = {'centro_costo', 'categoria_contable', 'periodo', 'descripcion', 'observaciones'}
   
   invalid_fields = set(request.data.keys()) - mutable_fields
   if invalid_fields:
       → 400 Bad Request: "Los siguientes campos no pueden ser editados: {invalid_fields}"
   ```

---

## 📝 Ejemplos de Uso

### ✅ Solicitud VÁLIDA - Reclasificar gasto

```bash
PUT /api/v1/gastos/123/
Content-Type: application/json

{
  "centro_costo": "VENTAS",
  "categoria_contable": "COMBUSTIBLE",
  "periodo": "2026-03"
}

# Response: 200 OK
{
  "id": 123,
  "documento_soporte": {...},
  "centro_costo": "VENTAS",
  "categoria_contable": "COMBUSTIBLE",
  "periodo": "2026-03",
  ...
}
```

### ❌ Solicitud INVÁLIDA - Intento de modificar DocumentoSoporte

```bash
PUT /api/v1/gastos/123/
Content-Type: application/json

{
  "subtotal": 1500000,  # ⚠️ Campo de DocumentoSoporte
  "centro_costo": "VENTAS"
}

# Response: 400 Bad Request
{
  "error": "immutable_field",
  "message": "El campo 'subtotal' pertenece al Documento Soporte (inmutable). No se puede modificar.",
  "field": "subtotal"
}
```

---

## 🧪 Testing

Para validar estos cambios:

```bash
# Crear un gasto
POST /api/v1/gastos/
{...gasto_data...}

# Editar clasificación contable (PERMITIDO)
PATCH /api/v1/gastos/1/
{
  "centro_costo": "DIFERENTE",
  "categoria_contable": "NUEVA"
}
# → Esperar: 200 OK

# Intento de editar subtotal (BLOQUEADO)
PATCH /api/v1/gastos/1/
{
  "subtotal": 999999
}
# → Esperar: 400 Bad Request con mensaje de campo inmutable
```

---

## 📦 Compatibilidad

### Backward Compatibility ✅
- Métodos GET, POST, DELETE siguen igual
- Solo agrega PUT/PATCH (antes bloqueados)
- Clientes que NO usan PUT/PATCH no se afectan
- Clientes que intentaban PUT/PATCH ahora pueden hacerlo correctamente

### API Versioning
- Cambio dentro de v2.61.4
- No requiere cambio de versión completamente
- Compatible con clientes existentes

---

## 📊 Resumen de Cambios

| Aspecto | Antes | Después |
|---------|-------|---------|
| PUT/PATCH | Bloqueado (405) | Permitido y Validado ✅ |
| Editar centro_costo | ❌ No permitido | ✅ Sí permitido |
| Editar categoria_contable | ❌ No permitido | ✅ Sí permitido |
| Editar documento_soporte | ❌ No permitido | ❌ No permitido (400) |
| Editar subtotal | ❌ No permitido | ❌ No permitido (400) |
| Editar fecha | ❌ No permitido | ❌ No permitido (400) |

---

## ✅ Validación Completada

- ✅ Cambio implementado en GastoViewSet
- ✅ Métodos update() y partial_update() creados
- ✅ Validaciones CRITICAL para inmutabilidad implementadas
- ✅ DocumentoSoporte totalmente protegido
- ✅ Backward compatible con clientes existentes
- ✅ Error messages claros y específicos

---

## 📌 Próximos Pasos (Opcionales)

1. **Crear ViewSet separado para DocumentoSoporte** (si se necesita exponer como recurso independiente)
2. **Agregar tests** para validar rechazos de campos inmutables
3. **Documentar en OpenAPI/Swagger** los métodos PUT/PATCH
4. **Considerar auditoría** de cambios en Gasto (quién editó, cuándo, qué cambió)

---

**Fecha:** 20-Mar-2026  
**Versión:** v2.61.4  
**Estado:** ✅ COMPLETADO
