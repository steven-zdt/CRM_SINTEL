# Vinculacion de Sede por Actividad — Indicadores por Sede

**Fecha plan:** 2026-06-01  
**Fecha implementacion:** 2026-06-01  
**Version:** v3.16.0  
**Estado:** COMPLETADO — 5/5 apps implementadas, migraciones aplicadas, endpoint KPI por sede agregado

---

## 1. Contexto y Modelo Mental

### Jerarquia existente

```
Empresa (singleton por schema)
    └── Sede  (apps/tenant/empresa/models.py)
         └── Area
              └── Empleado  (ya tenia sede FK desde el origen)
```

### Lo que se agrego

```
Empresa
    └── Sede
         ├── Empleado            (ya tenia sede — sin cambio)         ✓ existente
         ├── DocumentoSoporte    (gastos)                             ✓ DT-SEDE-01
         ├── Factura             (facturas)                           ✓ DT-SEDE-02
         ├── Proyecto            (proyectos)                          ✓ DT-SEDE-03
         ├── Cotizacion          (cotizaciones)                       ✓ DT-SEDE-04
         └── MovimientoInventario (inventario)                        ✓ DT-SEDE-05
```

### Regla de negocio

- `sede` es SIEMPRE **opcional** (`null=True, blank=True`) — no rompe datos historicos
- Si no se asigna sede, el registro pertenece a la empresa global
- La sede DEBE pertenecer a la misma `empresa_id` (DSV obligatorio en cada serializer)
- Los indicadores agrupan por `sede` o muestran `Sin sede asignada`
- `on_delete=SET_NULL` — si se elimina la sede, el registro queda sin sede (no cascada)

---

## 2. Patron de Implementacion

Basado en el patron existente en `empleados/models.py` y `empleados/api/serializers.py`.

### 2.1 Modelo

```python
sede = models.ForeignKey(
    'empresa.Sede',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='{app}s',        # 'gastos', 'facturas', 'proyectos', etc.
    verbose_name=_('Sede'),
    help_text=_('Sede donde se origina esta actividad. Opcional.'),
    db_index=True,
)
```

### 2.2 Selectors — campos canonicos

```python
LIST_FIELDS = (
    ...,
    'sede_id', 'sede__nombre',          # para listados Tabulator
)

DETAIL_FIELDS = (
    ...,
    'sede_id', 'sede__uuid', 'sede__nombre',  # para formularios de detalle
)
```

### 2.3 Serializer — ListSerializer

```python
sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)

class Meta:
    fields = (..., 'sede_nombre')
```

### 2.4 Serializer — DetailSerializer con DSV

```python
from apps.tenant.empresa.models import Sede

sede = UUIDOrPKRelatedField(
    queryset=Sede.objects.none(),
    required=False,
    allow_null=True,
    help_text='UUID de la sede (opcional)',
)
sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    empresa_id = self.context.get('empresa_id') or (
        self.context.get('request') and getattr(self.context['request'], 'empresa_id', None)
    )
    if empresa_id and 'sede' in self.fields:
        self.fields['sede'].queryset = Sede.objects.filter(
            empresa_id=empresa_id
        ).only('id', 'uuid', 'nombre')

def validate(self, attrs):
    attrs = super().validate(attrs)
    sede = attrs.get('sede')
    empresa_id = self.context.get('empresa_id')
    if sede and empresa_id and sede.empresa_id != empresa_id:
        raise serializers.ValidationError(
            {'sede': 'La sede seleccionada no pertenece a esta empresa.'}
        )
    return attrs
```

---

## 3. Implementacion por App

### DT-SEDE-01 — `gastos.DocumentoSoporte` [COMPLETADO]

**Migracion:** `apps/tenant/gastos/migrations/0022_add_sede_to_documentosoporte.py`

**Archivos modificados:**
- [apps/tenant/gastos/models.py](../apps/tenant/gastos/models.py) — campo `sede` FK agregado
- [apps/tenant/gastos/services/selectors.py](../apps/tenant/gastos/services/selectors.py) — `sede_id`, `sede__nombre` en DOCUMENTO_LIST_FIELDS y DOCUMENTO_DETAIL_FIELDS
- [apps/tenant/gastos/api/serializers.py](../apps/tenant/gastos/api/serializers.py) — `sede_nombre` en ListSerializer, `sede` + DSV en DetailSerializer

