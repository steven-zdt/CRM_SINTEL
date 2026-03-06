# Ejemplo de Refactorización: CuentaContable

## Cambios Backend Aplicados ✅

### 1. Modelo (`apps/tenant/contabilidad/models.py`)
```python
import uuid

class CuentaContable(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name=_('UUID')
    )
    # ... resto de campos
```

### 2. ViewSet Base (`apps/tenant/api/base.py`)
```python
class BaseTenantViewSet(viewsets.ModelViewSet):
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
```

### 3. ViewSet (`apps/tenant/contabilidad/api/viewsets.py`)
```python
from apps.tenant.api.base import BaseTenantViewSet

class CuentaContableViewSet(BaseTenantViewSet):
    # lookup_field="uuid" ya está en BaseTenantViewSet
    # ...
```

### 4. Services (`apps/tenant/contabilidad/services.py`)
```python
CUENTA_LIST_FIELDS = (
    "id",
    "uuid",  # ✅ Agregado
    "codigo",
    # ...
)
```

### 5. Router (`apps/tenant/contabilidad/api/urls.py`)
```python
TRAILING_SLASH = True
router = DefaultRouter(trailing_slash=TRAILING_SLASH)
```

## Cambios Frontend Necesarios

### 1. Incluir api.js en workspace.html
```html
<script src="{% static 'core/js/lib/api.js' %}"></script>
```

### 2. Refactorizar cuentas.page.js

**ANTES:**
```javascript
function cuentaDetailUrl(id) {
  return `${CUENTA_COLLECTION_URL}${id}/`;
}

async function fetchCuentaDetail(id) {
  const detailUrl = cuentaDetailUrl(id);
  const response = await fetch(detailUrl, { ... });
  return await response.json();
}

async function handleVerCuenta(id) {
  const data = await fetchCuentaDetail(id);
  // ...
}

async function handleEditarCuenta(id) {
  const data = await fetchCuentaDetail(id);
  // ...
}
```

