"""
Utilidades para la app tenants.

Funciones helper para normalización y validación de datos.
"""
import re
from django.conf import settings
from django.core.exceptions import ValidationError

def normalize_domain(domain: str) -> str:
    """
    Normaliza un dominio a FQDN puro (Fully Qualified Domain Name).
    
    ⚠️ CONFORME A DOCUMENTACIÓN OFICIAL DE DJANGO-TENANTS:
    Los dominios en Domain.domain deben ser FQDN puro sin puerto, sin protocolo,
    sin www, sin rutas. Esta función garantiza que el dominio esté listo para
    ser usado por django-tenants para routing por hostname.
    
    Reglas de normalización:
    - Convertir a minúsculas
    - Eliminar espacios en blanco al inicio/final (strip)
    - Eliminar prefijos de protocolo: https://, http://
    - Eliminar prefijos www. (opcional, para estandarizar)
    - Eliminar barras finales / y rutas
    - Eliminar puertos (ej: :8000) SIEMPRE (según doc oficial)
    
    Args:
        domain: Dominio a normalizar (puede venir con protocolo, rutas, puerto, etc.)
    
    Returns:
        str: Dominio normalizado (FQDN puro, minúsculas, sin protocolo, sin puerto, sin rutas)
        Ejemplo: "cliente.sintel.com" (nunca "cliente.sintel.com:8000")
    
    Examples:
        >>> normalize_domain("HTTPS://Mi.Empresa.Com/")
        'mi.empresa.com'
        >>> normalize_domain("http://www.cliente.sintel.com:8000/admin/")
        'cliente.sintel.com'  # Sin puerto, sin www, sin protocolo, sin rutas
        >>> normalize_domain("  ejemplo.com  ")
        'ejemplo.com'
    """
    if not domain:
        return ""
    
    # Convertir a string y eliminar espacios
    normalized = str(domain).strip()
    
    # Eliminar protocolos (http://, https://)
    normalized = re.sub(r'^https?://', '', normalized, flags=re.IGNORECASE)
    
    # Eliminar prefijo www. (opcional, para estandarizar)
    normalized = re.sub(r'^www\.', '', normalized, flags=re.IGNORECASE)
    
    # Eliminar rutas y parámetros (todo después de /)
    # Ejemplo: ejemplo.com:8000/admin/login/ -> ejemplo.com:8000
    if '/' in normalized:
        normalized = normalized.split('/')[0]
    
    # ⚠️ ESTÁNDAR: Puerto 80 (HTTP) - SIEMPRE eliminar el puerto
    # Los dominios en la BD NUNCA deben tener puerto
    # El middleware ForceNoPortMiddleware normaliza HTTP_HOST antes de django-tenants
    if ':' in normalized:
        # Eliminar el puerto (siempre, sin importar DEBUG o Producción)
        # Ejemplo: cliente.sintel.com:8000 -> cliente.sintel.com
        normalized = normalized.split(':')[0]
    
    # Eliminar espacios finales que puedan quedar
    normalized = normalized.strip()
    
    # Convertir a minúsculas
    normalized = normalized.lower()
    
    return normalized


def validate_fqdn(domain: str) -> bool:
    """
    Valida que el dominio sea un FQDN válido.
    
    Un FQDN válido debe:
    - Contener al menos un punto (ej: sintel.com)
    - No contener espacios
    - No contener caracteres especiales excepto guiones y puntos
    - Tener máximo 253 caracteres (RFC 1035)
    
    Args:
        domain: Dominio a validar
    
    Returns:
        bool: True si es un FQDN válido, False en caso contrario
    """
    if not domain:
        return False
    
    # Longitud máxima según RFC 1035
    if len(domain) > 253:
        return False
    
    # Debe contener al menos un punto (para ser FQDN)
    if '.' not in domain:
        return False
    
    # No debe contener espacios
    if ' ' in domain:
        return False
    
    # Patrón básico de FQDN: letras, números, guiones, puntos
    # Cada parte del dominio debe ser válida
    pattern = r'^([a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$'
    
    return bool(re.match(pattern, domain, re.IGNORECASE))


def validate_schema_name(schema_name: str) -> None:
    """
    Valida que un schema_name sea seguro para PostgreSQL.

    Reglas:
    - Solo letras minúsculas, números y guiones bajos (_).
    - Debe comenzar con una letra.
    - Longitud máxima de 63 caracteres.
    - No puede ser un nombre de esquema reservado.

    Lanza ValidationError si la validación falla.
    """
    if not schema_name:
        raise ValidationError("El schema_name es requerido.")

    value = str(schema_name).strip()

    # Longitud máxima de PostgreSQL
    if len(value) > 63:
        raise ValidationError("El schema_name no puede exceder 63 caracteres.")

    # Debe comenzar con una letra y solo contener letras minúsculas, números y guiones bajos
    if not re.match(r'^[a-z][a-z0-9_]*$', value):
        raise ValidationError(
            "El schema_name solo puede contener letras minúsculas, números y guiones bajos (_), "
            "y debe comenzar con una letra."
        )

    # Nombres de esquemas reservados
    reserved_names = {
        "public",
        "pg_catalog",
        "information_schema",
    }
    if value in reserved_names:
        raise ValidationError(f"El schema_name '{value}' está reservado y no puede ser utilizado.")

    # Si todo es válido, no retorna nada (None)