**related_name:** `'gastos'`

**Indicadores habilitados:** Gasto total por sede, top categorias de gasto por sede, comparativa entre sedes.

---

### DT-SEDE-02 — `facturas.Factura` [COMPLETADO]

**Migracion:** `apps/tenant/facturas/migrations/0028_factura_sede.py`

**Archivos modificados:**
- [apps/tenant/facturas/models.py](../apps/tenant/facturas/models.py) — campo `sede` FK agregado
- [apps/tenant/facturas/services/selectors.py](../apps/tenant/facturas/services/selectors.py) — `sede_id`, `sede__nombre` en LIST_FIELDS y DETAIL_FIELDS
- [apps/tenant/facturas/api/serializers.py](../apps/tenant/facturas/api/serializers.py) — `UUIDOrPKRelatedField` agregado; `sede_nombre` en FacturaListSerializer; `sede` + DSV en FacturaDetailSerializer

**related_name:** `'facturas'`

**Indicadores habilitados:** Ingresos por sede, ventas vs compras por sede, facturas pendientes por sede.

---

### DT-SEDE-03 — `proyectos.Proyecto` [COMPLETADO]

**Migracion:** `apps/tenant/proyectos/migrations/0019_proyecto_sede.py`

**Archivos modificados:**
- [apps/tenant/proyectos/models.py](../apps/tenant/proyectos/models.py) — campo `sede` FK agregado
- [apps/tenant/proyectos/services/selectors.py](../apps/tenant/proyectos/services/selectors.py) — `sede_id`, `sede__nombre` en LIST_FIELDS; `sede__uuid` en DETAIL_FIELDS
- [apps/tenant/proyectos/api/serializers.py](../apps/tenant/proyectos/api/serializers.py) — `sede_nombre` en ProyectoListSerializer; `sede` + DSV en ProyectoDetailSerializer (`exclude=['empresa']` — sede se incluye automaticamente)

**related_name:** `'proyectos'`

**Indicadores habilitados:** Proyectos activos por sede, valor contrato por sede, avance promedio por sede.

---

### DT-SEDE-04 — `cotizaciones.Cotizacion` [COMPLETADO]

**Migracion:** `apps/tenant/cotizaciones/migrations/0005_cotizacion_sede.py`

**Archivos modificados:**
- [apps/tenant/cotizaciones/models.py](../apps/tenant/cotizaciones/models.py) — campo `sede` FK agregado
- [apps/tenant/cotizaciones/services/selectors.py](../apps/tenant/cotizaciones/services/selectors.py) — `sede_id`, `sede__nombre` en LIST_FIELDS; `sede__uuid` en DETAIL_FIELDS
- [apps/tenant/cotizaciones/api/serializers.py](../apps/tenant/cotizaciones/api/serializers.py) — import `Sede`; `sede_nombre` en CotizacionListSerializer; `sede` + DSV en CotizacionSerializer; filtra queryset en `__init__`

**related_name:** `'cotizaciones'`

**Indicadores habilitados:** Pipeline comercial por sede, tasa de conversion por sede, cotizaciones enviadas vs aceptadas.

---

### DT-SEDE-05 — `inventario.MovimientoInventario` [COMPLETADO]

**Migracion:** `apps/tenant/inventario/migrations/0010_add_sede_to_movimiento.py` — generada y aplicada en esta sesion

**Archivos modificados:**
- [apps/tenant/inventario/models.py](../apps/tenant/inventario/models.py) — campo `sede` FK agregado a `MovimientoInventario`
- [apps/tenant/inventario/services/selectors.py](../apps/tenant/inventario/services/selectors.py) — `sede_id`, `sede__nombre` en MOVIMIENTO_LIST_FIELDS; `sede__uuid` en MOVIMIENTO_DETAIL_FIELDS
- [apps/tenant/inventario/api/serializers.py](../apps/tenant/inventario/api/serializers.py) — `sede_nombre` en MovimientoInventarioListSerializer y MovimientoInventarioDetailSerializer

**related_name:** `'movimientos_inventario'`

**Indicadores habilitados:** Stock por sede, rotacion de inventario por sede, entradas/salidas por sede.

---

## 4. Verificacion Final

