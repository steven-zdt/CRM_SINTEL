"""
Tests para verificar que el tenant público no puede eliminarse.

Verifica que:
- El servicio hard_delete_tenant rechaza eliminar el tenant público
- Se lanza ValidationError con mensaje apropiado
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from apps.public.tenants.models import Client
from apps.public.tenants.services.deletion_service import hard_delete_tenant

pytestmark = [
    pytest.mark.django_db,
]


@pytest.fixture
def public_tenant(db):
    """Obtener o crear el tenant público."""
    connection.set_schema_to_public()
    tenant, created = Client.objects.get_or_create(
        schema_name="public",
        defaults={"nombre": "Tenant Público", "is_active": True, "on_trial": False},
    )
    return tenant


def test_service_forbids_public_delete(public_tenant):
    """Test: El servicio hard_delete_tenant rechaza eliminar el tenant público."""
    connection.set_schema_to_public()

    # Intentar eliminar el tenant público debe lanzar ValidationError
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=public_tenant.id, actor_user_id=None)

    # Verificar que el mensaje de error menciona "público"
    error_msg = str(exc_info.value)
    assert (
        "público" in error_msg.lower() or "public" in error_msg.lower()
    ), f"El mensaje de error debe mencionar 'público' o 'public'. Mensaje: {error_msg}"


def test_service_forbids_public_delete_with_actor(public_tenant):
    """Test: El servicio rechaza eliminar el tenant público incluso con actor_user_id."""
    connection.set_schema_to_public()

    # Intentar eliminar el tenant público con actor_user_id debe lanzar ValidationError
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=public_tenant.id, actor_user_id=1)

    error_msg = str(exc_info.value)
    assert "público" in error_msg.lower() or "public" in error_msg.lower()
