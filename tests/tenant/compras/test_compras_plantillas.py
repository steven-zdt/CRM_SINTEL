import datetime
from decimal import Decimal

from django.db import connection, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain, TenantMembership
from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService
from apps.tenant.compras.services.crud_service import PlantillaOrdenCompraCRUDService
from apps.tenant.compras.services.selectors import PlantillaOrdenCompraSelector
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


class TestComprasPlantillas(SintelTenantTestCase):
    """
    Test suite for the new template-based purchase order numbering system.
    """

    def setUp(self):
        super().setUp()
        # Create an Empresa in the tenant schema
        self.empresa = Empresa.objects.create(
            razon_social="Empresa Tenant A",
            nit="123456789",
            dv="1",
            moneda="COP",
            direccion="Calle 123",
        )
        # ADR-003: OrdenCompra ahora requiere sede explicita
        self.sede = Sede.objects.create(empresa=self.empresa, nombre="Principal")
        # Create a mock supplier
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            numero_documento="800900100",
            razon_social="Proveedor Colombia S.A.S.",
        )

        # Adjust user role to ADMIN to allow viewset operations
        membership = TenantMembership.objects.filter(
            client=self.tenant, user=self.user
        ).first()
        if membership:
            membership.rol = "ADMIN"
            membership.save()

    def test_crear_plantilla_crud(self):
        """Test creating a template via CRUD service."""
        data = {
            "nombre": "Plantilla General",
            "prefijo": "OC-GEN",
            "rango_desde": 100,
            "rango_hasta": 200,
            "consecutivo_actual": 100,
            "vigente": True,
        }
        plantilla = PlantillaOrdenCompraCRUDService.crear_plantilla(self.empresa, data)
        self.assertEqual(plantilla.nombre, "Plantilla General")
        self.assertEqual(plantilla.prefijo, "OC-GEN")
        self.assertEqual(plantilla.rango_desde, 100)
        self.assertEqual(plantilla.rango_hasta, 200)
        self.assertEqual(plantilla.consecutivo_actual, 100)
        self.assertTrue(plantilla.vigente)
        self.assertEqual(plantilla.empresa, self.empresa)

    def test_crear_orden_compra_con_plantilla(self):
        """Test creating an OrdenCompra that consumes a sequence from the template."""
        # 1. Create template
        plantilla_data = {
            "nombre": "Plantilla Nacional",
            "prefijo": "OCN",
            "rango_desde": 10,
            "rango_hasta": 15,
            "consecutivo_actual": 10,
            "vigente": True,
        }
        plantilla = PlantillaOrdenCompraCRUDService.crear_plantilla(
            self.empresa, plantilla_data
        )

        # 2. Create purchase order payload
        order_data = {
            "plantilla_uuid": str(plantilla.uuid),
            "proveedor_uuid": str(self.proveedor.uuid),
            "fecha": "2026-06-18",
            "fecha_entrega": "2026-06-25",
            "observaciones": "Test compra con plantilla",
            "items": [
                {
                    "descripcion": "Item 1",
                    "cantidad": 10,
                    "valor_unitario": 5000,
                }
            ],
        }

        # 3. Call Business Service to create the order
        success, orden, status_code = OrdenCompraBusinessService.crear_orden_compra(
            data=order_data, items_data=order_data["items"], empresa=self.empresa, sede=self.sede
        )
        self.assertTrue(success)

        # 4. Verify consecutivo and numero_documento
        self.assertEqual(orden.consecutivo, 10)
        self.assertEqual(orden.numero_documento, "OCN-10")
        self.assertEqual(orden.plantilla, plantilla)

        # 5. Verify template sequence incremented
        plantilla.refresh_from_db()
        self.assertEqual(plantilla.consecutivo_actual, 11)

    def test_plantilla_rango_excedido(self):
        """Test that validation fails when the template ranges are exhausted."""
        plantilla_data = {
            "nombre": "Plantilla Limitada",
            "prefijo": "OCL",
            "rango_desde": 10,
            "rango_hasta": 10,  # Only one available number (10)
            "consecutivo_actual": 10,
            "vigente": True,
        }
        plantilla = PlantillaOrdenCompraCRUDService.crear_plantilla(
            self.empresa, plantilla_data
        )

        order_data = {
            "plantilla_uuid": str(plantilla.uuid),
            "proveedor_uuid": str(self.proveedor.uuid),
            "fecha": "2026-06-18",
            "items": [
                {
                    "descripcion": "Item 1",
                    "cantidad": 1,
                    "valor_unitario": 1000,
                }
            ],
        }

        # First consumption (consecutivo = 10) succeeds
        success1, orden1, status_code1 = OrdenCompraBusinessService.crear_orden_compra(
            order_data, order_data["items"], self.empresa, self.sede
        )
        self.assertTrue(success1)
        plantilla.refresh_from_db()
        self.assertEqual(plantilla.consecutivo_actual, 11)

        # Second consumption fails because consecutivo_actual (11) > rango_hasta (10)
        success2, errors2, status_code2 = OrdenCompraBusinessService.crear_orden_compra(
            order_data, order_data["items"], self.empresa, self.sede
        )
        self.assertFalse(success2)
        self.assertEqual(status_code2, 400)
        self.assertIn("agotado su rango", str(errors2))

    def test_plantilla_no_vigente(self):
        """Test that non-active templates fail validation."""
        plantilla_data = {
            "nombre": "Plantilla Inactiva",
            "prefijo": "OCI",
            "rango_desde": 10,
            "rango_hasta": 20,
            "consecutivo_actual": 10,
            "vigente": False,
        }
        plantilla = PlantillaOrdenCompraCRUDService.crear_plantilla(
            self.empresa, plantilla_data
        )

        order_data = {
            "plantilla_uuid": str(plantilla.uuid),
            "proveedor_uuid": str(self.proveedor.uuid),
            "fecha": "2026-06-18",
            "items": [
                {
                    "descripcion": "Item 1",
                    "cantidad": 1,
                    "valor_unitario": 1000,
                }
            ],
        }

        success, errors, status_code = OrdenCompraBusinessService.crear_orden_compra(
            order_data, order_data["items"], self.empresa, self.sede
        )
        self.assertFalse(success)
        self.assertEqual(status_code, 400)
        self.assertIn("no esta marcada como vigente", str(errors))

    def test_tenant_isolation_dsv(self):
        """Test Double Semantic Verification: template from another tenant cannot be used."""
        # Create another tenant (public schema context)
        from django_tenants.utils import schema_context

        connection.set_schema_to_public()

        tenant_b = TenantClient.objects.create(
            schema_name="test_tenant_b", nombre="Test Tenant B", is_active=True
        )
        Domain.objects.create(
            domain="test_tenant_b.sintel.local", tenant=tenant_b, is_primary=True
        )

        # In tenant_b, create an Empresa and a Template
        with schema_context("test_tenant_b"):
            empresa_b = Empresa.objects.create(
                razon_social="Empresa Tenant B",
                nit="987654321",
                dv="2",
                moneda="COP",
                direccion="Calle 456",
            )
            plantilla_b_data = {
                "nombre": "Plantilla Tenant B",
                "prefijo": "OCB",
                "rango_desde": 1,
                "rango_hasta": 100,
                "consecutivo_actual": 1,
                "vigente": True,
            }
            plantilla_b = PlantillaOrdenCompraCRUDService.crear_plantilla(
                empresa_b, plantilla_b_data
            )
            plantilla_b_uuid = str(plantilla_b.uuid)

        # Restore connection schema to our current test tenant
        connection.set_schema(self.tenant.schema_name)

        # Try to use tenant_b's template in self.tenant
        order_data = {
            "plantilla_uuid": plantilla_b_uuid,  # UUID from other tenant
            "proveedor_uuid": str(self.proveedor.uuid),
            "fecha": "2026-06-18",
            "items": [
                {
                    "descripcion": "Item 1",
                    "cantidad": 1,
                    "valor_unitario": 1000,
                }
            ],
        }

        success, errors, status_code = OrdenCompraBusinessService.crear_orden_compra(
            order_data, order_data["items"], self.empresa, self.sede
        )
        self.assertFalse(success)
        self.assertEqual(status_code, 400)
        self.assertIn("no fue encontrada", str(errors))
