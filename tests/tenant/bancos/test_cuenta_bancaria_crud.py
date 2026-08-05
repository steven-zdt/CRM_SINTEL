import pytest
from django.urls import reverse
from rest_framework import status

from apps.tenant.bancos.models import CuentaBancaria
from apps.tenant.bancos.services.crud_service import CuentaBancariaCRUDService
from apps.tenant.bancos.services.selectors import CuentaBancariaSelector
from tests.tenant.base_test import SintelTenantTestCase


class TestCuentaBancariaCRUD(SintelTenantTestCase):
    """
    Integration tests for CuentaBancaria CRUD operations.
    """

    def setUp(self):
        super().setUp()
        # Create a default Empresa since the viewset / mixins require it.
        from apps.tenant.empresa.models import Empresa

        self.empresa = Empresa.objects.create(
            razon_social="Test Empresa SINTEL",
            nit="900000111",
            dv="7",
            direccion="Calle Test 123",
            telefono="1234567",
            email_contacto="contacto@test.com",
            regimen_tributario="Responsable de IVA",
            moneda="COP",
        )
        # Link user profile to this company
        from apps.tenant.perfil.models import TenantProfile

        self.profile = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa,
            rol="ADMIN",
        )

    def test_create_cuenta_via_service(self):
        """Test: Create a CuentaBancaria using the service directly."""
        data = {
            "nombre": "Cuenta Principal",
            "banco": "BANCOLOMBIA",
            "tipo": "AHORROS",
            "numero": "123456789",
        }
        cuenta = CuentaBancariaCRUDService.crear_cuenta(data, self.empresa)
        self.assertEqual(cuenta.nombre, "Cuenta Principal")
        self.assertEqual(cuenta.numero, "123456789")
        self.assertEqual(cuenta.empresa, self.empresa)

        # Check duplicate constraint via service
        with self.assertRaises(Exception):
            CuentaBancariaCRUDService.crear_cuenta(data, self.empresa)

    def test_edit_cuenta_via_service(self):
        """Test: Edit an existing CuentaBancaria using the service."""
        data = {
            "nombre": "Cuenta Original",
            "banco": "BBVA",
            "tipo": "CORRIENTE",
            "numero": "987654321",
        }
        cuenta = CuentaBancariaCRUDService.crear_cuenta(data, self.empresa)

        edit_data = {"nombre": "Cuenta Modificada"}
        updated_cuenta = CuentaBancariaCRUDService.editar_cuenta(cuenta, edit_data)
        self.assertEqual(updated_cuenta.nombre, "Cuenta Modificada")

    def test_delete_cuenta_via_service(self):
        """Test: Delete a CuentaBancaria using the service."""
        data = {
            "nombre": "Cuenta Temporal",
            "banco": "DAVIVIENDA",
            "tipo": "AHORROS",
            "numero": "555555",
        }
        cuenta = CuentaBancariaCRUDService.crear_cuenta(data, self.empresa)
        CuentaBancariaCRUDService.eliminar_cuenta(cuenta)
        self.assertFalse(CuentaBancaria.objects.filter(id=cuenta.id).exists())

    def test_cuenta_api_flow(self):
        """Test: End-to-end REST API CRUD flow for CuentaBancaria."""
        list_url = reverse("bancos-cuentas-list")

        # 1. CREATE
        create_data = {
            "nombre": "Cuenta API",
            "banco": "BBVA",
            "tipo": "AHORROS",
            "numero": "999888777",
        }
        response = self.api_client.post(list_url, create_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        res_data = response.json()
        self.assertIn("uuid", res_data)
        uuid_str = res_data["uuid"]

        # 2. DETAIL / RETRIEVE
        detail_url = reverse("bancos-cuentas-detail", kwargs={"uuid": uuid_str})
        response = self.api_client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["numero"], "999888777")

        # 3. UPDATE (PUT)
        update_data = {
            "nombre": "Cuenta API Modificada",
            "banco": "BBVA",
            "tipo": "CORRIENTE",
            "numero": "999888777",
        }
        response = self.api_client.put(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["nombre"], "Cuenta API Modificada")

        # 4. DELETE
        response = self.api_client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CuentaBancaria.objects.filter(uuid=uuid_str).exists())
