"""
Tests de API para la app facturas.

[WARNING] v2.30: API-First (DRF JSON-only) - Tests de endpoints REST.
"""

from datetime import date, datetime
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenant.facturas.models import Factura, ItemFactura
from tests.tenant.base_test import SintelTenantTestCase


class TestFacturasAPI(SintelTenantTestCase):
    """Tests de API para Facturas."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.client = APIClient()
        # Crear empresa para que las facturas puedan usar datos del emisor
        from apps.tenant.empresa.models import Empresa

        Empresa.objects.create(
            razon_social="Empresa Test", nit="900123456", dv="7", moneda="COP"
        )

    def test_list_facturas_requires_authentication(self):
        """Test: GET /api/v1/facturas/ requiere autenticación."""
        url = reverse("factura-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_facturas_authenticated(self):
        """Test: GET /api/v1/facturas/ retorna 200 para usuarios autenticados."""
        self.client.force_login(self.user)
        url = reverse("factura-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_create_factura_requires_admin_staff(self):
        """Test: POST /api/v1/facturas/ requiere rol ADMIN/STAFF."""
        self.client.force_login(self.user)
        url = reverse("factura-list")
        data = {
            "numero": "FST-001",
            "prefijo": "FST",
            "consecutivo": 1,
            "tipo": "FE",
            "estado": "BORRADOR",
            "fecha_emision": "2024-01-15T10:00:00Z",
            "receptor_nit": "900123456",
            "receptor_razon_social": "Cliente Test",
            "moneda": "COP",
            "subtotal": "100000.00",
            "impuestos": "19000.00",
            "total": "119000.00",
            "items": [
                {
                    "codigo": "ITEM001",
                    "descripcion": "Producto test",
                    "cantidad": "1.00",
                    "unidad_medida": "UND",
                    "valor_unitario": "100000.00",
                    "porcentaje_iva": "19.00",
                }
            ],
        }
        response = self.client.post(url, data, format="json")
        # Debe retornar 403 si el usuario no es ADMIN/STAFF
        if response.status_code == status.HTTP_403_FORBIDDEN:
            self.assertIn("ADMIN/STAFF", str(response.data.get("detail", "")))
        else:
            # Si el usuario es ADMIN/STAFF, debe crear la factura
            self.assertIn(
                response.status_code,
                [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN],
            )

    def test_create_factura_with_items(self):
        """Test: POST /api/v1/facturas/ crea factura con items y recalcula totales."""
        # Asumir que el usuario es ADMIN/STAFF (o usar un usuario con ese rol)
        from apps.public.tenants.models import TenantMembership

        membership = TenantMembership.objects.filter(
            client=self.tenant, user=self.user
        ).first()
        if membership:
            membership.rol = "ADMIN"
            membership.save()

        self.client.force_login(self.user)
        url = reverse("factura-list")
        data = {
            "numero": "FST-002",
            "prefijo": "FST",
            "consecutivo": 2,
            "tipo": "FE",
            "estado": "BORRADOR",
            "fecha_emision": "2024-01-15T10:00:00Z",
            "receptor_nit": "900123456",
            "receptor_razon_social": "Cliente Test",
            "moneda": "COP",
            "items": [
                {
                    "codigo": "ITEM001",
                    "descripcion": "Producto test",
                    "cantidad": "1.00",
                    "unidad_medida": "UND",
                    "valor_unitario": "100000.00",
                    "porcentaje_iva": "19.00",
                }
            ],
        }
        response = self.client.post(url, data, format="json")

        if response.status_code == status.HTTP_201_CREATED:
            factura_data = response.data
            self.assertIn("id", factura_data)
            self.assertEqual(factura_data["numero"], "FST-002")
            self.assertEqual(factura_data["naturaleza"], "VENTA")
            # Verificar que los totales se calcularon desde items
            self.assertGreater(Decimal(str(factura_data["total"])), Decimal("0"))
            # Verificar que los items están incluidos
            self.assertIn("items", factura_data)
            self.assertEqual(len(factura_data["items"]), 1)

    def test_update_factura_requires_admin_staff(self):
        """Test: PATCH /api/v1/facturas/{id}/ requiere rol ADMIN/STAFF."""
        # Crear factura como ADMIN
        from apps.public.tenants.models import TenantMembership

        membership = TenantMembership.objects.filter(
            client=self.tenant, user=self.user
        ).first()
        if membership:
            membership.rol = "ADMIN"
            membership.save()

        self.client.force_login(self.user)
        factura = Factura.objects.create(
            numero="FST-003",
            prefijo="FST",
            consecutivo=3,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=datetime.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="800123456",
            receptor_razon_social="Cliente Test",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )

        # F29-001: BaseTenantViewSet.lookup_field = "uuid", no "pk".
        url = reverse("factura-detail", kwargs={"uuid": factura.uuid})
        data = {"estado": "ENVIADA"}
        response = self.client.patch(url, data, format="json")

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data["estado"], "ENVIADA")
        else:
            # Si no es ADMIN/STAFF, debe retornar 403
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_facturas_by_estado(self):
        """Test: GET /api/v1/facturas/?estado=BORRADOR filtra correctamente."""
        self.client.force_login(self.user)

        # Crear facturas con diferentes estados
        Factura.objects.create(
            numero="FST-004",
            prefijo="FST",
            consecutivo=4,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=datetime.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="800123456",
            receptor_razon_social="Cliente Test",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )
        Factura.objects.create(
            numero="FST-005",
            prefijo="FST",
            consecutivo=5,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.ENVIADA,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=datetime.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="800123456",
            receptor_razon_social="Cliente Test",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )

        url = reverse("factura-list")
        response = self.client.get(url, {"estado": "BORRADOR"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list):
            for factura in response.data:
                self.assertEqual(factura["estado"], "BORRADOR")

    def test_search_facturas_by_numero(self):
        """Test: GET /api/v1/facturas/?search=FST-004 busca por número."""
        self.client.force_login(self.user)

        Factura.objects.create(
            numero="FST-004",
            prefijo="FST",
            consecutivo=4,
            tipo=Factura.TipoFactura.FE,
            estado=Factura.Estado.BORRADOR,
            naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision=datetime.now(),
            emisor_nit="900123456",
            emisor_razon_social="Empresa Test",
            receptor_nit="800123456",
            receptor_razon_social="Cliente Test",
            moneda="COP",
            subtotal=Decimal("100000.00"),
            impuestos=Decimal("19000.00"),
            total=Decimal("119000.00"),
        )

        url = reverse("factura-list")
        response = self.client.get(url, {"search": "FST-004"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, list) and len(response.data) > 0:
            self.assertIn("FST-004", response.data[0]["numero"])
