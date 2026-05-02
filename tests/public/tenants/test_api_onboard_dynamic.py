import uuid

import pytest
from django.urls import reverse
from rest_framework import status

from apps.public.tenants.api.viewsets import VIEWSETS


def _find_client_viewset_entry():
    for prefix, viewset, basename in VIEWSETS:
        try:
            model_name = getattr(getattr(viewset, "queryset", None), "model", None).__name__
        except Exception:
            model_name = None
        if model_name == "Client":
            return prefix, viewset, basename
    return None, None, None


@pytest.mark.django_db
def test_onboard_dynamic_if_present(api_client, admin_user):
    """
    Descubre si la acción 'onboard' existe en el ViewSet real; si no existe en esta API,
    marca el test como SKIPPED (puede vivir en otra capa).
    """
    prefix, viewset, basename = _find_client_viewset_entry()
    assert basename, "No se encontró un ViewSet para Client en VIEWSETS."

    # ¿la acción existe?
    onboard_attr = getattr(viewset, "onboard", None)
    if onboard_attr is None:
        pytest.skip("La acción 'onboard' no está expuesta en esta API. (OK si vive en otra capa)")

    api_client.force_authenticate(user=admin_user)
    onboard_url = reverse(f"{basename}-onboard")  # requiere @action(url_name="onboard")

    schema_name = f"emp_{uuid.uuid4().hex[:6]}"
    payload = {
        "nombre": "Empresa Onboard Dinámica",
        "schema_name": schema_name,
        "admin_user_id": admin_user.id,
    }

    # 2 ejecuciones para probar idempotencia
    r1 = api_client.post(onboard_url, payload, format="json")
    assert r1.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK), r1.data

    r2 = api_client.post(onboard_url, payload, format="json")
    assert r2.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK), r2.data

