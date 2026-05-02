"""
Suite de Pruebas CRUD Completa para SINTEL v2.9

Valida la integridad de los modelos Client, Domain y TenantMembership
después de un hard reset de la base de datos.

Alineado con arquitectura_general.md:
- Client usa schema_name (NO subdomain)
- Domain se crea automáticamente vía señal post_save
- Domain.tenant es la FK (convención django-tenants)
- TenantMembership relaciona User con Client
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django_tenants.utils import schema_exists
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.validators import validate_schema_name

User = get_user_model()


@pytest.mark.django_db
class TestClientCRUD:
    """Tests CRUD para el modelo Client."""
    
    def test_create_client_success(self):
        """Test: Creación exitosa de Client usando schema_name."""
        client = Client.objects.create(
            nombre="Empresa Test",
            schema_name="empresatest"
        )
        
        assert client.id is not None
        assert client.nombre == "Empresa Test"
        assert client.schema_name == "empresatest"
        assert client.on_trial is True  # Default
        assert client.paid_until is None  # Default
        assert client.created_on is not None
    
    def test_create_client_schema_name_validation(self):
        """Test: Validación de schema_name (solo minúsculas, números, guiones)."""
        # Schema_name válido
        client = Client.objects.create(
            nombre="Test",
            schema_name="test-123_empresa"
        )
        assert client.schema_name == "test-123_empresa"
        
        # Schema_name con mayúsculas debe ser normalizado
        client2 = Client.objects.create(
            nombre="Test2",
            schema_name="TEST-EMPRESA"
        )
        assert client2.schema_name == "test-empresa"
    
    def test_create_client_schema_name_invalid(self):
        """Test: Schema_name inválido debe ser rechazado."""
        # Schema_name con espacios
        with pytest.raises(ValidationError):
            client = Client(nombre="Test", schema_name="test empresa")
            client.full_clean()
        
        # Schema_name "public" (reservado)
        with pytest.raises(ValidationError):
            client = Client(nombre="Test", schema_name="public")
            client.full_clean()
        
        # Schema_name con caracteres especiales
        with pytest.raises(ValidationError):
            client = Client(nombre="Test", schema_name="test@empresa")
            client.full_clean()
    
    def test_create_client_schema_name_unique(self):
        """Test: Schema_name debe ser único."""
        Client.objects.create(nombre="Empresa 1", schema_name="empresa1")
        
        with pytest.raises(IntegrityError):
            Client.objects.create(nombre="Empresa 2", schema_name="empresa1")
    
    def test_read_client(self):
        """Test: Lectura de Client."""
        client = Client.objects.create(
            nombre="Empresa Lectura",
            schema_name="lectura"
        )
        
        # Leer desde BD
        client_read = Client.objects.get(schema_name="lectura")
        assert client_read.id == client.id
        assert client_read.nombre == "Empresa Lectura"
        assert client_read.schema_name == "lectura"
    
    def test_update_client(self):
        """Test: Actualización de Client."""
        client = Client.objects.create(
            nombre="Empresa Original",
            schema_name="original"
        )
        
        # Actualizar nombre
        client.nombre = "Empresa Actualizada"
        client.on_trial = False
        client.save()
        
        # Verificar persistencia
        client_updated = Client.objects.get(schema_name="original")
        assert client_updated.nombre == "Empresa Actualizada"
        assert client_updated.on_trial is False
    
    def test_delete_client_cascade(self):
        """Test: Eliminación de Client elimina Domain y TenantMembership en cascada."""
        client = Client.objects.create(
            nombre="Empresa Delete",
            schema_name="delete"
        )
        
        # Crear Domain (automático por señal o manual)
        domain = Domain.objects.filter(tenant=client).first()
        if not domain:
            domain = Domain.objects.create(
                domain="delete.localhost",
                tenant=client,
                is_primary=True
            )
        
        # Crear TenantMembership
        user = User.objects.create_user(
            email="user@delete.com",
            password="test123"
        )
        membership = TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN"
        )
        
        # Eliminar Client
        client_id = client.id
        domain_id = domain.id
        membership_id = membership.id
        
        client.delete()
        
        # Verificar que se eliminaron en cascada
        assert not Client.objects.filter(id=client_id).exists()
        assert not Domain.objects.filter(id=domain_id).exists()
        assert not TenantMembership.objects.filter(id=membership_id).exists()
    
    def test_client_auto_create_schema(self):
        """Test: Client crea esquema PostgreSQL automáticamente."""
        client = Client.objects.create(
            nombre="Empresa Schema",
            schema_name="empresaschema"
        )
        
        # Verificar que el esquema existe
        assert schema_exists("empresaschema") is True


@pytest.mark.django_db
class TestDomainCRUD:
    """Tests CRUD para el modelo Domain."""
    
    def test_domain_created_by_signal(self):
        """Test: Domain se crea automáticamente vía señal post_save."""
        # Crear Client (dispara señal)
        client = Client.objects.create(
            nombre="Empresa Signal",
            schema_name="signaltest"
        )
        
        # Verificar que Domain fue creado automáticamente
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        assert domain is not None, "Domain NO fue creado por la señal"
        assert domain.tenant == client, "Domain.tenant debe apuntar a Client"
        assert domain.is_primary is True
        
        # Verificar construcción del dominio
        # Si schema_name no contiene punto, debe ser {schema_name}.localhost
        expected_domain = f"{client.schema_name}.localhost"
        assert domain.domain == expected_domain
    
    def test_domain_fqdn_schema_name(self):
        """Test: Si schema_name es FQDN, se usa como dominio completo."""
        client = Client.objects.create(
            nombre="Empresa FQDN",
            schema_name="empresa.example.com"
        )
        
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        assert domain is not None
        # Si schema_name contiene punto, debe usarse como dominio completo
        assert domain.domain == "empresa.example.com"
        assert ".localhost" not in domain.domain
    
    def test_domain_tenant_relationship(self):
        """Test: Relación Domain.tenant (NO .client)."""
        client = Client.objects.create(
            nombre="Empresa Relacion",
            schema_name="relacion"
        )
        
        domain = Domain.objects.filter(tenant=client).first()
        assert domain is not None
        
        # [OK] VALIDACIÓN CRÍTICA: Domain usa .tenant (NO .client)
        assert hasattr(domain, 'tenant'), "Domain debe tener atributo 'tenant'"
        assert domain.tenant == client
        assert domain.tenant.schema_name == "relacion"
        
        # Verificar que NO existe .client (solo .tenant)
        assert not hasattr(domain, 'client'), "Domain NO debe tener atributo 'client'"
    
    def test_domain_unique(self):
        """Test: Domain debe ser único."""
        client1 = Client.objects.create(nombre="Empresa 1", schema_name="emp1")
        client2 = Client.objects.create(nombre="Empresa 2", schema_name="emp2")
        
        # Obtener dominios creados por señal
        domain1 = Domain.objects.filter(tenant=client1, is_primary=True).first()
        
        # Intentar crear dominio duplicado
        with pytest.raises(IntegrityError):
            Domain.objects.create(
                domain=domain1.domain,
                tenant=client2,
                is_primary=True
            )
    
    def test_domain_cascade_delete(self):
        """Test: Eliminación de Client elimina Domain en cascada."""
        client = Client.objects.create(
            nombre="Empresa Cascade",
            schema_name="cascade"
        )
        
        domain = Domain.objects.filter(tenant=client).first()
        assert domain is not None
        
        domain_id = domain.id
        client.delete()
        
        assert not Domain.objects.filter(id=domain_id).exists()
    
    def test_domain_multiple_per_tenant(self):
        """Test: Un tenant puede tener múltiples dominios."""
        client = Client.objects.create(
            nombre="Empresa Multi",
            schema_name="multi"
        )
        
        # Dominio principal (creado por señal)
        primary = Domain.objects.filter(tenant=client, is_primary=True).first()
        assert primary is not None
        
        # Crear dominio adicional
        secondary = Domain.objects.create(
            domain="multi-alternativo.localhost",
            tenant=client,
            is_primary=False
        )
        
        # Verificar que ambos existen
        domains = Domain.objects.filter(tenant=client)
        assert domains.count() == 2
        assert primary.is_primary is True
        assert secondary.is_primary is False


@pytest.mark.django_db
class TestTenantMembershipCRUD:
    """Tests CRUD para el modelo TenantMembership."""
    
    def test_create_membership(self):
        """Test: Creación de TenantMembership."""
        client = Client.objects.create(
            nombre="Empresa Membership",
            schema_name="membership"
        )
        
        user = User.objects.create_user(
            email="member@test.com",
            password="test123"
        )
        
        membership = TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN",
            is_primary_admin=True
        )
        
        assert membership.id is not None
        assert membership.client == client
        assert membership.user == user
        assert membership.rol == "ADMIN"
        assert membership.is_primary_admin is True
    
    def test_membership_unique_together(self):
        """Test: Un usuario solo puede tener una membresía por tenant."""
        client = Client.objects.create(nombre="Empresa", schema_name="empresa")
        user = User.objects.create_user(email="user@test.com", password="test123")
        
        # Crear primera membresía
        TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN"
        )
        
        # Intentar crear segunda membresía (debe fallar)
        with pytest.raises(IntegrityError):
            TenantMembership.objects.create(
                client=client,
                user=user,
                rol="STAFF"
            )
    
    def test_membership_cascade_delete(self):
        """Test: Eliminación de Client elimina TenantMembership en cascada."""
        client = Client.objects.create(nombre="Empresa", schema_name="empresa")
        user = User.objects.create_user(email="user@test.com", password="test123")
        
        membership = TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN"
        )
        
        membership_id = membership.id
        client.delete()
        
        assert not TenantMembership.objects.filter(id=membership_id).exists()
    
    def test_membership_user_multiple_tenants(self):
        """Test: Un usuario puede ser miembro de múltiples tenants."""
        client1 = Client.objects.create(nombre="Empresa 1", schema_name="emp1")
        client2 = Client.objects.create(nombre="Empresa 2", schema_name="emp2")
        
        user = User.objects.create_user(email="user@test.com", password="test123")
        
        # Crear membresías en ambos tenants
        membership1 = TenantMembership.objects.create(
            client=client1,
            user=user,
            rol="ADMIN"
        )
        
        membership2 = TenantMembership.objects.create(
            client=client2,
            user=user,
            rol="STAFF"
        )
        
        assert membership1.client == client1
        assert membership2.client == client2
        assert membership1.user == membership2.user == user


@pytest.mark.django_db
class TestFullIntegrationCRUD:
    """Tests de integración completa del flujo CRUD."""
    
    def test_create_tenant_full_flow(self):
        """Test: Flujo completo de creación de tenant."""
        # 1. Crear Client
        client = Client.objects.create(
            nombre="Empresa Completa",
            schema_name="completa"
        )
        
        # 2. Verificar que Domain fue creado por señal
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()
        assert domain is not None
        assert domain.domain == "completa.localhost"
        
        # 3. Verificar que el esquema PostgreSQL existe
        assert schema_exists("completa") is True
        
        # 4. Crear TenantMembership
        user = User.objects.create_user(
            email="admin@completa.com",
            password="test123"
        )
        
        membership = TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN",
            is_primary_admin=True
        )
        
        # 5. Verificar integridad completa
        assert Client.objects.filter(schema_name="completa").exists()
        assert Domain.objects.filter(tenant=client).exists()
        assert TenantMembership.objects.filter(client=client, user=user).exists()
    
    def test_read_tenant_with_relationships(self):
        """Test: Lectura de tenant con todas sus relaciones."""
        client = Client.objects.create(
            nombre="Empresa Read",
            schema_name="read"
        )
        
        # Crear relaciones
        domain = Domain.objects.filter(tenant=client).first()
        user = User.objects.create_user(email="admin@read.com", password="test123")
        membership = TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN"
        )
        
        # Leer desde BD con relaciones
        client_read = Client.objects.prefetch_related('domains', 'memberships').get(
            schema_name="read"
        )
        
        assert client_read.nombre == "Empresa Read"
        assert client_read.domains.count() >= 1
        assert client_read.memberships.count() == 1
        assert client_read.memberships.first().user == user
    
    def test_update_tenant_and_verify_persistence(self):
        """Test: Actualización de tenant y verificación de persistencia."""
        client = Client.objects.create(
            nombre="Empresa Update",
            schema_name="update"
        )
        
        # Actualizar
        client.nombre = "Empresa Actualizada"
        client.on_trial = False
        client.save()
        
        # Verificar persistencia
        client_updated = Client.objects.get(schema_name="update")
        assert client_updated.nombre == "Empresa Actualizada"
        assert client_updated.on_trial is False
        
        # Verificar que Domain sigue asociado
        domain = Domain.objects.filter(tenant=client_updated).first()
        assert domain is not None
        assert domain.tenant == client_updated
    
    def test_delete_tenant_cascade_all(self):
        """Test: Eliminación de tenant elimina todo en cascada."""
        client = Client.objects.create(
            nombre="Empresa Delete",
            schema_name="delete"
        )
        
        domain = Domain.objects.filter(tenant=client).first()
        user = User.objects.create_user(email="admin@delete.com", password="test123")
        membership = TenantMembership.objects.create(
            client=client,
            user=user,
            rol="ADMIN"
        )
        
        # IDs para verificación
        client_id = client.id
        domain_id = domain.id
        membership_id = membership.id
        
        # Eliminar
        client.delete()
        
        # Verificar cascada completa
        assert not Client.objects.filter(id=client_id).exists()
        assert not Domain.objects.filter(id=domain_id).exists()
        assert not TenantMembership.objects.filter(id=membership_id).exists()
        
        # Verificar que el usuario NO se eliminó (es global)
        assert User.objects.filter(id=user.id).exists()


@pytest.mark.django_db
class TestDomainIntegrity:
    """Tests específicos para integridad de dominio según arquitectura."""
    
    def test_domain_auto_creation_from_schema_name(self):
        """Test: Dominio se construye automáticamente desde schema_name."""
        # Caso 1: Schema_name simple
        client1 = Client.objects.create(
            nombre="Empresa Simple",
            schema_name="simple"
        )
        domain1 = Domain.objects.filter(tenant=client1, is_primary=True).first()
        assert domain1.domain == "simple.localhost"
        
        # Caso 2: Schema_name con FQDN
        client2 = Client.objects.create(
            nombre="Empresa FQDN",
            schema_name="fqdn.example.com"
        )
        domain2 = Domain.objects.filter(tenant=client2, is_primary=True).first()
        assert domain2.domain == "fqdn.example.com"
    
    def test_domain_uses_tenant_fk(self):
        """Test: Domain usa tenant como FK (convención django-tenants)."""
        client = Client.objects.create(
            nombre="Empresa FK",
            schema_name="fk"
        )
        
        domain = Domain.objects.filter(tenant=client).first()
        
        # [OK] CRÍTICO: Domain debe usar .tenant (NO .client)
        assert hasattr(domain, 'tenant')
        assert domain.tenant == client
        
        # Verificar acceso inverso
        assert domain in client.domains.all()
        assert client.domains.count() >= 1
