"""
Script de auditoría para verificar que los endpoints API retornan SOLO JSON (sin HTML).

⚠️ POLÍTICA API-First: Los endpoints DRF NUNCA deben devolver HTML.
Este script lanza GET requests a una lista de endpoints y falla si encuentra HTML.
"""
import os
import sys
from pathlib import Path
import django

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain, TenantMembership
from django_tenants.utils import schema_context

User = get_user_model()

# Lista de endpoints a verificar
ENDPOINTS_TO_CHECK = [
    '/api/v1/empresas/',
    '/api/v1/facturas/',
    '/api/v1/asientos-contables/',
    '/api/v1/core/dashboard/sections/',
    '/api/v1/core/links/',
    '/api/v1/perfil/perfiles/me/',
]

# Etiquetas HTML que NO deben aparecer en respuestas API
HTML_TAGS = ['<html', '<pre', 'json-formatter-container', '<body', '<head', '<div class="api">']


def check_endpoint(client, endpoint, tenant_domain):
    """
    Verifica que un endpoint retorna solo JSON (sin HTML).
    
    Args:
        client: Django test client
        endpoint: Ruta del endpoint (ej: '/api/v1/empresas/')
        tenant_domain: Dominio del tenant (ej: 'cliente.sintel.com')
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Hacer request con el dominio del tenant
        response = client.get(
            endpoint,
            HTTP_HOST=tenant_domain,
            follow=False
        )
        
        # Verificar status code (puede ser 200, 401, 403, 404, etc.)
        if response.status_code not in [200, 401, 403, 404, 405]:
            return False, f"Status code inesperado: {response.status_code}"
        
        # Verificar Content-Type
        content_type = response.get('Content-Type', '')
        if 'application/json' not in content_type and response.status_code == 200:
            return False, f"Content-Type no es JSON: {content_type}"
        
        # Obtener contenido como texto
        content = response.content.decode('utf-8', errors='ignore')
        
        # Verificar que NO contiene etiquetas HTML
        found_html_tags = []
        for tag in HTML_TAGS:
            if tag.lower() in content.lower():
                found_html_tags.append(tag)
        
        if found_html_tags:
            return False, f"Contiene etiquetas HTML: {found_html_tags}"
        
        # Verificar que es JSON válido (si status es 200)
        if response.status_code == 200:
            try:
                import json
                json.loads(content)
            except json.JSONDecodeError:
                return False, "No es JSON válido"
        
        return True, "OK"
        
    except Exception as e:
        return False, f"Error: {str(e)}"


def run_audit():
    """
    Ejecuta la auditoría de todos los endpoints.
    """
    sys.stdout.buffer.write(b"🔍 Auditoría: Verificando que endpoints API retornan SOLO JSON...\n")
    sys.stdout.buffer.write(b"======================================================================\n\n")
    
    # Obtener un tenant de prueba
    try:
        with schema_context('public'):
            tenant = Client.objects.first()
            if not tenant:
                sys.stdout.buffer.write(b"⚠️  No se encontró ningún tenant. Creando uno de prueba...\n")
                # Crear tenant de prueba si no existe
                tenant = Client.objects.create(
                    schema_name='test_tenant',
                    nombre='Tenant de Prueba'
                )
                Domain.objects.create(
                    domain='test.sintel.com',
                    tenant=tenant,
                    is_primary=True
                )
            
            domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            if not domain:
                sys.stdout.buffer.write(b"❌ No se encontró dominio para el tenant.\n")
                sys.exit(1)
            
            tenant_domain = domain.domain
            
            # Crear usuario de prueba si no existe
            user, created = User.objects.get_or_create(
                email='test@example.com',
                defaults={'username': 'testuser'}
            )
            
            # Crear membresía si no existe
            TenantMembership.objects.get_or_create(
                client=tenant,
                user=user,
                defaults={'rol': 'ADMIN', 'is_active': True}
            )
            
    except Exception as e:
        sys.stdout.buffer.write(f"❌ Error configurando tenant de prueba: {e}\n".encode('utf-8'))
        sys.exit(1)
    
    # Crear cliente de prueba
    client = Client()
    
    # Autenticar usuario
    client.force_login(user)
    
    # Verificar cada endpoint
    errors = []
    warnings = []
    
    for endpoint in ENDPOINTS_TO_CHECK:
        sys.stdout.buffer.write(f"Verificando {endpoint}... ".encode('utf-8'))
        
        # Cambiar al esquema del tenant
        with schema_context(tenant.schema_name):
            success, message = check_endpoint(client, endpoint, tenant_domain)
            
            if success:
                sys.stdout.buffer.write(b"✅ OK\n")
            else:
                sys.stdout.buffer.write(f"❌ {message}\n".encode('utf-8'))
                errors.append((endpoint, message))
    
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.write(b"======================================================================\n")
    
    if errors:
        sys.stdout.buffer.write(f"❌ ERRORES ENCONTRADOS ({len(errors)}):\n".encode('utf-8'))
        for endpoint, message in errors:
            sys.stdout.buffer.write(f"   {endpoint}: {message}\n".encode('utf-8'))
        sys.stdout.buffer.write(b"\n❌ Auditoría FALLIDA\n\n")
        sys.exit(1)
    else:
        sys.stdout.buffer.write(b"✅ Auditoría EXITOSA\n\n")
        sys.exit(0)


if __name__ == "__main__":
    run_audit()
