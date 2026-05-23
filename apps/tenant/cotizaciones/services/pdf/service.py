"""
Servicio de generacion de PDF para cotizaciones v2.60.
"""
import logging
from decimal import Decimal

from django.db.models import Prefetch
from django.http import HttpRequest

from apps.tenant.cotizaciones.models import Cotizacion, CotizacionItem
from apps.tenant.empresa.models import Empresa
from .generator import CotizacionPDFGenerator

logger = logging.getLogger(__name__)


def obtener_cotizacion_para_pdf(empresa_id: int, cotizacion_uuid) -> Cotizacion | None:
    """Obtiene una cotizacion con todos sus items optimizados para generacion de PDF."""
    try:
        cotizacion = Cotizacion.objects.filter(
            empresa_id=empresa_id,
            uuid=cotizacion_uuid
        ).select_related(
            'cliente', 'empresa', 'configuracion'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=CotizacionItem.objects.only(
                    'cotizacion_id', 'tipo_item', 'descripcion', 'marca', 'referencia',
                    'unidad', 'cantidad', 'costo_unitario', 'porcentaje_utilidad',
                    'precio_unitario_venta', 'subtotal_linea', 'orden',
                ).order_by('orden', 'id'),
                to_attr='items_list'
            )
        ).first()

        return cotizacion
    except Exception as e:
        logger.error(f"[PDF Service] Error obteniendo cotizacion {cotizacion_uuid}: {str(e)}")
        return None


def preparar_contexto_pdf(
    cotizacion: Cotizacion,
    empresa: Empresa,
    request: HttpRequest | None = None
) -> dict:
    """Prepara el contexto completo para el template del PDF."""
    all_items = getattr(cotizacion, 'items_list', list(cotizacion.items.all()))

    productos_items = [item for item in all_items if item.tipo_item == CotizacionItem.TipoItem.PRODUCTO]
    materiales_items = [item for item in all_items if item.tipo_item == CotizacionItem.TipoItem.MATERIAL]
    servicios_items = [item for item in all_items if item.tipo_item == CotizacionItem.TipoItem.SERVICIO]

    subtotal_items = sum(Decimal(str(item.subtotal_linea or 0)) for item in all_items)

    iva_porcentaje = Decimal(str(cotizacion.iva_porcentaje or 19))
    porcentaje_aiu_admin = Decimal(str(cotizacion.porcentaje_aiu_admin or 0))
    porcentaje_aiu_imprevistos = Decimal(str(cotizacion.porcentaje_aiu_imprevistos or 0))
    porcentaje_aiu_utilidad = Decimal(str(cotizacion.porcentaje_aiu_utilidad or 0))

    aplicar_aiu = any([porcentaje_aiu_admin > 0, porcentaje_aiu_imprevistos > 0, porcentaje_aiu_utilidad > 0])

    if aplicar_aiu:
        valor_administracion = subtotal_items * (porcentaje_aiu_admin / Decimal('100.00'))
        valor_imprevistos = subtotal_items * (porcentaje_aiu_imprevistos / Decimal('100.00'))
        valor_utilidad = subtotal_items * (porcentaje_aiu_utilidad / Decimal('100.00'))
        aiu_total = valor_administracion + valor_imprevistos + valor_utilidad
        base_iva = subtotal_items + aiu_total
        iva_valor = base_iva * (iva_porcentaje / Decimal('100.00'))
        total_neto = subtotal_items + aiu_total + iva_valor
    else:
        valor_administracion = Decimal('0.00')
        valor_imprevistos = Decimal('0.00')
        valor_utilidad = Decimal('0.00')
        iva_valor = subtotal_items * (iva_porcentaje / Decimal('100.00'))
        total_neto = subtotal_items + iva_valor

    return {
        'cotizacion': cotizacion,
        'empresa': empresa,
        'seccion_1': productos_items,
        'seccion_2': materiales_items,
        'seccion_3': servicios_items,
        'subtotal_items': subtotal_items,
        'aplicar_aiu': aplicar_aiu,
        'aiu_admin_porcentaje': porcentaje_aiu_admin,
        'aiu_imprevistos_porcentaje': porcentaje_aiu_imprevistos,
        'aiu_utilidad_porcentaje': porcentaje_aiu_utilidad,
        'valor_administracion': valor_administracion,
        'valor_imprevistos': valor_imprevistos,
        'valor_utilidad': valor_utilidad,
        'iva_porcentaje': iva_porcentaje,
        'iva_valor': iva_valor,
        'total_neto': total_neto,
    }


def render_to_pdf(context: dict, request: HttpRequest | None = None) -> bytes:
    """Genera el PDF a partir del contexto preparado usando CotizacionPDFGenerator."""
    try:
        if not isinstance(context, dict) or 'cotizacion' not in context or 'empresa' not in context:
            raise ValueError("Contexto invalido para PDF")
        
        pdf_bytes = CotizacionPDFGenerator.render_to_pdf(
            template_path='tenant/cotizaciones/pdf/formato_profesional.html',
            context=context
        )
        
        if not pdf_bytes:
            raise ValueError("PDF generado esta vacio")
        
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"[PDF Service] Error generando PDF: {str(e)}", exc_info=True)
        raise


def generar_pdf_bytes(context: dict, request: HttpRequest | None = None) -> bytes:
    """Alias para render_to_pdf (compatibilidad)."""
    return render_to_pdf(context, request)
