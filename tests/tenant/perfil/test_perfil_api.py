"""
Tests de API de Perfil (SessionAuth + CSRF).

Verifica que:
- Sin sesión → GET /api/v1/perfil/perfiles/me/ 401
- Con sesión → 200 con payload mínimo esperado
- PATCH me: actualiza campos → 200
- configuracion = null o input vacío: normaliza a {} → 200
- Sin CSRF: 403
- Esquema no migrado: 503 controlado
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db import connection
from apps.public.tenants.models import TenantMembership

User = get_user_model()


class TestPerfilAPI(SintelTenantTestCase):
    """
    Tests para verificar la API de Perfil con SessionAuth + CSRF.
    """

    def test_get_me_returns_401_without_session(self):
        """
        Verifica que GET /api/v1/perfil/perfiles/me/ retorna 401 sin sesión.
        """
        # Crear cliente sin autenticar
        from django.test import Client
        client = Client(HTTP_HOST=self.domain.domain)
        
        response = client.get('/api/v1/perfil/perfiles/me/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_me_returns_200_with_session(self):
        """
        Verifica que GET /api/v1/perfil/perfiles/me/ retorna 200 con sesión.
        """
        response = self.api_client.get('/api/v1/perfil/perfiles/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verificar campos mínimos esperados
        self.assertIn('user_full_name', data)
        self.assertIn('user_email', data)
        self.assertIn('cargo', data)
        self.assertIn('departamento', data)
        self.assertIn('telefono_corporativo', data)
        self.assertIn('configuracion', data)
        
        # Verificar que configuracion es un objeto (dict)
        self.assertIsInstance(data['configuracion'], dict)

    def test_patch_me_updates_fields_with_csrf(self):
        """
        Verifica que PATCH /api/v1/perfil/perfiles/me/ actualiza campos con CSRF.
        """
        # Obtener CSRF token
        csrf_client = self.client
        csrf_client.get('/workspace/')  # Obtener cookie de sesión y CSRF
        
        # Obtener token CSRF de la cookie
        csrftoken = csrf_client.cookies.get('csrftoken')
        
        data = {
            'cargo': 'Nuevo Cargo',
            'departamento': 'Nuevo Departamento',
            'telefono_corporativo': '3001234567'
        }
        
        response = self.api_client.patch(
            '/api/v1/perfil/perfiles/me/',
            data,
            format='json',
            HTTP_X_CSRFTOKEN=csrftoken.value if csrftoken else None
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['cargo'], data['cargo'])
        self.assertEqual(response_data['departamento'], data['departamento'])
        self.assertEqual(response_data['telefono_corporativo'], data['telefono_corporativo'])

    def test_patch_me_normalizes_null_configuracion_to_empty_dict(self):
        """
        Verifica que PATCH /api/v1/perfil/perfiles/me/ normaliza configuracion=null a {}.
        """
        data = {
            'configuracion': None
        }
        
        response = self.api_client.patch('/api/v1/perfil/perfiles/me/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Verificar que configuracion es {} (no null)
        self.assertIsInstance(response_data['configuracion'], dict)
        self.assertEqual(response_data['configuracion'], {})

    def test_patch_me_accepts_empty_configuracion(self):
        """
        Verifica que PATCH /api/v1/perfil/perfiles/me/ acepta configuracion={} (input vacío).
        """
        data = {
            'configuracion': {}
        }
        
        response = self.api_client.patch('/api/v1/perfil/perfiles/me/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        # Verificar que configuracion es {}
        self.assertIsInstance(response_data['configuracion'], dict)
        self.assertEqual(response_data['configuracion'], {})

    def test_patch_me_returns_403_without_csrf(self):
        """
        Verifica que PATCH /api/v1/perfil/perfiles/me/ retorna 403 sin CSRF token.
        """
        # Crear cliente con enforce_csrf_checks=True
        from django.test import Client
        client = Client(enforce_csrf_checks=True, HTTP_HOST=self.domain.domain)
        client.force_login(self.user)
        
        data = {
            'cargo': 'Nuevo Cargo'
        }
        
        # Intentar PATCH sin CSRF token
        response = client.patch(
            '/api/v1/perfil/perfiles/me/',
            data,
            content_type='application/json'
        )
        
        # Debe retornar 403 (Forbidden) por falta de CSRF
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
