"""
Choices locales para segmentos DIAN.
"""


def get_segmento_dian_choices():
    """
    Retorna lista de tuplas (value, label) para segmentos DIAN.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (código, nombre)
    """
    return [
        ('GRAN_CONTRIBUYENTE', 'Gran contribuyente'),
        ('MEDIANO_ALTO', 'Contribuyente mediano alto'),
        ('MEDIANO', 'Contribuyente mediano'),
        ('PEQUENO', 'Contribuyente pequeño'),
        ('MICRO', 'Contribuyente micro'),
        ('OTRO', 'Otro / No aplica'),
    ]


def get_segmento_dian_by_codigo(codigo: str):
    """
    Retorna el nombre del segmento DIAN dado su código.
    
    Args:
        codigo: Código del segmento (ej: 'GRAN_CONTRIBUYENTE')
        
    Returns:
        str: Nombre del segmento o None si no existe
    """
    choices = dict(get_segmento_dian_choices())
    return choices.get(codigo)
