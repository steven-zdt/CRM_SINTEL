"""
Servicio de ingesta de facturas desde correo electrónico (MailDigester).

Este módulo implementa el Service Layer para procesar correos electrónicos,
extraer adjuntos, descomprimir archivos y detectar XML UBL 2.1 listos para importar.

WARNING: FASE 1: Solo contratos, interfaces y stubs (sin dependencias externas ni lógica real).

Principios:
- Service Layer Pattern: Lógica de negocio separada de modelos y vistas
- Cero Signals: Toda la lógica es explícita
- SSoT: La persistencia real está en apps.tenant.facturas.services
- API-First: La orquestación por endpoints vendrá en Core API (Fase 2+)
- Multi-tenant: La configuración de mailbox será por tenant, pero la persistencia
  ocurre después en el contexto del tenant correcto

Estructura:
- schemas.py: DTOs (MailboxConfigDTO, AttachmentDTO, InvoiceXMLDTO, etc.)
- inbox_client.py: Interfaz y stub para clientes IMAP/POP3
- extractors.py: Extracción de adjuntos desde mensajes
- archives.py: Utilidades para descomprimir ZIP/RAR/7z
- detectors.py: Heurísticas para detectar XML UBL y AttachedDocument
- pipeline.py: Orquestación principal (collect_invoice_xml_from_mailbox)
- exceptions.py: Excepciones específicas del dominio

Uso (Fase 1 - Stub):
    from apps.services.maildigester.pipeline import collect_invoice_xml_from_mailbox
    from apps.services.maildigester.schemas import MailboxConfigDTO
    
    config: MailboxConfigDTO = {
        "host": "imap.gmail.com",
        "port": 993,
        "protocol": "imap",
        "ssl": True,
        "username": "facturas@empresa.com",
        "password": "secret",
        "mailbox": "INBOX",
        "max_attachment_m(": 50
    }
    
    # Retorna lista de InvoiceXMLDTO (sin persistir aún)
    xmls = collect_invoice_xml_from_mailbox(config, limit_messages=10, naturaleza=").encode('utf-8')VENTA")
    
    # En Fase 2+, estos XMLs se enviarán a apps.tenant.facturas.services.importar_ubl()
"""
from .connection_test import maildigester_test_connection
from .exceptions import (
    ArchiveExpansionError,
    AttachmentTooLarge,
    InvalidXMLDocument,
    MailboxConnectionError,
    MailDigesterError,
    MimeTypeMismatch,
    PathTraversalError,
)
from .inbox_client import InboxClient, StubInboxClient
from .pipeline import collect_invoice_xml_from_mailbox
from .schemas import AttachmentDTO, ExtractedFileDTO, InvoiceXMLDTO, MailboxConfigDTO
from .tasks import fetch_and_process_billing_mail

__all__ = [
    # Pipeline principal
    "collect_invoice_xml_from_mailbox",
    # Tareas Celery (Fase 2)
    "fetch_and_process_billing_mail",
    # Test de conexión (v2.37)
    "maildigester_test_connection",
    # DTOs
    "MailboxConfigDTO",
    "AttachmentDTO",
    "ExtractedFileDTO",
    "InvoiceXMLDTO",
    # Excepciones
    "MailDigesterError",
    "MailboxConnectionError",
    "AttachmentTooLarge",
    "ArchiveExpansionError",
    "InvalidXMLDocument",
    "PathTraversalError",
    "MimeTypeMismatch",
    # Interfaces
    "InboxClient",
    "StubInboxClient",
]

