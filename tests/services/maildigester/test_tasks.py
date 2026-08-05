"""
Tests contractuales para tareas Celery de maildigester.

FASE 2: Valida que fetch_and_process_billing_mail() procesa XMLs y llama
a los servicios de facturas correctamente, usando monkeypatch para stubs.

[WARNING] Usa modo eager (CELERY_TASK_ALWAYS_EAGER=True) para tests sin workers.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.services.maildigester.schemas import MailboxConfigDTO
from apps.services.maildigester.tasks import fetch_and_process_billing_mail


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_fetch_and_process_billing_mail_eager(monkeypatch):
    """
    Verifica que la tarea procesa XMLs y llama a servicios de facturas.

    Simula:
    - Pipeline retorna 2 XMLs (1 válido + 1 duplicado)
    - Servicio de facturas importa el primero y lanza DuplicateNumero en el segundo
    """

    # 1) Stub pipeline: simula 2 XML (1 válido + 1 duplicado)
    def fake_collect(config, limit_messages=50, naturaleza="VENTA"):
        return [
            {
                "source_email_id": "msg_1",
                "source_filename": "FAC-123.xml",
                "xml_text": '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><cbc:ID>FAC-123</cbc:ID></Invoice>',
                "naturaleza": "VENTA",
                "metadata": {"subject": "OK"},
            },
            {
                "source_email_id": "msg_2",
                "source_filename": "FAC-124.xml",
                "xml_text": '<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><cbc:ID>FAC-124</cbc:ID></Invoice>',
                "naturaleza": "VENTA",
                "metadata": {"subject": "DUP"},
            },
        ]

    monkeypatch.setattr(
        "apps.services.maildigester.pipeline.collect_invoice_xml_from_mailbox",
        fake_collect,
    )

    # 2) Stub servicio facturas
    from apps.tenant.facturas.services import DuplicateNumero

    # Mock de Factura
    mock_factura_ok = MagicMock()
    mock_factura_ok.id = 1
    mock_factura_ok.numero = "FAC-123"

    call_count = 0

    def fake_upsert_factura_desde_ubl(
        file_or_text, naturaleza=None, xml_raw=None, dian_response_xml=None
    ):
        nonlocal call_count
        call_count += 1

        # Primer llamado: éxito
        if call_count == 1:
            return (mock_factura_ok, True)  # (Factura, created=True)

        # Segundo llamado: duplicado
        if call_count == 2:
            raise DuplicateNumero(
                "FAC-124", "La factura con número 'FAC-124' ya existe."
            )

        return (mock_factura_ok, False)

    monkeypatch.setattr(
        "apps.tenant.facturas.services.upsert_factura_desde_ubl",
        fake_upsert_factura_desde_ubl,
    )

    # 3) Ejecutar tarea en modo eager (config de CI del proyecto)
    config: MailboxConfigDTO = {
        "host": "stub.example.com",
        "port": 993,
        "protocol": "imap",
        "ssl": True,
        "username": "test@example.com",
        "password": "secret",
        "mailbox": "INBOX",
        "max_attachment_mb": 50,
    }

    res = fetch_and_process_billing_mail(
        tenant_schema="tenant_test",
        mailbox_config=config,
        limit_messages=10,
        naturaleza="VENTA",
    )

    # Verificar resultados
    assert res["xml_detected"] == 2
    assert res["imported"] == 1
    assert res["duplicates"] == 1
    assert res["errors"] == 0
    assert res["tenant_schema"] == "tenant_test"
    assert res["naturaleza"] == "VENTA"

    # Verificar detalles
    assert len(res["details"]) == 2
    assert res["details"][0]["status"] == "imported"
    assert res["details"][0]["numero"] == "FAC-123"
    assert res["details"][1]["status"] == "duplicate"
    assert "FAC-124" in res["details"][1]["message"]


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_fetch_and_process_billing_mail_handles_validation_error(monkeypatch):
    """
    Verifica que errores de validación (ValueError) se cuentan pero no rompen la tarea.
    """

    def fake_collect(config, limit_messages=50, naturaleza="VENTA"):
        return [
            {
                "source_email_id": "msg_1",
                "xml_text": "XML inválido",
                "naturaleza": "VENTA",
                "metadata": {},
            },
        ]

    monkeypatch.setattr(
        "apps.services.maildigester.pipeline.collect_invoice_xml_from_mailbox",
        fake_collect,
    )

    def fake_upsert_factura_desde_ubl(
        file_or_text, naturaleza=None, xml_raw=None, dian_response_xml=None
    ):
        raise ValueError("Error al parsear UBL: XML inválido")

    monkeypatch.setattr(
        "apps.tenant.facturas.services.upsert_factura_desde_ubl",
        fake_upsert_factura_desde_ubl,
    )

    config: MailboxConfigDTO = {
        "host": "stub.example.com",
        "port": 993,
        "protocol": "imap",
        "ssl": True,
        "username": "test@example.com",
        "password": "secret",
        "mailbox": "INBOX",
    }

    res = fetch_and_process_billing_mail(
        tenant_schema="tenant_test",
        mailbox_config=config,
        limit_messages=10,
        naturaleza="VENTA",
    )

    assert res["xml_detected"] == 1
    assert res["imported"] == 0
    assert res["errors"] == 1
    assert res["details"][0]["status"] == "error"
    assert res["details"][0]["error_type"] == "validation"


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_fetch_and_process_billing_mail_handles_empty_mailbox(monkeypatch):
    """
    Verifica que retorna resultado válido si no hay mensajes.
    """

    def fake_collect(config, limit_messages=50, naturaleza="VENTA"):
        return []  # Sin mensajes

    monkeypatch.setattr(
        "apps.services.maildigester.pipeline.collect_invoice_xml_from_mailbox",
        fake_collect,
    )

    config: MailboxConfigDTO = {
        "host": "stub.example.com",
        "port": 993,
        "protocol": "imap",
        "ssl": True,
        "username": "test@example.com",
        "password": "secret",
        "mailbox": "INBOX",
    }

    res = fetch_and_process_billing_mail(
        tenant_schema="tenant_test",
        mailbox_config=config,
        limit_messages=10,
        naturaleza="VENTA",
    )

    assert res["xml_detected"] == 0
    assert res["imported"] == 0
    assert res["duplicates"] == 0
    assert res["errors"] == 0
    assert len(res["details"]) == 0
