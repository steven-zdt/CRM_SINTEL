import pytest
from django_tenants.utils import schema_context
from rest_framework import status
from apps.tenant.gastos.models import ResolucionDIAN, DocumentoSoporte
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.empresa.models import Empresa
from apps.tenant.perfil.models import TenantProfile
from apps.public.tenants.models import TenantMembership
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestProveedorIntegration:
    """
    Test suite for verifying the integration of the Proveedor model into the Gastos module.
    Focuses on security (DSV), data integrity, and multi-tenant isolation.
    """

    def setup_method(self):
        self.username = "testuser"
        self.password = "password123"

    def _setup_tenant_data(self, tenant, username, email):
        """Helper to setup tenant, user, empresa, and basic data."""
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            user = User.objects.create_user(username=username, email=email, password=self.password)
            TenantProfile.objects.create(user=user, empresa=empresa, rol="ADMIN")
            
            with schema_context('public'):
                TenantMembership.objects.create(client=tenant, user=user, rol="ADMIN")
            
            resolucion = ResolucionDIAN.objects.create(
                empresa=empresa, numero_resolucion=f"RES_{username}", prefijo="G",
                rango_desde=1, rango_hasta=1000,
                fecha_resolucion="2026-01-01", fecha_fin="2027-01-01", vigente=True
            )
            
            proveedor = Proveedor.objects.create(
                empresa=empresa,
                razon_social=f"Proveedor {username}",
                numero_documento=f"999{username}",
                tipo_documento="NIT",
                activo=True
            )
            return user, empresa, resolucion, proveedor

    def test_create_gasto_with_valid_proveedor(self, client, tenant1):
        """Verifica que se pueda crear un gasto con un proveedor del mismo tenant."""
        user, empresa, res, prov = self._setup_tenant_data(tenant1, "user1", "u1@t1.com")
        
        client.force_login(user)
        payload = {
            "descripcion": "Gasto Valido",
            "documento_soporte": {
                "resolucion": res.id,
                "fecha": "2026-05-07",
                "proveedor": prov.id,
                "numero_documento_proveedor": "FACT-123",
                "subtotal": 100000.0,
                "retefuente_porcentaje": 4.0,
                "reteica_porcentaje": 0.0
            }
        }
        
        resp = client.post(
            "/api/v1/gastos/",
            data=payload,
            content_type="application/json",
            HTTP_HOST=f"{tenant1.schema_name}.sintel.com"
        )
        
        assert resp.status_code == status.HTTP_201_CREATED
        gasto_id = resp.json()['id']
        
        # Verificar en base de datos
        with schema_context(tenant1.schema_name):
            ds = DocumentoSoporte.objects.get(id=gasto_id)
            assert ds.proveedor == prov
            assert ds.vendedor_nombre == prov.razon_social # Property works

    def test_create_gasto_with_invalid_proveedor_dsv(self, client, tenant1, tenant2):
        """
        Verifica que el DSV bloquee la creacion de un gasto con un proveedor de otro tenant.
        Escenario: User T1 intenta usar Proveedor de T2.
        """
        # Setup T1
        user1, emp1, res1, prov1 = self._setup_tenant_data(tenant1, "user1", "u1@t1.com")
        # Setup T2 (Proveedor intruso)
        user2, emp2, res2, prov2 = self._setup_tenant_data(tenant2, "user2", "u2@t2.com")
        
        client.force_login(user1)
        payload = {
            "descripcion": "Intento de Ataque IDOR",
            "documento_soporte": {
                "resolucion": res1.id,
                "fecha": "2026-05-07",
                "proveedor": prov2.id, # PROVEEDOR DE OTRO TENANT
                "numero_documento_proveedor": "FACT-666",
                "subtotal": 50000.0
            }
        }
        
        resp = client.post(
            "/api/v1/gastos/",
            data=payload,
            content_type="application/json",
            HTTP_HOST=f"{tenant1.schema_name}.sintel.com"
        )
        
        # Debe fallar por Double Semantic Verification (DSV)
        # El business service lanza ValidationError si el proveedor no es del tenant
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "proveedor" in str(resp.json()) or "detail" in str(resp.json())

    def test_list_gastos_shows_proveedor_data(self, client, tenant1):
        """Verifica que el listado de gastos incluya la razon social del proveedor."""
        user, empresa, res, prov = self._setup_tenant_data(tenant1, "user1", "u1@t1.com")
        
        with schema_context(tenant1.schema_name):
            DocumentoSoporte.objects.create(
                empresa=empresa, resolucion_dian=res, consecutivo=1,
                fecha="2026-05-01", proveedor=prov,
                subtotal=1000, total=1000,
                descripcion="Gasto con Proveedor"
            )
            
        client.force_login(user)
        resp = client.get("/api/v1/gastos/", HTTP_HOST=f"{tenant1.schema_name}.sintel.com")
        
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()['results'][0]
        # El serializador GastoListSerializer debe tener ds_vendedor (aplanado)
        assert data['ds_vendedor'] == prov.razon_social
