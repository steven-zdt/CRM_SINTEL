"""
Tests de permisos CRUD para la app inventario.

[WARNING] v3.5: Verifica que ADMIN pueda realizar CRUD completo,
mientras que usuarios VISOR/OPERADOR sin rol ADMIN reciben 405 en mutaciones.

ARQUITECTURA DE PERMISOS SINTEL:
- IsTenantAdmin: Verifica TenantProfile.rol == 'ADMIN' (SSoT v2.61.8)
- En DEBUG: Los permisos tienen fallback True para facilitar desarrollo,
  PERO _check_enforced_mode verifica explicitamente IsTenantAdmin.
- Los tests deben crear TenantProfile en el esquema del tenant para
  que los usuarios tengan el rol correcto.

CORRECCIONES v3.5:
- Usuarios creados en esquema public (via schema_context)
- TenantProfile creado en esquema tenant para ADMIN
- Roles alineados con SINTEL: ADMIN/OPERADOR/VISOR (no STAFF/USER)
- lookup_field compatible con ViewSet (usa kwargs['pk'])
- MovimientoInventario: crear() via Service Layer (perform_create delega)
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.inventario.models import (
    ActivoFijo, CategoriaItem, MovimientoInventario, Producto
)
from apps.tenant.empresa.models import Empresa

User = get_user_model()


# ==============================================================================
# HELPER MIXIN: Crea usuarios con TenantProfile correctamente
# ==============================================================================
class InventarioPermissionsMixin:
    """
    Mixin para crear usuarios con roles correctos en el contexto multi-tenant.

    CRITICO: Los usuarios (User) viven en el esquema public.
    Los TenantProfile viven en el esquema del tenant.
    Esta diferencia de esquema requiere manejo explicito de schema_context.
    """

    def _create_user_in_public(self, username, email, password='testpass123'):
        """Crea un User en el esquema public."""
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=True,
            )
        return user

    def _create_tenant_profile(self, user, empresa, rol):
        """
        Crea un TenantProfile en el esquema del tenant activo.

        IMPORTANTE: Este metodo asume que la conexion ya esta en el
        esquema del tenant (lo maneja TenantTestCase automaticamente).
        """
        from apps.tenant.perfil.models import TenantProfile
        profile = TenantProfile.objects.create(
            user=user,
            empresa=empresa,
            rol=rol,
        )
        return profile

    def _make_client_for(self, user, domain):
        """Crea un APIClient autenticado para el usuario dado."""
        client = APIClient(HTTP_HOST=domain)
        client.force_authenticate(user=user)
        return client


# ==============================================================================
# TEST SUITE 1: CategoriaItem CRUD
# ==============================================================================
class TestCategoriaItemCRUD(InventarioPermissionsMixin, SintelTenantTestCase):
    """
    Tests CRUD para CategoriaItemViewSet.

    Verifica que:
    - ADMIN (TenantProfile.rol=ADMIN) puede crear, actualizar y eliminar.
    - OPERADOR/VISOR reciben 405 en operaciones de escritura.
    - Todos pueden leer (GET).
    """

    def setUp(self):
        """Configuracion inicial: empresa, usuarios con perfiles correctos."""
        super().setUp()

        # Crear empresa singleton (requerida para _get_empresa_id() en serializers)
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test Inventario",
            nit="900123456",
            direccion="Calle Test 123",
            telefono="1234567",
            singleton_key=1
        )

        # Crear usuarios en esquema public
        self.admin_user = self._create_user_in_public(
            username="admin_inv@test.com",
            email="admin_inv@test.com"
        )
        self.operador_user = self._create_user_in_public(
            username="operador_inv@test.com",
            email="operador_inv@test.com"
        )
        self.visor_user = self._create_user_in_public(
            username="visor_inv@test.com",
            email="visor_inv@test.com"
        )

        # Crear TenantProfile en el esquema del tenant (conexion ya en tenant)
        self._create_tenant_profile(self.admin_user, self.empresa, 'ADMIN')
        self._create_tenant_profile(self.operador_user, self.empresa, 'OPERADOR')
        self._create_tenant_profile(self.visor_user, self.empresa, 'VISOR')

        # Crear membresías en esquema public
        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant, user=self.admin_user, rol='ADMIN', is_active=True
            )
            TenantMembership.objects.create(
                client=self.tenant, user=self.operador_user, rol='OPERADOR', is_active=True
            )
            TenantMembership.objects.create(
                client=self.tenant, user=self.visor_user, rol='VISOR', is_active=True
            )

        # Clientes API para cada rol
        domain = self.domain.domain
        self.admin_client = self._make_client_for(self.admin_user, domain)
        self.operador_client = self._make_client_for(self.operador_user, domain)
        self.visor_client = self._make_client_for(self.visor_user, domain)

    # --- Creacion ---

    def test_admin_can_create(self):
        """ADMIN puede crear categorias (201 Created)."""
        url = reverse('inv-categorias-list')
        response = self.admin_client.post(url, {
            'nombre': 'Categoria ADMIN Test',
            'aplicacion': 'PRODUCTO',
            'activo': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         f"Esperado 201, obtenido {response.status_code}: {response.data}")
        self.assertEqual(response.data.get('nombre'), 'Categoria ADMIN Test')

    def test_operador_cannot_create(self):
        """OPERADOR NO puede crear categorias (405)."""
        url = reverse('inv-categorias-list')
        response = self.operador_client.post(url, {
            'nombre': 'Categoria OPERADOR Test',
            'aplicacion': 'PRODUCTO',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         f"Esperado 405, obtenido {response.status_code}: {response.data}")

    def test_visor_cannot_create(self):
        """VISOR NO puede crear categorias (405)."""
        url = reverse('inv-categorias-list')
        response = self.visor_client.post(url, {
            'nombre': 'Categoria VISOR Test',
            'aplicacion': 'PRODUCTO',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         f"Esperado 405, obtenido {response.status_code}: {response.data}")

    # --- Actualizacion ---

    def test_admin_can_update(self):
        """ADMIN puede actualizar categorias (200 OK)."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria Para Actualizar',
            aplicacion='PRODUCTO'
        )
        url = reverse('inv-categorias-detail', kwargs={'uuid': item.uuid})
        response = self.admin_client.patch(url, {
            'nombre': 'Categoria Actualizada'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         f"Esperado 200, obtenido {response.status_code}: {response.data}")
        self.assertEqual(response.data.get('nombre'), 'Categoria Actualizada')

    def test_visor_cannot_update(self):
        """VISOR NO puede actualizar categorias (405)."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria Protegida Update',
            aplicacion='PRODUCTO'
        )
        url = reverse('inv-categorias-detail', kwargs={'uuid': item.uuid})
        response = self.visor_client.patch(url, {'nombre': 'Modificada'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         f"Esperado 405, obtenido {response.status_code}: {response.data}")

    # --- Eliminacion ---

    def test_admin_can_delete(self):
        """ADMIN puede eliminar categorias (204 No Content)."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria A Eliminar',
            aplicacion='PRODUCTO'
        )
        url = reverse('inv-categorias-detail', kwargs={'uuid': item.uuid})
        response = self.admin_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT,
                         f"Esperado 204, obtenido {response.status_code}: {response.data}")

    def test_visor_cannot_delete(self):
        """VISOR NO puede eliminar categorias (405)."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre='Categoria Protegida Delete',
            aplicacion='PRODUCTO'
        )
        url = reverse('inv-categorias-detail', kwargs={'uuid': item.uuid})
        response = self.visor_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         f"Esperado 405, obtenido {response.status_code}")
        # Verificar que no fue eliminada
        self.assertTrue(CategoriaItem.objects.filter(uuid=item.uuid).exists())

    # --- Lectura ---

    def test_all_roles_can_read_list(self):
        """Todos los roles pueden leer el listado de categorias (200)."""
        CategoriaItem.objects.create(
            empresa=self.empresa, nombre='Cat Lectura', aplicacion='PRODUCTO'
        )
        url = reverse('inv-categorias-list')
        for label, client in [
            ('ADMIN', self.admin_client),
            ('OPERADOR', self.operador_client),
            ('VISOR', self.visor_client),
        ]:
            with self.subTest(rol=label):
                response = client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                                 f"[{label}] Esperado 200, obtenido {response.status_code}")

    def test_all_roles_can_read_detail(self):
        """Todos los roles pueden leer el detalle de una categoria (200)."""
        item = CategoriaItem.objects.create(
            empresa=self.empresa, nombre='Cat Detalle', aplicacion='PRODUCTO'
        )
        url = reverse('inv-categorias-detail', kwargs={'uuid': item.uuid})
        for label, client in [
            ('ADMIN', self.admin_client),
            ('OPERADOR', self.operador_client),
            ('VISOR', self.visor_client),
        ]:
            with self.subTest(rol=label):
                response = client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                                 f"[{label}] Esperado 200, obtenido {response.status_code}")


# ==============================================================================
# TEST SUITE 2: ActivoFijo CRUD
# ==============================================================================
class TestActivoFijoCRUD(InventarioPermissionsMixin, SintelTenantTestCase):
    """
    Tests CRUD para ActivoFijoViewSet.

    Verificacion de permisos por rol para activos fijos.
    El modelo solo requiere: codigo, nombre, costo_adquisicion (con defaults).
    """

    def setUp(self):
        """Configuracion inicial."""
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test Activos",
            nit="900123457",
            direccion="Calle Test 456",
            telefono="7654321",
            singleton_key=1
        )

        self.admin_user = self._create_user_in_public(
            username="admin_activos@test.com",
            email="admin_activos@test.com"
        )
        self.visor_user = self._create_user_in_public(
            username="visor_activos@test.com",
            email="visor_activos@test.com"
        )

        self._create_tenant_profile(self.admin_user, self.empresa, 'ADMIN')
        self._create_tenant_profile(self.visor_user, self.empresa, 'VISOR')

        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant, user=self.admin_user, rol='ADMIN', is_active=True
            )
            TenantMembership.objects.create(
                client=self.tenant, user=self.visor_user, rol='VISOR', is_active=True
            )

        domain = self.domain.domain
        self.admin_client = self._make_client_for(self.admin_user, domain)
        self.visor_client = self._make_client_for(self.visor_user, domain)

    def test_admin_can_create_activo(self):
        """ADMIN puede crear activos fijos (201 Created)."""
        url = reverse('inv-activos-list')
        response = self.admin_client.post(url, {
            'codigo': 'ACT-001',
            'nombre': 'Laptop Dell Latitude',
            'costo_adquisicion': '3500000.00',
            'estado': 'ACTIVO',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         f"Esperado 201, obtenido {response.status_code}: {response.data}")
        self.assertEqual(response.data.get('codigo'), 'ACT-001')

    def test_visor_cannot_create_activo(self):
        """VISOR NO puede crear activos fijos (405)."""
        url = reverse('inv-activos-list')
        response = self.visor_client.post(url, {
            'codigo': 'ACT-002',
            'nombre': 'Laptop HP',
            'costo_adquisicion': '2500000.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         f"Esperado 405, obtenido {response.status_code}: {response.data}")

    def test_all_roles_can_read_activos(self):
        """Todos los roles pueden listar activos fijos (200)."""
        ActivoFijo.objects.create(
            empresa=self.empresa,
            codigo='ACT-READ-001',
            nombre='Activo Lectura',
            costo_adquisicion=Decimal('1000.00')
        )
        url = reverse('inv-activos-list')
        for label, client in [('ADMIN', self.admin_client), ('VISOR', self.visor_client)]:
            with self.subTest(rol=label):
                response = client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                                 f"[{label}] Esperado 200, obtenido {response.status_code}")


# ==============================================================================
# TEST SUITE 3: MovimientoInventario CRUD
# ==============================================================================
class TestMovimientoInventarioCRUD(InventarioPermissionsMixin, SintelTenantTestCase):
    """
    Tests para MovimientoInventarioViewSet.

    ARQUITECTURA KARDEX:
    - Los movimientos SOLO se crean (POST) y leen (GET).
    - NO se permiten ediciones ni eliminaciones (inmutabilidad del Kardex).
    - Solo ADMIN puede crear movimientos.

    NOTA: El endpoint POST /api/v1/inventario/movimientos/ delega a
    service_movimiento_perform_create() en el Service Layer.
    """

    def setUp(self):
        """Configuracion inicial con producto para movimientos."""
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Test Movimientos",
            nit="900123458",
            direccion="Calle Test 789",
            telefono="1122334",
            singleton_key=1
        )

        self.admin_user = self._create_user_in_public(
            username="admin_movs@test.com",
            email="admin_movs@test.com"
        )
        self.visor_user = self._create_user_in_public(
            username="visor_movs@test.com",
            email="visor_movs@test.com"
        )

        self._create_tenant_profile(self.admin_user, self.empresa, 'ADMIN')
        self._create_tenant_profile(self.visor_user, self.empresa, 'VISOR')

        public_schema = get_public_schema_name()
        with schema_context(public_schema):
            from apps.public.tenants.models import TenantMembership
            TenantMembership.objects.create(
                client=self.tenant, user=self.admin_user, rol='ADMIN', is_active=True
            )
            TenantMembership.objects.create(
                client=self.tenant, user=self.visor_user, rol='VISOR', is_active=True
            )

        # Crear categoria y producto de prueba
        self.categoria = CategoriaItem.objects.create(
            empresa=self.empresa,
            nombre="CAT-MOVIMIENTO",
            aplicacion="PRODUCTO"
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            categoria=self.categoria,
            codigo="PROD-MOV-TEST",
            nombre="Producto Movimiento Test",
            unidad="UND",
            precio_venta=Decimal("1000.00")
        )

        domain = self.domain.domain
        self.admin_client = self._make_client_for(self.admin_user, domain)
        self.visor_client = self._make_client_for(self.visor_user, domain)

    def test_admin_can_create_movimiento(self):
        """ADMIN puede crear movimientos de inventario (201 Created)."""
        url = reverse('inv-movimientos-list')
        response = self.admin_client.post(url, {
            'producto': self.producto.pk,
            'tipo': 'ENTRADA_AJUSTE',
            'cantidad': '10.000',
            'costo_unitario': '1000.00',
            'origen_referencia': 'REF-TEST-001'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         f"Esperado 201, obtenido {response.status_code}: {response.data}")
        self.assertEqual(response.data.get('tipo'), 'ENTRADA_AJUSTE')

    def test_visor_cannot_create_movimiento(self):
        """VISOR NO puede crear movimientos de inventario (405)."""
        url = reverse('inv-movimientos-list')
        response = self.visor_client.post(url, {
            'producto': self.producto.pk,
            'tipo': 'ENTRADA_AJUSTE',
            'cantidad': '5.000',
            'costo_unitario': '1000.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                         f"Esperado 405, obtenido {response.status_code}: {response.data}")

    def test_all_roles_can_read_movimientos(self):
        """Todos los roles pueden listar movimientos (200)."""
        MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=self.producto,
            tipo='ENTRADA_AJUSTE',
            cantidad=Decimal('10.000'),
            costo_unitario=Decimal('1000.00'),
            origen_referencia='REF-READ-001'
        )
        url = reverse('inv-movimientos-list')
        for label, client in [('ADMIN', self.admin_client), ('VISOR', self.visor_client)]:
            with self.subTest(rol=label):
                response = client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                                 f"[{label}] Esperado 200, obtenido {response.status_code}")

    def test_movimiento_detail_readable(self):
        """El detalle de un movimiento es legible por cualquier rol."""
        movimiento = MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=self.producto,
            tipo='ENTRADA_AJUSTE',
            cantidad=Decimal('5.000'),
            costo_unitario=Decimal('500.00'),
            origen_referencia='REF-DETAIL-001'
        )
        url = reverse('inv-movimientos-detail', kwargs={'uuid': movimiento.uuid})
        for label, client in [('ADMIN', self.admin_client), ('VISOR', self.visor_client)]:
            with self.subTest(rol=label):
                response = client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                                 f"[{label}] Esperado 200, obtenido {response.status_code}")
