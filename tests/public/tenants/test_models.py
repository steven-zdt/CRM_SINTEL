"""
Tests de Modelos y Señales para tenants.

Valida la integridad referencial y la "Excepción de Señal".
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import override_settings

from apps.public.tenants.models import Client, Domain, TenantMembership
from tests.public.tenants.factories import (
    ClientFactory,
    DomainFactory,
    TenantMembershipFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestClientModel:
    """Tests para el modelo Client."""

    def test_client_creation(self):
        """Test: Crear un Client básico."""
        client = ClientFactory(nombre="Test Corp", schema_name="testcorp")

        assert client.nombre == "Test Corp"
        assert client.schema_name == "testcorp"
        assert client.on_trial is True
        assert client.auto_create_schema is True

    def test_client_str(self):
        """Test: Verificar __str__ del modelo Client."""
        client = ClientFactory(nombre="Mi Empresa", schema_name="miempresa")

        assert str(client) == "miempresa · Mi Empresa"

    def test_client_clean_normalizes_schema_name(self):
        """Test: clean() normaliza schema_name (strip y lower)."""
        client = ClientFactory.build(schema_name="  TESTCORP  ")
        client.clean()

        assert client.schema_name == "testcorp"

    def test_client_clean_validates_schema_name(self):
        """Test: clean() valida schema_name con caracteres inválidos."""
        client = ClientFactory.build(schema_name="TEST CORP")  # Espacios no permitidos

        with pytest.raises(ValidationError):
            client.clean()

    def test_client_unique_schema_name(self):
        """Test: schema_name debe ser único."""
        ClientFactory(schema_name="testcorp")

        with pytest.raises(IntegrityError):
            ClientFactory(schema_name="testcorp")


@pytest.mark.django_db
class TestDomainModel:
    """Tests para el modelo Domain."""

    def test_domain_creation(self):
        """Test: Crear un Domain básico."""
        client = ClientFactory()
        domain = DomainFactory(tenant=client, domain="testcorp.localhost")

        assert domain.domain == "testcorp.localhost"
        assert domain.is_primary is True
        assert domain.tenant == client

    def test_domain_str(self):
        """Test: Verificar __str__ del modelo Domain."""
        domain = DomainFactory(domain="testcorp.localhost")

        assert str(domain) == "testcorp.localhost"

    def test_domain_uses_tenant_not_client(self):
        """Test CRÍTICO: Domain usa 'tenant' como FK (convención django-tenants)."""
        client = ClientFactory()
        domain = DomainFactory(tenant=client)

        # Verificar que existe el atributo 'tenant'
        assert hasattr(domain, "tenant")
        assert domain.tenant == client

        # Verificar que el ID coincide
        assert domain.tenant.id == client.id

    def test_domain_related_name(self):
        """Test: Verificar related_name 'domains' en Client."""
        client = ClientFactory()
        domain1 = DomainFactory(tenant=client, is_primary=True)
        domain2 = DomainFactory(tenant=client, is_primary=False)

        # Acceder a través de related_name
        domains = client.domains.all()

        assert domain1 in domains
        assert domain2 in domains
        assert domains.count() == 2


@pytest.mark.django_db
class TestSignalException:
    """Tests para la señal post_save (EXCEPCIÓN DE ARQUITECTURA)."""

    def test_signal_creates_domain_automatically(self):
        """Test: Crear un Client y verificar que se creó automáticamente un Domain."""
        client = ClientFactory(schema_name="testcorp")

        # Verificar que existe un Domain creado por la señal
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()

        assert domain is not None
        assert domain.tenant == client
        assert domain.is_primary is True
        # La señal construye el dominio basado en schema_name
        assert domain.domain in [
            "testcorp.localhost",
            "testcorp",
        ]  # Depende de TENANT_DOMAIN_BASE

    def test_signal_creates_domain_with_fqdn(self):
        """Test: Crear Client con schema_name='empresa.com' y verificar que no agregó .localhost."""
        client = ClientFactory(schema_name="empresa.com")

        # Verificar que el dominio es exactamente 'empresa.com' (FQDN)
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()

        assert domain is not None
        assert domain.domain == "empresa.com"
        assert ".localhost" not in domain.domain

    @override_settings(TENANT_DOMAIN_BASE="sintel.net.co")
    def test_signal_creates_domain_with_subdomain(self):
        """Test: Crear Client con schema_name sin punto y verificar construcción de subdominio."""
        client = ClientFactory(schema_name="testcorp")

        # Verificar que el dominio se construyó como subdominio
        domain = Domain.objects.filter(tenant=client, is_primary=True).first()

        assert domain is not None
        assert domain.domain == "testcorp.sintel.net.co"

    def test_signal_only_creates_on_creation(self):
        """Test: La señal solo crea dominio cuando created=True."""
        client = ClientFactory()

        # Contar dominios iniciales
        initial_count = Domain.objects.filter(tenant=client).count()

        # Actualizar el client (NO debe crear otro dominio)
        client.nombre = "Updated Name"
        client.save()

        # Verificar que no se creó otro dominio
        final_count = Domain.objects.filter(tenant=client).count()
        assert final_count == initial_count


@pytest.mark.django_db
class TestTenantMembership:
    """Tests para el modelo TenantMembership."""

    def test_membership_creation(self):
        """Test: Crear un TenantMembership básico."""
        user = UserFactory()
        client = ClientFactory()
        membership = TenantMembershipFactory(client=client, user=user, rol="ADMIN")

        assert membership.client == client
        assert membership.user == user
        assert membership.rol == "ADMIN"
        assert membership.is_primary_admin is False

    def test_membership_unique_together(self):
        """Test: Verificar restricción unique_together (client, user)."""
        user = UserFactory()
        client = ClientFactory()

        # Crear primera membresía
        TenantMembershipFactory(client=client, user=user)

        # Intentar crear segunda membresía (debe fallar)
        with pytest.raises(IntegrityError):
            TenantMembershipFactory(client=client, user=user)

    def test_membership_related_names(self):
        """Test: Verificar related_names en Client y User."""
        user = UserFactory()
        client = ClientFactory()
        membership = TenantMembershipFactory(client=client, user=user)

        # Verificar related_name en Client
        assert membership in client.memberships.all()

        # Verificar related_name en User
        assert membership in user.tenant_memberships.all()

    def test_membership_role_choices(self):
        """Test: Verificar que los roles son válidos."""
        user = UserFactory()
        client = ClientFactory()

        # Roles válidos
        for role in ["ADMIN", "STAFF", "USER"]:
            membership = TenantMembershipFactory(client=client, user=user, rol=role)
            assert membership.rol == role
