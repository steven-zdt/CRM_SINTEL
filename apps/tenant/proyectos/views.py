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
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.proyectos.services import selectors
from apps.tenant.proyectos.tables import ProyectoTable

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
        return selectors.qs_list(empresa_id=empresa_id, search=self._search(), fase=self._fase())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = self._resolver_empresa_id()
        if empresa_id:
            context["kpis"] = selectors.kpis_list(empresa_id=empresa_id, search=self._search(), fase=self._fase())
        else:
            context["kpis"] = {"total": 0, "ejecucion": 0, "completados": 0, "pendientes": 0, "cartera": 0, "avance_prom": 0}
        context["fase_actual"] = self._fase() or ""
        return context
