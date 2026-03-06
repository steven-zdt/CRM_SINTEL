# Plan de Refactorización UUID + API Unificada

## Estado Actual

✅ **Completado:**
- Módulo centralizado de API helpers (`apps/tenant/core/static/core/js/lib/api.js`)
- Helpers: `buildDetailUrl`, `safeFetchJson`, `getEntityKeyFromRow`, `mapResponsabilidadesToCodes`

## Próximos Pasos (Sistema)

### 1. Backend: Agregar UUID a Modelos

Para cada modelo en `TENANT_APPS` que tenga endpoint de detalle:

```python
# En models.py
import uuid
from django.db import models

class TuModelo(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name='UUID'
    )
    # ... resto de campos
```

**Modelos a actualizar:**
- [ ] `CuentaContable` (contabilidad)
- [ ] `AsientoContable` (contabilidad)
- [ ] `Empleado` (empleados)
- [ ] `Gasto` (gastos)
- [ ] `Proveedor` (proveedores)
- [ ] `Cliente` (clientes)
- [ ] `CatalogoItem` (inventario)
- [ ] `ActivoFijo` (inventario)
- [ ] `MovimientoInventario` (inventario)
- [ ] `Empresa` (empresa) - singleton, pero puede tener uuid
- [ ] `Factura` (facturas) - si tiene endpoint de detalle
- [ ] Otros modelos con ViewSets de detalle

### 2. Backend: Migraciones

Para cada modelo, crear migración:

```bash
python manage.py makemigrations <app_name>
```

Luego crear migración de datos para backfill:

```python
# migrations/XXXX_backfill_uuid.py
from django.db import migrations
import uuid

def backfill_uuids(apps, schema_editor):
    TuModelo = apps.get_model('app_name', 'TuModelo')
    for obj in TuModelo.objects.filter(uuid__isnull=True):
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])

class Migration(migrations.Migration):
    dependencies = [
        ('app_name', 'XXXX_add_uuid_field'),
    ]
    operations = [
        migrations.RunPython(backfill_uuids),
    ]
```

### 3. Backend: ViewSet Base

Crear ViewSet base con `lookup_field="uuid"`:

```python
# apps/tenant/api/base.py
from rest_framework import viewsets

class BaseTenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet base para modelos tenant con lookup por UUID.
    """
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
```

### 4. Backend: Actualizar ViewSets

Para cada ViewSet:

```python
# Antes
class CuentaContableViewSet(viewsets.ModelViewSet):
    queryset = CuentaContable.objects.all()
    # ...

# Después
from apps.tenant.api.base import BaseTenantViewSet

class CuentaContableViewSet(BaseTenantViewSet):
    queryset = CuentaContable.objects.all()
    # lookup_field="uuid" ya está en BaseTenantViewSet
```

### 5. Backend: Actualizar Serializers

Agregar `uuid` a todos los serializers (list y detail):

```python
class CuentaContableListSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    class Meta:
        model = CuentaContable
        fields = ('uuid', 'codigo', 'nombre', ...)

class CuentaContableDetailSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    class Meta:
        model = CuentaContable
        fields = ('uuid', 'codigo', 'nombre', ...)  # todos los campos
```

### 6. Backend: Unificar Trailing Slash

En todos los routers (`**/urls.py`):

```python
from rest_framework.routers import DefaultRouter

# ⚠️ UNIFICAR: Todos los routers deben usar el mismo trailing_slash
TRAILING_SLASH = True  # Debe coincidir con frontend

router = DefaultRouter(trailing_slash=TRAILING_SLASH)
```

### 7. Frontend: Incluir api.js

En `workspace.html` o template base, incluir antes de otros scripts:

```html
<script src="{% static 'core/js/lib/api.js' %}"></script>
```

### 8. Frontend: Refactorizar *.page.js

Para cada archivo `*.page.js`, reemplazar:

