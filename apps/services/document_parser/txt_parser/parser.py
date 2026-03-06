"""
Parser para documentos de texto plano (TXT) (FASE 2.3).

⚠️ PRINCIPIOS:
- Heurísticas para extraer datos estructurados
- Retorna DTO JSON unificado según apps/services/document_parser/dto.py
"""
from typing import Dict, Any, Optional
import re
from apps.services.document_parser.normalizers import normalize_txt, sanitize_text, normalize_nit, normalize_currency, normalize_numeric_to_decimal_string


def parse_to_dto(file_bytes: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Parsea un documento TXT a DTO JSON unificado.
    
    ⚠️ FASE 2.3: Heurísticas → DTO.
    ⚠️ REVERSIÓN: Recibe contenido NORMALIZADO (string UTF-8) del normalizer.
    
    Args:
        file_bytes: Contenido del archivo TXT normalizado (bytes o str)
        filename: Nombre del archivo (opcional)
        
    Returns:
        Dict con estructura DTO JSON unificado
        
    Raises:
        ValueError: Si el TXT no es válido o no se puede parsear
    """
    # ⚠️ REVERSIÓN: El normalizer ya entregó TXT como string UTF-8 normalizado
    # Si viene como string, usarlo directamente; si viene como bytes, decodificar
    try:
        if isinstance(file_bytes, str):
            text = file_bytes  # Ya está normalizado
        else:
            text = file_bytes.decode('utf-8', errors='replace')
        
        # Aplicar normalización adicional si es necesario (whitespace, sanitización)
        text = normalize_txt(text)
    except Exception as e:
        raise ValueError(f"Error al leer TXT: {str(e)}")
    
    if not text:
        raise ValueError("El archivo TXT está vacío")
    
    # Detectar tipo de documento (Invoice o CreditNote) por heurísticas
    is_credit_note = _is_credit_note(text)
    document_type = "creditnote.ubl21" if is_credit_note else "invoice.ubl21"
    
    # Extraer datos usando heurísticas (patrones comunes)
    numero = _extract_numero(text)
    cufe = _extract_cufe(text)
    fecha_emision = _extract_fecha_emision(text)
    
    # Emisor
    emisor_nit = _extract_emisor_nit(text)
    emisor_razon_social = _extract_emisor_razon_social(text)
    
    # Receptor
    receptor_nit = _extract_receptor_nit(text)
    receptor_razon_social = _extract_receptor_razon_social(text)
    
    # Totales
    totales = _extract_totales(text)
    
    # Referencia (solo para CreditNote)
    referencia = None
    motivo = ""
    if is_credit_note:
        ref_numero = _extract_referencia(text)
        if ref_numero:
            referencia = {
                "numero": sanitize_text(ref_numero),
                "tipo": "invoice",
            }
        motivo = _extract_motivo(text)
    
    # Construir DTO (FASE 3: incluir type base para compatibilidad)
    # Extraer tipo base del document_type
    type_base = document_type.split('.')[0] if '.' in document_type else document_type
    
    dto = {
        "document_type": document_type,
        "type": type_base,  # Tipo base para router de validaciones
        "numero": numero or "",
        "identificadores": {
            "cufe": cufe or "",
            "numero": numero or "",
        },
        "fecha_emision": fecha_emision or "",
        "emisor": {
            "nit": normalize_nit(emisor_nit) or "",
            "razon_social": sanitize_text(emisor_razon_social) or "",
        },
        "receptor": {
            "nit": normalize_nit(receptor_nit) or "",
            "razon_social": sanitize_text(receptor_razon_social) or "",
        },
        "totales": {
            "moneda": totales.get("moneda", "COP"),
            "subtotal": normalize_numeric_to_decimal_string(totales.get("subtotal", "0.00")),
            "impuestos": normalize_numeric_to_decimal_string(totales.get("impuestos", "0.00")),
            "total": normalize_numeric_to_decimal_string(totales.get("total", "0.00")),
        },
    }
    
    if referencia:
        dto["referencia"] = referencia
    
    if motivo:
        dto["motivo"] = motivo
    
    return dto


def _is_credit_note(text: str) -> bool:
    """Detecta si el TXT es una Nota Crédito."""
    patterns = [
        r'nota\s*cr[ée]dito',
        r'credit\s*note',
        r'nc\s*\d+',
    ]
    text_lower = text.lower()
    return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns)


def _extract_numero(text: str) -> Optional[str]:
    """Extrae número de factura/nota crédito."""
    patterns = [
        r'factura\s*(?:n[úu]m[ée]ro|no\.?|#)\s*:?\s*([A-Z0-9\-]+)',
        r'numero\s*:?\s*([A-Z0-9\-]+)',
        r'no\.?\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1))
    return None


def _extract_cufe(text: str) -> Optional[str]:
    """Extrae CUFE/CUDE."""
    patterns = [
        r'cufe\s*:?\s*([A-Z0-9\-]+)',
        r'cude\s*:?\s*([A-Z0-9\-]+)',
        r'uuid\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1))
    return None


def _extract_fecha_emision(text: str) -> Optional[str]:
    """Extrae fecha de emisión."""
    patterns = [
        r'fecha\s*(?:de\s*)?emisi[óo]n\s*:?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
        r'(\d{4}[-/]\d{2}[-/]\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fecha = match.group(1).replace('/', '-')
            return f"{fecha}T00:00:00-05:00"
    return None


def _extract_emisor_nit(text: str) -> Optional[str]:
    """Extrae NIT del emisor."""
    patterns = [
        r'nit\s*(?:emisor|proveedor)?\s*:?\s*([0-9\-]+)',
        r'emisor.*?nit\s*:?\s*([0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_emisor_razon_social(text: str) -> Optional[str]:
    """Extrae razón social del emisor."""
    patterns = [
        r'raz[óo]n\s*social\s*(?:emisor)?\s*:?\s*([^\n]+)',
        r'emisor\s*:?\s*([^\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1))
    return None


def _extract_receptor_nit(text: str) -> Optional[str]:
    """Extrae NIT del receptor."""
    patterns = [
        r'nit\s*(?:receptor|cliente)?\s*:?\s*([0-9\-]+)',
        r'receptor.*?nit\s*:?\s*([0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_receptor_razon_social(text: str) -> Optional[str]:
    """Extrae razón social del receptor."""
    patterns = [
        r'raz[óo]n\s*social\s*(?:receptor)?\s*:?\s*([^\n]+)',
        r'receptor\s*:?\s*([^\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1))
    return None


def _extract_totales(text: str) -> Dict[str, Any]:
    """Extrae totales monetarios."""
    patterns = {
        "subtotal": [
            r'subtotal\s*:?\s*\$?\s*([0-9,\.]+)',
            r'sub\s*total\s*:?\s*\$?\s*([0-9,\.]+)',
        ],
        "impuestos": [
            r'impuestos?\s*:?\s*\$?\s*([0-9,\.]+)',
            r'iva\s*:?\s*\$?\s*([0-9,\.]+)',
        ],
        "total": [
            r'total\s*:?\s*\$?\s*([0-9,\.]+)',
            r'valor\s*total\s*:?\s*\$?\s*([0-9,\.]+)',
        ],
    }
    
    totales = {"moneda": "COP", "subtotal": "0.00", "impuestos": "0.00", "total": "0.00"}
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                totales[key] = value
                break
    
    return totales


def _extract_referencia(text: str) -> Optional[str]:
    """Extrae referencia a factura (para Notas Crédito)."""
    patterns = [
        r'factura\s*referenciada\s*:?\s*([A-Z0-9\-]+)',
        r'referencia\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1))
    return None


def _extract_motivo(text: str) -> str:
    """Extrae motivo de la nota crédito."""
    patterns = [
        r'motivo\s*:?\s*([^\n]+)',
        r'raz[óo]n\s*:?\s*([^\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return sanitize_text(match.group(1))
    return ""
