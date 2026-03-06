"""
Pruebas de humo para verificar que Empresa API es la única fuente de verdad (SSoT).

⚠️ POLÍTICA SSoT: apps/tenant/empresa/api es la ÚNICA fuente de datos empresariales.
"""
from tests.tenant.base_test import SintelTenantTestCase
from rest_framework import status
from apps.tenant.empresa.models import Empresa
from apps.tenant.empresa.services import get_empresa_data, get_empresa_emisor_data


class TestEmpresaSSoT(SintelTenantTestCase):
    """
    Pruebas para verificar que Empresa API es la única fuente de verdad.
    """

    def test_empresa_api_is_canonical(self):
        """
        Verifica que GET /api/v1/empresas/ retorna el contrato canónico.
        """
        # Crear empresa
        data = {
            "razon_social": "Empresa SSoT S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@ssoT.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data, format='json')
        
        # Obtener empresa vía API
        response = self.api_client.get("/api/v1/empresas/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        empresas = response.json()
        self.assertEqual(len(empresas), 1)
        
        empresa = empresas[0]
        
        # Verificar campos canónicos
        canonical_fields = [
            'id', 'razon_social', 'nit', 'dv', 'direccion', 'telefono',
            'email_contacto', 'regimen_tributario', 'logo', 'website', 'moneda',
            'created_at', 'updated_at'
        ]
        
        for field in canonical_fields:
            self.assertIn(field, empresa, f"Campo canónico '{field}' no está en la respuesta")

    def test_empresa_service_provider(self):
        """
        Verifica que el servicio provider retorna datos correctos.
        """
        # Crear empresa
        data = {
            "razon_social": "Empresa Provider S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@provider.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data, format='json')
        
        # Obtener datos vía servicio provider
        empresa_data = get_empresa_data()
        
        self.assertIsNotNone(empresa_data)
        self.assertEqual(empresa_data['razon_social'], "Empresa Provider S.A.")
        self.assertEqual(empresa_data['nit'], "900123456")
        self.assertEqual(empresa_data['nit_completo'], f"{empresa_data['nit']}-{empresa_data['dv']}")
        self.assertIn('direccion', empresa_data)
        self.assertIn('telefono', empresa_data)
        self.assertIn('email_contacto', empresa_data)

    def test_empresa_service_provider_empty(self):
        """
        Verifica que el servicio provider retorna None si no existe empresa.
        """
        empresa_data = get_empresa_data()
        self.assertIsNone(empresa_data)

    def test_empresa_emisor_service(self):
        """
        Verifica que get_empresa_emisor_data() retorna datos del emisor para facturas.
        """
        # Crear empresa
        data = {
            "razon_social": "Empresa Emisor S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@emisor.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data, format='json')
        
        # Obtener datos del emisor
        emisor_data = get_empresa_emisor_data()
        
        self.assertIsNotNone(emisor_data)
        self.assertEqual(emisor_data['razon_social'], "Empresa Emisor S.A.")
        self.assertEqual(emisor_data['nit'], "900123456")
        self.assertIn('nit_completo', emisor_data)
        self.assertIn('direccion', emisor_data)
        self.assertIn('telefono', emisor_data)
        self.assertIn('email_contacto', emisor_data)

    def test_core_mi_empresa_endpoint(self):
        """
        Verifica que GET /api/v1/core/mi-empresa/ expone el contrato canónico.
        """
        # Crear empresa
        data = {
            "razon_social": "Empresa Core S.A.",
            "nit": "900123456",
            "direccion": "Calle 123 #45-67",
            "telefono": "6012345678",
            "email_contacto": "contacto@core.com",
            "regimen_tributario": "Responsable de IVA",
        }
        self.api_client.post("/api/v1/empresas/", data, format='json')
        
        # Obtener vía Core API
        response = self.api_client.get("/api/v1/core/mi-empresa/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data_response = response.json()
        
        # Verificar estructura
        self.assertIn('empresa', data_response)
        self.assertIn('branding', data_response)
        self.assertIn('setup_required', data_response)
        
        empresa = data_response['empresa']
        self.assertIsNotNone(empresa)
        self.assertEqual(empresa['razon_social'], "Empresa Core S.A.")
        self.assertFalse(data_response['setup_required'])

    def test_core_mi_empresa_setup_required(self):
        """
        Verifica que GET /api/v1/core/mi-empresa/ retorna setup_required=True si no existe empresa.
        """
        response = self.api_client.get("/api/v1/core/mi-empresa/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('setup_required', data)
        self.assertTrue(data['setup_required'])
        self.assertIsNone(data.get('empresa'))