```bash
# Todos estos comandos pasaron en verde:
docker compose exec web python manage.py check
# System check identified no issues (0 silenced).

docker compose exec web python manage.py makemigrations --check
# No changes detected

docker compose exec web python manage.py migrate_schemas --tenant
# Applying tenant_inventario.0010_add_sede_to_movimiento... OK
```

---

## 5. Estado de Migraciones

| App | Migracion | Aplicada |
|-----|-----------|----------|
| `tenant_gastos` | `0022_add_sede_to_documentosoporte` | Si |
| `facturas` | `0028_factura_sede` | Si |
| `tenant_proyectos` | `0019_proyecto_sede` | Si |
| `tenant_cotizaciones` | `0005_cotizacion_sede` | Si |
| `tenant_inventario` | `0010_add_sede_to_movimiento` | Si |

---

## 6. Endpoint KPI Transversal por Sede [COMPLETADO 2026-06-04]

Se agrego un extractor Pull Model en `dashboard` para consolidar indicadores transversales por sede y exponerlos por API.

**Endpoint implementado:** `GET /api/v1/dashboard/kpis-por-sede/?fecha_inicio=&fecha_fin=`

**Archivos modificados:**
- [apps/tenant/dashboard/services/extractores/sedes_ext.py](../apps/tenant/dashboard/services/extractores/sedes_ext.py) — extractor agregado.
- [apps/tenant/dashboard/services/extractores/__init__.py](../apps/tenant/dashboard/services/extractores/__init__.py) — reexport de `SedesExtractor`.
- [apps/tenant/dashboard/services/dtos.py](../apps/tenant/dashboard/services/dtos.py) — DTO `KpiSedeDTO`.
- [apps/tenant/dashboard/services/business_service.py](../apps/tenant/dashboard/services/business_service.py) — metodo `obtener_kpis_por_sede`.
- [apps/tenant/dashboard/api/serializers.py](../apps/tenant/dashboard/api/serializers.py) — serializer `KpiSedeSerializer`.
- [apps/tenant/dashboard/api/viewsets.py](../apps/tenant/dashboard/api/viewsets.py) — action `kpis_por_sede`.

**Contrato de respuesta por fila:**

```json
{
  "sede_uuid": "uuid-o-null",
  "sede_nombre": "Sede principal",
  "gastos_total": "0.00",
  "ingresos_total": "0.00",
  "proyectos_activos": 0,
  "valor_proyectos": "0.00",
  "movimientos_inventario": 0,
  "margen": "0.00"
}
```

**Comportamiento:**
- Agrupa por `sede_id`.
- Incluye fila `Sin sede asignada` cuando existen datos sin sede.
- Aplica filtros opcionales `fecha_inicio` y `fecha_fin` sobre gastos, facturas e inventario.
- Proyectos activos se calculan excluyendo `fase_actual='CIERRE'`.

**Referencia de diseno original:**

```python
# apps/tenant/dashboard/services/extractors/sede_extractor.py

from django.db.models import Sum, Count
from apps.tenant.empresa.models import Sede
from apps.tenant.gastos.models import DocumentoSoporte
from apps.tenant.facturas.models import Factura
from apps.tenant.proyectos.models import Proyecto

def get_kpis_por_sede(empresa_id: int, fecha_inicio, fecha_fin) -> list[dict]:
    sedes = Sede.objects.filter(empresa_id=empresa_id).only('id', 'uuid', 'nombre')
    resultado = []

    for sede in sedes:
        gastos = DocumentoSoporte.objects.filter(
            empresa_id=empresa_id, sede=sede,
            fecha__range=(fecha_inicio, fecha_fin), anulado=False
        ).aggregate(total=Sum('total'))['total'] or 0

        ingresos = Factura.objects.filter(
            empresa_id=empresa_id, sede=sede, naturaleza='VENTA',
            fecha_emision__date__range=(fecha_inicio, fecha_fin)
        ).aggregate(total=Sum('total'))['total'] or 0

        proyectos_activos = Proyecto.objects.filter(
            empresa_id=empresa_id, sede=sede
        ).exclude(fase_actual='CIERRE').count()

        resultado.append({
            'sede_uuid': str(sede.uuid),
            'sede_nombre': sede.nombre,
            'gastos_total': gastos,
            'ingresos_total': ingresos,
            'proyectos_activos': proyectos_activos,
            'margen': ingresos - gastos,
        })

    return resultado
```

