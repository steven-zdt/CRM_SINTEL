"""
Parser para documentos PDF (FASE 2.3 + FASE 1 - Servicios Globales).

⚠️ PRINCIPIOS:
- Extracción de texto usando pdfminer
- Regex + tablas DIAN para extraer datos estructurados
- Retorna DTO JSON unificado según apps/services/document_parser/dto.py
- ⚠️ FASE 1: Mejoras específicas para Notas de Crédito en PDF
"""
from typing import Dict, Any, Optional
import re
from apps.services.document_parser.normalizers import extract_text_from_pdf, sanitize_text, normalize_nit, normalize_currency, normalize_numeric_to_decimal_string


def parse_to_dto(file_bytes: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Parsea un documento PDF a DTO JSON unificado.
    
    ⚠️ FASE 2.3: Regex + tablas DIAN.
    
    Args:
        file_bytes: Contenido del archivo PDF en bytes
        filename: Nombre del archivo (opcional)
        
    Returns:
        Dict con estructura DTO JSON unificado
        
    Raises:
        ValueError: Si el PDF no es válido o no se puede parsear
    """
    # Extraer texto del PDF
    try:
        pdf_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise ValueError(f"Error al extraer texto del PDF: {str(e)}")
    
    if not pdf_text:
        raise ValueError("No se pudo extraer texto del PDF")
    
    # Detectar tipo de documento (Invoice o CreditNote) por heurísticas
    is_credit_note = _is_credit_note(pdf_text)
    document_type = "creditnote.ubl21" if is_credit_note else "invoice.ubl21"
    
    # Extraer datos usando regex (patrones DIAN)
    numero = _extract_numero(pdf_text)
    cufe = _extract_cufe(pdf_text)
    fecha_emision = _extract_fecha_emision(pdf_text)
    
    # Emisor
    emisor_nit = _extract_emisor_nit(pdf_text)
    emisor_razon_social = _extract_emisor_razon_social(pdf_text)
    
    # Receptor
    receptor_nit = _extract_receptor_nit(pdf_text)
    receptor_razon_social = _extract_receptor_razon_social(pdf_text)
    
    # Totales
    totales = _extract_totales(pdf_text)
    
    # Referencia (solo para CreditNote)
    referencia = None
    motivo = ""
    if is_credit_note:
        referencia = _extract_referencia(pdf_text)
        motivo = _extract_motivo(pdf_text)
    
    # Construir DTO (FASE 3: incluir type base para compatibilidad)
    # Extraer tipo base del document_type (ej: "invoice.ubl21" -> "invoice")
    type_base = document_type.split('.')[0] if '.' in document_type else document_type
    
    # Normalizar valores para campos planos
    nit_emisor_normalized = normalize_nit(emisor_nit) or ""
    total_normalized = normalize_numeric_to_decimal_string(totales.get("total", "0.00"))
    referencia_factura = referencia.get("numero", "") if referencia else ""
    
    dto = {
        "document_type": document_type,
        "type": type_base,  # Tipo base para router de validaciones
        # ⚠️ FASE 1: Campos planos requeridos para acceso directo
        "numero": numero or "",
        "referencia_factura": referencia_factura,  # Campo plano para Notas de Crédito
        "fecha_emision": fecha_emision or "",
        "total": total_normalized,  # Campo plano para acceso directo
        "nit_emisor": nit_emisor_normalized,  # Campo plano para acceso directo
        # Estructura anidada (compatibilidad con DTO estándar)
        "identificadores": {
            "cufe": cufe or "",
            "numero": numero or "",
        },
        "emisor": {
            "nit": nit_emisor_normalized,
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
            "total": total_normalized,
        },
    }
    
    if referencia:
        dto["referencia"] = referencia
    
    if motivo:
        dto["motivo"] = motivo
    
    return dto


def _is_credit_note(text: str) -> bool:
    """
    Detecta si el PDF es una Nota Crédito.
    
    ⚠️ FASE 1: Patrones mejorados para detección robusta de Notas de Crédito.
    """
    patterns = [
        r'nota\s*cr[ée]dito',
        r'credit\s*note',
        r'nc\s*\d+',
        r'nota\s*de\s*cr[ée]dito',
        r'documento\s*equivalente\s*a\s*nota\s*cr[ée]dito',
        r'tipo\s*de\s*documento.*?nota\s*cr[ée]dito',
    ]
    text_lower = text.lower()
    return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in patterns)


def _extract_numero(text: str) -> Optional[str]:
    """
    Extrae número de factura/nota crédito.
    
    ⚠️ FASE 1: Patrones mejorados para Notas de Crédito.
    Busca patrones como (NC|NOTA CR[ÉE]DITO)\\s*[-:]?\\s*([A-Z0-9]+)
    """
    patterns = [
        # Patrones específicos para Nota de Crédito
        r'(?:nota\s*cr[ée]dito|nc)\s*(?:n[úu]m[ée]ro|no\.?|#)?\s*[-:]?\s*([A-Z0-9\-]+)',
        r'(?:nota\s*cr[ée]dito|nc)\s*[-:]?\s*([A-Z0-9\-]+)',
        # Patrones genéricos
        r'factura\s*(?:n[úu]m[ée]ro|no\.?|#)\s*:?\s*([A-Z0-9\-]+)',
        r'numero\s*(?:de\s*(?:factura|documento))?\s*:?\s*([A-Z0-9\-]+)',
        r'no\.?\s*:?\s*([A-Z0-9\-]+)',
        r'documento\s*(?:n[úu]m[ée]ro|no\.?|#)\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            numero = sanitize_text(match.group(1))
            if numero:  # Validar que no esté vacío
                return numero
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
    """
    Extrae fecha de emisión.
    
    ⚠️ FASE 1: Soporta múltiples formatos de fecha (YYYY-MM-DD, DD/MM/YYYY).
    """
    patterns = [
        # Patrones específicos con etiqueta
        r'fecha\s*(?:de\s*)?emisi[óo]n\s*:?\s*(\d{4}[-/]\d{2}[-/]\d{2})',
        r'fecha\s*(?:de\s*)?emisi[óo]n\s*:?\s*(\d{2}[-/]\d{2}[-/]\d{4})',
        # Patrones genéricos (YYYY-MM-DD o YYYY/MM/DD)
        r'(\d{4}[-/]\d{2}[-/]\d{2})',
        # Patrones DD/MM/YYYY o DD-MM-YYYY
        r'(\d{2}[-/]\d{2}[-/]\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fecha_raw = match.group(1)
            # Normalizar separadores
            fecha = fecha_raw.replace('/', '-')
            
            # Si es formato DD-MM-YYYY, convertir a YYYY-MM-DD
            if re.match(r'\d{2}-\d{2}-\d{4}', fecha):
                parts = fecha.split('-')
                fecha = f"{parts[2]}-{parts[1]}-{parts[0]}"
            
            return f"{fecha}T00:00:00-05:00"
    return None


def _extract_emisor_nit(text: str) -> Optional[str]:
    """
    Extrae NIT del emisor.
    
    ⚠️ FASE 1: Patrones mejorados para extraer NIT (patrón estándar de NIT).
    """
    patterns = [
        # Patrones específicos con etiqueta
        r'nit\s*(?:emisor|proveedor|vendedor)?\s*:?\s*([0-9\-\.]+)',
        r'emisor.*?nit\s*:?\s*([0-9\-\.]+)',
        r'proveedor.*?nit\s*:?\s*([0-9\-\.]+)',
        # Patrones genéricos
        r'nit\s*:?\s*([0-9\-\.]+)',
        # Patrón con formato NIT: 123456789-0
        r'nit[:\s]+([0-9]+(?:[-\.][0-9]+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nit = match.group(1).strip()
            if nit:  # Validar que no esté vacío
                return nit
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
    """
    Extrae totales monetarios.
    
    ⚠️ FASE 1: Mejoras para manejar puntos/comas de miles/decimales.
    Busca el monto total considerando puntos/comas de miles/decimales.
    """
    patterns = {
        "subtotal": [
            r'subtotal\s*:?\s*\$?\s*([0-9,\.]+)',
            r'sub\s*total\s*:?\s*\$?\s*([0-9,\.]+)',
            r'subtotal\s*(?:sin\s*impuestos)?\s*:?\s*\$?\s*([0-9,\.]+)',
        ],
        "impuestos": [
            r'impuestos?\s*:?\s*\$?\s*([0-9,\.]+)',
            r'iva\s*:?\s*\$?\s*([0-9,\.]+)',
            r'impuesto\s*(?:al\s*valor\s*agregado|iva)\s*:?\s*\$?\s*([0-9,\.]+)',
        ],
        "total": [
            r'total\s*(?:a\s*pagar|general)?\s*:?\s*\$?\s*([0-9,\.]+)',
            r'valor\s*total\s*:?\s*\$?\s*([0-9,\.]+)',
            r'total\s*:?\s*\$?\s*([0-9,\.]+)',
            # Patrón para formato colombiano: 1.234.567,89
            r'total\s*:?\s*\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',
        ],
    }
    
    totales = {"moneda": "COP", "subtotal": "0.00", "impuestos": "0.00", "total": "0.00"}
    
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_raw = match.group(1)
                # Normalizar: remover puntos de miles, convertir coma decimal a punto
                # Formato colombiano: 1.234.567,89 -> 1234567.89
                if ',' in value_raw and '.' in value_raw:
                    # Tiene ambos: asumir que . es miles y , es decimal
                    value = value_raw.replace('.', '').replace(',', '.')
                elif ',' in value_raw:
                    # Solo coma: puede ser decimal o miles
                    # Si hay más de una coma, es miles; si hay una, es decimal
                    if value_raw.count(',') > 1:
                        value = value_raw.replace(',', '')
                    else:
                        value = value_raw.replace(',', '.')
                else:
                    # Solo puntos: remover todos (asumir miles)
                    value = value_raw.replace('.', '')
                
                totales[key] = value
                break
    
    return totales


def _extract_referencia(text: str) -> Optional[Dict[str, str]]:
    """
    Extrae referencia a factura (para Notas Crédito).
    
    ⚠️ FASE 1: Patrones mejorados para extraer referencia_factura.
    Busca patrones como (Factura|Ref|Afecta)\\s*[-:]?\\s*([A-Z0-9]+)
    """
    patterns = [
        # Patrones específicos para referencia de factura
        r'factura\s*(?:referenciada|afectada|relacionada|original)\s*:?\s*([A-Z0-9\-]+)',
        r'referencia\s*(?:a\s*)?(?:factura|documento)?\s*:?\s*([A-Z0-9\-]+)',
        r'afecta\s*(?:a\s*)?(?:factura|documento)?\s*:?\s*([A-Z0-9\-]+)',
        r'factura\s*:?\s*([A-Z0-9\-]+)',
        r'ref\.?\s*:?\s*([A-Z0-9\-]+)',
        # Patrones genéricos
        r'documento\s*(?:referenciado|afectado)\s*:?\s*([A-Z0-9\-]+)',
        r'relacionado\s*con\s*(?:factura|documento)\s*:?\s*([A-Z0-9\-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            numero_ref = sanitize_text(match.group(1))
            if numero_ref:  # Validar que no esté vacío
                return {
                    "numero": numero_ref,
                    "tipo": "invoice",
                }
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
