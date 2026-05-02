"""
Tests para validar regla de naturaleza (VENTA/COMPRA) con SSoT y normalización.
"""
from django_tenants.test.cases import TenantTestCase

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import NaturalezaFactura
from apps.tenant.facturas.services import _determinar_naturaleza, _norm_nit


class NaturalezaRuleSSoTTests(TenantTestCase):
    """Tests para validar regla de naturaleza con SSoT y normalización."""
    
    def setUp(self):
        super().setUp()
        # Crear empresa del tenant (SSoT)
        Empresa.objects.create(
            razon_social="SINTEL TECNOLOGY SAS",
            nit="901123299",
            dv="1",
            direccion="Calle 123",
            telefono="3001234567"
        )
    
    def test_norm_nit_elimina_separadores(self):
        """Valida que _norm_nit elimina separadores y normaliza."""
        self.assertEqual(_norm_nit(" 901.123.299 "), "901123299")
        self.assertEqual(_norm_nit("901-123-299"), "901123299")
        self.assertEqual(_norm_nit("901 123 299"), "901123299")
    
    def test_norm_nit_elimina_ceros_izquierda(self):
        """Valida que _norm_nit elimina ceros a la izquierda."""
        self.assertEqual(_norm_nit("000901123299"), "901123299")
        self.assertEqual(_norm_nit("0901123299"), "901123299")
    
    def test_norm_nit_maneja_dv(self):
        """Valida que _norm_nit extrae solo la base del NIT (sin DV)."""
        # Si viene con DV, debe extraer solo la base
        self.assertEqual(_norm_nit("901123299-1"), "901123299")
        self.assertEqual(_norm_nit("901.123.299-1"), "901123299")
    
    def test_norm_nit_maneja_none(self):
        """Valida que _norm_nit maneja None correctamente."""
        self.assertIsNone(_norm_nit(None))
        self.assertIsNone(_norm_nit(""))
        self.assertIsNone(_norm_nit("   "))
    
    def test_venta_si_igual(self):
        """Valida que si emisor_nit == empresa_nit, naturaleza es VENTA."""
        # NITs iguales (con diferentes formatos)
        self.assertEqual(
            _determinar_naturaleza("901.123.299", "901123299"),
            NaturalezaFactura.VENTA
        )
        self.assertEqual(
            _determinar_naturaleza("901123299", "901123299"),
            NaturalezaFactura.VENTA
        )
        self.assertEqual(
            _determinar_naturaleza("901123299-1", "901123299"),
            NaturalezaFactura.VENTA
        )
    
    def test_compra_si_distinto(self):
        """Valida que si emisor_nit != empresa_nit, naturaleza es COMPRA."""
        self.assertEqual(
            _determinar_naturaleza("900298074", "901123299"),
            NaturalezaFactura.COMPRA
        )
        self.assertEqual(
            _determinar_naturaleza("860030723", "901123299"),
            NaturalezaFactura.COMPRA
        )
    
    def test_compra_con_none(self):
        """Valida que si emisor_nit es None, naturaleza es COMPRA."""
        self.assertEqual(
            _determinar_naturaleza(None, "901123299"),
            NaturalezaFactura.COMPRA
        )
    
    def test_compra_si_empresa_nit_none(self):
        """Valida que si empresa_nit es None, naturaleza es COMPRA."""
        # # WARNING: NOTA: En producción, esto no debería ocurrir porque get_empresa_emisor_data()
        # lanza EmpresaNotConfiguredError si no hay NIT. Este test valida el comportamiento
        # defensivo de _determinar_naturaleza.
        self.assertEqual(
            _determinar_naturaleza("901123299", None),
            NaturalezaFactura.COMPRA
        )
