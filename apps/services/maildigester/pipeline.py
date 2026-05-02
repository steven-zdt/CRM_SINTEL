"""
Pipeline principal de ingesta de facturas desde correo.

Orquesta el flujo completo: conexión → mensajes → adjuntos → descompresión →
detección UBL → retorno de XMLs listos para importar.

WARNING: FASE 1: Solo estructura y contratos, sin persistencia ni llamadas a ORM/DRF.
WARNING: SSoT: La persistencia real se hace en apps.tenant.facturas.services (Fase 2+).
WARNING: UID IMAP: Soporta procesamiento por UIDs para histórico completo + incremental.
"""
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from .archives import expand_archive, is_supported_archive
from .detectors import extract_xml_from_attacheddocument, guess_file_kind, is_ubl_invoice
from .exceptions import MailboxConnectionError
from .inbox_client import RealIMAPClient
from .schemas import InvoiceXMLDTO, MailboxConfigDTO

if TYPE_CHECKING:
    from .inbox_client import InboxClient


def collect_invoice_xml_from_mailbox(
    config: MailboxConfigDTO,
    *,
    limit_messages: int = 50,
    naturaleza: str | None = None,
    inbox_client: Optional["InboxClient"] = None
) -> list[InvoiceXMLDTO]:
    """
    Pipeline principal: de correos → XMLs listos para importar.
    
    Flujo:
    1) Conecta a la bandeja de correo
    2) Obtiene mensajes (hasta limit_messages)
    3) Extrae adjuntos de cada mensaje
    4) Si son archivos comprimidos (ZIP/RAR/7z), los expande
    5) Detecta XML UBL (o AttachedDocument) y extrae Invoice(s)
    6) Retorna lista de InvoiceXMLDTO (sin persistir)
    
    WARNING: FASE 1: No persiste ni llama ORM. No llama vistas DRF.
    WARNING: SSoT: La persistencia real se hace en apps.tenant.facturas.services
    (se invocará en Fase 2+ desde Core API o tareas Celery).
    
    WARNING: IDEMPOTENCIA: En Fase 2+ se implementará hash SHA256 para evitar duplicados.
    WARNING: NATURALEZA: Si no se especifica, se determina automáticamente desde el XML UBL.
    
    Args:
        config: Configuración de conexión al buzón
        limit_messages: Número máximo de mensajes a procesar (default: 50)
        naturaleza: Naturaleza de las facturas (VENTA|COMPRA, opcional - se determina desde XML)
        inbox_client: Cliente de buzón (si None, usa StubInboxClient)
        
    Returns:
        Lista de InvoiceXMLDTO con XMLs listos para importar
        
    Raises:
        MailboxConnectionError: Si no se puede conectar al buzón
        InvalidXMLDocument: Si ningún XML es válido (opcional, puede retornar lista vacía)
        
    Ejemplo:
        config = {
            "host": "imap.gmail.com",
            "port": 993,
            "protocol": "imap",
            "ssl": True,
            "username": "facturas@empresa.com",
            "password": "secret",
            "mailbox": "INBOX",
            "max_attachment_mb": 50
        }
        xmls = collect_invoice_xml_from_mailbox(config, limit_messages=10, naturaleza="VENTA")
        # Retorna: [InvoiceXMLDTO(source_email_id="msg_1", xml_text="...", ...), ...]
    """
    # Usar cliente proporcionado, o RealIMAPClient si no se especifica (en producción)
    # En desarrollo/testing, se puede pasar StubInboxClient explícitamente
    if inbox_client is None:
        # Por defecto, usar cliente real (IMAP)
        client = RealIMAPClient()
    else:
        client = inbox_client
    
    # 1) Conectar
    try:
        client.connect(config)
    except Exception as e:
        raise MailboxConnectionError(f"No se pudo conectar al buzón: {e}") from e
    
    try:
        # 2) Obtener mensajes
        messages = client.fetch_messages(limit=limit_messages)
        
        invoice_xmls: list[InvoiceXMLDTO] = []
        
        # 3) Procesar cada mensaje
        for message in messages:
            msg_id = message.get("id", "unknown")
            msg_subject = message.get("subject", "")
            msg_from = message.get("from", "")
            msg_date = message.get("date", "")
            
            try:
                # 4) Extraer adjuntos
                attachments = client.get_attachments(message)
                
                if not attachments:
                    continue  # Mensaje sin adjuntos relevantes
                
                # 5) Procesar cada adjunto
                for attachment in attachments:
                    filename = attachment["filename"]
                    content = attachment["content"]
                    content_type = attachment["content_type"]
                    size_bytes = attachment["size_bytes"]
                    
                    # Validar tamaño
                    max_mb = config.get("max_attachment_mb", 50)
                    max_bytes = max_mb * 1024 * 1024
                    if size_bytes > max_bytes:
                        continue  # Saltar adjuntos muy grandes
                    
                    # Adivinar tipo de archivo
                    file_kind = guess_file_kind(filename, content_type, content)
                    
                    # 6) Si es archivo comprimido, expandirlo
                    if file_kind in ("zip", "rar", "7z"):
                        if not is_supported_archive(filename, content_type):
                            continue
                        
                        try:
                            archive_file = {
                                "filename": filename,
                                "guessed_type": file_kind,
                                "size_bytes": size_bytes,
                                "content": content
                            }
                            extracted_files = expand_archive(archive_file)
                            
                            # Procesar cada archivo extraído
                            for extracted in extracted_files:
                                _process_file_for_invoice(
                                    extracted,
                                    msg_id,
                                    filename,  # archivo origen
                                    msg_subject,
                                    msg_from,
                                    msg_date,
                                    naturaleza,
                                    invoice_xmls
                                )
                        except Exception:
                            # Log error pero continuar con otros archivos
                            continue
                    
                    # 7) Si es XML directo, procesarlo
                    elif file_kind == "xml":
                        _process_file_for_invoice(
                            {
                                "filename": filename,
                                "guessed_type": "xml",
                                "size_bytes": size_bytes,
                                "content": content
                            },
                            msg_id,
                            filename,
                            msg_subject,
                            msg_from,
                            msg_date,
                            naturaleza,
                            invoice_xmls
                        )
                
                # 8) Finalizar mensaje (marcar como leído, mover, etc.)
                if config.get("mark_as_seen", False) or config.get("move_processed_to"):
                    client.finalize(
                        message,
                        mark_as_seen=config.get("mark_as_seen", False),
                        move_to=config.get("move_processed_to")
                    )
            
            except Exception:
                # Log error pero continuar con otros mensajes
                continue
        
        return invoice_xmls
    
    finally:
        # Siempre desconectar
        client.disconnect()


