"""
Utilidades locales para códigos CIIU (Actividad Económica).

Este módulo proporciona funciones básicas para normalizar y validar códigos CIIU
sin depender de catálogos externos.
"""


def normalize_ciiu_code(code: str) -> str:
    """
    Normaliza un código CIIU a 4 dígitos usando zfill.
    
    Args:
        code: Código CIIU (1-4 dígitos)
        
    Returns:
        str: Código normalizado a 4 dígitos (ej: "80" -> "0080")
    """
    if not code:
        return ""
    
    code = str(code).strip()
    if not code.isdigit():
        return code  # Retornar tal cual si no es numérico
    
    # Normalizar a 4 dígitos
    return code.zfill(4)


def validate_ciiu_format(code: str) -> bool:
    """
    Valida el formato básico de un código CIIU.
    
    Args:
        code: Código CIIU a validar
        
    Returns:
        bool: True si el formato es válido (1-4 dígitos numéricos)
    """
    if not code:
        return True  # Vacío es válido (opcional)
    
    code = str(code).strip()
    if not code.isdigit():
        return False
    
    return 1 <= len(code) <= 4
