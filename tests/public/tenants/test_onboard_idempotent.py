import pytest
from django.urls import reverse
from rest_framework import status

from apps.public.tenants.models import Client, Domain
from apps.public.tenants.utils import normalize_domain


@pytest.mark.django_db
def test_onboard_idempotent_via_service(django_assert_num_queries):
    """
    Llama directamente al servicio onboard_tenant varias veces con el mismo payload
    y verifica que Client y Domain no se duplican.
    """
    from apps.services.onboarding.empresa_service import onboard_tenant
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admin = User.objects.create_superuser(email="svcadmin@test.local", password="admin123")

    domains_before = Domain.objects.count()
    clients_before = Client.objects.count()

    for _ in range(5):
        client, domain, login_url = onboard_tenant(
            nombre="Empresa Test Service",
            schema_name="empresa_test_service",
            admin_user_id=admin.id,
        )
        assert client.schema_name == "empresa_test_service"
        assert normalize_domain(domain.domain) == f"empresa_test_service.localhost"
        assert login_url.startswith("http")

    assert Client.objects.filter(schema_name="empresa_test_service").count() == 1
    assert Domain.objects.filter(domain="empresa_test_service.localhost").count() == 1
    assert Domain.objects.count() == domains_before + 1
    assert Client.objects.count() == clients_before + 1