def collect_invoice_xml_from_mailbox_by_uid(
    config: MailboxConfigDTO,
    *,
    start_uid: int | None = None,
    batch_size: int = 100,
    naturaleza: str | None = None,
    inbox_client: Optional["InboxClient"] = None,
    should_abort: Callable[[], bool] | None = None
) -> tuple[list[InvoiceXMLDTO], int | None]:
    """
    Pipeline principal con procesamiento por UIDs IMAP (histórico + incremental).
    
    WARNING: UID IMAP: Los UIDs son únicos y persistentes por buzón (no cambian al eliminar mensajes).
    Permite procesamiento incremental eficiente sin reprocesar correos ya examinados.
    
    Flujo:
    1) Conecta a la bandeja de correo
    2) Obtiene mensajes por UID (desde start_uid+1 hasta batch_size mensajes)
    3) Extrae adjuntos de cada mensaje
    4) Si son archivos comprimidos (ZIP/RAR/7z), los expande
    5) Detecta XML UBL (o AttachedDocument) y extrae Invoice(s)
    6) Retorna lista de InvoiceXMLDTO y el último UID procesado
    
    WARNING: MODOS:
    - Histórico completo: start_uid=None → procesa desde UID 1
    - Incremental: start_uid=N → procesa solo UIDs > N
    
    WARNING: CANCELACIÓN COOPERATIVA: Si should_abort() retorna True, detiene el procesamiento.
    
    Args:
        config: Configuración de conexión al buzón
        start_uid: UID inicial (None = histórico completo desde UID 1)
        batch_size: Número máximo de mensajes por lote (default: 100)
        naturaleza: Naturaleza de las facturas (VENTA|COMPRA, opcional - se determina desde XML)
        inbox_client: Cliente de buzón (si None, usa RealIMAPClient)
        should_abort: Función callback para verificar cancelación cooperativa (opcional)
        
    Returns:
        Tupla (lista de InvoiceXMLDTO, último_uid_procesado)
        - último_uid_procesado: None si no se procesó ningún mensaje, int si se procesaron
        
    Raises:
        MailboxConnectionError: Si no se puede conectar al buzón
    """
    # Usar cliente proporcionado, o RealIMAPClient si no se especifica
    if inbox_client is None:
        client = RealIMAPClient()
    else:
        client = inbox_client
    
    # 1) Conectar
    try:
        client.connect(config)
    except Exception as e:
        raise MailboxConnectionError(f"No se pudo conectar al buzón: {e}") from e
    
    try:
        # 2) Obtener mensajes por UID
        if not hasattr(client, 'fetch_messages_by_uid'):
            # Fallback a método legacy si el cliente no soporta UIDs
            messages = client.fetch_messages(limit=batch_size)
            last_uid = None
        else:
            messages = client.fetch_messages_by_uid(start_uid=start_uid, batch_size=batch_size)
            # Extraer último UID procesado
            if messages:
                last_uid = max(msg.get("uid") for msg in messages if msg.get("uid"))
            else:
                last_uid = start_uid  # No hay mensajes nuevos
        
        invoice_xmls: list[InvoiceXMLDTO] = []
        
        # 3) Procesar cada mensaje
        for message in messages:
            # Verificar cancelación cooperativa
            if should_abort and should_abort():
                break
            
            msg_uid = message.get("uid")
            msg_id = message.get("id", "unknown")
            msg_subject = message.get("subject", "")
            msg_from = message.get("from", "")
            msg_date = message.get("date", "")
            
            try:
                # 4) Extraer adjuntos
                attachments = client.get_attachments(message)
                
                if not attachments:
                    continue  # Mensaje sin adjuntos relevantes
                
                # 5) Procesar cada adjunto
                for attachment in attachments:
                    # Verificar cancelación cooperativa entre archivos
                    if should_abort and should_abort():
                        break
                    
                    filename = attachment["filename"]
                    content = attachment["content"]
                    content_type = attachment["content_type"]
                    size_bytes = attachment["size_bytes"]
                    
                    # Validar tamaño
                    max_mb = config.get("max_attachment_mb", 50)
                    max_bytes = max_mb * 1024 * 1024
                    if size_bytes > max_bytes:
                        continue  # Saltar adjuntos muy grandes
                    
                    # Adivinar tipo de archivo
                    file_kind = guess_file_kind(filename, content_type, content)
                    
                    # 6) Si es archivo comprimido, expandirlo
                    if file_kind in ("zip", "rar", "7z"):
                        if not is_supported_archive(filename, content_type):
                            continue
                        
                        try:
                            archive_file = {
                                "filename": filename,
                                "guessed_type": file_kind,
                                "size_bytes": size_bytes,
                                "content": content
                            }
                            extracted_files = expand_archive(archive_file)
                            
                            # Procesar cada archivo extraído
                            for extracted in extracted_files:
                                # Verificar cancelación cooperativa entre archivos extraídos
                                if should_abort and should_abort():
                                    break
                                
                                _process_file_for_invoice(
                                    extracted,
                                    msg_id,
                                    filename,
                                    msg_subject,
                                    msg_from,
                                    msg_date,
                                    naturaleza,
                                    invoice_xmls
                                )
                        except Exception:
                            continue
                    
                    # 7) Si es XML directo, procesarlo
                    elif file_kind == "xml":
                        _process_file_for_invoice(
                            {
                                "filename": filename,
                                "guessed_type": "xml",
                                "size_bytes": size_bytes,
                                "content": content
                            },
                            msg_id,
                            filename,
                            msg_subject,
                            msg_from,
                            msg_date,
                            naturaleza,
                            invoice_xmls
                        )
                
                # 8) Finalizar mensaje (marcar como leído, mover, etc.)
                if config.get("mark_as_seen", False) or config.get("move_processed_to"):
                    client.finalize(
                        message,
                        mark_as_seen=config.get("mark_as_seen", False),
                        move_to=config.get("move_processed_to")
                    )
            
            except Exception:
                # Continuar con otros mensajes si uno falla
                continue
        
        return invoice_xmls, last_uid
    
    finally:
        # Siempre desconectar
        client.disconnect()


