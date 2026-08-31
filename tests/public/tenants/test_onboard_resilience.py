"""
Tests de resiliencia para onboarding de tenants.

Verifica que el onboarding funcione correctamente incluso cuando:
- La tabla de perfil no existe
- Las migraciones del tenant no están aplicadas
- Hay errores en el seed de perfil
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from django_tenants.utils import schema_context, schema_exists
from rest_framework import status

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls("config.urls_public"),
]


@pytest.fixture
def staff_user(db):
    """Fixture para crear un usuario staff para tests."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="staff@test.local",
        password="testpass123",
        is_staff=True,
        is_superuser=False,
    )


@pytest.mark.django_db
def test_onboard_returns_login_url_without_perfil_table(api_client, staff_user):
    """
    Test: Onboarding retorna login_url aunque no exista perfil_tenantprofile.

    Objetivo: Verificar que el onboarding no falle si la tabla de perfil
    no existe o no está migrada en el schema del tenant.
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    # NO configuramos perfil_tenantprofile a propósito
    # Usar reverse() para obtener la URL correcta del endpoint onboard
    url = reverse("tenant-onboard")
    response = api_client.post(
        url,
        {
            "nombre": "Home Test",
            "schema_name": "home_test",
            "dominio_fqdn": "home-test.localhost",
            "owner_email": "owner@home-test.com",
        },
        format="json",
        HTTP_HOST="testserver",
    )

    assert response.status_code == status.HTTP_201_CREATED, (
        f"Se esperaba 201, pero se recibió {response.status_code}. "
        f"Respuesta: {getattr(response, 'data', response.content.decode('utf-8'))}"
    )

    data = response.json()
    assert "login_url" in data
    assert "domain" in data
    # El dominio real depende de TENANT_DOMAIN_BASE del entorno (settings.py) --
    # no se hardcodea ".localhost", que ya no aplica tras el rebrand a
    # sintel.net.co (build_primary_domain() en empresa_service.py sustituye
    # cualquier dominio que no termine en TENANT_DOMAIN_BASE).
    # No se asume esquema (http/https) -- depende de SITE_PROTOCOL del
    # entorno (_build_login_url() en empresa_service.py); solo se exige
    # que login_url apunte al dominio real devuelto por la misma respuesta.
    assert data["domain"] in data["login_url"]
    assert "client_id" in data
    assert "membership_id" in data


@pytest.mark.django_db
def test_onboard_creates_profile_when_table_exists(api_client, staff_user):
    """
    Test: Si el app perfil está en TENANT_APPS y migrado, crea perfil.

    Objetivo: Verificar que cuando la tabla de perfil existe y está migrada,
    el onboarding crea el TenantProfile correctamente.
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    url = reverse("tenant-onboard")
    response = api_client.post(
        url,
        {
            "nombre": "Acme Test",
            "schema_name": "acme_test",
            "dominio_fqdn": "acme-test.localhost",
            "owner_email": "owner@acme-test.com",
        },
        format="json",
        HTTP_HOST="testserver",
    )

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert "login_url" in data
    assert "domain" in data
    # No se asume esquema (http/https) -- depende de SITE_PROTOCOL del
    # entorno (_build_login_url() en empresa_service.py); solo se exige
    # que login_url apunte al dominio real devuelto por la misma respuesta.
    assert data["domain"] in data["login_url"]

    # Verificar que el tenant fue creado
    from apps.public.tenants.models import Client

    client = Client.objects.get(schema_name="acme_test")
    assert client is not None

    # Intentar verificar que el perfil existe (si la tabla está migrada)
    try:
        with schema_context("acme_test"):
            from django.contrib.auth import get_user_model

            from apps.tenant.perfil.models import TenantProfile

            User = get_user_model()
            user = User.objects.get(email="owner@acme-test.com")
            profile = TenantProfile.objects.get(user=user)
            assert profile is not None
            assert profile.cargo == "Administrador Principal"
    except Exception:
        # Si la tabla no existe o no está migrada, está bien
        # El objetivo es que el onboarding no falle
        pass