**ANTES:**
```javascript
function cuentaDetailUrl(id) {
  return `${API_INDEX}${id}/`;
}

async function fetchCuentaDetail(id) {
  const url = cuentaDetailUrl(id);
  const res = await fetch(url, { ... });
  // ...
}
```

**DESPUÉS:**
```javascript
const { API, buildDetailUrl, safeFetchJson, getEntityKeyFromRow, assertValidKey } = window.API_HELPERS;

async function fetchCuentaDetail(uuid) {
  assertValidKey(uuid);
  const url = buildDetailUrl(API.cuentas, uuid);
  return await safeFetchJson(url, { method: 'GET' });
}

function handleEditarCuenta(row) {
  const uuid = getEntityKeyFromRow(row);
  console.debug('[cuentas.page] UUID seleccionado:', uuid);
  fetchCuentaDetail(uuid)
    .then(data => openCuentaModalConDatos(data))
    .catch(err => {
      if (err.status === 404) {
        showError('No encontrado. Verifica UUID y tenant actual.');
      } else {
        showError('Error cargando cuenta', err);
      }
    });
}
```

### 9. Frontend: Eliminar IDs Hardcodeados

Buscar y reemplazar:
- `id = 1` → `uuid = getEntityKeyFromRow(row)`
- `data-id="1"` → `data-uuid="${row.uuid}"`
- URLs hardcodeadas → `buildDetailUrl(API.recurso, uuid)`

### 10. Empresa: Responsabilidades RUT

**Backend:**
```python
# apps/tenant/empresa/api/views.py
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def responsabilidades_rut_choices(request):
    choices = [
        ("48", "IVA como agente de retención"),
        # ... completar con códigos oficiales
    ]
    return Response([{"code": c, "label": l} for c, l in choices])
```

**Frontend:**
```javascript
const { mapResponsabilidadesToCodes } = window.API_HELPERS;

async function guardarEmpresa(formValues) {
  const payload = { ...formValues };
  payload.responsabilidades_rut_codigos = mapResponsabilidadesToCodes(
    formValues.responsabilidadesSeleccionadas
  );
  
  const uuid = formValues.uuid || formValues.id;
  const url = buildDetailUrl(API.empresas, uuid);
  
  try {
    const data = await safeFetchJson(url, {
      method: 'PATCH',
      body: payload
    });
    notify('Empresa actualizada');
    return data;
  } catch (err) {
    if (err.status === 422 && err.fields?.responsabilidades_rut_codigos) {
      showFieldError('responsabilidades_rut_codigos', 
        err.fields.responsabilidades_rut_codigos.join('; '));
    }
    throw err;
  }
}
```

## Checklist de Aceptación

- [ ] Backend: Todos los ViewSets con `lookup_field="uuid"`
- [ ] Backend: Todos los modelos con campo `uuid` y migraciones aplicadas
- [ ] Backend: Todos los serializers incluyen `uuid` en list y detail
- [ ] Backend: Todos los routers con `trailing_slash=True` unificado
- [ ] Frontend: `api.js` incluido en templates
- [ ] Frontend: Todos los `*.page.js` usan `buildDetailUrl` y `safeFetchJson`
- [ ] Frontend: No hay IDs hardcodeados (`1`, etc.)
- [ ] Frontend: `getEntityKeyFromRow` usado para obtener UUID
- [ ] Empresa: Endpoint de choices para responsabilidades RUT
- [ ] Empresa: Mapeo correcto de responsabilidades a códigos
- [ ] Tests: GET detail con UUID válido → 200
- [ ] Tests: GET detail con UUID inexistente → 404
- [ ] Tests: PATCH empresa con responsabilidades válidas → 200
- [ ] Tests: PATCH empresa con código inválido → 422

## Orden de Ejecución Recomendado

1. Crear ViewSet base y actualizar un ViewSet de prueba
2. Agregar uuid a un modelo de prueba y crear migración
3. Actualizar serializer del modelo de prueba
4. Refactorizar un archivo JS de prueba
5. Verificar que funciona end-to-end
6. Replicar patrón a todos los demás módulos
