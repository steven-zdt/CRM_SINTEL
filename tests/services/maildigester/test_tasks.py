"""
Tests reales para fetch_and_process_billing_mail() -- Document Intake Service, FASE 1-3 y 28.

# WARNING: REEMPLAZA el contrato obsoleto (fetch_and_process_billing_mail(mailbox_config=...) +
monkeypatch de apps.tenant.facturas.services.upsert_factura_desde_ubl). Ese contrato ya no
existe: la tarea real usa config_id (resuelto via MailInboxConfig, FASE 14) y persiste via
FacturaBusinessService.guardar_desde_dto() (FASE 1 -- antes llamaba a
guardar_factura_desde_dto()/guardar_nota_credito_desde_dto(), funciones inexistentes que
causaban un ImportError silenciado bajo "SUCCESS" falso).

Estos tests llegan hasta PERSISTENCIA REAL (una Factura real en BD), no se detienen en mocks
de las etapas de pipeline -- solo se mockea collect_invoice_xml_from_mailbox_by_uid (la
frontera real entre "traer correo" e "interpretar documento"), igual que hace la tarea real.
Se usa Task.apply(task_id=...) (no una llamada directa) para que self.request.id este
correctamente poblado, igual que en ejecucion real via Celery.
"""
import os

from apps.tenant.empresa.models import Empresa, MailInboxConfig
from apps.tenant.facturas.models import DocumentProcessing, Factura, MailIngestionRun
from tests.tenant.base_test import SintelTenantTestCase

FIXTURE_XML_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "apps", "tenant", "facturas", "facturas_xml",
    "068b9738_TFAv21P1N000000000300962S900298074R901123299D20250204000000.xml",
)
# Emisor real del XML fixture (ver CompanyID schemeID=9 en el XML)
FIXTURE_EMISOR_NIT = "900298074"


def _read_fixture_xml_text():
    with open(FIXTURE_XML_PATH, "r", encoding="utf-8") as f:
        return f.read()