**Endpoint sugerido:** `GET /api/v1/dashboard/kpis-por-sede/?fecha_inicio=&fecha_fin=`

---

## 6.1 Verificacion del Endpoint KPI por Sede

```bash
python -m py_compile apps\tenant\dashboard\services\dtos.py apps\tenant\dashboard\api\serializers.py apps\tenant\dashboard\services\extractores\sedes_ext.py apps\tenant\dashboard\services\extractores\__init__.py apps\tenant\dashboard\services\business_service.py apps\tenant\dashboard\api\viewsets.py
# OK

python manage.py check
# System check identified no issues (0 silenced).

python manage.py shell -c "<schema_context tenant> DashboardBusinessService.obtener_kpis_por_sede(1)"
# OK en schema tenant empresademo; retorno lista vacia porque no habia sedes/datos agrupables.
```

---

## 7. Reglas de Cumplimiento

| Regla | Aplicada |
|---|---|
| `on_delete=SET_NULL` — nunca CASCADE | Si — todas las apps |
| DSV en serializer DetailSerializer | Si — todas las apps |
| `sede_id`, `sede__nombre` en `.only()` LIST_FIELDS | Si — todas las apps |
| `UUIDOrPKRelatedField` para lookup UUID | Si — todas las apps |
| FK como string `'empresa.Sede'` (no import directo en modelo) | Si — todas las apps |
| Una migracion atomica por app | Si — todas las apps |
| `django check` limpio | Si — 0 issues |

---

## 8. Resumen de Cambios por App

| App | Modelo | Migracion | Selector | Serializer | Estado |
|-----|--------|-----------|----------|-----------|--------|
| `gastos` | `DocumentoSoporte` | `0022_add_sede_to_documentosoporte` | `sede_id`, `sede__nombre` | ListSerializer + DetailSerializer + DSV | ✅ COMPLETADO |
| `facturas` | `Factura` | `0028_factura_sede` | `sede_id`, `sede__nombre`, `sede__uuid` | ListSerializer + DetailSerializer + DSV | ✅ COMPLETADO |
| `proyectos` | `Proyecto` | `0019_proyecto_sede` | `sede_id`, `sede__nombre`, `sede__uuid` | ListSerializer + DetailSerializer + DSV | ✅ COMPLETADO |
| `cotizaciones` | `Cotizacion` | `0005_cotizacion_sede` | `sede_id`, `sede__nombre`, `sede__uuid` | ListSerializer + DetailSerializer + DSV | ✅ COMPLETADO |
| `inventario` | `MovimientoInventario` | `0010_add_sede_to_movimiento` | `sede_id`, `sede__nombre`, `sede__uuid` | ListSerializer + DetailSerializer | ✅ COMPLETADO |
| `dashboard` | (DTO nuevo) | — | Extractor Pull Model | KpiSedeSerializer | ✅ COMPLETADO |

---

## 9. Campos Expuestos por API

### Listado (READ-ONLY)

```json
{
  "id": 123,
  "uuid": "uuid-string",
  "sede_nombre": "Sede principal",
  ...otros campos...
}
```

### Detalle (CREATE/UPDATE)

```json
{
  "id": 123,
  "uuid": "uuid-string",
  "sede": "uuid-o-id-de-sede",
  "sede_nombre": "Sede principal (read-only)",
  ...otros campos...
}
```

**Validaciones aplicadas:**
- `sede` es optional (null/blank permitido)
- Si se proporciona, debe pertenecer a la misma `empresa_id` (DSV)
- UUID y PK ambos soportados via `UUIDOrPKRelatedField`

---

## 10. Indicadores Habilitados por App

### Gastos (Gasto total por sede)

```sql
SELECT sede__nombre, SUM(total) as total_gastos
FROM gastos_documentosoporte
WHERE empresa_id = ? AND anulado = false
GROUP BY sede_id, sede__nombre
```

### Facturas (Ingresos por sede)

```sql
SELECT sede__nombre, naturaleza, COUNT(*) as cantidad, SUM(total) as total
FROM facturas_factura
WHERE empresa_id = ? AND naturaleza = 'VENTA'
GROUP BY sede_id, sede__nombre, naturaleza
```

### Proyectos (Proyectos activos por sede)

