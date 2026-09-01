"""
Fixtures para tests de tenants.

Incluye fixtures comunes para tests de onboarding y CRUD.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django_tenants.utils import get_public_schema_name


@pytest.fixture(autouse=True)
def celery_eager():
    """
    Configura Celery en modo eager para pruebas deterministas.

    Las tareas se ejecutan síncronamente, sin necesidad de worker.

    Este fixture usa override_settings solo cuando Django está configurado
    (tests con @pytest.mark.django_db). Para tests sin DB, simplemente yield.
    """
    try:
        # Intentar usar override_settings solo si Django está configurado
        from django.conf import settings

        _ = settings.DATABASES  # Esto fallará si Django no está configurado
    except Exception:
        # Django no está configurado, yield sin override
        yield
        return

    # Django está configurado, aplicar Celery eager
    try:
        with override_settings(
            CELERY_TASK_ALWAYS_EAGER=True,
            CELERY_TASK_EAGER_PROPAGATES=True,
        ):
            yield
    except Exception:
        # Si hay error durante teardown, simplemente yield sin cleanup
        yield


@pytest.fixture
def admin_user(db):
    """Fixture que crea un usuario administrador."""
    User = get_user_model()
    user = User.objects.create_superuser(email="admin@test.local", password="admin123")
    return user


@pytest.fixture
def admin_client(db, admin_user):
    """Fixture que crea un cliente Django autenticado como admin."""
    from django.test import Client

    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def api_client():
    """Fixture para APIClient de DRF."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def public_tenant(db):
    """Garantiza que exista el Client(schema_name='public') en la BD de test.

    Ninguna migración de apps/public/tenants/migrations/ siembra este
    registro: en un entorno de desarrollo normal existe porque
    setup_public_tenant/create_public_tenant ya se corrió alguna vez contra
    una BD persistente, pero una BD de test creada desde cero (--create-db)
    no lo tiene. get_or_create evita depender de ese estado heredado.
    """
    from apps.public.tenants.models import Client

    connection.set_schema_to_public()
    public_schema = get_public_schema_name()
    client, _ = Client.objects.get_or_create(
        schema_name=public_schema,
        defaults={"nombre": "Public Schema", "is_active": True, "on_trial": False},
    )
    return client
