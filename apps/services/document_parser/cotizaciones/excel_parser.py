"""
Parser Excel específico para Cotizaciones - Catálogos de Productos (v2.40).

WARNING: PRINCIPIOS:
- Parser exclusivo para el módulo de cotizaciones
- Lógica separada del parser genérico de Excel
- Usa SemanticMapper para mapeo inteligente de columnas
- Retorna DTO específico para catálogos de productos
"""
from typing import Any

# WARNING: v2.40: Usar normalizers específicos de cotizaciones (que reutilizan los genéricos)
from apps.services.document_parser.cotizaciones.normalizers import (
    SemanticMapper,
    normalize_excel_to_dataframe,
)


def parse_catalogo_to_dto(
    file_bytes: bytes,
    filename: str | None = None,
    kind_hint: str | None = None
) -> dict[str, Any]:
    """
    Parsea un Excel de catálogo de productos para Cotizaciones.
    
    WARNING: v2.40: Parser específico para el módulo de cotizaciones.
    Convierte cada fila del Excel en un DTO de producto usando mapeo semántico.
    
    Args:
        file_bytes: Contenido del archivo Excel en bytes
        filename: Nombre del archivo (opcional)
        kind_hint: Tipo sugerido (opcional, se ignora ya que es específico de cotizaciones)
        
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
            ],
            "mapping_metadata": {
                "column_mapping": {...},
                "confidence_scores": {...},
                "average_confidence": float
            }
        }
        
    Raises:
        ValueError: Si el Excel no es válido o no se pueden extraer productos
        ImportError: Si pandas no está instalado
    """
    # Convertir a DataFrame
    try:
        df = normalize_excel_to_dataframe(file_bytes)
    except Exception as e:
        error_msg = str(e)
        raise ValueError(f"Error al leer Excel: {error_msg}")
    
    if df is None:
        raise ImportError("pandas no está instalado. Instala con: pip install pandas openpyxl")
    
    if df.empty:
        raise ValueError("El archivo Excel está vacío")
    
    # Validar que el DataFrame tenga al menos una columna
    if len(df.columns) == 0:
        raise ValueError("El archivo Excel no tiene columnas válidas")
    
    items = []
    
    # WARNING: v2.40: Usar SemanticMapper para mapeo inteligente de columnas
    try:
        mapper = SemanticMapper(threshold=0.6)
        
        # Obtener nombres de columnas
        column_names = list(df.columns)
        
        if not column_names:
            raise ValueError("El archivo Excel no tiene columnas con nombres válidos")
        
        # Mapear columnas a campos del modelo usando SemanticMapper
        column_mapping, confidence_scores = mapper.map_columns(column_names)
    except Exception as e:
        raise ValueError(f"Error al mapear columnas del Excel: {str(e)}")
    
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
