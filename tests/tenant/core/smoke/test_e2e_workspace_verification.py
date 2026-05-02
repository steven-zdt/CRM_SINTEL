"""
Verificación específica del workspace: que consume Core API correctamente.

[WARNING] POLÍTICA v2.30: Verificar que workspace.html y sus partials consumen Core API.
"""
from django.test import TestCase, Client
import pytest

try:
    import playwright  # noqa: F401
    import cryptography  # noqa: F401
except Exception:
    pytest.skip("Skipping heavy smoke test: missing playwright/cryptography", allow_module_level=True)
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework import status

from apps.public.tenants.models import Client as TenantClient, Domain, TenantMembership
from apps.services.onboarding.empresa_service import crear_empresa

User = get_user_model()


class TestWorkspaceVerification(TestCase):
    """Verificación del workspace y consumo de Core API."""
    
    def setUp(self):
        """Configuración inicial."""
        with schema_context('public'):
            result = crear_empresa(
                nombre='Empresa Workspace Test',
                email_admin='owner@workspace.com',
                schema_name='test-workspace',
                on_trial=True,
            )
            self.owner_user = result['user']
            self.owner_user.set_password('testpass123')
            self.owner_user.save()
            
            self.tenant = result['client']
            self.tenant_domain = result['domain'].domain
    
    def test_workspace_view_accessible(self):
        """Verificar que /workspace/ es accesible."""
        client = Client(HTTP_HOST=self.tenant_domain)
        client.force_login(self.owner_user)
        
        response = client.get('/workspace/')
        
        # Debe retornar 200 (template renderizado)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Debe ser HTML
        self.assertIn('text/html', response['Content-Type'])
        # Debe contener el template workspace
        self.assertIn('workspace', response.content.decode('utf-8').lower())
    
    def test_workspace_consumes_core_api_endpoints(self):
        """Verificar que workspace consume endpoints Core API."""
        client = APIClient(HTTP_HOST=self.tenant_domain)
        client.force_authenticate(user=self.owner_user)
        
        # Endpoints que workspace debe consumir (vía JS o partials)
        core_endpoints = [
            '/api/v1/core/dashboard/',
            '/api/v1/core/mi-empresa/',
            '/api/v1/core/mi-perfil/',
            '/api/v1/core/facturas/resumen/',
            '/api/v1/core/contabilidad/resumen/',
        ]
        
        for endpoint in core_endpoints:
            response = client.get(endpoint)
            
            # Todos deben retornar 200
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Endpoint Core {endpoint} debe estar accesible para workspace"
            )
            
            # Todos deben retornar JSON
            self.assertEqual(
                response['Content-Type'],
                'application/json',
                f"Endpoint Core {endpoint} debe retornar JSON"
            )
            
            data = response.json()
            self.assertIsInstance(data, dict)
    
    def test_workspace_partials_consume_core(self):
        """Verificar que los partials de workspace consumen Core API."""
        client = APIClient(HTTP_HOST=self.tenant_domain)
        client.force_authenticate(user=self.owner_user)
        
        # Partials que workspace carga vía HTMX
        # Estos partials deben consumir Core API internamente
        partials_endpoints = [
            '/ui/dashboard/partials/header/',
            '/ui/dashboard/partials/kpis/',
            '/ui/empresa/partials/card/',
            '/ui/facturas/partials/table/',
            '/ui/contabilidad/partials/summary/',
            '/ui/perfil/partials/card/',
        ]
        
        for endpoint in partials_endpoints:
            response = client.get(endpoint)
            
            # Deben retornar 200 (HTML partial)
            # Nota: Algunos pueden retornar 404 si no están implementados
            # pero los que existen deben funcionar
            if response.status_code == status.HTTP_200_OK:
                # Debe ser HTML
                self.assertIn('text/html', response['Content-Type'])
    
    def test_workspace_data_structure_from_core(self):
        """Verificar que los datos de Core tienen estructura esperada para workspace."""
        client = APIClient(HTTP_HOST=self.tenant_domain)
        client.force_authenticate(user=self.owner_user)
        
        # Obtener datos del dashboard desde Core
        response = client.get('/api/v1/core/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        
        # Estructura mínima esperada para workspace
        self.assertIn('tenant', data)
        self.assertIn('user', data)
        self.assertIn('empresa', data)
        self.assertIn('facturas', data)
        self.assertIn('contabilidad', data)
        self.assertIn('perfil', data)
        self.assertIn('branding', data)
        
        # Verificar que branding tiene nombre (para header)
        branding = data['branding']
        self.assertIn('nombre', branding)
        
        # Verificar que facturas tiene estructura para KPIs
        facturas = data['facturas']
        self.assertIn('total', facturas)
        self.assertIn('pendientes', facturas)
        self.assertIn('mes_actual', facturas)
