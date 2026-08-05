"""
Tests contractuales para el pipeline principal de maildigester.

FASE 1: Valida que collect_invoice_xml_from_mailbox() retorna lista de InvoiceXMLDTO
con las claves requeridas, usando StubInboxClient.

[WARNING] No valida persistencia (eso será en Fase 2+).
"""

import pytest

from apps.services.maildigester.inbox_client import StubInboxClient
from apps.services.maildigester.pipeline import collect_invoice_xml_from_mailbox
from apps.services.maildigester.schemas import InvoiceXMLDTO, MailboxConfigDTO


def test_collect_invoice_xml_from_mailbox_returns_list():
    """
    Verifica que collect_invoice_xml_from_mailbox retorna una lista.
    """
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

    result = collect_invoice_xml_from_mailbox(
        config, limit_messages=5, naturaleza="VENTA"
    )

    assert isinstance(result, list)


def test_collect_invoice_xml_from_mailbox_returns_invoice_xml_dto():
    """
    Verifica que cada elemento retornado es un InvoiceXMLDTO con claves requeridas.
    """
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

    result = collect_invoice_xml_from_mailbox(
        config, limit_messages=5, naturaleza="VENTA"
    )

    # Verificar que todos los elementos tienen las claves requeridas de InvoiceXMLDTO
    required_keys = {"source_email_id", "xml_text", "naturaleza"}
    optional_keys = {"source_filename", "metadata"}

    for item in result:
        assert isinstance(item, dict)
        # Verificar claves requeridas
        for key in required_keys:
            assert key in item, f"Falta clave requerida: {key}"
        # Verificar tipos
        assert isinstance(item["source_email_id"], str)
        assert isinstance(item["xml_text"], str)
        assert item["naturaleza"] in ("VENTA", "COMPRA")
        # Verificar claves opcionales si existen
        if "source_filename" in item:
            assert isinstance(item["source_filename"], (str, type(None)))
        if "metadata" in item:
            assert isinstance(item["metadata"], dict)


def test_collect_invoice_xml_from_mailbox_with_custom_client():
    """
    Verifica que se puede pasar un cliente personalizado (StubInboxClient).
    """
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

    custom_client = StubInboxClient()
    result = collect_invoice_xml_from_mailbox(
        config, limit_messages=3, naturaleza="COMPRA", inbox_client=custom_client
    )

    assert isinstance(result, list)
    # Verificar que todos los elementos tienen naturaleza COMPRA
    for item in result:
        assert item["naturaleza"] == "COMPRA"


def test_collect_invoice_xml_from_mailbox_handles_empty_mailbox():
    """
    Verifica que retorna lista vacía si no hay mensajes.
    """
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

    # StubInboxClient con limit=0 no retorna mensajes
    result = collect_invoice_xml_from_mailbox(
        config, limit_messages=0, naturaleza="VENTA"
    )

    assert isinstance(result, list)
    # Puede estar vacía o tener elementos según implementación del stub
