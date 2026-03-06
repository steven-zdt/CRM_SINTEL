"""
Registro automático de parsers por app (v2.40).

⚠️ PRINCIPIOS:
- Registra automáticamente los parsers de cada app al importar
- Cada app tiene sus parsers independientes
- El router de document_ingest usa estos parsers registrados
"""
import logging
from apps.services.document_ingest.app_router import register_app_parser

logger = logging.getLogger("apps.services.document_parser.register_parsers")


def register_all_parsers():
    """
    Registra todos los parsers de todas las apps.
    
    ⚠️ v2.40: Se llama automáticamente al importar este módulo.
    """
    # Registrar parsers de Cotizaciones
    try:
        from apps.services.document_parser.cotizaciones.excel_parser import parse_catalogo_to_dto
        register_app_parser("cotizaciones", "excel", parse_catalogo_to_dto)
        register_app_parser("cotizaciones", "xls", parse_catalogo_to_dto)
        register_app_parser("cotizaciones", "xlsx", parse_catalogo_to_dto)
        logger.info("Parsers de cotizaciones registrados correctamente")
    except ImportError as e:
        logger.warning(f"No se pudieron registrar parsers de cotizaciones: {e}")
    
    # Registrar parsers de Facturas
    try:
        from apps.services.document_parser.facturas.excel_parser import parse_factura_excel_to_dto
        from apps.services.document_parser.facturas.pdf_parser import parse_factura_pdf_to_dto
        
        register_app_parser("facturas", "excel", parse_factura_excel_to_dto)
        register_app_parser("facturas", "xls", parse_factura_excel_to_dto)
        register_app_parser("facturas", "xlsx", parse_factura_excel_to_dto)
        register_app_parser("facturas", "pdf", parse_factura_pdf_to_dto)
        
        logger.info("Parsers de facturas registrados correctamente")
    except ImportError as e:
        logger.warning(f"No se pudieron registrar parsers de facturas: {e}")


# Registrar automáticamente al importar
register_all_parsers()
