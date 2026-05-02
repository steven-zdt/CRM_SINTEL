"""
Tests E2E/Smoke integrados del workspace.

Verifica flujos completos:
- Flujo Perfil: anónimo 401 → login → GET me 200 → PATCH me 200
- Flujo Empresa: mi-empresa 404 → POST 201 (ADMIN) → POST de nuevo 409 → PATCH 200
- No romper UI si algún módulo retorna 404/409/403
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import connection
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class TestWorkspaceSmokeE2E(SintelTenantTestCase):
    """
    Tests E2E/Smoke integrados del workspace.
    """

    def test_perfil_flow_e2e(self):
        """
        Flujo completo de Perfil: anónimo 401 → login → GET me 200 → PATCH me 200.
        """
        # 1. Verificar que sin sesión retorna 401
        from django.test import Client
        anon_client = Client(HTTP_HOST=self.domain.domain)
        
        response = anon_client.get('/api/v1/perfil/perfiles/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # 2. Con sesión, GET me debe retornar 200
        response = self.api_client.get('/api/v1/perfil/perfiles/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perfil_data = response.json()
        self.assertIn('user_full_name', perfil_data)
        self.assertIn('configuracion', perfil_data)
        
        # 3. PATCH me debe actualizar y retornar 200
        update_data = {
            'cargo': 'Cargo E2E Test',
            'departamento': 'Departamento E2E',
            'configuracion': {'test': True}
        }
        
        response = self.api_client.patch('/api/v1/perfil/perfiles/me/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_data = response.json()
        self.assertEqual(updated_data['cargo'], update_data['cargo'])
        self.assertEqual(updated_data['departamento'], update_data['departamento'])
        self.assertEqual(updated_data['configuracion'], update_data['configuracion'])

    def test_empresa_flow_e2e(self):
        """
        Flujo completo de Empresa: mi-empresa 404 → POST 201 (ADMIN) → POST de nuevo 409 → PATCH 200.
        """
        # 1. GET mi-empresa debe retornar 404 cuando no hay empresa
        response = self.api_client.get('/api/v1/empresas/mi-empresa/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # 2. POST create debe retornar 201 la primera vez
        data = {
            'razon_social': 'Empresa E2E Test S.A.',
            'nit': '900123456',
            'direccion': 'Calle E2E 123',
            'telefono': '6012345678',
            'email_contacto': 'e2e@test.com',
            'regimen_tributario': 'Responsable de IVA',
            'moneda': 'COP'
        }
        
        response = self.api_client.post('/api/v1/empresas/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        empresa_data = response.json()
        empresa_id = empresa_data['id']
        
        # 3. POST create de nuevo debe retornar 409 (singleton)
        response = self.api_client.post('/api/v1/empresas/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        
        # 4. GET mi-empresa ahora debe retornar 200
        response = self.api_client.get('/api/v1/empresas/mi-empresa/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. PATCH debe actualizar y retornar 200
        update_data = {
            'razon_social': 'Empresa E2E Actualizada S.A.',
            'direccion': 'Nueva Dirección E2E'
        }
        
        response = self.api_client.patch(f'/api/v1/empresas/{empresa_id}/', update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_data = response.json()
        self.assertEqual(updated_data['razon_social'], update_data['razon_social'])
        self.assertEqual(updated_data['direccion'], update_data['direccion'])

    def test_workspace_handles_404_gracefully(self):
        """
        Verifica que el workspace no se rompe si algún módulo retorna 404.
        """
        # El workspace debe estar accesible incluso si algunos módulos fallan
        response = self.client.get('/workspace/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que el template se renderiza correctamente
        self.assertContains(response, 'workspace', status_code=200)
        self.assertContains(response, 'id="sidebar"', status_code=200)

    def test_workspace_handles_403_gracefully(self):
        """
        Verifica que el workspace no se rompe si algún módulo retorna 403.
        """
        # Crear usuario con rol USER (sin permisos de escritura en Empresa)
        connection.set_schema_to_public()
        user_user = User.objects.create_user(
            email='user@test.sintel.local',
            username='user',
            password='testpass123',
            is_active=True
        )
        
        TenantMembership.objects.create(
            client=self.tenant,
            user=user_user,
            rol='USER',
            is_active=True
        )
        
        connection.set_schema(self.tenant.schema_name)
        
        # El workspace debe estar accesible para USER
        from django.test import Client
        user_client = Client(HTTP_HOST=self.domain.domain)
        user_client.force_login(user_user)
        
        response = user_client.get('/workspace/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que el template se renderiza correctamente
        self.assertContains(response, 'workspace', status_code=200)

    def test_workspace_handles_409_gracefully(self):
        """
        Verifica que el workspace no se rompe si Empresa retorna 409 (singleton).
        """
        # Crear empresa primero
        data = {
            'razon_social': 'Empresa Singleton Test S.A.',
            'nit': '900123456',
            'direccion': 'Calle Singleton 123',
            'telefono': '6012345678',
            'email_contacto': 'singleton@test.com',
            'regimen_tributario': 'Responsable de IVA',
            'moneda': 'COP'
        }
        
        response = self.api_client.post('/api/v1/empresas/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Intentar crear segunda empresa (debe retornar 409)
        response = self.api_client.post('/api/v1/empresas/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        
        # El workspace debe seguir accesible
        response = self.client.get('/workspace/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'workspace', status_code=200)

    def test_perfil_configuracion_null_normalization_e2e(self):
        """
        Verifica que el flujo E2E normaliza configuracion=null a {} correctamente.
        """
        # 1. PATCH con configuracion=null debe normalizar a {}
        data = {
            'configuracion': None
        }
        
        response = self.api_client.patch('/api/v1/perfil/perfiles/me/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perfil_data = response.json()
        self.assertIsInstance(perfil_data['configuracion'], dict)
        self.assertEqual(perfil_data['configuracion'], {})
        
        # 2. GET debe retornar configuracion como {}
        response = self.api_client.get('/api/v1/perfil/perfiles/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        perfil_data = response.json()
        self.assertIsInstance(perfil_data['configuracion'], dict)
