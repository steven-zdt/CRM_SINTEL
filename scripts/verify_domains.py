"""
Script de verificación (Smoke Test) para la Política Estricta de Subdominios.

Este script verifica:
1. El dominio actual del tenant público (debe ser TENANT_DOMAIN_BASE)
2. Simula la creación de un tenant 'test_auto' y verifica que su dominio sea 'test_auto.{TENANT_DOMAIN_BASE}'

Uso:
    python manage.py shell < scripts/verify_domains.py
    o
    python scripts/verify_domains.py
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


def verificar_tenant_publico():
    """Verifica que el tenant público tenga el dominio correcto."""
    print("\n" + "=" * 60)
    print("🔍 VERIFICACIÓN 1: Dominio del Tenant Público")
    print("=" * 60)
    
    try:
        tenant = Client.objects.get(schema_name='public')
        print(f"✅ Tenant público encontrado: {tenant.nombre}")
        
        dominio_esperado = settings.TENANT_DOMAIN_BASE
        print(f"   TENANT_DOMAIN_BASE: {dominio_esperado}")
        
        dominio_principal = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        
        if dominio_principal:
            print(f"   Dominio principal actual: {dominio_principal.domain}")
            
            if dominio_principal.domain == dominio_esperado:
                print(f"✅ CORRECTO: El dominio principal coincide con TENANT_DOMAIN_BASE")
                return True
            else:
                print(f"❌ ERROR: El dominio principal ({dominio_principal.domain}) NO coincide con TENANT_DOMAIN_BASE ({dominio_esperado})")
                print(f"   Ejecuta: python manage.py ensure_public_domain")
                return False
        else:
            print(f"❌ ERROR: No se encontró dominio principal para el tenant público")
            print(f"   Ejecuta: python manage.py ensure_public_domain")
            return False
            
    except Client.DoesNotExist:
        print(f"❌ ERROR: El tenant público no existe")
        print(f"   Ejecuta: python manage.py setup_public_tenant")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def simular_creacion_tenant():
    """Simula la creación de un tenant y verifica que su dominio sea un subdominio."""
    print("\n" + "=" * 60)
    print("🔍 VERIFICACIÓN 2: Creación Automática de Subdominios")
    print("=" * 60)
    
    try:
        # Crear o obtener un usuario de prueba
        test_user, _ = User.objects.get_or_create(
            username='test_auto_user',
            defaults={
                'email': 'test_auto@sintel.com',
                'is_staff': True,
            }
        )
        test_user.set_password('test_password')
        test_user.save()
        
        schema_name = 'test_auto'
        nombre = 'Empresa Test Auto'
        dominio_esperado = f"{schema_name}.{settings.TENANT_DOMAIN_BASE}"
        
        print(f"   Schema name: {schema_name}")
        print(f"   Dominio esperado: {dominio_esperado}")
        
        # Verificar si el tenant ya existe
        if Client.objects.filter(schema_name=schema_name).exists():
            print(f"⚠️  El tenant '{schema_name}' ya existe. Eliminándolo para la prueba...")
            client_existente = Client.objects.get(schema_name=schema_name)
            # Eliminar dominio asociado
            Domain.objects.filter(tenant=client_existente).delete()
            # Eliminar tenant (esto eliminará el esquema)
            client_existente.delete()
            print(f"✅ Tenant anterior eliminado")
        
        # Crear tenant usando el servicio
        print(f"\n   Creando tenant '{nombre}'...")
        client, domain, login_url = crear_tenant(
            nombre=nombre,
            admin_user_id=test_user.id,
            schema_name=schema_name
        )
        
        print(f"✅ Tenant creado: {client.nombre} (schema: {client.schema_name})")
        print(f"   Dominio creado: {domain.domain}")
        print(f"   Login URL: {login_url}")
        
        # Verificar que el dominio sea el esperado
        if domain.domain == dominio_esperado:
            print(f"✅ CORRECTO: El dominio creado ({domain.domain}) coincide con el esperado ({dominio_esperado})")
            
            # Limpiar: eliminar el tenant de prueba
            print(f"\n   Limpiando tenant de prueba...")
            Domain.objects.filter(tenant=client).delete()
            client.delete()
            print(f"✅ Tenant de prueba eliminado")
            
            return True
        else:
            print(f"❌ ERROR: El dominio creado ({domain.domain}) NO coincide con el esperado ({dominio_esperado})")
            
            # Limpiar: eliminar el tenant de prueba
            Domain.objects.filter(tenant=client).delete()
            client.delete()
            
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "=" * 60)
    print("🚀 VERIFICACIÓN DE POLÍTICA ESTRICTA DE SUBDOMINIOS")
    print("=" * 60)
    print(f"\n📋 Configuración:")
    print(f"   TENANT_DOMAIN_BASE: {settings.TENANT_DOMAIN_BASE}")
    print(f"   DEBUG: {settings.DEBUG}")
    
    # Verificación 1: Tenant público
    resultado_1 = verificar_tenant_publico()
    
    # Verificación 2: Creación automática de subdominios
    resultado_2 = simular_creacion_tenant()
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VERIFICACIONES")
    print("=" * 60)
    print(f"   Verificación 1 (Tenant Público): {'✅ PASÓ' if resultado_1 else '❌ FALLÓ'}")
    print(f"   Verificación 2 (Subdominios Auto): {'✅ PASÓ' if resultado_2 else '❌ FALLÓ'}")
    
    if resultado_1 and resultado_2:
        print("\n🎉 TODAS LAS VERIFICACIONES PASARON")
        print("   La Política Estricta de Subdominios está correctamente implementada.")
    else:
        print("\n⚠️  ALGUNAS VERIFICACIONES FALLARON")
        print("   Revisa los errores anteriores y corrige la configuración.")
    
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()