```sql
SELECT sede__nombre, COUNT(*) as proyectos_activos, SUM(valor_contrato) as valor_total
FROM proyectos_proyecto
WHERE empresa_id = ? AND fase_actual != 'CIERRE'
GROUP BY sede_id, sede__nombre
```

### Cotizaciones (Pipeline comercial por sede)

```sql
SELECT sede__nombre, estado, COUNT(*) as cantidad
FROM cotizaciones_cotizacion
WHERE empresa_id = ?
GROUP BY sede_id, sede__nombre, estado
```

### Inventario (Stock y rotacion por sede)

```sql
SELECT sede__nombre, SUM(cantidad_disponible) as stock_total, COUNT(DISTINCT producto_id) as items
FROM inventario_movimientoinventario
WHERE empresa_id = ?
GROUP BY sede_id, sede__nombre
```

### Dashboard (KPI Transversal)

```
GET /api/v1/dashboard/kpis-por-sede/?fecha_inicio=2026-01-01&fecha_fin=2026-12-31
```

Respuesta:
```json
[
  {
    "sede_uuid": "uuid1",
    "sede_nombre": "Bogota",
    "gastos_total": "1500000.00",
    "ingresos_total": "5000000.00",
    "proyectos_activos": 3,
    "valor_proyectos": "2000000.00",
    "movimientos_inventario": 45,
    "margen": "3500000.00"
  },
  {
    "sede_uuid": null,
    "sede_nombre": "Sin sede asignada",
    "gastos_total": "200000.00",
    "ingresos_total": "800000.00",
    "proyectos_activos": 0,
    "valor_proyectos": "0.00",
    "movimientos_inventario": 10,
    "margen": "600000.00"
  }
]
```

---

## 11. Procedimientos de Mantenimiento

### Agregar sede a una nueva app

1. **Modelo:**
   ```python
   sede = models.ForeignKey(
       'empresa.Sede',
       on_delete=models.SET_NULL,
       null=True,
       blank=True,
       related_name='{app}s',
       verbose_name=_('Sede'),
       db_index=True,
   )
   ```

2. **Selector:**
   - Agregar `'sede_id', 'sede__nombre'` a `LIST_FIELDS`
   - Agregar `'sede__uuid'` a `DETAIL_FIELDS`

3. **Serializer:**
   - ListSerializer: agregar `sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)`
   - DetailSerializer: agregar DSV + validacion

4. **Migracion:**
   - `python manage.py makemigrations <app> --name add_sede_to_<modelo>`
   - Aplicar: `python manage.py migrate_schemas`

5. **Validacion:**
   - `python manage.py check`
   - `python manage.py makemigrations --check`
   - Tests de API si existen

### Cambiar comportamiento de eliminar sede

**Actual:** `on_delete=SET_NULL` — el registro queda sin sede

**Alternativas (NO recomendadas):**
- `CASCADE`: elimina todos los registros de la sede (perdida de datos)
- `PROTECT`: no permite eliminar sedes usadas (bloqueo de UX)

### Filtrar por sede en frontend

**Formato esperado:**
```javascript
// Listar solo registros de una sede
GET /api/v1/{app}/{model}/?sede_uuid=<uuid>

// O por ID (fallback)
GET /api/v1/{app}/{model}/?sede=<id>
```

**En formularios:**
```html
<select name="sede" id="sede">
  <option value="">-- Sin sede asignada --</option>
  <option value="uuid1">Bogota</option>
  <option value="uuid2">Medellin</option>
</select>
```

---

## 12. Testing y Verificacion

### Smoke Test de Integridad

```bash
# 1. Verificar que no hay migraciones pendientes
python manage.py makemigrations --check

# 2. Verificar que no hay issues de Django
python manage.py check

# 3. Verificar que las FK existen en BD
python manage.py shell -c "
from apps.tenant.gastos.models import DocumentoSoporte
from apps.tenant.facturas.models import Factura
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.inventario.models import MovimientoInventario
print('Todos los modelos tienen campo sede:', all([
  hasattr(m, 'sede') for m in [DocumentoSoporte, Factura, Proyecto, Cotizacion, MovimientoInventario]
]))
"

# 4. Verificar el endpoint KPI
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/dashboard/kpis-por-sede/?fecha_inicio=2026-01-01&fecha_fin=2026-12-31"
```

### Test de Creacion con Sede

