"""
Tests de seguridad: CSRF Protection.

Valida que las peticiones POST requieran token CSRF válido.
"""

import pytest
from django.test import Client
from django.test.utils import override_settings


@pytest.mark.django_db
def test_post_without_csrf_is_forbidden():
    """
    POST sin CSRF debe ser rechazado (403 o 405 según endpoint).
    """
    with override_settings(ALLOWED_HOSTS=["miempresa.localhost"]):
        c = Client(HTTP_HOST="miempresa.localhost")
        # Intentar POST sin CSRF token
        resp = c.post("/api/v1/core/auth/logout/", data={})
        # Según tu endpoint, pero nunca debe ejecutar acción sin CSRF
        assert resp.status_code in (403, 405)


@pytest.mark.django_db
def test_post_with_csrf_allowed():
    """
    POST con CSRF token válido debe ser permitido (si el endpoint existe).
    """
    with override_settings(ALLOWED_HOSTS=["miempresa.localhost"]):
        c = Client(HTTP_HOST="miempresa.localhost")
        # Obtener CSRF token primero
        resp = c.get("/")
        csrftoken = c.cookies.get("csrftoken")

        if csrftoken:
            # Intentar POST con CSRF token
            resp = c.post(
                "/api/v1/core/auth/logout/", data={}, HTTP_X_CSRFTOKEN=csrftoken.value
            )
            # No debe ser 403 si el token es válido (puede ser 200, 204, 401, etc.)
            assert resp.status_code != 403
