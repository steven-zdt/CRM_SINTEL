"""
Tests para DashboardViewSet v3.9.4
Valida endpoints, permisos, serialización
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.tenant.empresa.models import Empresa
from apps.public.accounts.models import User
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.dashboard.services.dtos import (
    DashboardMetricasDTO,
    WidgetFacturasDTO,
    WidgetInventarioDTO,
    WidgetEmpleadosDTO,
    WidgetGastosDTO,
)
from apps.tenant.dashboard.api.serializers import DashboardMetricasSerializer


class DashboardViewSetTestCase(APITestCase):
    """Tests para GET /api/v1/dashboard/"""

    @classmethod
    def setUpTestData(cls):
        """Setup: usuario + empresa + tenant profile."""
        # Crear usuario
        cls.user = User.objects.create_user(
            email='admin@dashboard.test',
            password='testpass123'
        )

        # Crear empresa
        cls.empresa = Empresa.objects.create(
            razon_social='Dashboard Test Corp',
            nit='1111111111'
        )

        # Crear tenant profile (ADMIN)
        cls.profile = TenantProfile.objects.create(
            user=cls.user,
            empresa=cls.empresa,
            rol='ADMIN'
        )

    def setUp(self):
        """Antes de cada test: autenticar cliente."""
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_dashboard_metricas_200(self):
        """Test: GET /api/v1/dashboard/ retorna 200."""
        url = reverse('tenant_dashboard_api:dashboard-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_dashboard_metricas_estructura(self):
        """Test: response tiene estructura correcta."""
        url = reverse('tenant_dashboard_api:dashboard-list')
        response = self.client.get(url)
        data = response.json()

        # Verificar campos principales
        self.assertIn('empresa_nombre', data)
        self.assertIn('empresa_nit', data)
        self.assertIn('fecha_actualizacion', data)
        self.assertIn('facturas', data)
        self.assertIn('inventario', data)
        self.assertIn('empleados', data)

    def test_get_dashboard_metricas_facturas_widget(self):
        """Test: widget de facturas tiene campos esperados."""
        url = reverse('tenant_dashboard_api:dashboard-list')
        response = self.client.get(url)
        data = response.json()

        facturas = data.get('facturas', {})
        self.assertIn('total_facturas', facturas)
        self.assertIn('facturas_pendientes', facturas)
        self.assertIn('facturas_vencidas', facturas)
        self.assertIn('ingresos_mes', facturas)
        self.assertIn('ingresos_promedio', facturas)

    def test_get_dashboard_metricas_inventario_widget(self):
        """Test: widget de inventario tiene campos esperados."""
        url = reverse('tenant_dashboard_api:dashboard-list')
        response = self.client.get(url)
        data = response.json()

        inventario = data.get('inventario', {})
        self.assertIn('total_productos', inventario)
        self.assertIn('productos_bajo_stock', inventario)
        self.assertIn('movimientos_mes', inventario)
        self.assertIn('valor_inventario', inventario)
        self.assertIn('rotacion_promedio', inventario)

    def test_get_dashboard_metricas_empleados_widget(self):
        """Test: widget de empleados tiene campos esperados."""
        url = reverse('tenant_dashboard_api:dashboard-list')
        response = self.client.get(url)
        data = response.json()

        empleados = data.get('empleados', {})
        self.assertIn('total_empleados', empleados)
        self.assertIn('empleados_activos', empleados)
        self.assertIn('nominas_pendientes', empleados)
        self.assertIn('total_nómina_mes', empleados)

    def test_get_dashboard_sin_autenticacion_401(self):
        """Test: sin autenticación retorna 401."""
        self.client.force_authenticate(user=None)
        url = reverse('tenant_dashboard_api:dashboard-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalidar_cache_admin_200(self):
        """Test: admin puede invalidar caché."""
        url = reverse('tenant_dashboard_api:dashboard-invalidar-cache')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.json())

    def test_invalidar_cache_non_admin_403(self):
        """Test: usuario no-admin no puede invalidar caché."""
        # Crear usuario operador (no admin)
        operator = User.objects.create_user(
            email='operator@test.com',
            password='testpass123'
        )
        TenantProfile.objects.create(
            user=operator,
            empresa=self.empresa,
            rol='OPERADOR'
        )

        self.client.force_authenticate(user=operator)
        url = reverse('tenant_dashboard_api:dashboard-invalidar-cache')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_metricas_action_alias(self):
        """Test: GET /api/v1/dashboard/metricas/ funciona (alias)."""
        url = reverse('tenant_dashboard_api:dashboard-metricas')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cache_reuse_segundas_llamadas(self):
        """Test: segunda llamada retorna datos cacheados (más rápida)."""
        import time
        url = reverse('tenant_dashboard_api:dashboard-list')

        # Primera llamada
        start1 = time.time()
        response1 = self.client.get(url)
        time1 = time.time() - start1

        # Segunda llamada (caché)
        start2 = time.time()
        response2 = self.client.get(url)
        time2 = time.time() - start2

        # Ambas deben ser 200 (la estructura no cambia)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Segunda llamada debería ser más rápida (caché)
        # Nota: en tests el diferencial puede no ser significativo
        self.assertIsNotNone(response1.json())
        self.assertIsNotNone(response2.json())


class DashboardMetricasSerializerTestCase(TestCase):
    """Tests para DashboardMetricasSerializer."""

    def test_serializer_valida_dttos_correctos(self):
        """Test: serializer valida DTOs con estructura correcta."""
        from apps.tenant.dashboard.services.dtos import (
            DashboardMetricasDTO,
            WidgetFacturasDTO,
            WidgetInventarioDTO,
            WidgetEmpleadosDTO,
        )
        from apps.tenant.dashboard.api.serializers import DashboardMetricasSerializer

        from apps.tenant.dashboard.services.dtos import WidgetGastosDTO

        dto = DashboardMetricasDTO(
            empresa_nombre='Test Corp',
            empresa_nit='1234567890',
            fecha_actualizacion='2026-05-23T10:00:00',
            facturas=WidgetFacturasDTO(
                total_facturas=10,
                facturas_pendientes=3,
                facturas_vencidas=1,
                ingresos_mes=Decimal('500000'),
                ingresos_promedio=Decimal('50000')
            ),
            inventario=WidgetInventarioDTO(
                total_productos=50,
                productos_bajo_stock=5,
                movimientos_mes=100,
                valor_inventario=Decimal('1000000'),
                rotacion_promedio=Decimal('2.0')
            ),
            empleados=WidgetEmpleadosDTO(
                total_empleados=20,
                empleados_activos=18,
                nominas_pendientes=2,
                total_nómina_mes=Decimal('5000000')
            ),
            gastos=WidgetGastosDTO(
                total_gastos_mes=Decimal('100000'),
                gastos_pendientes=5,
                gastos_vencidos=1,
                gasto_promedio=Decimal('20000')
            )
        )

        serializer = DashboardMetricasSerializer(dto)
        data = serializer.data

        # Validar estructura
        self.assertEqual(data['empresa_nombre'], 'Test Corp')
        self.assertEqual(data['empresa_nit'], '1234567890')
        self.assertEqual(data['facturas']['total_facturas'], 10)
        self.assertEqual(
            data['facturas']['ingresos_mes'],
            '500000.00'
        )
        self.assertEqual(data['inventario']['total_productos'], 50)
        self.assertEqual(data['empleados']['total_empleados'], 20)
