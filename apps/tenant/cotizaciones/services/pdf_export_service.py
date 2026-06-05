import logging
from io import BytesIO
from decimal import Decimal
from django.template.loader import get_template
from django.db.models import Prefetch

try:
    from xhtml2pdf import pisa
    HAS_XHTML2PDF = True
except ImportError:
    HAS_XHTML2PDF = False
    pisa = None

from ..models import Cotizacion, CotizacionItem
from .item_service import CotizacionItemSelector

logger = logging.getLogger(__name__)

class CotizacionPDFExportService:
    @staticmethod
    def render_to_pdf(template_path, context):
        if not HAS_XHTML2PDF:
            raise ImportError("xhtml2pdf no esta instalado.")
        
        try:
            template = get_template(template_path)
            html = template.render(context)
            
            result = BytesIO()
            pisa_status = pisa.pisaDocument(
                BytesIO(html.encode("UTF-8")), 
                result, 
                encoding='UTF-8'
            )
            
            if pisa_status.err:
                logger.error(f"Error generando PDF: {pisa_status.err}")
                return None
            
            return result.getvalue()
        except Exception as e:
            logger.error(f"Error en render_to_pdf: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def preparar_contexto(cotizacion, empresa, request=None):
        items_qs = CotizacionItemSelector.get_list(cotizacion.id, empresa.id)

        productos = [i for i in items_qs if i.tipo_item == CotizacionItem.TipoItem.PRODUCTO]
        materiales = [i for i in items_qs if i.tipo_item == CotizacionItem.TipoItem.MATERIAL]
        servicios = [i for i in items_qs if i.tipo_item == CotizacionItem.TipoItem.SERVICIO]

        subtotal = sum(Decimal(str(i.subtotal_linea or 0)) for i in items_qs)

        iva_pct = Decimal(str(cotizacion.iva_porcentaje or 19))
        aiu_admin_pct = Decimal(str(cotizacion.porcentaje_aiu_admin or 0))
        aiu_imprevistos_pct = Decimal(str(cotizacion.porcentaje_aiu_imprevistos or 0))
        aiu_utilidad_pct = Decimal(str(cotizacion.porcentaje_aiu_utilidad or 0))

        v_admin = subtotal * (aiu_admin_pct / Decimal('100.00'))
        v_imprevistos = subtotal * (aiu_imprevistos_pct / Decimal('100.00'))
        v_utilidad = subtotal * (aiu_utilidad_pct / Decimal('100.00'))
        aiu_total = v_admin + v_imprevistos + v_utilidad

        base_iva = subtotal + aiu_total
        iva_valor = base_iva * (iva_pct / Decimal('100.00'))
        total = subtotal + aiu_total + iva_valor

        aplicar_aiu = any([aiu_admin_pct > 0, aiu_imprevistos_pct > 0, aiu_utilidad_pct > 0])

        return {
            'cotizacion': cotizacion,
            'empresa': empresa,
            'seccion_1': productos,
            'seccion_2': materiales,
            'seccion_3': servicios,
            'subtotal_items': subtotal,
            'aplicar_aiu': aplicar_aiu,
            'aiu_admin_porcentaje': aiu_admin_pct,
            'aiu_imprevistos_porcentaje': aiu_imprevistos_pct,
            'aiu_utilidad_porcentaje': aiu_utilidad_pct,
            'valor_administracion': v_admin,
            'valor_imprevistos': v_imprevistos,
            'valor_utilidad': v_utilidad,
            'iva_porcentaje': iva_pct,
            'iva_valor': iva_valor,
            'total_neto': total,
            'dias_totales': cotizacion.dias_totales,
            'dias_infraestructura': cotizacion.dias_infraestructura,
            'dias_instalacion': cotizacion.dias_instalacion,
            'dias_configuracion': cotizacion.dias_configuracion,
            'dias_pruebas': cotizacion.dias_pruebas,
        }

    @classmethod
    def generar_pdf_publico(cls, cotizacion, empresa, request=None):
        context = cls.preparar_contexto(cotizacion, empresa, request)
        return cls.render_to_pdf('tenant/cotizaciones/pdf/formato_profesional.html', context)

    @classmethod
    def generar_pdf_interno(cls, cotizacion, empresa, request=None):
        context = cls.preparar_contexto(cotizacion, empresa, request)
        # Aqui se podrian anadir campos internos al contexto si fuera necesario
        return cls.render_to_pdf('tenant/cotizaciones/pdf/formato_interno.html', context)
