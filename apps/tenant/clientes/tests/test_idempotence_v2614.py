"""
Tests de integración para idempotencia de Clientes v2.61.4.

Valida:
- Idempotencia: POST 2x = 1 cliente (update_or_create pattern)
- HTTP status: 201 Created vs 200 OK
- Zero Trust: Validación de empresa_id en contexto
- Caching: @cached_property tenant_empresa
"""
import pytest
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services.services import crear_cliente
from apps.tenant.empresa.models import Empresa


@pytest.mark.django_db
class TestIdempotenciaClientes:
    """Suite: Idempotencia en creación de clientes."""
    
    def test_crear_cliente_idempotente_post_2x_equals_1(self, tenant):
        """
        # WARNING: v2.61.4: POST 2x con mismos datos = 1 cliente (IDEMPOTENCIA)
        
        Valida que update_or_create() previene duplicados incluso con POST repetido:
        - First POST: Create (201)
        - Second POST: Update (200)
        - Result: 1 cliente, no duplicados
        """
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre="Test Empresa", 
                    razon_social="TEST S.A.S.", 
                    nit="901234567"
                )
            
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",  # Lookup field
                "razon_social": "CLIENTE ORIGINAL",
                "nombre_comercial": "CLIENTE CO",
                "regimen_tributario": "ORDINARIO",
                "email": "cliente@example.com",
                "telefono": "3000000000",
                "activo": True,
            }
            
            # # WARNING: PRIMER POST: Crear cliente
            cliente1, creado1 = crear_cliente(empresa, payload)
            assert creado1 is True, "First call should create"
            assert cliente1.razon_social == "CLIENTE ORIGINAL"
            count_after_first = Cliente.objects.filter(empresa=empresa).count()
            assert count_after_first == 1, "Should have 1 cliente after first POST"
            
            # # WARNING: SEGUNDO POST: Idéntico. Debe actualizar, NO crear duplicado
            cliente2, creado2 = crear_cliente(empresa, payload)
            assert creado2 is False, "Second call should update (not create)"
            assert cliente2.id == cliente1.id, "Should be same cliente object"
            count_after_second = Cliente.objects.filter(empresa=empresa).count()
            assert count_after_second == 1, "Should still have 1 cliente after second POST"
    
    def test_crear_cliente_idempotente_actualiza_campos(self, tenant):
        """
        # WARNING: v2.61.4: Campos se actualizan si cambian (pero lookup fields no cambiarían)
        
        Valida que update_or_create() actualiza datos adicionales:
        """
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre="Test Empresa", 
                    razon_social="TEST S.A.S.", 
                    nit="901234567"
                )
            
            payload_v1 = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "CLIENTE V1",
                "nombre_comercial": "CLIENTE CO V1",
                "regimen_tributario": "ORDINARIO",
                "email": "cliente@example.com",
                "telefono": "3000000000",
                "activo": True,
            }
            
            # # WARNING: Primera llamada: Crear con V1
            cliente1, creado1 = crear_cliente(empresa, payload_v1)
            assert cliente1.nombre_comercial == "CLIENTE CO V1"
            
            # # WARNING: Segunda llamada: Mismo documento, pero actualizamos campos
            payload_v2 = {**payload_v1, "nombre_comercial": "CLIENTE CO V2"}
            cliente2, creado2 = crear_cliente(empresa, payload_v2)
            
            assert cliente2.id == cliente1.id
            assert creado2 is False
            assert cliente2.nombre_comercial == "CLIENTE CO V2", "Should update field"
            assert Cliente.objects.filter(empresa=empresa).count() == 1


