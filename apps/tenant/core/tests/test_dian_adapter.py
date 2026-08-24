"""
FISCAL-05: DIANAdapter (apps.tenant.core.dian.adapters) -- NO VERIFICADO
contra el ambiente real de la DIAN (ver advertencia en adapters.py). Estos
tests cubren la LOGICA del adaptador (empaquetado, parseo de respuesta,
manejo de configuracion faltante, propagacion de excepciones de red) via
un `_client_factory` inyectado -- no ejercitan ninguna llamada SOAP real
ni requieren `zeep` instalado.

Puro Python, unittest.TestCase sin pytest.mark.django_db (solo
apps.tenant.core.dian.transport.ElectronicDocument, sin modelos).
"""
import base64
import io
import unittest
import zipfile
from unittest.mock import MagicMock

from apps.tenant.core.dian import DIANAdapter, ElectronicDocument


def _documento_de_prueba() -> ElectronicDocument:
    return ElectronicDocument(
        document_type="Invoice",
        numero="FE1001",
        tracking_key="cufe-de-prueba",
        signed_xml=b"<Invoice/>",
        attached_document=b"<AttachedDocument>contenido</AttachedDocument>",
        ambiente="pruebas",
        empresa_nit="900000000",
    )


class DIANAdapterConfiguracionTests(unittest.TestCase):
    def test_sin_wsdl_configurado_retorna_error_transmision_sin_intentar_conectar(self):
        adapter = DIANAdapter(wsdl_url="", _client_factory=MagicMock(side_effect=AssertionError("no debe llamarse")))

        resultado = adapter.send(_documento_de_prueba())

        self.assertFalse(resultado.success)
        self.assertEqual(resultado.status, "ERROR_TRANSMISION")
        self.assertIn("wsdl_not_configured", resultado.errors)


class DIANAdapterEmpaquetadoTests(unittest.TestCase):
    def test_empaqueta_el_attached_document_en_zip_base64(self):
        documento = _documento_de_prueba()

        b64 = DIANAdapter._empaquetar_documento(documento)
        zip_bytes = base64.b64decode(b64)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            nombres = zf.namelist()
            self.assertEqual(nombres, ["FE1001.xml"])
            self.assertEqual(zf.read("FE1001.xml"), documento.attached_document)


class DIANAdapterParseoRespuestaTests(unittest.TestCase):
    def test_respuesta_valida_true_mapea_a_aceptado(self):
        respuesta = MagicMock(IsValid=True, StatusCode="00", StatusDescription="Ok", XmlDocumentKey="track-1")

        resultado = DIANAdapter._parsear_respuesta(respuesta)

        self.assertTrue(resultado.success)
        self.assertEqual(resultado.status, "ACEPTADO")
        self.assertEqual(resultado.track_id, "track-1")

    def test_respuesta_valida_false_mapea_a_rechazado_sin_perder_el_mensaje(self):
        respuesta = MagicMock(IsValid=False, StatusCode="99", StatusDescription="XML invalido", XmlDocumentKey=None)

        resultado = DIANAdapter._parsear_respuesta(respuesta)

        self.assertTrue(resultado.success, "el roundtrip SOAP si se completo -- es un rechazo de negocio, no un error de transporte")
        self.assertEqual(resultado.status, "RECHAZADO")
        self.assertIn("XML invalido", resultado.errors)

    def test_respuesta_con_shape_no_reconocido_no_inventa_un_estado(self):
        respuesta = object()  # sin IsValid -- shape completamente distinto al esperado

        resultado = DIANAdapter._parsear_respuesta(respuesta)

        self.assertFalse(resultado.success)
        self.assertEqual(resultado.status, "ERROR_TRANSMISION")
        self.assertIn("unrecognized_response_shape", resultado.errors)


class DIANAdapterEnvioTests(unittest.TestCase):
    def test_send_feliz_usa_el_client_factory_inyectado(self):
        cliente_falso = MagicMock()
        cliente_falso.service.SendBillSync.return_value = MagicMock(
            IsValid=True, StatusCode="00", StatusDescription="Ok", XmlDocumentKey="track-2",
        )
        adapter = DIANAdapter(wsdl_url="https://wsdl-de-prueba.invalido/", _client_factory=lambda url: cliente_falso)

        resultado = adapter.send(_documento_de_prueba())

        self.assertTrue(resultado.success)
        self.assertEqual(resultado.status, "ACEPTADO")
        cliente_falso.service.SendBillSync.assert_called_once()
        _, kwargs = cliente_falso.service.SendBillSync.call_args
        self.assertEqual(kwargs["fileName"], "FE1001.zip")

    def test_excepcion_de_red_durante_send_se_propaga_no_se_traga(self):
        """Critico para FISCAL-04: ElectronicInvoiceApplicationService.transmitir()
        depende de que las excepciones de red SALGAN de send() sin ser
        atrapadas aqui, para tratarlas como transmision AMBIGUA."""
        def factory_que_falla(url):
            raise ConnectionError("timeout simulado")

        adapter = DIANAdapter(wsdl_url="https://wsdl-de-prueba.invalido/", _client_factory=factory_que_falla)

        with self.assertRaises(ConnectionError):
            adapter.send(_documento_de_prueba())


if __name__ == "__main__":
    unittest.main()
