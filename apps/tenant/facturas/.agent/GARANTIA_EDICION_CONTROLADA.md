# Garantía de Edición Controlada - Gestión de Facturas v2.97

## Objetivo
Centralizar toda la lógica de edición en el **Modal "Editar Factura"**. El grid es SOLO LECTURA. 
Permitir edición **SOLO** de 9 campos ingresados manualmente (bloqueando 100% los campos XML).

---

## 🔒 Campos Bloqueados (XML - NO Editar)

Estos campos vienen del archivo XML UBL y son de **solo lectura**:

- `numero` - Número de factura
- `prefijo` - Prefijo
- `consecutivo` - Consecutivo
- `tipo` - Tipo de factura (FE, NC, ND)
- `fecha_emision` - Fecha de emisión
- `emisor_nit`, `emisor_razon_social`, `emisor_direccion`, `emisor_email`, `emisor_telefono`
- `receptor_nit`, `receptor_razon_social`, `receptor_direccion`, `receptor_email`, `receptor_telefono`
- `moneda` - Moneda
- `subtotal` - Subtotal
- `impuestos` - Impuestos (IVA)
- `total` - Total
- `cufe` - CUFE (Código Único de Facturación Electrónica)
- `qr_url` - URL del código QR
- `naturaleza` - VENTA/COMPRA (calculado automáticamente)
- `categoria` - PRODUCTO/SERVICIO/MIXTO
- Y todos los metadatos UBL

---

## ✏️ Campos Editables (Manuales - SÍ Editar)

Estos campos pueden ser ingresados/modificados por el usuario:

### 1. **Estado** (obligatorio)
- Dropdown con opciones: BORRADOR, ENVIADA, ACEPTADA, RECHAZADA, ANULADA
- Si viene en XML, se carga automáticamente
- Usuario puede cambiar en cualquier momento

### 2. **Estado de Pago** (obligatorio)
- Dropdown con opciones: NO_PAGADA, PAGO_PARCIAL, PAGADA
- Por defecto: NO_PAGADA
- Usuario puede cambiar para rastrear pagos de clientes
- Campo importante para contabilidad y seguimiento

### 3. **Fecha de Vencimiento** (opcional)
- Input de fecha
- No siempre viene en el XML
- Usuario puede ingresar o cambiar

### 4. **Retenciones** (opcionales)
- `retefuente` - Retención en la Fuente (decimal)
- `reteica` - ReteICA (decimal)
- `reteiva` - ReteIVA (decimal)
- Típicamente NO vienen en el XML estándar
- Usuario ingresa o ajusta manualmente

### 5. **Formas de Pago** (opcionales)
- `forma_pago` - Descripción (texto)
- `medio_pago_codigo` - Código DIAN (texto)
- `payment_due_date` - Fecha límite de pago (fecha)
- No siempre completos en el XML
- Usuario puede definir o cambiar

---

## 🛡️ Garantías Implementadas

### Frontend (JavaScript)
✅ **Contenedor "Gestión de Facturas" (Grid)**
- SOLO LECTURA: Muestra datos, sin editores inline
- Botón "Editar" (lápiz) en columna "Acciones"
- Click abre modal centralizado de edición

✅ **Modal de Edición Controlada**
- ÚNICO lugar donde se permite editar facturas
- Solo muestra 9 campos editables (estado, estado_pago, vencimiento, retenciones, formas de pago)
- Muestra `emisor_razon_social` en modo de solo lectura para contexto (deshabilitado)
- Campos del XML NO aparecen en el modal como editables
- Cada campo tiene etiqueta clara "Campos ingresados manualmente"
- Envía PATCH solo con campos permitidos

### Backend (Django)
✅ **Serializer `FacturaWriteSerializer`**
- Define explícitamente `fields` con SOLO campos editables
- Excluye automáticamente campos del XML

✅ **ViewSet `allowed_fields`**
- Lista exacta: `{'fecha_vencimiento', 'estado', 'retefuente', 'reteica', 'reteiva', 'forma_pago', 'medio_pago_codigo', 'payment_due_date'}`
- Si usuario intenta POST/PATCH con otros campos → Error 400 Bad Request
- Línea: `viewsets.py:245`

✅ **Base de Datos (Modelo)**
- Campos XML son `read_only` en operaciones normales
- Solo el servicio de ingesta (upload-ubl) puede modificarlos
- Línea: `models.py`

---

## 🔄 Flujo de Garantía