@pytest.mark.django_db
class TestHTTPStatusCodes:
    """Suite: HTTP status codes reflejen idempotencia (201 vs 200)."""
    
    def test_api_create_cliente_http_201_first_post(self, tenant, admin_user):
        """
        # WARNING: v2.61.4: First POST = HTTP 201 Created
        
        Valida que ViewSet.create() retorna 201 cuando creado=True:
        """
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)
        
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre="Test Empresa", 
                    razon_social="TEST S.A.S.", 
                    nit="901234567"
                )
            
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "CLIENTE NEW",
                "nombre_comercial": "CLIENTE CO",
                "regimen_tributario": "ORDINARIO",
                "email": "cliente@example.com",
                "telefono": "3000000000",
                "activo": True,
                # DEUDA-C01 (mision "Clientes + Cartera", 2026-09-11): JURIDICA
                # via ViewSet (validar_representante=True) exige representante legal.
                "contactos": [{
                    "nombre_completo": "Representante Legal Test",
                    "email": "representante@example.com",
                    "es_representante_legal": True,
                }],
            }

            # # WARNING: PRIMER POST
            response1 = api_client.post(
                '/api/v1/clientes/',
                payload,
                format='json',
                HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
            )
            assert response1.status_code == 201, f"Expected 201, got {response1.status_code}: {response1.data}"
            data1 = response1.json()
            cliente_id = data1.get('id')
            assert cliente_id is not None, "Should return created cliente ID"
    
    def test_api_create_cliente_http_400_second_post_duplicado(self, tenant, admin_user):
        """
        Hallazgo real: FASE 4 anti-duplicidad (Zero Trust,
        ClienteDetailSerializer.validate()) rechaza con 400 un documento
        duplicado en CREATE, ANTES de llegar a la logica de upsert de
        registrar_cliente_completo() -- esta expectativa reemplaza la
        v2.61.4 original (200 idempotente), superada por ese cambio
        posterior. La idempotencia upsert real sigue probada y viva a
        nivel de servicio en TestIdempotenciaClientes (crear_cliente(),
        que no pasa por el serializer del ViewSet).
        """
        api_client = APIClient()
        api_client.force_authenticate(user=admin_user)
        
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre="Test Empresa", 
                    razon_social="TEST S.A.S.", 
                    nit="901234567"
                )
            
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "CLIENTE NEW",
                "nombre_comercial": "CLIENTE CO",
                "regimen_tributario": "ORDINARIO",
                "email": "cliente@example.com",
                "telefono": "3000000000",
                "activo": True,
                # DEUDA-C01 (mision "Clientes + Cartera", 2026-09-11): JURIDICA
                # via ViewSet (validar_representante=True) exige representante legal.
                "contactos": [{
                    "nombre_completo": "Representante Legal Test",
                    "email": "representante@example.com",
                    "es_representante_legal": True,
                }],
            }

            # # WARNING: PRIMER POST: Create
            response1 = api_client.post(
                '/api/v1/clientes/',
                payload,
                format='json',
                HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
            )
            assert response1.status_code == 201
            
            # # WARNING: SEGUNDO POST: mismo documento -> rechazado (FASE 4 anti-duplicidad)
            response2 = api_client.post(
                '/api/v1/clientes/',
                payload,
                format='json',
                HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
            )
            assert response2.status_code == 400, f"Expected 400, got {response2.status_code}: {response2.data}"
            assert 'numero_documento' in response2.json()


@pytest.mark.django_db
class TestZeroTrustValidation:
    """Suite: Validación Zero Trust en contexto de empresa."""
    
    def test_creating_cliente_with_wrong_empresa_fails(self, tenant):
        """
        # WARNING: v2.61.4: Crear cliente sin empresa o con empresa inválida falla.
        
        Valida que Zero Trust require empresa válida:
        """
        with schema_context(tenant.schema_name):
            payload = {
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": "901000999",
                "razon_social": "CLIENTE",
                "nombre_comercial": "CLIENTE CO",
                "regimen_tributario": "ORDINARIO",
                "email": "cliente@example.com",
                "telefono": "3000000000",
                "activo": True,
            }
            
            # # WARNING: Intentar crear con empresa=None
            with pytest.raises(Exception):
                crear_cliente(None, payload)
    
    def test_serializer_context_includes_empresa_id(self, tenant, admin_user):
        """
        # WARNING: v2.61.4: Serializer context debe incluir empresa_id para validación.
        
        Valida que get_serializer_context() inyecta empresa_id:
        """
        from django.test import RequestFactory
        from rest_framework.test import force_authenticate

        from apps.tenant.clientes.api.viewsets import ClienteViewSet
        
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre="Test Empresa", 
                    razon_social="TEST S.A.S.", 
                    nit="901234567"
                )
            
            # Crear request y ViewSet
            factory = RequestFactory()
            request = factory.get('/')
            force_authenticate(request, user=admin_user)
            
            viewset = ClienteViewSet()
            viewset.request = request
            viewset.format_kwarg = None
            
            # # WARNING: Obtener contexto del serializer
            context = viewset.get_serializer_context()
            
            # # WARNING: Validar que empresa_id está en contexto
            assert 'empresa_id' in context, "Context should include empresa_id"
            assert context['empresa_id'] == empresa.id, "empresa_id should match"


@pytest.mark.django_db
class TestCaching:
    """Suite: Validar @cached_property tenant_empresa."""
    
    def test_tenant_empresa_cached_per_request(self, tenant, admin_user):
        """
        # WARNING: v2.61.4: @cached_property tenant_empresa debe cachear por request.
        
        Valida que se ejecuta solo 1 query por request al acceder a tenant_empresa:
        """
        from django.db import connection
        from django.test import RequestFactory
        from django.test.utils import CaptureQueriesContext
        from rest_framework.test import force_authenticate

        from apps.tenant.clientes.api.viewsets import ClienteViewSet
        
        with schema_context(tenant.schema_name):
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre="Test Empresa", 
                    razon_social="TEST S.A.S.", 
                    nit="901234567"
                )
            
            factory = RequestFactory()
            request = factory.get('/')
            force_authenticate(request, user=admin_user)
            
            viewset = ClienteViewSet()
            viewset.request = request
            viewset.format_kwarg = None
            
            # # WARNING: Capturar queries
            with CaptureQueriesContext(connection) as ctx:
                # Primera llamada a tenant_empresa
                emp1 = viewset.tenant_empresa
                count_after_first = len(ctx)
                
                # Segunda llamada a tenant_empresa
                emp2 = viewset.tenant_empresa
                count_after_second = len(ctx)
            
            # # WARNING: Validar caching
            assert emp1.id == emp2.id
            assert count_after_first == count_after_second, (
                f"tenant_empresa should be cached. "
                f"Queries after first call: {count_after_first}, "
                f"Queries after second call: {count_after_second}"
            )
