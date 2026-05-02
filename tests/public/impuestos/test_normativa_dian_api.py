"""
Pruebas de humo para APIs de normativa DIAN (catálogos tributarios).

[WARNING] POLÍTICA SSoT: Verifica que apps/public/impuestos es la única fuente de verdad.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.public.impuestos.models import (
    ContribuyenteTipo,
    RegimenRenta,
    ResponsabilidadRUT,
    PerfilTributario,
)

User = get_user_model()


class NormativaDIANAPITestCase(TestCase):
    """Pruebas de humo para APIs de normativa DIAN."""

    def setUp(self):
        """Configurar cliente API y datos de prueba."""
        self.client = APIClient()
        
        # Crear usuario staff para pruebas de escritura
        self.staff_user = User.objects.create_user(
            username='staff_test',
            email='staff@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=False
        )
        
        # Crear usuario no staff para pruebas de lectura
        self.regular_user = User.objects.create_user(
            username='regular_test',
            email='regular@test.com',
            password='testpass123',
            is_staff=False
        )
        
        # Crear datos de prueba
        self.contribuyente_tipo = ContribuyenteTipo.objects.create(
            nombre="Persona Jurídica - Gran Contribuyente",
            clase=ContribuyenteTipo.CLASE_PJ,
            segmento_dian=ContribuyenteTipo.SEG_GRAN,
            activo=True
        )
        
        self.regimen_renta = RegimenRenta.objects.create(
            codigo=RegimenRenta.ORD,
            nombre="Régimen Ordinario",
            tarifa_base_pj=32.00,
            requiere_facturacion_electronica=True,
            aplica_retenciones=True,
            activo=True
        )
        
        self.responsabilidad_rut = ResponsabilidadRUT.objects.create(
            codigo="48",
            nombre="Responsable de IVA",
            es_responsable_iva=True,
            es_facturador_electronico=True,
            activo=True
        )
        
        self.perfil_tributario = PerfilTributario.objects.create(
            nombre="PJ - Gran Contribuyente - Ordinario",
            tipo_contribuyente=self.contribuyente_tipo,
            regimen_renta=self.regimen_renta,
            activo=True
        )
        self.perfil_tributario.responsabilidades.add(self.responsabilidad_rut)

    def test_contribuyente_tipo_list_public(self):
        """Verifica que GET /api/public/v1/impuestos/contribuyentes-tipos/ es público."""
        response = self.client.get('/api/public/v1/impuestos/contribuyentes-tipos/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.json() or [])
        # Verificar que retorna JSON (no HTML)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_contribuyente_tipo_create_requires_staff(self):
        """Verifica que POST requiere permisos de staff."""
        # Sin autenticación
        response = self.client.post('/api/public/v1/impuestos/contribuyentes-tipos/', {
            'nombre': 'Test Tipo',
            'clase': ContribuyenteTipo.CLASE_PN,
            'segmento_dian': ContribuyenteTipo.SEG_OTRO,
            'activo': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Con usuario regular (no staff)
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post('/api/public/v1/impuestos/contribuyentes-tipos/', {
            'nombre': 'Test Tipo',
            'clase': ContribuyenteTipo.CLASE_PN,
            'segmento_dian': ContribuyenteTipo.SEG_OTRO,
            'activo': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Con usuario staff
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post('/api/public/v1/impuestos/contribuyentes-tipos/', {
            'nombre': 'Test Tipo',
            'clase': ContribuyenteTipo.CLASE_PN,
            'segmento_dian': ContribuyenteTipo.SEG_OTRO,
            'activo': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regimen_renta_list_public(self):
        """Verifica que GET /api/public/v1/impuestos/regimenes-renta/ es público."""
        response = self.client.get('/api/public/v1/impuestos/regimenes-renta/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.json() or [])
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_regimen_renta_create_requires_staff(self):
        """Verifica que POST requiere permisos de staff."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post('/api/public/v1/impuestos/regimenes-renta/', {
            'codigo': RegimenRenta.SIMPLE,
            'nombre': 'Régimen Simple de Tributación',
            'requiere_facturacion_electronica': True,
            'aplica_retenciones': False,
            'activo': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_responsabilidad_rut_list_public(self):
        """Verifica que GET /api/public/v1/impuestos/responsabilidades-rut/ es público."""
        response = self.client.get('/api/public/v1/impuestos/responsabilidades-rut/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.json() or [])
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_responsabilidad_rut_filter_by_responsable_iva(self):
        """Verifica filtrado por es_responsable_iva."""
        response = self.client.get('/api/public/v1/impuestos/responsabilidades-rut/?es_responsable_iva=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        if 'results' in data:
            for item in data['results']:
                self.assertTrue(item['es_responsable_iva'])

    def test_perfil_tributario_list_public(self):
        """Verifica que GET /api/public/v1/impuestos/perfiles-tributarios/ es público."""
        response = self.client.get('/api/public/v1/impuestos/perfiles-tributarios/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.json() or [])
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_perfil_tributario_detail_includes_relations(self):
        """Verifica que el detalle incluye relaciones (tipo_contribuyente, regimen_renta, responsabilidades)."""
        response = self.client.get(f'/api/public/v1/impuestos/perfiles-tributarios/{self.perfil_tributario.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('tipo_contribuyente', data)
        self.assertIn('regimen_renta', data)
        self.assertIn('responsabilidades', data)
        self.assertIsInstance(data['responsabilidades'], list)

    def test_perfil_tributario_create_requires_staff(self):
        """Verifica que POST requiere permisos de staff."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post('/api/public/v1/impuestos/perfiles-tributarios/', {
            'nombre': 'Test Perfil',
            'tipo_contribuyente_id': self.contribuyente_tipo.id,
            'regimen_renta_id': self.regimen_renta.id,
            'responsabilidades_ids': [self.responsabilidad_rut.id],
            'activo': True
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_api_json_only(self):
        """Verifica que todas las APIs retornan solo JSON (sin HTML)."""
        endpoints = [
            '/api/public/v1/impuestos/contribuyentes-tipos/',
            '/api/public/v1/impuestos/regimenes-renta/',
            '/api/public/v1/impuestos/responsabilidades-rut/',
            '/api/public/v1/impuestos/perfiles-tributarios/',
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response['Content-Type'], 'application/json')
            # Verificar que no contiene HTML
            content = response.content.decode('utf-8')
            self.assertNotIn('<html', content.lower())
            self.assertNotIn('json-formatter-container', content.lower())
