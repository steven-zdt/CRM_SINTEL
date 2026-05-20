"""
Tests de integración para idempotencia de Proveedores v2.61.4.

Valida:
- Idempotencia: POST 2x = 1 proveedor (update_or_create pattern)
- HTTP status: 201 Created vs 200 OK
- Zero Trust: Validación de empresa_id en contexto
- Caching: @cached_property tenant_empresa
"""
import pytest
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import Domain
from apps.tenant.empresa.models import Empresa
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proveedores.services.services import crear_proveedor


@pytest.fixture(scope="module")
def tenant(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock(), schema_context(get_public_schema_name()):
        tenant = TenantClient.objects.filter(schema_name='home').only('id', 'schema_name').first()
        if not tenant:
            tenant = TenantClient(schema_name='home', nombre='Home Test Tenant', is_active=True)
            tenant.save()
        Domain.objects.get_or_create(
            domain='home.sintel.com',
            defaults={'tenant': tenant, 'is_primary': True},
        )
        return TenantClient.objects.only('id', 'schema_name').get(pk=tenant.pk)


@pytest.fixture
def admin_user(django_user_model, tenant):
    from apps.public.tenants.models import TenantMembership
    from apps.tenant.perfil.models import TenantProfile
    
    user = django_user_model.objects.filter(email='proveedores-admin@example.com').first()
    if not user:
        user = django_user_model.objects.create_superuser(
            username='proveedores-admin',
            email='proveedores-admin@example.com',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
    
    TenantMembership.objects.get_or_create(
        client=tenant,
        user=user,
        defaults={'is_active': True, 'rol': 'ADMIN'}
    )
    
    with schema_context(tenant.schema_name):
        empresa = _get_or_create_empresa()
        TenantProfile.objects.get_or_create(
            user=user,
            empresa=empresa,
            defaults={'rol': 'ADMIN'}
        )
        
    return user


def _get_or_create_empresa():
    empresa = Empresa.objects.only('id', 'razon_social', 'nit').first()
    if empresa:
        return empresa
    return Empresa.objects.create(
        razon_social='EMPRESA TEST PROVEEDORES S.A.S.',
        nit='901234567',
        direccion='Calle Falsa 123',
    )



@pytest.mark.django_db
class TestIdempotenciaProveedores:
    """Suite: Idempotencia en creación de proveedores."""
    
    def test_crear_proveedor_idempotente_post_2x_equals_1(self, tenant):
        """
        # WARNING: v2.61.4: POST 2x con mismos datos = 1 proveedor (IDEMPOTENCIA)
        
        Valida que update_or_create() previene duplicados:
        - First POST: Create (201)
        - Second POST: Update (200)
        - Result: 1 proveedor, no duplicados
        """
        with schema_context(tenant.schema_name):
            empresa = _get_or_create_empresa()
            
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",  # Lookup field
                "razon_social": "PROVEEDOR ORIGINAL",
                "nombre_comercial": "PROV CO",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            # # WARNING: PRIMER POST: Crear proveedor
            proveedor1, creado1 = crear_proveedor(empresa.id, payload)
            assert creado1 is True, "First call should create"
            assert proveedor1.razon_social == "PROVEEDOR ORIGINAL"
            count_after_first = Proveedor.objects.filter(empresa=empresa).count()
            assert count_after_first == 1, "Should have 1 proveedor after first POST"
            
            # # WARNING: SEGUNDO POST: Idéntico. Debe actualizar, NO crear duplicado
            proveedor2, creado2 = crear_proveedor(empresa.id, payload)
            assert creado2 is False, "Second call should update (not create)"
            assert proveedor2.id == proveedor1.id, "Should be same proveedor object"
            count_after_second = Proveedor.objects.filter(empresa=empresa).count()
            assert count_after_second == 1, "Should still have 1 proveedor after second POST"
    
    def test_crear_proveedor_idempotente_actualiza_campos(self, tenant):
        """
        # WARNING: v2.61.4: Campos se actualizan si cambian (update_or_create).
        
        Valida que update_or_create() actualiza datos adicionales:
        """
        with schema_context(tenant.schema_name):
            empresa = _get_or_create_empresa()
            
            payload_v1 = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "PROVEEDOR V1",
                "nombre_comercial": "PROV CO V1",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            # # WARNING: Primera llamada: Crear con V1
            proveedor1, creado1 = crear_proveedor(empresa.id, payload_v1)
            assert proveedor1.nombre_comercial == "PROV CO V1"
            
            # # WARNING: Segunda llamada: Mismo documento, pero actualizamos campos
            payload_v2 = {**payload_v1, "nombre_comercial": "PROV CO V2"}
            proveedor2, creado2 = crear_proveedor(empresa.id, payload_v2)
            
            assert proveedor2.id == proveedor1.id
            assert creado2 is False
            assert proveedor2.nombre_comercial == "PROV CO V2", "Should update field"
            assert Proveedor.objects.filter(empresa=empresa).count() == 1
    
    def test_create_proveedor_different_documento_creates_new(self, tenant):
        """
        # WARNING: v2.61.4: Diferentes números de documento = registros diferentes.
        
        Valida que update_or_create() usa lookup fields correctamente:
        """
        with schema_context(tenant.schema_name):
            empresa = _get_or_create_empresa()
            
            payload1 = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000111",  # DIFERENTE
                "razon_social": "PROVEEDOR 1",
                "nombre_comercial": "PROV 1",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov1@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            payload2 = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000222",  # DIFERENTE
                "razon_social": "PROVEEDOR 2",
                "nombre_comercial": "PROV 2",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov2@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            # # WARNING: Crear dos proveedores con números diferentes
            prov1, creado1 = crear_proveedor(empresa.id, payload1)
            assert creado1 is True
            
            prov2, creado2 = crear_proveedor(empresa.id, payload2)
            assert creado2 is True
            assert prov2.id != prov1.id, "Different documento numbers should create different records"
            
            # # WARNING: Validar que hay 2 proveedores
            assert Proveedor.objects.filter(empresa=empresa).count() == 2


@pytest.mark.django_db
class TestHTTPStatusCodesProveedores:
    """Suite: HTTP status codes reflejen idempotencia (201 vs 200)."""
    
    def test_api_create_proveedor_http_201_first_post(self, tenant, admin_user):
        """
        # WARNING: v2.61.4: First POST = HTTP 201 Created
        """
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)
        tenant_host = f"{tenant.schema_name}.sintel.com"
        
        with schema_context(tenant.schema_name):
            empresa = _get_or_create_empresa()
            
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "PROVEEDOR NEW",
                "nombre_comercial": "PROV CO",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            # # WARNING: PRIMER POST
            response1 = api_client.post('/api/v1/proveedores/', payload, format='json', HTTP_HOST=tenant_host)
            response1_body = getattr(response1, 'data', None) or getattr(response1, 'content', b'')
            assert response1.status_code == 201, f"Expected 201, got {response1.status_code}: {response1_body}"
            data1 = response1.json()
            proveedor_id = data1.get('id')
            assert proveedor_id is not None, "Should return created proveedor ID"
    
    def test_api_create_proveedor_http_200_second_post(self, tenant, admin_user):
        """
        # WARNING: v2.61.4: Second POST (idempotencia) = HTTP 200 OK
        """
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)
        tenant_host = f"{tenant.schema_name}.sintel.com"
        
        with schema_context(tenant.schema_name):
            empresa = _get_or_create_empresa()
            
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "PROVEEDOR NEW",
                "nombre_comercial": "PROV CO",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            # # WARNING: PRIMER POST: Create
            response1 = api_client.post('/api/v1/proveedores/', payload, format='json', HTTP_HOST=tenant_host)
            assert response1.status_code == 201
            
            # # WARNING: SEGUNDO POST: Update (idempotencia)
            response2 = api_client.post('/api/v1/proveedores/', payload, format='json', HTTP_HOST=tenant_host)
            response2_body = getattr(response2, 'data', None) or getattr(response2, 'content', b'')
            assert response2.status_code == 200, f"Expected 200, got {response2.status_code}: {response2_body}"
            data2 = response2.json()
            
            # # WARNING: Validar que el ID no cambió
            assert data2.get('id') == response1.json().get('id'), "Should be same proveedor"


