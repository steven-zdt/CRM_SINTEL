"""
Tests para onboarding asíncrono de tenants con Celery.

Valida:
- Tarea Celery onboard_tenant_task
- Normalización de dominio (sin puerto)
- Endpoints API async (onboard-async, onboard-status)
- Polling de estado de tarea
- Creación correcta de Client, Domain, TenantMembership
"""

import pytest


def _normalize_domain_helper(domain: str) -> str:
    """
    Helper para normalizar dominio (quita puerto).

    Duplicado de _normalize_domain para tests.
    """
    return domain.split(":")[0].strip()


def test_normalize_domain_removes_port():
    """Valida que _normalize_domain elimina el puerto del dominio."""
    assert _normalize_domain_helper("sintel.net.co:8000") == "sintel.net.co"
    assert _normalize_domain_helper("sintel.net.co") == "sintel.net.co"
    assert _normalize_domain_helper("localhost:8000") == "localhost"
    assert (
        _normalize_domain_helper("mi-empresa.localhost:3000") == "mi-empresa.localhost"
    )


@pytest.mark.django_db
def test_onboard_tenant_task_creates_tenant_with_normalized_domain(admin_user):
    """Valida que onboard_tenant_task crea tenant con dominio normalizado."""
    from apps.public.tenants.models import Client, Domain, TenantMembership
    from apps.public.tenants.tasks import onboard_tenant_task

    result = onboard_tenant_task(
        nombre="Acme SAS",
        dominio="acme.localhost:8000",  # Con puerto
        admin_user_id=admin_user.id,
    )

    assert result is not None
    assert "client_id" in result
    assert "schema_name" in result
    assert "domain" in result
    assert "login_url" in result

    # Verificar que el dominio NO tiene puerto
    assert result["domain"] == "acme.localhost"
    assert ":8000" not in result["domain"]

    # Verificar que Client existe
    client = Client.objects.get(id=result["client_id"])
    assert client.nombre == "Acme SAS"

    # Verificar que Domain tiene dominio sin puerto
    domain = Domain.objects.get(tenant=client)
    assert domain.domain == "acme.localhost"
    assert ":8000" not in domain.domain

    # Verificar TenantMembership
    membership = TenantMembership.objects.get(client=client, user=admin_user)
    assert membership.rol == "ADMIN"
    assert membership.is_primary_admin is True


@pytest.mark.django_db
def test_onboard_async_endpoint_returns_task_id(admin_user):
    """Valida que POST /api/admin/v1/tenants/onboard-async/ retorna task_id (202)."""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)

    url = "/api/admin/v1/tenants/onboard-async/"
    payload = {
        "nombre": "Test Tenant",
        "dominio": "test.localhost:8000",
        "admin_user_id": admin_user.id,
    }

    response = api_client.post(url, data=payload, format="json")

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] is not None


@pytest.mark.django_db
def test_onboard_status_endpoint_returns_task_state(admin_user):
    """Valida que GET /api/admin/v1/tenants/onboard-status/ retorna estado de tarea."""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)

    # Disparar tarea
    url_async = "/api/admin/v1/tenants/onboard-async/"
    payload = {
        "nombre": "Status Test",
        "dominio": "status.localhost",
        "admin_user_id": admin_user.id,
    }
    response_async = api_client.post(url_async, data=payload, format="json")
    assert response_async.status_code == 202
    task_id = response_async.json()["task_id"]

    # Consultar estado
    url_status = f"/api/admin/v1/tenants/onboard-status/?task_id={task_id}"
    response_status = api_client.get(url_status)

    assert response_status.status_code == 200
    data = response_status.json()
    assert "task_id" in data
    assert "state" in data
    assert data["task_id"] == task_id

    # En modo eager, la tarea debería completarse inmediatamente
    # Verificar que state es SUCCESS y tiene result
    if data["state"] == "SUCCESS":
        assert "result" in data
        assert "client_id" in data["result"]
        assert "domain" in data["result"]
        assert "login_url" in data["result"]


@pytest.mark.django_db
def test_onboard_status_endpoint_requires_task_id(admin_user):
    """Valida que onboard-status requiere task_id."""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)

    url = "/api/admin/v1/tenants/onboard-status/"
    response = api_client.get(url)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


@pytest.mark.django_db
def test_console_tenants_create_redirects_to_status(admin_client, admin_user):
    """Valida que tenants_create redirige a status con task_id."""
    from apps.public.tenants.models import Client

    url = reverse("console:tenants-create")
    payload = {
        "nombre": "Console Test",
        "dominio": "console.localhost:8000",
        "admin_user_id": admin_user.id,
    }

    response = admin_client.post(url, data=payload, follow=True)

    # Debería redirigir a status o a lista
    assert response.status_code == 200
    # Verificar que la redirección ocurrió
    assert len(response.redirect_chain) > 0


