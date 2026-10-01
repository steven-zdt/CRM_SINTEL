"""
Vista HTML server-rendered (HTMX) para los KPIs del listado de Ventas.

El listado en si (tabla) lo sirve POST /api/v1/ventas/dt/ (VentaViewSet.dt)
+ DataTables JS -- ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
(gate visual cerrado, django-tables2/VentaTable retirados). Esta vista NO
reemplaza la API DRF (apps/tenant/ventas/api/viewsets.py), que sigue viva
para crear/editar/anular y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.views.generic import TemplateView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.ventas.services.selectors import VentaSelector

logger = logging.getLogger(__name__)


class VentaKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    template_name = "tenant/ventas/partials/kpis_ventas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[VentaKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        if empresa_id:
            search = (self.request.GET.get("q") or "").strip() or None
            estado = self.request.GET.get("estado") or None
            qs = VentaSelector.get_list(empresa_id=empresa_id, search=search, estado=estado)
            context["kpi_total_ventas"] = qs.count()
            context["kpi_monto_total"] = (
                qs.exclude(estado="ANULADA").aggregate(t=Sum("total_neto"))["t"] or 0
            )
            context["kpi_borradores"] = qs.filter(estado="BORRADOR").count()
            context["kpi_facturadas"] = qs.filter(estado="FACTURADA_DIAN").count()
        else:
            context["kpi_total_ventas"] = 0
            context["kpi_monto_total"] = 0
            context["kpi_borradores"] = 0
            context["kpi_facturadas"] = 0
        return context
