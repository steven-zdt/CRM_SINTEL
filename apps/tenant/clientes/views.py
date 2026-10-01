"""
Vista HTML server-rendered (HTMX) para los KPIs del listado de Clientes.

El listado en si (tabla) lo sirve POST /api/v1/clientes/dt/
(ClienteViewSet.dt()) + DataTables JS -- ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md (patron extendido aqui,
ClienteTable/ClienteTableView django-tables2 retirados). No reemplaza la
API DRF (apps/tenant/clientes/api/viewsets.py), que sigue viva para
crear/editar/eliminar y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.clientes.services.selectors import ClienteSelector

logger = logging.getLogger(__name__)


class ClienteKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    template_name = "tenant/clientes/partials/kpis_clientes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ClienteKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        context["kpis"] = (
            ClienteSelector.get_kpis(empresa_id)
            if empresa_id
            else {
                "total": 0,
                "activos": 0,
                "inactivos": 0,
                "juridicas": 0,
                "naturales": 0,
                "retenedores": 0,
            }
        )
        return context
