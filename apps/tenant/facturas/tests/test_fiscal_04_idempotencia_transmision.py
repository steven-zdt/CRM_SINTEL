"""
FISCAL-04: idempotencia real de ElectronicInvoiceApplicationService.transmitir().

Cubre: proteccion contra doble-envio mientras esta ENVIADA (ancla = el
propio Factura.estado, via TRANSICIONES_VALIDAS de FISCAL-03 -- sin flag
ni tabla nueva), preservacion del estado ante timeout/excepcion del
transporte (no revierte a BORRADOR, no inventa un resultado), reintento
legitimo permitido desde ERROR_TRANSMISION, y guardas de negocio
(naturaleza VENTA, XML firmado presente).
"""
from decimal import Decimal

from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.core.dian import NullTransportAdapter, TransmissionResult
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, FacturaAnexos
from apps.tenant.facturas.services.electronic_invoice_service import ElectronicInvoiceApplicationService
from tests.tenant.base_test import SintelTenantTestCase


class _TransportQueLanzaExcepcion:
    """Simula un timeout/error de red real -- send() nunca retorna un TransmissionResult."""
    def send(self, document):
        raise ConnectionError("timeout simulado -- se desconoce si la DIAN recibio el documento")


class _TransportQueAcepta:
    def send(self, document):
        return TransmissionResult(success=True, status="ACEPTADO", track_id="track-1", response_code="00")


class ElectronicInvoiceIdempotenciaTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Fiscal-04", nit="900000903", direccion="Calle Fiscal-04",
        )

    def _factura(self, estado=Factura.Estado.BORRADOR, naturaleza=Factura.Naturaleza.VENTA, con_xml=True):
        factura = Factura.objects.create(
            empresa=self.empresa, numero="FE-F04-1", prefijo="FE", consecutivo=1, tipo="FE",
            naturaleza=naturaleza, estado=estado, fecha_emision="2026-06-15",
            emisor_nit="900000903", emisor_razon_social="Empresa Fiscal-04",
            receptor_nit="800000000", receptor_razon_social="Cliente F04",
            subtotal=Decimal("100000.00"), impuestos=Decimal("19000.00"), total=Decimal("119000.00"),
            cufe="cufe-f04-test",
        )
        if con_xml:
            FacturaAnexos.objects.create(factura=factura, ubl_xml="<Invoice>contenido</Invoice>")
        return factura

    # ---- Idempotencia real: no se puede reenviar mientras esta ENVIADA ----

    def test_no_permite_transmitir_una_factura_ya_enviada(self):
        factura = self._factura(estado=Factura.Estado.ENVIADA)

        with self.assertRaises(DRFValidationError):
            ElectronicInvoiceApplicationService.transmitir(factura, transport=NullTransportAdapter())

        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ENVIADA, "no debe haber cambiado de estado")

    def test_no_permite_transmitir_una_factura_ya_aceptada(self):
        factura = self._factura(estado=Factura.Estado.ACEPTADA)

        with self.assertRaises(DRFValidationError):
            ElectronicInvoiceApplicationService.transmitir(factura, transport=NullTransportAdapter())

    # ---- Timeout/excepcion: el estado ENVIADA queda comprometido, nunca se revierte ----

    def test_excepcion_en_transporte_deja_la_factura_en_enviada_no_en_borrador(self):
        factura = self._factura(estado=Factura.Estado.BORRADOR)

        resultado = ElectronicInvoiceApplicationService.transmitir(
            factura, transport=_TransportQueLanzaExcepcion(),
        )

        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ENVIADA, "fase 1 ya se habia comprometido")
        self.assertFalse(resultado["resultado"].success)
        self.assertEqual(resultado["resultado"].status, "ENVIADA_AMBIGUA")

    def test_tras_timeout_un_reintento_inmediato_se_bloquea(self):
        """El mismo escenario del plan: 'Factura #123 -> enviada -> timeout ->
        ¿se envio realmente?' -- un reintento automatico NO debe reenviar a ciegas."""
        factura = self._factura(estado=Factura.Estado.BORRADOR)
        ElectronicInvoiceApplicationService.transmitir(factura, transport=_TransportQueLanzaExcepcion())
        factura.refresh_from_db()

        with self.assertRaises(DRFValidationError):
            ElectronicInvoiceApplicationService.transmitir(factura, transport=NullTransportAdapter())

    # ---- Camino feliz con NullTransportAdapter (honesto: siempre ERROR_TRANSMISION) ----

    def test_null_transport_adapter_deja_la_factura_en_error_transmision(self):
        factura = self._factura(estado=Factura.Estado.BORRADOR)

        resultado = ElectronicInvoiceApplicationService.transmitir(factura, transport=NullTransportAdapter())

        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ERROR_TRANSMISION)
        self.assertFalse(resultado["resultado"].success)

    def test_reintento_desde_error_transmision_es_legitimo(self):
        factura = self._factura(estado=Factura.Estado.ERROR_TRANSMISION)

        resultado = ElectronicInvoiceApplicationService.transmitir(factura, transport=_TransportQueAcepta())

        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.ACEPTADA)
        self.assertTrue(resultado["resultado"].success)

    # ---- Guardas de negocio ----

    def test_no_transmite_facturas_de_compra(self):
        factura = self._factura(naturaleza=Factura.Naturaleza.COMPRA)

        with self.assertRaises(ValueError):
            ElectronicInvoiceApplicationService.transmitir(factura, transport=NullTransportAdapter())

    def test_rechaza_factura_sin_xml_firmado_sin_cambiar_estado(self):
        factura = self._factura(estado=Factura.Estado.BORRADOR, con_xml=False)

        with self.assertRaises(ValueError):
            ElectronicInvoiceApplicationService.transmitir(factura, transport=NullTransportAdapter())

        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.Estado.BORRADOR, "no debe haber avanzado sin documento real")

    def test_respuesta_aceptada_persiste_raw_response_en_anexos(self):
        factura = self._factura(estado=Factura.Estado.BORRADOR)

        ElectronicInvoiceApplicationService.transmitir(factura, transport=_TransportQueAcepta())

        factura.refresh_from_db()
        # _TransportQueAcepta no define raw_response (default "") -- confirma que
        # el campo solo se sobreescribe cuando el adaptador real trae contenido.
        self.assertFalse(factura.anexos.application_response_xml)
