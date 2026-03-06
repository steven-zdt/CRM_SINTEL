"""
Excepciones específicas del dominio maildigester.

Todas las excepciones del servicio de ingesta de correo deben heredar de estas
clases base para facilitar el manejo de errores y logging.

⚠️ FASE 1: Solo definiciones, sin lógica de negocio.
"""


class MailDigesterError(Exception):
    """Excepción base para todos los errores del servicio maildigester."""
    pass


class MailboxConnectionError(MailDigesterError):
    """
    Error al conectar o autenticar con el buzón de correo.
    
    Ejemplo:
        raise MailboxConnectionError("No se pudo conectar a imap.gmail.com:993")
    """
    pass


class AttachmentTooLarge(MailDigesterError):
    """
    El adjunto excede el límite de tamaño permitido.
    
    Ejemplo:
        raise AttachmentTooLarge("El archivo 'factura.zip' (60MB) excede el límite de 50MB")
    """
    pass


class ArchiveExpansionError(MailDigesterError):
    """
    Error al descomprimir un archivo (ZIP/RAR/7z).
    
    Ejemplo:
        raise ArchiveExpansionError("No se pudo descomprimir 'facturas.zip': archivo corrupto")
    """
    pass


class InvalidXMLDocument(MailDigesterError):
    """
    El documento XML no es válido o no es un UBL 2.1.
    
    Ejemplo:
        raise InvalidXMLDocument("El XML no contiene un elemento Invoice válido")
    """
    pass


class PathTraversalError(MailDigesterError):
    """
    Intento de path traversal detectado en nombre de archivo.
    
    ⚠️ SEGURIDAD: Se rechaza cualquier ruta que contenga '..' o rutas absolutas.
    
    Ejemplo:
        raise PathTraversalError("Nombre de archivo rechazado: '../../etc/passwd'")
    """
    pass


class MimeTypeMismatch(MailDigesterError):
    """
    El tipo MIME declarado no coincide con el contenido real del archivo.
    
    Ejemplo:
        raise MimeTypeMismatch("Content-Type dice 'application/xml' pero el archivo es ZIP")
    """
    pass
