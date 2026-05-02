"""
Tests de permisos CRUD para la app inventario.

[WARNING] v2.40: Verifica que ADMIN/STAFF pueden realizar CRUD completo,
mientras que usuarios no-staff solo pueden leer.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context, get_public_schema_name
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.inventario.models import CategoriaItem, ActivoFijo, MovimientoInventario
from apps.tenant.empresa.models import Empresa
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class TestCategoriaItemCRUD(SintelTenantTestCase):
    """Tests CRUD para CategoriaItemViewSet."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        # Crear empresa para que los modelos puedan usar FK a Empresa
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456",
            direccion="Calle Test 123",
            telefono="1234567",
            singleton_key=1
        )
        # Crear usuarios con diferentes roles
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staff@test.com",
            email="staff@test.com",
            password="testpass123"
        )
        self.regular_user = User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="testpass123"
        )
        # Crear membresías en el tenant
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            tenant = self.tenant  # SintelTenantTestCase proporciona self.tenant
            TenantMembership.objects.create(
                client=tenant,
                user=self.admin_user,
                rol="ADMIN",
                is_active=True
            )
            TenantMembership.objects.create(
                client=tenant,
                user=self.staff_user,
                rol="STAFF",
                is_active=True
            )
            TenantMembership.objects.create(
                client=tenant,
                user=self.regular_user,
                rol="USER",
                is_active=True
            )
    
    def test_admin_can_create(self):
        """ADMIN puede crear categorias."""
        self.api_client.force_authenticate(user=self.admin_user)
        url = reverse('inv-categorias-list')  # Cambio de inv-catalogo-list a inv-categorias-list si aplica
        
        response = self.api_client.post(url, {
            'empresa': self.empresa.id,
            'nombre': 'Categoria Test',
            'aplicacion': 'PRODUCTO',
            'activo': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nombre'], 'Categoria Test')
    
    def test_staff_can_create(self):
        """STAFF puede crear categorias."""
        self.api_client.force_authenticate(user=self.staff_user)
        url = reverse('inv-categorias-list')
        
        response = self.api_client.post(url, {
            'empresa': self.empresa.id,
            'nombre': 'Categoria Test 2',
            'aplicacion': 'PRODUCTO',
            'activo': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_regular_user_cannot_create(self):
        """Usuario regular NO puede crear categorias."""
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-categorias-list')
        
        response = self.api_client.post(url, {
            'empresa': self.empresa.id,
            'nombre': 'Categoria Test 3',
            'aplicacion': 'PRODUCTO'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_admin_can_update(self):
        """ADMIN puede actualizar categorias."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria Original',
            aplicacion='PRODUCTO'
        )
        self.api_client.force_authenticate(user=self.admin_user)
        url = reverse('inv-categorias-detail', kwargs={'pk': item.id})
        
        response = self.api_client.patch(url, {
            'nombre': 'Categoria Actualizada'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'Categoria Actualizada')
    
    def test_regular_user_cannot_update(self):
        """Usuario regular NO puede actualizar categorias."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria Original',
            aplicacion='PRODUCTO'
        )
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-categorias-detail', kwargs={'pk': item.id})
        
        response = self.api_client.patch(url, {
            'nombre': 'Categoria Modificada'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_admin_can_delete(self):
        """ADMIN puede eliminar categorias."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria a Eliminar',
            aplicacion='PRODUCTO'
        )
        self.api_client.force_authenticate(user=self.admin_user)
        url = reverse('inv-categorias-detail', kwargs={'pk': item.id})
        
        response = self.api_client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CategoriaItem.objects.filter(id=item.id).exists())
    
    def test_regular_user_cannot_delete(self):
        """Usuario regular NO puede eliminar categorias."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria Protegida',
            aplicacion='PRODUCTO'
        )
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-categorias-detail', kwargs={'pk': item.id})
        
        response = self.api_client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(CategoriaItem.objects.filter(id=item.id).exists())
    
    def test_regular_user_can_read(self):
        """Usuario regular PUEDE leer categorias."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria para Leer',
            aplicacion='PRODUCTO'
        )
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-categorias-detail', kwargs={'pk': item.id})
        
        response = self.api_client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], 'Categoria para Leer')


class TestActivoFijoCRUD(SintelTenantTestCase):
    """Tests CRUD para ActivoFijoViewSet."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456",
            direccion="Calle Test 123",
            telefono="1234567",
            singleton_key=1
        )
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="testpass123"
        )
        self.regular_user = User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="testpass123"
        )
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            tenant = self.tenant
            TenantMembership.objects.create(
                client=tenant,
                user=self.admin_user,
                rol="ADMIN",
                is_active=True
            )
            TenantMembership.objects.create(
                client=tenant,
                user=self.regular_user,
                rol="USER",
                is_active=True
            )
    
    def test_admin_can_create(self):
        """ADMIN puede crear activos fijos."""
        self.api_client.force_authenticate(user=self.admin_user)
        url = reverse('inv-activos-list')
        
        response = self.api_client.post(url, {
            'empresa': self.empresa.id,
            'codigo': 'ACT-001',
            'nombre': 'Activo Test',
            'costo_adquisicion': '50000.00',
            'activo': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['codigo'], 'ACT-001')
    
    def test_regular_user_cannot_create(self):
        """Usuario regular NO puede crear activos fijos."""
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-activos-list')
        
        response = self.api_client.post(url, {
            'empresa': self.empresa.id,
            'codigo': 'ACT-002',
            'nombre': 'Activo Test 2',
            'costo_adquisicion': '60000.00',
            'activo': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_regular_user_can_read(self):
        """Usuario regular PUEDE leer activos fijos."""
        activo = ActivoFijo.objects.create(
            empresa=self.empresa,
            codigo='ACT-READ',
            nombre='Activo para Leer',
            costo_adquisicion=Decimal('50000.00')
        )
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-activos-detail', kwargs={'pk': activo.id})
        
        response = self.api_client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['codigo'], 'ACT-READ')


class TestMovimientoInventarioCRUD(SintelTenantTestCase):
    """Tests CRUD para MovimientoInventarioViewSet."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test",
            nit="900123456",
            direccion="Calle Test 123",
            telefono="1234567",
            singleton_key=1
        )
        self.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="testpass123"
        )
        self.regular_user = User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="testpass123"
        )
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            tenant = self.tenant
            TenantMembership.objects.create(
                client=tenant,
                user=self.admin_user,
                rol="ADMIN",
                is_active=True
            )
            TenantMembership.objects.create(
                client=tenant,
                user=self.regular_user,
                rol="USER",
                is_active=True
            )
        
        # Crear categoria y producto para movimientos
        self.categoria = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre="CAT-TEST",
            aplicacion="PRODUCTO"
        )
        from apps.tenant.inventario.models import Producto
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            categoria=self.categoria,
            codigo="PROD-TEST",
            nombre="Producto Test",
            unidad="UND",
            precio_venta=Decimal("1000.00")
        )

    def test_admin_can_create(self):
        """ADMIN puede crear movimientos de inventario."""
        self.api_client.force_authenticate(user=self.admin_user)
        url = reverse('inv-movimientos-list')
        
        response = self.api_client.post(url, {
            'producto': self.producto.id,
            'tipo': 'ENTRADA_AJUSTE',
            'cantidad': '10.000',
            'costo_unitario': '1000.00',
            'origen_referencia': 'REF-001'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['tipo'], 'ENTRADA_AJUSTE')
    
    def test_regular_user_cannot_create(self):
        """Usuario regular NO puede crear movimientos de inventario."""
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-movimientos-list')
        
        response = self.api_client.post(url, {
            'producto': self.producto.id,
            'tipo': 'ENTRADA_AJUSTE',
            'cantidad': '5.000',
            'costo_unitario': '1000.00',
            'origen_referencia': 'REF-002'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_regular_user_can_read(self):
        """Usuario regular PUEDE leer movimientos de inventario."""
        movimiento = MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=self.producto,
            tipo='ENTRADA_AJUSTE',
            cantidad=Decimal('10.000'),
            costo_unitario=Decimal('1000.00'),
            origen_referencia='REF-READ'
        )
        self.api_client.force_authenticate(user=self.regular_user)
        url = reverse('inv-movimientos-detail', kwargs={'pk': movimiento.id})
        
        response = self.api_client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['tipo'], 'ENTRADA_AJUSTE')
