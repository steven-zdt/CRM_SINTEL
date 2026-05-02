"""
Pruebas de humo para verificar el patrón Singleton de Empresa.

[WARNING] PATRÓN SINGLETON: Solo una empresa por tenant.
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status
from apps.tenant.empresa.models import Empresa


class TestEmpresaSingletonAPI(SintelTenantTestCase):
    """
    Pruebas para verificar el patrón Singleton de Empresa.
    """

    def test_get_list_empty(self):
        """
        Verifica que GET /api/v1/empresas/ retorna [] cuando no hay empresa.
        """
        response = self.api_client.get("/api/v1/empresas/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_post_create_empresa(self):
        """
        Verifica que POST /api/v1/empresas/ crea una empresa y retorna 201.
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
        
        response = self.api_client.post("/api/v1/empresas/", data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertIn('id', response_data)
        self.assertEqual(response_data['razon_social'], data['razon_social'])
        self.assertEqual(response_data['nit'], data['nit'])
        self.assertIn('dv', response_data)  # DV calculado automáticamente

    def test_get_list_after_create(self):
        """
        Verifica que GET /api/v1/empresas/ retorna array con 1 elemento después de crear.
        """
        # Crear empresa
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data, format='json')
        
        # Verificar lista
        response = self.api_client.get("/api/v1/empresas/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data_list = response.json()
        self.assertIsInstance(data_list, list)
        self.assertEqual(len(data_list), 1)
        self.assertEqual(data_list[0]['razon_social'], "Empresa de Prueba S.A.")

    def test_post_create_second_empresa_409(self):
        """
        Verifica que POST /api/v1/empresas/ retorna 409 si ya existe una empresa (singleton).
        """
        # Crear primera empresa
        data1 = {
            "razon_social": "Primera Empresa S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto1@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data1, format='json')
        
        # Intentar crear segunda empresa
        data2 = {
            "razon_social": "Segunda Empresa S.A.",
            "nit": "900654321",
            "direccion": "Calle 456 #78-90",
            "telefono": "6098765432",
            "email_contacto": "contacto2@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        response = self.api_client.post("/api/v1/empresas/", data2, format='json')
        
        # Debe retornar 409 Conflict
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        response_data = response.json()
        self.assertIn('detail', response_data)
        self.assertIn('Ya existe una Empresa', response_data['detail'])

    def test_patch_update_empresa(self):
        """
        Verifica que PATCH /api/v1/empresas/{id}/ actualiza la empresa y retorna 200.
        """
        # Crear empresa
        data_create = {
            "razon_social": "Empresa Original S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "original@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        create_response = self.api_client.post("/api/v1/empresas/", data_create, format='json')
        empresa_id = create_response.json()['id']
        
        # Actualizar empresa
        data_update = {
            "razon_social": "Empresa Actualizada S.A.",
            "telefono": "6011111111",
        }
        response = self.api_client.patch(f"/api/v1/empresas/{empresa_id}/", data_update, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['razon_social'], "Empresa Actualizada S.A.")
        self.assertEqual(response_data['telefono'], "6011111111")
        # Campos no actualizados deben mantenerse
        self.assertEqual(response_data['nit'], data_create['nit'])

    def test_put_update_empresa(self):
        """
        Verifica que PUT /api/v1/empresas/{id}/ actualiza la empresa completamente y retorna 200.
        """
        # Crear empresa
        data_create = {
            "razon_social": "Empresa Original S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "original@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        create_response = self.api_client.post("/api/v1/empresas/", data_create, format='json')
        empresa_id = create_response.json()['id']
        
        # Actualizar empresa completamente
        data_update = {
            "razon_social": "Empresa Actualizada S.A.",
            "nit": "900654321",
            "direccion": "Calle Nueva #12-34",
            "telefono": "6011111111",
            "email_contacto": "actualizada@prueba.com",
            "regimen_tributario": "No Responsable",
            "moneda": "USD",
        }
        response = self.api_client.put(f"/api/v1/empresas/{empresa_id}/", data_update, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['razon_social'], "Empresa Actualizada S.A.")
        self.assertEqual(response_data['nit'], "900654321")
        self.assertEqual(response_data['telefono'], "6011111111")

    def test_unauthorized_access_403(self):
        """
        Verifica que usuarios sin membresía en el tenant reciben 403.
        """
        from rest_framework.test import APIClient
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Crear usuario sin membresía
        user_sin_membresia = User.objects.create_user(
            username='sin_membresia',
            email='sin_membresia@test.com',
            password='testpass123'
        )
        
        # Cliente autenticado pero sin membresía
        client = APIClient()
        client.force_authenticate(user=user_sin_membresia)
        
        response = client.get("/api/v1/empresas/")
        
        # Debe retornar 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mi_empresa_action(self):
        """
        Verifica que GET /api/v1/empresas/mi-empresa/ retorna la empresa del tenant.
        """
        # Crear empresa
        data = {
            "razon_social": "Empresa de Prueba S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@prueba.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data, format='json')
        
        # Obtener mi empresa
        response = self.api_client.get("/api/v1/empresas/mi-empresa/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('empresa', response_data)
        self.assertIsNotNone(response_data['empresa'])
        self.assertEqual(response_data['empresa']['razon_social'], "Empresa de Prueba S.A.")

    def test_mi_empresa_action_empty(self):
        """
        Verifica que GET /api/v1/empresas/mi-empresa/ retorna null si no hay empresa.
        """
        response = self.api_client.get("/api/v1/empresas/mi-empresa/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('empresa', response_data)
        self.assertIsNone(response_data['empresa'])
