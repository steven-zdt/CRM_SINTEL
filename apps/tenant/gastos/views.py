"""
Vistas HTML server-rendered para los listados de gastos.

Ambas grillas ("Gastos"/Documentos Soporte y "Resoluciones DIAN") migraron a
DataTables -- POST /api/v1/gastos/dt/ (GastoViewSet.dt()) y POST
/api/v1/gastos/resoluciones/dt/ (ResolucionDIANViewSet.dt()) + DataTables JS,
ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md. DocumentoSoporteTable/
DocumentoSoporteTableView y ResolucionDIANTable/ResolucionDIANTableView
(django-tables2) retirados. Solo queda GastoKpisView (KPIs de "Gastos").

No reemplazan la API DRF (apps/tenant/gastos/api/viewsets.py) — esta vive en
paralelo para clientes API-first / tests de IDOR ya existentes.

Aislamiento multi-tenant: reutiliza SintelDSVMixin.get_empresa_id() (misma
fuente de verdad que BaseTenantViewSet) y los selectors ya existentes con
.only()/filter(empresa_id=...), en vez de reimplementar la resolucion de
empresa o el filtrado por tenant.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.gastos.services.selectors import DocumentoSelector

logger = logging.getLogger(__name__)


class GastoKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    """Renderiza los KPIs de Documentos Soporte (pestaña "Gastos")."""

    template_name = "tenant/gastos/partials/kpis_gastos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[GastoKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        if empresa_id:
            # Mismo alcance de sede (OrganizationalScope) que ya usa
            # GastoViewSet.dt()/get_qs_list() para la grilla real.
            from apps.tenant.core.services.organizational_scope import (
                OrganizationalScope,
                OrganizationalScopeError,
            )

            try:
                sede_ids = OrganizationalScope.resolve(self.request).sede_ids
            except OrganizationalScopeError:
                sede_ids = None

            qs = DocumentoSelector.get_list(empresa_id=empresa_id, sede_ids=sede_ids)
            total = qs.count()
            anulados = qs.filter(anulado=True).count()
            context["resumen"] = DocumentoSelector.get_summary(empresa_id)
            context["total_documentos"] = total
            context["total_anulados"] = anulados
            context["total_activos"] = total - anulados
        else:
            context["resumen"] = None
            context["total_documentos"] = 0
            context["total_anulados"] = 0
            context["total_activos"] = 0
        return context