class FetchAndProcessBillingMailRealPersistenceTests(SintelTenantTestCase):
    """
    FASE 28: test real de tasks.py que llega hasta persistencia (no mocks de guardar_desde_dto).
    """

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            nit=FIXTURE_EMISOR_NIT,
            razon_social="Empresa Test Mail Hub SAS",
            direccion="Calle Falsa 123",
        )
        self.mailbox_config = MailInboxConfig.objects.create(
            empresa=self.empresa,
            nombre="Buzon Test",
            email_address="facturas@test.com",
            is_active=True,
        )

    def _patch_pipeline(self, xml_text, last_uid=100):
        """Reemplaza SOLO la frontera correo->XML (frontera real de la tarea)."""
        from apps.services.maildigester import pipeline

        def fake_collect_by_uid(mailbox_config, start_uid=None, batch_size=50, naturaleza=None, should_abort=None):
            return (
                [{
                    "source_email_id": "msg_1",
                    "source_filename": "factura.xml",
                    "xml_text": xml_text,
                    "naturaleza": "VENTA",
                    "metadata": {},
                }],
                last_uid,
            )

        original = pipeline.collect_invoice_xml_from_mailbox_by_uid
        pipeline.collect_invoice_xml_from_mailbox_by_uid = fake_collect_by_uid
        self.addCleanup(setattr, pipeline, "collect_invoice_xml_from_mailbox_by_uid", original)

    def _run_task(self, config_id, task_id, limit_messages=10):
        from apps.services.maildigester.tasks import fetch_and_process_billing_mail

        async_result = fetch_and_process_billing_mail.apply(
            kwargs={
                "tenant_schema": self.tenant.schema_name,
                "config_id": config_id,
                "limit_messages": limit_messages,
            },
            task_id=task_id,
        )
        return async_result.get()

    def test_persists_real_factura_and_marks_success(self):
        """
        FASE 1/2: el bug real (ImportError sobre guardar_factura_desde_dto) esta corregido --
        la tarea debe persistir una Factura real y marcar SUCCESS (no un SUCCESS falso).
        """
        xml_text = _read_fixture_xml_text()
        self._patch_pipeline(xml_text, last_uid=100)

        run = MailIngestionRun.objects.create(
            empresa=self.empresa, task_id="test-persist-1", status="PENDING"
        )

        result = self._run_task(self.mailbox_config.id, run.task_id)

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["counts"]["imported"], 1)
        self.assertEqual(result["counts"]["errors"], 0)

        run.refresh_from_db()
        self.assertEqual(run.status, "SUCCESS")
        self.assertEqual(run.counts["imported"], 1)

        facturas = Factura.objects.filter(empresa=self.empresa)
        self.assertEqual(facturas.count(), 1)
        self.assertTrue(facturas.first().cufe)

        # MAIL-17: debe existir el detalle por documento, no solo el agregado del run.
        docs = DocumentProcessing.objects.filter(run=run)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs.first().status, "SUCCESS")
        self.assertEqual(docs.first().handler, "InvoiceHandler")
        self.assertEqual(docs.first().domain, "facturas")

    def test_reprocessing_same_document_is_idempotent_not_duplicated(self):
        """
        FASE 13: idempotencia por CUFE -- reprocesar el mismo XML no crea una segunda Factura,
        se cuenta como duplicate, y el run sigue en SUCCESS (0 errores).
        """
        xml_text = _read_fixture_xml_text()
        self._patch_pipeline(xml_text, last_uid=100)

        run1 = MailIngestionRun.objects.create(
            empresa=self.empresa, task_id="test-idempotent-1", status="PENDING"
        )
        result1 = self._run_task(self.mailbox_config.id, run1.task_id)
        self.assertEqual(result1["counts"]["imported"], 1)

        run2 = MailIngestionRun.objects.create(
            empresa=self.empresa, task_id="test-idempotent-2", status="PENDING"
        )
        result2 = self._run_task(self.mailbox_config.id, run2.task_id)

        self.assertEqual(result2["status"], "SUCCESS")
        self.assertEqual(result2["counts"]["duplicates"], 1)
        self.assertEqual(result2["counts"]["imported"], 0)
        self.assertEqual(result2["counts"]["errors"], 0)

        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 1)

    def test_nit_mismatch_is_classified_as_error_not_silent_success(self):
        """
        FASE 2/3: un documento cuyo emisor/receptor no coincide con la empresa del tenant debe
        contarse como error clasificado (no silenciado bajo un "except Exception" generico), y
        el run final debe ser FAILED (no SUCCESS falso) cuando no hay ningun documento importado
        ni duplicado.
        """
        # Forzar mismatch: el NIT de la empresa del tenant no coincide con emisor/receptor del XML
        self.empresa.nit = "111111111"
        self.empresa.save(update_fields=["nit"])

        xml_text = _read_fixture_xml_text()
        self._patch_pipeline(xml_text, last_uid=200)

        run = MailIngestionRun.objects.create(
            empresa=self.empresa, task_id="test-mismatch-1", status="PENDING"
        )
        result = self._run_task(self.mailbox_config.id, run.task_id)

        self.assertEqual(result["counts"]["errors"], 1)
        self.assertEqual(result["counts"]["imported"], 0)
        self.assertEqual(result["status"], "FAILED")

        run.refresh_from_db()
        self.assertEqual(run.status, "FAILED")
        self.assertEqual(Factura.objects.filter(empresa=self.empresa).count(), 0)

    def test_invalid_xml_creates_document_processing_row_without_crashing_logging(self):
        """
        MAIL-17: un XML invalido no debe crashear la tarea por un bug de logging
        (extra={"message": ...} colisiona con el atributo reservado de LogRecord --
        bug real hallado al verificar este mismo escenario) y debe quedar un
        DocumentProcessing con status=INVALID y un error_message legible.
        """
        from apps.services.maildigester import pipeline

        def fake_collect_invalid(mailbox_config, start_uid=None, batch_size=50, naturaleza=None, should_abort=None):
            return (
                [{
                    "source_email_id": "msg_bad",
                    "source_filename": "basura.xml",
                    "xml_text": "<xml>no es un documento valido</xml>",
                    "naturaleza": "VENTA",
                    "metadata": {},
                }],
                100,
            )

        original = pipeline.collect_invoice_xml_from_mailbox_by_uid
        pipeline.collect_invoice_xml_from_mailbox_by_uid = fake_collect_invalid
        self.addCleanup(setattr, pipeline, "collect_invoice_xml_from_mailbox_by_uid", original)

        run = MailIngestionRun.objects.create(
            empresa=self.empresa, task_id="test-invalid-xml-1", status="PENDING"
        )
        result = self._run_task(self.mailbox_config.id, run.task_id)

        self.assertEqual(result["counts"]["errors"], 1)
        self.assertEqual(result["status"], "FAILED")

        docs = DocumentProcessing.objects.filter(run=run)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs.first().status, "INVALID")
        self.assertTrue(docs.first().error_message)
        self.assertNotIn("LogRecord", docs.first().error_message)
