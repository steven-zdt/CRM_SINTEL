"""
Parser Excel específico para Facturas (v2.40).

⚠️ PRINCIPIOS:
- Parser exclusivo para el módulo de facturas
- Lógica separada del parser genérico de Excel
- Retorna DTO específico para facturas/notas crédito
"""
from typing import Dict, Any, Optional
from apps.services.document_parser.normalizers import (
    normalize_excel_to_dataframe, sanitize_text, normalize_nit, 
    normalize_currency, normalize_numeric_to_decimal_string
)


def parse_factura_excel_to_dto(
    file_bytes: bytes,
    filename: Optional[str] = None,
    kind_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parsea un Excel de factura/nota crédito para Facturas.
    
    ⚠️ v2.40: Parser específico para el módulo de facturas.
    
    Args:
        file_bytes: Contenido del archivo Excel en bytes
        filename: Nombre del archivo (opcional)
        kind_hint: Tipo sugerido (opcional, se ignora para facturas)
        
    Returns:
        Dict con estructura DTO JSON unificado para facturas/notas crédito
        
    Raises:
        ValueError: Si el Excel no es válido o no se puede parsear
        ImportError: Si pandas no está instalado
    """
    # Convertir a DataFrame
    try:
        df = normalize_excel_to_dataframe(file_bytes)
    except Exception as e:
        raise ValueError(f"Error al leer Excel: {str(e)}")
    
    if df is None:
        raise ImportError("pandas no está instalado. Instala con: pip install pandas openpyxl")
    
    if df.empty:
        raise ValueError("El archivo Excel está vacío")
    
    # Detectar tipo de documento (Invoice o CreditNote) por heurísticas
    is_credit_note = _is_credit_note(df)
    document_type = "creditnote.ubl21" if is_credit_note else "invoice.ubl21"
    
    # Extraer datos del DataFrame (buscar columnas comunes)
    numero = _extract_from_dataframe(df, ["numero", "numero_factura", "factura", "id", "documento"])
    cufe = _extract_from_dataframe(df, ["cufe", "uuid", "codigo"])
    fecha_emision = _extract_from_dataframe(df, ["fecha", "fecha_emision", "fecha_emision", "date"])
    
    # Emisor
    emisor_nit = _extract_from_dataframe(df, ["emisor_nit", "nit_emisor", "proveedor_nit", "nit"])
    emisor_razon_social = _extract_from_dataframe(df, ["emisor_razon_social", "razon_social_emisor", "proveedor", "emisor"])
    
    # Receptor
    receptor_nit = _extract_from_dataframe(df, ["receptor_nit", "nit_receptor", "cliente_nit"])
    receptor_razon_social = _extract_from_dataframe(df, ["receptor_razon_social", "razon_social_receptor", "cliente", "receptor"])
    
    # Totales
    subtotal = _extract_from_dataframe(df, ["subtotal", "sub_total", "base"])
    impuestos = _extract_from_dataframe(df, ["impuestos", "iva", "tax"])
    total = _extract_from_dataframe(df, ["total", "valor_total", "amount"])
    moneda = _extract_from_dataframe(df, ["moneda", "currency", "currency_id"]) or "COP"
    
    # Referencia (solo para CreditNote)
    referencia = None
    motivo = ""
    if is_credit_note:
        ref_numero = _extract_from_dataframe(df, ["referencia", "factura_referencia", "ref_factura"])
        if ref_numero:
            referencia = {
                "numero": sanitize_text(str(ref_numero)),
                "tipo": "invoice",
            }
        motivo = _extract_from_dataframe(df, ["motivo", "razon", "descripcion"]) or ""
    
    # Construir DTO (FASE 3: incluir type base para compatibilidad)
    # Extraer tipo base del document_type
    type_base = document_type.split('.')[0] if '.' in document_type else document_type
    
    dto = {
        "document_type": document_type,
        "type": type_base,  # Tipo base para router de validaciones
        "numero": sanitize_text(str(numero)) if numero else "",
        "identificadores": {
            "cufe": sanitize_text(str(cufe)) if cufe else "",
            "numero": sanitize_text(str(numero)) if numero else "",
        },
        "fecha_emision": _normalize_fecha(str(fecha_emision)) if fecha_emision else "",
        "emisor": {
            "nit": normalize_nit(str(emisor_nit)) if emisor_nit else "",
            "razon_social": sanitize_text(str(emisor_razon_social)) if emisor_razon_social else "",
        },
        "receptor": {
            "nit": normalize_nit(str(receptor_nit)) if receptor_nit else "",
            "razon_social": sanitize_text(str(receptor_razon_social)) if receptor_razon_social else "",
        },
        "totales": {
            "moneda": normalize_currency(str(moneda)),
            "subtotal": normalize_numeric_to_decimal_string(subtotal) if subtotal else "0.00",
            "impuestos": normalize_numeric_to_decimal_string(impuestos) if impuestos else "0.00",
            "total": normalize_numeric_to_decimal_string(total) if total else "0.00",
        },
    }
    
    if referencia:
        dto["referencia"] = referencia
    
    if motivo:
        dto["motivo"] = sanitize_text(str(motivo))
    
    return dto


def _is_credit_note(df) -> bool:
    """Detecta si el Excel es una Nota Crédito."""
    # Buscar en nombres de columnas o primera fila
    columns_str = ' '.join(df.columns.astype(str).str.lower())
    first_row_str = ' '.join(df.iloc[0].astype(str).str.lower()) if not df.empty else ""
    
    patterns = ['nota credito', 'credit note', 'nc']
    text = f"{columns_str} {first_row_str}"
    
    return any(pattern in text for pattern in patterns)


def _extract_from_dataframe(df, possible_columns: list) -> Optional[Any]:
    """Extrae valor del DataFrame buscando en columnas posibles."""
    for col in possible_columns:
        if col in df.columns:
            # Tomar primer valor no nulo
            value = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if value is not None:
                return value
    return None


def _normalize_fecha(fecha_str: str) -> str:
    """Normaliza fecha a formato ISO 8601."""
    # Intentar parsear diferentes formatos
    import re
    from datetime import datetime
    
    patterns = [
        r'(\d{4})[-/](\d{2})[-/](\d{2})',
        r'(\d{2})[-/](\d{2})[-/](\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, fecha_str)
        if match:
            try:
                if len(match.group(1)) == 4:  # YYYY-MM-DD
                    year, month, day = match.groups()
                else:  # DD-MM-YYYY
                    day, month, year = match.groups()
                return f"{year}-{month}-{day}T00:00:00-05:00"
            except:
                pass
    
    return fecha_str
