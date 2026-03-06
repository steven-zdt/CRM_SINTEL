"""
Detección del tipo de documento fuente.

Detecta el tipo de archivo por extensión, MIME type y tipo declarado.
"""
import mimetypes
from pathlib import Path


EXT_KIND = {
    ".pdf": "PDF",
    ".html": "HTML",
    ".htm": "HTML",
    ".xml": "XML",
    ".xls": "XLS",
    ".xlsx": "XLS",
    ".csv": "CSV",
}


def detect_kind(documento) -> dict:
    """
    Detecta el tipo de documento fuente.
    
    Args:
        documento: Instancia de DocumentoFuente
        
    Returns:
        dict con 'kind' ('PDF'|'HTML'|'XML'|'XLS'|'XLSX'|'OTRO') y 'subkind'
    """
    # Prioridad 1: extensión guardada en el modelo
    if documento.extension:
        kind = EXT_KIND.get(documento.extension.lower(), documento.tipo or "OTRO")
        subkind = documento.extension
    # Prioridad 2: tipo declarado en el modelo
    elif documento.tipo and documento.tipo != "OTRO":
        kind = documento.tipo
        subkind = None
    # Prioridad 3: detección por archivo
    elif documento.archivo:
        file_path = documento.archivo.name
        extension = Path(file_path).suffix.lower()
        kind = EXT_KIND.get(extension, documento.tipo or "OTRO")
        subkind = extension
    # Prioridad 4: detección por URL
    elif documento.url_origen:
        guess, _ = mimetypes.guess_type(documento.url_origen)
        if guess == "text/html":
            kind = "HTML"
        else:
            url_lower = documento.url_origen.lower()
            if url_lower.endswith('.pdf'):
                kind = 'PDF'
            elif url_lower.endswith(('.html', '.htm')):
                kind = 'HTML'
            elif url_lower.endswith('.xml'):
                kind = 'XML'
            elif url_lower.endswith(('.xls', '.xlsx')):
                kind = 'XLS'
            elif url_lower.endswith('.csv'):
                kind = 'CSV'
            else:
                kind = documento.tipo or 'OTRO'
        subkind = None
    else:
        kind = documento.tipo or 'OTRO'
        subkind = None
    
    return {
        'kind': kind,
        'subkind': subkind,
    }
