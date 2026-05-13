"""
PDF Service Subpackage v2.62.0 - SINTEL FSD
"""
from .service import (
    obtener_cotizacion_para_pdf,
    preparar_contexto_pdf,
    render_to_pdf,
    generar_pdf_bytes,
)
from .generator import CotizacionPDFGenerator

__all__ = [
    'obtener_cotizacion_para_pdf',
    'preparar_contexto_pdf',
    'render_to_pdf',
    'generar_pdf_bytes',
    'CotizacionPDFGenerator',
]
