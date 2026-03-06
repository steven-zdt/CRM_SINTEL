"""
Parser para documentos PDF usando pdfminer.six.

Referencia: https://pdfminersix.readthedocs.io/
"""
from pdfminer.high_level import extract_text
# from pdfminer.high_level import extract_pages  # Para layout fino si se necesita
import re


def parse_pdf_to_chunks(fpath_or_file) -> dict:
    """
    Parsea un PDF y extrae texto estructurado.
    
    Args:
        fpath_or_file: Ruta al archivo o objeto file-like
        
    Returns:
        dict con:
        - 'raw_text': texto completo
        - 'sections': [{'articulo': '...', 'titulo': '...', 'texto': '...'}]
        - 'tables': []  # Opcional si se parsea layout
    """
    # Extraer texto completo
    raw_text = extract_text(fpath_or_file)
    
    # Tokenizar por artículos (heurística: buscar "Artículo" seguido de número)
    sections = []
    
    # Patrón para detectar artículos
    # Ejemplos: "Artículo 1", "ARTÍCULO 2", "Art. 3", "Artículo 1.1"
    article_pattern = re.compile(
        r'(?:Artículo|ARTÍCULO|Art\.?)\s+(\d+(?:\.\d+)?)[\.:]?\s*(.*?)(?=(?:Artículo|ARTÍCULO|Art\.?)\s+\d+|$)',
        re.IGNORECASE | re.DOTALL
    )
    
    matches = list(article_pattern.finditer(raw_text))
    
    for i, match in enumerate(matches):
        article_num = match.group(1)
        content = match.group(2).strip()
        
        # Extraer título si existe (primera línea o línea después del número)
        lines = content.split('\n', 2)
        title = lines[0].strip() if len(lines) > 0 else ""
        texto = '\n'.join(lines[1:]) if len(lines) > 1 else content
        
        sections.append({
            'articulo': f"Artículo {article_num}",
            'titulo': title,
            'texto': texto,
        })
    
    # Si no se encontraron artículos, crear una sección única
    if not sections:
        sections.append({
            'articulo': None,
            'titulo': None,
            'texto': raw_text,
        })
    
    return {
        'raw_text': raw_text,
        'sections': sections,
        'tables': [],  # TODO: Implementar detección de tablas con extract_pages si se necesita
    }
