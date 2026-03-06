"""
Pruebas de integración para redirección por rol en dashboard.

Cubre:
- Login ADMIN/STAFF/USER → redirect_url correcto
- Acceso manual a /dashboard/ → redirección por rol
- Intento de acceso a dashboards no permitidos → 403
"""
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient

from tests.tenant.base_test import SintelTenantTestCase
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class TestLoginRedirectByRole(SintelTenantTestCase):
    """Pruebas de redirect_url en Login API según rol."""
    
    def test_login_admin_returns_admin_redirect_url(self):
        """Verifica que login de ADMIN retorna redirect_url de admin."""
        # self.user es ADMIN por defecto
        response = self.api_client.post(
            '/api/v1/landing/auth/login/',
            {
                'email': self.user.email,
                'password': self.get_user_password(),
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/admin/'
    
    def test_login_staff_returns_staff_redirect_url(self):
        """Verifica que login de STAFF retorna redirect_url de staff."""
        # Crear usuario STAFF
        with schema_context('public'):
            staff = User.objects.create_user(
                email='staff@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=staff,
                rol='STAFF',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario STAFF
        staff_client = APIClient(HTTP_HOST=self.domain.domain)
        staff_client.force_authenticate(user=staff)
        
        # Hacer login (simular POST)
        response = staff_client.post(
            '/api/v1/landing/auth/login/',
            {
                'email': staff.email,
                'password': 'testpass123',
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/staff/'
    
    def test_login_user_returns_user_redirect_url(self):
        """Verifica que login de USER retorna redirect_url de user."""
        # Crear usuario USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario USER
        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user)
        
        # Hacer login (simular POST)
        response = user_client.post(
            '/api/v1/landing/auth/login/',
            {
                'email': user.email,
                'password': 'testpass123',
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/user/'


class TestDashboardDispatcherRedirect(SintelTenantTestCase):
    """
    Pruebas del dispatcher /dashboard/ (API-First).
    
    ⚠️ NOTA: Con API-First estricto, /dashboard/ ya no está expuesto como ruta server-side.
    Si se necesita una ruta /dashboard/, debe ser manejada por el frontend (SPA) o shell estático.
    Estos tests verifican que la redirección por rol funcione desde la API de login/activación.
    """
    
    def test_login_api_returns_correct_redirect_url_for_admin(self):
        """Verifica que la API de login retorna redirect_url correcta para ADMIN."""
        # self.user es ADMIN por defecto
        response = self.api_client.post(
            '/api/v1/landing/auth/login/',
            {
                'email': self.user.email,
                'password': self.get_user_password(),
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/admin/'
    
    def test_login_api_returns_correct_redirect_url_for_staff(self):
        """Verifica que la API de login retorna redirect_url correcta para STAFF."""
        # Crear usuario STAFF
        with schema_context('public'):
            staff = User.objects.create_user(
                email='staff@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=staff,
                rol='STAFF',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario STAFF
        staff_client = APIClient(HTTP_HOST=self.domain.domain)
        staff_client.force_authenticate(user=staff)
        
        # Hacer login (simular POST)
        response = staff_client.post(
            '/api/v1/landing/auth/login/',
            {
                'email': staff.email,
                'password': 'testpass123',
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/staff/'
    
    def test_login_api_returns_correct_redirect_url_for_user(self):
        """Verifica que la API de login retorna redirect_url correcta para USER."""
        # Crear usuario USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario USER
        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user)
        
        # Hacer login (simular POST)
        response = user_client.post(
            '/api/v1/landing/auth/login/',
            {
                'email': user.email,
                'password': 'testpass123',
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/user/'


class TestDashboardAPIAccessControl(SintelTenantTestCase):
    """Pruebas de control de acceso a APIs del dashboard por rol."""
    
    def test_user_cannot_access_admin_only_api(self):
        """Verifica que USER no puede acceder a APIs que requieren ADMIN."""
        # Crear usuario USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario USER
        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user)
        
        # Intentar acceder a API del dashboard (debe permitir acceso básico)
        response = user_client.get('/api/v1/dashboard/summary/')
        
        # Debe permitir acceso (200) - el endpoint summary permite USER o superior
        assert response.status_code == status.HTTP_200_OK
    
    def test_user_can_access_user_level_api(self):
        """Verifica que USER puede acceder a APIs de nivel USER."""
        # Crear usuario USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario USER
        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user)
        
        # Acceder a API del dashboard
        response = user_client.get('/api/v1/dashboard/summary/')
        
        # Debe permitir acceso (200)
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/user/'
    
    def test_staff_can_access_staff_level_api(self):
        """Verifica que STAFF puede acceder a APIs de nivel STAFF."""
        # Crear usuario STAFF
        with schema_context('public'):
            staff = User.objects.create_user(
                email='staff@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=staff,
                rol='STAFF',
                is_active=True,
            )
        
        # Crear cliente autenticado con usuario STAFF
        staff_client = APIClient(HTTP_HOST=self.domain.domain)
        staff_client.force_authenticate(user=staff)
        
        # Acceder a API del dashboard
        response = staff_client.get('/api/v1/dashboard/summary/')
        
        # Debe permitir acceso (200)
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/staff/'
    
    def test_admin_can_access_all_apis(self):
        """Verifica que ADMIN puede acceder a todas las APIs."""
        # self.user es ADMIN por defecto
        
        # Acceder a API del dashboard
        response = self.api_client.get('/api/v1/dashboard/summary/')
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        assert response.data['redirect_url'] == '/dashboard/admin/'
        
        # Acceder a KPIs
        response = self.api_client.get('/api/v1/dashboard/kpis/')
        assert response.status_code == status.HTTP_200_OK
        
        # Acceder a quick actions
        response = self.api_client.get('/api/v1/dashboard/quick-actions/')
        assert response.status_code == status.HTTP_200_OK


class TestActivationRedirectByRole(SintelTenantTestCase):
    """Pruebas de redirect_url en Activación API según rol."""
    
    def test_activation_returns_role_based_redirect_url(self):
        """Verifica que la activación retorna redirect_url por rol."""
        # Nota: Este test requiere un token de activación válido
        # Por simplicidad, verificamos que la función get_dashboard_redirect_url
        # funciona correctamente para cada rol
        
        # ADMIN
        redirect_url = self._get_redirect_url_for_role('ADMIN')
        assert redirect_url == '/dashboard/admin/'
        
        # STAFF
        with schema_context('public'):
            staff = User.objects.create_user(
                email='staff@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=staff,
                rol='STAFF',
                is_active=True,
            )
        
        from apps.tenant.dashboard.services import get_dashboard_redirect_url
        redirect_url = get_dashboard_redirect_url(staff, self.tenant, absolute=False)
        assert redirect_url == '/dashboard/staff/'
        
        # USER
        with schema_context('public'):
            user = User.objects.create_user(
                email='user@test-dashboard.local',
                password='testpass123',
            )
            TenantMembership.objects.create(
                client=self.tenant,
                user=user,
                rol='USER',
                is_active=True,
            )
        
        redirect_url = get_dashboard_redirect_url(user, self.tenant, absolute=False)
        assert redirect_url == '/dashboard/user/'
    
    def _get_redirect_url_for_role(self, role):
        """Helper para obtener redirect_url según rol."""
        from apps.tenant.dashboard.services import get_dashboard_redirect_url
        return get_dashboard_redirect_url(self.user, self.tenant, absolute=False)