def _process_file_for_invoice(
    file: dict,
    source_email_id: str,
    source_filename: str,
    msg_subject: str,
    msg_from: str,
    msg_date: str,
    naturaleza: str | None,
    invoice_xmls: list[InvoiceXMLDTO]
) -> None:
    """
    Procesa un archivo (XML o extraído) para detectar Invoice UBL.
    
    Helper interno del pipeline.
    
    WARNING: NATURALEZA: Si no se especifica, se determina automáticamente desde el XML UBL.
    
    Args:
        file: ExtractedFileDTO con el archivo a procesar
        source_email_id: ID del mensaje origen
        source_filename: Nombre del archivo origen (puede ser ZIP)
        msg_subject: Asunto del mensaje
        msg_from: Remitente
        msg_date: Fecha del mensaje
        naturaleza: Naturaleza de la factura (VENTA|COMPRA, opcional - se determina desde XML)
        invoice_xmls: Lista donde agregar InvoiceXMLDTO encontrados
    """
    if file.get("guessed_type") != "xml":
        return
    
    content = file.get("content", b"")
    if not content:
        return
    
    # Decodificar a texto (UTF-8 por defecto, con fallback)
    try:
        xml_text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            xml_text = content.decode("latin-1")
        except UnicodeDecodeError:
            return  # No se puede decodificar, saltar
    
    # Verificar si es AttachedDocument
    attached_xmls = extract_xml_from_attacheddocument(xml_text)
    
    if attached_xmls:
        # Procesar cada Invoice/CreditNote extraído del AttachedDocument
        for invoice_xml in attached_xmls:
            if is_ubl_invoice(invoice_xml):
                # Determinar si es CreditNote o Invoice
                xml_lower = invoice_xml.lower()
                is_creditnote = '<creditnote' in xml_lower or '<credit_note' in xml_lower
                
                invoice_xmls.append(InvoiceXMLDTO(
                    source_email_id=source_email_id,
                    source_filename=source_filename,
                    xml_text=invoice_xml,
                    naturaleza=naturaleza or "VENTA",  # Valor por defecto si no se especifica
                    metadata={
                        "asunto": msg_subject,
                        "remitente": msg_from,
                        "fecha_recepcion": msg_date,
                        "tipo_origen": "attached_document",
                        "document_type": "creditnote" if is_creditnote else "invoice"
                    }
                ))
    else:
        # XML directo
        if is_ubl_invoice(xml_text):
            # Determinar si es CreditNote o Invoice
            xml_lower = xml_text.lower()
            is_creditnote = '<creditnote' in xml_lower or '<credit_note' in xml_lower
            
            invoice_xmls.append(InvoiceXMLDTO(
                source_email_id=source_email_id,
                source_filename=file.get("filename", source_filename),
                xml_text=xml_text,
                naturaleza=naturaleza or "VENTA",  # Valor por defecto si no se especifica
                metadata={
                    "asunto": msg_subject,
                    "remitente": msg_from,
                    "fecha_recepcion": msg_date,
                    "tipo_origen": "direct_xml",
                    "document_type": "creditnote" if is_creditnote else "invoice"
                }
            ))
