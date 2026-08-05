"""
Fixtures para tests de tenants.

Incluye fixtures comunes para tests de onboarding y CRUD.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings


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
