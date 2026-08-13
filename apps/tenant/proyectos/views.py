"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de
Proyectos. Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md).

No reemplaza la API DRF (apps/tenant/proyectos/api/viewsets.py), que sigue
viva para crear/editar/eliminar y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.proyectos.models import Proyecto, TareaCorta
from apps.tenant.proyectos.services import selectors
from apps.tenant.proyectos.services.selectors import TareaCortaSelector
from apps.tenant.proyectos.tables import ProyectoTable, TareaCortaTable

logger = logging.getLogger(__name__)


class ProyectoTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_class = ProyectoTable
    template_name = "tenant/proyectos/partials/tabla_proyectos.html"
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ProyectoTableView] Sin empresa resuelta para user=%s",
                self.request.user.pk,
            )
            return None

    def _search(self):
        return (self.request.GET.get("q") or "").strip() or None

    def _fase(self):
        return (self.request.GET.get("fase") or "").strip() or None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Proyecto.objects.none()

        # [OSF Fase F13] Antes de esta fase, la grilla HTML (lo que el
        # usuario realmente ve) no aplicaba ningun filtro de alcance
        # organizacional, a diferencia del endpoint DRF equivalente (F7) -
        # mismo patron de bug que compras Bug 1 (F5), facturas (F11) y
        # gastos (F13). NULL-safe: un registro sin sede sigue visible.
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        return selectors.qs_list(
            empresa_id=empresa_id, search=self._search(), fase=self._fase(), sede_ids=sede_ids,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = self._resolver_empresa_id()
        if empresa_id:
            context["kpis"] = selectors.kpis_list(empresa_id=empresa_id, search=self._search(), fase=self._fase())
        else:
            context["kpis"] = {"total": 0, "ejecucion": 0, "completados": 0, "pendientes": 0, "cartera": 0, "avance_prom": 0}
        context["fase_actual"] = self._fase() or ""
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
            logger.warning("[TareaCortaTableView] Sin empresa resuelta para user=%s", self.request.user.pk)
            return None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return TareaCorta.objects.none()

        empleado_uuid = (self.request.GET.get("empleado") or "").strip() or None
        estado = (self.request.GET.get("estado") or "").strip() or None
        search = (self.request.GET.get("q") or "").strip() or None
        return TareaCortaSelector.qs_por_empleado(
            empresa_id=empresa_id, empleado_uuid=empleado_uuid, estado=estado, search=search,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.object_list
        if isinstance(qs, list):
            rows = []
        else:
            rows = list(qs.values_list("estado", flat=True))
        context["kpi_total"] = len(rows)
        context["kpi_proceso"] = rows.count("EN_PROCESO")
        context["kpi_completada"] = rows.count("COMPLETADA")
        context["kpi_pendiente"] = rows.count("PENDIENTE")
        return context
