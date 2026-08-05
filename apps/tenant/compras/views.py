"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de
Ordenes de Compra. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplaza la API DRF (apps/tenant/compras/api/viewsets.py), que sigue
viva para crear/editar/cambiar-estado y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.compras.models import OrdenCompra
from apps.tenant.compras.services.selectors import OrdenCompraSelector
from apps.tenant.compras.tables import OrdenCompraTable

logger = logging.getLogger(__name__)


class OrdenCompraTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    model = OrdenCompra
    table_class = OrdenCompraTable
    template_name = "tenant/compras/partials/tabla_compras.html"
    table_pagination = {"per_page": 20}

    def get_queryset(self):
        self._empresa_id = None
        try:
            self._empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning("[OrdenCompraTableView] Sin empresa resuelta para user=%s", self.request.user.pk)
            return OrdenCompra.objects.none()

        search = (self.request.GET.get("q") or "").strip() or None
        estado = self.request.GET.get("estado") or None
        return OrdenCompraSelector.get_list(empresa_id=self._empresa_id, search=search, estado=estado)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = getattr(self, "_empresa_id", None)
        if empresa_id:
            qs = self.object_list
            context["kpi_total_ordenes"] = qs.count()
            context["kpi_monto_total"] = qs.exclude(estado="ANULADA").aggregate(t=Sum("total"))["t"] or 0
            context["kpi_aprobadas"] = qs.filter(Q(estado="APROBADA") | Q(estado="RECIBIDA")).count()
            context["kpi_pendientes"] = qs.filter(estado="PENDIENTE").count()
        else:
            context["kpi_total_ordenes"] = 0
            context["kpi_monto_total"] = 0
            context["kpi_aprobadas"] = 0
            context["kpi_pendientes"] = 0
        return context
