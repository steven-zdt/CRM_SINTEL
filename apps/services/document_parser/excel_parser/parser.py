"""
Parser para documentos Excel (XLS, XLSX) (FASE 2.3).

WARNING: PRINCIPIOS:
- Convierte Excel a DataFrame normalizado
- DataFrame → DTO JSON unificado
- Retorna DTO según apps/services/document_parser/dto.py
- Mapeo semántico inteligente de columnas (v2.40)
"""
from typing import Any

from apps.services.document_parser.normalizers import (
    SemanticMapper,
    normalize_currency,
    normalize_excel_to_dataframe,
    normalize_nit,
    normalize_numeric_to_decimal_string,
    sanitize_text,
)


def parse_to_dto(file_bytes: bytes, filename: str | None = None, kind_hint: str | None = None) -> dict[str, Any]:
    """
    Parsea un documento Excel a DTO JSON unificado.
    
    WARNING: FASE 2.3: DataFrame → DTO.
    WARNING: v2.40: Soporta catálogos de productos cuando kind_hint="inventario"
    
    Args:
        file_bytes: Contenido del archivo Excel en bytes
        filename: Nombre del archivo (opcional)
        kind_hint: Tipo sugerido (opcional, ej: "inventario" para catálogos)
        
    Returns:
        Dict con estructura DTO JSON unificado o array de productos si es catálogo
        
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
    
    # WARNING: v2.40: Detectar si es catálogo de productos (inventario)
    if kind_hint and kind_hint.lower() in ("inventario", "catalogo", "productos"):
        return _parse_catalog_to_dto(df, filename)
    
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


def _extract_from_dataframe(df, possible_columns: list) -> Any | None:
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


def _parse_catalog_to_dto(df, filename: str | None = None) -> dict[str, Any]:
    """
    Parsea un Excel de catálogo de productos a array de DTOs.
    
    WARNING: v2.40: Convierte cada fila del Excel en un DTO de producto.
    
    Args:
        df: DataFrame normalizado del Excel
        filename: Nombre del archivo (opcional)
        
    Returns:
        Dict con estructura:
        {
            "document_type": "inventario.catalogo",
            "type": "inventario",
            "items": [
                {
                    "codigo": str,
                    "nombre": str,
                    "marca": str (opcional),
                    "referencia": str (opcional),
                    "unidad": str (default: "UND"),
                    "precio_venta": str (decimal),
                    "descripcion": str (opcional)
                },
                ...
            ]
        }
        
    Raises:
        ValueError: Si el DataFrame está vacío o no se pueden extraer productos
    """
    
    # Validar que el DataFrame no esté vacío
    if df is None or df.empty:
        raise ValueError("El DataFrame está vacío o es None")
    
    items = []
    
    # WARNING: v2.40: Usar SemanticMapper para mapeo inteligente de columnas
    mapper = SemanticMapper(threshold=0.6)
    
    # Obtener nombres de columnas originales (antes de normalización)
    # Las columnas del DataFrame ya están normalizadas, pero necesitamos los originales
    # para el mapeo semántico. Usaremos las columnas normalizadas como base.
    column_names = list(df.columns)
    
    # Mapear columnas a campos del modelo usando SemanticMapper
    column_mapping, confidence_scores = mapper.map_columns(column_names)
    
    # Invertir el mapping para facilitar búsqueda: {columna_normalizada: campo_modelo}
    reverse_mapping = {col: field for field, col in column_mapping.items()}
    
    # Función helper para extraer valor de una fila usando el mapeo semántico
    def extract_value(row_dict, field_name: str):
        """
        Extrae valor de una fila usando el mapeo semántico.
        
        Args:
            row_dict: Dict con valores de la fila (claves normalizadas)
            field_name: Nombre del campo del modelo (ej: 'codigo', 'precio_venta')
            
        Returns:
            Valor extraído o None
        """
        # Buscar en el mapeo directo
        if field_name in column_mapping:
            mapped_column = column_mapping[field_name]
            # Normalizar el nombre de la columna mapeada
            normalized_mapped = mapper._normalize_column_name(mapped_column)
            
            # Buscar en las claves del row_dict
            for col_key in row_dict.keys():
                col_key_normalized = mapper._normalize_column_name(str(col_key))
                if col_key_normalized == normalized_mapped:
                    value = row_dict[col_key]
                    if value is not None and str(value).strip() and str(value).lower() != 'nan':
                        return str(value).strip()
        
        # Si no hay mapeo directo, buscar por similitud en todas las columnas
        # (fallback para casos donde el mapeo no fue perfecto)
        for col_key in row_dict.keys():
            col_key_normalized = mapper._normalize_column_name(str(col_key))
            matched_field, score = mapper._find_best_match(col_key, mapper.FIELD_SYNONYMS.get(field_name, []))
            if matched_field and score >= mapper.threshold:
                value = row_dict[col_key]
                if value is not None and str(value).strip() and str(value).lower() != 'nan':
                    return str(value).strip()
        
        return None
    
    # Procesar cada fila del DataFrame
    try:
        for idx, row in df.iterrows():
            # Convertir row (Series) a dict para facilitar acceso
            row_dict = row.to_dict()
            
            # Extraer campos usando el mapeo semántico
            codigo = extract_value(row_dict, 'codigo')
            nombre = extract_value(row_dict, 'nombre')
            
            # Si no hay código o nombre, saltar esta fila
            if not codigo and not nombre:
                continue
            
            # Si no hay código, usar el índice como código temporal
            if not codigo:
                codigo = f"TEMP-{idx+1}"
            
            # Si no hay nombre, usar código como nombre
            if not nombre:
                nombre = codigo
            
            # Construir DTO del producto
            producto_dto = {
                "codigo": codigo,
                "nombre": nombre,
            }
            
            # Campos opcionales usando el mapeo semántico
            marca = extract_value(row_dict, 'marca')
            if marca:
                producto_dto["marca"] = marca
            
            referencia = extract_value(row_dict, 'referencia')
            if referencia:
                producto_dto["referencia"] = referencia
            
            unidad = extract_value(row_dict, 'unidad')
            producto_dto["unidad"] = unidad if unidad else "UND"
            
            precio_venta = extract_value(row_dict, 'precio_venta')
            if precio_venta:
                # Normalizar precio (remover símbolos de moneda, espacios, etc.)
                precio_clean = str(precio_venta).replace('$', '').replace(',', '').replace(' ', '').strip()
                try:
                    float(precio_clean)  # Validar que sea numérico
                    producto_dto["precio_venta"] = precio_clean
                except (ValueError, TypeError):
                    producto_dto["precio_venta"] = "0.00"
            else:
                producto_dto["precio_venta"] = "0.00"
            
            descripcion = extract_value(row_dict, 'descripcion')
            if descripcion:
                producto_dto["descripcion"] = descripcion
            
            items.append(producto_dto)
    except Exception as e:
        # Si hay un error procesando las filas, lanzar ValueError
        raise ValueError(f"Error al procesar filas del Excel: {str(e)}")
    
    # Validar que se hayan extraído al menos algunos items
    if not items:
        raise ValueError("No se pudieron extraer productos del Excel. Verifique que el archivo tenga columnas válidas (código, nombre, etc.)")
    
    # Calcular confidence_score promedio del mapeo
    avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.0
    
    # Retornar estructura con items y metadatos de mapeo
    return {
        "document_type": "inventario.catalogo",
        "type": "inventario",
        "items": items,
        "mapping_metadata": {
            "column_mapping": column_mapping,
            "confidence_scores": confidence_scores,
            "average_confidence": round(avg_confidence, 2)
        }
    }
