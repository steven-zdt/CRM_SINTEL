"""
Servicio de generación de PDF para cotizaciones v2.60.

# WARNING: ARQUITECTURA MODULAR: Lógica de negocio desacoplada del generador.
- Usa CotizacionPDFGenerator (módulo independiente) para generar PDFs
- # WARNING: QA: Agrupa ítems por tipo_item (PRODUCTO, MATERIAL, SERVICIO) para secciones claras
- Oculta secciones vacías
- Resumen económico secuencial con lógica AIU
- # WARNING: QA: User-Driven - Valores financieros tomados directamente del objeto cotizacion

# WARNING: PRINCIPIO DE INVERSIÓN DE DEPENDENCIAS:
- Este módulo NO conoce xhtml2pdf directamente
- Depende de la abstracción CotizacionPDFGenerator
- Si se cambia de librería PDF, solo se modifica pdf_generator.py
"""
import logging
from decimal import Decimal

from django.db.models import Prefetch
from django.http import HttpRequest

from apps.tenant.cotizaciones.models import Cotizacion, CotizacionItem
from apps.tenant.cotizaciones.utils.pdf_generator import CotizacionPDFGenerator
from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)


def obtener_cotizacion_para_pdf(empresa_id: int, cotizacion_id: int) -> Cotizacion | None:
    """
    Obtiene una cotización con todos sus items optimizados para generación de PDF.
    
    # WARNING: CRÍTICO: Incluye explícitamente seccion_modulo en los campos recuperados.
    """
    try:
        cotizacion = Cotizacion.objects.filter(
            empresa_id=empresa_id,
            pk=cotizacion_id
        ).select_related(
            'cliente', 'empresa', 'configuracion'
        ).prefetch_related(
            Prefetch(
                'items',
                queryset=CotizacionItem.objects.all()
                    .order_by('orden', 'id'),
                to_attr='items_list'
            )
        ).get(pk=cotizacion_id)
        
        logger.info(f"[PDF Service] [OK] Cotización {cotizacion_id} obtenida (items: {len(getattr(cotizacion, 'items_list', []))})")
        
        return cotizacion
    except Cotizacion.DoesNotExist:
        logger.warning(f"[PDF Service] # WARNING: Cotización {cotizacion_id} no encontrada")
        return None
    except Exception as e:
        logger.error(f"[PDF Service] [ERROR] Error obteniendo cotización {cotizacion_id}: {str(e)}")
        return None


