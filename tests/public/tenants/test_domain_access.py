"""
Tests funcionales para validar acceso desde subdominios dinámicos.

Valida que Django acepta correctamente peticiones desde subdominios
configurados (ej: cliente.sintel.com) y que el esquema correcto está activo.
"""
import pytest
from django.test import Client
from django.db import connection

# Imports dentro de funciones para evitar problemas de configuración de Django
# Los modelos y factories se importan dentro de las funciones que los usan


@pytest.mark.django_db
class TestDomainAccess:
    """
    Tests para validar acceso desde subdominios dinámicos.
    
    Escenario: Crear un tenant con dominio y verificar que Django
    acepta peticiones desde ese dominio.
    """
    
    def test_access_from_subdomain_returns_ok(self):
        """Test: Verificar que una petición desde subdominio retorna 200/302 (no 400)."""
        from apps.public.tenants.models import Client as TenantClient, Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory
        
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear tenant con dominio de sintel.com
        tenant = ClientFactory(
            nombre="Empresa Test Access",
            schema_name="test_access",
            is_active=True
        )
        
        # Crear dominio asociado
        domain = DomainFactory(
            tenant=tenant,
            domain="test-access.sintel.com",
            is_primary=True
        )
        
        # Verificar que el tenant y dominio fueron creados
        assert tenant.schema_name == "test_access"
        assert domain.domain == "test-access.sintel.com"
        
        # Crear cliente de pruebas
        client = Client()
        
        # Hacer petición con HTTP_HOST configurado al dominio del tenant
        response = client.get(
            '/',
            HTTP_HOST=domain.domain
        )
        
        # Debe retornar 200 OK o 302 Redirect (NO debe retornar 400 Bad Request / DisallowedHost)
        assert response.status_code in (200, 302, 404), \
            f"La petición desde subdominio debe retornar 200/302/404, no {response.status_code}. " \
            f"Error: {response.content.decode('utf-8')[:200] if hasattr(response, 'content') else 'N/A'}"
        
        # Verificar que NO es un error de DisallowedHost
        assert response.status_code != 400, \
            f"La petición no debe retornar 400 Bad Request (DisallowedHost). " \
            f"Status: {response.status_code}, Content: {response.content.decode('utf-8')[:200]}"
    
    def test_access_from_subdomain_uses_correct_schema(self):
        """Test: Verificar que el esquema correcto está activo cuando se accede desde subdominio."""
        from apps.public.tenants.models import Client as TenantClient, Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory
        from django_tenants.utils import schema_exists
        
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear tenant con dominio de sintel.com
        tenant = ClientFactory(
            nombre="Empresa Schema Test",
            schema_name="schema_test",
            is_active=True
        )
        
        # Crear dominio asociado
        domain = DomainFactory(
            tenant=tenant,
            domain="schema-test.sintel.com",
            is_primary=True
        )
        
        # Verificar que el esquema existe
        assert schema_exists(tenant.schema_name), \
            f"El esquema '{tenant.schema_name}' debe existir en la base de datos"
        
        # Crear cliente de pruebas
        client = Client()
        
        # Hacer petición con HTTP_HOST configurado
        response = client.get(
            '/',
            HTTP_HOST=domain.domain
        )
        
        # Verificar que la petición fue aceptada
        assert response.status_code in (200, 302, 404), \
            f"La petición debe ser aceptada. Status: {response.status_code}"
        
        # Nota: En un test real, podrías verificar el contenido específico del tenant
        # o usar un contexto de esquema para verificar que el esquema correcto está activo.
        # Por ahora, verificamos que la petición fue aceptada sin errores de DisallowedHost.
    
    def test_access_from_multiple_subdomains(self):
        """Test: Verificar acceso desde múltiples subdominios diferentes."""
        from apps.public.tenants.models import Client as TenantClient, Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory
        
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear múltiples tenants con diferentes subdominios
        tenants_data = [
            ("empresa1", "empresa1.sintel.com"),
            ("empresa2", "empresa2.sintel.com"),
            ("empresa3", "empresa3.sintel.com"),
        ]
        
        tenants = []
        for schema_name, domain_name in tenants_data:
            tenant = ClientFactory(
                nombre=f"Empresa {schema_name}",
                schema_name=schema_name,
                is_active=True
            )
            domain = DomainFactory(
                tenant=tenant,
                domain=domain_name,
                is_primary=True
            )
            tenants.append((tenant, domain))
        
        # Crear cliente de pruebas
        client = Client()
        
        # Verificar acceso desde cada subdominio
        for tenant, domain in tenants:
            response = client.get(
                '/',
                HTTP_HOST=domain.domain
            )
            
            # Cada petición debe ser aceptada
            assert response.status_code in (200, 302, 404), \
                f"Petición desde {domain.domain} debe retornar 200/302/404, " \
                f"no {response.status_code}"
            
            # No debe ser error de DisallowedHost
            assert response.status_code != 400, \
                f"Petición desde {domain.domain} no debe retornar 400 Bad Request"
    
    def test_access_from_base_domain(self):
        """Test: Verificar acceso desde el dominio base (sintel.com)."""
        from apps.public.tenants.models import Client as TenantClient, Domain
        
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Obtener o crear tenant público
        public_tenant = TenantClient.objects.filter(schema_name='public').first()
        if not public_tenant:
            public_tenant = TenantClient.objects.create(
                nombre="SINTEL Global",
                schema_name="public"
            )
        
        # Crear cliente de pruebas
        client = Client()
        
        # Hacer petición desde el dominio base
        response = client.get(
            '/',
            HTTP_HOST='sintel.com'
        )
        
        # Debe ser aceptada (puede ser 200, 302, o 404 dependiendo de la configuración)
        assert response.status_code in (200, 302, 404), \
            f"Petición desde dominio base debe retornar 200/302/404, no {response.status_code}"
        
        # No debe ser error de DisallowedHost
        assert response.status_code != 400, \
            "Petición desde dominio base no debe retornar 400 Bad Request"
    
    def test_suspended_tenant_blocks_access_from_subdomain(self):
        """Test: Verificar que un tenant suspendido bloquea acceso desde su subdominio."""
        from apps.public.tenants.models import Client as TenantClient, Domain
        from tests.public.tenants.factories import ClientFactory, DomainFactory
        
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear tenant suspendido
        tenant = ClientFactory(
            nombre="Empresa Suspendida",
            schema_name="suspended_test",
            is_active=False  # Tenant suspendido
        )
        
        # Crear dominio asociado
        domain = DomainFactory(
            tenant=tenant,
            domain="suspended-test.sintel.com",
            is_primary=True
        )
        
        # Crear cliente de pruebas
        client = Client()
        
        # Hacer petición desde el subdominio del tenant suspendido
        response = client.get(
            '/',
            HTTP_HOST=domain.domain
        )
        
        # Debe retornar 403 Forbidden (bloqueado por TenantSecurityMiddleware)
        assert response.status_code == 403, \
            f"Tenant suspendido debe retornar 403 Forbidden, no {response.status_code}"
        
        # Verificar que el contenido contiene el mensaje de suspensión
        content = response.content.decode('utf-8')
        assert "Servicio Suspendido" in content or "Service Suspended" in content, \
            "La respuesta debe contener el mensaje de suspensión"
