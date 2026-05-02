"""
Helpers para cifrado de secretos usando Fernet.

WARNING: SEGURIDAD: Cifrado simétrico para passwords y secretos.
WARNING: CONFIGURACIÓN: Requiere MAILCFG_FERNET_KEY en variables de entorno.
WARNING: FALLBACK: En desarrollo, genera clave automática si no está configurada.
"""
import logging
import os

from cryptography.fernet import Fernet
from django.conf import settings

log = logging.getLogger("security.crypto")

# Clave Fernet (32 bytes base64-encoded)
_FERNET_KEY = None


def get_fernet_key():
    """
    Obtiene la clave Fernet desde variables de entorno o genera una para desarrollo.
    
    WARNING: PRODUCCIÓN: Debe estar configurada MAILCFG_FERNET_KEY en env.
    WARNING: DESARROLLO: Genera clave automática si no está configurada (no persistente).
    """
    global _FERNET_KEY
    
    if _FERNET_KEY is not None:
        return _FERNET_KEY
    
    # Intentar obtener desde variables de entorno
    key_str = os.environ.get('MAILCFG_FERNET_KEY')
    
    if key_str:
        try:
            _FERNET_KEY = key_str.encode()
            # Validar que sea una clave Fernet válida
            Fernet(_FERNET_KEY)
            log.info("Clave Fernet cargada desde MAILCFG_FERNET_KEY")
            return _FERNET_KEY
        except Exception as e:
            log.error(f"Error validando MAILCFG_FERNET_KEY: {e}")
            raise ValueError("MAILCFG_FERNET_KEY no es una clave Fernet válida")
    
    # Fallback: generar clave para desarrollo (no persistente)
    if settings.DEBUG:
        _FERNET_KEY = Fernet.generate_key()
        log.warning(
            "WARNING: DESARROLLO: Generada clave Fernet automática (no persistente). "
            "En producción, configure MAILCFG_FERNET_KEY en variables de entorno."
        )
        return _FERNET_KEY
    
    # Producción sin clave: error
    raise ValueError(
        "MAILCFG_FERNET_KEY no configurada. "
        "Configure esta variable en producción para cifrar passwords."
    )


def encrypt_password(password: str) -> str:
    """
    Cifra un password usando Fernet.
    
    Args:
        password: Password en texto plano
    
    Returns:
        Password cifrado (base64-encoded)
    
    Raises:
        ValueError: Si no se puede obtener la clave Fernet
    """
    if not password:
        return password
    
    try:
        key = get_fernet_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(password.encode())
        return encrypted.decode()
    except Exception as e:
        log.error(f"Error cifrando password: {e}")
        raise


def decrypt_password(encrypted_password: str) -> str:
    """
    Descifra un password usando Fernet.
    
    Args:
        encrypted_password: Password cifrado (base64-encoded)
    
    Returns:
        Password en texto plano
    
    Raises:
        ValueError: Si no se puede descifrar (clave incorrecta o datos corruptos)
    """
    if not encrypted_password:
        return encrypted_password
    
    try:
        key = get_fernet_key()
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        log.error(f"Error descifrando password: {e}")
        raise ValueError("No se pudo descifrar el password (clave incorrecta o datos corruptos)")
