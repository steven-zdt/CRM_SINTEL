"""
🔍 Script de Diagnóstico Forense para Resolución de Tenants

Este script realiza un análisis exhaustivo del sistema de resolución de tenants
para identificar por qué un dominio no está siendo resuelto correctamente.

Uso:
    python scripts/diagnostico_forense_tenant.py <hostname>

Ejemplo:
    python scripts/diagnostico_forense_tenant.py home.localhost
    python scripts/diagnostico_forense_tenant.py home.localhost:8000
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.conf import settings
from django_tenants.utils import get_public_schema_name, get_tenant_model, get_tenant_domain_model
from django_tenants.middleware.main import TenantMainMiddleware
from django.http import HttpRequest
from urllib.parse import urlparse


def extraer_hostname(hostname_completo: str) -> str:
    """
    Extrae el hostname puro (sin puerto) de una cadena.
    
    django-tenants usa solo el hostname sin puerto para resolver el tenant.
    """
    # Si tiene puerto, extraer solo la parte del hostname
    if ':' in hostname_completo:
        return hostname_completo.split(':')[0]
    return hostname_completo


def diagnostico_completo(hostname_input: str):
    """
    Realiza un diagnóstico completo del sistema de resolución de tenants.
    """
    print("=" * 80)
    print("🔍 DIAGNÓSTICO FORENSE DE RESOLUCIÓN DE TENANTS")
    print("=" * 80)
    print()
    
    # 1. Extraer hostname puro
    hostname_puro = extraer_hostname(hostname_input)
    print(f"📋 Hostname de entrada: {hostname_input}")
    print(f"📋 Hostname puro (sin puerto): {hostname_puro}")
    print()
    
    # 2. Verificar configuración de Django
    print("=" * 80)
    print("1️⃣ CONFIGURACIÓN DE DJANGO")
    print("=" * 80)
    print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
    print(f"   TENANT_URLCONF: {settings.TENANT_URLCONF}")
    print(f"   TENANT_MODEL: {settings.TENANT_MODEL}")
    print(f"   TENANT_DOMAIN_MODEL: {settings.TENANT_DOMAIN_MODEL}")
    print(f"   TENANT_DOMAIN_BASE: {getattr(settings, 'TENANT_DOMAIN_BASE', 'NO CONFIGURADO')}")
    print(f"   DEBUG: {settings.DEBUG}")
    print()
    
    # 3. Verificar modelos
    print("=" * 80)
    print("2️⃣ MODELOS DE TENANT")
    print("=" * 80)
    try:
        Client = get_tenant_model()
        Domain = get_tenant_domain_model()
        print(f"   ✅ Client model: {Client}")
        print(f"   ✅ Domain model: {Domain}")
    except Exception as e:
        print(f"   ❌ Error al obtener modelos: {e}")
        return
    print()
    
    # 4. Verificar esquema actual
    print("=" * 80)
    print("3️⃣ ESQUEMA ACTUAL")
    print("=" * 80)
    try:
        current_schema = connection.schema_name
        print(f"   Esquema actual: {current_schema}")
        public_schema = get_public_schema_name()
        print(f"   Esquema público: {public_schema}")
    except Exception as e:
        print(f"   ❌ Error al obtener esquema: {e}")
    print()
    
    # 5. Listar todos los dominios registrados
    print("=" * 80)
    print("4️⃣ DOMINIOS REGISTRADOS EN LA BASE DE DATOS")
    print("=" * 80)
    try:
        # Cambiar al esquema público para consultar dominios
        connection.set_schema_to_public()
        
        all_domains = Domain.objects.all().select_related('tenant').order_by('domain')
        
        if not all_domains.exists():
            print("   ⚠️  NO HAY DOMINIOS REGISTRADOS")
        else:
            print(f"   Total de dominios: {all_domains.count()}")
            print()
            print("   " + "-" * 76)
            print(f"   {'Dominio':<40} {'Tenant':<20} {'Primary':<10} {'Schema':<10}")
            print("   " + "-" * 76)
            
            for domain in all_domains:
                tenant_name = getattr(domain.tenant, 'nombre', domain.tenant.schema_name)
                primary_mark = "✅" if domain.is_primary else "  "
                match_mark = "🎯" if domain.domain == hostname_puro or domain.domain == hostname_input else "  "
                print(f"   {match_mark} {domain.domain:<38} {tenant_name:<20} {primary_mark:<10} {domain.tenant.schema_name:<10}")
            
            print("   " + "-" * 76)
            print()
            
            # Buscar coincidencias exactas
            exact_match = Domain.objects.filter(domain=hostname_puro).first()
            if exact_match:
                print(f"   ✅ COINCIDENCIA EXACTA ENCONTRADA:")
                print(f"      Dominio: {exact_match.domain}")
                print(f"      Tenant: {exact_match.tenant.nombre} ({exact_match.tenant.schema_name})")
                print(f"      Primary: {exact_match.is_primary}")
            else:
                print(f"   ❌ NO SE ENCONTRÓ COINCIDENCIA EXACTA para '{hostname_puro}'")
                
            # Buscar coincidencias con puerto
            if ':' in hostname_input:
                exact_match_with_port = Domain.objects.filter(domain=hostname_input).first()
                if exact_match_with_port:
                    print(f"   ✅ COINCIDENCIA CON PUERTO ENCONTRADA:")
                    print(f"      Dominio: {exact_match_with_port.domain}")
                    print(f"      Tenant: {exact_match_with_port.tenant.nombre} ({exact_match_with_port.tenant.schema_name})")
                    print(f"      Primary: {exact_match_with_port.is_primary}")
                else:
                    print(f"   ⚠️  NO SE ENCONTRÓ COINCIDENCIA CON PUERTO para '{hostname_input}'")
                    print(f"   ℹ️  django-tenants usa SOLO el hostname sin puerto para resolver")
    except Exception as e:
        print(f"   ❌ Error al consultar dominios: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 6. Simular resolución del middleware
    print("=" * 80)
    print("5️⃣ SIMULACIÓN DE RESOLUCIÓN DEL MIDDLEWARE")
    print("=" * 80)
    try:
        # Crear un request simulado
        request = HttpRequest()
        request.META['HTTP_HOST'] = hostname_input
        request.META['SERVER_NAME'] = hostname_puro
        request.META['SERVER_PORT'] = '8000' if ':8000' in hostname_input else '80'
        
        # Intentar resolver usando el middleware
        middleware = TenantMainMiddleware(get_response=lambda req: None)
        
        # El middleware modifica connection.schema_name
        # Guardar el esquema original
        original_schema = connection.schema_name
        
        try:
            # Simular el proceso del middleware
            middleware.process_request(request)
            
            # Verificar qué tenant se resolvió
            resolved_schema = connection.schema_name
            resolved_tenant = getattr(request, 'tenant', None)
            
            if resolved_tenant:
                print(f"   ✅ TENANT RESUELTO:")
                print(f"      Tenant: {resolved_tenant.nombre} ({resolved_tenant.schema_name})")
                print(f"      Esquema activo: {resolved_schema}")
                print(f"      URLConf que se usará: {settings.TENANT_URLCONF if resolved_schema != public_schema else settings.ROOT_URLCONF}")
            else:
                print(f"   ❌ NO SE PUDO RESOLVER EL TENANT")
                print(f"      Esquema activo: {resolved_schema}")
                print(f"      URLConf que se usará: {settings.ROOT_URLCONF}")
                print(f"      ⚠️  Esto significa que se usará el esquema público")
        finally:
            # Restaurar el esquema original
            connection.set_schema(original_schema)
            
    except Exception as e:
        print(f"   ❌ Error al simular middleware: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 7. Verificar configuración de dominio base
    print("=" * 80)
    print("6️⃣ VERIFICACIÓN DE CONFIGURACIÓN DE DOMINIO BASE")
    print("=" * 80)
    tenant_domain_base = getattr(settings, 'TENANT_DOMAIN_BASE', None)
    if tenant_domain_base:
        print(f"   TENANT_DOMAIN_BASE: {tenant_domain_base}")
        print(f"   Hostname esperado para tenant 'home': home.{tenant_domain_base}")
        
        # Verificar si el hostname coincide con el patrón esperado
        if hostname_puro.startswith('home.'):
            expected_domain = f"home.{tenant_domain_base}"
            if hostname_puro == expected_domain:
                print(f"   ✅ El hostname coincide con el patrón esperado")
            else:
                print(f"   ⚠️  El hostname NO coincide con el patrón esperado")
                print(f"      Esperado: {expected_domain}")
                print(f"      Recibido: {hostname_puro}")
    else:
        print("   ⚠️  TENANT_DOMAIN_BASE no está configurado en settings.py")
    print()
    
    # 8. Recomendaciones
    print("=" * 80)
    print("7️⃣ RECOMENDACIONES")
    print("=" * 80)
    
    try:
        connection.set_schema_to_public()
        exact_match = Domain.objects.filter(domain=hostname_puro).first()
        
        if not exact_match:
            print("   ❌ PROBLEMA DETECTADO: No existe un dominio registrado para este hostname")
            print()
            print("   💡 SOLUCIÓN:")
            print(f"      1. Verifica que el tenant 'home' existe en la base de datos")
            print(f"      2. Verifica que existe un Domain con domain='{hostname_puro}'")
            print(f"      3. Si no existe, crea el dominio manualmente:")
            print()
            print(f"         from apps.public.tenants.models import Client, Domain")
            print(f"         from django_tenants.utils import set_tenant_to_public")
            print()
            print(f"         set_tenant_to_public()")
            print(f"         client = Client.objects.get(schema_name='home')")
            print(f"         Domain.objects.get_or_create(")
            print(f"             domain='{hostname_puro}',")
            print(f"             defaults={{'tenant': client, 'is_primary': True}}")
            print(f"         )")
            print()
        else:
            print("   ✅ El dominio está registrado correctamente")
            print(f"      Tenant: {exact_match.tenant.nombre}")
            print(f"      Schema: {exact_match.tenant.schema_name}")
            print()
            print("   💡 Si aún así no funciona, verifica:")
            print("      1. Que el middleware TenantMainMiddleware esté activo")
            print("      2. Que esté configurado como PRIMER middleware en settings.py")
            print("      3. Que el servidor web (nginx/apache) esté pasando el header HTTP_HOST correctamente")
    except Exception as e:
        print(f"   ❌ Error al generar recomendaciones: {e}")
    
    print()
    print("=" * 80)
    print("✅ DIAGNÓSTICO COMPLETADO")
    print("=" * 80)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python scripts/diagnostico_forense_tenant.py <hostname>")
        print("Ejemplo: python scripts/diagnostico_forense_tenant.py home.localhost")
        sys.exit(1)
    
    hostname = sys.argv[1]
    diagnostico_completo(hostname)
