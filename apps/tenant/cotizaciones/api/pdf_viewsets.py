"""
ViewSet independiente para generación de PDFs de cotizaciones v2.62.0.
"""
import logging

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.services.pdf import (
    generar_pdf_bytes,
    obtener_cotizacion_para_pdf,
    preparar_contexto_pdf,
)

logger = logging.getLogger(__name__)


class CotizacionPDFViewSet(viewsets.ViewSet):
    """
    ViewSet para generación de PDFs de cotizaciones v2.62.0.
    Endpoint: GET /api/v1/cotizaciones/pdf/{uuid}/
    """
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]

    def retrieve(self, request, pk=None):
        """
        Genera PDF de cotización.
        GET /api/v1/cotizaciones/pdf/{uuid}/
        """
        try:
            empresa = resolve_tenant_empresa(request, self)
            if not empresa:
                return Response(
                    {"detail": "No se pudo determinar la empresa activa"},
                    status=status.HTTP_403_FORBIDDEN
                )

            cotizacion = obtener_cotizacion_para_pdf(empresa.id, pk)
            if not cotizacion:
                return Response(
                    {"detail": "Cotización no encontrada"},
                    status=status.HTTP_404_NOT_FOUND
                )

            try:
                cotizacion.refresh_from_db()
            except Exception as e:
                logger.warning(f"[PDF ViewSet] Error refrescando cotización: {e}")

            context = preparar_contexto_pdf(cotizacion, empresa, request)
            pdf_bytes = generar_pdf_bytes(context, request)

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.numero_cotizacion}.pdf"'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            logger.info(f"[PDF ViewSet] PDF generado para cotización {cotizacion.uuid}")
            return response

        except Exception as e:
            import traceback
            logger.error(f"[PDF ViewSet] Error generando PDF: {str(e)}", exc_info=True)
            return Response(
                {
                    "detail": "Error al generar el PDF",
                    "message": str(e) if settings.DEBUG else "Contacte al administrador",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
