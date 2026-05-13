# Estado Actual App Facturas - v2.97

**Fecha:** 2026-05-11  
**Versión:** v2.97  
**Status:** ✅ PRODUCCIÓN (Con edición centralizada y Estado de Pago)  
**Última Actualización:** 2026-05-11

---

## 📋 Cambios Recientes Implementados (Sprint Actual)

### 1️⃣ Nuevo Campo: Estado de Pago

**Propósito:** Rastrear si un cliente pagó la factura (NO_PAGADA, PAGO_PARCIAL, PAGADA)

**Implementación:**
- ✅ Modelo: `Factura.estado_pago` con choices (NO_PAGADA, PAGO_PARCIAL, PAGADA)
- ✅ Default: NO_PAGADA
- ✅ Migración: `0006_factura_estado_pago.py` (aplicada)
- ✅ Serializers: Incluido en FacturaListSerializer y FacturaWriteSerializer
- ✅ UI: Columna en tabla + Dropdown en modal de edición
- ✅ Styling: Badges con colores (🔴 Rojo, 🟡 Amarillo, 🟢 Verde)

**Archivos Modificados:**
- `models.py` - Líneas 32-38 (EstadoPago class + campo)
- `api/serializers.py` - Líneas 95, 228 (agregado a fields)
- `api/viewsets.py` - Línea 250 (allowed_fields)
- `services/selectors.py` - Línea 30 (LIST_FIELDS)
- `static/js/facturas/features/facturas_list.js` - Columna Estado de Pago

---

### 2️⃣ Emisor Visible en Modal (Read-only)

**Propósito:** Usuario ve para quién es la factura sin poder editarlo

**Implementación:**
- ✅ Campo `emisor_razon_social` en modal con `disabled` attribute
- ✅ Etiqueta clara: "Este campo es de solo lectura"
- ✅ Ubicado al inicio del formulario modal

**Archivos Modificados:**
- `static/js/facturas/features/facturas_list.js` - Líneas 561-564

---

### 3️⃣ Edición Centralizada en Modal

**Cambio Crítico:** Toda la edición SOLO en modal, grid es 100% lectura

**Antes (v2.95):**
```
Grid → Edición inline directa en celdas
   ├─ editor: "date" en Vencimiento
   ├─ editor: "select" en Estado
   ├─ editor: "number" en Retenciones
   └─ Guardar automático en cada celda
```

**Ahora (v2.97):**
```
Grid → SOLO LECTURA (sin editores inline)
   └─ Click en celda → Sin efecto
   
Modal (único lugar de edición)
   ├─ Botón "Editar" (lápiz) abre modal
   ├─ Formulario con 9 campos editables
   ├─ Guardar → PATCH al servidor
   └─ Validación centralizada en backend
```

**Cambios Técnicos:**
- ❌ Removidos todos `editor: "..."` de columnas
- ❌ Removidos todos `editorParams`
- ❌ Removido event handler `cellEdited`
- ✅ Mantiene solo `formatter` para display
- ✅ Botón "Editar" funcional y centralizado

**Archivos Modificados:**
- `static/js/facturas/features/facturas_list.js` - Líneas 165-282 (removidos editors)

---

## 🔒 Garantía de Seguridad (9 Campos Editables)

### Campos Permitidos (Manuales - Editables)

```python
allowed_fields = {
    'estado',                 # Estado del documento
    'estado_pago',            # ⭐ NUEVO: Estado de pago
    'fecha_vencimiento',      # Fecha vencimiento
    'retefuente',             # Retención Fuente
    'reteica',                # ReteICA
    'reteiva',                # ReteIVA
    'forma_pago',             # Forma de pago
    'medio_pago_codigo',      # Código medio pago
    'payment_due_date'        # Fecha límite pago
}
```

### Campos Bloqueados (XML - No Editables)

- `numero`, `prefijo`, `consecutivo` - Identificadores
- `tipo`, `naturaleza`, `categoria` - Clasificación
- `fecha_emision` - Fecha original
- `emisor_*`, `receptor_*` - Datos de partes
- `moneda`, `subtotal`, `impuestos`, `total` - Montos
- `cufe`, `qr_url` - Códigos legales
- Y todos los metadatos UBL

---

## 🎯 Flujo de Edición (v2.97)

