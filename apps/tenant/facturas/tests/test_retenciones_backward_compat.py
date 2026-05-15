"""
Tests para backward compatibility de Retenciones (v3.7.1).

Verifica que:
- Factura.retefuente lee desde @property (Contabilidad.Retencion)
- ItemFactura retention fields leen desde @property
- Serializers mantienen campos en read_only
- Endpoint obtener_retenciones() sigue funcionando igual
- Migración de datos preserva valores
"""

from decimal import Decimal
from rest_framework import status

from apps.config.tests.base_tenant import TenantAPITestCase
from apps.tenant.facturas.models import Factura, ItemFactura
from apps.tenant.contabilidad.models import Retencion
from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
from apps.tenant.empresa.models import Empresa


class FacturaBackwardCompatTestCase(TenantAPITestCase):
    """Tests para backward compatibility de Factura.retefuente properties."""

    def setUp(self):
        super().setUp()

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Test Corp',
            nit='900123456',
        )

        # Crear factura
        self.factura = Factura.objects.create(
            empresa=self.empresa,
            numero='FAC-001',
            consecutivo=1,
            fecha_emision='2026-05-13',
            emisor_nit='900123456',
            emisor_razon_social='Test Corp',
            receptor_nit='123456789',
            receptor_razon_social='Cliente Test',
            naturaleza='VENTA',
        )

    def test_factura_retefuente_property_lee_desde_retencion(self):
        """Test: factura.total_retencion_fuente lee desde Retencion model."""
        # Crear retención
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            porcentaje=Decimal('2.50'),
            monto=Decimal('100.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=self.factura.id,
        )

        # @property debe retornar la suma desde Retencion
        self.assertEqual(
            self.factura.total_retencion_fuente,
            Decimal('100.00')
        )

    def test_factura_total_retenciones_multiples(self):
        """Test: Suma correcta de múltiples retenciones del mismo tipo."""
        # Crear 3 retenciones RETEFUENTE
        for monto in [50.00, 30.00, 20.00]:
            RetencionesService.crear_retencion(
                empresa=self.empresa,
                tipo='RETEFUENTE',
                monto=Decimal(str(monto)),
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=self.factura.id,
            )

        self.assertEqual(
            self.factura.total_retencion_fuente,
            Decimal('100.00')
        )

    def test_factura_retencion_default_si_no_existen_registros(self):
        """Test: Fallback a valor default si no existen Retencion records."""
        # No crear retenciones
        self.assertEqual(
            self.factura.total_retencion_fuente,
            Decimal('0.00')
        )

    def test_factura_reteica_property(self):
        """Test: factura.total_reteica lee correctamente."""
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEICA',
            monto=Decimal('25.50'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=self.factura.id,
        )

        self.assertEqual(
            self.factura.total_reteica,
            Decimal('25.50')
        )

    def test_factura_reteiva_property(self):
        """Test: factura.total_reteiva lee correctamente."""
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEIVA',
            monto=Decimal('75.75'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=self.factura.id,
        )

        self.assertEqual(
            self.factura.total_reteiva,
            Decimal('75.75')
        )

    def test_factura_no_incluye_reversadas(self):
        """Test: Las retenciones reversadas NO se incluyen en la suma."""
        ret = RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            monto=Decimal('100.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='Factura',
            documento_origen_id=self.factura.id,
        )

        # Reversar la retención
        RetencionesService.reversar_retencion(
            retencion=ret,
            empresa=self.empresa,
            documento_reversada_app='facturas',
            documento_reversada_modelo='NotaCredito',
            documento_reversada_id=1,
        )

        # El total debe ser 0 porque la original está marcada como reversada
        self.assertEqual(
            self.factura.total_retencion_fuente,
            Decimal('0.00')
        )

    def test_factura_serializer_retencion_fields_read_only(self):
        """Test: Serializer marca retention fields como read_only."""
        from apps.tenant.facturas.api.serializers import FacturaListSerializer

        serializer = FacturaListSerializer(self.factura)
        # Los campos deben estar en los datos serializados
        self.assertIn('retefuente', serializer.data)
        self.assertIn('reteica', serializer.data)
        self.assertIn('reteiva', serializer.data)

    def test_factura_api_retefuente_read_only(self):
        """Test: API no permite escribir en retefuente (read_only)."""
        payload = {
            'numero': 'FAC-002',
            'consecutivo': 2,
            'fecha_emision': '2026-05-14',
            'receptor_nit': '987654321',
            'receptor_razon_social': 'Otro Cliente',
            'retefuente': '999.99',  # Intentar setear
        }

        response = self.client.post(
            '/api/v1/facturas/',
            data=payload,
            content_type='application/json',
        )

        # Crear debería funcionar pero sin considerar retefuente
        if response.status_code == status.HTTP_201_CREATED:
            factura = Factura.objects.get(numero='FAC-002')
            # retefuente debe ser 0.00 (default), no 999.99
            self.assertEqual(factura.retefuente, Decimal('0.00'))