@pytest.mark.django_db
class TestZeroTrustValidationProveedores:
    """Suite: Validación Zero Trust en contexto de empresa."""
    
    def test_creating_proveedor_with_invalid_empresa_fails(self, tenant):
        """
        # WARNING: v2.61.4: Crear proveedor con empresa_id inválida falla.
        """
        with schema_context(tenant.schema_name):
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "PROVEEDOR",
                "nombre_comercial": "PROV CO",
                "regimen_tributario": "ORDINARIO",
                "email_contacto": "prov@example.com",
                "telefono_contacto": "3000000000",
                "activo": True,
            }
            
            # # WARNING: Intentar crear con empresa_id inválida (999999)
            with pytest.raises(Exception):
                crear_proveedor(999999, payload)
    
    def test_serializer_context_includes_empresa_id_proveedores(self, tenant, admin_user):
        """
        # WARNING: v2.61.4: Serializer context debe incluir empresa_id para validación.
        """
        from django.test import RequestFactory
        from rest_framework.test import force_authenticate

        from apps.tenant.proveedores.api.viewsets import ProveedorViewSet
        
        with schema_context(tenant.schema_name):
            empresa = _get_or_create_empresa()
            
            factory = RequestFactory()
            request = factory.get('/')
            force_authenticate(request, user=admin_user)
            
            viewset = ProveedorViewSet()
            viewset.request = request
            viewset.format_kwarg = None
            
            # # WARNING: Obtener contexto del serializer
            context = viewset.get_serializer_context()
            
            # # WARNING: Validar que empresa_id está en contexto
            assert 'empresa_id' in context, "Context should include empresa_id"
            assert context['empresa_id'] == empresa.id, "empresa_id should match"
