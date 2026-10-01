"""
Vista HTML server-rendered (HTMX) para los KPIs del listado de Ordenes de
Compra. Ambas grillas ("Ordenes de Compra" y "Plantillas de Numeracion")
migraron a DataTables -- POST /api/v1/compras/{dt,plantillas/dt}/
(OrdenCompraViewSet.dt()/PlantillaOrdenCompraViewSet.dt()) + DataTables JS,
ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md. OrdenCompraTable/
OrdenCompraTableView y PlantillaOrdenCompraTable/PlantillaOrdenCompraTableView
(django-tables2) retirados. Solo queda OrdenCompraKpisView (KPIs de
"Ordenes de Compra").

No reemplaza la API DRF (apps/tenant/compras/api/viewsets.py), que sigue
viva para crear/editar/cambiar-estado y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.views.generic import TemplateView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.compras.services.selectors import OrdenCompraSelector

logger = logging.getLogger(__name__)


class OrdenCompraKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    template_name = "tenant/compras/partials/kpis_compras.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[OrdenCompraKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        if empresa_id:
            # Mismo alcance sede/area (OrganizationalScope) que ya usa
            # OrdenCompraViewSet.dt()/get_qs_list() para la grilla real --
            # los KPIs deben reflejar el mismo conjunto de filas.
            from apps.tenant.core.services.organizational_scope import (
                OrganizationalScope,
                OrganizationalScopeError,
            )

            try:
                scope = OrganizationalScope.resolve(self.request)
                sede_ids, area_ids = scope.sede_ids, scope.area_ids
            except OrganizationalScopeError:
                sede_ids, area_ids = None, None

            qs = OrdenCompraSelector.get_list(
                empresa_id=empresa_id,
                sede_ids=sede_ids,
                area_ids=area_ids,
            )
            # Fase 3 (PLAN_OPTIMIZACION_COMPRAS...): un unico aggregate() con
            # Count/Sum condicionados en vez de 4 queries independientes
            # sobre el mismo queryset base.
            agregados = qs.aggregate(
                total_ordenes=Count("id"),
                monto_total=Sum("total", filter=~Q(estado="ANULADA")),
                aprobadas=Count("id", filter=Q(estado="APROBADA") | Q(estado="RECIBIDA")),
                pendientes=Count("id", filter=Q(estado="PENDIENTE")),
            )
            context["kpi_total_ordenes"] = agregados["total_ordenes"]
            context["kpi_monto_total"] = agregados["monto_total"] or 0
            context["kpi_aprobadas"] = agregados["aprobadas"]
            context["kpi_pendientes"] = agregados["pendientes"]
        else:
            context["kpi_total_ordenes"] = 0
            context["kpi_monto_total"] = 0
            context["kpi_aprobadas"] = 0
            context["kpi_pendientes"] = 0
        return context