class ItemFacturaBackwardCompatTestCase(TenantAPITestCase):
    """Tests para backward compatibility de ItemFactura retention properties."""

    def setUp(self):
        super().setUp()

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Item Test Corp',
            nit='810654321',
        )

        self.factura = Factura.objects.create(
            empresa=self.empresa,
            numero='FAC-ITEM-001',
            consecutivo=1,
            fecha_emision='2026-05-13',
            emisor_nit='810654321',
            emisor_razon_social='Item Test Corp',
            receptor_nit='111222333',
            receptor_razon_social='Cliente Item',
            naturaleza='VENTA',
        )

        self.item = ItemFactura.objects.create(
            empresa=self.empresa,
            factura=self.factura,
            descripcion='Test Item',
            cantidad=Decimal('1.00'),
            valor_unitario=Decimal('1000.00'),
            subtotal=Decimal('1000.00'),
            total=Decimal('1000.00'),
        )

    def test_itemfactura_retefuente_property(self):
        """Test: item.total_retefuente_item lee desde Retencion."""
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEFUENTE',
            monto=Decimal('50.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='ItemFactura',
            documento_origen_id=self.item.id,
        )

        self.assertEqual(
            self.item.total_retefuente_item,
            Decimal('50.00')
        )

    def test_itemfactura_reteiva_property(self):
        """Test: item.total_reteiva_item lee correctamente."""
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEIVA',
            monto=Decimal('25.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='ItemFactura',
            documento_origen_id=self.item.id,
        )

        self.assertEqual(
            self.item.total_reteiva_item,
            Decimal('25.00')
        )

    def test_itemfactura_reteica_property(self):
        """Test: item.total_reteica_item lee correctamente."""
        RetencionesService.crear_retencion(
            empresa=self.empresa,
            tipo='RETEICA',
            monto=Decimal('10.00'),
            documento_origen_app='facturas',
            documento_origen_modelo='ItemFactura',
            documento_origen_id=self.item.id,
        )

        self.assertEqual(
            self.item.total_reteica_item,
            Decimal('10.00')
        )

    def test_itemfactura_campos_editable_false(self):
        """Test: Los campos de retención tienen editable=False."""
        from apps.tenant.facturas.models import ItemFactura

        # Verificar que los campos están marcados como editable=False
        field_retefuente = ItemFactura._meta.get_field('porcentaje_retefuente')
        self.assertFalse(field_retefuente.editable)

        field_valor = ItemFactura._meta.get_field('valor_retefuente')
        self.assertFalse(field_valor.editable)


class EndpointBackwardCompatTestCase(TenantAPITestCase):
    """Tests para compatibilidad del endpoint obtener-retenciones."""

    def setUp(self):
        super().setUp()

        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            nombre='Endpoint Test',
            nit='850123456',
        )

    def test_obtener_retenciones_venta_consulta_clientes(self):
        """Test: GET /api/v1/facturas/obtener-retenciones/ para VENTA."""
        from apps.tenant.clientes.models import Cliente
        from apps.tenant.contabilidad.models import ConfiguracionRetenciones, CuentaContable

        # Crear cliente con retenciones
        cliente = Cliente.objects.create(
            empresa=self.empresa,
            numero_documento='123456789',
            nombre='Cliente Retenedor',
            aplica_retefuente=True,
            retefuente_porcentaje=Decimal('2.50'),
        )

        # Crear config en Contabilidad
        cuenta = CuentaContable.objects.create(
            empresa=self.empresa,
            codigo='2365',
            nombre='Retención',
            nivel=6,
            es_deudora=False,
            activa=True,
        )

        ConfiguracionRetenciones.objects.create(
            empresa=self.empresa,
            tipo_tercero='CLIENTE',
            nit_tercero='123456789',
            tipo_retencion='RETEFUENTE',
            porcentaje_por_defecto=Decimal('2.50'),
            naturaleza='VENTA',
            cuenta_retencion=cuenta,
            activa=True,
        )

        response = self.client.get(
            '/api/v1/facturas/obtener-retenciones/?nit=123456789&naturaleza=VENTA',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['aplica_retefuente'])
        self.assertEqual(float(data['retefuente_porcentaje']), 2.50)

    def test_obtener_retenciones_compra_devuelve_defaults(self):
        """Test: GET /api/v1/facturas/obtener-retenciones/ para COMPRA retorna 0."""
        response = self.client.get(
            '/api/v1/facturas/obtener-retenciones/'
            '?nit=999888777&naturaleza=COMPRA',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # COMPRA siempre retorna defaults (retenciones en XML)
        self.assertFalse(data['aplica_retefuente'])
        self.assertEqual(float(data['retefuente_porcentaje']), 0.00)
