"""
Tests para la API pública de Landing.

Valida:
- Whitelist: Solo se exponen campos públicos, no datos sensibles
- Acceso público: No requiere autenticación
"""
from rest_framework import status

from tests.tenant.base_test import SintelTenantTestCase
from apps.tenant.empresa.models import Empresa
from apps.services.empresa.gestion_service import crear_o_actualizar_empresa


class TestLandingPublicAPI(SintelTenantTestCase):
    """
    Tests para la API pública de Landing.
    
    Valida que:
    - La API es accesible sin autenticación (AllowAny)
    - Solo se exponen campos públicos (whitelist)
    - No se exponen datos sensibles (nit, regimen_tributario, etc.)
    """
    
    def setUp(self):
        """
        Setup: Crear empresa con datos sensibles y públicos.
        
        Datos sensibles: nit, regimen_tributario
        Datos públicos: razon_social, logo, website, email_contacto
        """
        # Llamar al setUp del padre
        super().setUp()
        
        # Crear empresa con datos sensibles y públicos
        # ⚠️ IMPORTANTE: El NIT debe estar sin puntos (el servicio lo limpia, pero mejor pasarlo limpio)
        self.empresa = crear_o_actualizar_empresa(
            razon_social='Sintel Corp',  # ✅ Público
            nit='900000000',  # ⚠️ SENSIBLE: No debe aparecer (sin puntos para evitar errores de validación)
            direccion='Dirección Privada',  # ⚠️ PRIVADO: No debe aparecer
            telefono='6012345678',  # ⚠️ PRIVADO: No debe aparecer
            email_contacto='contacto@sintel.com',  # ✅ Público
            regimen_tributario='Gran Contribuyente',  # ⚠️ SENSIBLE: No debe aparecer
            website='https://sintel.com'  # ✅ Público
        )
    
    def test_serializer_whitelist(self):
        """
        Prueba: Validar que la API pública no expone datos fiscales (whitelist estricta).
        
        Caso de prueba:
        1. Crear empresa con nit='900.000.000', razon_social='Sintel Corp', regimen='Gran Contribuyente'
        2. Usar APIClient sin autenticación (es público)
        3. GET a /api/v1/landing/empresa/
        4. Validaciones estrictas:
           - Status 200
           - JSON contiene 'razon_social'
           - JSON NO contiene 'nit'
           - JSON NO contiene 'regimen_tributario' (o 'regimen')
           - JSON NO contiene 'id' (interno)
        """
        # Cliente anónimo (sin autenticación, es público)
        # ⚠️ IMPORTANTE: Configurar HTTP_HOST para que el middleware de routing funcione
        from rest_framework.test import APIClient
        anonymous_client = APIClient(HTTP_HOST=self.domain.domain)
        
        # GET a /api/v1/landing/empresa/
        response = anonymous_client.get('/api/v1/landing/empresa/')
        
        # Validaciones estrictas
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "La API pública debe retornar 200 OK"
        )
        
        # Obtener datos de la respuesta
        data = response.data
        
        # ✅ Validar que campos PÚBLICOS están presentes
        self.assertIn(
            'razon_social',
            data,
            "El campo 'razon_social' debe estar presente (público)"
        )
        self.assertIn(
            'email_contacto',
            data,
            "El campo 'email_contacto' debe estar presente (público)"
        )
        self.assertIn(
            'website',
            data,
            "El campo 'website' debe estar presente (público)"
        )
        
        # ⚠️ Validar que campos SENSIBLES NO están presentes
        self.assertNotIn(
            'nit',
            data,
            "El campo 'nit' NO debe estar presente (dato sensible/fiscal)"
        )
        self.assertNotIn(
            'dv',
            data,
            "El campo 'dv' NO debe estar presente (dato sensible/fiscal)"
        )
        self.assertNotIn(
            'regimen_tributario',
            data,
            "El campo 'regimen_tributario' NO debe estar presente (dato sensible/fiscal)"
        )
        self.assertNotIn(
            'regimen',
            data,
            "El campo 'regimen' NO debe estar presente (dato sensible/fiscal)"
        )
        self.assertNotIn(
            'id',
            data,
            "El campo 'id' NO debe estar presente (dato interno)"
        )
        self.assertNotIn(
            'direccion',
            data,
            "El campo 'direccion' NO debe estar presente (dato privado)"
        )
        self.assertNotIn(
            'telefono',
            data,
            "El campo 'telefono' NO debe estar presente (dato privado)"
        )
        
        # Validar valores de campos públicos
        self.assertEqual(
            data['razon_social'],
            'Sintel Corp',
            "El campo 'razon_social' debe tener el valor correcto"
        )
        self.assertEqual(
            data['email_contacto'],
            'contacto@sintel.com',
            "El campo 'email_contacto' debe tener el valor correcto"
        )
        self.assertEqual(
            data['website'],
            'https://sintel.com',
            "El campo 'website' debe tener el valor correcto"
        )
    
    def test_public_api_info_endpoint(self):
        """
        Prueba adicional: Verificar que /api/v1/landing/info/ también funciona.
        
        Este endpoint expone información del tenant (nombre, URLs).
        """
        # Cliente anónimo
        # ⚠️ IMPORTANTE: Configurar HTTP_HOST para que el middleware de routing funcione
        from rest_framework.test import APIClient
        anonymous_client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Hacer GET a la API de info
        response = anonymous_client.get('/api/v1/landing/info/')
        
        # Validaciones
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "La API pública de info debe ser accesible sin autenticación"
        )
        
        # Verificar que contiene campos esperados
        data = response.data
        self.assertIn('nombre', data, "Debe contener el nombre del tenant")
        self.assertIn('schema_name', data, "Debe contener el schema_name del tenant")
        self.assertIn('domain_url', data, "Debe contener la URL del dominio")
        self.assertIn('login_url', data, "Debe contener la URL de login")
    
    def test_public_api_estado_cero(self):
        """
        Prueba adicional: Verificar que la API maneja correctamente el estado cero
        (cuando no existe empresa configurada).
        """
        # Eliminar la empresa creada en setUp
        Empresa.objects.all().delete()
        
        # Cliente anónimo
        # ⚠️ IMPORTANTE: Configurar HTTP_HOST para que el middleware de routing funcione
        from rest_framework.test import APIClient
        anonymous_client = APIClient(HTTP_HOST=self.domain.domain)
        
        # Hacer GET a la API pública de empresa
        response = anonymous_client.get('/api/v1/landing/empresa/')
        
        # Validaciones
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            "Si no existe empresa, debe retornar 404"
        )
        
        # Verificar que el mensaje de error es apropiado
        data = response.data
        self.assertIn('error', data, "Debe contener un campo 'error'")
        self.assertIn('message', data, "Debe contener un campo 'message'")