```
1. Usuario abre Gestión de Facturas
   ↓
2. Ve tabla con SOLO LECTURA
   ├─ Intenta click en celda → Sin efecto ✅
   └─ Datos mostrados sin editores
   ↓
3. Click en botón "Editar" (lápiz) en fila
   ↓
4. Modal se abre con:
   ├─ Emisor (deshabilitado, contexto)
   ├─ Estado (dropdown)
   ├─ Estado de Pago (dropdown) ⭐
   ├─ Vencimiento (date picker)
   ├─ Retenciones (3 campos número)
   ├─ Formas de Pago (3 campos)
   └─ Botón "Guardar Cambios"
   ↓
5. Usuario modifica campos
   ↓
6. Click "Guardar Cambios"
   ↓
7. PATCH /api/v1/facturas/{id}/
   ├─ Validación backend (allowed_fields)
   ├─ FacturaWriteSerializer
   └─ Persistencia en DB
   ↓
8. Respuesta 200 OK
   ├─ Modal cierra
   ├─ Tabla se actualiza
   └─ Feedback visual al usuario
```

---

## 📊 Validación en Múltiples Capas

| Capa | Mecanismo | Garantía |
|------|-----------|----------|
| **Frontend (Grid)** | SOLO LECTURA, sin editores | ❌ Imposible editar desde UI |
| **Frontend (Modal)** | 9 campos en formulario | ❌ XML fields no presentes |
| **Frontend (Network)** | PATCH con allowed_fields | ❌ Solo 9 campos en payload |
| **Backend (ViewSet)** | Validación allowed_fields | ❌ Error 400 para otros campos |
| **Backend (Serializer)** | FacturaWriteSerializer | ❌ Validación de tipos |
| **Backend (DB)** | Modelo con read_only en ORM | ❌ XML fields inmutables |

---

## ✅ Tests de Validación

### Desde UI (Usuario Normal)
```
1. Abre http://home.sintel.com/workspace/#facturas
2. Ve tabla con datos (SOLO LECTURA)
3. Intenta click en celda → Sin efecto ✅
4. Click botón "Editar" (lápiz)
5. Modal abre con 9 campos editables
6. Emisor visible pero deshabilitado ✅
7. Cambio Estado de Pago a "Pagada"
8. Click "Guardar Cambios"
9. PATCH exitoso → Tabla se actualiza ✅
```

### Desde API (Developer)
```bash
# Intento legítimo
PATCH /api/v1/facturas/2/
{
    "estado": "ENVIADA",
    "estado_pago": "PAGADA",
    "fecha_vencimiento": "2026-06-30"
}
→ 200 OK ✅

# Intento malicioso (campo no permitido)
PATCH /api/v1/facturas/2/
{
    "numero": "HACK",
    "estado": "ENVIADA"
}
→ 400 Bad Request ❌
{
    "error": "forbidden_fields",
    "forbidden": ["numero"]
}
```

---

## 📁 Estructura de Archivos (Post-Cambios)

```
apps/tenant/facturas/
├── models.py ............................ ✅ EstadoPago + campo estado_pago
├── api/
│   ├── serializers.py ................... ✅ estado_pago en fields
│   ├── viewsets.py ...................... ✅ allowed_fields con estado_pago
│   └── permissions.py ................... ✅ Sin cambios
├── services/
│   ├── selectors.py ..................... ✅ estado_pago en LIST_FIELDS
│   ├── business_service.py .............. ✅ Sin cambios
│   └── crud_service.py .................. ✅ Sin cambios
├── static/js/facturas/
│   ├── features/
│   │   └── facturas_list.js ............. ✅ Grid lectura + Modal edición
│   ├── facturas.api.js .................. ✅ Sin cambios
│   └── facturas_main.js ................. ✅ Sin cambios
├── templates/
│   ├── offcanvas_crear_factura.html ..... ✅ Sin cambios
│   └── partials/assets_facturas.html .... ✅ Sin cambios
├── migrations/
│   └── 0006_factura_estado_pago.py ...... ✅ APLICADA
└── .agent/
    ├── GARANTIA_EDICION_CONTROLADA.md .. ✅ v2.97 (Edición centralizada)
    └── ESTADO_ACTUAL_v297.md ............ ✅ Este archivo
```

---

## 🚀 Estado de Sincronización

- ✅ Migraciones aplicadas (shared + tenant)
- ✅ Archivos estáticos recolectados
- ✅ Contenedor web reiniciado
- ✅ Sistema sin errores
- ✅ Grid SOLO LECTURA
- ✅ Modal edición centralizada
- ✅ Estado de Pago funcional

---

## 🎯 Conclusión

La app **Facturas v2.97** está lista para producción con:

1. ✅ **Edición segura:** Centralizada en modal, validada en 6 capas
2. ✅ **Estado de Pago:** Nuevo campo para rastrear pagos de clientes
3. ✅ **UX mejorada:** Grid limpio (lectura) + Modal completo (edición)
4. ✅ **Garantía XML:** 100% protección de campos extraídos
5. ✅ **Datos de contexto:** Emisor visible (pero no editable)

**Próximos pasos opcionales:**
- Agregar columna "Monto Pagado" para pago parcial
- Historial de cambios en estado de pago
- Notificaciones automáticas por vencimiento

