"""
Tests CRUD de usuarios vía API (API-First).

Verifica que:
- POST /api/admin/v1/accounts/users/ crea usuarios correctamente
- GET /api/admin/v1/accounts/users/ lista usuarios
- PATCH /api/admin/v1/accounts/users/{id}/ actualiza usuarios
- DELETE /api/admin/v1/accounts/users/{id}/ elimina usuarios
- Requiere IsAdminUser (401/403 si no está autenticado)
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls('config.urls_public'),  # Usar ROOT_URLCONF del esquema público
]


@pytest.fixture
def api_client():
    """Cliente API para tests."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Usuario admin global."""
    connection.set_schema_to_public()
    return User.objects.create_superuser(
        email="admin@test.local",
        password="admin123"
    )


@pytest.fixture
def regular_user(db):
    """Usuario regular (no staff)."""
    connection.set_schema_to_public()
    return User.objects.create_user(
        email="regular@test.local",
        password="regular123",
        is_staff=False
    )


def test_create_user_requires_admin(api_client, admin_user, regular_user):
    """Test: Crear usuario requiere IsAdminUser."""
    connection.set_schema_to_public()
    from django.urls import reverse
    
    # Sin autenticación → 401
    response = api_client.post(
        reverse('user-list'),
        {
            'email': 'new@test.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'User'
        },
        format='json'
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    
    # Usuario regular (no staff) → 403
    api_client.force_authenticate(user=regular_user)
    response = api_client.post(
        reverse('user-list'),
        {
            'email': 'new@test.com',
            'password': 'testpass123',
        },
        format='json'
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Admin → 201
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        reverse('user-list'),
        {
            'email': 'new@test.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'User'
        },
        format='json'
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['email'] == 'new@test.com'
    assert 'password' not in response.data  # Password nunca se expone


def test_create_user_success(api_client, admin_user):
    """Test: Crear usuario exitosamente."""
    connection.set_schema_to_public()
    from django.urls import reverse
    api_client.force_authenticate(user=admin_user)
    
    initial_count = User.objects.count()
    
    response = api_client.post(
        reverse('user-list'),
        {
            'email': 'testuser@example.com',
            'password': 'securepass123',
            'first_name': 'Test',
            'last_name': 'User',
            'is_staff': False,
            'is_active': True
        },
        format='json'
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.count() == initial_count + 1
    
    user = User.objects.get(email='testuser@example.com')
    assert user.first_name == 'Test'
    assert user.last_name == 'User'
    assert user.is_staff is False
    assert user.is_active is True
    # Verificar que el password fue hasheado (no texto plano)
    assert user.password != 'securepass123'
    assert user.check_password('securepass123') is True


def test_create_user_duplicate_email(api_client, admin_user):
    """Test: No permite crear usuario con email duplicado."""
    connection.set_schema_to_public()
    from django.urls import reverse
    api_client.force_authenticate(user=admin_user)
    
    # Crear primer usuario
    User.objects.create_user(email='existing@test.com', password='pass123')
    
    # Intentar crear otro con el mismo email
    response = api_client.post(
        reverse('user-list'),
        {
            'email': 'existing@test.com',
            'password': 'pass123'
        },
        format='json'
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in str(response.data.get('error', '')).lower() or 'ya existe' in str(response.data.get('error', '')).lower()


def test_list_users_requires_admin(api_client, admin_user, regular_user):
    """Test: Listar usuarios requiere IsAdminUser."""
    connection.set_schema_to_public()
    from django.urls import reverse
    
    # Sin autenticación → 401/403
    response = api_client.get(reverse('user-list'))
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    
    # Usuario regular → 403
    api_client.force_authenticate(user=regular_user)
    response = api_client.get(reverse('user-list'))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Admin → 200
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(reverse('user-list'))
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data or isinstance(response.data, list)


def test_update_user_success(api_client, admin_user):
    """Test: Actualizar usuario exitosamente."""
    connection.set_schema_to_public()
    from django.urls import reverse
    api_client.force_authenticate(user=admin_user)
    
    # Crear usuario
    user = User.objects.create_user(
        email='update@test.com',
        password='oldpass123',
        first_name='Old',
        last_name='Name'
    )
    
    # Actualizar
    response = api_client.patch(
        reverse('user-detail', args=[user.id]),
        {
            'first_name': 'New',
            'last_name': 'Name',
            'is_staff': True
        },
        format='json'
    )
    
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.first_name == 'New'
    assert user.last_name == 'Name'
    assert user.is_staff is True


def test_update_user_password(api_client, admin_user):
    """Test: Actualizar password hashea correctamente."""
    connection.set_schema_to_public()
    from django.urls import reverse
    api_client.force_authenticate(user=admin_user)
    
    # Crear usuario
    user = User.objects.create_user(
        email='passupdate@test.com',
        password='oldpass123'
    )
    old_password_hash = user.password
    
    # Actualizar password
    response = api_client.patch(
        reverse('user-detail', args=[user.id]),
        {
            'password': 'newpass123'
        },
        format='json'
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert 'password' not in response.data  # Password nunca se expone
    
    user.refresh_from_db()
    # El hash debe cambiar
    assert user.password != old_password_hash
    # Debe poder autenticarse con la nueva contraseña
    assert user.check_password('newpass123') is True
    assert user.check_password('oldpass123') is False


def test_delete_user_success(api_client, admin_user):
    """Test: Eliminar usuario exitosamente."""
    connection.set_schema_to_public()
    from django.urls import reverse
    api_client.force_authenticate(user=admin_user)
    
    # Crear usuario
    user = User.objects.create_user(
        email='delete@test.com',
        password='pass123'
    )
    user_id = user.id
    
    # Eliminar
    response = api_client.delete(reverse('user-detail', args=[user_id]))
    
    assert response.status_code in (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK)
    assert not User.objects.filter(id=user_id).exists()
