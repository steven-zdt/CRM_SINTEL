"""
Detector de tipo de documento (FASE 2.1).

⚠️ PRINCIPIOS:
- Detecta tipo de documento por cabeceras, heurísticas, contenido parcial
- Retorna media_type y confidence (0.0-1.0)
- Agnóstico del formato: Puede detectar XML, PDF, XLS, CSV, TXT
- Extensible: Permite agregar nuevos detectores sin modificar código existente
"""
from typing import Optional, Dict, Any
import mimetypes


def detect_by_extension(filename: Optional[str]) -> Optional[str]:
    """
    Detecta tipo de documento por extensión de archivo.
    
    Args:
        filename: Nombre del archivo con extensión
        
    Returns:
        str: Tipo detectado (ej: "xml", "pdf", "xlsx") o None
    """
    if not filename:
        return None
    
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else None
    if not ext:
        return None
    
    # Mapeo de extensiones a tipos
    extension_map = {
        'xml': 'xml',
        'pdf': 'pdf',
        'xls': 'xls',
        'xlsx': 'xlsx',
        'csv': 'csv',
        'txt': 'txt',
    }
    
    return extension_map.get(ext)


def detect_by_mime_type(mime_type: Optional[str]) -> Optional[str]:
    """
    Detecta tipo de documento por MIME type.
    
    Args:
        mime_type: MIME type del archivo (ej: "application/xml", "application/pdf")
        
    Returns:
        str: Tipo detectado (ej: "xml", "pdf") o None
    """
    if not mime_type:
        return None
    
    mime_map = {
        'application/xml': 'xml',
        'text/xml': 'xml',
        'application/pdf': 'pdf',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'text/csv': 'csv',
        'text/plain': 'txt',
    }
    
    return mime_map.get(mime_type.lower())


def detect_by_magic_bytes(content: bytes) -> Optional[str]:
    """
    Detecta tipo de documento por magic bytes (firma de archivo).
    
    ⚠️ FASE 2.1: Detecta por cabeceras (%PDF, <?xml, PK\\x03\\x04 para XLSX).
    
    Args:
        content: Primeros bytes del archivo (mínimo 4 bytes recomendado)
        
    Returns:
        str: Tipo detectado (ej: "xml", "pdf", "excel", "csv", "txt") o None
    """
    if not content or len(content) < 4:
        return None
    
    # Magic bytes conocidos (cabeceras)
    if content.startswith(b'<?xml') or content.startswith(b'<'):
        return 'xml'
    elif content.startswith(b'%PDF'):
        return 'pdf'
    elif content.startswith(b'PK\x03\x04'):  # ZIP-based (XLSX, DOCX)
        # Necesitaríamos más análisis para distinguir XLSX de DOCX
        # Por ahora, retornamos "excel" genérico
        return 'excel'
    elif content.startswith(b'\xd0\xcf\x11\xe0'):  # OLE2 (XLS antiguo)
        return 'excel'
    elif content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM (CSV/TXT)
        # Necesitamos más análisis para distinguir CSV de TXT
        return 'csv'  # o 'txt', se refinará con heurísticas
    
    return None


def detect_document_type(
    content: bytes,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detecta el tipo de documento usando múltiples estrategias (FASE 2.1).
    
    Orden de prioridad:
    1. Magic bytes (más confiable, confidence=1.0)
    2. MIME type (confidence=0.8)
    3. Extensión de archivo (confidence=0.6)
    4. Heurísticas de contenido (confidence=0.4-0.6)
    
    Args:
        content: Contenido del documento en bytes (mínimo 4 bytes recomendado)
        filename: Nombre del archivo (opcional)
        mime_type: MIME type del archivo (opcional)
        
    Returns:
        Dict con formato:
        {
            "media_type": "xml|pdf|excel|csv|txt" o None,
            "confidence": 0.0-1.0 (float)
        }
    """
    # 1. Intentar por magic bytes (más confiable, confidence=1.0)
    detected = detect_by_magic_bytes(content)
    if detected:
        # Normalizar xls/xlsx a excel
        if detected in ("xls", "xlsx"):
            detected = "excel"
        return {"media_type": detected, "confidence": 1.0}
    
    # 2. Intentar por MIME type (confidence=0.8)
    detected = detect_by_mime_type(mime_type)
    if detected:
        # Normalizar xls/xlsx a excel
        if detected in ("xls", "xlsx"):
            detected = "excel"
        return {"media_type": detected, "confidence": 0.8}
    
    # 3. Intentar por extensión (confidence=0.6)
    detected = detect_by_extension(filename)
    if detected:
        # Normalizar xls/xlsx a excel
        if detected in ("xls", "xlsx"):
            detected = "excel"
        return {"media_type": detected, "confidence": 0.6}
    
    # 4. Heurísticas de contenido parcial (confidence=0.4-0.6)
    detected, confidence = detect_by_content_heuristics(content)
    if detected:
        return {"media_type": detected, "confidence": confidence}
    
    return {"media_type": None, "confidence": 0.0}


def detect_by_content_heuristics(content: bytes) -> tuple[Optional[str], float]:
    """
    Detecta tipo de documento por heurísticas de contenido parcial.
    
    Args:
        content: Contenido del documento en bytes
        
    Returns:
        Tupla (media_type, confidence):
        - media_type: Tipo detectado o None
        - confidence: Nivel de confianza (0.0-1.0)
    """
    if not content or len(content) < 4:
        return None, 0.0
    
    # Heurística: Buscar patrones XML en los primeros 512 bytes
    sample = content[:512].decode('utf-8', errors='ignore').lower()
    
    # XML: Buscar tags comunes
    xml_indicators = ['<invoice', '<creditnote', '<ubl', '<factura', '<?xml']
    xml_count = sum(1 for indicator in xml_indicators if indicator in sample)
    if xml_count >= 2:
        return "xml", 0.6
    elif xml_count >= 1:
        return "xml", 0.4
    
    # CSV: Buscar delimitadores comunes (coma, punto y coma, tab)
    if len(content) > 10:
        first_line = content[:min(200, len(content))].decode('utf-8', errors='ignore')
        if ',' in first_line or ';' in first_line or '\t' in first_line:
            # Verificar que tenga múltiples columnas
            if first_line.count(',') >= 2 or first_line.count(';') >= 2:
                return "csv", 0.5
    
    # TXT: Si no es ninguno de los anteriores y es texto legible
    try:
        text_sample = content[:100].decode('utf-8', errors='ignore')
        if text_sample.isprintable() and not any(c in text_sample for c in ['<', '{', '[']):
            return "txt", 0.3
    except:
        pass
    
    return None, 0.0
