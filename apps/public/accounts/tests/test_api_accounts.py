"""
Tests de API para la app accounts.

Verifica:
- CRUD completo de User
- Endpoint me/ (perfil del usuario autenticado)
- Email único
- Username autogenerado desde email
- Paginación y filtros
"""

from rest_framework import status

from apps.config.tests.base_public import PublicAPITestCase
from apps.public.accounts.models import User


class UserViewSetTests(PublicAPITestCase):
    """Tests para UserViewSet (CRUD completo)."""

    def setUp(self):
        """Configuración inicial."""
        super().setUp()

        # Crear usuarios de prueba
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            first_name="Usuario",
            last_name="Uno",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            is_staff=False,
        )

    def test_list_users(self):
        """Test: GET /api/public/v1/users/ devuelve lista paginada."""
        response = self.json("get", "/api/public/v1/users/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertPaginationFormat(response.data)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_detail_user(self):
        """Test: GET /api/public/v1/users/{id}/ devuelve detalle."""
        response = self.json("get", f"/api/public/v1/users/{self.user1.id}/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user1.id)
        self.assertEqual(response.data["email"], "user1@example.com")

    def test_create_user(self):
        """Test: POST /api/public/v1/users/ crea nuevo usuario."""
        data = {
            "email": "newuser@example.com",
            "password": "testpass123",
            "first_name": "Nuevo",
            "last_name": "Usuario",
        }
        response = self.json("post", "/api/public/v1/users/", data)
        self.assertJSONResponse(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "newuser@example.com")
        # Verificar que el username se generó automáticamente
        self.assertIsNotNone(response.data["username"])

        # Verificar que el usuario se creó en la BD
        user = User.objects.get(email="newuser@example.com")
        self.assertIsNotNone(user.username)

    def test_create_user_duplicate_email(self):
        """Test: No se puede crear usuario con email duplicado."""
        data = {
            "email": "user1@example.com",  # Email ya existente
            "password": "testpass123",
        }
        response = self.json("post", "/api/public/v1/users/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user(self):
        """Test: PUT /api/public/v1/users/{id}/ actualiza usuario."""
        data = {
            "email": "user1@example.com",
            "first_name": "Actualizado",
            "last_name": "Usuario",
        }
        response = self.json("put", f"/api/public/v1/users/{self.user1.id}/", data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Actualizado")

    def test_partial_update_user(self):
        """Test: PATCH /api/public/v1/users/{id}/ actualiza parcialmente."""
        data = {"first_name": "Parcial"}
        response = self.json("patch", f"/api/public/v1/users/{self.user1.id}/", data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Parcial")
        # Verificar que otros campos no cambiaron
        self.assertEqual(response.data["email"], "user1@example.com")

    def test_delete_user(self):
        """Test: DELETE /api/public/v1/users/{id}/ elimina usuario."""
        user_id = self.user2.id
        response = self.json("delete", f"/api/public/v1/users/{user_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verificar que el usuario fue eliminado
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_me_endpoint(self):
        """Test: GET /api/public/v1/users/me/ devuelve perfil del usuario autenticado."""
        # Autenticar como user1
        self.client.force_authenticate(user=self.user1)
        response = self.json("get", "/api/public/v1/users/me/")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user1.id)
        self.assertEqual(response.data["email"], "user1@example.com")

    def test_me_endpoint_update(self):
        """Test: PUT /api/public/v1/users/me/ actualiza perfil propio."""
        self.client.force_authenticate(user=self.user1)
        data = {
            "email": "user1@example.com",
            "first_name": "Mi Nombre",
        }
        response = self.json("put", "/api/public/v1/users/me/", data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Mi Nombre")

    def test_filter_by_is_active(self):
        """Test: Filtrar por is_active."""
        # Desactivar user2
        self.user2.is_active = False
        self.user2.save()

        response = self.json("get", "/api/public/v1/users/?is_active=true")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        for result in response.data["results"]:
            self.assertTrue(result["is_active"])

    def test_search_by_email(self):
        """Test: Búsqueda por email."""
        response = self.json("get", "/api/public/v1/users/?search=user1@example.com")
        self.assertJSONResponse(response, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)
        self.assertIn("user1@example.com", response.data["results"][0]["email"])

    def test_requires_admin(self):
        """Test: Solo administradores pueden gestionar usuarios."""
        # Autenticar como usuario no admin
        self.client.force_authenticate(user=self.user2)
        response = self.json("get", "/api/public/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
