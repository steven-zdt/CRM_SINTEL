# Panel de Totales Netos - Módulo Facturas

**Versión:** v2.40  
**Fecha:** 2025-01-20  
**Autor:** Arquitectura SINTEL

## 📋 Resumen Ejecutivo

El Panel de Totales Netos es un componente crítico del módulo de facturación que proporciona un desglose fiscal detallado de **Ventas** y **Compras**, excluyendo automáticamente las facturas que tienen una Nota de Crédito aplicada. Esto garantiza la integridad contable y fiscal según la normativa colombiana.

## 🎯 Regla de Negocio Crítica

### Exclusión de Facturas con Nota de Crédito

**REGLA FUNDAMENTAL:**
- **Factura con `nota_credito_id IS NOT NULL`** → **Valor 0** para todos los cálculos (Subtotal, Impuestos, Total)
- **Factura sin Nota de Crédito** → Se suma normalmente al total neto

**Justificación Contable:**
Una factura con Nota de Crédito aplicada ha sido anulada o ajustada fiscalmente. Por lo tanto, sus valores no deben contabilizarse en los totales netos para evitar duplicación o sobreestimación de ingresos/gastos.

## 🏗️ Arquitectura de la Solución

### Componentes Implementados

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (UI/UX)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Panel de Totales Netos (Tarjetas Bootstrap 5)       │   │
│  │  - Card Ventas Netas                                  │   │
│  │  - Card Compras Netas                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  DataTables Client-Side                               │   │
│  │  - drawCallback → Recalcular Totales                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ API REST
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (Django/DRF)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Endpoint: GET /api/v1/facturas/summary/             │   │
│  │  - FacturaViewSet.summary()                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Service Layer: get_facturacion_summary()            │   │
│  │  - Agregaciones Django (Sum, Count)                   │   │
│  │  - Filtro: nota_credito__isnull=True                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Modelo: Factura                                      │   │
│  │  - Campos: subtotal, impuestos, total, naturaleza    │   │
│  │  - Relación: nota_credito (OneToOne)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Archivos Modificados

### 1. Backend - Servicios

**Archivo:** `apps/tenant/facturas/services.py`

**Función Agregada:**
```python
def get_facturacion_summary(empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Calcula resumen de facturación neta excluyendo facturas con Nota de Crédito.
    
    ⚠️ v2.40: REGLA CRÍTICA - Facturas con nota_credito_id IS NOT NULL => Valor 0.
    Solo suma facturas sin NC asociada para mantener integridad fiscal.
    """
```

**Lógica de Agregación:**
- Usa `Q(nota_credito__isnull=True)` para excluir facturas con NC
- Agrupa por `naturaleza` (VENTA/COMPRA)
- Calcula: `subtotal_neto`, `impuestos_neto`, `total_neto`, `cantidad`
- Usa `Coalesce(Sum(...), Decimal('0.00'))` para evitar valores None

### 2. Backend - API

**Archivo:** `apps/tenant/facturas/api/viewsets.py`

**Endpoint Agregado:**
```python
@action(detail=False, methods=["get"], url_path="summary")
def summary(self, request: Request) -> Response:
    """
    Endpoint para obtener resumen de facturación neta.
    GET /api/v1/facturas/summary/
    """
```

**Respuesta JSON:**
```json
{
  "ventas": {
    "subtotal_neto": "100000.00",
    "impuestos_neto": "19000.00",
    "total_neto": "119000.00",
    "cantidad": 5
  },
  "compras": {
    "subtotal_neto": "50000.00",
    "impuestos_neto": "9500.00",
    "total_neto": "59500.00",
    "cantidad": 2
  }
}
```

### 3. Backend - Serializers

**Archivo:** `apps/tenant/facturas/api/serializers.py`

**Cambios en `FacturaListSerializer`:**
- Agregados campos `subtotal` e `impuestos` al serializer
- Necesarios para cálculos dinámicos en el frontend (filas visibles)

### 4. Frontend - Template HTML

**Archivo:** `apps/tenant/core/templates/tenant/core/partials/facturas/list.html`

