"""
Tokenizador para extraer entidades estructuradas de texto.

Extrae: Artículo, Impuesto, Tema, Vigencia
"""
import re
from typing import List, Dict, Any
from datetime import datetime


def tokenize_sections(chunks: dict) -> List[Dict[str, Any]]:
    """
    Tokeniza secciones de texto para extraer entidades.
    
    Args:
        chunks: Dict con 'sections' o 'items' o 'records' según el tipo de parser
        
    Returns:
        Lista de tokens con estructura:
        {
            'articulo': str | None,
            'impuesto': str | None,
            'tema': str | None,
            'vigencia_desde': date | None,
            'vigencia_hasta': date | None,
            'texto': str,
            'referencias': List[str],
        }
    """
    tokens = []
    
    # Procesar según el tipo de chunks
    if 'sections' in chunks:
        # De PDF o HTML
        for section in chunks.get('sections', []):
            token = _tokenize_section(section)
            tokens.append(token)
    
    elif 'items' in chunks:
        # De XML
        for item in chunks.get('items', []):
            token = _tokenize_xml_item(item)
            tokens.append(token)
    
    elif 'records' in chunks:
        # De Excel
        for record in chunks.get('records', []):
            token = _tokenize_excel_record(record)
            tokens.append(token)
    
    else:
        # Fallback: usar raw_text si existe
        raw_text = chunks.get('raw_text') or chunks.get('texto', '')
        if raw_text:
            tokens.append(_tokenize_text(raw_text))
    
    return tokens


def _tokenize_section(section: dict) -> Dict[str, Any]:
    """Tokeniza una sección de PDF/HTML."""
    texto = section.get('texto', '') or section.get('paragraphs', [])
    if isinstance(texto, list):
        texto = ' '.join(texto)
    
    titulo = section.get('titulo') or section.get('articulo', '')
    
    return _tokenize_text(texto, titulo)


def _tokenize_xml_item(item: dict) -> Dict[str, Any]:
    """Tokeniza un item de XML."""
    texto = item.get('text', '')
    tag = item.get('tag', '')
    attrs = item.get('attributes', {})
    
    # Extraer información de atributos
    vigencia_desde = _parse_date(attrs.get('vigencia_desde') or attrs.get('desde'))
    vigencia_hasta = _parse_date(attrs.get('vigencia_hasta') or attrs.get('hasta'))
    
    return {
        'articulo': None,
        'impuesto': tag if tag in ('Impuesto', 'Retencion', 'Tarifa') else None,
        'tema': attrs.get('tema') or attrs.get('nombre'),
        'vigencia_desde': vigencia_desde,
        'vigencia_hasta': vigencia_hasta,
        'texto': texto,
        'referencias': _extract_references(texto),
    }


def _tokenize_excel_record(record: dict) -> Dict[str, Any]:
    """Tokeniza un registro de Excel."""
    # Mapear columnas comunes
    texto = ' '.join([str(v) for v in record.values() if v])
    
    return {
        'articulo': record.get('articulo') or record.get('art'),
        'impuesto': record.get('impuesto') or record.get('tipo_impuesto'),
        'tema': record.get('tema') or record.get('concepto') or record.get('nombre'),
        'vigencia_desde': _parse_date(record.get('vigencia_desde') or record.get('desde')),
        'vigencia_hasta': _parse_date(record.get('vigencia_hasta') or record.get('hasta')),
        'texto': texto,
        'referencias': _extract_references(texto),
    }


def _tokenize_text(texto: str, titulo: str = '') -> Dict[str, Any]:
    """Tokeniza texto plano extrayendo entidades."""
    full_text = f"{titulo} {texto}".strip()
    
    # Extraer artículo
    articulo = None
    article_match = re.search(r'(?:Artículo|ARTÍCULO|Art\.?)\s+(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
    if article_match:
        articulo = article_match.group(0)
    
    # Extraer impuestos mencionados (heurística)
    impuesto = None
    impuesto_keywords = ['IVA', 'Retención', 'ICA', 'Renta', 'CREE', 'Impuesto']
    for keyword in impuesto_keywords:
        if keyword.lower() in full_text.lower():
            impuesto = keyword
            break
    
    # Extraer fechas de vigencia
    vigencia_desde = _extract_vigencia_desde(full_text)
    vigencia_hasta = _extract_vigencia_hasta(full_text)
    
    return {
        'articulo': articulo,
        'impuesto': impuesto,
        'tema': titulo if titulo else None,
        'vigencia_desde': vigencia_desde,
        'vigencia_hasta': vigencia_hasta,
        'texto': full_text,
        'referencias': _extract_references(full_text),
    }


def _extract_references(texto: str) -> List[str]:
    """Extrae referencias a otros artículos/normas."""
    references = []
    
    # Patrón para referencias: "Artículo X", "Ley X de Y", "Decreto X"
    patterns = [
        r'(?:Artículo|Art\.?)\s+\d+',
        r'Ley\s+\d+\s+de\s+\d{4}',
        r'Decreto\s+\d+\s+de\s+\d{4}',
        r'Resolución\s+\d+',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, texto, re.IGNORECASE)
        references.extend(matches)
    
    return list(set(references))  # Eliminar duplicados


def _extract_vigencia_desde(texto: str):
    """Extrae fecha de inicio de vigencia."""
    # Patrones comunes: "vigente desde", "a partir de", "desde el"
    patterns = [
        r'(?:vigente\s+)?desde\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'a\s+partir\s+de\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'desde\s+el\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            return _parse_date(match.group(1))
    
    return None


def _extract_vigencia_hasta(texto: str):
    """Extrae fecha de fin de vigencia."""
    # Patrones comunes: "vigente hasta", "hasta el", "válido hasta"
    patterns = [
        r'(?:vigente\s+)?hasta\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'hasta\s+el\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'válido\s+hasta\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            return _parse_date(match.group(1))
    
    return None


def _parse_date(date_str: Any) -> Any:
    """Parsea una fecha desde string."""
    if not date_str:
        return None
    
    if isinstance(date_str, datetime):
        return date_str.date()
    
    if hasattr(date_str, 'date'):
        return date_str.date()
    
    # Intentar parsear string
    if isinstance(date_str, str):
        # Formatos comunes: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
        formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
    
    return None
