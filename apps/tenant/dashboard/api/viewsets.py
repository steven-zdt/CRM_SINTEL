"""
ViewSet para Dashboard v3.9.4 — Endpoints de métricas consolidadas.
FSD Architecture: hereda BaseTenantViewSet + ServiceMixin
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember
from apps.tenant.dashboard.api.serializers import DashboardMetricasSerializer
from apps.tenant.dashboard.services.business_service import DashboardBusinessService


class DashboardViewSet(BaseTenantViewSet):
    """
    ViewSet para el Dashboard Ejecutivo.

    Endpoints:
    - GET /api/v1/dashboard/ — listar métricas consolidadas
    - GET /api/v1/dashboard/metricas/ — acceso alternativo
    - GET /api/v1/dashboard/invalidar-cache/ — invalida caché (admin)
    """

    permission_classes = [IsTenantMember]
    serializer_class = DashboardMetricasSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        # El dashboard no tiene QuerySet tradicional
        # Todas las métricas se calculan on-demand
        return super().get_queryset().none()

    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/dashboard/
        Retorna métricas consolidadas para la empresa actual.
        """
        try:
            empresa_id = self._get_empresa_id(request)

            metricas = DashboardBusinessService.obtener_metricas_consolidadas(empresa_id)

            serializer = DashboardMetricasSerializer(metricas)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"DashboardViewSet.list error: {str(e)}", exc_info=True)

            return Response(
                {"detail": "Error al cargar métricas del dashboard"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def metricas(self, request):
        """
        GET /api/v1/dashboard/metricas/
        Alias para obtener métricas (GET / también funciona).
        """
        return self.list(request)

    @action(detail=False, methods=['post'])
    def invalidar_cache(self, request):
        """
        POST /api/v1/dashboard/invalidar-cache/
        Invalida el caché de métricas (solo ADMIN).
        Útil después de operaciones masivas (import, sincronización, etc).
        """
        # Validar que sea admin
        if not self._user_is_admin(request):
            return Response(
                {"detail": "Solo administradores pueden invalidar el caché"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            empresa_id = self._get_empresa_id(request)
            DashboardBusinessService.invalidar_cache(empresa_id)

            return Response(
                {"detail": "Caché invalidado correctamente"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"detail": f"Error al invalidar caché: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _get_empresa_id(request) -> int:
        """Helper para obtener empresa_id desde request."""
        # Obtener del tenant (middleware ya lo establece)
        tenant = getattr(request, 'tenant', None)
        if tenant and hasattr(tenant, 'id'):
            return tenant.id
        raise ValueError("No se pudo determinar la empresa")

    @staticmethod
    def _user_is_admin(request) -> bool:
        """Helper para validar si el usuario es admin."""
        try:
            from apps.tenant.core.services.membership import get_user_role
            role = get_user_role(request.user, getattr(request, 'tenant', None))
            return role == 'ADMIN'
        except:
            return False