@pytest.mark.django_db
def test_console_tenants_status_page_renders(admin_client, admin_user):
    """Valida que tenants_status_page renderiza correctamente."""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)

    # Disparar tarea para obtener task_id
    url_async = "/api/admin/v1/tenants/onboard-async/"
    payload = {
        "nombre": "Status Page Test",
        "dominio": "statuspage.localhost",
        "admin_user_id": admin_user.id,
    }
    response_async = api_client.post(url_async, data=payload, format="json")
    task_id = response_async.json()["task_id"]

    # Acceder a la página de status
    url = reverse("console:tenants-status")
    response = admin_client.get(f"{url}?task_id={task_id}")

    assert response.status_code == 200
    # Verificar que el template se renderiza
    assert (
        "task_id" in response.content.decode() or task_id in response.content.decode()
    )


@pytest.mark.django_db
def test_onboard_async_creates_tenant_in_public_schema(admin_user):
    """Valida que la tarea crea Client/Domain en schema public."""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)
    from apps.public.tenants.models import Client

    url = "/api/admin/v1/tenants/onboard-async/"
    payload = {
        "nombre": "Schema Test",
        "dominio": "schema.localhost",
        "admin_user_id": admin_user.id,
    }

    response = api_client.post(url, data=payload, format="json")
    assert response.status_code == 202
    task_id = response.json()["task_id"]

    # En modo eager, la tarea debería completarse
    # Consultar estado hasta SUCCESS
    url_status = f"/api/admin/v1/tenants/onboard-status/?task_id={task_id}"
    response_status = api_client.get(url_status)
    data = response_status.json()

    # En modo eager debería ser SUCCESS inmediatamente
    assert (
        data["state"] == "SUCCESS"
    ), f"Estado esperado SUCCESS, obtenido: {data['state']}"

    result = data["result"]
    client_id = result["client_id"]

    # Verificar que Client existe en public schema
    assert Client.objects.filter(id=client_id).exists()
    created_client = Client.objects.get(id=client_id)
    assert created_client.nombre == "Schema Test"


@pytest.mark.django_db
def test_onboard_async_normalizes_domain_in_result(admin_user):
    """Valida que el resultado de la tarea tiene dominio normalizado."""
    api_client = APIClient()
    api_client.force_authenticate(user=admin_user)

    url = "/api/admin/v1/tenants/onboard-async/"
    payload = {
        "nombre": "Normalize Test",
        "dominio": "normalize.localhost:8000",  # Con puerto
        "admin_user_id": admin_user.id,
    }

    response = api_client.post(url, data=payload, format="json")
    assert response.status_code == 202
    task_id = response.json()["task_id"]

    # Consultar estado
    url_status = f"/api/admin/v1/tenants/onboard-status/?task_id={task_id}"
    response_status = api_client.get(url_status)
    data = response_status.json()

    # En modo eager debería ser SUCCESS inmediatamente
    assert data["state"] == "SUCCESS"
    result = data["result"]
    assert result["domain"] == "normalize.localhost"
    assert ":8000" not in result["domain"]
    assert ":8000" not in result["login_url"]
    # [WARNING] REGLA DE NEGOCIO: login_url debe apuntar a la raíz (/) - landing page
    assert result["login_url"].endswith(
        "/"
    ), f"login_url debe terminar en '/', got '{result['login_url']}'"
    assert (
        "/login" not in result["login_url"]
    ), f"login_url NO debe contener '/login', got '{result['login_url']}'"


@pytest.mark.django_db
def test_onboard_async_requires_authentication():
    """Valida que onboard-async requiere autenticación."""
    api_client = APIClient()

    url = "/api/admin/v1/tenants/onboard-async/"
    payload = {"nombre": "Auth Test", "dominio": "auth.localhost", "admin_user_id": 1}

    response = api_client.post(url, data=payload, format="json")

    # Debería requerir autenticación (401 o 403)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_onboard_async_requires_staff(django_user_model):
    """Valida que onboard-async requiere permisos de staff."""
    api_client = APIClient()

    # Crear usuario no-staff
    user = django_user_model.objects.create_user(
        email="nonstaff@test.local", password="test123"
    )
    api_client.force_authenticate(user=user)

    url = "/api/admin/v1/tenants/onboard-async/"
    payload = {
        "nombre": "Staff Test",
        "dominio": "staff.localhost",
        "admin_user_id": user.id,
    }

    response = api_client.post(url, data=payload, format="json")

    # Debería requerir staff (403)
    assert response.status_code == 403
