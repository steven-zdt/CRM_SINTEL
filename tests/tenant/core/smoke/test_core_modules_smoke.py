"""
Smoke tests para módulos Core (facturas, contabilidad).

⚠️ POLÍTICA v2.30: Validar que Core expone resúmenes de facturas y contabilidad.
"""
from rest_framework import status
from rest_framework.test import APIClient
from tests.tenant.base_test import SintelTenantTestCase


class TestCoreModulesSmoke(SintelTenantTestCase):
    """Tests de humo para módulos Core (facturas, contabilidad)."""
    
    def test_facturas_resumen_200_keys(self):
        """GET /api/v1/core/facturas/resumen/ → 200 con llaves/estadísticas mínimas."""
        response = self.api_client.get('/api/v1/core/facturas/resumen/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Llaves mínimas esperadas
        self.assertIn('total', data)
        self.assertIn('pendientes', data)
        self.assertIn('aceptadas', data)
        self.assertIn('rechazadas', data)
        self.assertIn('mes_actual', data)
        self.assertIn('ultimas', data)
        
        # Verificar tipos
        self.assertIsInstance(data['total'], int)
        self.assertIsInstance(data['pendientes'], int)
        self.assertIsInstance(data['aceptadas'], int)
        self.assertIsInstance(data['rechazadas'], int)
        self.assertIsInstance(data['mes_actual'], dict)
        self.assertIsInstance(data['ultimas'], list)
        
        # Verificar estructura de mes_actual
        mes_actual = data['mes_actual']
        self.assertIn('cantidad', mes_actual)
        self.assertIn('total', mes_actual)
        self.assertIn('subtotal', mes_actual)
        self.assertIn('impuestos', mes_actual)
    
    def test_contabilidad_resumen_200_keys(self):
        """GET /api/v1/core/contabilidad/resumen/ → 200 con llaves/estadísticas mínimas."""
        response = self.api_client.get('/api/v1/core/contabilidad/resumen/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        
        # Llaves mínimas esperadas
        self.assertIn('total_cuentas', data)
        self.assertIn('total_asientos', data)
        self.assertIn('mes_actual', data)
        self.assertIn('ultimos_asientos', data)
        
        # Verificar tipos
        self.assertIsInstance(data['total_cuentas'], int)
        self.assertIsInstance(data['total_asientos'], int)
        self.assertIsInstance(data['mes_actual'], dict)
        self.assertIsInstance(data['ultimos_asientos'], list)
        
        # Verificar estructura de mes_actual
        mes_actual = data['mes_actual']
        self.assertIn('total_movimientos', mes_actual)
        self.assertIn('total_debitos', mes_actual)
        self.assertIn('total_creditos', mes_actual)
    
    def test_facturas_resumen_requires_authentication(self):
        """GET /api/v1/core/facturas/resumen/ sin autenticación → 401/403."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/facturas/resumen/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_contabilidad_resumen_requires_authentication(self):
        """GET /api/v1/core/contabilidad/resumen/ sin autenticación → 401/403."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/core/contabilidad/resumen/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_facturas_resumen_no_membership_403(self):
        """GET /api/v1/core/facturas/resumen/ sin membresía → 403."""
        from django.contrib.auth import get_user_model
        from django_tenants.utils import schema_context
        from apps.public.tenants.models import TenantMembership
        
        User = get_user_model()
        
        # Crear usuario sin membresía
        with schema_context('public'):
            user_no_membership = User.objects.create_user(
                username='no_member',
                email='no_member@example.com',
                password='testpass123',
            )
        
        # Autenticar con usuario sin membresía
        client = APIClient(HTTP_HOST=self.domain.domain)
        client.force_authenticate(user=user_no_membership)
        
        response = client.get('/api/v1/core/facturas/resumen/')
        # Debe retornar 403 (sin membresía) o 401 (si el middleware rechaza antes)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_contabilidad_resumen_no_membership_403(self):
        """GET /api/v1/core/contabilidad/resumen/ sin membresía → 403."""
        from django.contrib.auth import get_user_model
        from django_tenants.utils import schema_context
        
        User = get_user_model()
        
        # Crear usuario sin membresía
        with schema_context('public'):
            user_no_membership = User.objects.create_user(
                username='no_member2',
                email='no_member2@example.com',
                password='testpass123',
            )
        
        # Autenticar con usuario sin membresía
        client = APIClient(HTTP_HOST=self.domain.domain)
        client.force_authenticate(user=user_no_membership)
        
        response = client.get('/api/v1/core/contabilidad/resumen/')
        # Debe retornar 403 (sin membresía) o 401 (si el middleware rechaza antes)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