**Panel de Totales Netos:**
```html
<div class="row mb-4" id="panel-totales-netos">
  <!-- Card Ventas Netas -->
  <div class="col-md-6 mb-3">
    <div class="card h-100 border-success">
      <div class="card-header bg-success text-white">
        <i class="bi bi-graph-up-arrow me-2"></i>
        <strong>Ventas Netas</strong>
      </div>
      <div class="card-body">
        <h3 id="ventas-total-neto">$0</h3>
      </div>
      <div class="card-footer bg-light">
        <span>Subtotal: <strong id="ventas-subtotal-neto">$0</strong></span>
        <span>IVA: <strong id="ventas-impuestos-neto">$0</strong></span>
      </div>
    </div>
  </div>
  
  <!-- Card Compras Netas -->
  <!-- Estructura similar con border-primary -->
</div>
```

### 5. Frontend - JavaScript

**Archivo:** `apps/tenant/core/static/core/js/facturas/facturas.page.js`

**Funciones Implementadas:**

#### `formatCurrency(value)`
Formatea montos en pesos colombianos usando `Intl.NumberFormat`:
```javascript
formatCurrency(value) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(numValue);
}
```

#### `updateFinancePanel()`
Carga resumen desde el backend y actualiza las tarjetas:
- Endpoint: `GET /api/v1/facturas/summary/`
- Actualiza elementos: `ventas-total-neto`, `ventas-subtotal-neto`, `ventas-impuestos-neto`
- Similar para compras

#### `updateFinancePanelFromVisibleRows()`
Recalcula totales basándose en filas visibles de DataTables:
- Itera sobre `api.rows({ search: 'applied' })`
- Excluye facturas con `nota_credito_id`
- Suma solo filas visibles (respeta filtros/búsqueda)
- Se ejecuta en `drawCallback` de DataTables

## 🔄 Flujo de Datos

### 1. Carga Inicial
```
Usuario abre módulo Facturas
  ↓
DOMUtils.onVisibleOnce('#tab-facturas', init)
  ↓
initDataTable() → Carga GET /api/v1/facturas/
  ↓
updateFinancePanel() → Carga GET /api/v1/facturas/summary/
  ↓
Renderiza tarjetas con totales del backend
```

### 2. Filtrado/Búsqueda Dinámico
```
Usuario filtra/busca en DataTables
  ↓
DataTables.draw() → drawCallback ejecutado
  ↓
updateFinancePanelFromVisibleRows()
  ↓
Recalcula sumando solo filas visibles sin NC
  ↓
Actualiza tarjetas en tiempo real
```

### 3. Subida/Eliminación de Factura
```
Usuario sube/elimina factura
  ↓
handleUploadUBL() / handleDelete()
  ↓
Recarga tabla (initDataTable())
  ↓
updateFinancePanel() → Recarga desde backend
  ↓
Tarjetas actualizadas con nuevos totales
```

## 📊 Estructura de Datos

### Modelo Factura (Campos Relevantes)
```python
class Factura(models.Model):
    # Totales
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    impuestos = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Naturaleza
    naturaleza = models.CharField(
        choices=[('VENTA', 'Venta'), ('COMPRA', 'Compra')]
    )
    
    # Relación con Nota de Crédito
    nota_credito = models.OneToOneField(
        'NotaCredito',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
```

### Query de Agregación
```python
# Ventas Netas (sin NC)
Factura.objects.filter(
    nota_credito__isnull=True,
    naturaleza=Factura.Naturaleza.VENTA
).aggregate(
    subtotal_neto=Coalesce(Sum('subtotal'), Decimal('0.00')),
    impuestos_neto=Coalesce(Sum('impuestos'), Decimal('0.00')),
    total_neto=Coalesce(Sum('total'), Decimal('0.00')),
    cantidad=Count('id')
)
```

## 🎨 Interfaz de Usuario

### Tarjetas de Totales

**Card Ventas Netas:**
- Color: Verde (`border-success`, `bg-success`)
- Icono: `bi-graph-up-arrow`
- Contenido:
  - Título: "Ventas Netas"
  - Valor Principal: Total Neto (formato COP)
  - Footer: Subtotal | IVA

