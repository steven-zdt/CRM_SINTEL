import pytest
from django.urls import reverse
from rest_framework import status

from apps.public.tenants.models import Client, Domain
from apps.public.tenants.utils import normalize_domain


@pytest.mark.django_db
def test_admin_create_read_update_tenant(api_client, admin_user):
    """
    CRUD básico vía API Admin para Client (tenant).

    - Crea un tenant vía POST /api/admin/v1/tenants/
    - Lista y verifica presencia en resultados paginados
    - Actualiza nombre vía PATCH
    """
    api_client.force_authenticate(user=admin_user)

    # F29-002: router basename real es "tenant" desde el refactor Fase
    # 5-BIS (commit 60d8a33), no "admin-tenants".
    list_url = reverse("tenant-list")

    payload = {
        "schema_name": "crt",
        "nombre": "Crt",
        # Dominio se infiere por servicio/onboarding; aquí solo probamos CRUD Client
    }

    # CREATE
    resp = api_client.post(list_url, payload, format="json")
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
    tenant_id = resp.data["id"]

    # READ list (paginado)
    resp = api_client.get(list_url)
    assert resp.status_code == status.HTTP_200_OK
    assert "results" in resp.data
    assert any(it["id"] == tenant_id for it in resp.data["results"])

    # DETAIL
    detail_url = reverse("tenant-detail", args=[tenant_id])
    resp = api_client.get(detail_url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["id"] == tenant_id
    assert resp.data["nombre"] == "Crt"

    # UPDATE (PATCH)
    resp = api_client.patch(detail_url, {"nombre": "Crt Edit"}, format="json")
    assert resp.status_code in (status.HTTP_200_OK, status.HTTP_202_ACCEPTED)

    # Verificar en BD
    client = Client.objects.get(id=tenant_id)
    assert client.nombre == "Crt Edit"


@pytest.mark.django_db
def test_admin_onboard_idempotent(api_client, admin_user, settings):
    """
    Acción onboard debe ser idempotente:
    - Repetir el mismo payload no debe crear nuevos Client/Domain.
    """
    api_client.force_authenticate(user=admin_user)
    url = reverse("tenant-onboard")

    schema_name = "empresa_test"
    raw_domain = "https://www.test.localhost:8000/admin/"
    fqdn = normalize_domain(raw_domain)

    payload = {
        "nombre": "Empresa Test",
        "schema_name": schema_name,
        "admin_user_id": admin_user.id,
    }

    for _ in range(5):
        resp = api_client.post(url, payload, format="json")
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
        assert "domain" in resp.data
        assert normalize_domain(resp.data["domain"]) == fqdn
        assert resp.data["login_url"].startswith("http")

    # Verificar que no se crearon duplicados
    assert Client.objects.filter(schema_name=schema_name).count() == 1
    assert Domain.objects.filter(domain=fqdn).count() == 1


@pytest.mark.django_db
def test_admin_onboard_domain_conflict(api_client, admin_user):
    """
    Si se intenta onboard con un dominio ya asociado a otro tenant,
    el servicio debe responder 409/ValidationError.
    """
    api_client.force_authenticate(user=admin_user)
    url = reverse("tenant-onboard")

    # Crear tenant A
    c1 = Client.objects.create(schema_name="c1", nombre="C1")
    d1 = Domain.objects.create(tenant=c1, domain="conflict.localhost", is_primary=True)

    payload = {
        "nombre": "Empresa B",
        "schema_name": "c2",
        "admin_user_id": admin_user.id,
    }

    # Forzar que el servicio derive el mismo dominio conflict.localhost
    from django.conf import settings

    settings.TENANT_DOMAIN_BASE = "localhost"

    resp = api_client.post(url, payload, format="json")
    assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)
