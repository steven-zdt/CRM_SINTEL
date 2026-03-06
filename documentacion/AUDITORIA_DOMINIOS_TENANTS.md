# 🔍 Auditoría de Dominios y Acceso Web de Tenants

## 📋 Objetivo

Garantizar que cada tenant creado tiene:
1. ✅ Dominio activo y configurado correctamente
2. ✅ Dominio principal marcado (`is_primary=True`)
3. ✅ Tenant activo (`is_active=True`)
4. ✅ Esquema PostgreSQL existente
5. ✅ Acceso web funcionando

## 🛠️ Herramientas Disponibles

### 1. Comando de Management: `auditar_dominios_tenants`

Comando completo para auditar todos los tenants o uno específico.

#### Uso Básico

```bash
# Auditar TODOS los tenants
docker compose exec web python manage.py auditar_dominios_tenants

# Auditar un tenant específico
docker compose exec web python manage.py auditar_dominios_tenants --schema home

# Auditar con prueba de acceso web (simula petición HTTP)
docker compose exec web python manage.py auditar_dominios_tenants --test-web

# Auditar y corregir problemas automáticamente
docker compose exec web python manage.py auditar_dominios_tenants --fix
```

#### Opciones Disponibles

- `--schema SCHEMA_NAME`: Auditar solo un tenant específico
- `--fix`: Intentar corregir problemas automáticamente
- `--test-web`: Probar acceso web real (simula petición HTTP)

#### Ejemplo de Salida

```
================================================================================
🔍 AUDITORÍA DE DOMINIOS Y ACCESO WEB DE TENANTS
================================================================================

--------------------------------------------------------------------------------
📋 Tenant: Home S.A. (schema: home)
--------------------------------------------------------------------------------
✅ Tenant activo
✅ Esquema PostgreSQL 'home' existe
✅ Tiene 1 dominio(s)
✅ Dominio principal: home.sintel.com
✅ Formato de dominio correcto: home.sintel.com
✅ Acceso web funciona: HTTP 200

✅ TENANT OK

================================================================================
📊 RESUMEN DE AUDITORÍA
================================================================================
Total de tenants auditados: 5
✅ Tenants OK: 4
❌ Tenants con problemas: 1
```

### 2. Tests Automatizados: `test_domain_activation.py`

Suite de tests que valida automáticamente la creación de tenants con dominio activo.

#### Ejecutar Tests

```bash
# Ejecutar todos los tests de dominio
docker compose exec web python manage.py test tests.public.tenants.test_domain_activation

# Ejecutar un test específico
docker compose exec web python manage.py test tests.public.tenants.test_domain_activation.TenantDomainActivationTests.test_crear_tenant_crea_dominio_automaticamente
```

#### Tests Incluidos

1. **`test_crear_tenant_crea_dominio_automaticamente`**
   - Verifica que al crear un tenant, se crea automáticamente el dominio

2. **`test_crear_tenant_dominio_principal_marcado`**
   - Verifica que el dominio creado está marcado como principal

3. **`test_crear_tenant_esta_activo_por_defecto`**
   - Verifica que el tenant creado está activo por defecto

4. **`test_crear_tenant_esquema_postgresql_existe`**
   - Verifica que el esquema PostgreSQL fue creado

5. **`test_crear_tenant_acceso_web_funciona`**
   - Verifica que el acceso web al tenant funciona correctamente

6. **`test_crear_tenant_url_login_correcta`**
   - Verifica que la URL de login generada es correcta

7. **`test_crear_tenant_membresia_admin_creada`**
   - Verifica que se crea la membresía del administrador

8. **`test_crear_tenant_dominio_no_duplicado`**
   - Verifica que no se crean dominios duplicados

9. **`test_crear_tenant_dominio_formato_subdominio`**
   - Verifica que el dominio siempre sigue el formato de subdominio

### 3. Script de Verificación Rápida: `verificar_tenant_web.py`

Script Python para verificar rápidamente un tenant específico.

#### Uso

```bash
# Editar el script y cambiar SCHEMA_NAME
# Luego ejecutar en el shell de Django:
docker compose exec web python manage.py shell < scripts/verificar_tenant_web.py
```

O directamente en el shell:

```python
from django.test import Client
from apps.public.tenants.models import Client, Domain

# Verificar tenant 'home'
tenant = Client.objects.get(schema_name='home')
domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()

print(f"Tenant: {tenant.nombre}")
print(f"Dominio: {domain.domain}")
print(f"Activo: {tenant.is_active}")

# Probar acceso web
test_client = Client(HTTP_HOST=domain.domain)
response = test_client.get('/')
print(f"HTTP Status: {response.status_code}")
```

## 🔧 Validaciones Implementadas

### En el Servicio `crear_tenant`

El servicio ahora incluye validaciones finales después de crear el tenant:

