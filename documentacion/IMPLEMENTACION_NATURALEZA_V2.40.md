# 📊 Implementación Columna "Naturaleza" (Venta vs Compra) v2.40

**Fecha:** 2026-02-10  
**Versión:** 2.40  
**Estado:** ✅ Implementado y Funcional

## 📋 Resumen Ejecutivo

Se implementó la visualización de la columna "Naturaleza" (VENTA/COMPRA) en el DataTable de Facturas. La lógica de cálculo ya existía en el backend, pero ahora se expone correctamente en el frontend con renderizado visual mediante badges de colores.

## 🎯 Objetivo

Mostrar en el DataTable de Facturas si una factura es de **VENTA** (la empresa vende) o de **COMPRA** (la empresa compra), calculado automáticamente al importar el XML/DTO.

## 📐 Regla de Negocio

### Cálculo de Naturaleza

La naturaleza se determina comparando el NIT del Emisor de la factura con el NIT de la Empresa del tenant:

- **Si `Factura.emisor_nit == Empresa.nit`** → `naturaleza = 'VENTA'` (Salida - la empresa vende)
- **Si `Factura.emisor_nit != Empresa.nit`** → `naturaleza = 'COMPRA'` (Entrada - la empresa compra)

### Normalización de NITs

Los NITs se normalizan antes de comparar usando `normalize_nit()` del servicio general para:
- Eliminar espacios en blanco
- Normalizar guiones y caracteres especiales
- Asegurar comparación consistente

## 🔧 Implementación Técnica

### 1. Backend - Lógica de Servicio

**Archivo:** `apps/tenant/facturas/services.py`

La lógica ya estaba implementada correctamente:

```python
def _resolver_naturaleza(emisor_nit: str | None, empresa_nit: str | None) -> str:
    """
    Resuelve naturaleza (VENTA/COMPRA) comparando emisor vs empresa (SSoT).
    
    Returns:
        Factura.Naturaleza.VENTA si emisor == empresa
        Factura.Naturaleza.COMPRA si difiere
    """
    from apps.services.document_parser.normalizers import normalize_nit as norm_nit
    
    emisor_norm = norm_nit(emisor_nit)
    empresa_norm = norm_nit(empresa_nit)
    
    if emisor_norm and empresa_norm and emisor_norm == empresa_norm:
        return Factura.Naturaleza.VENTA
    return Factura.Naturaleza.COMPRA
```

**Uso en `guardar_factura_desde_dto()`:**
```python
# Línea 293: Resolver naturaleza (SSoT)
naturaleza = _resolver_naturaleza(emisor_nit, empresa_config.get("nit"))

# Línea 350: Guardar en factura_data
factura_data = {
    # ...
    "naturaleza": naturaleza,
    # ...
}
```

### 2. Backend - API Serializer

**Archivo:** `apps/tenant/facturas/api/serializers.py`

**Cambios aplicados:**
```python
class FacturaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = (
            "id",  # ⚠️ PRIMERO: Requerido para rowId
            "numero",
            "naturaleza",  # ⚠️ v2.40: VENTA/COMPRA calculado al importar
            "fecha_emision",
            "emisor_razon_social",
            "receptor_razon_social",
            "moneda",
            "total",
            "estado",
        )
        read_only_fields = ("id", "fecha_emision", "naturaleza")
```

### 3. Backend - ViewSet DataTables

**Archivo:** `apps/tenant/facturas/api/viewsets.py`

**Cambios aplicados:**

1. **Agregado a `.only()`:**
```python
base_qs = Factura.objects.only(
    "id",
    "numero",
    "naturaleza",  # ⚠️ v2.40: VENTA/COMPRA
    "fecha_emision",
    # ...
)
```

2. **Agregado a `fields_map`:**
```python
spec = DataTableSpec(
    fields_map={
        0: "id",  # Columna 0: ID (oculto)
        1: "numero",  # Columna 1: Número
        2: "naturaleza",  # Columna 2: Naturaleza (VENTA/COMPRA) ⚠️ v2.40
        3: "fecha_emision",  # Columna 3: Fecha emisión
        # ...
    },
    # ...
)
```

### 4. Frontend - HTML Template

**Archivo:** `apps/tenant/core/templates/tenant/core/partials/facturas/list.html`

**Cambios aplicados:**
```html
<table id="table-facturas" class="table table-striped table-hover dt-responsive nowrap w-100">
  <thead>
    <tr>
      <th style="display: none;">ID</th> <!-- Columna 0: ID oculto -->
      <th>Número</th> <!-- Columna 1 -->
      <th>Tipo</th> <!-- Columna 2: Naturaleza (VENTA/COMPRA) ⚠️ v2.40 -->
      <th>Fecha Emisión</th> <!-- Columna 3 -->
      <!-- ... resto de columnas ... -->
    </tr>
  </thead>
</table>
```

**Nota:** Ahora son **10 columnas** (incluyendo ID oculto).

### 5. Frontend - JavaScript

**Archivo:** `apps/tenant/core/static/core/js/facturas/facturas.page.js`

**Cambios aplicados:**

1. **Función de renderizado:**
```javascript
/**
 * Renderiza badge de naturaleza (VENTA/COMPRA)
 * ⚠️ v2.40: Nueva función para mostrar tipo de factura
 */
function renderNaturaleza(data) {
  if (!data) return '<span class="badge bg-secondary">N/A</span>';
  
  const badges = {
    'VENTA': 'success',  // Verde para ventas (salida)
    'COMPRA': 'primary'  // Azul para compras (entrada)
  };
  
  const texts = {
    'VENTA': 'Venta',
    'COMPRA': 'Compra'
  };
  
  const badgeClass = badges[data] || 'secondary';
  const text = texts[data] || data;
  
  return `<span class="badge bg-${badgeClass}">${text}</span>`;
}
```

