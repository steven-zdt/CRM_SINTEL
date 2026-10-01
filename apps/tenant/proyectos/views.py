"""
Vista HTML server-rendered (HTMX) para los KPIs del listado de Proyectos.
El listado en si (tabla) migro a DataTables -- POST /api/v1/proyectos/dt/
(ProyectoViewSet.dt()) + DataTables JS, ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md (ProyectoTable/
ProyectoTableView django-tables2 retirados).

No reemplaza la API DRF (apps/tenant/proyectos/api/viewsets.py), que sigue
viva para crear/editar/eliminar y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.proyectos.models import TareaCorta
from apps.tenant.proyectos.services import selectors
from apps.tenant.proyectos.services.selectors import TareaCortaSelector
from apps.tenant.proyectos.tables import TareaCortaTable

logger = logging.getLogger(__name__)


class ProyectoKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    template_name = "tenant/proyectos/partials/kpis_proyectos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ProyectoKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        if empresa_id:
            context["kpis"] = selectors.kpis_list(empresa_id=empresa_id)
        else:
            context["kpis"] = {
                "total": 0,
                "ejecucion": 0,
                "completados": 0,
                "pendientes": 0,
                "cartera": 0,
                "avance_prom": 0,
            }
        return context


class TareaCortaTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    """Renderiza el panel "Nueva Tarea" (tareas cortas embebidas en Proyectos)."""

    table_class = TareaCortaTable
    template_name = "tenant/proyectos/partials/tabla_tareas_cortas.html"
    table_pagination = False

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[TareaCortaTableView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            return None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return TareaCorta.objects.none()

        empleado_uuid = (self.request.GET.get("empleado") or "").strip() or None
        estado = (self.request.GET.get("estado") or "").strip() or None
        search = (self.request.GET.get("q") or "").strip() or None
        return TareaCortaSelector.qs_por_empleado(
            empresa_id=empresa_id,
            empleado_uuid=empleado_uuid,
            estado=estado,
            search=search,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.object_list
        rows = [] if isinstance(qs, list) else list(qs.values_list("estado", flat=True))
        context["kpi_total"] = len(rows)
        context["kpi_proceso"] = rows.count("EN_PROCESO")
        context["kpi_completada"] = rows.count("COMPLETADA")
        context["kpi_pendiente"] = rows.count("PENDIENTE")
        return context
