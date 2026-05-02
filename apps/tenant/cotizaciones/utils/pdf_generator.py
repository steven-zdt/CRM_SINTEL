"""
Motor modular de generación de PDF para Cotizaciones v2.60.

# WARNING: ARQUITECTURA MODULAR: Separado de la lógica de negocio.
- Único punto de importación de xhtml2pdf en el proyecto
- Desacoplado de servicios y vistas
- Fácil de reemplazar por otra librería si es necesario
"""
from io import BytesIO

from django.template.loader import get_template

# # WARNING: ÚNICO PUNTO DE IMPORTACIÓN: xhtml2pdf solo se importa aquí
try:
    from xhtml2pdf import pisa
    HAS_XHTML2PDF = True
except ImportError:
    HAS_XHTML2PDF = False
    pisa = None


class CotizacionPDFGenerator:
    """
    Motor modular de PDF. Separado de la lógica de negocio.
    
    # WARNING: ARQUITECTURA: Este es el único módulo que conoce xhtml2pdf.
    Si en el futuro se necesita cambiar de librería, solo se modifica aquí.
    """
    
    @staticmethod
    def render_to_pdf(template_path, context):
        """
        Renderiza un template HTML a PDF usando xhtml2pdf.
        
        Args:
            template_path: Ruta del template HTML relativa a TEMPLATE_DIRS
                          (ej: 'tenant/cotizaciones/pdf/formato_profesional.html')
            context: Diccionario con el contexto para el template
        
        Returns:
            bytes: Contenido del PDF generado, o None si hay error
        
        Raises:
            ImportError: Si xhtml2pdf no está instalado
            TemplateDoesNotExist: Si el template no se encuentra
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not HAS_XHTML2PDF:
            raise ImportError(
                "xhtml2pdf no está instalado. "
                "Instale con: pip install xhtml2pdf"
            )
        
        try:
            # # WARNING: RUTA: La ruta debe ser relativa al directorio templates/ de la app
            # Con APP_DIRS: True, Django busca en apps/tenant/cotizaciones/templates/
            # Ejemplo: 'cotizaciones/pdf/formato_profesional.html'
            # Django buscará en: apps/tenant/cotizaciones/templates/cotizaciones/pdf/formato_profesional.html
            # # WARNING: DEBUG: Intentar cargar el template y capturar el error específico
            try:
                template = get_template(template_path)
                logger.info(f"[PDF Generator] [OK] Template cargado exitosamente: {template_path}")
            except Exception as template_error:
                logger.error(f"[PDF Generator] [ERROR] Error cargando template '{template_path}': {str(template_error)}")
                # Re-lanzar el error para que el ViewSet lo maneje
                raise
            
            html = template.render(context)
            if not html:
                logger.error(f"[PDF Generator] Template '{template_path}' renderizado está vacío")
                return None
            
            result = BytesIO()
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')
            
            if pdf.err:
                logger.error(f"[PDF Generator] Error generando PDF desde '{template_path}': {pdf.err}")
                return None
            
            pdf_bytes = result.getvalue()
            if not pdf_bytes:
                logger.error(f"[PDF Generator] PDF generado desde '{template_path}' está vacío")
                return None
            
            logger.info(f"[PDF Generator] PDF generado exitosamente: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"[PDF Generator] Error en render_to_pdf para '{template_path}': {str(e)}", exc_info=True)
            raise
