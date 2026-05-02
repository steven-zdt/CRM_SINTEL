"""
Tests unitarios para validar separación de payload (Factura vs anexos).
"""
from django.test import SimpleTestCase

from apps.tenant.facturas.services import _split_factura_payload


class SplitPayloadTests(SimpleTestCase):
    """Tests para validar que _split_factura_payload separa correctamente."""
    
    def test_split_remueve_anexos_de_factura(self):
        """Valida que los anexos se separan del payload de Factura."""
        in_payload = {
            "numero": "10020298",
            "naturaleza": "COMPRA",
            "total": 12809.16,
            "ubl_xml": "<xml...>",
            "application_response_xml": "<appresp...>"
        }
        
        factura, anexos = _split_factura_payload(in_payload)
        
        # Validar que factura NO contiene anexos
        self.assertIn("numero", factura)
        self.assertIn("naturaleza", factura)
        self.assertIn("total", factura)
        self.assertNotIn("ubl_xml", factura, "ubl_xml no debe estar en factura_data")
        self.assertNotIn("application_response_xml", factura, 
                        "application_response_xml no debe estar en factura_data")
        
        # Validar que anexos contiene los blobs
        self.assertEqual(anexos["ubl_xml"], "<xml...>")
        self.assertEqual(anexos["application_response_xml"], "<appresp...>")
    
    def test_split_sin_anexos(self):
        """Valida que funciona correctamente cuando no hay anexos."""
        in_payload = {
            "numero": "10020299",
            "naturaleza": "VENTA",
            "total": 5000.00
        }
        
        factura, anexos = _split_factura_payload(in_payload)
        
        # Validar que factura contiene todos los campos
        self.assertEqual(factura["numero"], "10020299")
        self.assertEqual(factura["naturaleza"], "VENTA")
        self.assertEqual(factura["total"], 5000.00)
        
        # Validar que anexos está vacío
        self.assertEqual(anexos, {})
    
    def test_split_solo_anexos(self):
        """Valida que funciona cuando solo hay anexos."""
        in_payload = {
            "ubl_xml": "<xml...>",
            "application_response_xml": "<appresp...>"
        }
        
        factura, anexos = _split_factura_payload(in_payload)
        
        # Validar que factura está vacío
        self.assertEqual(factura, {})
        
        # Validar que anexos contiene los blobs
        self.assertEqual(anexos["ubl_xml"], "<xml...>")
        self.assertEqual(anexos["application_response_xml"], "<appresp...>")
    
    def test_split_payload_vacio(self):
        """Valida que funciona con payload vacío."""
        factura, anexos = _split_factura_payload({})
        
        self.assertEqual(factura, {})
        self.assertEqual(anexos, {})
    
    def test_split_payload_none(self):
        """Valida que funciona con payload None."""
        factura, anexos = _split_factura_payload(None)
        
        self.assertEqual(factura, {})
        self.assertEqual(anexos, {})
