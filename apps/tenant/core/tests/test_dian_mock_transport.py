"""
FISCAL-02A: MockTransportAdapter -- simulacion controlada, CERO conexion
externa. Puro Python, sin DB (unittest.TestCase sin pytest.mark.django_db).
"""
import unittest

from apps.tenant.core.dian import ElectronicDocument, MockTransportAdapter


def _documento(tracking_key="cufe-mock-1") -> ElectronicDocument:
    return ElectronicDocument(
        document_type="Invoice", numero="FE-MOCK-1", tracking_key=tracking_key,
        signed_xml=b"<Invoice/>", attached_document=b"<AttachedDocument/>",
    )


class MockTransportAdapterEscenariosTests(unittest.TestCase):
    def test_test_accepted_retorna_aceptado(self):
        adapter = MockTransportAdapter(scenario="TEST_ACCEPTED")
        resultado = adapter.send(_documento())
        self.assertTrue(resultado.success)
        self.assertEqual(resultado.status, "ACEPTADO")
        self.assertIsNotNone(resultado.track_id)
        self.assertIsNotNone(resultado.submitted_at)

    def test_test_rejected_retorna_rechazado_con_errores(self):
        adapter = MockTransportAdapter(scenario="TEST_REJECTED")
        resultado = adapter.send(_documento())
        self.assertTrue(resultado.success, "el roundtrip se completo -- es un rechazo de negocio")
        self.assertEqual(resultado.status, "RECHAZADO")
        self.assertTrue(resultado.errors)

    def test_test_pending_retorna_pendiente(self):
        adapter = MockTransportAdapter(scenario="TEST_PENDING")
        resultado = adapter.send(_documento())
        self.assertEqual(resultado.status, "PENDIENTE")

    def test_test_timeout_lanza_timeouterror(self):
        adapter = MockTransportAdapter(scenario="TEST_TIMEOUT")
        with self.assertRaises(TimeoutError):
            adapter.send(_documento())

    def test_test_connection_error_lanza_connectionerror(self):
        adapter = MockTransportAdapter(scenario="TEST_CONNECTION_ERROR")
        with self.assertRaises(ConnectionError):
            adapter.send(_documento())


class MockTransportAdapterOverridePorDocumentoTests(unittest.TestCase):
    def test_scenario_por_tracking_key_prevalece_sobre_el_default(self):
        adapter = MockTransportAdapter(
            scenario="TEST_ACCEPTED",
            scenario_por_tracking_key={"cufe-especial": "TEST_REJECTED"},
        )

        aceptado = adapter.send(_documento("cufe-normal"))
        rechazado = adapter.send(_documento("cufe-especial"))

        self.assertEqual(aceptado.status, "ACEPTADO")
        self.assertEqual(rechazado.status, "RECHAZADO")


class MockTransportAdapterGetStatusTests(unittest.TestCase):
    def test_get_status_recupera_el_resultado_del_send_previo(self):
        adapter = MockTransportAdapter(scenario="TEST_ACCEPTED")
        documento = _documento()
        adapter.send(documento)

        consulta = adapter.get_status(documento.tracking_key)

        self.assertEqual(consulta.status, "ACEPTADO")

    def test_get_status_sin_transmision_previa_no_inventa_un_resultado(self):
        adapter = MockTransportAdapter()
        resultado = adapter.get_status("cufe-nunca-enviado")
        self.assertFalse(resultado.success)
        self.assertIn("not_found", resultado.errors)


class MockTransportAdapterIntentosTests(unittest.TestCase):
    def test_intentos_cuenta_cada_llamada_send_por_tracking_key(self):
        adapter = MockTransportAdapter(scenario="TEST_ACCEPTED")
        documento = _documento()

        self.assertEqual(adapter.intentos(documento.tracking_key), 0)
        adapter.send(documento)
        self.assertEqual(adapter.intentos(documento.tracking_key), 1)
        adapter.send(documento)
        self.assertEqual(adapter.intentos(documento.tracking_key), 2)


if __name__ == "__main__":
    unittest.main()