**DESPUÉS:**
```javascript
// Al inicio del archivo, después de las constantes
const { API, buildDetailUrl, safeFetchJson, getEntityKeyFromRow, assertValidKey } = window.API_HELPERS;

// Reemplazar cuentaDetailUrl
function cuentaDetailUrl(uuid) {
  assertValidKey(uuid);
  return buildDetailUrl(API.cuentas, uuid);
}

// Reemplazar fetchCuentaDetail
async function fetchCuentaDetail(uuid) {
  assertValidKey(uuid);
  const url = buildDetailUrl(API.cuentas, uuid);
  try {
    return await safeFetchJson(url, { method: 'GET' });
  } catch (err) {
    if (err.status === 404) {
      throw new Error('Cuenta no encontrada. Verifica UUID y tenant actual.');
    }
    throw err;
  }
}

// Reemplazar handleVerCuenta
async function handleVerCuenta(row) {
  const uuid = getEntityKeyFromRow(row);
  if (!uuid) {
    showFeedback('#cuenta-view-feedback', 'Error: UUID de cuenta requerido', 'error');
    return;
  }
  
  console.debug('[cuentas.page] UUID seleccionado:', uuid);
  
  try {
    const data = await fetchCuentaDetail(uuid);
    // ... llenar modal con data
  } catch (err) {
    console.error('[cuentas.page] Error en handleVerCuenta:', err);
    showFeedback('#cuenta-view-feedback', err.message || 'Error cargando cuenta', 'error');
  }
}

// Reemplazar handleEditarCuenta
async function handleEditarCuenta(row) {
  const uuid = getEntityKeyFromRow(row);
  if (!uuid) {
    showFeedback('#cuenta-edit-feedback', 'Error: UUID de cuenta requerido', 'error');
    return;
  }
  
  console.debug('[cuentas.page] UUID seleccionado para editar:', uuid);
  
  try {
    const data = await fetchCuentaDetail(uuid);
    // ... llenar modal con data
    const editModal = document.getElementById('modal-editar-cuenta');
    if (editModal) {
      editModal.dataset.uuid = uuid;  // Cambiar de data-id a data-uuid
    }
  } catch (err) {
    console.error('[cuentas.page] Error en handleEditarCuenta:', err);
    showFeedback('#cuenta-edit-feedback', err.message || 'Error cargando cuenta', 'error');
  }
}

// Reemplazar handleGuardarCuenta
async function handleGuardarCuenta() {
  const editModal = document.getElementById('modal-editar-cuenta');
  const uuid = editModal?.dataset.uuid;  // Cambiar de data-id a data-uuid
  
  if (!uuid) {
    showFeedback('#cuenta-edit-feedback', 'Error: UUID de cuenta requerido', 'error');
    return;
  }
  
  const payload = {
    codigo: document.getElementById('cuenta-edit-codigo')?.value,
    nombre: document.getElementById('cuenta-edit-nombre')?.value,
    // ... resto de campos
  };
  
  try {
    const url = buildDetailUrl(API.cuentas, uuid);
    const data = await safeFetchJson(url, {
      method: 'PATCH',
      body: payload
    });
    
    showFeedback('#cuenta-edit-feedback', 'Cuenta actualizada correctamente', 'success');
    // ... refrescar tabla y cerrar modal
  } catch (err) {
    if (err.status === 422 && err.fields) {
      // Mostrar errores por campo
      Object.keys(err.fields).forEach(field => {
        const input = document.getElementById(`cuenta-edit-${field}`);
        if (input) {
          input.classList.add('is-invalid');
          // Mostrar mensaje de error
        }
      });
      showFeedback('#cuenta-edit-feedback', 'Error de validación. Verifica los campos marcados.', 'error');
    } else {
      showFeedback('#cuenta-edit-feedback', err.message || 'Error guardando cuenta', 'error');
    }
  }
}

// En la columna de acciones, cambiar data-id por data-uuid
// ANTES:
render: (data, type, row) => `
  <button class="btn btn-sm btn-secondary btn-ver" data-id="${row.id}">Ver</button>
  <button class="btn btn-sm btn-primary btn-editar" data-id="${row.id}">Editar</button>
`

// DESPUÉS:
render: (data, type, row) => {
  const uuid = getEntityKeyFromRow(row);
  return `
    <button class="btn btn-sm btn-secondary btn-ver" data-uuid="${uuid}">Ver</button>
    <button class="btn btn-sm btn-primary btn-editar" data-uuid="${uuid}">Editar</button>
  `;
}

// En los event listeners, cambiar dataset.id por dataset.uuid
// ANTES:
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('.btn-ver');
  if (btn) {
    const id = btn.dataset.id;
    if (id) handleVerCuenta(id);
  }
});

// DESPUÉS:
document.addEventListener('click', (ev) => {
  const btn = ev.target.closest('.btn-ver');
  if (btn) {
    const uuid = btn.dataset.uuid || btn.dataset.id;  // Fallback para compatibilidad
    if (uuid) handleVerCuenta({ uuid });  // Pasar objeto row
  }
});
```

## Migración de Datos

Crear migración para backfill de UUIDs:

```python
# migrations/XXXX_backfill_cuenta_uuid.py
from django.db import migrations
import uuid

def backfill_uuids(apps, schema_editor):
    CuentaContable = apps.get_model('contabilidad', 'CuentaContable')
    for obj in CuentaContable.objects.filter(uuid__isnull=True):
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])

class Migration(migrations.Migration):
    dependencies = [
        ('contabilidad', 'XXXX_add_uuid_to_cuenta'),
    ]
    operations = [
        migrations.RunPython(backfill_uuids),
    ]
```

## Próximos Pasos

1. Aplicar el mismo patrón a `AsientoContable`
2. Replicar a todos los demás módulos (Empleado, Gasto, Proveedor, Cliente, etc.)
3. Crear migraciones para cada modelo
4. Actualizar todos los archivos JS
