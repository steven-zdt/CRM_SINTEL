# ✅ Checklist de Hard Reset - SINTEL v2.40

## 📋 Pre-Reset: Verificaciones Críticas

### 1. ✅ Verificar SHARED_APPS y TENANT_APPS

**Comando:**
```bash
docker-compose exec web python manage.py shell -c "from django.conf import settings; print('SHARED_APPS:', len(settings.SHARED_APPS), 'apps'); print('TENANT_APPS:', len(settings.TENANT_APPS), 'apps')"
```

**Resultado esperado:**
- SHARED_APPS: ~12 apps (django-tenants, apps.public.*, DRF, Django contrib)
- TENANT_APPS: ~15 apps (apps.tenant.*, DRF, django_filters, drf_spectacular)

### 2. ✅ Verificar que no haya dependencias circulares

**Comando:**
```bash
docker-compose exec web python manage.py check
```

**Resultado esperado:** Sin errores

### 3. ✅ Verificar que Cotizacion y Empresa se importan correctamente

**Comando:**
```bash
docker-compose exec web python manage.py shell -c "from apps.tenant.cotizaciones.models import Cotizacion; from apps.tenant.empresa.models import Empresa; print('✅ Modelos importados correctamente')"
```

**Resultado esperado:** ✅ Modelos importados correctamente

### 4. ✅ Verificar que el Monkey Patch de admin.py no interfiera

**Comando:**
```bash
docker-compose exec web python manage.py shell -c "from apps.tenant.core.admin import tenant_admin_site; print('✅ Admin site cargado correctamente')"
```

**Resultado esperado:** ✅ Admin site cargado correctamente

## 📋 Post-Reset: Verificaciones Post-Migración

### 1. ✅ Verificar que las migraciones se generaron correctamente

**Comando:**
```bash
docker-compose exec web python manage.py showmigrations --plan | grep -E "(tenant_cotizaciones|tenant_empresa|tenants)" | head -20
```

**Resultado esperado:** Todas las migraciones marcadas como `[X]` (aplicadas)

### 2. ✅ Verificar que el esquema público tiene las tablas correctas

**Comando:**
```bash
docker-compose exec db psql -U sintel -d sintel -c "\dt tenants_*"
```

**Resultado esperado:**
- `tenants_client`
- `tenants_domain`
- `tenants_tenantmembership`

### 3. ✅ Verificar que no hay esquemas de tenants huérfanos

**Comando:**
```bash
docker-compose exec db psql -U sintel -d sintel -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast') AND schema_name NOT LIKE 'pg_%';"
```

**Resultado esperado:** Solo el esquema `public` (o vacío si no hay tenants)

### 4. ✅ Verificar que el superusuario se creó correctamente

**Comando:**
```bash
docker-compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('Usuarios:', User.objects.count())"
```

**Resultado esperado:** Al menos 1 usuario (el superusuario creado)

### 5. ✅ Verificar que el tenant público se configuró correctamente

**Comando:**
```bash
docker-compose exec web python manage.py shell -c "from apps.public.tenants.models import Client, Domain; print('Clients:', Client.objects.count()); print('Domains:', Domain.objects.count())"
```

**Resultado esperado:**
- Clients: 1 (el tenant público)
- Domains: 1 o más (dominios del tenant público)

## 📋 Verificaciones de Integridad v2.40

### 1. ✅ Verificar que apps.tenant.core.admin.py tiene el Monkey Patch

**Archivo:** `apps/tenant/core/admin.py`

**Verificar que existe:**
```python
# ⚠️ v3.3: Monkey patch para el AdminSite global
if not hasattr(admin.site, '_safe_index_applied'):
    admin.site.index = _safe_index.__get__(admin.site, admin.AdminSite)
    admin.site._safe_index_applied = True
```

### 2. ✅ Verificar que apps.tenant.cotizaciones.admin.py tiene validaciones proactivas

**Archivo:** `apps/tenant/cotizaciones/admin.py`

**Verificar que cada ModelAdmin tiene:**
```python
def has_module_permission(self, request):
    if connection.schema_name == 'public':
        return False
    return super().has_module_permission(request)

def get_queryset(self, request):
    if connection.schema_name == 'public':
        return self.model.objects.none()
    return super().get_queryset(request)
```

### 3. ✅ Verificar que no hay fixtures requeridas

**Resultado:** ✅ **NO hay fixtures requeridas**

**Razón:**
- Los porcentajes de IVA se configuran en `ConfiguracionCotizacion` por empresa
- Las monedas se definen en el modelo `ConfiguracionCotizacion.formato_moneda`
- No hay catálogos de impuestos predefinidos
- El sistema funciona sin datos iniciales

## 🚨 Problemas Conocidos y Soluciones

### Problema 1: Error "relation already exists" al recrear tenant

**Solución:** ✅ **RESUELTO** - La migración `0005_create_configuracion_table.py` ahora es idempotente usando `SeparateDatabaseAndState` con `RunSQL` condicional.

### Problema 2: Dependencias circulares entre Cotizacion y Empresa

**Solución:** ✅ **NO HAY PROBLEMA** - Ambos modelos están en TENANT_APPS y en el mismo esquema de tenant. La ForeignKey de `Cotizacion` a `Empresa` es correcta y no causa conflictos.

### Problema 3: Monkey Patch interfiere con migraciones

**Solución:** ✅ **NO INTERFIERE** - El patch `_safe_index` solo se aplica al `admin.site` global y se ejecuta después de que Django carga los modelos. No interfiere con la creación de tablas durante las migraciones.

## 📋 Orden de Ejecución Recomendado

1. ✅ Ejecutar pre-verificaciones
2. ✅ Ejecutar script de hard reset
3. ✅ Crear superusuario
4. ✅ Configurar tenant público
5. ✅ Ejecutar post-verificaciones
6. ✅ Probar onboarding de un tenant

## 🎯 Resultado Final Esperado

Después del hard reset, el sistema debe estar:
- ✅ Con todas las migraciones regeneradas y aplicadas
- ✅ Con el esquema público limpio y funcional
- ✅ Con un superusuario creado
- ✅ Con el tenant público configurado
- ✅ Listo para crear nuevos tenants mediante onboarding
- ✅ Sin errores de dependencias circulares
- ✅ Con el Monkey Patch de admin funcionando correctamente
