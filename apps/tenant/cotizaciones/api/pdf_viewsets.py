"""
ViewSet independiente para generación de PDFs de cotizaciones v2.40.

⚠️ MÓDULO INDEPENDIENTE: ViewSet completamente separado del CotizacionViewSet principal.
- Endpoint: GET /api/v1/cotizaciones/pdf/{id}/
- Lógica delegada a pdf_service.py
- Respuesta: application/pdf
"""
import logging
from django.conf import settings
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication

from apps.tenant.empresa.models import Empresa
from apps.tenant.cotizaciones.permissions import IsCotizacionesMember, IsCotizacionesAdminOrReadOnly
from apps.tenant.cotizaciones.pdf_service import (
    obtener_cotizacion_para_pdf,
    preparar_contexto_pdf,
    generar_pdf_bytes
)

logger = logging.getLogger(__name__)


class CotizacionPDFViewSet(viewsets.ViewSet):
    """
    ViewSet independiente para generación de PDFs de cotizaciones.
    
    ⚠️ v2.40: Módulo completamente independiente del CotizacionViewSet principal.
    - Endpoint: GET /api/v1/cotizaciones/pdf/{id}/
    - Lógica delegada a pdf_service.py
    - Respuesta: application/pdf
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsCotizacionesMember, IsCotizacionesAdminOrReadOnly]
    
    def retrieve(self, request, pk=None):
        """
        Genera el PDF de la cotización.
        
        GET /api/v1/cotizaciones/pdf/{id}/
        
        ⚠️ v2.40: Generación dinámica de PDF (WeasyPrint eliminado - función deshabilitada)
        - Agrupa ítems por seccion_modulo (1.0, 2.0, 3.0)
        - Oculta secciones vacías
        - Resumen económico secuencial con lógica AIU
        - Marca de agua para cotizaciones ACEPTADAS
        
        Returns:
            - 200 OK: PDF file
            - 404 NOT FOUND: Si la cotización no existe
            - 500 INTERNAL SERVER ERROR: Si hay error generando el PDF
        """
        try:
            # ⚠️ PERFORMANCE BIBLE: Usar .only('id') para obtener empresa singleton
            empresa = Empresa.objects.only('id').first()
            if not empresa:
                return Response(
                    {"detail": "Empresa no encontrada"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ⚠️ REPARACIÓN: Obtener cotización optimizada para PDF con refresh
            cotizacion = obtener_cotizacion_para_pdf(empresa.id, int(pk))
            
            if not cotizacion:
                return Response(
                    {"detail": "Cotización no encontrada"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ⚠️ REPARACIÓN: Refrescar desde BD para asegurar datos actualizados
            try:
                cotizacion.refresh_from_db()
                logger.info(f"[PDF ViewSet] ✅ Cotización {cotizacion.id} refrescada desde BD")
            except Exception as refresh_error:
                logger.warning(f"[PDF ViewSet] ⚠️ Error refrescando cotización: {refresh_error}")
            
            # ⚠️ v2.40: Obtener perfil_id del request si está disponible (opcional)
            perfil_id = request.query_params.get('perfil_id', None)
            if perfil_id:
                try:
                    perfil_id = int(perfil_id)
                except (ValueError, TypeError):
                    perfil_id = None
                    logger.warning(f"[PDF ViewSet] perfil_id inválido en query params: {request.query_params.get('perfil_id')}")
            
            # Preparar contexto para el template
            context = preparar_contexto_pdf(cotizacion, empresa, request, perfil_id=perfil_id)
            
            # Generar PDF
            pdf_bytes = generar_pdf_bytes(context, request)
            
            # ⚠️ REPARACIÓN: Crear respuesta HTTP con el PDF y headers de no-cache
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.numero}.pdf"'
            
            # ⚠️ REPARACIÓN: Headers para evitar caché y asegurar PDF dinámico
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            logger.info(f"[PDF ViewSet] ✅ PDF generado para cotización {cotizacion.id} (sin caché)")
            
            return response
            
        except NotImplementedError as e:
            logger.error(f"[PDF ViewSet] Generación de PDF no disponible: {str(e)}")
            return Response(
                {
                    "detail": "Generación de PDF no disponible",
                    "message": "WeasyPrint ha sido eliminado del proyecto. La generación de PDF debe implementarse con una biblioteca alternativa."
                },
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[PDF ViewSet] Error generando PDF para cotización {pk}: {str(e)}\n{error_trace}", exc_info=True)
            return Response(
                {
                    "detail": "Error al generar el PDF",
                    "message": str(e),
                    "trace": error_trace if settings.DEBUG else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
