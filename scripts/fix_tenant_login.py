"""
Script rápido para diagnosticar y corregir problemas de login en tenant.

Este script:
1. Verifica el tenant especificado
2. Verifica el usuario especificado
3. Crea TenantMembership si no existe
4. Permite cambiar la contraseña si es necesario

Uso:
    python manage.py shell < scripts/fix_tenant_login.py
    O modificar las variables SCHEMA_NAME y USER_EMAIL antes de ejecutar
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()

# Configuración (CAMBIAR SEGÚN NECESIDAD)
SCHEMA_NAME = 'ejemplo'  # Cambiar por el schema_name del tenant
USER_EMAIL = 'admin@ejemplo.com'  # Cambiar por el email del usuario
DEFAULT_PASSWORD = 'admin123'  # Cambiar por una contraseña segura

print("\n" + "=" * 60)
print(f"🔧 FIX: Problema de Login en Tenant '{SCHEMA_NAME}'")
print("=" * 60)

# 1. Verificar tenant
print("\n📋 PASO 1: Verificando tenant...")
try:
    tenant = Client.objects.get(schema_name=SCHEMA_NAME)
    print(f"✅ Tenant encontrado: {tenant.nombre}")
    
    if not tenant.is_active:
        print("⚠️  Tenant está inactivo. Activando...")
        tenant.is_active = True
        tenant.save()
        print("✅ Tenant activado")
except Client.DoesNotExist:
    print(f"❌ ERROR: El tenant '{SCHEMA_NAME}' NO existe")
    exit(1)

# 2. Verificar dominio
print("\n📋 PASO 2: Verificando dominio...")
domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
if domain:
    print(f"✅ Dominio: {domain.domain}")
else:
    print("❌ ERROR: No se encontró dominio principal")
    exit(1)

# 3. Verificar/Crear usuario
print(f"\n📋 PASO 3: Verificando usuario '{USER_EMAIL}'...")
try:
    usuario = User.objects.get(email=USER_EMAIL)
    print(f"✅ Usuario encontrado: {usuario.username}")
except User.DoesNotExist:
    print(f"⚠️  Usuario NO existe. Creando...")
    usuario = User.objects.create_user(
        username=USER_EMAIL.split('@')[0],
        email=USER_EMAIL,
        password=DEFAULT_PASSWORD,
        is_staff=True,
        is_active=True
    )
    print(f"✅ Usuario creado: {usuario.email}")

# Asegurar que el usuario esté activo y sea staff
if not usuario.is_active:
    print("⚠️  Usuario inactivo. Activando...")
    usuario.is_active = True
    usuario.save()
    print("✅ Usuario activado")

if not usuario.is_staff:
    print("⚠️  Usuario no es staff. Configurando...")
    usuario.is_staff = True
    usuario.save()
    print("✅ Usuario configurado como staff")

# 4. Verificar/Crear TenantMembership
print(f"\n📋 PASO 4: Verificando TenantMembership...")
try:
    membership = TenantMembership.objects.get(
        client=tenant,
        user=usuario
    )
    print(f"✅ Membresía existe: Rol={membership.rol}, Admin={membership.is_primary_admin}")
except TenantMembership.DoesNotExist:
    print("⚠️  Membresía NO existe. Creando...")
    membership = TenantMembership.objects.create(
        client=tenant,
        user=usuario,
        rol='ADMIN',
        is_primary_admin=True
    )
    print(f"✅ Membresía creada: Rol={membership.rol}, Admin={membership.is_primary_admin}")

# 5. Opcional: Cambiar contraseña
print(f"\n📋 PASO 5: Configurando contraseña...")
print(f"   ¿Deseas cambiar la contraseña? (Por defecto: '{DEFAULT_PASSWORD}')")
print(f"   Para cambiar manualmente:")
print(f"   >>> usuario.set_password('tu_contraseña')")
print(f"   >>> usuario.save()")

# Establecer contraseña por defecto si no tiene
if not usuario.has_usable_password():
    print("⚠️  Usuario no tiene contraseña. Configurando...")
    usuario.set_password(DEFAULT_PASSWORD)
    usuario.save()
    print(f"✅ Contraseña configurada: '{DEFAULT_PASSWORD}'")
else:
    print(f"✅ Usuario ya tiene contraseña configurada")

# 6. Resumen
print("\n" + "=" * 60)
print("📊 RESUMEN")
print("=" * 60)
print(f"✅ Tenant: {tenant.nombre} (activo: {tenant.is_active})")
print(f"✅ Dominio: {domain.domain}")
print(f"✅ Usuario: {usuario.email} (activo: {usuario.is_active}, staff: {usuario.is_staff})")
print(f"✅ Membresía: Rol={membership.rol}, Admin={membership.is_primary_admin}")
print(f"✅ Contraseña: Configurada")

print(f"\n🌐 URL de acceso:")
print(f"   http://{domain.domain}:8000/login/")
print(f"   o")
print(f"   http://{domain.domain}:8000/admin/login/")

print(f"\n👤 Credenciales:")
print(f"   Email/Username: {USER_EMAIL}")
print(f"   Password: {DEFAULT_PASSWORD if not usuario.has_usable_password() else '(ya configurada)'}")

print(f"\n💡 Si aún no puedes hacer login:")
print(f"   1. Verifica que estés usando el email correcto: {USER_EMAIL}")
print(f"   2. Si cambiaste la contraseña, usa la nueva contraseña")
print(f"   3. Verifica que el tenant esté activo")
print(f"   4. Limpia las cookies del navegador")

print("\n" + "=" * 60)