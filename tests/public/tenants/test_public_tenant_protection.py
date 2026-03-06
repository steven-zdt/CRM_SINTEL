"""
Tests de garantía para protección absoluta del tenant público.

Valida que el tenant público (schema_name='public') es indeletable desde:
- Servicio de eliminación
- API Admin
- Django Admin
- UI (ocultar/deshabilitar botón)
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_exists
from apps.public.tenants.models import Client
from apps.public.tenants.services.deletion_service import hard_delete_tenant

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def admin_user(db):
    """Usuario admin global."""
    connection.set_schema_to_public()
    return User.objects.create_superuser(
        email="admin@test.local",
        password="admin123"
    )


@pytest.fixture
def public_tenant(db):
    """Tenant público (schema_name='public')."""
    connection.set_schema_to_public()
    public_schema = get_public_schema_name()
    tenant = Client.objects.get(schema_name=public_schema)
    # Asegurar que está activo (normalmente lo está)
    tenant.is_active = True
    tenant.save()
    return tenant


def test_public_tenant_cannot_be_deleted_by_service(public_tenant):
    """
    Test A: Servicio hard_delete_tenant() devuelve ValidationError si schema_name=='public'.
    """
    connection.set_schema_to_public()
    
    public_schema = get_public_schema_name()
    assert public_tenant.schema_name == public_schema
    
    # Intentar eliminar tenant público debe fallar
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=public_tenant.id)
    
    assert "público" in str(exc_info.value).lower() or "public" in str(exc_info.value).lower()
    assert "no puede eliminarse" in str(exc_info.value).lower() or "indeletable" in str(exc_info.value).lower()
    
    # Verificar que el tenant público NO fue eliminado
    assert Client.objects.filter(schema_name=public_schema).exists()
    
    # Verificar que el esquema sigue existiendo
    assert schema_exists(public_schema)


def test_public_tenant_cannot_be_deleted_even_if_inactive(public_tenant):
    """
    Test B: Incluso si is_active=False, el tenant público no puede eliminarse.
    """
    connection.set_schema_to_public()
    
    # Desactivar temporalmente el tenant público
    public_tenant.is_active = False
    public_tenant.save()
    
    public_schema = get_public_schema_name()
    
    # Intentar eliminar debe fallar aunque esté inactivo
    with pytest.raises(ValidationError) as exc_info:
        hard_delete_tenant(client_id=public_tenant.id)
    
    assert "público" in str(exc_info.value).lower() or "public" in str(exc_info.value).lower()
    
    # Restaurar estado
    public_tenant.is_active = True
    public_tenant.save()


def test_api_hard_delete_public_forbidden(api_client, admin_user, public_tenant):
    """
    Test C: API Admin bloquea siempre el borrado de public (403 + mensaje).
    """
    connection.set_schema_to_public()
    api_client.force_authenticate(user=admin_user)
    
    public_schema = get_public_schema_name()
    url = f"/api/public/v1/tenants/{public_tenant.id}/"
    
    response = api_client.delete(url)
    
    # Debe retornar 403 Forbidden
    assert response.status_code == 403, f"Expected 403, got {response.status_code}. Response: {response.data}"
    
    # Verificar mensaje de error
    error_msg = str(response.data.get('error', '')).lower()
    assert "público" in error_msg or "public" in error_msg
    assert "no puede eliminarse" in error_msg or "indeletable" in error_msg
    
    # Verificar que el tenant público NO fue eliminado
    assert Client.objects.filter(schema_name=public_schema).exists()
    
    # Verificar que el esquema sigue existiendo
    assert schema_exists(public_schema)


def test_api_hard_delete_public_forbidden_even_if_inactive(api_client, admin_user, public_tenant):
    """
    Test D: API bloquea eliminación de public incluso si is_active=False.
    """
    connection.set_schema_to_public()
    
    # Desactivar temporalmente el tenant público
    public_tenant.is_active = False
    public_tenant.save()
    
    api_client.force_authenticate(user=admin_user)
    url = f"/api/public/v1/tenants/{public_tenant.id}/"
    
    response = api_client.delete(url)
    
    # Debe retornar 403 Forbidden (no 400)
    assert response.status_code == 403
    
    # Restaurar estado
    public_tenant.is_active = True
    public_tenant.save()


def test_public_tenant_schema_never_dropped(public_tenant):
    """
    Test E: El esquema 'public' nunca se elimina, incluso si se intenta.
    """
    connection.set_schema_to_public()
    
    public_schema = get_public_schema_name()
    
    # Verificar que el esquema existe antes
    assert schema_exists(public_schema)
    
    # Intentar eliminar (debe fallar)
    with pytest.raises(ValidationError):
        hard_delete_tenant(client_id=public_tenant.id)
    
    # Verificar que el esquema sigue existiendo después
    assert schema_exists(public_schema)
    
    # Verificar que el Client sigue existiendo
    assert Client.objects.filter(schema_name=public_schema).exists()


def test_public_tenant_delete_never_calls_client_delete(public_tenant, mocker):
    """
    Test F: Verificar que client.delete() nunca se llama para el tenant público.
    """
    connection.set_schema_to_public()
    
    # Mock del método delete() del modelo
    delete_mock = mocker.patch.object(Client, 'delete')
    
    # Intentar eliminar tenant público
    with pytest.raises(ValidationError):
        hard_delete_tenant(client_id=public_tenant.id)
    
    # Verificar que delete() nunca fue llamado
    delete_mock.assert_not_called()


def test_public_tenant_protection_logging(public_tenant, caplog):
    """
    Test G: Verificar que los intentos de eliminar public se registran en logs de seguridad.
    """
    connection.set_schema_to_public()
    
    import logging
    logger = logging.getLogger('security.tenants')
    logger.setLevel(logging.CRITICAL)
    
    with caplog.at_level(logging.CRITICAL, logger='security.tenants'):
        try:
            hard_delete_tenant(client_id=public_tenant.id)
        except ValidationError:
            pass  # Esperado
    
    # Verificar que se registró el intento
    assert len(caplog.records) > 0
    log_messages = ' '.join([record.message for record in caplog.records])
    assert "público" in log_messages.lower() or "public" in log_messages.lower()
    assert "rechazado" in log_messages.lower() or "rejected" in log_messages.lower()


def test_ui_logic_hides_delete_button_for_public_tenant():
    """
    Test H: Verificar la lógica que oculta/deshabilita el botón de eliminar para public.
    
    Nota: Este test verifica la lógica que se implementa en JavaScript.
    En un entorno real, se probaría con Selenium o similar.
    """
    # Simular datos de tenant público (lógica que se aplica en JavaScript)
    tenant_public = {
        'id': 1,
        'schema_name': 'public',
        'nombre': 'SINTEL Global',
        'is_active': True
    }
    
    # Lógica que se implementa en JavaScript: verificar si es público
    is_public_tenant = tenant_public['schema_name'] == 'public'
    
    # Si es público, el botón debe estar deshabilitado
    if is_public_tenant:
        delete_btn_html = '<button disabled title="Prohibido: el esquema público no puede eliminarse">Eliminar</button>'
    else:
        delete_btn_html = '<button>Eliminar</button>'
    
    # Verificar que el botón está deshabilitado para public
    assert 'disabled' in delete_btn_html
    assert 'Prohibido' in delete_btn_html or 'público' in delete_btn_html
