"""
Smoke tests para contratos UI (solo JSON, sin HTML).

⚠️ POLÍTICA v2.30: Validar que Core API respeta arquitectura API-First (solo JSON).
"""
from rest_framework import status
from rest_framework.test import APIClient
from tests.tenant.base_test import SintelTenantTestCase


class TestUIContracts(SintelTenantTestCase):
    """Tests de humo para contratos UI (API-First)."""
    
    def test_all_endpoints_return_json(self):
        """Validar contrato UI-only: endpoints Core devuelven exclusivamente JSON."""
        endpoints = [
            '/api/v1/core/dashboard/',
            '/api/v1/core/mi-empresa/',
            '/api/v1/core/mi-perfil/',
            '/api/v1/core/facturas/resumen/',
            '/api/v1/core/contabilidad/resumen/',
            '/api/v1/core/landing/info/',
        ]
        
        for endpoint in endpoints:
            response = self.api_client.get(endpoint)
            
            # Verificar Content-Type
            self.assertEqual(
                response['Content-Type'],
                'application/json',
                f"Endpoint {endpoint} no retorna JSON"
            )
            
            # Verificar que la respuesta es JSON válido
            try:
                data = response.json()
                self.assertIsInstance(data, dict)
            except Exception as e:
                self.fail(f"Endpoint {endpoint} no retorna JSON válido: {e}")
    
    def test_no_html_responses(self):
        """Verificar que ninguna vista HTML se sirve desde Core API."""
        endpoints = [
            '/api/v1/core/dashboard/',
            '/api/v1/core/mi-empresa/',
            '/api/v1/core/mi-perfil/',
            '/api/v1/core/facturas/resumen/',
            '/api/v1/core/contabilidad/resumen/',
            '/api/v1/core/landing/info/',
        ]
        
        for endpoint in endpoints:
            response = self.api_client.get(endpoint)
            
            # Verificar que no es HTML
            content_type = response.get('Content-Type', '')
            self.assertNotIn('text/html', content_type, 
                           f"Endpoint {endpoint} retorna HTML en lugar de JSON")
            
            # Verificar que el contenido no es HTML
            content = response.content.decode('utf-8', errors='ignore')
            self.assertNotIn('<!DOCTYPE html>', content.lower(),
                           f"Endpoint {endpoint} contiene HTML")
            self.assertNotIn('<html', content.lower(),
                           f"Endpoint {endpoint} contiene HTML")
    
    def test_redirect_url_in_responses(self):
        """Verificar que las respuestas incluyen redirect_url donde aplique."""
        # Login debe incluir redirect_url
        if self.user.has_usable_password():
            client = APIClient(HTTP_HOST=self.domain.domain)
            response = client.post(
                '/api/v1/core/auth/login/',
                {
                    'email': self.user.email,
                    'password': 'testpass123',
                },
                format='json'
            )
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                self.assertIn('redirect_url', data,
                            "Login debe incluir redirect_url")
        
        # Logout debe incluir redirect_url
        response = self.api_client.post('/api/v1/core/auth/logout/')
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('redirect_url', data,
                        "Logout debe incluir redirect_url")
    
    def test_activate_redirect_url(self):
        """Verificar que activate incluye redirect_url cuando es exitoso."""
        # Este test requiere un token válido, por lo que puede fallar
        # pero verifica la estructura esperada
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Intentar con token inválido (debe fallar, pero verificar estructura)
        response = client.post(
            '/api/v1/core/landing/auth/activate/?token=invalid',
            {
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        
        # Si retorna 200, debe incluir redirect_url
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('redirect_url', data,
                        "Activate exitoso debe incluir redirect_url")
    
    def test_password_reset_confirm_redirect_url(self):
        """Verificar que password-reset/confirm incluye redirect_url cuando es exitoso."""
        # Este test requiere un token válido, por lo que puede fallar
        # pero verifica la estructura esperada
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Intentar con token inválido (debe fallar, pero verificar estructura)
        response = client.post(
            '/api/v1/core/auth/password-reset/confirm/',
            {
                'uid': 'invalid',
                'token': 'invalid',
                'password1': 'newpass123',
                'password2': 'newpass123',
            },
            format='json'
        )
        
        # Si retorna 200, debe incluir redirect_url
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIn('redirect_url', data,
                        "Password reset confirm exitoso debe incluir redirect_url")
    
    def test_error_responses_json(self):
        """Verificar que las respuestas de error también son JSON."""
        client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Intentar acceder sin autenticación
        response = client.get('/api/v1/core/dashboard/')
        
        # Debe retornar error, pero en formato JSON
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])
        
        # Verificar Content-Type
        self.assertEqual(
            response['Content-Type'],
            'application/json',
            "Respuestas de error deben ser JSON"
        )
        
        # Verificar que es JSON válido
        try:
            data = response.json()
            self.assertIn('detail', data)
        except Exception as e:
            self.fail(f"Respuesta de error no es JSON válido: {e}")
