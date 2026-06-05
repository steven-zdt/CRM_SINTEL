"""
ViewSet para Dashboard v3.9.4 — Endpoints de métricas consolidadas.
FSD Architecture: hereda BaseTenantViewSet + ServiceMixin
"""
import logging

from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import IsTenantMember
from apps.tenant.dashboard.api.serializers import DashboardMetricasSerializer, KpiSedeSerializer
from apps.tenant.dashboard.services.business_service import DashboardBusinessService

logger = logging.getLogger(__name__)


class DashboardViewSet(SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para el Dashboard Ejecutivo.

    Endpoints:
    - GET /api/v1/dashboard/ — metricas consolidadas
    - GET /api/v1/dashboard/metricas/ — alias
    - POST /api/v1/dashboard/invalidar-cache/ — invalida cache (admin)
    """

    permission_classes = [IsTenantMember]
    serializer_class = DashboardMetricasSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        from apps.tenant.empresa.models import Empresa
        return Empresa.objects.none()

    def list(self, request, *args, **kwargs):
        """GET /api/v1/dashboard/ — metricas consolidadas."""
        try:
            empresa_id = self.get_empresa_id()
            metricas = DashboardBusinessService.obtener_metricas_consolidadas(empresa_id)
            return Response(DashboardMetricasSerializer(metricas).data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"DashboardViewSet.list error: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error al cargar metricas del dashboard"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def metricas(self, request):
        """GET /api/v1/dashboard/metricas/ — alias de list."""
        return self.list(request)

    @action(detail=False, methods=['post'])
    def invalidar_cache(self, request):
        """POST /api/v1/dashboard/invalidar-cache/ — invalida cache (admin)."""
        try:
            empresa_id = self.get_empresa_id()
            DashboardBusinessService.invalidar_cache(empresa_id)
            return Response({"detail": "Cache invalidado correctamente"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"detail": f"Error al invalidar cache: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'], url_path='kpis-por-sede')
    def kpis_por_sede(self, request):
        """GET /api/v1/dashboard/kpis-por-sede/."""
        try:
            empresa_id = self.get_empresa_id()
            fecha_inicio = parse_date(request.query_params.get('fecha_inicio') or '')
            fecha_fin = parse_date(request.query_params.get('fecha_fin') or '')
            rows = DashboardBusinessService.obtener_kpis_por_sede(
                empresa_id=empresa_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )
            return Response(KpiSedeSerializer(rows, many=True).data, status=status.HTTP_200_OK)
        except Exception:
            logger.error("DashboardViewSet.kpis_por_sede error", exc_info=True)
            return Response(
                {"detail": "Error al cargar KPIs por sede"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
