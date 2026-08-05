import pytest

from apps.public.tenants.models import Client, Domain
from apps.public.tenants.utils import normalize_domain


@pytest.mark.django_db
def test_normalize_domain_removes_protocol_www_path_and_port():
    raw = "HTTPS://WWW.CLIENTE.LOCALHOST:8000/admin/"
    assert normalize_domain(raw) == "cliente.localhost"


@pytest.mark.django_db
def test_unique_primary_per_tenant_constraint():
    client = Client.objects.create(schema_name="c1", nombre="C1")
    Domain.objects.create(tenant=client, domain="c1.localhost", is_primary=True)

    # Segundo primario para el mismo tenant debe violar UniqueConstraint
    with pytest.raises(Exception):
        Domain.objects.create(tenant=client, domain="c1b.localhost", is_primary=True)


@pytest.mark.django_db
def test_domain_global_uniqueness():
    c1 = Client.objects.create(schema_name="c1", nombre="C1")
    Domain.objects.create(tenant=c1, domain="x.localhost", is_primary=True)

    c2 = Client.objects.create(schema_name="c2", nombre="C2")

    # Mismo FQDN para otro tenant debe violar unicidad global de domain
    with pytest.raises(Exception):
        Domain.objects.create(tenant=c2, domain="x.localhost", is_primary=True)
