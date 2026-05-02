"""
Servicio de procesamiento de correos electrónicos (MailDigester).

Este servicio procesa correos electrónicos para extraer facturas XML adjuntas
y procesarlas usando el servicio de XML Parser.

WARNING: IMPORTANTE: Usa schema_context para procesar correos en el contexto del tenant correcto.
"""
import email
import imaplib
from email.header import decode_header
from typing import Any

from django_tenants.utils import schema_context

# TODO: Migrar a pipeline universal - usar ingest_document en lugar de procesar_factura_xml
# from apps.services.document_ingest.ingest_service import ingest_document


def decodificar_header(header_value: str) -> str:
    """
    Decodifica un header de email que puede estar codificado.
    
    Args:
        header_value: Valor del header a decodificar
        
    Returns:
        String decodificado
    """
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


def extraer_adjuntos_xml(mensaje: email.message.Message) -> list[dict[str, Any]]:
    """
    Extrae archivos XML adjuntos de un mensaje de email.
    
    Args:
        mensaje: Mensaje de email (email.message.Message)
        
    Returns:
        Lista de diccionarios con información de los adjuntos XML
    """
    adjuntos_xml = []
    
    for part in mensaje.walk():
        if part.get_content_disposition() == 'attachment':
            filename = part.get_filename()
            if filename and filename.lower().endswith('.xml'):
                contenido = part.get_payload(decode=True)
                adjuntos_xml.append({
                    'filename': decodificar_header(filename),
                    'content': contenido,
                    'content_type': part.get_content_type(),
                })
    
    return adjuntos_xml


def procesar_correo(
    schema_name: str,
    mensaje: email.message.Message,
    procesar_xml: bool = True
) -> dict[str, Any]:
    """
    Procesa un correo electrónico en el contexto de un tenant específico.
    
    WARNING: IMPORTANTE: Usa schema_context para procesar en el esquema del tenant correcto.
    
    Args:
        schema_name: Nombre del esquema del tenant
        mensaje: Mensaje de email a procesar
        procesar_xml: Si True, procesa los XML adjuntos usando xml_parser
        
    Returns:
        Diccionario con información del procesamiento
    """
    resultado = {
        'procesado': False,
        'adjuntos_xml': [],
        'facturas_procesadas': [],
        'errores': [],
    }
    
    # Extraer información del correo
    asunto = decodificar_header(mensaje.get('Subject', ''))
    remitente = decodificar_header(mensaje.get('From', ''))
    fecha = mensaje.get('Date', '')
    
    # Extraer adjuntos XML
    adjuntos = extraer_adjuntos_xml(mensaje)
    resultado['adjuntos_xml'] = [adj['filename'] for adj in adjuntos]
    
    if not adjuntos:
        resultado['errores'].append('No se encontraron archivos XML adjuntos')
        return resultado
    
    # Procesar en el contexto del tenant
    with schema_context(schema_name):
        for adjunto in adjuntos:
            try:
                if procesar_xml:
                    # TODO: Migrar a pipeline universal
                    # Por ahora, usar ingest_document del pipeline universal
                    try:
                        from apps.services.document_ingest.ingest_service import ingest_document
                        result, status_code = ingest_document(
                            content=adjunto['content'],
                            filename=adjunto['filename'],
                            preview=False,
                            async_mode=False
                        )
                        # Adaptar resultado al formato esperado
                        if result.get("persisted"):
                            factura_resultado = {
                                "dto": result.get("dto", {}),
                                "persisted": True,
                                "id": result.get("id"),
                                "numero": result.get("numero"),
                                "procesado": True,
                            }
                        else:
                            factura_resultado = {
                                "dto": result.get("dto", {}),
                                "persisted": False,
                                "procesado": False,
                                "error": result.get("error"),
                                "message": result.get("message"),
                            }
                        resultado['facturas_procesadas'].append(factura_resultado)
                    except ImportError:
                        # Fallback si el pipeline universal no está disponible
                        resultado['facturas_procesadas'].append({
                            'filename': adjunto['filename'],
                            'procesado': False,
                            'mensaje': 'Pipeline universal no disponible'
                        })
                else:
                    # Solo registrar el adjunto sin procesar
                    resultado['facturas_procesadas'].append({
                        'filename': adjunto['filename'],
                        'procesado': False,
                        'mensaje': 'Procesamiento XML deshabilitado'
                    })
            except Exception as e:
                resultado['errores'].append({
                    'filename': adjunto['filename'],
                    'error': str(e)
                })
    
    resultado['procesado'] = len(resultado['errores']) == 0
    resultado['asunto'] = asunto
    resultado['remitente'] = remitente
    resultado['fecha'] = fecha
    
    return resultado


def conectar_imap(
    servidor: str,
    usuario: str,
    password: str,
    puerto: int = 993,
    usar_ssl: bool = True
) -> imaplib.IMAP4_SSL:
    """
    Conecta a un servidor IMAP.
    
    Args:
        servidor: Dirección del servidor IMAP
        usuario: Usuario para autenticación
        password: Contraseña para autenticación
        puerto: Puerto del servidor (default: 993 para SSL)
        usar_ssl: Si True, usa SSL (default: True)
        
    Returns:
        Conexión IMAP
    """
    if usar_ssl:
        conexion = imaplib.IMAP4_SSL(servidor, puerto)
    else:
        conexion = imaplib.IMAP4(servidor, puerto)
    
    conexion.login(usuario, password)
    return conexion


def obtener_correos_no_leidos(
    conexion: imaplib.IMAP4_SSL,
    carpeta: str = 'INBOX'
) -> list[bytes]:
    """
    Obtiene los IDs de correos no leídos.
    
    Args:
        conexion: Conexión IMAP
        carpeta: Carpeta a revisar (default: 'INBOX')
        
    Returns:
        Lista de IDs de correos no leídos
    """
    conexion.select(carpeta)
    status, mensajes = conexion.search(None, 'UNSEEN')
    
    if status == 'OK':
        return mensajes[0].split()
    return []


def obtener_mensaje_por_id(
    conexion: imaplib.IMAP4_SSL,
    mensaje_id: bytes
) -> email.message.Message | None:
    """
    Obtiene un mensaje de email por su ID.
    
    Args:
        conexion: Conexión IMAP
        mensaje_id: ID del mensaje
        
    Returns:
        Mensaje de email o None si no se encuentra
    """
    status, datos = conexion.fetch(mensaje_id, '(RFC822)')
    
    if status == 'OK' and datos:
        mensaje_bytes = datos[0][1]
        return email.message_from_bytes(mensaje_bytes)
    return None
