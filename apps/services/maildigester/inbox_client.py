"""
Interfaz y implementaciones para clientes de buzón de correo (IMAP/POP3).

Define el Protocol/ABC para clientes de correo y provee:
- RealIMAPClient: Implementación real usando imaplib (IMAP/IMAPS)
- StubInboxClient: Implementación stub para pruebas y desarrollo

WARNING: FASE 2: Implementación real con imaplib (IMAP/IMAPS con STARTTLS).
"""
import email
import imaplib
import ssl
from email.header import decode_header
from typing import Any, Protocol

from .exceptions import MailboxConnectionError
from .schemas import AttachmentDTO, MailboxConfigDTO


class InboxClient(Protocol):
    """
    Protocolo para clientes de buzón de correo.
    
    Cualquier implementación (IMAP, POP3, etc.) debe cumplir este contrato.
    """
    
    def connect(self, config: MailboxConfigDTO) -> None:
        """
        Conecta y autentica con el buzón de correo.
        
        Args:
            config: Configuración de conexión
            
        Raises:
            MailboxConnectionError: Si la conexión o autenticación falla
        """
        ...
    
    def fetch_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Obtiene mensajes del buzón.
        
        Args:
            limit: Número máximo de mensajes a obtener
            
        Returns:
            Lista de dicts con campos mínimos:
            - id: str (identificador único del mensaje)
            - subject: str (asunto)
            - from: str (remitente)
            - date: str (fecha en formato RFC822)
            - raw: bytes (mensaje completo en formato RFC822) o estructura equivalente
            
        Raises:
            MailboxConnectionError: Si no hay conexión activa
        """
        ...
    
    def get_attachments(self, message: dict[str, Any]) -> list[AttachmentDTO]:
        """
        Extrae adjuntos de un mensaje.
        
        Args:
            message: Dict con datos del mensaje (retornado por fetch_messages)
            
        Returns:
            Lista de AttachmentDTO con los adjuntos del mensaje
        """
        ...
    
    def finalize(self, message: dict[str, Any], *, mark_as_seen: bool = False, move_to: str | None = None) -> None:
        """
        Finaliza el procesamiento de un mensaje (marcar como leído, mover, etc.).
        
        Args:
            message: Dict con datos del mensaje
            mark_as_seen: Si True, marca el mensaje como leído
            move_to: Si se proporciona, mueve el mensaje a esta carpeta
            
        Raises:
            MailboxConnectionError: Si no hay conexión activa
        """
        ...
    
    def disconnect(self) -> None:
        """
        Cierra la conexión con el buzón.
        """
        ...


class RealIMAPClient:
    """
    Implementación real de InboxClient usando imaplib.
    
    Soporta:
    - IMAPS (993, TLS implícito)
    - IMAP (143) + STARTTLS
    - Autenticación, selección de carpeta, búsqueda y fetch de mensajes
    - Extracción de adjuntos
    
    WARNING: SEGURIDAD: Valida certificados TLS en producción (no insecure).
    
    Ejemplo:
        client = RealIMAPClient()
        client.connect({
            "host": "imap.gmail.com",
            "port": 993,
            "protocol": "imap",
            "ssl": True,
            "username": "user@example.com",
            "password": "secret",
            "mailbox": "INBOX"
        })
        messages = client.fetch_messages(limit=10)
    """
    
    def __init__(self):
        self._connection: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None
        self._config: MailboxConfigDTO | None = None
        self._connected = False
    
    def connect(self, config: MailboxConfigDTO) -> None:
        """
        Conecta y autentica con el buzón de correo.
        
        Args:
            config: Configuración de conexión
            
        Raises:
            MailboxConnectionError: Si la conexión o autenticación falla
        """
        required = ["host", "username", "password"]
        missing = [k for k in required if k not in config]
        if missing:
            raise MailboxConnectionError(f"Faltan campos requeridos: {', '.join(missing)}")
        
        host = config["host"]
        port = config.get("port", 993)
        use_ssl = config.get("ssl", True)
        use_starttls = config.get("starttls", False)
        username = config["username"]
        password = config["password"]
        protocol = config.get("protocol", "imap")
        
        if protocol != "imap":
            raise MailboxConnectionError(f"Protocolo {protocol} no soportado. Solo IMAP está implementado.")
        
        try:
            if use_ssl and not use_starttls:
                # IMAPS (puerto 993, TLS implícito)
                # WARNING: SEGURIDAD: En producción, validar certificados (check_hostname=True por defecto)
                context = ssl.create_default_context()
                self._connection = imaplib.IMAP4_SSL(host, port, ssl_context=context)
            else:
                # IMAP (puerto 143) + STARTTLS
                self._connection = imaplib.IMAP4(host, port)
                # Iniciar STARTTLS si está habilitado
                if use_starttls:
                    self._connection.starttls(ssl_context=ssl.create_default_context())
            
            # Autenticar
            self._connection.login(username, password)
            
            self._config = config
            self._connected = True
            
        except imaplib.IMAP4.error as e:
            raise MailboxConnectionError(f"Error de autenticación IMAP: {e}") from e
        except (ConnectionError, OSError, ssl.SSLError) as e:
            raise MailboxConnectionError(f"Error de conexión a {host}:{port}: {e}") from e
        except Exception as e:
            raise MailboxConnectionError(f"Error inesperado al conectar: {e}") from e
    
    def fetch_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Obtiene mensajes del buzón (LEGACY: usa índices de secuencia, no UIDs).
        
        WARNING: DEPRECADO: Usar fetch_messages_by_uid() para procesamiento incremental.
        
        Args:
            limit: Número máximo de mensajes a obtener
            
        Returns:
            Lista de dicts con campos: id, subject, from, date, raw
            
        Raises:
            MailboxConnectionError: Si no hay conexión activa
        """
        if not self._connected or not self._connection:
            raise MailboxConnectionError("No hay conexión activa. Llame a connect() primero.")
        
        mailbox = self._config.get("mailbox", "INBOX") if self._config else "INBOX"
        
        try:
            # Seleccionar carpeta
            status, _ = self._connection.select(mailbox, readonly=True)
            if status != "OK":
                raise MailboxConnectionError(f"No se pudo seleccionar la carpeta '{mailbox}'")
            
            # Buscar todos los mensajes (no filtrados por UNSEEN para permitir reprocesamiento)
            status, message_ids = self._connection.search(None, "ALL")
            if status != "OK":
                raise MailboxConnectionError("No se pudo buscar mensajes")
            
            # Convertir IDs a lista y limitar
            id_list = message_ids[0].split()
            if not id_list:
                return []
            
            # Limitar cantidad
            id_list = id_list[:limit]
            
            messages = []
            for msg_id in id_list:
                try:
                    # Fetch mensaje completo (RFC822)
                    status, msg_data = self._connection.fetch(msg_id, "(RFC822)")
                    if status != "OK" or not msg_data:
                        continue
                    
                    # Parsear mensaje
                    msg_bytes = msg_data[0][1]
                    msg = email.message_from_bytes(msg_bytes)
                    
                    # Extraer headers
                    subject = self._decode_header(msg.get("Subject", ""))
                    from_addr = self._decode_header(msg.get("From", ""))
                    date = msg.get("Date", "")
                    
                    messages.append({
                        "id": msg_id.decode("utf-8") if isinstance(msg_id, bytes) else str(msg_id),
                        "subject": subject,
                        "from": from_addr,
                        "date": date,
                        "raw": msg_bytes,
                        "_email_message": msg  # Guardar objeto email.message para extraer adjuntos
                    })
                except Exception:
                    # Continuar con otros mensajes si uno falla
                    continue
            
            return messages
            
        except imaplib.IMAP4.error as e:
            raise MailboxConnectionError(f"Error IMAP al obtener mensajes: {e}") from e
        except Exception as e:
            raise MailboxConnectionError(f"Error inesperado al obtener mensajes: {e}") from e
    
    def fetch_messages_by_uid(self, start_uid: int | None = None, batch_size: int = 100) -> list[dict[str, Any]]:
        """
        Obtiene mensajes del buzón usando UIDs IMAP (para procesamiento incremental).
        
        WARNING: UID IMAP: Los UIDs son únicos y persistentes por buzón (no cambian al eliminar mensajes).
        Permite procesamiento incremental eficiente sin reprocesar correos ya examinados.
        
        Args:
            start_uid: UID inicial (si None, procesa desde UID 1 = histórico completo)
            batch_size: Número máximo de mensajes a obtener en este lote
            
        Returns:
            Lista de dicts con campos: uid, id, subject, from, date, raw
            
        Raises:
            MailboxConnectionError: Si no hay conexión activa
        """
        if not self._connected or not self._connection:
            raise MailboxConnectionError("No hay conexión activa. Llame a connect() primero.")
        
        mailbox = self._config.get("mailbox", "INBOX") if self._config else "INBOX"
        
        try:
            # Seleccionar carpeta
            status, _ = self._connection.select(mailbox, readonly=True)
            if status != "OK":
                raise MailboxConnectionError(f"No se pudo seleccionar la carpeta '{mailbox}'")
            
            # Construir criterio de búsqueda UID
            if start_uid is None:
                # Histórico completo: desde UID 1
                search_criteria = "UID 1:*"
            else:
                # Incremental: solo UIDs mayores al último procesado
                search_criteria = f"UID {start_uid + 1}:*"
            
            # Buscar UIDs
            status, uid_list = self._connection.uid('search', None, search_criteria)
            if status != "OK":
                raise MailboxConnectionError("No se pudo buscar UIDs")
            
            # Convertir UIDs a lista
            if not uid_list or not uid_list[0]:
                return []
            
            uid_bytes_list = uid_list[0].split()
            if not uid_bytes_list:
                return []
            
            # Limitar cantidad por lote
            uid_bytes_list = uid_bytes_list[:batch_size]
            
            messages = []
            for uid_bytes in uid_bytes_list:
                try:
                    uid_str = uid_bytes.decode("utf-8") if isinstance(uid_bytes, bytes) else str(uid_bytes)
                    uid_int = int(uid_str)
                    
                    # Fetch mensaje completo por UID (RFC822)
                    status, msg_data = self._connection.uid('fetch', uid_bytes, "(RFC822)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        continue
                    
                    # Parsear mensaje
                    msg_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else msg_data[0]
                    if isinstance(msg_bytes, tuple):
                        msg_bytes = msg_bytes[1]
                    
                    msg = email.message_from_bytes(msg_bytes)
                    
                    # Extraer headers
                    subject = self._decode_header(msg.get("Subject", ""))
                    from_addr = self._decode_header(msg.get("From", ""))
                    date = msg.get("Date", "")
                    
                    messages.append({
                        "uid": uid_int,  # UID IMAP (único y persistente)
                        "id": uid_str,  # ID como string (compatibilidad)
                        "subject": subject,
                        "from": from_addr,
                        "date": date,
                        "raw": msg_bytes,
                        "_email_message": msg  # Guardar objeto email.message para extraer adjuntos
                    })
                except (ValueError, IndexError, Exception):
                    # Continuar con otros mensajes si uno falla
                    continue
            
            return messages
            
        except imaplib.IMAP4.error as e:
            raise MailboxConnectionError(f"Error IMAP al obtener mensajes por UID: {e}") from e
        except Exception as e:
            raise MailboxConnectionError(f"Error inesperado al obtener mensajes por UID: {e}") from e
    
    def get_attachments(self, message: dict[str, Any]) -> list[AttachmentDTO]:
        """
        Extrae adjuntos de un mensaje.
        
        Args:
            message: Dict con datos del mensaje (retornado por fetch_messages)
            
        Returns:
            Lista de AttachmentDTO con los adjuntos del mensaje
        """
        msg_obj = message.get("_email_message")
        if not msg_obj:
            return []
        
        attachments = []
        
        for part in msg_obj.walk():
            # Verificar si es adjunto
            disposition = part.get("Content-Disposition", "")
            if "attachment" not in disposition.lower():
                # También considerar partes con filename aunque no tengan Content-Disposition
                filename = part.get_filename()
                if not filename:
                    continue
            
            filename = part.get_filename()
            if not filename:
                continue
            
            # Decodificar filename
            filename = self._decode_header(filename)
            
            # Obtener contenido
            try:
                content = part.get_payload(decode=True)
                if not content:
                    continue
                
                content_type = part.get_content_type()
                size_bytes = len(content)
                
                attachments.append({
                    "filename": filename,
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                    "content": content
                })
            except Exception:
                # Saltar adjuntos que no se pueden decodificar
                continue
        
        return attachments
    
    def finalize(self, message: dict[str, Any], *, mark_as_seen: bool = False, move_to: str | None = None) -> None:
        """
        Finaliza el procesamiento de un mensaje (marcar como leído, mover, etc.).
        
        WARNING: UID: Si el mensaje tiene campo "uid", usa UID para las operaciones (más seguro y persistente).
        
        Args:
            message: Dict con datos del mensaje (debe tener "id" o "uid")
            mark_as_seen: Si True, marca el mensaje como leído
            move_to: Si se proporciona, mueve el mensaje a esta carpeta
            
        Raises:
            MailboxConnectionError: Si no hay conexión activa
        """
        if not self._connected or not self._connection:
            raise MailboxConnectionError("No hay conexión activa")
        
        # Preferir UID si está disponible (más seguro y persistente)
        msg_uid = message.get("uid")
        msg_id = message.get("id")
        
        if not msg_uid and not msg_id:
            return
        
        try:
            # Usar UID si está disponible, sino usar ID
            if msg_uid:
                identifier = str(msg_uid).encode("utf-8") if isinstance(msg_uid, int) else str(msg_uid).encode("utf-8")
                use_uid = True
            else:
                identifier = msg_id.encode("utf-8") if isinstance(msg_id, str) else msg_id
                use_uid = False
            
            # Marcar como leído
            if mark_as_seen:
                if use_uid:
                    self._connection.uid('store', identifier, "+FLAGS", "\\Seen")
                else:
                    self._connection.store(identifier, "+FLAGS", "\\Seen")
            
            # Mover a otra carpeta
            if move_to:
                mailbox = self._config.get("mailbox", "INBOX") if self._config else "INBOX"
                # Crear carpeta si no existe (opcional, puede fallar si no hay permisos)
                try:
                    self._connection.create(move_to)
                except imaplib.IMAP4.error:
                    pass  # Carpeta ya existe o sin permisos
                
                # Copiar y luego marcar para borrar (o usar MOVE si está disponible)
                if use_uid:
                    self._connection.uid('copy', identifier, move_to)
                    self._connection.uid('store', identifier, "+FLAGS", "\\Deleted")
                else:
                    self._connection.copy(identifier, move_to)
                    self._connection.store(identifier, "+FLAGS", "\\Deleted")
                self._connection.expunge()
                
        except imaplib.IMAP4.error:
            # No romper el flujo si falla la finalización
            pass
    
    def disconnect(self) -> None:
        """Cierra la conexión con el buzón."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass  # Ignorar errores al desconectar
            finally:
                self._connection = None
                self._connected = False
                self._config = None
    
    @staticmethod
    def _decode_header(header_value: str) -> str:
        """Decodifica un header de email que puede estar codificado."""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string


class StubInboxClient:
    """
    Implementación stub de InboxClient para pruebas y desarrollo.
    
    No se conecta a ningún servidor real; simula respuestas.
    Útil para validar contratos y flujos sin dependencias externas.
    
    Ejemplo:
        client = StubInboxClient()
        client.connect({"host": "stub", "username": "test", ...})
        messages = client.fetch_messages(limit=10)
    """
    
    def __init__(self):
        self._connected = False
        self._config: MailboxConfigDTO | None = None
        self._message_counter = 0
    
    def connect(self, config: MailboxConfigDTO) -> None:
        """
        Simula conexión (solo valida configuración mínima).
        
        Args:
            config: Configuración de conexión
            
        Raises:
            MailboxConnectionError: Si faltan campos requeridos
        """
        required = ["host", "username", "password"]
        missing = [k for k in required if k not in config]
        if missing:
            raise MailboxConnectionError(f"Faltan campos requeridos: {', '.join(missing)}")
        
        self._config = config
        self._connected = True
    
    def fetch_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Simula obtención de mensajes.
        
        Retorna mensajes stub con estructura mínima válida.
        
        Args:
            limit: Número máximo de mensajes
            
        Returns:
            Lista de dicts simulados
            
        Raises:
            MailboxConnectionError: Si no hay conexión activa
        """
        if not self._connected:
            raise MailboxConnectionError("No hay conexión activa. Llame a connect() primero.")
        
        messages = []
        for i in range(min(limit, 5)):  # Stub: máximo 5 mensajes
            self._message_counter += 1
            msg_id = f"stub_msg_{self._message_counter}"
            messages.append({
                "id": msg_id,
                "subject": f"Factura electrónica {self._message_counter}",
                "from": "proveedor@empresa.com",
                "date": "Mon, 15 Jan 2024 10:30:00 +0000",
                "raw": b"From: proveedor@empresa.com\r\nSubject: Factura\r\n\r\nMensaje stub"
            })
        
        return messages
    
    def get_attachments(self, message: dict[str, Any]) -> list[AttachmentDTO]:
        """
        Simula extracción de adjuntos.
        
        Retorna adjuntos stub según el ID del mensaje.
        
        Args:
            message: Dict con datos del mensaje
            
        Returns:
            Lista de AttachmentDTO simulados
        """
        msg_id = message.get("id", "")
        
        # Stub: mensajes pares tienen ZIP, impares tienen XML directo
        if "stub_msg_2" in msg_id or "stub_msg_4" in msg_id:
            return [{
                "filename": "factura.zip",
                "content_type": "application/zip",
                "size_bytes": 1024,
                "content": b"PK\x03\x04..."  # ZIP stub header
            }]
        else:
            return [{
                "filename": "FAC-123.xml",
                "content_type": "application/xml",
                "size_bytes": 512,
                "content": b'<?xml version="1.0"?><Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"><cbc:ID>FAC-123</cbc:ID></Invoice>'
            }]
    
    def finalize(self, message: dict[str, Any], *, mark_as_seen: bool = False, move_to: str | None = None) -> None:
        """
        Simula finalización de procesamiento (no-op en stub).
        
        Args:
            message: Dict con datos del mensaje
            mark_as_seen: Si True, marca como leído (simulado)
            move_to: Carpeta destino (simulado)
        """
        if not self._connected:
            raise MailboxConnectionError("No hay conexión activa")
        # Stub: no hace nada real
    
    def disconnect(self) -> None:
        """Simula desconexión."""
        self._connected = False
        self._config = None
