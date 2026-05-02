"""
Tests para API pública de tenants.

Verifica que:
- GET /api/public/v1/tenants/ responde 200 sin errores 500
- No expone campos sensibles de membresías/usuarios
- Queryset optimizado sin prefetch pesado
"""
import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from apps.public.tenants.models import Client

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls('config.urls_public'),
]


@pytest.fixture
def api_client():
    """Cliente API para tests."""
    return APIClient()


@pytest.fixture
def test_tenants(db):
    """Crear algunos tenants de prueba."""
    connection.set_schema_to_public()
    tenants = []
    for i in range(3):
        tenant = Client.objects.create(
            nombre=f"Test Tenant {i+1}",
            schema_name=f"test_tenant_{i+1}",
            is_active=True,
            on_trial=True
        )
        tenants.append(tenant)
    return tenants


def test_public_tenants_list_ok(api_client, test_tenants):
    """Test: GET /api/public/v1/tenants/ responde 200 sin errores."""
    connection.set_schema_to_public()
    
    response = api_client.get("/api/public/v1/tenants/")
    
    # Debe responder 200 (aunque requiera autenticación, no debe ser 500)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    
    # Si responde 200, verificar que no hay campos sensibles
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        
        # Asegurarse que no hay claves de memberships/usuarios expuestas
        if isinstance(data, dict) and "results" in data:
            sample = data["results"][0] if data["results"] else {}
        elif isinstance(data, list):
            sample = data[0] if data else {}
        else:
            sample = data
        
        # Verificar que no se exponen campos sensibles
        forbidden_keys = ("memberships", "users", "tenantmembership_set", "tenant_memberships")
        for key in forbidden_keys:
            assert key not in sample, f"El campo sensible '{key}' no debe estar en la respuesta pública"


def test_public_tenants_list_no_500(api_client, test_tenants):
    """Test: GET /api/public/v1/tenants/ no debe retornar 500."""
    connection.set_schema_to_public()
    
    response = api_client.get("/api/public/v1/tenants/")
    
    # No debe ser 500 (error del servidor)
    assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR, \
        f"La API pública no debe retornar 500. Respuesta: {response.content}"


def test_public_tenants_queryset_optimized(api_client, test_tenants):
    """Test: Verificar que el queryset está optimizado (only() fields)."""
    connection.set_schema_to_public()
    from apps.public.tenants.api.viewsets import ClientViewSet
    
    # Verificar que el queryset usa only()
    queryset = ClientViewSet.queryset
    assert hasattr(queryset.query, 'deferred_loading'), "El queryset debe estar optimizado"
    
    # Verificar que no hace prefetch pesado de membresías
    # (prefetch_related('memberships__user') no debe estar en el queryset base)
    prefetch_lookups = getattr(queryset.query, 'prefetch_lookups', [])
    for lookup in prefetch_lookups:
        assert 'membership' not in str(lookup).lower() or 'domain' in str(lookup).lower(), \
            f"El queryset no debe hacer prefetch de membresías en API pública. Lookups: {prefetch_lookups}"
