import pytest
from django.urls import reverse

from tests.tenant.base_test import SintelTenantTestCase


class TestEmpresaCrud(SintelTenantTestCase):
    """
    Smoke test CRUD mínimo de Empresa en un esquema tenant.

    Usa SintelTenantTestCase para asegurar:
    - Schema correcto
    - HTTP_HOST correcto
    - APIClient autenticado
    """

    @pytest.mark.django_db
    def test_empresa_crud_on_tenant(self):
        # Nombre de la vista/route para el ViewSet de Empresa en tenant
        # Ajusta si el basename es distinto (ej: 'empresa-empresa')
        list_url = reverse("empresa-list")

        # CREATE
        r = self.api_client.post(
            list_url,
            {"razon_social": "Mi Empresa S.A.S."},
            format="json",
        )
        assert r.status_code in (200, 201)

        # LIST
        r = self.api_client.get(list_url)
        assert r.status_code == 200
        assert "results" in r.data
        assert r.data["count"] >= 1
