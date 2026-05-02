"""
Tests de integración para validar creación de Factura con anexos sin TypeError.
"""
from decimal import Decimal

from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos, NaturalezaFactura
from apps.tenant.facturas.services import crear_factura


class CrearFacturaAnexosTests(TenantTestCase):
    """Tests para validar que crear_factura maneja anexos correctamente."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT)
        Empresa.objects.create(
            razon_social="SINTEL",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567"
        )
    
    def test_crea_factura_y_anexos(self):
        """Valida que crear_factura crea Factura y FacturaAnexos sin TypeError."""
        factura_data = {
            "numero": "10020298",
            "naturaleza": NaturalezaFactura.COMPRA,
            "emisor_nit": "900298074",
            "emisor_razon_social": "Proveedor Test",
            "receptor_nit": "901123299",
            "receptor_razon_social": "SINTEL",
            "subtotal": Decimal("10764.00"),
            "impuestos": Decimal("2045.16"),
            "total": Decimal("12809.16"),
            "moneda": "COP",
            "ubl_xml": "<xml>...</xml>",
            "application_response_xml": "<ApplicationResponse>...</ApplicationResponse>"
        }
        
        # # WARNING: CRÍTICO: Esto NO debe lanzar TypeError
        factura = crear_factura(factura_data, items_data=[])
        
        # Validar que la factura se creó
        self.assertTrue(Factura.objects.filter(id=factura.id).exists(), 
                       "La factura debe haberse creado")
        
        # Validar que los anexos se crearon
        anexos = FacturaAnexos.objects.get(factura=factura)
        self.assertTrue(anexos.ubl_xml.startswith("<xml"), 
                       "ubl_xml debe haberse guardado en FacturaAnexos")
        self.assertTrue(anexos.application_response_xml.startswith("<ApplicationResponse"),
                       "application_response_xml debe haberse guardado en FacturaAnexos")
    
    def test_crea_factura_sin_anexos(self):
        """Valida que crear_factura funciona sin anexos."""
        factura_data = {
            "numero": "10020299",
            "naturaleza": NaturalezaFactura.VENTA,
            "emisor_nit": "901123299",
            "emisor_razon_social": "SINTEL",
            "receptor_nit": "900000000",
            "receptor_razon_social": "Cliente Test",
            "subtotal": Decimal("1000.00"),
            "impuestos": Decimal("190.00"),
            "total": Decimal("1190.00"),
            "moneda": "COP"
        }
        
        factura = crear_factura(factura_data, items_data=[])
        
        # Validar que la factura se creó
        self.assertTrue(Factura.objects.filter(id=factura.id).exists())
        
        # Validar que NO se crearon anexos
        self.assertFalse(
            FacturaAnexos.objects.filter(factura=factura).exists(),
            "No debe haber anexos si no se proporcionaron"
        )
    
    def test_crea_factura_solo_ubl_xml(self):
        """Valida que crear_factura funciona con solo ubl_xml."""
        factura_data = {
            "numero": "10020300",
            "naturaleza": NaturalezaFactura.COMPRA,
            "emisor_nit": "900298074",
            "emisor_razon_social": "Proveedor Test",
            "receptor_nit": "901123299",
            "receptor_razon_social": "SINTEL",
            "subtotal": Decimal("5000.00"),
            "impuestos": Decimal("950.00"),
            "total": Decimal("5950.00"),
            "moneda": "COP",
            "ubl_xml": "<Invoice>...</Invoice>"
        }
        
        factura = crear_factura(factura_data, items_data=[])
        
        # Validar que la factura se creó
        self.assertTrue(Factura.objects.filter(id=factura.id).exists())
        
        # Validar que se creó anexo con solo ubl_xml
        anexos = FacturaAnexos.objects.get(factura=factura)
        self.assertTrue(anexos.ubl_xml.startswith("<Invoice"))
        self.assertIsNone(anexos.application_response_xml)
