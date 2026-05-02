# Matriz de Endpoints DataTables (/dt/) por App

## Resumen

Esta matriz documenta los endpoints `/dt/` requeridos para cada app con listados tabulares, siguiendo el estándar DataTables server-side (POST, CSRF, whitelist) según Arquitectura v2.37.

---

## Endpoints Implementados

### ✅ Facturas
- **Endpoint**: `POST /api/v1/facturas/dt/facturas/`
- **Archivo**: `apps/tenant/facturas/api/datatables.py`
- **Función**: `facturas_dt(request)`
- **Modelo**: `Factura`
- **Serializer**: `FacturaListSerializer`
- **fields_map**: 
  - `0: "numero"`
  - `1: "naturaleza"`
  - `2: "emisor_razon_social"`
  - `3: "receptor_razon_social"`
  - `4: "fecha_emision"`
  - `5: "subtotal"`
  - `6: "impuestos"`
  - `7: "total"`
  - `8: "cufe"`
- **search_fields**: `["numero", "cufe", "emisor_razon_social", "emisor_nit", "receptor_razon_social", "receptor_nit"]`
- **Filtros adicionales**: `naturaleza`, `nit`, `fecha_emision__date__gte`, `fecha_emision__date__lte`
- **QuerySet**: `Factura.objects.select_related("nota_credito").only(*list_fields)`

---

## Endpoints Pendientes

### 🔄 Gastos
- **Endpoint**: `POST /api/v1/gastos/dt/gastos/`
- **Archivo**: `apps/tenant/gastos/api/datatables.py` (crear)
- **Modelo**: `Gasto`
- **Serializer**: `GastoListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "descripcion"`
  - `1: "monto"`
  - `2: "fecha"`
  - `3: "categoria"`
- **search_fields**: `["descripcion", "categoria", "notas"]`
- **Filtros adicionales**: `fecha__gte`, `fecha__lte`, `categoria`

### 🔄 Proveedores
- **Endpoint**: `POST /api/v1/proveedores/dt/proveedores/`
- **Archivo**: `apps/tenant/proveedores/api/datatables.py` (crear)
- **Modelo**: `Proveedor`
- **Serializer**: `ProveedorListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "razon_social"`
  - `1: "nit_completo"`
  - `2: "direccion"`
  - `3: "telefono"`
  - `4: "email"`
- **search_fields**: `["razon_social", "nit", "email"]`
- **Filtros adicionales**: Ninguno (por ahora)

### 🔄 Empleados
- **Endpoint**: `POST /api/v1/empleados/dt/empleados/`
- **Archivo**: `apps/tenant/empleados/api/datatables.py` (crear)
- **Modelo**: `Empleado`
- **Serializer**: `EmpleadoListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "nombres"`
  - `1: "apellidos"`
  - `2: "tipo_documento"`
  - `3: "numero_documento"`
  - `4: "email"`
  - `5: "telefono"`
- **search_fields**: `["nombres", "apellidos", "numero_documento", "email"]`
- **Filtros adicionales**: `tipo_documento`

### 🔄 Contabilidad — Cuentas
- **Endpoint**: `POST /api/v1/core/contabilidad/dt/cuentas/`
- **Archivo**: `apps/tenant/core/api/datatables_contabilidad.py` (crear)
- **Modelo**: `CuentaContable`
- **Serializer**: `CuentaListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "codigo"`
  - `1: "nombre"`
  - `2: "tipo"`
  - `3: "descripcion"`
- **search_fields**: `["codigo", "nombre", "descripcion"]`
- **Filtros adicionales**: `tipo`

### 🔄 Contabilidad — Asientos
- **Endpoint**: `POST /api/v1/core/contabilidad/dt/asientos/`
- **Archivo**: `apps/tenant/core/api/datatables_contabilidad.py` (crear)
- **Modelo**: `AsientoContable`
- **Serializer**: `AsientoListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "numero"`
  - `1: "fecha"`
  - `2: "descripcion"`
  - `3: "estado"`
- **search_fields**: `["numero", "descripcion"]`
- **Filtros adicionales**: `fecha__gte`, `fecha__lte`, `estado`

### 🔄 Inventario — Catálogo
- **Endpoint**: `POST /api/v1/core/inventario/dt/catalogo/`
- **Archivo**: `apps/tenant/core/api/datatables_inventario.py` (crear)
- **Modelo**: `ItemCatalogo`
- **Serializer**: `ItemCatalogoListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "codigo"`
  - `1: "nombre"`
  - `2: "categoria"`
  - `3: "stock"`
  - `4: "precio"`
- **search_fields**: `["codigo", "nombre", "categoria"]`
- **Filtros adicionales**: `categoria`, `stock__gte`, `stock__lte`

### 🔄 Inventario — Activos
- **Endpoint**: `POST /api/v1/core/inventario/dt/activos/`
- **Archivo**: `apps/tenant/core/api/datatables_inventario.py` (crear)
- **Modelo**: `Activo`
- **Serializer**: `ActivoListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "codigo"`
  - `1: "nombre"`
  - `2: "estado"`
  - `3: "ubicacion"`
- **search_fields**: `["codigo", "nombre", "ubicacion"]`
- **Filtros adicionales**: `estado`, `ubicacion`

### 🔄 Mail (MailDigester) — Ejecuciones
- **Endpoint**: `POST /api/v1/core/maildigester/dt/runs/`
- **Archivo**: `apps/tenant/core/api/datatables_maildigester.py` (crear)
- **Modelo**: `MailIngestionRun`
- **Serializer**: `MailIngestionRunListSerializer` (crear)
- **fields_map propuesto**:
  - `0: "estado"`
  - `1: "config_email"`
  - `2: "fecha_inicio"`
  - `3: "fecha_fin"`
  - `4: "total_procesados"`
  - `5: "facturas_creadas"`
- **search_fields**: `["config_email", "estado"]`
- **Filtros adicionales**: `estado`, `fecha_inicio__gte`, `fecha_inicio__lte`

---

## Patrón de Implementación

### Estructura del Archivo `datatables.py`

```python
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from apps.shared.datatable import DataTableSpec, DataTableServer
from apps.tenant.<app>.models import <Model>
from apps.tenant.<app>.api.serializers import <Model>ListSerializer

@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def <resource>_dt(request):
    # QuerySet optimizado
    base_qs = <Model>.objects.only(*list_fields)
    
    # Extra filter (opcional)
    def extra_filter(req, qs):
        # Aplicar filtros adicionales
        return qs
    
    # Especificación DataTable
    spec = DataTableSpec(
        fields_map={0: "campo1", 1: "campo2", ...},
        search_fields=["campo1", "campo2", ...],
        base_qs=base_qs,
        serializer=<Model>ListSerializer,
        extra_filter=extra_filter,
    )
    
    return DataTableServer(spec).handle(request)
```

### Registro en `urls.py`

```python
from apps.tenant.<app>.api.datatables import <resource>_dt

urlpatterns += [
    path("dt/<resource>/", <resource>_dt, name="<app>_<resource>_dt"),
]
```

---

## Serializers Requeridos

Cada app necesita un `*ListSerializer` con campos mínimos (solo columnas visibles):

```python
class <Model>ListSerializer(serializers.ModelSerializer):
    """Serializer mínimo para listado DataTables."""
    class Meta:
        model = <Model>
        fields = ("id", "campo1", "campo2", ...)  # Solo campos visibles
        read_only_fields = ("id", ...)
```

---

**Última actualización**: 2024-12-19  
**Versión**: 1.0
