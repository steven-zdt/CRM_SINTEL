"""
Tests de seguridad: Host Header Attack.

Valida que ALLOWED_HOSTS filtre correctamente hosts no permitidos.
"""

import pytest
from django.test import Client
from django.test.utils import override_settings


@pytest.mark.django_db
def test_invalid_host_rejected():
    """
    ALLOWED_HOSTS debe filtrar host no permitidos.

    Django puede responder 400 (DisallowedHost) o 404 si el middleware atrapa antes.
    """
    with override_settings(ALLOWED_HOSTS=["valid.localhost"]):
        c = Client(HTTP_HOST="evil.example.com")
        resp = c.get("/")
        # Django puede responder 400 (DisallowedHost) o 404 si tu middleware atrapa antes.
        assert resp.status_code in (400, 404)


@pytest.mark.django_db
def test_valid_host_accepted():
    """
    ALLOWED_HOSTS debe permitir hosts válidos.
    """
    with override_settings(ALLOWED_HOSTS=["valid.localhost", "sintel.net.co"]):
        c = Client(HTTP_HOST="valid.localhost")
        resp = c.get("/")
        # No debe ser 400/404 si el host es válido
        assert resp.status_code not in (400, 404)
