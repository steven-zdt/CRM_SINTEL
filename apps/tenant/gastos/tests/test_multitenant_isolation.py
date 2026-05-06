import datetime
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import tenant_context
from apps.tenant.gastos.models import Gasto, DocumentoSoporte, ResolucionDIAN
from apps.tenant.empresa.models import Empresa
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.tenant.perfil.models import TenantProfile
from django.contrib.auth import get_user_model

User = get_user_model()

class TestGastoMultitenantIsolation(TenantTestCase):
    """
    Test suite for verifying multi-tenant isolation in the Gastos module.
    Uses TenantTestCase to ensure proper schema isolation.
    """

    def setUp(self):
        super().setUp()
        # Tenant 1 (self.tenant) is created by TenantTestCase
        Domain.objects.get_or_create(tenant=self.tenant, domain=f"{self.tenant.schema_name}.localhost", is_primary=True)
        
        # Create Tenant 2 (must be done in public schema)
        from django_tenants.utils import schema_context
        with schema_context('public'):
            self.tenant2 = Client.objects.create(schema_name='tenant2', nombre='Tenant 2')
            Domain.objects.create(tenant=self.tenant2, domain='tenant2.localhost', is_primary=True)

        # Setup data for Tenant 1
        with tenant_context(self.tenant):
            self.empresa1, _ = Empresa.objects.get_or_create(
                nit="111", 
                defaults={'razon_social': "Empresa 1", 'direccion': "Calle 1 # 2-3"}
            )
            self.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="password")
            TenantMembership.objects.create(client=self.tenant, user=self.user1, is_active=True, rol="ADMIN")
            TenantProfile.objects.create(user=self.user1, empresa=self.empresa1, rol="ADMIN")
            
            self.resolucion1 = ResolucionDIAN.objects.create(
                empresa=self.empresa1,
                numero_resolucion="RES-1",
                prefijo="SI",
                rango_desde=1,
                rango_hasta=100,
                fecha_resolucion=datetime.date.today(),
                fecha_inicio=datetime.date.today(),
                fecha_fin=datetime.date.today() + datetime.timedelta(days=365),
                vigente=True
            )
            self.doc1 = DocumentoSoporte.objects.create(
                empresa=self.empresa1,
                resolucion_dian=self.resolucion1,
                prefijo="SI",
                consecutivo=1,
                fecha=datetime.date.today(),
                vendedor_nombre="Proveedor 1",
                vendedor_nit="999",
                subtotal=Decimal("100000.00"),
                total=Decimal("100000.00")
            )
            self.gasto1 = Gasto.objects.create(
                empresa=self.empresa1,
                documento_soporte=self.doc1,
                periodo="2026-05",
                descripcion="Gasto Tenant 1"
            )

        # Setup data for Tenant 2
        with tenant_context(self.tenant2):
            self.empresa2, _ = Empresa.objects.get_or_create(
                nit="222", 
                defaults={'razon_social': "Empresa 2", 'direccion': "Carrera 4 # 5-6"}
            )
            self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="password")
            TenantMembership.objects.create(client=self.tenant2, user=self.user2, is_active=True, rol="ADMIN")
            TenantProfile.objects.create(user=self.user2, empresa=self.empresa2, rol="ADMIN")
            
            self.resolucion2 = ResolucionDIAN.objects.create(
                empresa=self.empresa2,
                numero_resolucion="RES-2",
                prefijo="NO",
                rango_desde=1,
                rango_hasta=100,
                fecha_resolucion=datetime.date.today(),
                fecha_inicio=datetime.date.today(),
                fecha_fin=datetime.date.today() + datetime.timedelta(days=365),
                vigente=True
            )
            self.doc2 = DocumentoSoporte.objects.create(
                empresa=self.empresa2,
                resolucion_dian=self.resolucion2,
                prefijo="NO",
                consecutivo=1,
                fecha=datetime.date.today(),
                vendedor_nombre="Proveedor 2",
                vendedor_nit="888",
                subtotal=Decimal("200000.00"),
                total=Decimal("200000.00")
            )
            self.gasto2 = Gasto.objects.create(
                empresa=self.empresa2,
                documento_soporte=self.doc2,
                periodo="2026-05",
                descripcion="Gasto Tenant 2"
            )

    def test_user1_cannot_see_tenant2_gastos(self):
        """User 1 should only see Gastos from Tenant 1."""
        self.client.force_login(self.user1)
        url = '/api/v1/gastos/'
        
        # TestClient from TenantTestCase handles domain
        response = self.client.get(url, HTTP_HOST=f"{self.tenant.schema_name}.localhost")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        
        # Verify that we only see Gasto 1 by checking the description
        self.assertTrue(any(r['descripcion'] == "Gasto Tenant 1" for r in results))
        self.assertFalse(any(r['descripcion'] == "Gasto Tenant 2" for r in results))

    def test_user2_cannot_see_tenant1_gastos(self):
        """User 2 should only see Gastos from Tenant 2."""
        self.client.force_login(self.user2)
        url = '/api/v1/gastos/'
        
        response = self.client.get(url, HTTP_HOST=f"{self.tenant2.schema_name}.localhost")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        
        self.assertTrue(any(r['descripcion'] == "Gasto Tenant 2" for r in results))
        self.assertFalse(any(r['descripcion'] == "Gasto Tenant 1" for r in results))

    def test_user1_cannot_retrieve_tenant2_gasto_directly(self):
        """
        User 1 should not be able to retrieve data from Tenant 2.
        Using UUID guarantees isolation as UUIDs are unique.
        """
        self.client.force_login(self.user1)
        
        # We try to get Gasto 2's UUID but on Tenant 1's host
        url = f'/api/v1/gastos/{self.gasto2.uuid}/'
        response = self.client.get(url, HTTP_HOST=f"{self.tenant.schema_name}.localhost")
        
        # Should always be 404 because gasto2.uuid does not exist in tenant1 schema
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
