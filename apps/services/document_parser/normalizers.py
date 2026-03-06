"""
Normalizador de contenido de documentos (FASE 2.2).

⚠️ PRINCIPIOS:
- Convertir a UTF-8
- Limpiar acentos y caracteres ilegales
- Normalizar whitespace
- Sanitizar texto
- Convertir valores numéricos a decimal-string
- Extraer texto desde PDF (pdfminer)
- Pasar XLS/CSV a DataFrame normalizado
- Normalizar TXT
- Mapeo semántico inteligente de columnas (v2.40)
"""
import re
import unicodedata
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from difflib import SequenceMatcher

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from pdfminer.high_level import extract_text as pdf_extract_text
    from pdfminer.layout import LAParams
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False


def normalize_encoding(content: bytes, encoding: Optional[str] = None) -> bytes:
    """
    Normaliza la codificación del contenido a UTF-8.
    
    Args:
        content: Contenido original en bytes
        encoding: Codificación esperada (opcional, se detecta automáticamente si no se proporciona)
        
    Returns:
        bytes: Contenido en UTF-8
    """
    if encoding:
        try:
            return content.decode(encoding).encode('utf-8')
        except (UnicodeDecodeError, LookupError):
            pass
    
    # Detectar codificación automáticamente (si chardet está disponible)
    if HAS_CHARDET:
        try:
            detected = chardet.detect(content)
            if detected and detected.get('encoding'):
                try:
                    return content.decode(detected['encoding']).encode('utf-8')
                except (UnicodeDecodeError, LookupError):
                    pass
        except Exception:
            pass
    
    # Fallback: UTF-8 con manejo de errores
    try:
        return content.decode('utf-8', errors='replace').encode('utf-8')
    except Exception:
        # Último recurso: latin-1 (siempre funciona)
        return content.decode('latin-1', errors='replace').encode('utf-8')


def remove_binary_embeds(content: bytes) -> bytes:
    """
    Elimina binarios incrustados del contenido.
    
    Args:
        content: Contenido original en bytes
        
    Returns:
        bytes: Contenido sin binarios incrustados
    """
    # Para XML: eliminar CDATA con binarios (imágenes, etc.)
    # Para PDF/XLS: esto se maneja en los parsers específicos
    # Por ahora, retornamos el contenido sin cambios
    # (los parsers específicos manejarán la limpieza)
    return content


def sanitize_text(text: str) -> str:
    """
    Sanea un campo de texto: elimina caracteres ilegales, normaliza espacios, trimming.
    
    Args:
        text: Texto a sanear
        
    Returns:
        str: Texto saneado
    """
    if not text:
        return ""
    
    # Normalizar espacios en blanco
    text = re.sub(r'\s+', ' ', text)
    
    # Eliminar caracteres de control (excepto \n, \r, \t)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Trimming
    text = text.strip()
    
    return text


def normalize_nit(nit: Optional[str]) -> Optional[str]:
    """
    Normaliza un NIT: elimina guiones, espacios, puntos.
    
    Args:
        nit: NIT a normalizar
        
    Returns:
        str: NIT normalizado o None si está vacío
    """
    if not nit:
        return None
    
    # Eliminar caracteres no alfanuméricos
    nit = re.sub(r'[^0-9A-Za-z]', '', nit)
    
    if not nit:
        return None
    
    return nit.upper()


def normalize_currency(moneda: Optional[str]) -> str:
    """
    Normaliza código de moneda a formato estándar.
    
    Args:
        moneda: Código de moneda (ej: "COP", "USD", "cop", "usd")
        
    Returns:
        str: Código de moneda normalizado (default: "COP")
    """
    if not moneda:
        return "COP"
    
    moneda = moneda.strip().upper()
    
    # Códigos válidos ISO 4217
    valid_codes = {"COP", "USD", "EUR", "GBP", "MXN", "BRL", "ARS", "CLP", "PEN"}
    
    if moneda in valid_codes:
        return moneda
    
    # Mapeo de códigos comunes
    mapping = {
        "PESO": "COP",
        "PESOS": "COP",
        "COLOMBIANO": "COP",
    }
    
    return mapping.get(moneda, "COP")