1. ✅ Verifica que el tenant está activo (`is_active=True`)
2. ✅ Verifica que el esquema PostgreSQL existe
3. ✅ Verifica que existe exactamente un dominio principal
4. ✅ Verifica que el dominio tiene el formato correcto

Si alguna validación falla, se lanza un `ValidationError` y la transacción se revierte.

### En la Señal `post_save`

La señal `create_client_domain` en `apps/public/tenants/signals.py`:

1. ✅ Crea automáticamente el dominio como subdominio: `{schema_name}.{TENANT_DOMAIN_BASE}`
2. ✅ Marca el dominio como principal (`is_primary=True`)
3. ✅ Valida que el `schema_name` no contenga puntos (no se permiten FQDN)

## 📊 Checklist de Verificación

Para cada tenant creado, verificar:

- [ ] Tenant existe en la base de datos
- [ ] Tenant está activo (`is_active=True`)
- [ ] Esquema PostgreSQL existe
- [ ] Dominio principal existe (`is_primary=True`)
- [ ] Formato de dominio correcto: `{schema_name}.{TENANT_DOMAIN_BASE}`
- [ ] Acceso web funciona (HTTP 200, 302, o 301)
- [ ] Administrador principal asignado (`TenantMembership` con `is_primary_admin=True`)

## 🚨 Problemas Comunes y Soluciones

### Problema: Tenant sin dominio

**Síntoma:**
```
❌ NO tiene dominios asociados
```

**Solución:**
```bash
# Ejecutar auditoría con --fix
docker compose exec web python manage.py auditar_dominios_tenants --fix

# O crear manualmente el dominio
python manage.py shell
>>> from apps.public.tenants.models import Client, Domain
>>> tenant = Client.objects.get(schema_name='home')
>>> Domain.objects.create(
...     domain=f"{tenant.schema_name}.sintel.com",
...     tenant=tenant,
...     is_primary=True
... )
```

### Problema: Dominio sin marcar como principal

**Síntoma:**
```
❌ NO tiene dominio principal (is_primary=True)
```

**Solución:**
```bash
# Ejecutar auditoría con --fix
docker compose exec web python manage.py auditar_dominios_tenants --fix --schema home
```

### Problema: Acceso web retorna 404

**Síntoma:**
```
❌ Acceso web falla: HTTP 404 (tenant no encontrado)
```

**Solución:**
1. Verificar que el dominio está en la tabla `tenants_domain`
2. Verificar que `django-tenants` puede resolver el dominio:
   ```bash
   docker compose exec web python manage.py diagnostico_routing --schema home --hostname home.sintel.com:8000
   ```
3. Si el problema es el puerto, agregar el dominio con puerto:
   ```bash
   docker compose exec web python manage.py fix_tenant_domain --schema home --port 8000
   ```

### Problema: Tenant inactivo

**Síntoma:**
```
❌ Tenant INACTIVO (is_active=False)
```

**Solución:**
```bash
# Ejecutar auditoría con --fix
docker compose exec web python manage.py auditar_dominios_tenants --fix --schema home

# O activar manualmente
python manage.py shell
>>> from apps.public.tenants.models import Client
>>> tenant = Client.objects.get(schema_name='home')
>>> tenant.is_active = True
>>> tenant.save()
```

## 🔄 Flujo de Creación de Tenant

1. **Servicio `crear_tenant`** crea el `Client`
2. **Señal `post_save`** crea automáticamente el `Domain` como subdominio
3. **Servicio** verifica que el dominio fue creado correctamente
4. **Servicio** ejecuta migraciones del tenant
5. **Servicio** crea `TenantMembership` para el administrador
6. **Servicio** valida que todo está correcto (validaciones finales)
7. **Servicio** retorna `(client, domain, login_url)`

## 📝 Notas Importantes

- ⚠️ **El tenant público (`public`) no puede ser desactivado ni eliminado**
- ⚠️ **Todos los dominios deben seguir el formato de subdominio**: `{schema_name}.{TENANT_DOMAIN_BASE}`
- ⚠️ **No se permiten FQDN** (dominios con punto en `schema_name`)
- ✅ **El dominio se crea automáticamente** por la señal `post_save`
- ✅ **El tenant está activo por defecto** (`is_active=True`)
- ✅ **El dominio principal se marca automáticamente** (`is_primary=True`)

## 🎯 Mejores Prácticas

1. **Ejecutar auditoría después de crear tenants:**
   ```bash
   docker compose exec web python manage.py auditar_dominios_tenants --test-web
   ```

2. **Ejecutar tests antes de desplegar:**
   ```bash
   docker compose exec web python manage.py test tests.public.tenants.test_domain_activation
   ```

3. **Verificar acceso web manualmente:**
   - Abrir navegador en `http://{schema_name}.sintel.com:8000/`
   - Debe mostrar la landing page del tenant (no 404)

4. **Monitorear logs de creación:**
   - Revisar logs de Django para errores en la señal `post_save`
   - Verificar que no hay errores de validación
