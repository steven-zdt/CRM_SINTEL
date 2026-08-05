# Admin Site Aislado para Tenants Privados

## ✅ Implementación Completada

### Objetivo
Crear un `TenantAdminSite` personalizado que **SOLO** muestre los modelos pertenecientes a `TENANT_APPS`, eliminando cualquier rastro de la administración pública (Client, Domain, etc.).

---

## 📁 Archivos Creados/Modificados

### 1. `apps/tenant/core/admin.py` (NUEVO)

**Contenido:**
- `TenantAdminSite`: Admin Site personalizado para tenants
- `tenant_admin_site`: Instancia aislada del admin
- `register_tenant_apps()`: Función que filtra y copia modelos de TENANT_APPS
- `ensure_tenant_apps_registered()`: Función segura para registro

**Características:**
- ✅ Solo muestra modelos de `TENANT_APPS`
- ✅ Filtra automáticamente modelos del esquema público
- ✅ Copia la configuración de ModelAdmin (list_display, fieldsets, etc.)
- ✅ Validación de permisos (solo usuarios activos y staff)

### 2. `apps/tenant/core/apps.py` (MODIFICADO)

**Cambios:**
- Agregado método `ready()` que ejecuta el registro después de que todas las apps estén listas
- Garantiza que todos los admin.py de tenant ya hayan registrado sus modelos

### 3. `config/urls_tenant.py` (MODIFICADO)

**Cambios:**
- Importa `tenant_admin_site` desde `apps.tenant.core.admin`
- Reemplaza `admin.site.urls` por `tenant_admin_site.urls`
- Comentarios explicativos sobre el aislamiento

---

## 🔄 Flujo de Funcionamiento

### 1. Inicialización

1. Django carga todas las apps según `INSTALLED_APPS`
2. Cada app de tenant registra sus modelos en `admin.site` (usando `@admin.register()`)
3. `TenantCoreConfig.ready()` se ejecuta cuando todas las apps están listas
4. `ensure_tenant_apps_registered()` copia los modelos de tenant a `tenant_admin_site`

### 2. Filtrado de Modelos

```python
# Obtener etiquetas de apps permitidas
tenant_app_labels = {'empresa', 'facturas', 'contabilidad', 'perfil', ...}

# Iterar sobre admin.site._registry
for model, model_admin in admin.site._registry.items():
    if model._meta.app_label in tenant_app_labels:
        # Registrar en tenant_admin_site
        tenant_admin_site.register(model, model_admin.__class__)
```

### 3. Acceso al Admin

- **URL:** `http://cliente.sintel.net.co:8000/admin/`
- **Admin Site:** `tenant_admin_site` (aislado)
- **Modelos visibles:** Solo modelos de `TENANT_APPS`
- **Modelos NO visibles:** Client, Domain, User (del esquema público)

---

## 📋 Modelos Incluidos

### Modelos de Tenant (VISIBLES en tenant_admin_site)

- ✅ `Empresa` (app: `empresa`)
- ✅ `Factura` (app: `facturas`)
- ✅ `ItemFactura` (app: `facturas`)
- ✅ `AsientoContable` (app: `contabilidad`)
- ✅ `CuentaContable` (app: `contabilidad`)
- ✅ `MovimientoContable` (app: `contabilidad`)

### Modelos del Esquema Público (NO VISIBLES en tenant_admin_site)

- ❌ `Client` (app: `tenants`)
- ❌ `Domain` (app: `tenants`)
- ❌ `TenantMembership` (app: `tenants`)
- ❌ `User` (app: `accounts`) - Usuarios globales
- ❌ Cualquier otro modelo de `SHARED_APPS`

---

## 🔒 Garantías de Seguridad

### 1. Aislamiento Total
- ✅ `tenant_admin_site` es completamente independiente de `admin.site`
- ✅ Los modelos del esquema público NO aparecen en el admin de tenant
- ✅ No hay forma de acceder a modelos públicos desde el admin de tenant

### 2. Validación de Permisos
- ✅ Solo usuarios activos (`is_active=True`) pueden acceder
- ✅ Solo usuarios staff (`is_staff=True`) pueden acceder
- ✅ Validación adicional en `TenantAdminSite.has_permission()`

### 3. Filtrado Automático
- ✅ El filtrado se hace automáticamente basado en `TENANT_APPS`
- ✅ No requiere configuración manual por modelo
- ✅ Se actualiza automáticamente cuando se agregan nuevas apps de tenant

---

## 🧪 Verificación

### Test Manual

1. **Acceder al Admin de Tenant:**
   ```bash
   # URL: http://home.sintel.net.co:8000/admin/
   # Debe mostrar solo modelos de tenant (Empresa, Factura, etc.)
   # NO debe mostrar Client, Domain, etc.
   ```

2. **Verificar Modelos Visibles:**
   - ✅ Debe aparecer: Empresa, Factura, AsientoContable, etc.
   - ❌ NO debe aparecer: Client, Domain, TenantMembership

3. **Verificar Permisos:**
   - Usuario no staff → No puede acceder
   - Usuario staff → Puede acceder y ver modelos de tenant

### Test Automatizado

```bash
# Verificar que el admin site está configurado correctamente
docker compose exec web python manage.py check

# Verificar que los modelos están registrados
docker compose exec web python manage.py shell
```

```python
from apps.tenant.core.admin import tenant_admin_site
from apps.public.tenants.models import Client, Domain
from apps.tenant.empresa.models import Empresa

# Verificar que modelos de tenant están registrados
print(tenant_admin_site.is_registered(Empresa))  # Debe ser True

# Verificar que modelos públicos NO están registrados
print(tenant_admin_site.is_registered(Client))    # Debe ser False
print(tenant_admin_site.is_registered(Domain))    # Debe ser False
```

---

## 📚 Referencias

- `apps/tenant/core/admin.py` - Implementación del TenantAdminSite
- `apps/tenant/core/apps.py` - AppConfig con registro diferido
- `config/urls_tenant.py` - Configuración de URLs usando tenant_admin_site
- `config/settings.py` - Definición de TENANT_APPS

---

## ⚠️ Notas Importantes

1. **Orden de Carga:**
   - El registro se hace en `AppConfig.ready()` para garantizar que todos los admin.py se hayan cargado
   - Si agregas nuevos modelos de tenant, se registrarán automáticamente

2. **Configuración de ModelAdmin:**
   - La configuración (list_display, fieldsets, etc.) se copia del admin global
   - Si necesitas personalizar el admin de tenant, puedes registrar el modelo directamente en `tenant_admin_site`

3. **Admin Global vs Tenant Admin:**
   - `admin.site` → Admin del esquema público (sintel.net.co/admin/)
   - `tenant_admin_site` → Admin de tenants privados (cliente.sintel.net.co/admin/)

---

## ✅ Estado Final

**Implementación:** ✅ **COMPLETA**

- ✅ TenantAdminSite creado y configurado
- ✅ Filtrado automático de modelos implementado
- ✅ Registro diferido en AppConfig.ready()
- ✅ URLs actualizadas para usar tenant_admin_site
- ✅ Aislamiento total garantizado

El admin de tenants privados está completamente aislado y solo muestra modelos de `TENANT_APPS`.
