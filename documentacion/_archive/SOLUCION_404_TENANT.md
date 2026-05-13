# Solución: Error 404 al acceder a tenant con puerto

## ❌ Problema

Al acceder a `http://home.sintel.com:8000/`, se obtiene un error 404 (Page not found) en lugar de mostrar la landing page del tenant.

## 🔍 Diagnóstico

El problema ocurre porque django-tenants no identifica correctamente el tenant cuando se accede con el puerto en el dominio. Aunque django-tenants debería extraer automáticamente el hostname sin puerto del `HTTP_HOST`, en algunos casos no lo hace correctamente.

### Verificación

1. **Tenant existe:** ✅
   ```bash
   docker compose exec web python manage.py diagnostico_routing --schema home
   ```

2. **Dominio configurado:** ✅
   - Dominio principal: `home.sintel.com`
   - Dominio con puerto: `home.sintel.com:8000` (agregado como solución temporal)

## ✅ Solución Implementada

### Opción 1: Agregar dominio con puerto (Solución Temporal)

Para desarrollo, puedes agregar el dominio con puerto explícitamente:

```bash
docker compose exec web python manage.py fix_tenant_domain --schema home --port 8000
```

Esto crea un dominio adicional `home.sintel.com:8000` que django-tenants puede identificar directamente.

**Ventajas:**
- Solución rápida y directa
- Funciona inmediatamente

**Desventajas:**
- No es ideal para producción (no deberías usar puertos en URLs)
- Duplica la configuración de dominios

### Opción 2: Verificar configuración del middleware (Solución Ideal)

django-tenants debería manejar automáticamente los puertos. Si el problema persiste, verifica:

1. **TenantMainMiddleware está activo:**
   ```python
   # config/settings.py
   MIDDLEWARE = [
       'django_tenants.middleware.main.TenantMainMiddleware',  # ✅ Debe ser el PRIMERO
       # ... otros middlewares
   ]
   ```

2. **ALLOWED_HOSTS incluye el dominio:**
   ```python
   # config/settings.py
   ALLOWED_HOSTS = [
       '.sintel.com',  # ✅ Acepta cualquier subdominio
       'sintel.com',
       'localhost',
       '127.0.0.1',
   ]
   ```

3. **TENANT_URLCONF está configurado:**
   ```python
   # config/settings.py
   TENANT_URLCONF = 'config.urls_tenant'  # ✅ URLs para tenants privados
   ```

## 🔧 Comandos Útiles

### Diagnosticar routing

```bash
docker compose exec web python manage.py diagnostico_routing --schema home
```

### Agregar dominio con puerto

```bash
docker compose exec web python manage.py fix_tenant_domain --schema home --port 8000
```

### Verificar dominios de un tenant

```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain
tenant = Client.objects.get(schema_name='home')
domains = Domain.objects.filter(tenant=tenant)
for d in domains:
    print(f"{d.domain} (primary: {d.is_primary})")
```

## 📋 Verificación Final

Después de aplicar la solución, verifica:

1. ✅ Acceder a `http://home.sintel.com:8000/` muestra la landing page
2. ✅ Acceder a `http://home.sintel.com:8000/dashboard/` funciona (si estás autenticado)
3. ✅ Acceder a `http://home.sintel.com:8000/api/v1/empresa/empresas/` funciona

## ⚠️ Notas Importantes

1. **Producción:** En producción, no deberías usar puertos en las URLs. Usa un proxy reverso (nginx, traefik) que maneje los puertos y redirija al contenedor.

2. **Desarrollo:** La solución temporal (agregar dominio con puerto) es aceptable para desarrollo, pero no es ideal para producción.

3. **django-tenants:** La biblioteca debería manejar automáticamente los puertos, pero en algunos casos puede fallar. Si el problema persiste, considera reportar el issue en el repositorio de django-tenants.

## 🚀 Próximos Pasos

1. Verificar que el acceso funcione con el dominio con puerto
2. En producción, configurar un proxy reverso que maneje los puertos
3. Considerar eliminar el dominio con puerto una vez que el proxy esté configurado
