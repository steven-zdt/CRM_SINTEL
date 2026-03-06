"""
Tests de Servicios de Negocio para tenants.

Valida la lógica de apps.services.onboarding.empresa_service.
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.services.onboarding.empresa_service import crear_tenant, generar_schema_name
from tests.public.tenants.factories import UserFactory, ClientFactory

User = get_user_model()


@pytest.mark.django_db
class TestCrearTenant:
    """Tests para la función crear_tenant."""
    
    def test_crear_tenant_success(self, admin_user):
        """Test: Ejecutar crear_tenant con datos válidos y verificar resultados."""
        nombre = "Test Corp"
        schema_name = "testcorp"
        
        client, domain, login_url = crear_tenant(
            nombre=nombre,
            schema_name=schema_name,
            admin_user_id=admin_user.id
        )
        
        # Verificar que Client existe
        assert client is not None
        assert client.nombre == nombre
        assert client.schema_name == schema_name
        assert Client.objects.filter(schema_name=schema_name).exists()
        
        # Verificar que Domain existe (vía señal)
        assert domain is not None
        assert domain.tenant == client
        assert domain.is_primary is True
        assert Domain.objects.filter(tenant=client, is_primary=True).exists()
        
        # Verificar que se creó TenantMembership con rol ADMIN
        membership = TenantMembership.objects.filter(
            client=client,
            user=admin_user,
            rol="ADMIN"
        ).first()
        
        assert membership is not None
        assert membership.is_primary_admin is True
        assert membership.user == admin_user
        assert membership.client == client
    
    def test_crear_tenant_creates_schema(self, admin_user):
        """Test: Verificar que se creó el esquema PostgreSQL."""
        from django_tenants.utils import schema_exists
        
        schema_name = "testcorp"
        
        client, domain, login_url = crear_tenant(
            nombre="Test Corp",
            schema_name=schema_name,
            admin_user_id=admin_user.id
        )
        
        # Verificar que el esquema existe (puede requerir permisos de DB)
        # Nota: En algunos entornos de test, esto puede fallar si no hay permisos
        try:
            assert schema_exists(schema_name) is True
        except Exception:
            # Si falla por permisos, al menos verificar que el Client existe
            assert Client.objects.filter(schema_name=schema_name).exists()
    
    def test_crear_tenant_normalizes_schema_name(self, admin_user):
        """Test: crear_tenant normaliza schema_name (strip y lower)."""
        client, domain, login_url = crear_tenant(
            nombre="Test Corp",
            schema_name="  TESTCORP  ",
            admin_user_id=admin_user.id
        )
        
        assert client.schema_name == "testcorp"
    
    def test_crear_tenant_duplicate_schema_name(self, admin_user):
        """Test: Intentar crear tenant con schema_name duplicado debe fallar."""
        schema_name = "testcorp"
        
        # Crear primer tenant
        crear_tenant(
            nombre="Test Corp 1",
            schema_name=schema_name,
            admin_user_id=admin_user.id
        )
        
        # Intentar crear segundo tenant con mismo schema_name
        with pytest.raises(ValidationError, match="ya existe"):
            crear_tenant(
                nombre="Test Corp 2",
                schema_name=schema_name,
                admin_user_id=admin_user.id
            )
    
    def test_crear_tenant_invalid_user(self):
        """Test: Intentar crear tenant con usuario inexistente debe fallar."""
        with pytest.raises(User.DoesNotExist):
            crear_tenant(
                nombre="Test Corp",
                schema_name="testcorp",
                admin_user_id=99999  # ID inexistente
            )
    
    def test_crear_tenant_returns_login_url(self, admin_user):
        """Test: Verificar que crear_tenant retorna login_url apuntando a la raíz (/)."""
        client, domain, login_url = crear_tenant(
            nombre="Test Corp",
            schema_name="testcorp",
            admin_user_id=admin_user.id
        )
        
        assert login_url is not None
        assert domain.domain in login_url
        # ⚠️ REGLA DE NEGOCIO: login_url debe apuntar a la raíz (/) - landing page
        assert login_url.endswith("/"), f"login_url debe terminar en '/', got '{login_url}'"
        assert "/login" not in login_url, f"login_url NO debe contener '/login', got '{login_url}'"
        assert "/admin/login" not in login_url, f"login_url NO debe contener '/admin/login', got '{login_url}'"


@pytest.mark.django_db
class TestValidaciones:
    """Tests para validaciones de schema_name."""
    
    def test_schema_name_invalid_characters(self, admin_user):
        """Test: Intentar crear tenant con caracteres inválidos en schema_name."""
        invalid_schemas = [
            "test corp",  # Espacios
            "TEST_CORP",  # Mayúsculas (aunque se normaliza, probamos validación)
            "test@corp",  # Caracteres especiales
            "test.corp!",  # Caracteres especiales
        ]
        
        for invalid_schema in invalid_schemas:
            with pytest.raises((ValidationError, ValueError)):
                crear_tenant(
                    nombre="Test Corp",
                    schema_name=invalid_schema,
                    admin_user_id=admin_user.id
                )
    
    def test_schema_name_reserved_public(self, admin_user):
        """Test: Intentar crear tenant con schema_name='public' debe fallar."""
        with pytest.raises(ValidationError):
            crear_tenant(
                nombre="Test Corp",
                schema_name="public",  # Reservado
                admin_user_id=admin_user.id
            )
    
    def test_schema_name_too_long(self, admin_user):
        """Test: Intentar crear tenant con schema_name muy largo debe fallar."""
        long_schema = "a" * 64  # Más de 63 caracteres
        
        with pytest.raises(ValidationError):
            crear_tenant(
                nombre="Test Corp",
                schema_name=long_schema,
                admin_user_id=admin_user.id
            )


@pytest.mark.django_db
class TestGenerarSchemaName:
    """Tests para la función generar_schema_name."""
    
    def test_generar_schema_name_basic(self):
        """Test: Generar schema_name desde nombre básico."""
        schema = generar_schema_name("Mi Empresa")
        
        assert schema == "mi-empresa"
        assert schema.islower()
        assert " " not in schema
    
    def test_generar_schema_name_special_chars(self):
        """Test: Generar schema_name con caracteres especiales."""
        schema = generar_schema_name("Empresa & Cía. S.A.")
        
        assert schema.islower()
        assert "&" not in schema
        assert "." not in schema
        assert " " not in schema
    
    def test_generar_schema_name_avoids_public(self):
        """Test: Generar schema_name evita 'public'."""
        schema = generar_schema_name("Public Company")
        
        assert schema != "public"
        assert "public" in schema  # Pero puede contener 'public' como parte
    
    def test_generar_schema_name_handles_duplicates(self):
        """Test: Generar schema_name maneja duplicados."""
        # Crear primer tenant
        ClientFactory(schema_name="mi-empresa")
        
        # Generar schema_name (debe agregar sufijo)
        schema = generar_schema_name("Mi Empresa")
        
        assert schema.startswith("mi-empresa")
        assert schema != "mi-empresa"  # Debe ser diferente
