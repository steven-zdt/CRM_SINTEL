"""
FISCAL-02: contrato de transporte DIAN (apps.tenant.core.dian.transport).

Puro Python -- dataclasses + Protocol, sin modelos ni DB. unittest.TestCase
simple (sin pytest.mark.django_db) para no pagar el costo de fixture de
schema tenant en algo que no lo necesita.
"""
import unittest

from apps.tenant.core.dian import (
    ElectronicDocument,
    ElectronicDocumentTransportPort,
    NullTransportAdapter,
    TransmissionResult,
)


class ElectronicDocumentTransportContractTests(unittest.TestCase):
    def _documento_de_prueba(self) -> ElectronicDocument:
        return ElectronicDocument(
            document_type="Invoice",
            numero="FE1001",
            tracking_key="cufe-de-prueba",
            signed_xml=b"<Invoice/>",
            attached_document=b"<AttachedDocument/>",
            ambiente="pruebas",
            empresa_nit="900000000",
        )

    def test_null_adapter_cumple_el_protocol_en_runtime(self):
        adapter = NullTransportAdapter()
        self.assertIsInstance(adapter, ElectronicDocumentTransportPort)

    def test_null_adapter_nunca_finge_exito(self):
        adapter = NullTransportAdapter()
        resultado = adapter.send(self._documento_de_prueba())

        self.assertIsInstance(resultado, TransmissionResult)
        self.assertFalse(resultado.success)
        self.assertEqual(resultado.status, "ERROR_TRANSMISION")
        self.assertIn("transport_not_configured", resultado.errors)
        self.assertNotEqual(resultado.status, "ACEPTADA")
        self.assertNotEqual(resultado.status, "RECHAZADA")

    def test_transmission_result_expone_todos_los_campos_del_contrato(self):
        resultado = TransmissionResult(
            success=True,
            status="ACEPTADO",
            track_id="track-123",
            response_code="00",
            response_message="Documento aceptado",
            errors=[],
            raw_response="<ApplicationResponse/>",
        )

        self.assertTrue(resultado.success)
        self.assertEqual(resultado.status, "ACEPTADO")
        self.assertEqual(resultado.track_id, "track-123")
        self.assertEqual(resultado.response_code, "00")
        self.assertEqual(resultado.response_message, "Documento aceptado")
        self.assertEqual(resultado.errors, [])
        self.assertEqual(resultado.raw_response, "<ApplicationResponse/>")

    def test_electronic_document_es_inmutable(self):
        documento = self._documento_de_prueba()
        with self.assertRaises(Exception):
            documento.numero = "otro"  # dataclass frozen=True -> FrozenInstanceError

    def test_adaptador_custom_que_no_implementa_send_no_cumple_el_protocol(self):
        class AdaptadorIncompleto:
            pass

        self.assertFalse(isinstance(AdaptadorIncompleto(), ElectronicDocumentTransportPort))


if __name__ == "__main__":
    unittest.main()
