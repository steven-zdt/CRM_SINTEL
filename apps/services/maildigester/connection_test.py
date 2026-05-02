"""
Servicio para probar conexión a buzones de correo sin persistir datos.

WARNING: v2.37: Alineado con arquitectura Service Layer y SSoT.
- Desacoplado de modelos y vistas
- No persiste datos
- Usa RealIMAPClient para pruebas reales
- Manejo de errores explícito
"""
import logging
from typing import Any

from .exceptions import MailboxConnectionError
from .inbox_client import RealIMAPClient

log = logging.getLogger("mailinbox.api")


def maildigester_test_connection(config: dict[str, Any]) -> tuple[bool, str]:
    """
    Prueba conexión a buzón de correo sin persistir datos.
    
    WARNING: SEGURIDAD: No persiste credenciales, solo prueba conexión.
    WARNING: DESACOPLADO: No depende de modelos ni vistas.
    
    Args:
        config: Dict con configuración de conexión:
            - host: str (ej: "imap.gmail.com")
            - port: int (ej: 993)
            - protocol: str ("imap" o "pop3")
            - username: str (email o usuario)
            - password: str (contraseña o app password)
            - use_ssl: bool (True para IMAPS, False para IMAP)
            - use_starttls: bool (opcional, para IMAP con STARTTLS)
    
    Returns:
        Tuple[bool, str]: (ok, message)
            - ok: True si la conexión fue exitosa, False si falló
            - message: Mensaje descriptivo del resultado
    
    Ejemplo:
        config = {
            "host": "imap.gmail.com",
            "port": 993,
            "protocol": "imap",
            "username": "user@gmail.com",
            "password": "app_password",
            "use_ssl": True
        }
        ok, message = maildigester_test_connection(config)
    """
    # Validar campos requeridos
    required_fields = ['host', 'port', 'protocol', 'username', 'password', 'use_ssl']
    missing = [f for f in required_fields if f not in config]
    if missing:
        error_msg = f"Faltan campos requeridos: {', '.join(missing)}"
        log.warning(f"[maildigester_test_connection] {error_msg}")
        return False, error_msg
    
    host = config['host']
    port = config['port']
    protocol = config['protocol']
    username = config['username']
    password = config['password']  # WARNING: No loguear password
    use_ssl = config['use_ssl']
    use_starttls = config.get('use_starttls', False)
    
    # Validar protocolo
    if protocol not in ['imap', 'pop3']:
        error_msg = f"Protocolo '{protocol}' no soportado. Solo se soporta 'imap' o 'pop3'."
        log.warning(f"[maildigester_test_connection] {error_msg}")
        return False, error_msg
    
    # Por ahora solo soportamos IMAP (POP3 pendiente)
    if protocol != 'imap':
        error_msg = f"Protocolo '{protocol}' aún no está implementado. Solo IMAP está disponible."
        log.warning(f"[maildigester_test_connection] {error_msg}")
        return False, error_msg
    
    # Preparar configuración para RealIMAPClient
    mailbox_config = {
        'host': host,
        'port': port,
        'protocol': protocol,
        'username': username,
        'password': password,
        'ssl': use_ssl,
        'starttls': use_starttls,
        'mailbox': 'INBOX'  # Carpeta por defecto para prueba
    }
    
    client = None
    try:
        # Intentar conectar y autenticar
        log.info(f"[maildigester_test_connection] Probando conexión a {username}@{host}:{port} (SSL: {use_ssl})")
        
        client = RealIMAPClient()
        client.connect(mailbox_config)
        
        # Si llegamos aquí, la conexión fue exitosa
        success_msg = f"Conexión exitosa a {host}:{port}"
        log.info(f"[maildigester_test_connection] Test connection OK: {username}@{host}:{port}")
        return True, success_msg
        
    except MailboxConnectionError as e:
        # Error de conexión o autenticación
        error_msg = f"Error de conexión: {str(e)}"
        log.warning(f"[maildigester_test_connection] Test connection FAILED: {username}@{host}:{port} - {error_msg}")
        return False, error_msg
        
    except Exception as e:
        # Error inesperado
        error_msg = f"Error inesperado: {str(e)}"
        log.error(f"[maildigester_test_connection] Error inesperado: {error_msg}", exc_info=True)
        return False, error_msg
        
    finally:
        # Asegurar desconexión
        if client:
            try:
                client.disconnect()
            except Exception:
                pass  # Ignorar errores al desconectar
