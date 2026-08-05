"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de
Ventas. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplaza la API DRF (apps/tenant/ventas/api/viewsets.py), que sigue
viva para crear/editar/anular y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.selectors import VentaSelector
from apps.tenant.ventas.tables import VentaTable

logger = logging.getLogger(__name__)


class VentaTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    model = Venta
    table_class = VentaTable
    template_name = "tenant/ventas/partials/tabla_ventas.html"
    table_pagination = {"per_page": 20}

    def get_queryset(self):
        self._empresa_id = None
        try:
            self._empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning("[VentaTableView] Sin empresa resuelta para user=%s", self.request.user.pk)
            return Venta.objects.none()

        search = (self.request.GET.get("q") or "").strip() or None
        estado = self.request.GET.get("estado") or None
        return VentaSelector.get_list(empresa_id=self._empresa_id, search=search, estado=estado)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = getattr(self, "_empresa_id", None)
        if empresa_id:
            qs = self.object_list
            context["kpi_total_ventas"] = qs.count()
            context["kpi_monto_total"] = qs.exclude(estado="ANULADA").aggregate(t=Sum("total_neto"))["t"] or 0
            context["kpi_borradores"] = qs.filter(estado="BORRADOR").count()
            context["kpi_facturadas"] = qs.filter(estado="FACTURADA_DIAN").count()
        else:
            context["kpi_total_ventas"] = 0
            context["kpi_monto_total"] = 0
            context["kpi_borradores"] = 0
            context["kpi_facturadas"] = 0
        return context
