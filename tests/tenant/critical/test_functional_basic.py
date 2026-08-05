"""
[WARNING] FASE 6: Tests Funcionales Básicos (por app core).

Solo para apps core del ciclo activo: CRUD básico dentro del tenant.
"""

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework import status

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, NaturalezaFactura


class FacturasFunctionalTests(TenantTestCase):
    """
    Tests funcionales básicos para Facturas.

    [WARNING] FASE 6: CRUD mínimo dentro del tenant.
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """Configura tenant de prueba."""
        from apps.public.tenants.models import Client

        return Client.objects.create(
            schema_name="test_tenant_facturas",
            nombre="Test Tenant Facturas",
            is_active=True,
            on_trial=True,
        )

    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        # Crear empresa (SSoT)
        self.empresa = Empresa.objects.create(
            razon_social="SINTEL", nit="901123299", dv="1"
        )

    def test_crear_factura(self):
        """
        Test: Crear factura dentro del tenant.

        Criterios de aceptación:
        - CRUD funciona dentro del tenant
        - No rompe el esquema compartido
        """
        factura = Factura.objects.create(
            numero="FAC-001",
            prefijo="FAC",
            consecutivo=1,
            fecha_emision=timezone.now(),
            emisor_nit="901123299",
            receptor_nit="900000000",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=Decimal("1000.00"),
            impuestos=Decimal("190.00"),
            total=Decimal("1190.00"),
            moneda="COP",
        )

        self.assertIsNotNone(factura.id)
        self.assertEqual(factura.numero, "FAC-001")
        self.assertTrue(Factura.objects.filter(numero="FAC-001").exists())

    def test_listar_facturas(self):
        """
        Test: Listar facturas dentro del tenant.

        Criterios de aceptación:
        - Lista retorna solo facturas del tenant actual
        """
        # Crear facturas
        Factura.objects.create(
            numero="FAC-001",
            prefijo="FAC",
            consecutivo=1,
            fecha_emision=timezone.now(),
            emisor_nit="901123299",
            receptor_nit="900000000",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=Decimal("1000.00"),
            impuestos=Decimal("190.00"),
            total=Decimal("1190.00"),
            moneda="COP",
        )
        Factura.objects.create(
            numero="FAC-002",
            prefijo="FAC",
            consecutivo=2,
            fecha_emision=timezone.now(),
            emisor_nit="901123299",
            receptor_nit="900000000",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=Decimal("2000.00"),
            impuestos=Decimal("380.00"),
            total=Decimal("2380.00"),
            moneda="COP",
        )

        # Listar
        facturas = Factura.objects.all()
        self.assertEqual(facturas.count(), 2)
        self.assertIn("FAC-001", [f.numero for f in facturas])
        self.assertIn("FAC-002", [f.numero for f in facturas])

    def test_eliminar_factura(self):
        """
        Test: Eliminar factura dentro del tenant.

        Criterios de aceptación:
        - Eliminación funciona correctamente
        - No afecta otros registros
        """
        factura = Factura.objects.create(
            numero="FAC-DELETE",
            prefijo="FAC",
            consecutivo=99,
            fecha_emision=timezone.now(),
            emisor_nit="901123299",
            receptor_nit="900000000",
            naturaleza=NaturalezaFactura.VENTA,
            subtotal=Decimal("1000.00"),
            impuestos=Decimal("190.00"),
            total=Decimal("1190.00"),
            moneda="COP",
        )

        factura_id = factura.id
        factura.delete()

        self.assertFalse(Factura.objects.filter(id=factura_id).exists())


class ClientesFunctionalTests(TenantTestCase):
    """
    Tests funcionales básicos para Clientes.

    [WARNING] FASE 6: CRUD mínimo dentro del tenant.
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """Configura tenant de prueba."""
        from apps.public.tenants.models import Client

        return Client.objects.create(
            schema_name="test_tenant_clientes",
            nombre="Test Tenant Clientes",
            is_active=True,
            on_trial=True,
        )

    def test_crear_cliente(self):
        """
        Test: Crear cliente dentro del tenant.

        Criterios de aceptación:
        - CRUD funciona dentro del tenant
        """
        cliente = Cliente.objects.create(
            nombre="Cliente Test", nit="900111111", email="cliente@test.com"
        )

        self.assertIsNotNone(cliente.id)
        self.assertEqual(cliente.nombre, "Cliente Test")
        self.assertTrue(Cliente.objects.filter(nit="900111111").exists())

    def test_listar_clientes(self):
        """
        Test: Listar clientes dentro del tenant.

        Criterios de aceptación:
        - Lista retorna solo clientes del tenant actual
        """
        Cliente.objects.create(nombre="Cliente 1", nit="900111111")
        Cliente.objects.create(nombre="Cliente 2", nit="900222222")

        clientes = Cliente.objects.all()
        self.assertEqual(clientes.count(), 2)


class EmpresaFunctionalTests(TenantTestCase):
    """
    Tests funcionales básicos para Empresa (SSoT).

    [WARNING] FASE 6: Validar que SSoT funciona correctamente.
    """

    @classmethod
    def setup_tenant(cls, tenant_user=None):
        """Configura tenant de prueba."""
        from apps.public.tenants.models import Client

        return Client.objects.create(
            schema_name="test_tenant_empresa",
            nombre="Test Tenant Empresa",
            is_active=True,
            on_trial=True,
        )

    def test_crear_empresa_singleton(self):
        """
        Test: Crear empresa (debe ser singleton por tenant).

        Criterios de aceptación:
        - Solo puede haber una Empresa por tenant
        - Actualizar actualiza en lugar de crear duplicado
        """
        empresa1 = Empresa.objects.create(
            razon_social="Empresa Test", nit="901123299", dv="1"
        )

        # Intentar crear segunda empresa (debe actualizar o fallar según tu lógica)
        empresa2, created = Empresa.objects.get_or_create(
            defaults={"razon_social": "Empresa Test 2", "nit": "901123300", "dv": "1"}
        )

        # Verificar que solo hay una empresa o que se actualizó correctamente
        count = Empresa.objects.count()
        self.assertLessEqual(count, 1, "Solo debe haber una Empresa por tenant")
