"""
DTOs (Data Transfer Objects) para el servicio maildigester.

Define los contratos de datos para entrada y salida de las funciones del servicio.
Usa TypedDict para validación de tipos en tiempo de desarrollo.

WARNING: FASE 1: Solo contratos, sin lógica de negocio.
"""
from typing import Any, Literal, TypedDict


class MailboxConfigDTO(TypedDict, total=False):
    """
    Configuración de conexión a buzón de correo.
    
    WARNING: GMAIL: Si provider == "gmail", host/port/ssl se fuerzan a presets de Gmail.
    
    Ejemplo:
        config = {
            "provider": "gmail",
            "host": "imap.gmail.com",
            "port": 993,
            "protocol": "imap",
            "ssl": True,
            "starttls": False,
            "username": "facturas@empresa.com",
            "password": "secret",
            "mailbox": "INBOX",
            "max_attachment_mb": 50,
            "move_processed_to": "Procesados",
            "mark_as_seen": True,
            "smtp": {
                "host": "smtp.gmail.com",
                "port": 587,
                "ssl": False,
                "starttls": True,
                "username": "facturas@empresa.com",
                "password": "secret"
            }
        }
    """
    provider: Literal["gmail", "custom"] | None  # Proveedor predefinido
    host: str
    port: int
    protocol: Literal["imap", "pop3"]
    ssl: bool
    starttls: bool  # STARTTLS (puerto 143) vs SSL implícito (puerto 993)
    username: str
    password: str
    mailbox: str  # INBOX, Facturacion, etc.
    max_attachment_mb: int  # p. ej., 50 (alineado con límite de ingesta)
    move_processed_to: str | None  # carpeta destino tras procesar
    mark_as_seen: bool
    smtp: dict[str, Any] | None  # Configuración SMTP opcional (para futuros usos)


class AttachmentDTO(TypedDict):
    """
    DTO para adjuntos extraídos de mensajes de correo.
    
    Ejemplo:
        attachment = {
            "filename": "factura.xml",
            "content_type": "application/xml",
            "size_bytes": 1024,
            "content": b"<?xml version='1.0'?>..."
        }
    """
    filename: str
    content_type: str
    size_bytes: int
    content: bytes


class ExtractedFileDTO(TypedDict):
    """
    DTO para archivos extraídos (ya sea adjunto directo o descomprimido).
    
    Ejemplo:
        file = {
            "filename": "FAC-123.xml",
            "guessed_type": "xml",
            "size_bytes": 2048,
            "content": b"<?xml version='1.0'?>..."
        }
    """
    filename: str
    guessed_type: Literal["xml", "zip", "rar", "7z", "other"]
    size_bytes: int
    content: bytes


class InvoiceXMLDTO(TypedDict, total=False):
    """
    DTO para XML de factura UBL listo para importar.
    
    Este es el contrato de salida principal de collect_invoice_xml_from_mailbox().
    Los servicios de apps.tenant.facturas consumirán estos DTOs para persistir.
    
    Ejemplo:
        invoice_xml = {
            "source_email_id": "msg_12345",
            "source_filename": "factura.zip",
            "xml_text": "<?xml version='1.0' encoding='UTF-8'?><Invoice>...</Invoice>",
            "naturaleza": "VENTA",
            "metadata": {
                "asunto": "Factura electrónica",
                "remitente": "proveedor@empresa.com",
                "fecha_recepcion": "2024-01-15T10:30:00Z"
            }
        }
    """
    source_email_id: str  # id del mensaje/correo
    source_filename: str | None
    xml_text: str  # XML UBL normalizado a texto
    naturaleza: Literal["VENTA", "COMPRA"]
    metadata: dict[str, Any]  # libre: proveedor, asunto, etc.
