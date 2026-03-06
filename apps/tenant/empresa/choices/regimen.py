"""
Choices locales para regímenes de renta.
"""


def get_regimen_choices():
    """
    Retorna lista de tuplas (value, label) para regímenes de renta.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (código, nombre)
    """
    return [
        ('ORDINARIO', 'Régimen Ordinario'),
        ('ESPECIAL', 'Régimen Tributario Especial (RTE)'),
        ('SIMPLE', 'Régimen Simple de Tributación (SIMPLE)'),
    ]


def get_regimen_by_codigo(codigo: str):
    """
    Retorna el nombre del régimen dado su código.
    
    Args:
        codigo: Código del régimen (ej: 'ORDINARIO')
        
    Returns:
        str: Nombre del régimen o None si no existe
    """
    choices = dict(get_regimen_choices())
    return choices.get(codigo)