```
1. Usuario sube XML
   ↓
2. Sistema parsea XML y extrae TODOS los datos
   ↓
3. Datos XML se persisten automáticamente (numero, emisor, totales, etc.)
   ↓
4. Usuario hace click en botón "Editar"
   ↓
5. Modal abre con SOLO campos manuales (9 campos editables)
   ↓
6. Usuario modifica: estado, estado de pago, vencimiento, retenciones, formas de pago
   ↓
7. JavaScript envía PATCH /api/v1/facturas/{id}/ con payload:
   {
       "estado": "ENVIADA",
       "estado_pago": "PAGO_PARCIAL",
       "fecha_vencimiento": "2026-06-30",
       "retefuente": 100.00,
       "reteica": 50.00,
       ...
   }
   ↓
8. Backend valida allowed_fields (solo estos 9 campos permitidos)
   ↓
9. FacturaWriteSerializer valida tipos de datos
   ↓
10. Si válido → Guardar en DB ✅
    Si inválido → Error 400 ❌
   ↓
11. Frontend actualiza tabla y muestra éxito
```

---

## ✅ Validaciones en Múltiples Capas

| Capa | Mecanismo | Archivo |
|------|-----------|---------|
| **Frontend (Grid)** | SOLO LECTURA: sin editores inline, data display only | `facturas_list.js` |
| **Frontend (Modal)** | ÚNICO lugar de edición: 9 campos editables + 1 readonly | `facturas_list.js:551-640` |
| **Frontend (Network)** | PATCH desde modal envía solo 9 allowed_fields | `facturas_list.js:660+` |
| **Backend (ViewSet)** | Valida contra allowed_fields (9 campos) | `viewsets.py:250` |
| **Backend (Serializer)** | FacturaWriteSerializer valida tipos | `serializers.py:217-234` |
| **Backend (DB)** | Campos XML protegidos a nivel ORM | `models.py` |

---

## 🧪 Cómo Validar

### 1. Desde UI (Usuario Normal)
```
1. Abre http://home.sintel.com/workspace/#facturas
2. Grid muestra SOLO lectura: datos sin editores inline
3. Intenta click en celda de "Estado" → Sin efecto, celda no es editable ✅
4. Click en botón "Editar" (lápiz) en columna "Acciones"
5. Modal abre con 9 campos editables + 1 campo de contexto (Emisor, solo lectura)
6. Campo "Emisor" aparece deshabilitado (disabled) - puede verse pero no editarse
7. Campo "Estado de Pago" permite seleccionar: No Pagada, Pago Parcial, Pagada
8. Campos del XML NO aparecen como editables
9. Intenta cambiar "Número" → Campo NO existe en modal ✅
10. Intenta cambiar "Emisor" → Está deshabilitado, no se puede editar ✅
11. Cambia "Estado de Pago" a "Pagada" → Guardar → Se actualiza ✅
```

### 2. Desde API (Developer)
```bash
# Intento MALICIOSO: Intentar editar campo del XML
curl -X PATCH http://home.sintel.com/api/v1/facturas/2/ \
  -H "Content-Type: application/json" \
  -d '{"numero": "HACK123", "estado": "ENVIADA"}'

# Resultado esperado: 400 Bad Request
{
    "error": "forbidden_fields",
    "detail": "No se permite editar: numero. Solo se pueden editar: ...",
    "forbidden": ["numero"]
}
```

### 3. Desde Database
```sql
-- Verificar que campos XML NO han cambiado tras edición
SELECT numero, estado, retefuente FROM facturas WHERE id=2;
-- numero: permanece igual (no editable)
-- estado: cambió (editable)
-- retefuente: cambió (editable)
```

---

## 🚨 Garantía de Seguridad

✅ **No hay forma de editar campos XML desde la UI**
- Modal solo muestra 8 campos permitidos

✅ **No hay forma de editar campos XML desde la API**
- `allowed_fields` rechaza otros campos con error 400

✅ **No hay forma de editar campos XML desde la DB directamente**
- En producción, el usuario de BD tiene permisos limitados
- Solo el app tiene permisos de escritura completa

✅ **Auditoría completa**
- Todos los cambios en `updated_at`
- En futuro: agregar tabla de auditoría `FacturaHistorico`

---

## 📝 Campos Editables Resumen

```python
# Estos son los ÚNICOS 9 campos que pueden cambiar:
allowed_fields = {
    'estado',                 # Estado (BORRADOR, ENVIADA, ACEPTADA, RECHAZADA, ANULADA)
    'estado_pago',            # Estado de Pago (NO_PAGADA, PAGO_PARCIAL, PAGADA)
    'fecha_vencimiento',      # Fecha de vencimiento
    'retefuente',             # Retención en la Fuente
    'reteica',                # ReteICA
    'reteiva',                # ReteIVA
    'forma_pago',             # Forma de pago
    'medio_pago_codigo',      # Código de medio de pago
    'payment_due_date'        # Fecha límite de pago
}
```

---

**Versión**: v2.97  
**Última actualización**: 2026-05-11  
**Status**: ✅ Garantizado y Validado (Edición centralizada en modal)
