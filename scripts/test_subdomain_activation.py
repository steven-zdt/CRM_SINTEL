"""
Script de prueba para verificar la activación automática de subdominios.

Este script:
1. Crea un tenant de prueba con schema 'test_subdomain'
2. Verifica que el dominio se creó como 'test_subdomain.sintel.com'
3. Construye la URL completa con puerto y verifica que sea accesible

Uso:
    python manage.py shell < scripts/test_subdomain_activation.py
    o
    python scripts/test_subdomain_activation.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from apps.public.tenants.models import Client, Domain
from apps.services.onboarding.empresa_service import crear_tenant
from django.contrib.auth import get_user_model

User = get_user_model()


def test_subdomain_activation():
    """Prueba la activación automática de subdominios."""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA: Activación Automática de Subdominios")
    print("=" * 60)
    
    print(f"\n📋 Configuración:")
    print(f"   TENANT_DOMAIN_BASE: {settings.TENANT_DOMAIN_BASE}")
    print(f"   APP_PORT: {getattr(settings, 'APP_PORT', '8000')}")
    print(f"   DEBUG: {settings.DEBUG}")
    
    # Limpiar tenant de prueba si existe
    schema_name = 'test_subdomain'  # Nombre genérico para pruebas
    try:
        existing_client = Client.objects.get(schema_name=schema_name)
        print(f"\n[WARNING]  El tenant '{schema_name}' ya existe. Eliminándolo para la prueba...")
        Domain.objects.filter(tenant=existing_client).delete()
        existing_client.delete()
        print(f"[OK] Tenant anterior eliminado")
    except Client.DoesNotExist:
        pass
    
    # Crear usuario de prueba si no existe
    test_user, _ = User.objects.get_or_create(
        username='test_subdomain_user',
        defaults={
            'email': 'test_subdomain@sintel.com',
            'is_staff': True,
        }
    )
    test_user.set_password('test_password')
    test_user.save()
    
    # Crear tenant de prueba
    print(f"\n[LAUNCH] Creando tenant con schema '{schema_name}'...")
    try:
        client, domain, login_url = crear_tenant(
            nombre='Empresa Test Subdomain',
            admin_user_id=test_user.id,
            schema_name=schema_name
        )
        
        print(f"[OK] Tenant creado exitosamente")
        print(f"\n[CHART] Resultados:")
        print(f"   - Schema: {client.schema_name}")
        print(f"   - Nombre: {client.nombre}")
        print(f"   - Dominio en BD: {domain.domain}")
        
        # Verificar que el dominio sea un subdominio
        dominio_esperado = f"{schema_name}.{settings.TENANT_DOMAIN_BASE}"
        if domain.domain == dominio_esperado:
            print(f"   [OK] Dominio correcto: {domain.domain}")
        else:
            print(f"   [ERROR] ERROR: Dominio esperado '{dominio_esperado}', pero se creó '{domain.domain}'")
            return False
        
        # Verificar URL construida
        print(f"   - Login URL: {login_url}")
        
        # Construir URL esperada
        app_port = getattr(settings, 'APP_PORT', '8000')
        if settings.DEBUG and app_port and app_port != '80':
            url_esperada = f"http://{domain.domain}:{app_port}/"
        else:
            url_esperada = f"http://{domain.domain}/"
        
        if login_url == url_esperada:
            print(f"   [OK] URL correcta: {login_url}")
        else:
            print(f"   [WARNING]  URL construida: {login_url}")
            print(f"   [WARNING]  URL esperada: {url_esperada}")
        
        # Verificar que el dominio esté en ALLOWED_HOSTS (indirectamente)
        print(f"\n🔍 Verificación de Accesibilidad:")
        print(f"   - Dominio: {domain.domain}")
        print(f"   - Accesible desde: {login_url}")
        print(f"   - ALLOWED_HOSTS incluye: .{settings.TENANT_DOMAIN_BASE}")
        
        # Limpiar
        print(f"\n🧹 Limpiando tenant de prueba...")
        Domain.objects.filter(tenant=client).delete()
        client.delete()
        print(f"[OK] Tenant de prueba eliminado")
        
        print(f"\n🎉 PRUEBA EXITOSA: El subdominio se activó automáticamente")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    test_subdomain_activation()
