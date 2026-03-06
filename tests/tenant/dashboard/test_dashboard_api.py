"""
Pruebas de humo para la API del dashboard (API-First).

⚠️ v2.30: Verifica que los endpoints del dashboard funcionan correctamente.
"""
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, tenant_context
from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class TestDashboardSummaryAPI(SintelTenantTestCase):
    """Pruebas para el endpoint de resumen del dashboard."""
    
    def test_summary_requires_authentication(self):
        """Verifica que el endpoint requiere autenticación."""
        # Crear cliente sin autenticación
        from rest_framework.test import APIClient
        unauthenticated_client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Hacer request sin autenticación
        response = unauthenticated_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_summary_returns_data_for_authenticated_user(self):
        """Verifica que el endpoint retorna datos para usuario autenticado."""
        # Hacer request con usuario autenticado (self.api_client ya está autenticado)
        response = self.api_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tenant' in response.data
        assert 'user' in response.data
        assert 'user_role' in response.data
        assert 'kpis' in response.data
        assert 'redirect_url' in response.data
        
        # Verificar datos del tenant
        assert response.data['tenant']['id'] == self.tenant.id
        assert response.data['tenant']['nombre'] == self.tenant.nombre
        
        # Verificar datos del usuario
        assert response.data['user']['id'] == self.user.id
        assert response.data['user']['email'] == self.user.email
        
        # Verificar rol (debería ser ADMIN por defecto en SintelTenantTestCase)
        assert response.data['user_role'] == 'ADMIN'
        
        # Verificar redirect_url
        assert response.data['redirect_url'] == '/dashboard/admin/'


class TestDashboardKPIsAPI(SintelTenantTestCase):
    """Pruebas para el endpoint de KPIs del dashboard."""
    
    def test_kpis_requires_authentication(self):
        """Verifica que el endpoint requiere autenticación."""
        # Crear cliente sin autenticación
        from rest_framework.test import APIClient
        unauthenticated_client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Hacer request sin autenticación
        response = unauthenticated_client.get('/api/v1/dashboard/kpis/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_kpis_returns_data_for_authenticated_user(self):
        """Verifica que el endpoint retorna KPIs para usuario autenticado."""
        # Hacer request con usuario autenticado
        response = self.api_client.get('/api/v1/dashboard/kpis/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_facturas' in response.data
        assert 'facturas_pendientes' in response.data
        assert 'total_clientes' in response.data
        assert 'ingresos_mes' in response.data


class TestDashboardQuickActionsAPI(SintelTenantTestCase):
    """Pruebas para el endpoint de acciones rápidas del dashboard."""
    
    def test_quick_actions_requires_authentication(self):
        """Verifica que el endpoint requiere autenticación."""
        # Crear cliente sin autenticación
        from rest_framework.test import APIClient
        unauthenticated_client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Hacer request sin autenticación
        response = unauthenticated_client.get('/api/v1/dashboard/quick-actions/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_quick_actions_returns_data_for_admin(self):
        """Verifica que el endpoint retorna acciones para ADMIN."""
        # Hacer request con usuario ADMIN (self.user es ADMIN por defecto)
        response = self.api_client.get('/api/v1/dashboard/quick-actions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        
        # Verificar que hay acciones
        assert len(response.data) > 0
        
        # Verificar estructura de acciones
        for action in response.data:
            assert 'id' in action
            assert 'label' in action
            assert 'url' in action
    
    def test_quick_actions_filtered_by_role(self):
        """Verifica que las acciones se filtran según el rol."""
        # Crear usuario con rol USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario USER
        from rest_framework.test import APIClient
        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user)
        
        # Hacer request con usuario USER
        response = user_client.get('/api/v1/dashboard/quick-actions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        
        # Hacer request con usuario ADMIN
        admin_response = self.api_client.get('/api/v1/dashboard/quick-actions/')
        
        # USER debería tener menos acciones que ADMIN
        assert len(response.data) <= len(admin_response.data)


class TestDashboardPermissions(SintelTenantTestCase):
    """Pruebas de permisos por rol."""
    
    def test_user_without_membership_denied(self):
        """Verifica que un usuario sin membresía es denegado."""
        # Crear usuario sin membresía
        with schema_context('public'):
            user = User.objects.create_user(
                email='no-member@test-dashboard.local',
                password='testpass123',
            )
        
        # Crear cliente autenticado con usuario sin membresía
        from rest_framework.test import APIClient
        no_member_client = APIClient(HTTP_HOST=self.domain.domain)
        no_member_client.force_authenticate(user=user)
        
        # Hacer request
        response = no_member_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_user_with_inactive_membership_denied(self):
        """Verifica que un usuario con membresía inactiva es denegado."""
        # Crear usuario con membresía inactiva
        with schema_context('public'):
            user = User.objects.create_user(
                email='inactive@test-dashboard.local',
                password='testpass123',
            )
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=False,  # Membresía inactiva
            )
        
        # Crear cliente autenticado con usuario con membresía inactiva
        from rest_framework.test import APIClient
        inactive_client = APIClient(HTTP_HOST=self.domain.domain)
        inactive_client.force_authenticate(user=user)
        
        # Hacer request
        response = inactive_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDashboardRedirectURL(SintelTenantTestCase):
    """Pruebas para redirect_url según rol."""
    
    def test_admin_redirect_url(self):
        """Verifica que ADMIN recibe redirect_url correcta."""
        # self.user es ADMIN por defecto
        response = self.api_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['redirect_url'] == '/dashboard/admin/'
    
    def test_staff_redirect_url(self):
        """Verifica que STAFF recibe redirect_url correcta."""
        # Crear usuario STAFF
        with schema_context('public'):
            staff = User.objects.create_user(
                email='staff@test-dashboard.local',
                password='testpass123',
            )
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant,
                user=staff,
                rol='STAFF',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario STAFF
        from rest_framework.test import APIClient
        staff_client = APIClient(HTTP_HOST=self.domain.domain)
        staff_client.force_authenticate(user=staff)
        
        response = staff_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['redirect_url'] == '/dashboard/staff/'
    
    def test_user_redirect_url(self):
        """Verifica que USER recibe redirect_url correcta."""
        # Crear usuario USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario USER
        from rest_framework.test import APIClient
        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user)
        
        response = user_client.get('/api/v1/dashboard/summary/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['redirect_url'] == '/dashboard/user/'