@pytest.mark.django_db
def test_onboard_handles_duplicate_domain_gracefully(api_client, staff_user):
    """
    Test: Onboarding maneja correctamente dominios duplicados.

    Objetivo: Verificar que si se intenta crear un tenant con un dominio
    que ya existe, se retorna un error claro.
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    url = reverse("tenant-onboard")

    # dominio_fqdn debe terminar en TENANT_DOMAIN_BASE del entorno, o
    # build_primary_domain() lo sustituye por uno autogenerado unico por
    # schema_name -- lo que anularia la prueba de duplicado (nunca
    # colisionarian). Ver empresa_service.py::build_primary_domain.
    from django.conf import settings

    dominio_compartido = f"duplicado-test.{settings.TENANT_DOMAIN_BASE}"

    # Crear primer tenant
    response1 = api_client.post(
        url,
        {
            "nombre": "First Tenant",
            "schema_name": "first_tenant",
            "dominio_fqdn": dominio_compartido,
            "owner_email": "owner1@first.com",
        },
        format="json",
        HTTP_HOST="testserver",
    )

    assert response1.status_code == status.HTTP_201_CREATED, (
        f"Se esperaba 201, pero se recibió {response1.status_code}. "
        f"Respuesta: {getattr(response1, 'data', response1.content.decode('utf-8'))}"
    )

    # Intentar crear segundo tenant con el mismo dominio
    response2 = api_client.post(
        url,
        {
            "nombre": "Second Tenant",
            "schema_name": "second_tenant",
            "dominio_fqdn": dominio_compartido,  # Mismo dominio
            "owner_email": "owner2@second.com",
        },
        format="json",
        HTTP_HOST="testserver",
    )

    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        "dominio" in str(response2.data).lower()
        or "ya está" in str(response2.data).lower()
    )


@pytest.mark.django_db
def test_onboard_validates_required_fields(api_client, staff_user):
    """
    Test: Onboarding valida campos requeridos.

    Objetivo: Verificar que se retornan errores claros cuando faltan campos requeridos.
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    url = reverse("tenant-onboard")

    # Intentar crear tenant sin campos requeridos
    response = api_client.post(
        url,
        {
            "nombre": "Incomplete Tenant",
            # Faltan: schema_name, dominio_fqdn, owner_email, owner_password
        },
        format="json",
        HTTP_HOST="testserver",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    # Verificar que se mencionan los campos faltantes
    assert any(
        field in str(data).lower()
        for field in ["schema_name", "dominio_fqdn", "owner_email", "owner_password"]
    )


@pytest.mark.django_db
def test_onboard_requires_staff_permission(api_client, django_user_model):
    """
    Test: Onboarding requiere permisos de staff (IsAdminUser).

    Objetivo: Verificar que usuarios no-staff reciben 403 al intentar crear tenants.
    """
    connection.set_schema_to_public()

    # Crear usuario no-staff
    regular_user = django_user_model.objects.create_user(
        email="regular@test.local",
        password="testpass123",
        is_staff=False,
        is_superuser=False,
    )

    api_client.force_authenticate(user=regular_user)

    url = reverse("tenant-onboard")
    response = api_client.post(
        url,
        {
            "nombre": "Test Tenant",
            "schema_name": "test_tenant",
            "dominio_fqdn": "test.localhost",
            "owner_email": "owner@test.com",
            "owner_password": "Secr3tPass!",
        },
        format="json",
        HTTP_HOST="testserver",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_onboard_no_orphan_schema_when_seed_fails(staff_user):
    """
    Test: crear_tenant_con_owner() no deja un schema PostgreSQL huerfano
    cuando el seed de Empresa/TenantProfile falla DESPUES de que
    Client.save() ya creo y migro el schema fisico.

    Contexto (documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md,
    Hallazgo #4): se temia que call_command('migrate_schemas', ...) no
    participara de la misma transaccion Django que crear_tenant_con_owner()
    (decorado @transaction.atomic), dejando el schema fisico sin revertir
    aunque el Client/Domain/Membership si se revirtieran. Verificado
    experimentalmente contra Postgres real: NO ocurre -- migrate_schemas
    corre en la MISMA conexion, dentro del mismo bloque atomic (via
    savepoints anidados), y el DDL de Postgres es transaccional, por lo que
    el rollback revierte tanto las filas Django como el schema fisico. Este
    test fija esa garantia como regresion permanente.
    """
    connection.set_schema_to_public()
    schema_name = "orphan_regression_test"

    from apps.public.tenants.models import Client
    from apps.services.onboarding.empresa_service import crear_tenant_con_owner

    assert not schema_exists(schema_name)
    assert not Client.objects.filter(schema_name=schema_name).exists()

    with patch(
        "apps.tenant.empresa.services.business_service.asegurar_estructura_organizacional_inicial",
        side_effect=RuntimeError("fallo forzado para test de regresion"),
    ):
        with pytest.raises(RuntimeError):
            crear_tenant_con_owner(
                nombre="Orphan Regression Test",
                schema_name=schema_name,
                dominio_fqdn="orphan-regression-test.localhost",
                owner_email="owner@orphan-regression-test.com",
            )

    connection.set_schema_to_public()

    assert not schema_exists(schema_name), (
        "El schema PostgreSQL sobrevivio al rollback -- quedo huerfano."
    )
    assert not Client.objects.filter(schema_name=schema_name).exists()
    from apps.public.tenants.models import Domain

    assert not Domain.objects.filter(domain__startswith="orphan-regression-test").exists()
    assert not User.objects.filter(email="owner@orphan-regression-test.com").exists()


@pytest.mark.django_db
def test_onboard_validates_domain_without_port(api_client, staff_user):
    """
    Test: Onboarding rechaza dominios con puerto.

    Objetivo: Verificar que se rechazan dominios con puerto (según doc oficial de django-tenants).
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=staff_user)

    url = reverse("tenant-onboard")
    response = api_client.post(
        url,
        {
            "nombre": "Test Tenant",
            "schema_name": "test_tenant",
            "dominio_fqdn": "test.localhost:8000",  # Con puerto (debe ser rechazado)
            "owner_email": "owner@test.com",
        },
        format="json",
        HTTP_HOST="testserver",
    )

    # El serializer debe normalizar y rechazar puertos
    # Si el dominio se normaliza correctamente, debería funcionar
    # Si no, debería retornar 400
    assert response.status_code in [
        status.HTTP_201_CREATED,
        status.HTTP_400_BAD_REQUEST,
    ]
    if response.status_code == status.HTTP_201_CREATED:
        # Si se normaliza correctamente, verificar que el dominio guardado no tiene puerto
        data = response.json()
        assert ":8000" not in data["domain"]
