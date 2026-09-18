"""
FACTURAS-UI-CRONO-01 FASE 2/4/18: tests unitarios de la matriz REAL de
FacturaBusinessService._resolver_naturaleza() -- no existia ningun test
que probara esta funcion directamente (solo el wrapper de compatibilidad
_determinar_naturaleza(), que nunca antes de esta mision pudo retornar
None/"Revisar"). No requieren base de datos ni tenant (funcion estatica
pura).
"""
from django.test import SimpleTestCase

from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.business_service import (
    FacturaBusinessService,
    clean_nit,
    same_business_name,
    same_nit,
)

VENTA = Factura.Naturaleza.VENTA
COMPRA = Factura.Naturaleza.COMPRA
EMPRESA_NIT = "901123299"


def _resolver(emisor_nit, receptor_nit, empresa_nit=EMPRESA_NIT):
    return FacturaBusinessService._resolver_naturaleza(emisor_nit, receptor_nit, empresa_nit)


class SameNitTests(SimpleTestCase):
    def test_nit_identico(self):
        self.assertTrue(same_nit("901123299", "901123299"))

    def test_nit_con_puntos_y_espacios(self):
        self.assertTrue(same_nit(" 901.123.299 ", "901123299"))

    def test_nit_con_dv_separado_por_guion(self):
        """Prioridad NIT (FASE 3): el DV con guion no debe causar falso negativo."""
        self.assertTrue(same_nit("901123299-1", "901123299"))
        self.assertTrue(same_nit("901.123.299-1", "901123299"))

    def test_nit_distinto_no_coincide(self):
        self.assertFalse(same_nit("860030723", "901123299"))

    def test_nit_vacio_nunca_coincide(self):
        self.assertFalse(same_nit("", "901123299"))
        self.assertFalse(same_nit(None, "901123299"))
        self.assertFalse(same_nit("901123299", ""))
        self.assertFalse(same_nit("", ""))

    def test_no_convierte_nits_distintos_en_uno(self):
        """FASE 3: la normalizacion no debe hacer coincidir NITs
        genuinamente distintos que casualmente comparten prefijo."""
        self.assertFalse(same_nit("901123299", "9011232990"))


class SameBusinessNameTests(SimpleTestCase):
    def test_nombre_identico_normalizado(self):
        self.assertTrue(same_business_name("Acme S.A.S.", "  acme sas  "))

    def test_espacios_repetidos_y_mayusculas(self):
        self.assertTrue(same_business_name("Acme   S.A.S", "ACME S.A.S"))

    def test_nombre_distinto_no_coincide(self):
        self.assertFalse(same_business_name("Acme SAS", "Beta SAS"))


class ResolverNaturalezaMatrixTests(SimpleTestCase):
    """Matriz completa de FASE 4 de la mision, probada 1:1."""

    def test_nuestra_empresa_a_cliente_es_venta(self):
        self.assertEqual(_resolver(emisor_nit=EMPRESA_NIT, receptor_nit="900123456"), VENTA)

    def test_proveedor_a_nuestra_empresa_es_compra(self):
        self.assertEqual(_resolver(emisor_nit="900123456", receptor_nit=EMPRESA_NIT), COMPRA)

    def test_nuestra_empresa_a_nuestra_empresa_es_revisar(self):
        self.assertIsNone(_resolver(emisor_nit=EMPRESA_NIT, receptor_nit=EMPRESA_NIT))

    def test_proveedor_a_cliente_distinto_es_revisar(self):
        self.assertIsNone(_resolver(emisor_nit="900123456", receptor_nit="800999888"))

    def test_sin_emisor_a_nuestra_empresa_es_revisar(self):
        """No inventar un proveedor solo porque el receptor somos nosotros."""
        self.assertIsNone(_resolver(emisor_nit="", receptor_nit=EMPRESA_NIT))
        self.assertIsNone(_resolver(emisor_nit=None, receptor_nit=EMPRESA_NIT))

    def test_proveedor_sin_receptor_es_revisar(self):
        self.assertIsNone(_resolver(emisor_nit="900123456", receptor_nit=""))

    def test_nuestra_empresa_sin_receptor_es_venta(self):
        """A diferencia de COMPRA, VENTA no exige receptor presente: ya
        sabemos con certeza que el emisor somos nosotros -- mismo
        comportamiento que siempre tuvo el wrapper de compatibilidad
        _determinar_naturaleza() (nunca recibio receptor_nit), confirmado
        por test_naturaleza_unit.py::test_venta_igual."""
        self.assertEqual(_resolver(emisor_nit=EMPRESA_NIT, receptor_nit=""), VENTA)

    def test_empresa_sin_nit_configurado_es_revisar(self):
        self.assertIsNone(_resolver(emisor_nit="900123456", receptor_nit=EMPRESA_NIT, empresa_nit=""))
        self.assertIsNone(_resolver(emisor_nit="900123456", receptor_nit=EMPRESA_NIT, empresa_nit=None))

    def test_ambos_nit_vacios_es_revisar(self):
        self.assertIsNone(_resolver(emisor_nit="", receptor_nit=""))

    def test_prioridad_nit_ignora_dv_con_guion(self):
        """FASE 18 'Prioridad NIT': NIT coincide (aunque el XML traiga el
        DV con guion) -> VENTA, sin importar el formato."""
        self.assertEqual(
            _resolver(emisor_nit=f"{EMPRESA_NIT}-1", receptor_nit="900123456"), VENTA
        )

    def test_nombre_nunca_decide_la_clasificacion(self):
        """FASE 18 'Nombre insuficiente': _resolver_naturaleza ni siquiera
        recibe el nombre -- no puede clasificar por nombre aunque el
        NIT no coincida. Confirma que la firma real de la funcion es
        estrictamente NIT-based (sin parametro de nombre)."""
        import inspect

        params = list(inspect.signature(FacturaBusinessService._resolver_naturaleza).parameters)
        self.assertNotIn("nombre", " ".join(params).lower())
        self.assertNotIn("razon_social", " ".join(params).lower())