def normalize_whitespace(text: str) -> str:
    """
    Normaliza whitespace: múltiples espacios a uno, trimming.
    
    ⚠️ FASE 2.2: Normalización de whitespace.
    
    Args:
        text: Texto a normalizar
        
    Returns:
        str: Texto con whitespace normalizado
    """
    if not text:
        return ""
    
    # Reemplazar múltiples espacios/tabs/newlines por un solo espacio
    text = re.sub(r'\s+', ' ', text)
    
    # Trimming
    text = text.strip()
    
    return text


def clean_accents(text: str) -> str:
    """
    Limpia acentos y caracteres ilegales.
    
    ⚠️ FASE 2.2: Limpieza de acentos y caracteres especiales.
    
    Args:
        text: Texto a limpiar
        
    Returns:
        str: Texto sin acentos (normalizado a ASCII)
    """
    if not text:
        return ""
    
    # Normalizar a NFD (descomponer acentos)
    text = unicodedata.normalize('NFD', text)
    
    # Eliminar marcas diacríticas (acentos)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    return text


def normalize_numeric_to_decimal_string(value: Any) -> str:
    """
    Convierte valores numéricos a decimal-string.
    
    ⚠️ FASE 2.2: Conversión de valores numéricos.
    
    Args:
        value: Valor numérico (int, float, Decimal, str)
        
    Returns:
        str: Valor como string decimal (ej: "100000.00")
    """
    if value is None:
        return "0.00"
    
    try:
        if isinstance(value, str):
            # Limpiar separadores de miles
            value = value.replace(',', '').replace('.', '')
            decimal = Decimal(value) / Decimal('100') if '.' not in value else Decimal(value)
        else:
            decimal = Decimal(str(value))
        
        # Formatear a 2 decimales
        return f"{decimal:.2f}"
    except (ValueError, TypeError, Exception):
        return "0.00"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extrae texto desde PDF usando pdfminer.
    
    ⚠️ FASE 2.2: Extracción de texto desde PDF.
    
    Args:
        pdf_bytes: Contenido del PDF en bytes
        
    Returns:
        str: Texto extraído del PDF (normalizado UTF-8)
    """
    if not HAS_PDFMINER:
        raise ImportError("pdfminer no está instalado. Instala con: pip install pdfminer.six")
    
    try:
        from io import BytesIO
        
        # Extraer texto con layout parameters
        laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
        )
        
        text = pdf_extract_text(BytesIO(pdf_bytes), laparams=laparams)
        
        # Normalizar a UTF-8
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Normalizar whitespace
        text = normalize_whitespace(text)
        
        return text
    except Exception as e:
        raise ValueError(f"Error al extraer texto del PDF: {str(e)}")


def normalize_excel_to_dataframe(excel_bytes: bytes, sheet_name: Optional[str] = None) -> Optional[Any]:
    """
    Pasa XLS/XLSX a DataFrame normalizado.
    
    ⚠️ FASE 2.2: Conversión de Excel a DataFrame.
    
    Args:
        excel_bytes: Contenido del archivo Excel en bytes
        sheet_name: Nombre de la hoja a leer (opcional, lee la primera si no se especifica)
        
    Returns:
        pandas.DataFrame o None si pandas no está disponible
    """
    if not HAS_PANDAS:
        return None
    
    try:
        from io import BytesIO
        
        # Leer Excel
        df = pd.read_excel(BytesIO(excel_bytes), sheet_name=sheet_name, engine='openpyxl')
        
        # Normalizar: eliminar filas/columnas completamente vacías
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Normalizar nombres de columnas (trim, lowercase, reemplazar espacios)
        df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
        
        return df
    except Exception as e:
        raise ValueError(f"Error al leer Excel: {str(e)}")


def normalize_csv_to_dataframe(csv_bytes: bytes, delimiter: Optional[str] = None) -> Optional[Any]:
    """
    Pasa CSV a DataFrame normalizado.
    
    ⚠️ FASE 2.2: Conversión de CSV a DataFrame.
    
    Args:
        csv_bytes: Contenido del archivo CSV en bytes
        delimiter: Delimitador (opcional, se detecta automáticamente)
        
    Returns:
        pandas.DataFrame o None si pandas no está disponible
    """
    if not HAS_PANDAS:
        return None
    
    try:
        from io import BytesIO
        
        # Normalizar encoding primero
        normalized = normalize_encoding(csv_bytes)
        csv_text = normalized.decode('utf-8', errors='replace')
        
        # Detectar delimitador si no se proporciona
        if not delimiter:
            # Probar delimitadores comunes
            for delim in [',', ';', '\t', '|']:
                if delim in csv_text[:200]:  # Revisar primeras líneas
                    delimiter = delim
                    break
            if not delimiter:
                delimiter = ','  # Default
        
        # Leer CSV
        df = pd.read_csv(BytesIO(normalized), delimiter=delimiter, encoding='utf-8')
        
        # Normalizar: eliminar filas/columnas completamente vacías
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Normalizar nombres de columnas
        df.columns = [str(col).strip().lower().replace(' ', '_') for col in df.columns]
        
        return df
    except Exception as e:
        raise ValueError(f"Error al leer CSV: {str(e)}")


def normalize_txt(text: str) -> str:
    """
    Normaliza texto plano (TXT).
    
    ⚠️ FASE 2.2: Normalización de texto plano.
    
    Args:
        text: Texto a normalizar
        
    Returns:
        str: Texto normalizado (UTF-8, whitespace normalizado, sanitizado)
    """
    if not text:
        return ""
    
    # Normalizar encoding (si viene como bytes, convertir a str primero)
    if isinstance(text, bytes):
        text = normalize_encoding(text).decode('utf-8', errors='replace')
    
    # Sanitizar texto
    text = sanitize_text(text)
    
    # Normalizar whitespace
    text = normalize_whitespace(text)
    
    return text


def normalize_xml(xml_bytes: bytes) -> bytes:
    """
    Normaliza contenido XML a UTF-8, elimina BOM, limpia firmas XAdES opcionales.
    
    ⚠️ REVERSIÓN: Normalización SIEMPRE aplicada a XML.
    
    Args:
        xml_bytes: Contenido XML en bytes
        
    Returns:
        bytes: XML normalizado a UTF-8
    """
    # 1. Eliminar BOM si existe
    if xml_bytes.startswith(b'\xef\xbb\xbf'):
        xml_bytes = xml_bytes[3:]
    elif xml_bytes.startswith(b'\xff\xfe') or xml_bytes.startswith(b'\xfe\xff'):
        # UTF-16 BOM - convertir a UTF-8
        try:
            encoding = 'utf-16-le' if xml_bytes.startswith(b'\xff\xfe') else 'utf-16-be'
            xml_bytes = xml_bytes[2:].decode(encoding, errors='replace').encode('utf-8')
        except Exception:
            pass
    
    # 2. Normalizar encoding a UTF-8
    normalized = normalize_encoding(xml_bytes)
    
    # 3. (Opcional) Limpiar firmas XAdES si entorpecen el parser
    # Por ahora, no las eliminamos automáticamente - el parser lxml las maneja bien
    # Si en el futuro se requiere, se puede agregar aquí
    
    return normalized


def normalize_content(
    content: bytes,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Normaliza contenido de documento de forma unificada y determinística.
    
    ⚠️ REVERSIÓN: Normalización SIEMPRE aplicada a TODOS los tipos (XML, CSV, XLS/XLSX, TXT, PDF).
    
    Esta función es el punto único de normalización antes del parsing.
    Todos los parsers deben consumir exclusivamente el valor 'normalized' devuelto.
    
    Args:
        content: Contenido del documento en bytes
        filename: Nombre del archivo (opcional, para detección de tipo)
        mime_type: MIME type del archivo (opcional, para detección de tipo)
        
    Returns:
        Dict con estructura:
        {
            "media_type": "xml|csv|excel|txt|pdf|unknown",
            "normalized": bytes|str|DataFrame (según tipo),
            "meta": {
                "encoding": "utf-8",
                "bom_stripped": bool,
                "newline": "LF"|"CRLF"|None,
                "decimal": ".",
                "detected_delimiter": ","|";"|"\\t"|None,
                "cleanups": [str, ...]
            }
        }
        
    Raises:
        ValueError: Si el tipo no se reconoce o el contenido es insalvable
    """
    from apps.services.document_parser.detector import detect_document_type
    
    # Detectar tipo de documento
    detection_result = detect_document_type(content, filename, mime_type)
    media_type = detection_result.get("media_type")
    confidence = detection_result.get("confidence", 0.0)
    
    # Normalizar tipos de Excel: xls/xlsx → excel
    if media_type in ("xls", "xlsx"):
        media_type = "excel"
    
    meta = {
        "encoding": "utf-8",
        "bom_stripped": False,
        "newline": None,
        "decimal": ".",
        "detected_delimiter": None,
        "cleanups": [],
    }
    
    # Si no se detecta tipo, intentar inferir desde mime_type o filename
    if not media_type or confidence < 0.3:
        if mime_type:
            if 'xml' in mime_type.lower():
                media_type = "xml"
            elif 'csv' in mime_type.lower() or 'text/csv' in mime_type.lower():
                media_type = "csv"
            elif 'excel' in mime_type.lower() or 'spreadsheet' in mime_type.lower():
                media_type = "excel"
            elif 'pdf' in mime_type.lower():
                media_type = "pdf"
            elif 'text/plain' in mime_type.lower():
                media_type = "txt"
        
        if not media_type and filename:
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else None
            if ext in ('xml'):
                media_type = "xml"
            elif ext in ('csv'):
                media_type = "csv"
            elif ext in ('xls', 'xlsx'):
                media_type = "excel"
            elif ext in ('pdf'):
                media_type = "pdf"
            elif ext in ('txt', 'text'):
                media_type = "txt"
    
    # Si aún no se detecta, lanzar error
    if not media_type:
        raise ValueError("Tipo de documento no reconocido. Soporta: XML, CSV, XLS/XLSX, TXT, PDF")
    
    normalized = None
    cleanups = []
    
    # Normalizar según tipo
    if media_type == "xml":
        # Normalizar XML: UTF-8, eliminar BOM, limpiar si es necesario
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            meta["bom_stripped"] = True
            cleanups.append("bom_removed")
        
        normalized = normalize_xml(content)
        cleanups.append("encoding_normalized")
        
    elif media_type == "csv":
        # Normalizar CSV: UTF-8, detectar delimitador, normalizar encabezados
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            meta["bom_stripped"] = True
            cleanups.append("bom_removed")
        
        normalized_bytes = normalize_encoding(content)
        csv_text = normalized_bytes.decode('utf-8', errors='replace')
        
        # Detectar delimitador
        for delim in [',', ';', '\t', '|']:
            if delim in csv_text[:200]:
                meta["detected_delimiter"] = delim
                cleanups.append(f"delimiter_detected_{delim}")
                break
        
        # Normalizar newlines a LF
        if '\r\n' in csv_text:
            csv_text = csv_text.replace('\r\n', '\n')
            meta["newline"] = "CRLF->LF"
            cleanups.append("newline_normalized")
        elif '\r' in csv_text:
            csv_text = csv_text.replace('\r', '\n')
            meta["newline"] = "CR->LF"
            cleanups.append("newline_normalized")
        else:
            meta["newline"] = "LF"
        
        normalized = csv_text
        cleanups.append("encoding_normalized")
        
    elif media_type == "excel":
        # Normalizar Excel: leer con pandas, normalizar DataFrame
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            meta["bom_stripped"] = True
            cleanups.append("bom_removed")
        
        # Excel es binario, pero normalizamos encoding de metadatos si aplica
        normalized = content  # Mantener como bytes para pandas
        cleanups.append("excel_binary_preserved")
        
    elif media_type == "txt":
        # Normalizar TXT: UTF-8, LF, trimming, whitespace
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            meta["bom_stripped"] = True
            cleanups.append("bom_removed")
        
        normalized_bytes = normalize_encoding(content)
        txt_text = normalized_bytes.decode('utf-8', errors='replace')
        
        # Normalizar newlines
        if '\r\n' in txt_text:
            txt_text = txt_text.replace('\r\n', '\n')
            meta["newline"] = "CRLF->LF"
            cleanups.append("newline_normalized")
        elif '\r' in txt_text:
            txt_text = txt_text.replace('\r', '\n')
            meta["newline"] = "CR->LF"
            cleanups.append("newline_normalized")
        else:
            meta["newline"] = "LF"
        
        # Aplicar normalización de texto
        normalized = normalize_txt(txt_text)
        cleanups.append("encoding_normalized")
        cleanups.append("whitespace_normalized")
        
    elif media_type == "pdf":
        # Normalizar PDF: extraer texto si es posible, o mantener binario
        # Por ahora, mantenemos como bytes (el parser PDF manejará la extracción)
        normalized = content  # Mantener como bytes
        cleanups.append("pdf_binary_preserved")
        
    else:
        raise ValueError(f"Tipo de documento no soportado: {media_type}")
    
    meta["cleanups"] = cleanups
    
    return {
        "media_type": media_type,
        "normalized": normalized,
        "meta": meta,
    }


