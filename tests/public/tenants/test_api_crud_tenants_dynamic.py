import uuid

import pytest
from django.urls import reverse
from rest_framework import status

from apps.public.tenants.api.viewsets import VIEWSETS


def _find_client_viewset_entry():
    """
    Busca el (prefix, viewset, basename) cuyo queryset.model sea 'Client'
    (o por nombre de clase como fallback).
    """
    # Estrategia A: por modelo
    for prefix, viewset, basename in VIEWSETS:
        try:
            model_name = getattr(
                getattr(viewset, "queryset", None), "model", None
            ).__name__
        except Exception:
            model_name = None
        if model_name == "Client":
            return prefix, viewset, basename

    # Estrategia B: por nombre de clase
    for prefix, viewset, basename in VIEWSETS:
        if viewset.__name__.lower().startswith(("client", "tenant")):
            return prefix, viewset, basename

    return None, None, None


@pytest.mark.django_db
def test_tenants_crud_dynamic(api_client, admin_user):
    """
    CRUD dinámico contra el ViewSet real publicado por VIEWSETS.

    No asume rutas antiguas; usa el basename verdadero del router.
    """
    prefix, viewset, basename = _find_client_viewset_entry()
    assert basename, (
        "No se encontró un ViewSet para Client en VIEWSETS. "
        "Asegúrate de registrar (prefix, ClientViewSet, basename='...') en VIEWSETS."
    )

    api_client.force_authenticate(user=admin_user)

    # Rutas resueltas dinámicamente desde basename
    list_url = reverse(f"{basename}-list")

    # Datos mínimos esperados por serializer (ajustar si tu serializer exige otros campos)
    schema = f"t_{uuid.uuid4().hex[:8]}"
    payload = {
        "schema_name": schema,
        "nombre": "Empresa CRUD Dinámica",
    }

    # CREATE
    r = api_client.post(list_url, payload, format="json")
    if r.status_code not in (status.HTTP_201_CREATED, status.HTTP_200_OK):
        # Manejar errores 404/405 correctamente (HttpResponseNotFound no tiene .data)
        error_msg = f"Error {r.status_code}"
        if hasattr(r, "data"):
            error_msg += f": {r.data}"
        elif hasattr(r, "content"):
            error_msg += f": {r.content.decode('utf-8') if isinstance(r.content, bytes) else r.content}"
        pytest.fail(error_msg)

    created_id = (
        r.data.get("id") or r.data.get("pk") or r.data.get("data", {}).get("id")
    )
    assert created_id, f"La respuesta no devolvió ID. Respuesta: {r.data}"

    # LIST
    r = api_client.get(list_url)
    assert r.status_code == status.HTTP_200_OK

    # Soportar paginado DRF (results) o lista directa
    results = (
        r.data.get("results")
        if isinstance(r.data, dict) and "results" in r.data
        else r.data
    )
    assert any(
        (row.get("id") == created_id) for row in (results or [])
    ), f"El tenant creado no aparece en la lista. Respuesta: {r.data}"

    # RETRIEVE
    detail_url = reverse(f"{basename}-detail", args=[created_id])
    r = api_client.get(detail_url)
    assert r.status_code == status.HTTP_200_OK
    assert r.data.get("id") == created_id

    # UPDATE (PATCH)
    r = api_client.patch(detail_url, {"nombre": "Empresa CRUD Editada"}, format="json")
    if r.status_code not in (status.HTTP_200_OK, status.HTTP_202_ACCEPTED):
        error_msg = f"Error {r.status_code}"
        if hasattr(r, "data"):
            error_msg += f": {r.data}"
        elif hasattr(r, "content"):
            error_msg += f": {r.content.decode('utf-8') if isinstance(r.content, bytes) else r.content}"
        pytest.fail(error_msg)
    assert r.data.get("nombre") in ("Empresa CRUD Editada",)
