import base64
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
from .crud_service import CotizacionCRUDService
from .item_service import CotizacionItemSelector

logger = logging.getLogger(__name__)

class CotizacionPDFExportService:
    _LOGO_MIME_BY_EXT = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'svg': 'image/svg+xml',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }

    @staticmethod
    def _logo_data_uri(empresa):
        """Codifica el logo del tenant como data URI para el PDF. Boundary de
        IO externo (storage) -- se guarda con try/except para no romper la
        generacion completa del PDF si el archivo no existe o esta corrupto."""
        if not empresa.logo:
            return None
        try:
            with empresa.logo.open('rb') as f:
                raw = f.read()
            ext = empresa.logo.name.rsplit('.', 1)[-1].lower()
            mime = CotizacionPDFExportService._LOGO_MIME_BY_EXT.get(ext, 'application/octet-stream')
            return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        except Exception:
            logger.warning(f"No se pudo leer el logo de empresa_id={empresa.id} para el PDF", exc_info=True)
            return None

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
        # import perezoso: business_service.py importa este modulo a nivel de
        # modulo (genera_pdf), un import directo aqui crearia un ciclo.
        from .business_service import CotizacionService

        items_qs = CotizacionItemSelector.get_list(cotizacion.id, empresa.id)

        productos = [i for i in items_qs if i.tipo_item == CotizacionItem.TipoItem.PRODUCTO]
        materiales = [i for i in items_qs if i.tipo_item == CotizacionItem.TipoItem.MATERIAL]
        servicios = [i for i in items_qs if i.tipo_item == CotizacionItem.TipoItem.SERVICIO]

        # Q-3: misma fuente que la SSoT (CotizacionService.calcular_totales) --
        # el mismo Sum agregado de BD, no una suma en Python sobre el queryset.
        subtotal = CotizacionCRUDService.get_items_subtotal(cotizacion.id, empresa.id)

        # REGRESION (2026-09-12): "or 19" hacia que una cotizacion con
        # iva_porcentaje=0 (exenta) se facturara al cliente con 19% de IVA
        # en el PDF, divergiendo del total real calculado por el dominio
        # (CotizacionService.calcular_totales usa "or 0", business_service.py:251).
        iva_pct = Decimal(str(cotizacion.iva_porcentaje or 0))
        aiu_admin_pct = Decimal(str(cotizacion.porcentaje_aiu_admin or 0))
        aiu_imprevistos_pct = Decimal(str(cotizacion.porcentaje_aiu_imprevistos or 0))
        aiu_utilidad_pct = Decimal(str(cotizacion.porcentaje_aiu_utilidad or 0))

        v_admin = subtotal * (aiu_admin_pct / Decimal('100.00'))
        v_imprevistos = subtotal * (aiu_imprevistos_pct / Decimal('100.00'))
        v_utilidad = subtotal * (aiu_utilidad_pct / Decimal('100.00'))
        aiu_total = v_admin + v_imprevistos + v_utilidad

        base_iva = subtotal + aiu_total
        iva_valor = base_iva * (iva_pct / Decimal('100.00'))
        # Q-3: mismo redondeo que CotizacionService._q() (ROUND_HALF_UP,
        # MONEY_Q) -- antes el PDF no cuantizaba y podia divergir en centavos
        # de `cotizacion.total_con_impuestos`, el valor realmente persistido.
        total = CotizacionService._q(subtotal + aiu_total + iva_valor)

        aplicar_aiu = any([aiu_admin_pct > 0, aiu_imprevistos_pct > 0, aiu_utilidad_pct > 0])

        return {
            'cotizacion': cotizacion,
            'empresa': empresa,
            # Q-5: branding real del tenant en vez del literal "SINTEL"
            # hardcodeado (proveedor de la plataforma, no el emisor del
            # documento). Data URI en vez de empresa.logo.url porque
            # xhtml2pdf no resuelve rutas MEDIA relativas sin un
            # link_callback dedicado -- el data URI evita ese problema.
            'logo_data_uri': CotizacionPDFExportService._logo_data_uri(empresa),
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