**Card Compras Netas:**
- Color: Azul (`border-primary`, `bg-primary`)
- Icono: `bi-cart-dash`
- Contenido:
  - Título: "Compras Netas"
  - Valor Principal: Total Neto (formato COP)
  - Footer: Subtotal | IVA

**Texto Legal:**
- Ubicado debajo de las tarjetas
- Mensaje: *"Valores calculados excluyendo documentos con Nota de Crédito aplicada"*

## ⚙️ Configuración y Uso

### Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/facturas/summary/` | Obtiene resumen de facturación neta |
| `GET` | `/api/v1/facturas/` | Lista de facturas (incluye `subtotal`, `impuestos`) |

### Permisos Requeridos

- `IsAuthenticated`: Usuario debe estar autenticado
- `IsTenantAdminOrReadOnly`: Solo lectura para usuarios autenticados

### Formato de Moneda

Todos los montos se formatean como:
- Moneda: COP (Pesos Colombianos)
- Formato: `$1.234.567` (sin decimales)
- Locale: `es-CO`

## 🔍 Casos de Uso

### Caso 1: Factura Normal (Sin NC)
```
Factura FST001:
  - Subtotal: $100,000
  - IVA: $19,000
  - Total: $119,000
  - Naturaleza: VENTA
  - nota_credito_id: null

Resultado: Se suma a "Ventas Netas"
```

### Caso 2: Factura con Nota de Crédito
```
Factura FST002:
  - Subtotal: $50,000
  - IVA: $9,500
  - Total: $59,500
  - Naturaleza: VENTA
  - nota_credito_id: 123 (NC aplicada)

Resultado: NO se suma (valor 0 en cálculos)
```

### Caso 3: Filtrado Dinámico
```
Usuario busca "FST" en DataTables
  ↓
Solo muestra facturas que contienen "FST"
  ↓
updateFinancePanelFromVisibleRows() recalcula
  ↓
Tarjetas muestran totales solo de facturas visibles
```

## 🧪 Validación y Testing

### Escenarios de Prueba

1. **Factura sin NC:**
   - ✅ Debe aparecer en totales
   - ✅ Debe sumarse correctamente

2. **Factura con NC:**
   - ✅ NO debe aparecer en totales
   - ✅ Debe tener valor 0 en cálculos

3. **Filtrado:**
   - ✅ Totales deben recalcularse al filtrar
   - ✅ Solo sumar filas visibles

4. **Subida de Factura:**
   - ✅ Panel debe actualizarse automáticamente
   - ✅ Nuevos totales deben reflejarse

5. **Subida de NC:**
   - ✅ Factura referenciada debe excluirse de totales
   - ✅ Panel debe actualizarse correctamente

## 📝 Notas Técnicas

### Optimización

- **Agregaciones en Base de Datos:** Los cálculos se realizan en PostgreSQL usando `Sum()` y `Count()`, no en Python
- **Client-Side Recalculation:** Para filtros dinámicos, se recalcula desde datos ya cargados (sin peticiones adicionales)
- **Lazy Loading:** El panel se carga solo cuando el tab de facturas es visible

### Integridad de Datos

- **Snapshot Histórico:** Los campos `subtotal`, `impuestos`, `total` se guardan al momento de importar el XML
- **Inmutabilidad:** Una vez importada, la factura no puede modificarse (excepto eliminación técnica)
- **Relación OneToOne:** Cada factura puede tener máximo una Nota de Crédito

### Compatibilidad

- **Bootstrap 5:** Tarjetas y componentes UI
- **DataTables 1.13+:** Para tablas interactivas
- **Intl.NumberFormat:** Formato de moneda (soportado en navegadores modernos)

## 🔗 Referencias

- **Arquitectura General:** `documentacion/arquitectura_general.md` v2.40
- **Pipeline Universal:** `documentacion/universal_pipeline_v2.37.md`
- **Modelo Factura:** `apps/tenant/facturas/models.py`
- **Service Layer:** `apps/tenant/facturas/services.py`

## 📅 Historial de Cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2025-01-20 | v2.40 | Implementación inicial del Panel de Totales Netos |

---

**⚠️ IMPORTANTE:** Este panel es crítico para la integridad fiscal. Cualquier modificación debe mantener la regla de exclusión de facturas con Nota de Crédito.
