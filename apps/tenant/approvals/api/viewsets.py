"""
SolicitudAprobacionViewSet -- Fase 7 de PLAN_CENTRO_APROBACIONES_DASHBOARD_
COMPRAS.md (#31): API del Centro de Aprobaciones. Montado en
`/api/v1/dashboard/aprobaciones/` (config/api_urls.py) -- el codigo vive en
`apps/tenant/approvals/` (dueno real del dominio, #37 del plan: "Dashboard =
presentacion/control", nunca dueno de Approvals/Compras/Requisiciones).

Solo lectura + acciones de workflow -- SolicitudAprobacion nunca se crea/
edita/borra directo via API (se crea como side-effect de
RequisicionCompraBusinessService.enviar_a_aprobacion(), Fase 5).
"""

import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.shared.datatable import ColumnFilter, ColumnFilterType, DataTableServer, DataTableSpec
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import HasOrganizationalScope, IsTenantAdmin, IsTenantMember
from apps.tenant.approvals.models import SolicitudAprobacion
from apps.tenant.approvals.services import SolicitudAprobacionServiceMixin
from apps.tenant.approvals.services.selectors import SolicitudAprobacionSelector
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

from .serializers import SolicitudAprobacionDetailSerializer, SolicitudAprobacionListSerializer

logger = logging.getLogger(__name__)


class SolicitudAprobacionViewSet(
    OrganizationalContextMixin, SolicitudAprobacionServiceMixin, SintelDSVMixin, BaseTenantViewSet
):
    """
    ViewSet del Centro de Aprobaciones. Solo ADMIN (#29 del plan: "Solo
    ADMIN debe poder acceder inicialmente al Centro de Aprobaciones").
    """

    queryset = SolicitudAprobacion.objects.none()
    serializer_class = SolicitudAprobacionDetailSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        return [IsTenantMember(), IsTenantAdmin(), HasOrganizationalScope()]

    def get_queryset(self):
        if not hasattr(self, "action") or self.action is None:
            return SolicitudAprobacion.objects.none()
        if self.action == "list":
            return self.get_qs_list()
        uuid_val = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        return self.get_qs_detail(uuid_val)

    def get_serializer_class(self):
        if self.action == "list":
            return SolicitudAprobacionListSerializer
        return SolicitudAprobacionDetailSerializer

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "error": "creacion_no_soportada",
                "message": "Las Solicitudes de Aprobacion se crean automaticamente, nunca directo via API.",
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """Fase 8 del plan (#6 banner, #7 KPIs): unica fuente de los numeros
        del banner/KPIs del Centro de Aprobaciones -- nunca calculados en JS."""
        try:
            empresa_id = self._get_empresa_id_seguro()
            data = SolicitudAprobacionSelector.get_resumen(empresa_id)
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["post"], url_path="dt")
    def dt(self, request):
        """Bandeja server-side (Fase 8, #7 del plan) -- DataTables 3.x,
        mismo patron que RequisicionCompraViewSet.dt(). Por defecto solo
        PENDIENTE (la vista de trabajo real del Centro); `?estado=` en el
        payload de columna 4 permite ver otros estados."""
        # Columnas (Fase 8, #7 del plan): 0 Prioridad, 1 Tipo, 2 Documento,
        # 3 Solicitante, 4 Proyecto, 5 Origen(Cotizacion), 6 Valor, 7 Riesgo,
        # 8 Tiempo pendiente, 9 Estado, 10 Accion.
        base_qs = self.get_qs_list()
        spec = DataTableSpec(
            fields_map={
                0: "prioridad",
                8: "fecha_envio",
                9: "estado",
            },
            search_fields=[
                "snapshot_financiero__numero",
                "snapshot_financiero__cotizacion_numero",
                "snapshot_financiero__proyecto_nombre",
            ],
            base_qs=base_qs,
            serializer=SolicitudAprobacionListSerializer,
            column_filters={
                0: ColumnFilter("prioridad", ColumnFilterType.EXACT),
                1: ColumnFilter("tipo_documento", ColumnFilterType.EXACT),
                9: ColumnFilter("estado", ColumnFilterType.EXACT),
            },
        )
        return DataTableServer(spec).handle(request)

    @action(detail=True, methods=["get"], url_path="trazabilidad")
    def trazabilidad(self, request, uuid=None):
        try:
            solicitud = self.get_object()
            dto = self.service_trazabilidad(solicitud)
            return Response(dto, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="aprobar")
    def aprobar(self, request, uuid=None):
        try:
            observacion = request.data.get("observacion", "")
            success, result, status_code = self.service_aprobar(uuid, observacion)
            if not success:
                return Response(result, status=status_code)
            out_serializer = SolicitudAprobacionDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="rechazar")
    def rechazar(self, request, uuid=None):
        try:
            motivo = request.data.get("motivo", "")
            if not motivo:
                return Response(
                    {"error": "motivo_requerido", "message": "Debe indicar el motivo de rechazo."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            success, result, status_code = self.service_rechazar(uuid, motivo)
            if not success:
                return Response(result, status=status_code)
            out_serializer = SolicitudAprobacionDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)
