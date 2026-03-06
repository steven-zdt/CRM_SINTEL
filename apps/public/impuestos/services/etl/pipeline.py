"""
Pipeline ETL: parse -> tokenize -> normalize -> validate -> upsert

Orquesta el flujo completo de normalización.
"""
from apps.public.impuestos.models import DocumentoFuente
from apps.public.impuestos.services.etl.detectors import detect_kind
from apps.public.impuestos.services.etl.parse_pdf import parse_pdf_to_chunks
from apps.public.impuestos.services.etl.parse_html import parse_html_to_chunks
from apps.public.impuestos.services.etl.parse_xml import parse_xml_catalog
from apps.public.impuestos.services.etl.parse_excel import parse_excel_catalog
from apps.public.impuestos.services.etl.parse_csv import parse_csv_catalog
from apps.public.impuestos.services.etl.tokenizer import tokenize_sections
from apps.public.impuestos.services.etl.normalizer import normalize_payload
from apps.public.impuestos.services.etl.validators import validate_payload
from apps.public.impuestos.services.etl.upserts import upsert_catalogs


def run_etl(documento: DocumentoFuente) -> dict:
    """
    Ejecuta el pipeline ETL completo.
    
    Args:
        documento: Instancia de DocumentoFuente
        
    Returns:
        dict con estadísticas del procesamiento
        
    Raises:
        ValueError: Si el tipo de documento no es soportado
        ValidationError: Si hay errores de validación
    """
    # 1. Detectar tipo
    detection = detect_kind(documento)
    kind = detection['kind']
    
    if kind == 'OTRO':
        raise ValueError(f"Tipo de documento no soportado: {kind}")
    
    # 2. Parsear según tipo
    if not documento.archivo:
        raise ValueError("DocumentoFuente debe tener archivo para procesar")
    
    archivo_path = documento.archivo.path
    
    if kind == 'PDF':
        chunks = parse_pdf_to_chunks(archivo_path)
    elif kind == 'HTML':
        with open(archivo_path, 'rb') as f:
            html_bytes = f.read()
        chunks = parse_html_to_chunks(html_bytes)
    elif kind == 'XML':
        with open(archivo_path, 'rb') as f:
            xml_bytes = f.read()
        chunks = parse_xml_catalog(xml_bytes)
    elif kind in ('XLS', 'XLSX'):
        chunks = parse_excel_catalog(archivo_path)
    elif kind == 'CSV':
        chunks = parse_csv_catalog(archivo_path)
    else:
        raise ValueError(f"Tipo de documento no soportado: {kind}")
    
    # 3. Tokenizar
    tokens = tokenize_sections(chunks)
    
    if not tokens:
        return {
            'tokens': 0,
            'tipos_creados': 0,
            'tarifas_creadas': 0,
            'retenciones_creadas': 0,
            'codigos_creados': 0,
            'actividades_creadas': 0,
            'normas_creadas': 0,
            'warnings': ['No se encontraron tokens en el documento'],
        }
    
    # 4. Normalizar
    payload = normalize_payload(tokens)
    
    # 5. Validar
    validate_payload(payload)
    
    # 6. Upsert atómico
    stats = upsert_catalogs(payload, documento)
    
    # Agregar métricas adicionales
    stats['tokens'] = len(tokens)
    stats['tipo_documento'] = kind
    
    return stats
