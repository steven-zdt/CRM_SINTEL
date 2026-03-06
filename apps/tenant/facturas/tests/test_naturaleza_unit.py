"""
Tests unitarios para normalización de NIT y determinación de naturaleza.

⚠️ UNIT TESTS: No requieren base de datos ni tenant.
"""
from django.test import SimpleTestCase
from apps.tenant.facturas.services import _norm_nit, _determinar_naturaleza
from apps.tenant.facturas.models import Factura


class TestNormNit(SimpleTestCase):
    """Tests para normalización de NIT."""
    
    def test_norm_formats_con_separadores(self):
        """Test: Normaliza NITs con separadores (puntos, guiones, espacios)."""
        self.assertEqual(_norm_nit(" 901.123.299 "), "901123299")
        self.assertEqual(_norm_nit("901.123.299"), "901123299")
        self.assertEqual(_norm_nit("901-123-299"), "901123299")
        self.assertEqual(_norm_nit("901 123 299"), "901123299")
    
    def test_norm_con_dv(self):
        """Test: Normaliza NITs con dígito verificador."""
        # NIT con DV separado por guion
        self.assertEqual(_norm_nit("901123299-1"), "901123299")
        self.assertEqual(_norm_nit("901.123.299-1"), "901123299")
        # NIT con DV concatenado (más de 9 caracteres)
        self.assertEqual(_norm_nit("9011232991"), "901123299")
        self.assertEqual(_norm_nit("90112329912"), "901123299")
    
    def test_norm_sin_dv(self):
        """Test: Normaliza NITs sin dígito verificador."""
        self.assertEqual(_norm_nit("901123299"), "901123299")
        self.assertEqual(_norm_nit("860030723"), "860030723")
    
    def test_norm_ceros_izquierda(self):
        """Test: Quita ceros a la izquierda pero mantiene '0' si es necesario."""
        self.assertEqual(_norm_nit("000901123299"), "901123299")
        self.assertEqual(_norm_nit("000000000"), "0")
        self.assertEqual(_norm_nit("0"), "0")
    
    def test_norm_none_vacio(self):
        """Test: Retorna None para valores None o vacíos."""
        self.assertIsNone(_norm_nit(None))
        self.assertIsNone(_norm_nit(""))
        self.assertIsNone(_norm_nit("   "))
    
    def test_norm_case_insensitive(self):
        """Test: Convierte a mayúsculas."""
        self.assertEqual(_norm_nit("abc123"), "ABC123")
        self.assertEqual(_norm_nit("ABC123"), "ABC123")


class TestDecision(SimpleTestCase):
    """Tests para determinación de naturaleza."""
    
    def test_venta_igual(self):
        """Test: VENTA cuando emisor_nit == empresa_nit (normalizados)."""
        self.assertEqual(
            _determinar_naturaleza("901.123.299", "901123299"),
            Factura.Naturaleza.VENTA
        )
        self.assertEqual(
            _determinar_naturaleza("901123299-1", "901123299"),
            Factura.Naturaleza.VENTA
        )
        self.assertEqual(
            _determinar_naturaleza("901123299", "901.123.299"),
            Factura.Naturaleza.VENTA
        )
    
    def test_compra_distinto(self):
        """Test: COMPRA cuando emisor_nit != empresa_nit."""
        self.assertEqual(
            _determinar_naturaleza("860030723", "901123299"),
            Factura.Naturaleza.COMPRA
        )
        self.assertEqual(
            _determinar_naturaleza("860.030.723", "901123299"),
            Factura.Naturaleza.COMPRA
        )
    
    def test_compra_emisor_none(self):
        """Test: COMPRA cuando emisor_nit es None."""
        self.assertEqual(
            _determinar_naturaleza(None, "901123299"),
            Factura.Naturaleza.COMPRA
        )
    
    def test_compra_empresa_none(self):
        """Test: COMPRA cuando empresa_nit es None."""
        self.assertEqual(
            _determinar_naturaleza("901123299", None),
            Factura.Naturaleza.COMPRA
        )
    
    def test_compra_ambos_none(self):
        """Test: COMPRA cuando ambos son None."""
        self.assertEqual(
            _determinar_naturaleza(None, None),
            Factura.Naturaleza.COMPRA
        )
