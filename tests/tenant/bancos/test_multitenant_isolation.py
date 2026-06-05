from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django_tenants.utils import schema_context
from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.bancos.services.selectors import CuentaBancariaSelector

class TestBancosMultitenantIsolation(SintelTenantTestCase):
    """
    Multitenant/Multi-company isolation tests for the Bancos module.
    """

    def setUp(self):
        super().setUp()

        # Company A (Self/Default)
        self.empresa_a = Empresa.objects.create(
            razon_social="Empresa A SAS",
            nit="900000001",
            dv="1",
            direccion="Calle A",
            telefono="1111111",
            email_contacto="contacto@empresa-a.com",
            regimen_tributario="Responsable de IVA",
            moneda="COP",
        )
        
        # Link user profile to Empresa A
        self.profile = TenantProfile.objects.create(
            user=self.user,
            empresa=self.empresa_a,
            rol="ADMIN",
        )

        self.cuenta_a = CuentaBancaria.objects.create(
            empresa=self.empresa_a,
            nombre="Cuenta Empresa A",
            banco="BANCOLOMBIA",
            tipo="AHORROS",
            numero="123456",
        )

        # Create Tenant B and its objects in its own schema
        from django.db import connection
        from apps.public.tenants.models import Client as TenantClient, Domain
        
        # Save current schema to restore it later
        original_schema = connection.schema_name
        connection.set_schema_to_public()
        
        self.tenant_b = TenantClient.objects.create(
            schema_name="test_tenant_b_bancos",
            nombre="Test Tenant B Bancos",
            is_active=True,
            on_trial=True
        )
        Domain.objects.create(domain="tenant-b-bancos.localhost", tenant=self.tenant_b, is_primary=True)
        
        # Restore the original schema context
        connection.set_schema(original_schema)

        with schema_context("test_tenant_b_bancos"):
            self.empresa_b = Empresa.objects.create(
                razon_social="Empresa B SAS",
                nit="900000002",
                dv="2",
                direccion="Calle B",
                telefono="2222222",
                email_contacto="contacto@empresa-b.com",
                regimen_tributario="Responsable de IVA",
                moneda="COP",
            )
            self.cuenta_b = CuentaBancaria.objects.create(
                empresa=self.empresa_b,
                nombre="Cuenta Empresa B",
                banco="DAVIVIENDA",
                tipo="CORRIENTE",
                numero="654321",
            )
            self.cuenta_b_uuid = self.cuenta_b.uuid

    def test_level_1_query_isolation(self):
        """
        Level 1: Query isolation.
        Assert that queries via the selector only return accounts for the authenticated company.
        """
        qs = CuentaBancariaSelector.get_list(self.empresa_a.id)
        self.assertIn(self.cuenta_a, qs)
        # Verify that the selector does not return Tenant B's accounts in the current context
        self.assertFalse(qs.filter(uuid=self.cuenta_b_uuid).exists())

    def test_level_2_write_isolation_idor_prevention(self):
        """
        Level 2: Write isolation (Anti-IDOR protection).
        Assert that creating a statement for Company A referencing Company B's account is rejected.
        """
        list_url = reverse("bancos-extractos-list")
        
        # Payload attempts to create an extracto for Company A but pointing to self.cuenta_b_uuid (Company B)
        data = {
            "cuenta": str(self.cuenta_b_uuid),
            "mes": 6,
            "anio": 2026,
            "saldo_inicial": "1000.00",
            "saldo_final": "2000.00",
        }
        
        response = self.api_client.post(list_url, data, format="json")
        
        # It must be rejected with 400 Bad Request, 404 Not Found, or 422 Unprocessable Entity
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]
        )

    def test_level_3_cross_talk_prevention(self):
        """
        Level 3: Cross-talk prevention.
        Assert that details of Company B's account cannot be retrieved or deleted by Company A's user.
        """
        detail_url = reverse("bancos-cuentas-detail", kwargs={"uuid": str(self.cuenta_b_uuid)})
        
        # GET request from Company A's authenticated client
        response = self.api_client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # DELETE request from Company A's authenticated client
        response = self.api_client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
