# 🔍 Diagnóstico: Error de Login en Tenant Privado

## ❌ Error Reportado

```
Por favor ingrese el nombre de usuario y la clave correctos para obtener cuenta de personal. 
Observe que ambos campos pueden ser sensibles a mayúsculas.
```

**URL:** `http://home.sintel.net.co:8000/admin/login/`  
**Usuario esperado:** `admin@home.com`

## 🔧 Pasos de Diagnóstico

### 1. Verificar Tenant y Dominio

```bash
python manage.py shell
```

```python
from apps.public.tenants.models import Client, Domain

# Verificar tenant 'home'
tenant = Client.objects.get(schema_name='home')
print(f"Tenant: {tenant.nombre}")
print(f"Activo: {tenant.is_active}")

# Verificar dominio
domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
print(f"Dominio: {domain.domain}")
```

### 2. Verificar Usuario

```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Buscar usuario por email
try:
    usuario = User.objects.get(email='admin@home.com')
    print(f"Usuario encontrado: {usuario.username}")
    print(f"Email: {usuario.email}")
    print(f"Activo: {usuario.is_active}")
    print(f"Staff: {usuario.is_staff}")
    print(f"Tiene contraseña: {usuario.has_usable_password()}")
except User.DoesNotExist:
    print("❌ Usuario NO encontrado")
    
    # Buscar usuarios similares
    usuarios = User.objects.filter(email__icontains='admin')
    for u in usuarios:
        print(f"  - {u.email} (username: {u.username})")
```

### 3. Verificar TenantMembership

```python
from apps.public.tenants.models import TenantMembership

# Verificar membresía
try:
    membership = TenantMembership.objects.get(
        client=tenant,
        user=usuario
    )
    print(f"✅ Membresía encontrada:")
    print(f"  - Rol: {membership.rol}")
    print(f"  - Admin principal: {membership.is_primary_admin}")
except TenantMembership.DoesNotExist:
    print("❌ NO existe TenantMembership")
    print("💡 Crear membresía:")
    print("   TenantMembership.objects.create(")
    print("       client=tenant,")
    print("       user=usuario,")
    print("       rol='ADMIN',")
    print("       is_primary_admin=True")
    print("   )")
```

### 4. Verificar Contraseña

```python
# Verificar si la contraseña es correcta (sin revelarla)
# Si no sabes la contraseña, puedes cambiarla:

usuario.set_password('nueva_contraseña_segura')
usuario.save()
print("✅ Contraseña actualizada")
```

### 5. Verificar Autenticación Backend

```python
from django.conf import settings
from django.contrib.auth import authenticate
from django.test import RequestFactory

# Simular autenticación
factory = RequestFactory()
request = factory.get('/')
request.tenant = tenant

# Intentar autenticar
user = authenticate(
    request=request,
    username='admin@home.com',
    password='tu_contraseña'
)

if user:
    print(f"✅ Autenticación exitosa: {user.email}")
else:
    print("❌ Autenticación falló")
    print("   Posibles causas:")
    print("   1. Contraseña incorrecta")
    print("   2. Usuario no tiene TenantMembership")
    print("   3. Tenant no está activo")
```

## 🛠️ Soluciones Comunes

### Solución 1: Crear TenantMembership

Si el usuario existe pero no tiene membresía:

```python
from apps.public.tenants.models import Client, TenantMembership
from django.contrib.auth import get_user_model

User = get_user_model()
tenant = Client.objects.get(schema_name='home')
usuario = User.objects.get(email='admin@home.com')

TenantMembership.objects.create(
    client=tenant,
    user=usuario,
    rol='ADMIN',
    is_primary_admin=True
)
```

### Solución 2: Cambiar Contraseña

Si la contraseña es incorrecta:

```python
from django.contrib.auth import get_user_model

User = get_user_model()
usuario = User.objects.get(email='admin@home.com')
usuario.set_password('nueva_contraseña_segura')
usuario.save()
```

### Solución 3: Activar Usuario

Si el usuario está inactivo:

```python
usuario.is_active = True
usuario.is_staff = True  # Necesario para acceder al admin
usuario.save()
```

### Solución 4: Activar Tenant

Si el tenant está inactivo:

```python
tenant.is_active = True
tenant.save()
```

## ⚠️ Warning de Cross-Origin-Opener-Policy

El warning sobre `Cross-Origin-Opener-Policy` es un aviso del navegador, no un error crítico. Ocurre porque:

1. Estás usando HTTP en lugar de HTTPS
2. El dominio no es considerado "trustworthy" por el navegador

**Solución temporal (desarrollo):**
- Ignorar el warning (no afecta la funcionalidad)
- Usar `localhost` en lugar de `sintel.net.co` para desarrollo local

**Solución en producción:**
- Configurar HTTPS
- Agregar el header `Cross-Origin-Opener-Policy` solo en HTTPS

## 🔍 Comando de Auditoría Automática

Usa el comando de management creado:

```bash
python manage.py auditar_tenant home --email admin@home.com
```

Este comando verifica automáticamente:
- ✅ Existencia del tenant
- ✅ Dominio asociado
- ✅ Usuario y sus propiedades
- ✅ TenantMembership
- ✅ Acceso al esquema

## 📋 Checklist de Verificación

- [ ] Tenant 'home' existe y está activo
- [ ] Dominio 'home.sintel.net.co' está asociado al tenant
- [ ] Usuario 'admin@home.com' existe
- [ ] Usuario está activo (`is_active=True`)
- [ ] Usuario tiene contraseña configurada
- [ ] Existe TenantMembership entre usuario y tenant
- [ ] TenantMembership tiene rol 'ADMIN'
- [ ] Contraseña es correcta
- [ ] Tenant está activo (`is_active=True`)

## 🚨 Problemas Comunes

### 1. Usuario no tiene TenantMembership

**Síntoma:** Error "Por favor ingrese el nombre de usuario y la clave correctos"

**Causa:** El usuario existe pero no está asociado al tenant

**Solución:** Crear TenantMembership (ver Solución 1)

### 2. Contraseña Incorrecta

**Síntoma:** Error "Por favor ingrese el nombre de usuario y la clave correctos"

**Causa:** La contraseña ingresada no coincide

**Solución:** Cambiar contraseña (ver Solución 2)

### 3. Usuario Inactivo

**Síntoma:** Error de autenticación

**Causa:** `usuario.is_active = False`

**Solución:** Activar usuario (ver Solución 3)

### 4. Tenant Inactivo

**Síntoma:** Error de autenticación o acceso denegado

**Causa:** `tenant.is_active = False`

**Solución:** Activar tenant (ver Solución 4)

### 5. Usuario no es Staff

**Síntoma:** No puede acceder al admin

**Causa:** `usuario.is_staff = False`

**Solución:** 
```python
usuario.is_staff = True
usuario.save()
```