"""
FISCAL-03: matriz de transiciones fiscales reales
(FacturaBusinessService.TRANSICIONES_VALIDAS / validar_transicion_automatica()).

Puro Python -- solo lee factura.estado, sin queries -- unittest.TestCase
sin pytest.mark.django_db (una instancia Factura() sin guardar es
suficiente, no hace falta tenant/schema real).
"""
import unittest

from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.business_service import FacturaBusinessService


class FacturaTransicionesFiscalesTests(unittest.TestCase):
    def _factura_en_estado(self, estado: str) -> Factura:
        return Factura(estado=estado)

    def test_borrador_puede_pasar_a_enviada(self):
        factura = self._factura_en_estado(Factura.Estado.BORRADOR)
        FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ENVIADA)  # no debe lanzar

    def test_borrador_no_puede_saltar_directo_a_aceptada(self):
        factura = self._factura_en_estado(Factura.Estado.BORRADOR)
        with self.assertRaises(DRFValidationError):
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ACEPTADA)

    def test_enviada_puede_pasar_a_los_3_desenlaces_reales(self):
        for destino in (Factura.Estado.ACEPTADA, Factura.Estado.RECHAZADA, Factura.Estado.ERROR_TRANSMISION):
            factura = self._factura_en_estado(Factura.Estado.ENVIADA)
            FacturaBusinessService.validar_transicion_automatica(factura, destino)  # no debe lanzar

    def test_aceptada_es_practicamente_terminal_solo_permite_anulada(self):
        factura = self._factura_en_estado(Factura.Estado.ACEPTADA)
        FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ANULADA)  # no debe lanzar
        with self.assertRaises(DRFValidationError):
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ENVIADA)

    def test_rechazada_y_error_transmision_permiten_reintentar_enviada(self):
        for origen in (Factura.Estado.RECHAZADA, Factura.Estado.ERROR_TRANSMISION):
            factura = self._factura_en_estado(origen)
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ENVIADA)  # no debe lanzar

    def test_anulada_es_terminal(self):
        factura = self._factura_en_estado(Factura.Estado.ANULADA)
        with self.assertRaises(DRFValidationError):
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.ENVIADA)

    def test_mensaje_de_error_lista_las_transiciones_validas(self):
        factura = self._factura_en_estado(Factura.Estado.BORRADOR)
        with self.assertRaises(DRFValidationError) as ctx:
            FacturaBusinessService.validar_transicion_automatica(factura, Factura.Estado.RECHAZADA)
        detalle = str(ctx.exception.detail)
        self.assertIn("BORRADOR", detalle)
        self.assertIn("RECHAZADA", detalle)


if __name__ == "__main__":
    unittest.main()
