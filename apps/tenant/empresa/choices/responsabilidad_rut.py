"""
Choices locales para responsabilidades RUT.
"""


def get_responsabilidad_rut_choices():
    """
    Retorna lista de tuplas (value, label) para responsabilidades RUT.
    
    Returns:
        List[Tuple[str, str]]: Lista de opciones (código, nombre)
    """
    return [
        ('47', 'Responsable de IVA como agente de retención'),
        ('48', 'Responsable de IVA'),
        ('49', 'No responsable de IVA'),
        ('52', 'Gran contribuyente'),
        ('13', 'Facturador electrónico'),
    ]


def get_responsabilidad_rut_by_codigo(codigo: str):
    """
    Retorna el nombre de la responsabilidad RUT dado su código.
    
    Args:
        codigo: Código de la responsabilidad (ej: '48')
        
    Returns:
        str: Nombre de la responsabilidad o None si no existe
    """
    choices = dict(get_responsabilidad_rut_choices())
    return choices.get(codigo)


def get_responsabilidades_rut_codigos_validos():
    """
    Retorna lista de códigos válidos de responsabilidades RUT.
    
    Returns:
        List[str]: Lista de códigos válidos
    """
    return [codigo for codigo, _ in get_responsabilidad_rut_choices()]


def validate_responsabilidades_rut(codigos: list):
    """
    Valida que los códigos de responsabilidades RUT sean válidos.
    
    Args:
        codigos: Lista de códigos a validar
        
    Returns:
        bool: True si todos los códigos son válidos
        
    Raises:
        ValueError: Si algún código no es válido
    """
    validos = get_responsabilidades_rut_codigos_validos()
    invalidos = [c for c in codigos if c not in validos]
    if invalidos:
        raise ValueError(f"Códigos de responsabilidades RUT no válidos: {invalidos}")
    return True
