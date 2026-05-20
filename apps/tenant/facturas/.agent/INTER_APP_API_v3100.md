# Facturas Inter-App API — v3.10.0

**ABIERTO PARA LECTURA DESDE APPS DE NEGOCIO**

---

## Contrato

Desde v3.10.0, las apps de negocio (Contabilidad, Proyectos, Gastos, Empleados, Proveedores, Clientes, etc.) pueden acceder a **TODOS** los datos de Facturas sin restricción de `empresa_id`.

### Ubicación SSoT

```python
from apps.tenant.facturas.services import FacturaInterAppAPI
```

---

## API Disponible

### 1. `list_all()` — QuerySet de TODAS las facturas

```python
from apps.tenant.facturas.services import FacturaInterAppAPI

# Sin filtro — todas las facturas
qs = FacturaInterAppAPI.list_all()
for factura in qs:
    print(factura.numero, factura.total)

# Con búsqueda
qs = FacturaInterAppAPI.list_all(search='123456')  # busca por numero/cufe/razon_social

# Iteración segura con .only()
qs = FacturaInterAppAPI.list_all().only('numero', 'total', 'fecha_emision')

# Agregación
from django.db.models import Sum
total = qs.aggregate(Sum('total'))['total__sum']
```

### 2. `get_by_id()` / `get_by_uuid()`

```python
factura = FacturaInterAppAPI.get_by_id(factura_id=123)
factura = FacturaInterAppAPI.get_by_id(factura_uuid='550e8400-e29b-41d4-a716-446655440000')
```

### 3. `get_by_cufe()` / `get_by_numero()`

```python
factura = FacturaInterAppAPI.get_by_cufe('430078201999970062490010001000000003320050313521512')
factura = FacturaInterAppAPI.get_by_numero('PV001-00000001')
```

### 4. `summary_all()` — Resumen consolidado

```python
summary = FacturaInterAppAPI.summary_all()
# {
#     "ventas": {
#         "subtotal_neto": Decimal('1000000.00'),
#         "impuestos_neto": Decimal('180000.00'),
#         "total_neto": Decimal('1180000.00'),
#         "cantidad": 150
#     },
#     "compras": {...}
# }
```

---

## Reglas de Uso

### ✅ Permitido

- Lectura con `.filter()`, `.aggregate()`, `.count()`, etc.
- Pasar QuerySet como argumento a otras funciones
- Usar `.only()` / `.defer()` para optimización
- Llamadas desde servicios internos (NO APIs HTTP)

### ❌ Prohibido

- **NUNCA desde API HTTP** (ViewSets) — usar `FacturaSelectors.qs_list(empresa_id=<user's empresa_id>)` en lugar de FacturaInterAppAPI
- **Escritura/mutación** — usar `FacturaBusinessService` con empresa_id válido + DSV
- **Exposición directa a cliente HTTP** — filtrar resultados según contexto del usuario

---

## Ejemplos de Integración

### Contabilidad — Buscar facturas para contabilizar

```python
# apps/tenant/contabilidad/services/extractores/gasto_extractor.py
from apps.tenant.facturas.services import FacturaInterAppAPI

class FacturaExtractor:
    @staticmethod
    def obtener_facturas_no_contabilizadas():
        qs = FacturaInterAppAPI.list_all()
        return qs.filter(
            naturaleza=Factura.Naturaleza.COMPRA,
            estado='ACEPTADA',
            # ... otros filtros
        ).only('uuid', 'numero', 'total', 'fecha_emision')
```

### Proyectos — Vincular factura a proyecto

```python
# apps/tenant/proyectos/services/proyecto_service.py
from apps.tenant.facturas.services import FacturaInterAppAPI

class ProyectoBusinessService:
    @staticmethod
    def vincular_factura(proyecto_id, factura_uuid):
        factura = FacturaInterAppAPI.get_by_id(factura_uuid=factura_uuid)
        if not factura:
            raise ValueError(f"Factura {factura_uuid} no existe")
        
        proyecto = Proyecto.objects.get(id=proyecto_id)
        proyecto.factura = factura
        proyecto.save()
```

### Dashboard — Mostrar indicadores consolidados

```python
# apps/tenant/core/services/dashboard_service.py
from apps.tenant.facturas.services import FacturaInterAppAPI

class DashboardService:
    @staticmethod
    def resumen_financiero():
        return FacturaInterAppAPI.summary_all()
```

---

## Cambios desde v3.9.x

| Versión | Cambio |
|---------|--------|
| < v3.9.0 | Apps usaban imports directo desde `models.py` (sin selector) |
| v3.9.0-3.9.5 | Selectors aceptaban `empresa_id=None` pero sin documentación clara |
| **v3.10.0** | ✅ **Nueva clase `FacturaInterAppAPI`** — contrato explícito + métodos convenientes |

---

## Seguridad

**Importante:** FacturaInterAppAPI devuelve datos SIN filtro empresa_id. Esto es correcto para:
- Extracciones en lotes (Contabilidad)
- Búsquedas consolidadas (Dashboard)
- Integraciones entre módulos internos

**PROHIBIDO exponerlo directamente a HTTP:**
```python
# ❌ INCORRECTO — Expone datos de TODAS las empresas al usuario
class FacturaAPIView(APIView):
    def get(self, request):
        qs = FacturaInterAppAPI.list_all()  # PELIGRO: sin filtro usuario
        return Response(...)

# ✅ CORRECTO — Filtra por empresa_id del usuario
class FacturaAPIView(APIView):
    def get(self, request):
        empresa_id = request.user.tenant_profile.empresa_id
        qs = FacturaSelectors.qs_list(empresa_id=empresa_id)
        return Response(...)
```

---

## Backward Compatibility

✅ Métodos anteriores siguen funcionando:
- `FacturaSelectors.qs_list(empresa_id=None)` — sigue abierto
- Imports directo desde `models.py` — permitidos pero deprecated
- Llamadas con `empresa_id=<int>` — siguen filtrando correctamente

Recomendación: refactorizar imports antiguos a usar `FacturaInterAppAPI` para claridad.

---

## Soporte

Si una app necesita acceso a datos de Factura no cubiertos por FacturaInterAppAPI:
1. Crear issue documentando el caso de uso
2. Agregar método a `FacturaInterAppAPI` en business_service.py
3. Exportar desde `__init__.py`
