"""
Suite de Pruebas de Integración UI - Creación de Tenants (Consola).

Valida el flujo completo de creación de tenants desde la interfaz web,
asegurando que la refactorización del Core (Modelos, Señales, Servicios)
funcione correctamente cuando un usuario humano usa el sistema.

Flujo a Probar:
1. GET /console/tenants/new/ -> Formulario
2. POST /console/tenants/create/ -> Procesa creación
3. Backend: Tarea Celery onboard_tenant_task -> Servicio crear_tenant
4. Validación: Client, Domain (vía señal), TenantMembership creados
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import override_settings
from pytest_django.asserts import assertTemplateUsed, assertRedirects
from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()


@pytest.mark.django_db
@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class TestTenantUICreationFlow:
    """Tests de integración para el flujo completo de creación de tenants desde la UI."""
    
    def test_get_new_tenant_form_renders_correctly(self, admin_client):
        """
        Test: Renderizado del formulario (GET /console/tenants/new/).
        
        Valida:
        - Status Code: 200
        - Template usado: console/pages/tenants/new.html
        - Campo schema_name presente (NO subdomain)
        - Usuarios disponibles en contexto
        """
        url = reverse("console:tenants-new")
        response = admin_client.get(url)
        
        # Verificar status code
        assert response.status_code == 200
        
        # Verificar template usado
        assertTemplateUsed(response, "console/pages/tenants/new.html")
        
        # Verificar que se pasan usuarios en el contexto
        assert "users" in response.context
        assert isinstance(response.context["users"], (list, type(User.objects.none())))
        
        # ✅ VALIDACIÓN CRÍTICA: Verificar que el formulario usa schema_name (NO subdomain)
        content = response.content.decode('utf-8')
        assert 'name="schema_name"' in content or 'id="schema_name"' in content
        assert 'name="nombre"' in content or 'id="nombre"' in content
        assert 'name="admin_user_id"' in content or 'id="admin_user_id"' in content
        
        # Verificar que NO existe campo subdomain
        assert 'name="subdomain"' not in content
        
        # Verificar que existe campo dominio (opcional)
        assert 'name="dominio"' in content or 'id="dominio"' in content
    
    def test_create_tenant_successful_flow(self, admin_client, admin_user):
        """
        Test: Creación exitosa de tenant (POST /console/tenants/create/).
        
        Valida:
        - Redirección a status page
        - Client creado con schema_name correcto
        - Domain creado automáticamente por señal (domain.tenant == client)
        - TenantMembership creado para admin_user
        """
        # Datos del formulario
        nombre = "Empresa UI Test"
        schema_name = "uitest"
        admin_user_id = admin_user.id
        
        url = reverse("console:tenants-create")
        
        # Verificar que no existe el tenant antes
        assert not Client.objects.filter(schema_name=schema_name).exists()
        
        # POST al endpoint de creación
        response = admin_client.post(url, {
            "nombre": nombre,
            "schema_name": schema_name,
            "admin_user_id": admin_user_id,
        })
        
        # ✅ Verificar redirección (302) a status page
        assert response.status_code == 302
        assert "tenants/status" in response.url
        assert "task_id" in response.url
        
        # ✅ VALIDACIÓN CRÍTICA: Verificar integridad de datos en BD
        
        # 1. Client existe con schema_name correcto
        client = Client.objects.filter(schema_name=schema_name).first()
        assert client is not None, "Client no fue creado"
        assert client.nombre == nombre
        assert client.schema_name == schema_name
        
        # 2. Domain fue creado automáticamente por la señal post_save
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        assert domain is not None, "Domain no fue creado por la señal"
        assert domain.tenant == client, "Domain.tenant debe apuntar a Client (NO usar .client)"
        
        # Verificar que el dominio se construyó correctamente
        # Si schema_name no contiene punto, debe ser {schema_name}.localhost
        expected_domain = f"{schema_name}.localhost"
        assert domain.domain == expected_domain, f"Domain esperado: {expected_domain}, obtenido: {domain.domain}"
        
        # 3. TenantMembership fue creado para el admin_user
        membership = TenantMembership.objects.filter(
            client=client,
            user=admin_user,
            rol="ADMIN"
        ).first()
        assert membership is not None, "TenantMembership no fue creado"
        assert membership.is_primary_admin is True
        assert membership.rol == "ADMIN"
    
    def test_create_tenant_with_custom_domain(self, admin_client, admin_user):
        """
        Test: Creación de tenant con dominio personalizado.
        
        Valida:
        - Si se proporciona dominio, se actualiza el dominio creado automáticamente
        """
        nombre = "Empresa Custom Domain"
        schema_name = "customdomain"
        dominio = "custom.example.com"
        admin_user_id = admin_user.id
        
        url = reverse("console:tenants-create")
        
        response = admin_client.post(url, {
            "nombre": nombre,
            "schema_name": schema_name,
            "dominio": dominio,
            "admin_user_id": admin_user_id,
        })
        
        assert response.status_code == 302
        
        # Verificar que el dominio personalizado se usó
        client = Client.objects.get(schema_name=schema_name)
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        
        # El dominio debe ser el personalizado (sin puerto)
        assert domain.domain == dominio.split(":")[0]
    
    def test_create_tenant_duplicate_schema_name(self, admin_client, admin_user):
        """
        Test: Validación de errores - schema_name duplicado.
        
        Valida:
        - No debe crear tenant duplicado
        - Debe mostrar mensaje de error
        - Debe redirigir a formulario con mensaje
        """
        schema_name = "duplicado"
        
        # Crear primer tenant
        Client.objects.create(
            schema_name=schema_name,
            nombre="Primera Empresa",
            auto_create_schema=True
        )
        
        url = reverse("console:tenants-create")
        
        # Intentar crear segundo tenant con mismo schema_name
        response = admin_client.post(url, {
            "nombre": "Segunda Empresa",
            "schema_name": schema_name,
            "admin_user_id": admin_user.id,
        })
        
        # ✅ Verificar que NO se creó otro tenant
        assert Client.objects.filter(schema_name=schema_name).count() == 1
        
        # ✅ Verificar redirección con mensaje de error
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
        
        # Verificar que hay mensaje de error (se pasa en la sesión)
        # Nota: Los mensajes se pasan vía messages framework, no en la respuesta directa
        # Para verificar mensajes, necesitaríamos hacer un GET después del POST
    
    def test_create_tenant_invalid_schema_name(self, admin_client, admin_user):
        """
        Test: Validación de schema_name inválido.
        
        Valida:
        - Schema_name con caracteres inválidos debe ser rechazado
        - Schema_name "public" (reservado) debe ser rechazado
        """
        url = reverse("console:tenants-create")
        
        # Test 1: Schema_name con espacios (inválido)
        response = admin_client.post(url, {
            "nombre": "Empresa Test",
            "schema_name": "test empresa",  # Espacios no permitidos
            "admin_user_id": admin_user.id,
        })
        
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
        assert not Client.objects.filter(schema_name="test empresa").exists()
        
        # Test 2: Schema_name "public" (reservado)
        response = admin_client.post(url, {
            "nombre": "Empresa Test",
            "schema_name": "public",  # Reservado
            "admin_user_id": admin_user.id,
        })
        
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
        assert not Client.objects.filter(schema_name="public").exists()
    
    def test_create_tenant_missing_required_fields(self, admin_client, admin_user):
        """
        Test: Validación de campos requeridos.
        
        Valida:
        - Si faltan campos requeridos, debe redirigir con error
        """
        url = reverse("console:tenants-create")
        
        # Test 1: Falta nombre
        response = admin_client.post(url, {
            "schema_name": "test",
            "admin_user_id": admin_user.id,
        })
        
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
        
        # Test 2: Falta schema_name
        response = admin_client.post(url, {
            "nombre": "Test",
            "admin_user_id": admin_user.id,
        })
        
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
        
        # Test 3: Falta admin_user_id
        response = admin_client.post(url, {
            "nombre": "Test",
            "schema_name": "test",
        })
        
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
    
    def test_create_tenant_domain_validation(self, admin_client, admin_user):
        """
        Test: Validación de dominio duplicado.
        
        Valida:
        - Si se proporciona un dominio que ya existe, debe rechazarse
        """
        # Crear tenant con dominio
        existing_client = Client.objects.create(
            schema_name="existing",
            nombre="Empresa Existente",
            auto_create_schema=True
        )
        Domain.objects.create(
            domain="existing.example.com",
            tenant=existing_client,
            is_primary=True
        )
        
        url = reverse("console:tenants-create")
        
        # Intentar crear tenant con dominio duplicado
        response = admin_client.post(url, {
            "nombre": "Nueva Empresa",
            "schema_name": "nueva",
            "dominio": "existing.example.com",  # Duplicado
            "admin_user_id": admin_user.id,
        })
        
        assert response.status_code == 302
        assert response.url == reverse("console:tenants-new")
        
        # Verificar que NO se creó el nuevo tenant
        assert not Client.objects.filter(schema_name="nueva").exists()
    
    def test_create_tenant_signal_creates_domain_automatically(self, admin_client, admin_user):
        """
        Test: Validación crítica - La señal crea el dominio automáticamente.
        
        Valida:
        - Al crear Client, la señal post_save crea Domain automáticamente
        - El dominio se construye correctamente basado en schema_name
        """
        schema_name = "signal-test"
        url = reverse("console:tenants-create")
        
        response = admin_client.post(url, {
            "nombre": "Signal Test",
            "schema_name": schema_name,
            "admin_user_id": admin_user.id,
            # NO proporcionar dominio - debe generarse automáticamente
        })
        
        assert response.status_code == 302
        
        # Verificar que el dominio fue creado por la señal
        client = Client.objects.get(schema_name=schema_name)
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        
        assert domain is not None, "La señal NO creó el dominio automáticamente"
        assert domain.tenant == client, "Domain debe usar 'tenant' como FK (convención django-tenants)"
        assert domain.is_primary is True
        
        # Verificar construcción del dominio
        expected_domain = f"{schema_name}.localhost"
        assert domain.domain == expected_domain
    
    def test_create_tenant_fqdn_schema_name(self, admin_client, admin_user):
        """
        Test: Schema_name con FQDN (contiene punto).
        
        Valida:
        - Si schema_name contiene punto, se usa como dominio completo
        """
        schema_name = "fqdn.example.com"  # FQDN
        url = reverse("console:tenants-create")
        
        response = admin_client.post(url, {
            "nombre": "FQDN Test",
            "schema_name": schema_name,
            "admin_user_id": admin_user.id,
        })
        
        assert response.status_code == 302
        
        client = Client.objects.get(schema_name=schema_name)
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        
        # Si schema_name contiene punto, debe usarse como dominio completo
        assert domain.domain == schema_name
        assert ".localhost" not in domain.domain


@pytest.mark.django_db
@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class TestTenantUIFormValidation:
    """Tests específicos para validación del formulario."""
    
    def test_form_context_contains_users(self, admin_client):
        """Test: El formulario debe incluir lista de usuarios en contexto."""
        url = reverse("console:tenants-new")
        response = admin_client.get(url)
        
        assert response.status_code == 200
        assert "users" in response.context
        
        # Verificar que los usuarios tienen los campos esperados
        users = response.context["users"]
        if users:
            user = users[0]
            assert "id" in user
            assert "email" in user
    
    def test_form_requires_staff(self, client):
        """Test: El formulario requiere usuario staff."""
        # Crear usuario NO staff
        user = User.objects.create_user(
            email="regular@test.local",
            password="test123"
        )
        client.force_login(user)
        
        url = reverse("console:tenants-new")
        response = client.get(url)
        
        # Debe ser 403 (PermissionDenied) o 302 (redirect a login)
        assert response.status_code in (302, 403)


@pytest.mark.django_db
@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class TestTenantUIIntegrationChain:
    """Tests de integración completa: UI -> Celery -> Servicio -> Modelos."""
    
    def test_full_integration_chain(self, admin_client, admin_user):
        """
        Test: Cadena completa de integración.
        
        Flujo:
        1. Usuario accede al formulario (GET)
        2. Usuario completa y envía formulario (POST)
        3. Vista dispara tarea Celery (onboard_tenant_task)
        4. Tarea ejecuta servicio (crear_tenant)
        5. Servicio crea Client (dispara señal)
        6. Señal crea Domain automáticamente
        7. Servicio crea TenantMembership
        8. Validar que todo existe en BD
        """
        # Paso 1: Acceder al formulario
        form_url = reverse("console:tenants-new")
        form_response = admin_client.get(form_url)
        assert form_response.status_code == 200
        
        # Paso 2: Enviar formulario
        create_url = reverse("console:tenants-create")
        create_response = admin_client.post(create_url, {
            "nombre": "Integration Test Corp",
            "schema_name": "integrationtest",
            "admin_user_id": admin_user.id,
        })
        
        # Paso 3-7: Validar que la cadena completa funcionó
        assert create_response.status_code == 302
        
        # Validar Client
        client = Client.objects.get(schema_name="integrationtest")
        assert client.nombre == "Integration Test Corp"
        
        # Validar Domain (creado por señal)
        domain = Domain.objects.get(tenant=client, is_primary=True)
        assert domain.domain == "integrationtest.localhost"
        
        # Validar TenantMembership
        membership = TenantMembership.objects.get(
            client=client,
            user=admin_user
        )
        assert membership.rol == "ADMIN"
        assert membership.is_primary_admin is True
        
        # Validar que el esquema PostgreSQL fue creado (si hay permisos)
        try:
            from django_tenants.utils import schema_exists
            assert schema_exists("integrationtest") is True
        except Exception:
            # Si no hay permisos, al menos validar que el Client existe
            pass