2. **Agregada columna en `COLUMNS`:**
```javascript
const COLUMNS = [
  { data: 'id', visible: false, orderable: false }, // Columna 0: ID oculto
  { data: 'numero', className: 'fw-bold' }, // Columna 1: Número
  { data: 'naturaleza', render: renderNaturaleza }, // Columna 2: Naturaleza ⚠️ v2.40
  { data: 'fecha_emision', render: renderDateTime }, // Columna 3: Fecha Emisión
  // ... resto de columnas ...
];
```

3. **Actualizado orden por defecto:**
```javascript
order: [[3, 'desc']], // ⚠️ v2.40: Ordenar por fecha_emision (columna 3) - naturaleza es columna 2
```

## 📊 Estructura Final de Columnas

| Índice | Columna | Visible | Ordenable | Renderizado |
|--------|---------|---------|-----------|-------------|
| 0 | ID | ❌ No | ❌ No | - |
| 1 | Número | ✅ Sí | ✅ Sí | Texto en negrita |
| 2 | **Tipo (Naturaleza)** | ✅ Sí | ✅ Sí | Badge (Verde/Azul) |
| 3 | Fecha Emisión | ✅ Sí | ✅ Sí | Fecha formateada |
| 4 | Emisor | ✅ Sí | ✅ Sí | Texto |
| 5 | Receptor | ✅ Sí | ✅ Sí | Texto |
| 6 | Moneda | ✅ Sí | ✅ Sí | Texto |
| 7 | Total | ✅ Sí | ✅ Sí | Moneda formateada |
| 8 | Estado | ✅ Sí | ✅ Sí | Badge de estado |
| 9 | Acciones | ✅ Sí | ❌ No | Botones de acción |

## 🎨 Visualización

### Badges de Naturaleza

- **VENTA** (Verde - `bg-success`): 
  ```html
  <span class="badge bg-success">Venta</span>
  ```
  - Indica que la empresa es el emisor (vende)

- **COMPRA** (Azul - `bg-primary`): 
  ```html
  <span class="badge bg-primary">Compra</span>
  ```
  - Indica que la empresa es el receptor (compra)

- **N/A** (Gris - `bg-secondary`): 
  ```html
  <span class="badge bg-secondary">N/A</span>
  ```
  - Si el campo está vacío o es inválido

## ✅ Verificación de Implementación

### Checklist

- [x] Lógica de cálculo implementada en `services.py` (`_resolver_naturaleza`)
- [x] Campo `naturaleza` agregado a `FacturaListSerializer`
- [x] Campo `naturaleza` agregado a `.only()` en `datatables` action
- [x] Campo `naturaleza` agregado a `fields_map` (columna 2)
- [x] Columna `<th>Tipo</th>` agregada en HTML (posición 2)
- [x] Función `renderNaturaleza()` implementada en JavaScript
- [x] Columna `naturaleza` agregada en `COLUMNS` array
- [x] Orden por defecto actualizado a columna 3 (fecha_emision)
- [x] Comentarios actualizados en todos los archivos

### Archivos Modificados

1. ✅ `apps/tenant/facturas/api/serializers.py`
2. ✅ `apps/tenant/facturas/api/viewsets.py`
3. ✅ `apps/tenant/core/templates/tenant/core/partials/facturas/list.html`
4. ✅ `apps/tenant/core/static/core/js/facturas/facturas.page.js`
5. ✅ `apps/tenant/core/templates/tenant/core/workspace.html`

## 🔍 Flujo Completo

### Al Importar XML/DTO

1. **Parseo XML** → Extrae `emisor_nit` del documento
2. **Obtener Empresa** → `Empresa.objects.first().nit` (SSoT)
3. **Calcular Naturaleza** → `_resolver_naturaleza(emisor_nit, empresa_nit)`
4. **Guardar Factura** → `factura_data["naturaleza"] = naturaleza`
5. **Persistir** → Factura guardada con naturaleza calculada

### Al Visualizar en DataTable

1. **Backend** → `FacturaListSerializer` incluye `naturaleza`
2. **Frontend** → `renderNaturaleza()` convierte valor a badge
3. **Visualización** → Usuario ve badge verde (Venta) o azul (Compra)

## 📚 Referencias

- **Lógica de negocio:** `apps/tenant/facturas/services.py` - función `_resolver_naturaleza()`
- **Modelo:** `apps/tenant/facturas/models.py` - campo `naturaleza` (CharField con choices)
- **Estándar:** `documentacion/arquitectura_general.md` v2.40
- **Auditoría relacionada:** `documentacion/AUDITORIA_DATATABLES_V2.40.md`

## 🎯 Resultado

✅ **La columna "Naturaleza" se muestra correctamente en el DataTable de Facturas:**
- Se calcula automáticamente al importar XML/DTO
- Se visualiza con badges de colores (verde para Venta, azul para Compra)
- Es ordenable y filtrable desde el backend
- Está alineada con el estándar v2.40 (10 columnas totales)

---

**Documentado por:** AI Assistant  
**Revisado:** Pendiente  
**Aprobado:** Pendiente
