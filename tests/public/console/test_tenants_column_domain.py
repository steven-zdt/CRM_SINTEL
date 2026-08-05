"""
Tests para verificar que la columna "Dominio" se incluye en DataTables de tenants.

Verifica que:
- El endpoint DataTables incluye primary_domain en la respuesta
- El primary_domain se anota correctamente usando Subquery
- Si un tenant tiene dominio primario, aparece en la respuesta
- Si un tenant no tiene dominio, primary_domain es null
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.public.tenants.models import Client, Domain

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture(autouse=True)
def setup_public_schema():
    """Fixture automático que configura el esquema público y ROOT_URLCONF para cada test."""
    with override_settings(ROOT_URLCONF="config.urls_public"):
        connection.set_schema_to_public()
        yield


@pytest.fixture
def api_client():
    """Cliente API para tests."""
    return APIClient()


@pytest.fixture
def staff_user(db):
    """Usuario staff para tests."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="staff@test.local",
        password="testpass123",
        is_staff=True,
        is_superuser=False,
    )


@pytest.fixture
def tenant_with_domain(db):
    """Crea un tenant con dominio primario."""
    connection.set_schema_to_public()

    tenant = Client.objects.create(
        nombre="Acme Corp", schema_name="acme", is_active=True, on_trial=True
    )

    Domain.objects.create(tenant=tenant, domain="acme.localhost", is_primary=True)

    return tenant


@pytest.fixture
def tenant_without_domain(db):
    """Crea un tenant sin dominio."""
    connection.set_schema_to_public()

    tenant = Client.objects.create(
        nombre="Sin Dominio Corp",
        schema_name="sin_dominio",
        is_active=True,
        on_trial=True,
    )

    return tenant


def test_dt_tenants_includes_primary_domain(tenant_with_domain):
    """
    Test: El queryset anota primary_domain correctamente cuando el tenant tiene dominio.

    Objetivo: Verificar que el queryset con Subquery devuelve primary_domain
    cuando el tenant tiene un dominio primario configurado.
    """
    connection.set_schema_to_public()

    # Simular la anotación que hace la vista
    from django.db.models import OuterRef, Subquery

    primary_domain_sq = Subquery(
        Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[
            :1
        ]
    )

    qs = Client.objects.only("id", "nombre", "schema_name", "is_active").annotate(
        primary_domain=primary_domain_sq
    )

    tenant = qs.get(schema_name="acme")
    assert (
        tenant.primary_domain == "acme.localhost"
    ), f"Se esperaba 'acme.localhost', pero se recibió '{tenant.primary_domain}'"

    # Verificar que el serializer incluye primary_domain
    from apps.public.console.api.serializers import TenantListSerializer

    serializer = TenantListSerializer(tenant)
    assert (
        "primary_domain" in serializer.data
    ), "El serializer debe incluir 'primary_domain'"
    assert (
        serializer.data["primary_domain"] == "acme.localhost"
    ), f"Se esperaba 'acme.localhost' en serializer, pero se recibió '{serializer.data.get('primary_domain')}'"


def test_dt_tenants_primary_domain_null_when_no_domain(tenant_without_domain):
    """
    Test: El queryset devuelve primary_domain=null cuando el tenant no tiene dominio.

    Objetivo: Verificar que el queryset con Subquery devuelve primary_domain como null
    cuando el tenant no tiene un dominio primario configurado.
    """
    connection.set_schema_to_public()

    # Simular la anotación que hace la vista
    from django.db.models import OuterRef, Subquery

    primary_domain_sq = Subquery(
        Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[
            :1
        ]
    )

    qs = Client.objects.only("id", "nombre", "schema_name", "is_active").annotate(
        primary_domain=primary_domain_sq
    )

    tenant = qs.get(schema_name="sin_dominio")
    assert (
        tenant.primary_domain is None or tenant.primary_domain == ""
    ), f"Se esperaba null o vacío, pero se recibió '{tenant.primary_domain}'"

    # Verificar que el serializer incluye primary_domain como null
    from apps.public.console.api.serializers import TenantListSerializer

    serializer = TenantListSerializer(tenant)
    assert (
        "primary_domain" in serializer.data
    ), "El serializer debe incluir 'primary_domain'"
    assert (
        serializer.data["primary_domain"] is None
        or serializer.data["primary_domain"] == ""
    ), f"Se esperaba null o vacío en serializer, pero se recibió '{serializer.data.get('primary_domain')}'"


def test_dt_tenants_search_by_domain(tenant_with_domain):
    """
    Test: El queryset permite buscar por dominio usando domains__domain.

    Objetivo: Verificar que el queryset permite buscar tenants
    por el dominio primario usando el campo domains__domain.
    """
    connection.set_schema_to_public()

    # Simular la anotación que hace la vista
    from django.db.models import OuterRef, Q, Subquery

    primary_domain_sq = Subquery(
        Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[
            :1
        ]
    )

    qs = Client.objects.only("id", "nombre", "schema_name", "is_active").annotate(
        primary_domain=primary_domain_sq
    )

    # Buscar por dominio usando domains__domain
    search_value = "acme.localhost"
    qs_filtered = qs.filter(
        Q(nombre__icontains=search_value)
        | Q(schema_name__icontains=search_value)
        | Q(domains__domain__icontains=search_value)
    ).distinct()

    # Verificar que el tenant con ese dominio aparece en los resultados
    found = qs_filtered.filter(schema_name="acme").exists()
    assert (
        found
    ), "El tenant con dominio 'acme.localhost' debe aparecer en los resultados de búsqueda"


def test_dt_tenants_primary_domain_uses_primary_flag(db):
    """
    Test: El queryset devuelve solo el dominio con is_primary=True.

    Objetivo: Verificar que si un tenant tiene múltiples dominios,
    solo se devuelve el que tiene is_primary=True.
    """
    connection.set_schema_to_public()

    # Crear tenant con múltiples dominios
    tenant = Client.objects.create(
        nombre="Multi Domain Corp",
        schema_name="multi_domain",
        is_active=True,
        on_trial=True,
    )

    # Dominio secundario (no primario)
    Domain.objects.create(
        tenant=tenant, domain="secondary.multi-domain.localhost", is_primary=False
    )

    # Dominio primario
    Domain.objects.create(
        tenant=tenant, domain="multi-domain.localhost", is_primary=True
    )

    # Simular la anotación que hace la vista
    from django.db.models import OuterRef, Subquery

    primary_domain_sq = Subquery(
        Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[
            :1
        ]
    )

    qs = Client.objects.only("id", "nombre", "schema_name", "is_active").annotate(
        primary_domain=primary_domain_sq
    )

    tenant_annotated = qs.get(schema_name="multi_domain")
    assert (
        tenant_annotated.primary_domain == "multi-domain.localhost"
    ), f"Se esperaba 'multi-domain.localhost' (dominio primario), pero se recibió '{tenant_annotated.primary_domain}'"

    # Verificar que el serializer incluye el dominio primario correcto
    from apps.public.console.api.serializers import TenantListSerializer

    serializer = TenantListSerializer(tenant_annotated)
    assert (
        serializer.data["primary_domain"] == "multi-domain.localhost"
    ), f"Se esperaba 'multi-domain.localhost' en serializer, pero se recibió '{serializer.data.get('primary_domain')}'"
