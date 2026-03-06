"""
Tests de ruteo multi-tenant y autenticación del workspace.

Verifica que:
- Dominio público: GET /workspace/ → 404/NoMatch
- Anónimo en tenant: GET /workspace/ → 302 a /login/
- Login en tenant: GET /workspace/ → 200
"""
import pytest
from django.test import Client
from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework import status
from apps.public.tenants.models import Client as TenantClient, Domain
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestWorkspaceRoutingAuth:
    """
    Tests para verificar el ruteo multi-tenant y autenticación del workspace.
    """

    def test_workspace_not_available_in_public_domain(self, db):
        """
        Verifica que GET /workspace/ no está disponible en el dominio público.
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear cliente sin dominio de tenant
        client = Client()
        
        # Intentar acceder a /workspace/ desde dominio público
        # Debe retornar 404 o NoMatch (no debe estar en PUBLIC_URLCONF)
        response = client.get('/workspace/', HTTP_HOST='sintel.com')
        
        # Debe retornar 404 (no encontrado) o 302 (redirección)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_302_FOUND]

    def test_workspace_redirects_anonymous_to_login(self, db):
        """
        Verifica que GET /workspace/ redirige a /login/ cuando el usuario no está autenticado.
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear tenant y dominio
        tenant = TenantClient.objects.create(
            schema_name='test_cliente',
            nombre='Cliente Test',
            is_active=True,
            on_trial=True
        )
        
        domain = Domain.objects.create(
            tenant=tenant,
            domain='cliente.sintel.local',
            is_primary=True
        )
        
        # Crear cliente sin autenticar
        client = Client()
        
        # Intentar acceder a /workspace/ desde dominio del tenant sin autenticar
        response = client.get('/workspace/', HTTP_HOST=domain.domain)
        
        # Debe redirigir a /login/ (302)
        assert response.status_code == status.HTTP_302_FOUND
        assert '/login/' in response.url

    def test_workspace_returns_200_when_authenticated(self, db):
        """
        Verifica que GET /workspace/ retorna 200 cuando el usuario está autenticado en el tenant.
        """
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()
        
        # Crear tenant y dominio
        tenant = TenantClient.objects.create(
            schema_name='test_cliente',
            nombre='Cliente Test',
            is_active=True,
            on_trial=True
        )
        
        domain = Domain.objects.create(
            tenant=tenant,
            domain='cliente.sintel.local',
            is_primary=True
        )
        
        # Crear usuario y membresía
        user = User.objects.create_user(
            email='admin@cliente.sintel.local',
            username='admin',
            password='testpass123',
            is_active=True
        )
        
        from apps.public.tenants.models import TenantMembership
        TenantMembership.objects.create(
            client=tenant,
            user=user,
            rol='ADMIN',
            is_primary_admin=True,
            is_active=True
        )
        
        # Crear cliente autenticado
        client = Client()
        client.force_login(user)
        
        # Acceder a /workspace/ desde dominio del tenant autenticado
        response = client.get('/workspace/', HTTP_HOST=domain.domain)
        
        # Debe retornar 200 OK
        assert response.status_code == status.HTTP_200_OK