def preparar_contexto_pdf(
    cotizacion: Cotizacion,
    empresa: Empresa,
    request: HttpRequest | None = None,
    perfil_id: int | None = None
) -> dict:
    """
    Prepara el contexto completo para el template del PDF.
    
    Args:
        cotizacion: Cotización a procesar
        empresa: Empresa (SSoT)
        request: Request HTTP (opcional)
        perfil_id: ID del perfil de configuración (opcional)
    
    Returns:
        Dict con todos los datos necesarios para renderizar el template
    """
    # Obtener todos los items del prefetch
    all_items = getattr(cotizacion, 'items_list', list(cotizacion.items.all()))
    
    logger.info(f"[PDF Service] Cotización {cotizacion.id}: Total items obtenidos: {len(all_items)}")
    
    # Obtener perfil de configuración
    perfil_configuracion = cotizacion.configuracion
    if not perfil_configuracion:
        try:
            from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
            perfil_configuracion = ConfiguracionCotizacion.objects.filter(empresa=empresa, activo=True).first()
        except Exception as e:
            logger.warning(f"[PDF Service] No se pudo obtener perfil de configuración: {str(e)}")
            perfil_configuracion = None
    
    # # WARNING: QA: Agrupar items por tipo_item (PRODUCTO, MATERIAL, SERVICIO) para secciones claras
    # Esto asegura que el PDF tenga secciones claras basadas en el tipo de item
    productos_items = [item for item in all_items if item.tipo_item == CotizacionItem.TipoItem.PRODUCTO]
    materiales_items = [item for item in all_items if item.tipo_item == CotizacionItem.TipoItem.MATERIAL]
    servicios_items = [item for item in all_items if item.tipo_item == CotizacionItem.TipoItem.SERVICIO]
    
    # Mantener compatibilidad con nombres de sección existentes
    seccion_1_items = productos_items  # PRODUCTO → Sección 1
    seccion_2_items = materiales_items  # MATERIAL → Sección 2
    seccion_3_items = servicios_items   # SERVICIO → Sección 3
    
    # Calcular totales
    subtotal_items = Decimal('0.00')
    for item in all_items:
        subtotal_items += Decimal(str(item.subtotal_linea or 0))
    
    # # WARNING: QA: User-Driven - Tomar valores directamente del objeto cotizacion
    # Los campos financieros vienen directamente del usuario, no de la plantilla
    iva_porcentaje = Decimal(str(cotizacion.iva_porcentaje or 19))
    porcentaje_aiu_admin = Decimal(str(cotizacion.porcentaje_aiu_admin or 0))
    porcentaje_aiu_imprevistos = Decimal(str(cotizacion.porcentaje_aiu_imprevistos or 0))
    porcentaje_aiu_utilidad = Decimal(str(cotizacion.porcentaje_aiu_utilidad or 0))
    
    # Verificar si aplica AIU (si alguno de los porcentajes es mayor a 0)
    aplicar_aiu = (
        porcentaje_aiu_admin > 0 or
        porcentaje_aiu_imprevistos > 0 or
        porcentaje_aiu_utilidad > 0
    )
    
    if aplicar_aiu:
        # Calcular AIU sobre subtotal
        base_calculo_aiu = subtotal_items
        aiu_admin_porcentaje = porcentaje_aiu_admin
        aiu_imprevistos_porcentaje = porcentaje_aiu_imprevistos
        aiu_utilidad_porcentaje = porcentaje_aiu_utilidad
        
        valor_administracion = base_calculo_aiu * (aiu_admin_porcentaje / Decimal('100.00'))
        valor_imprevistos = base_calculo_aiu * (aiu_imprevistos_porcentaje / Decimal('100.00'))
        valor_utilidad = base_calculo_aiu * (aiu_utilidad_porcentaje / Decimal('100.00'))
        
        # IVA solo sobre Utilidad
        iva_valor = valor_utilidad * (iva_porcentaje / Decimal('100.00'))
        
        total_neto = subtotal_items + valor_administracion + valor_imprevistos + valor_utilidad + iva_valor
    else:
        # Modo estándar: IVA sobre subtotal
        iva_valor = subtotal_items * (iva_porcentaje / Decimal('100.00'))
        
        aiu_admin_porcentaje = Decimal('0.00')
        aiu_imprevistos_porcentaje = Decimal('0.00')
        aiu_utilidad_porcentaje = Decimal('0.00')
        valor_administracion = Decimal('0.00')
        valor_imprevistos = Decimal('0.00')
        valor_utilidad = Decimal('0.00')
        total_neto = subtotal_items + iva_valor
    
    # # WARNING: QA: Contexto completo con todos los campos financieros (User-Driven)
    context = {
        'cotizacion': cotizacion,
        'empresa': empresa,
        'perfil_configuracion': perfil_configuracion,
        'seccion_1': seccion_1_items,  # PRODUCTO
        'seccion_2': seccion_2_items,  # MATERIAL
        'seccion_3': seccion_3_items,  # SERVICIO
        'subtotal_items': subtotal_items,
        'aplicar_aiu': aplicar_aiu,
        # # WARNING: QA: Campos de AIU tomados directamente del objeto cotizacion (User-Driven)
        'aiu_admin_porcentaje': aiu_admin_porcentaje,
        'aiu_imprevistos_porcentaje': aiu_imprevistos_porcentaje,
        'aiu_utilidad_porcentaje': aiu_utilidad_porcentaje,
        'valor_administracion': valor_administracion,
        'valor_imprevistos': valor_imprevistos,
        'valor_utilidad': valor_utilidad,
        # # WARNING: QA: iva_porcentaje tomado directamente del objeto cotizacion (User-Driven)
        'iva_porcentaje': iva_porcentaje,
        'iva_valor': iva_valor,
        'total_neto': total_neto,
    }
    
    logger.info(f"[PDF Service] Contexto preparado: {len(all_items)} items, aplicar_aiu={aplicar_aiu}")
    return context


def render_to_pdf(context: dict, request: HttpRequest | None = None) -> bytes:
    """
    Genera el PDF a partir del contexto preparado usando CotizacionPDFGenerator.
    
    # WARNING: ARQUITECTURA: Delega la generación del PDF al módulo generador desacoplado.
    Este método solo valida el contexto y delega al generador.
    NO contiene lógica de renderizado de PDF (eso está en pdf_generator.py).
    
    Args:
        context: Contexto con datos de la cotización
        request: Request HTTP (opcional, no usado actualmente pero mantenido para compatibilidad)
    
    Returns:
        bytes del PDF generado
    
    Raises:
        ValueError: Si el contexto es inválido o el PDF está vacío
        ImportError: Si xhtml2pdf no está instalado
        Exception: Si hay error generando el PDF
    """
    try:
        # Validar que el contexto tenga los campos necesarios
        if not isinstance(context, dict):
            raise ValueError(f"Contexto no es un diccionario: {type(context)}")
        if 'cotizacion' not in context:
            raise ValueError("Contexto no contiene 'cotizacion'")
        if 'empresa' not in context:
            raise ValueError("Contexto no contiene 'empresa'")
        
        # # WARNING: ARQUITECTURA: Delegar al módulo generador desacoplado
        # El generador es el único que conoce xhtml2pdf
        # NO hay lógica de renderizado aquí - todo está en pdf_generator.py
        pdf_bytes = CotizacionPDFGenerator.render_to_pdf(
            template_path='pdf/cotizacion_format.html',
            context=context
        )
        
        if not pdf_bytes:
            raise ValueError("PDF generado está vacío o hubo un error en la generación")
        
        logger.info(f"[PDF Service] PDF generado exitosamente: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except ImportError as e:
        # Re-lanzar ImportError con contexto adicional
        logger.error(f"[PDF Service] Error de importación: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"[PDF Service] Error generando PDF: {str(e)}", exc_info=True)
        raise


# Alias para compatibilidad con código existente
def generar_pdf_bytes(context: dict, request: HttpRequest | None = None) -> bytes:
    """
    Alias para render_to_pdf (compatibilidad con código existente).
    """
    return render_to_pdf(context, request)
