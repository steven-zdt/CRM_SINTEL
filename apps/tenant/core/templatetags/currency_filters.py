"""
Filtros personalizados para formateo de moneda COP.

# WARNING: v2.40: Filtros para formatear valores monetarios en formato colombiano
con separadores de miles y símbolo de peso.
"""
import re
from decimal import Decimal

from django import template

register = template.Library()


@register.filter(name='currency_cop')
def currency_cop(value):
    """
    Formatea un valor numérico como moneda colombiana (COP).
    
    Ejemplo:
        {{ 1000000|currency_cop }}  -> $ 1.000.000,00
    
    Args:
        value: Valor numérico (int, float, Decimal, str)
    
    Returns:
        str: Valor formateado como moneda COP
    """
    if value is None:
        return "$0,00"
    
    try:
        # Convertir a Decimal para precisión
        if isinstance(value, str):
            # Limpiar caracteres no numéricos excepto punto y coma
            value = re.sub(r'[^\d.,-]', '', value)
            value = value.replace(',', '.')
        
        decimal_value = Decimal(str(value))
        
        # Formatear con separadores de miles (punto) y decimales (coma)
        # Ejemplo: 1000000.50 -> "1.000.000,50"
        formatted = f"{decimal_value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # # WARNING: REPARACIÓN: Sin espacio entre $ y número para evitar saltos de línea en PDF
        return f"${formatted}"
    except (ValueError, TypeError, AttributeError):
        return "$0,00"


@register.filter(name='sanitize_text')
def sanitize_text(value):
    """
    Sanitiza texto para evitar caracteres especiales problemáticos.
    
    Elimina o escapa caracteres problemáticos:
    - Caracteres de control (excepto \n, \r, \t)
    - Caracteres Unicode problemáticos
    
    Args:
        value: Texto a sanitizar
    
    Returns:
        str: Texto sanitizado
    """
    if not value:
        return ""
    
    try:
        # Convertir a string
        text = str(value)
        
        # Eliminar caracteres de control excepto saltos de línea y tabulaciones
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalizar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        # Escapar caracteres HTML problemáticos
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return text.strip()
    except (TypeError, AttributeError):
        return ""
