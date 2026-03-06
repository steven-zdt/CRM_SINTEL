"""
Tests de API para la app facturas.

Verifica:
- CRUD completo de Factura e ItemFactura
- GET /api/v1/facturas/por_estado/?estado=...
- POST /api/v1/facturas/{id}/cambiar_estado/
- Paginación y filtros
"""
from decimal import Decimal
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.facturas.models import Factura, ItemFactura


class FacturaViewSetTests(TenantAPITestCase):
    """Tests para FacturaViewSet."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        
        self.factura1 = Factura.objects.create(
            numero='FAC-001',
            prefijo='FAC',
            consecutivo=1,
            tipo='FE',
            estado='BORRADOR',
            fecha_emision='2024-01-15',
            emisor_nit='900123456',
            emisor_razon_social='Empresa Emisora S.A.S.',
            receptor_nit='800654321',
            receptor_razon_social='Cliente Receptor S.A.S.',
            subtotal=Decimal('100000.00'),
            impuestos=Decimal('19000.00'),
            total=Decimal('119000.00'),
        )
        
        self.factura2 = Factura.objects.create(
            numero='FAC-002',
            prefijo='FAC',
            consecutivo=2,
            tipo='FE',
            estado='ACEPTADA',
            fecha_emision='2024-01-16',
            emisor_nit='900123456',
            emisor_razon_social='Empresa Emisora S.A.S.',
            receptor_nit='800654321',
            receptor_razon_social='Cliente Receptor S.A.S.',
            subtotal=Decimal('200000.00'),
            impuestos=Decimal('38000.00'),
            total=Decimal('238000.00'),
        )
    
    def test_list_facturas(self):
        """Test: GET /api/v1/facturas/ devuelve lista paginada."""
        response = self.tget('/api/v1/facturas/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertPaginationFormat(data)
        self.assertGreaterEqual(len(data['results']), 2)
    
    def test_detail_factura(self):
        """Test: GET /api/v1/facturas/{id}/ devuelve detalle."""
        response = self.tget(f'/api/v1/facturas/{self.factura1.id}/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['id'], self.factura1.id)
        self.assertEqual(data['numero'], 'FAC-001')
    
    def test_create_factura(self):
        """Test: POST /api/v1/facturas/ crea nueva factura."""
        data = {
            'numero': 'FAC-003',
            'prefijo': 'FAC',
            'consecutivo': 3,
            'tipo': 'FE',
            'estado': 'BORRADOR',
            'fecha_emision': '2024-01-17',
            'emisor_nit': '900123456',
            'emisor_razon_social': 'Empresa Emisora S.A.S.',
            'receptor_nit': '800654321',
            'receptor_razon_social': 'Cliente Receptor S.A.S.',
            'subtotal': '50000.00',
            'impuestos': '9500.00',
            'total': '59500.00',
        }
        response = self.tpost('/api/v1/facturas/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['numero'], 'FAC-003')
    
    def test_por_estado_action(self):
        """Test: GET /api/v1/facturas/por_estado/?estado=ACEPTADA."""
        response = self.tget('/api/v1/facturas/por_estado/?estado=ACEPTADA')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        # Verificar que todas las facturas tienen el estado solicitado
        for factura in data.get('results', []):
            self.assertEqual(factura['estado'], 'ACEPTADA')
    
    def test_por_estado_missing_param(self):
        """Test: GET /api/v1/facturas/por_estado/ sin parámetro devuelve 400."""
        response = self.tget('/api/v1/facturas/por_estado/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_cambiar_estado_action(self):
        """Test: POST /api/v1/facturas/{id}/cambiar_estado/ cambia el estado."""
        data = {'estado': 'ENVIADA'}
        response = self.tpost(f'/api/v1/facturas/{self.factura1.id}/cambiar_estado/', data)
        self.assertJSONResponse(response, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data['estado'], 'ENVIADA')
        
        # Verificar en BD
        self.factura1.refresh_from_db()
        self.assertEqual(self.factura1.estado, 'ENVIADA')
    
    def test_cambiar_estado_invalid(self):
        """Test: POST con estado inválido devuelve 400."""
        data = {'estado': 'INVALIDO'}
        response = self.tpost(f'/api/v1/facturas/{self.factura1.id}/cambiar_estado/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_filter_by_estado(self):
        """Test: Filtrar por estado."""
        response = self.tget('/api/v1/facturas/?estado=BORRADOR')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        for result in data['results']:
            self.assertEqual(result['estado'], 'BORRADOR')
    
    def test_search_by_numero(self):
        """Test: Búsqueda por número."""
        response = self.tget('/api/v1/facturas/?search=FAC-001')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertGreater(len(data['results']), 0)
        self.assertIn('FAC-001', data['results'][0]['numero'])


class ItemFacturaViewSetTests(TenantAPITestCase):
    """Tests para ItemFacturaViewSet."""
    
    def setUp(self):
        """Configuración inicial."""
        super().setUp()
        
        self.factura = Factura.objects.create(
            numero='FAC-001',
            prefijo='FAC',
            consecutivo=1,
            tipo='FE',
            estado='BORRADOR',
            fecha_emision='2024-01-15',
            emisor_nit='900123456',
            emisor_razon_social='Empresa Emisora S.A.S.',
            receptor_nit='800654321',
            receptor_razon_social='Cliente Receptor S.A.S.',
            subtotal=Decimal('100000.00'),
            impuestos=Decimal('19000.00'),
            total=Decimal('119000.00'),
        )
        
        self.item = ItemFactura.objects.create(
            factura=self.factura,
            codigo='ITEM-001',
            descripcion='Producto Test',
            cantidad=Decimal('10.00'),
            unidad_medida='UN',
            valor_unitario=Decimal('10000.00'),
            porcentaje_iva=Decimal('19.00'),
        )
    
    def test_list_items(self):
        """Test: GET /api/v1/items-factura/ devuelve lista paginada."""
        response = self.tget('/api/v1/items-factura/')
        self.assertJSONResponse(response, status.HTTP_200_OK)
        data = response.json()
        self.assertPaginationFormat(data)
    
    def test_create_item(self):
        """Test: POST /api/v1/items-factura/ crea nuevo item."""
        data = {
            'factura': self.factura.id,
            'codigo': 'ITEM-002',
            'descripcion': 'Producto Nuevo',
            'cantidad': '5.00',
            'unidad_medida': 'UN',
            'valor_unitario': '20000.00',
            'porcentaje_iva': '19.00',
        }
        response = self.tpost('/api/v1/items-factura/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data['codigo'], 'ITEM-002')