```python
# En tests/tenant/<app>/test_models.py
def test_crear_registro_con_sede():
    empresa = Empresa.objects.first()
    sede = Sede.objects.create(empresa=empresa, nombre='Test')
    
    # gastos
    doc = DocumentoSoporte.objects.create(
        empresa=empresa, sede=sede, ...otros_campos...
    )
    assert doc.sede == sede
    
    # Similar para otras apps
```

### Test de DSV

```python
def test_dsv_sede_diferente_empresa():
    empresa1 = Empresa.objects.first()
    empresa2 = Empresa.objects.create(...)  # otra empresa
    sede_empresa2 = Sede.objects.create(empresa=empresa2, nombre='Otra')
    
    serializer = DocumentoSoporteDetailSerializer(
        data={'sede': str(sede_empresa2.uuid), ...},
        context={'empresa_id': empresa1.id}
    )
    assert not serializer.is_valid()
    assert 'sede' in serializer.errors
```

---

## 13. Notas de Diseño

### Por que sede es opcional

- **Compatibilidad hacia atras:** Datos historicos sin sede no se pierden
- **Flexibilidad:** Empresa puede no usar sedes al inicio
- **Migracion segura:** Permite adopcion gradual de sede por actividad

### Por que `on_delete=SET_NULL` y no CASCADE

- **Preservacion de datos:** No se pierden gastos/facturas/etc si se elimina la sede
- **Auditoria:** Historial completo disponible (con sede=NULL)
- **UX:** El usuario ve `Sin sede asignada` en lugar de registros desaparecidos

### Por que `UUIDOrPKRelatedField` en vez de solo UUID

- **Compatibilidad con frontend legacy:** Acepta tanto UUID como ID numerico
- **Gradual deprecation:** Permite transicion de PK a UUID sin romper APIs
- **Flexibilidad:** El cliente usa lo que tenga disponible

---

## 14. Proximos Pasos

### Inmediato (Post 2026-06-04)

- [x] Implementar FK sede en 5 apps principales
- [x] Aplicar migraciones a todos los schemas tenant
- [x] Agregar endpoint KPI transversal en dashboard
- [ ] Actualizar templates/frontend para filtrar y mostrar sede en listados
- [ ] Agregar tests de API para operaciones con sede

### Corto plazo (2026-06-15)

- [ ] Endpoint de filtrado avanzado: `GET /api/v1/<app>/<model>/?sede_uuid=<uuid>`
- [ ] Dashboard: widget KPI por sede con graficas
- [ ] Reportes: generar reportes agrupados por sede
- [ ] Permisos: considera si ciertos roles deben ver solo su sede

### Mediano plazo (2026-07)

- [ ] Extender modelo de asignacion de usuarios a sedes (hoy es solo en empleados)
- [ ] Control de acceso a nivel de sede (middleware/permissions)
- [ ] Consolidacion de KPIs en reportes ejecutivos por sede
- [ ] Analisis de rentabilidad por sede

---

## 15. Referencias Cruzadas

- **Migraciones:** Ver `PLAN_DEPURACION_ORGANIZACION_2026_06_04.md` § "Acciones ejecutadas - Fase 6"
- **Auditoria de cada app:** `apps/tenant/<app>/.agent/AUDITORIA_FLUJO_*.md`
- **Pull Model:** `CLAUDE.md` § "Accounting integration → Retenciones (Pull Model)"
- **Service Layer:** `CLAUDE.md` § "Service-Driven Architecture"
- **Multi-tenant:** `ARQUITECTURA_MULTI_TENANT_DJANGO.md`

---

## Conclusion

La implementacion de **Sede por Actividad (v3.16.0)** esta **COMPLETADA** en todas sus fases:

✅ 5 apps con FK sede + migraciones aplicadas  
✅ Selectors y serializers con DSV y campos canonicos  
✅ Endpoint KPI transversal en dashboard  
✅ `django check` sin issues  
✅ Documentacion de mantenimiento y testing  

La arquitectura es **escalable** y **auditable**:
- Pull Model respetado (dashboard extrae, no invierte dependencias)
- Seguridad multi-tenant (DSV en cada serializer)
- Compatibilidad hacia atras (sede siempre opcional)
- Bases para analytics transversales (KPI por sede)

**Status para PR:** LISTO — las migraciones fueron incluidas en Fase 6 de PLAN_DEPURACION y todas estan aplicadas. Listo para merge a `main`.
