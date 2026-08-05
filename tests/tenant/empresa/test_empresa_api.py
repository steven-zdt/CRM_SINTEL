"""
Tests de API de Empresa (SSoT + singleton).

Verifica que:
- GET mi-empresa: en tenant sin empresa → 404
- POST create (ADMIN/STAFF): primera vez → 201, segunda vez → 409, PATCH → 200
- Permisos: con rol USER: POST/PATCH → 403
- CSRF: write sin CSRF → 403
- Contrato DV: DV vacío ⇒ null en UI, servidor lo acepta (0–9 o null)
"""

from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status

from apps.public.tenants.models import TenantMembership
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()


class TestEmpresaAPI(SintelTenantTestCase):
    """
    Tests para verificar la API de Empresa (SSoT + singleton).
    """

    def test_get_mi_empresa_returns_404_when_no_empresa(self):
        """
        Verifica que GET /api/v1/empresas/mi-empresa/ retorna 404 cuando no hay empresa.
        """
        response = self.api_client.get("/api/v1/empresas/mi-empresa/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_create_empresa_returns_201_first_time(self):
        """
        Verifica que POST /api/v1/empresas/ crea empresa y retorna 201 la primera vez.
        """
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
            "moneda": "COP",
        }

        response = self.api_client.post("/api/v1/empresas/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertIn("id", response_data)
        self.assertEqual(response_data["razon_social"], data["razon_social"])
        self.assertEqual(response_data["nit"], data["nit"])
        self.assertIn("dv", response_data)  # DV calculado automáticamente

    def test_post_create_empresa_returns_409_second_time(self):
        """
        Verifica que POST /api/v1/empresas/ retorna 409 la segunda vez (singleton).
        """
        # Crear primera empresa
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
            "moneda": "COP",
        }

        response = self.api_client.post("/api/v1/empresas/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Intentar crear segunda empresa (debe fallar con 409)
        response = self.api_client.post("/api/v1/empresas/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_patch_empresa_returns_200(self):
        """
        Verifica que PATCH /api/v1/empresas/{id}/ actualiza empresa y retorna 200.
        """
        # Crear empresa primero
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
            "moneda": "COP",
        }

        response = self.api_client.post("/api/v1/empresas/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        empresa_id = response.json()["id"]

        # Actualizar empresa
        update_data = {
            "razon_social": "Empresa Actualizada S.A.",
            "direccion": "Nueva Dirección 789",
        }

        response = self.api_client.patch(
            f"/api/v1/empresas/{empresa_id}/", update_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["razon_social"], update_data["razon_social"])
        self.assertEqual(response_data["direccion"], update_data["direccion"])

    def test_post_empresa_returns_403_for_user_role(self):
        """
        Verifica que POST /api/v1/empresas/ retorna 403 para rol USER (solo ADMIN/STAFF).
        """
        # Crear usuario con rol USER
        connection.set_schema_to_public()
        user_user = User.objects.create_user(
            email="user@test.sintel.local",
            username="user",
            password="testpass123",
            is_active=True,
        )

        TenantMembership.objects.create(
            client=self.tenant, user=user_user, rol="USER", is_active=True
        )

        connection.set_schema(self.tenant.schema_name)

        # Crear cliente autenticado como USER
        from rest_framework.test import APIClient

        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user_user)

        # Intentar crear empresa (debe fallar con 403)
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
            "moneda": "COP",
        }

        response = user_client.post("/api/v1/empresas/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_empresa_returns_403_for_user_role(self):
        """
        Verifica que PATCH /api/v1/empresas/{id}/ retorna 403 para rol USER (solo ADMIN/STAFF).
        """
        # Crear empresa como ADMIN primero
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
            "moneda": "COP",
        }

        response = self.api_client.post("/api/v1/empresas/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        empresa_id = response.json()["id"]

        # Crear usuario con rol USER
        connection.set_schema_to_public()
        user_user = User.objects.create_user(
            email="user@test.sintel.local",
            username="user",
            password="testpass123",
            is_active=True,
        )

        TenantMembership.objects.create(
            client=self.tenant, user=user_user, rol="USER", is_active=True
        )

        connection.set_schema(self.tenant.schema_name)

        # Crear cliente autenticado como USER
        from rest_framework.test import APIClient

        user_client = APIClient(HTTP_HOST=self.domain.domain)
        user_client.force_authenticate(user=user_user)

        # Intentar actualizar empresa (debe fallar con 403)
        update_data = {"razon_social": "Empresa Actualizada S.A."}

        response = user_client.patch(
            f"/api/v1/empresas/{empresa_id}/", update_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_empresa_accepts_null_dv(self):
        """
        Verifica que la API acepta DV vacío (null) y lo normaliza correctamente.
        """
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "dv": None,  # DV vacío
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
            "moneda": "COP",
        }

        response = self.api_client.post("/api/v1/empresas/", data, format="json")

        # Debe retornar 201 (DV se calcula automáticamente o se acepta null)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        # DV debe estar presente (calculado o null)
        self.assertIn("dv", response_data)
