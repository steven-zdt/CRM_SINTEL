# 🔧 Solución: Problema de Puerto en Dominio de Tenants

## ❌ Problema Identificado

Cuando se crea un tenant privado (ej: `omega-corp`), el sistema guarda el dominio como `omega-corp.sintel.net.co` (sin puerto). Sin embargo, en desarrollo, el navegador accede con puerto: `http://omega-corp.sintel.net.co:8000/`.

**Consecuencia:**
- django-tenants busca coincidencia **exacta** del hostname
- No encuentra `omega-corp.sintel.net.co:8000` en la base de datos
- Asume que es una petición pública y carga el esquema `public`
- El usuario ve la consola pública en lugar de la landing page del tenant

## ✅ Solución Implementada

### 1. Modificación de la Señal `post_save`

**Archivo:** `apps/public/tenants/signals.py`

La señal ahora crea **automáticamente** dos dominios en modo desarrollo:

1. **Dominio principal** (sin puerto): `omega-corp.sintel.net.co` → `is_primary=True`
2. **Dominio con puerto** (solo en DEBUG): `omega-corp.sintel.net.co:8000` → `is_primary=False`

**Código:**
```python
# Crear dominio principal (sin puerto)
Domain.objects.create(
    domain=domain_name,
    tenant=instance,
    is_primary=True
)

# En desarrollo, crear dominio adicional con puerto
if settings.DEBUG:
    app_port = getattr(settings, 'APP_PORT', '8000')
    if app_port and app_port != '80' and app_port != '443':
        domain_with_port = f"{domain_name}:{app_port}"
        Domain.objects.create(
            domain=domain_with_port,
            tenant=instance,
            is_primary=False
        )
```

### 2. Comando para Corregir Tenants Existentes

**Archivo:** `apps/public/tenants/management/commands/fix_all_tenant_domains.py`

Este comando corrige todos los tenants existentes agregando el dominio con puerto.

**Uso:**
```bash
# Corregir todos los tenants existentes
docker compose exec web python manage.py fix_all_tenant_domains

# Especificar puerto manualmente
docker compose exec web python manage.py fix_all_tenant_domains --port 8000

# Forzar actualización incluso si el dominio ya existe
docker compose exec web python manage.py fix_all_tenant_domains --force
```

## 🔍 Flujo Corregido

### Fase 1: Creación del Tenant

**Antes:**
- Se creaba solo: `omega-corp.sintel.net.co`

**Ahora:**
- Se crea: `omega-corp.sintel.net.co` (principal)
- Se crea: `omega-corp.sintel.net.co:8000` (desarrollo)

### Fase 2: Intercepción de la Petición

**Antes:**
- Navegador: `omega-corp.sintel.net.co:8000`
- Base de datos: `omega-corp.sintel.net.co`
- ❌ No coincide → Carga esquema público

**Ahora:**
- Navegador: `omega-corp.sintel.net.co:8000`
- Base de datos: `omega-corp.sintel.net.co:8000` ✅
- ✅ Coincide → Carga esquema del tenant

### Fase 3: Enrutamiento

**Antes:**
- Carga `config.urls_public` (incorrecto)

**Ahora:**
- Carga `config.urls_tenant` (correcto)
- Muestra `TenantLandingView` (landing page del tenant)

## 🚀 Uso

### Para Nuevos Tenants

Los nuevos tenants se crean automáticamente con ambos dominios en desarrollo. No se requiere acción adicional.

### Para Tenants Existentes

Si tienes tenants creados antes de esta actualización, ejecuta:

```bash
docker compose exec web python manage.py fix_all_tenant_domains
```

Esto agregará el dominio con puerto a todos los tenants existentes.

## 📋 Verificación

### Verificar que el dominio con puerto existe:

```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

tenant = Client.objects.get(schema_name='omega-corp')
domains = Domain.objects.filter(tenant=tenant)

for domain in domains:
    print(f"{domain.domain} (primary: {domain.is_primary})")

# Debe mostrar:
# omega-corp.sintel.net.co (primary: True)
# omega-corp.sintel.net.co:8000 (primary: False)
```

### Probar acceso:

```bash
# Debe mostrar la landing page del tenant (no la consola pública)
curl -I http://omega-corp.sintel.net.co:8000/
```

## ⚠️ Notas Importantes

1. **Solo en Desarrollo:** El dominio con puerto se crea automáticamente solo cuando `DEBUG=True`
2. **Producción:** En producción, los puertos 80 (HTTP) y 443 (HTTPS) son implícitos, no se incluyen en el dominio
3. **Puerto Configurable:** El puerto se obtiene de `settings.APP_PORT` (default: `8000`)
4. **Dominio Principal:** El dominio sin puerto siempre es el principal (`is_primary=True`)

## 🔧 Solución de Problemas

### Error: "Tenant no encontrado" en desarrollo

**Solución:** Ejecuta el comando de corrección:
```bash
docker compose exec web python manage.py fix_all_tenant_domains
```

### Error: "Dominio ya existe pero pertenece a otro tenant"

**Solución:** Verifica que no haya conflictos de dominios:
```bash
docker compose exec web python manage.py shell
```

```python
from apps.public.tenants.models import Domain

# Buscar dominios duplicados
domains = Domain.objects.all().values('domain').annotate(count=Count('id')).filter(count__gt=1)
for domain in domains:
    print(f"Dominio duplicado: {domain['domain']}")
```

### El dominio con puerto no se crea automáticamente

**Verificar:**
1. `DEBUG=True` en `settings.py`
2. `APP_PORT` está configurado (default: `8000`)
3. El puerto no es `80` ni `443` (puertos estándar no necesitan especificarse)

## 📝 Resumen

- ✅ **Problema resuelto:** Los nuevos tenants se crean automáticamente con dominio con puerto en desarrollo
- ✅ **Comando disponible:** `fix_all_tenant_domains` para corregir tenants existentes
- ✅ **Sin impacto en producción:** Solo afecta desarrollo (DEBUG=True)
- ✅ **Backward compatible:** Los tenants existentes pueden corregirse fácilmente
