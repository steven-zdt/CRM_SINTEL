"""
Motor modular de generacion de PDF para Cotizaciones v2.60.
"""
from io import BytesIO
import logging
from django.template.loader import get_template

logger = logging.getLogger(__name__)

try:
    from xhtml2pdf import pisa
    HAS_XHTML2PDF = True
except ImportError:
    HAS_XHTML2PDF = False
    pisa = None


class CotizacionPDFGenerator:
    """
    Motor modular de PDF. Separado de la logica de negocio.
    """
    
    @staticmethod
    def render_to_pdf(template_path, context):
        """
        Renderiza un template HTML a PDF usando xhtml2pdf.
        """
        if not HAS_XHTML2PDF:
            raise ImportError(
                "xhtml2pdf no esta instalado. "
                "Instale con: pip install xhtml2pdf"
            )
        
        try:
            template = get_template(template_path)
            html = template.render(context)
            
            if not html:
                logger.error(f"[PDF Generator] Template '{template_path}' renderizado esta vacio")
                return None
            
            result = BytesIO()
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')
            
            if pdf.err:
                logger.error(f"[PDF Generator] Error generando PDF desde '{template_path}': {pdf.err}")
                return None
            
            pdf_bytes = result.getvalue()
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"[PDF Generator] Error en render_to_pdf para '{template_path}': {str(e)}", exc_info=True)
            raise
