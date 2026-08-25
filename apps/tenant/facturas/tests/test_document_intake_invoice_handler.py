"""
Tests reales del Document Intake Service (FASE 6-11, 22, 28) -- InvoiceHandler.

Prueba la cadena completa ReceivedDocument -> DocumentDispatcher ->
InvoiceHandler -> FacturaBusinessService.guardar_desde_dto() hasta
persistencia real (una Factura real en BD), reutilizando el mismo XML
fixture ya usado para verificar FASE 1 de la migracion de tasks.py. No usa
mocks de guardar_desde_dto -- solo verifica el contrato transversal nuevo.
"""
import os

from apps.services.document_intake import DocumentSource, ProcessingStatus, ReceivedDocument
from apps.services.document_intake.dispatcher import DocumentDispatcher
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.document_intake.invoice_handler import InvoiceHandler
from apps.tenant.facturas.models import Factura
from tests.tenant.base_test import SintelTenantTestCase

FIXTURE_XML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "facturas_xml",
    "068b9738_TFAv21P1N000000000300962S900298074R901123299D20250204000000.xml",
)
# Emisor real del XML fixture
FIXTURE_EMISOR_NIT = "900298074"


def _read_fixture_xml_bytes():
    with open(FIXTURE_XML_PATH, "rb") as f:
        return f.read()


class InvoiceHandlerDocumentIntakeTests(SintelTenantTestCase):
    """FASE 11/22: Facturas como primer consumidor real del Document Intake Service."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            nit=FIXTURE_EMISOR_NIT,
            razon_social="Empresa Test Document Intake SAS",
            direccion="Calle Falsa 123",
        )
        # Dispatcher aislado por test (no el singleton global) para no
        # depender de que otros tests hayan registrado handlers antes.
        self.dispatcher = DocumentDispatcher()
        self.dispatcher.register("invoice", InvoiceHandler())
        self.dispatcher.register("creditnote", InvoiceHandler())

    def _make_document(self, **overrides):
        defaults = dict(
            tenant_schema=self.tenant.schema_name,
            source=DocumentSource.EMAIL,
            content=_read_fixture_xml_bytes(),
            filename="factura.xml",
            mime_type="application/xml",
            document_type="invoice",
            metadata={"empresa_id": self.empresa.id},
        )
        defaults.update(overrides)
        return ReceivedDocument(**defaults)

    def test_dispatch_persists_real_factura(self):
        result = self.dispatcher.dispatch(self._make_document())

        self.assertEqual(result.status, ProcessingStatus.SUCCESS)
        self.assertEqual(result.domain, "facturas")
        self.assertEqual(result.handler, "InvoiceHandler")
        self.assertTrue(result.metadata.get("cufe"))

        facturas = Factura.objects.filter(empresa=self.empresa)
        self.assertEqual(facturas.count(), 1)
        self.assertEqual(facturas.first().cufe, result.metadata["cufe"])

    def test_dispatch_same_document_twice_is_idempotent(self):
        doc = self._make_document()
        result1 = self.dispatcher.dispatch(doc)
        self.assertEqual(result1.status, ProcessingStatus.SUCCESS)

        result2 = self.dispatcher.dispatch(doc)
        self.assertEqual(result2.status, ProcessingStatus.DUPLICATE)

        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 1)

    def test_dispatch_unsupported_type_requires_review_not_crash(self):
        doc = self._make_document(document_type="gasto")
        result = self.dispatcher.dispatch(doc)

        self.assertEqual(result.status, ProcessingStatus.REQUIRES_REVIEW)
        self.assertIn("no_handler_for_type:gasto", result.errors)
        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 0)

    def test_dispatch_missing_empresa_id_is_invalid_not_crash(self):
        doc = self._make_document(metadata={})
        result = self.dispatcher.dispatch(doc)

        self.assertEqual(result.status, ProcessingStatus.INVALID)
        self.assertIn("missing_empresa_id", result.errors)