# ==============================================================================
# SEMANTIC MAPPER (v2.40) - Mapeo Inteligente de Columnas
# ==============================================================================

class SemanticMapper:
    """
    Mapeador semántico para columnas de archivos externos.
    
    ⚠️ v2.40: Realiza mapeo inteligente de columnas desconocidas a campos del modelo
    usando sinónimos y fuzzy matching.
    
    Uso:
        mapper = SemanticMapper()
        mapping, confidence = mapper.map_columns(['SKU', 'Ref. STS', 'Costo Base'])
        # mapping: {'codigo': 'SKU', 'referencia': 'Ref. STS', 'precio_venta': 'Costo Base'}
        # confidence: {'codigo': 0.95, 'referencia': 0.85, 'precio_venta': 0.90}
    """
    
    # Diccionario de sinónimos para cada campo del modelo Producto
    FIELD_SYNONYMS = {
        'codigo': [
            'codigo', 'sku', 'codigo_producto', 'id', 'item', 'articulo_id',
            'codigo_articulo', 'producto_id', 'numero_producto', 'ref_interna',
            'codigo_interno', 'codigo_barras', 'ean', 'upc'
        ],
        'nombre': [
            'nombre', 'descripcion', 'producto', 'item', 'articulo', 'nombre_producto',
            'descripcion_corta', 'titulo', 'denominacion', 'nombre_comercial',
            'producto_nombre', 'descripcion_producto'
        ],
        'marca': [
            'marca', 'brand', 'fabricante', 'manufacturer', 'proveedor_marca',
            'marca_producto', 'fabricante_producto', 'brand_name'
        ],
        'referencia': [
            'referencia', 'ref', 'modelo', 'part_number', 'part_number_producto',
            'ref_fabricante', 'referencia_fabricante', 'modelo_producto',
            'codigo_fabricante', 'ref_sts', 'ref_sts_producto'
        ],
        'unidad': [
            'unidad', 'um', 'unidad_medida', 'medida', 'unidad_medicion',
            'uom', 'unit_of_measure', 'unidad_base', 'medida_base'
        ],
        'precio_venta': [
            'precio', 'precio_venta', 'valor', 'costo', 'precio_unitario', 'precio_base',
            'costo_base', 'precio_lista', 'valor_unitario', 'precio_publico',
            'precio_catalogo', 'precio_estandar', 'costo_unitario', 'p_unitario',
            'precio_venta_unitario', 'valor_venta', 'precio_neto'
        ],
        'descripcion': [
            'descripcion', 'detalle', 'observaciones', 'notas', 'descripcion_detallada',
            'comentarios', 'descripcion_larga', 'detalle_producto', 'especificaciones'
        ]
    }
    
    # Tipos de datos esperados para cada campo (para deducción automática)
    FIELD_TYPES = {
        'codigo': str,
        'nombre': str,
        'marca': str,
        'referencia': str,
        'unidad': str,
        'precio_venta': (int, float, Decimal),
        'descripcion': str
    }
    
    def __init__(self, threshold: float = 0.6):
        """
        Inicializa el mapeador semántico.
        
        Args:
            threshold: Umbral mínimo de similitud para considerar un match (0.0-1.0)
        """
        self.threshold = threshold
    
    def _normalize_column_name(self, column: str) -> str:
        """
        Normaliza el nombre de una columna para comparación.
        
        Args:
            column: Nombre de columna original
            
        Returns:
            Nombre normalizado (lowercase, sin espacios, sin acentos)
        """
        # Convertir a lowercase
        normalized = column.lower().strip()
        
        # Remover caracteres especiales comunes
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Reemplazar espacios múltiples por uno solo
        normalized = re.sub(r'\s+', '_', normalized)
        
        # Remover acentos (simplificado)
        normalized = sanitize_text(normalized)
        
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula la similitud entre dos textos usando SequenceMatcher.
        
        Args:
            text1: Primer texto
            text2: Segundo texto
            
        Returns:
            Score de similitud (0.0-1.0)
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _find_best_match(self, column: str, synonyms: List[str]) -> Tuple[Optional[str], float]:
        """
        Encuentra el mejor match para una columna entre una lista de sinónimos.
        
        Args:
            column: Nombre de columna a mapear
            synonyms: Lista de sinónimos posibles
            
        Returns:
            Tupla (sinonimo_matched, confidence_score)
        """
        normalized_column = self._normalize_column_name(column)
        best_match = None
        best_score = 0.0
        
        for synonym in synonyms:
            normalized_synonym = self._normalize_column_name(synonym)
            
            # Coincidencia exacta
            if normalized_column == normalized_synonym:
                return synonym, 1.0
            
            # Coincidencia parcial (contiene)
            if normalized_synonym in normalized_column or normalized_column in normalized_synonym:
                score = 0.9
                if score > best_score:
                    best_match = synonym
                    best_score = score
            
            # Fuzzy matching
            score = self._calculate_similarity(normalized_column, normalized_synonym)
            if score > best_score:
                best_match = synonym
                best_score = score
        
        # Solo retornar si supera el threshold
        if best_score >= self.threshold:
            return best_match, best_score
        
        return None, 0.0
    
    def map_columns(self, columns: List[str]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """
        Mapea una lista de columnas a campos del modelo Producto.
        
        Args:
            columns: Lista de nombres de columnas del archivo externo
            
        Returns:
            Tupla (mapping_dict, confidence_dict):
            - mapping_dict: {campo_modelo: nombre_columna_original}
            - confidence_dict: {campo_modelo: confidence_score}
        """
        mapping = {}
        confidence = {}
        
        # Para cada campo del modelo
        for field_name, synonyms in self.FIELD_SYNONYMS.items():
            best_column = None
            best_score = 0.0
            
            # Buscar la mejor coincidencia entre las columnas disponibles
            for column in columns:
                matched_synonym, score = self._find_best_match(column, synonyms)
                
                if matched_synonym and score > best_score:
                    # Verificar que esta columna no haya sido ya mapeada
                    if column not in mapping.values():
                        best_column = column
                        best_score = score
            
            # Si encontramos un match válido, agregarlo al mapping
            if best_column and best_score >= self.threshold:
                mapping[field_name] = best_column
                confidence[field_name] = best_score
        
        return mapping, confidence
    
    def infer_field_by_type(self, value: Any, available_fields: List[str]) -> Optional[str]:
        """
        Infiere el campo del modelo basándose en el tipo de dato del valor.
        
        Args:
            value: Valor a analizar
            available_fields: Lista de campos disponibles para inferir
            
        Returns:
            Nombre del campo inferido o None
        """
        # Si el valor es numérico, probablemente es precio_venta
        if isinstance(value, (int, float, Decimal)) or (isinstance(value, str) and self._is_numeric(value)):
            if 'precio_venta' in available_fields:
                return 'precio_venta'
        
        # Si el valor es muy corto y alfanumérico, probablemente es código
        if isinstance(value, str) and len(value) <= 64 and value.replace('_', '').replace('-', '').isalnum():
            if 'codigo' in available_fields:
                return 'codigo'
        
        # Si el valor es una unidad de medida conocida
        unidades_conocidas = ['und', 'mt', 'kg', 'lt', 'un', 'm', 'cm', 'mm', 'pz']
        if isinstance(value, str) and value.lower().strip() in unidades_conocidas:
            if 'unidad' in available_fields:
                return 'unidad'
        
        return None
    
    def _is_numeric(self, value: str) -> bool:
        """
        Verifica si un string representa un número.
        
        Args:
            value: String a verificar
            
        Returns:
            True si es numérico, False en caso contrario
        """
        try:
            # Remover símbolos de moneda y espacios
            cleaned = value.replace('$', '').replace(',', '').replace(' ', '').strip()
            float(cleaned)
            return True
        except (ValueError, AttributeError):
            return False
