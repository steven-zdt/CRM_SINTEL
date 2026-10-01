"""
Vista HTML server-rendered (HTMX) para los KPIs de conciliacion de
Extractos Bancarios (BAN-09). Cuentas Bancarias y Extractos Bancarios
migraron a DataTables (ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md)
-- CuentaBancariaTableView/ExtractoBancarioTableView retiradas, las tablas
las sirven POST /api/v1/bancos/{cuentas,extractos}/dt/
(CuentaBancariaViewSet.dt()/ExtractoBancarioViewSet.dt()) + DataTables JS.

No reemplaza la API DRF (apps/tenant/bancos/api/viewsets.py), que sigue
viva para crear/editar/procesar/eliminar y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.bancos.services.selectors import ExtractoBancarioKpiSelector

logger = logging.getLogger(__name__)


class ExtractoBancarioKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    """BAN-09: KPI de conciliacion a nivel de empresa (todas las cuentas/
    extractos), mostrado en la cabecera del tab Extractos."""

    template_name = "tenant/bancos/partials/kpis_extractos.html"

    def _resolver_empresa_id(self):
        """
        BUG (2026-09-12, hallazgo B-1): solo atrapaba DRFValidationError,
        a diferencia del path de creacion (BaseServiceMixin._get_empresa_id_seguro(),
        apps/tenant/api/mixins.py) que atrapa cualquier excepcion y cae al
        singleton Empresa del schema del tenant. Si la resolucion fallaba
        por otro motivo en el GET que repuebla el panel (ej. justo despues
        de subir un extracto), esta vista caia silenciosamente a KPIs en
        cero aunque la fila existiera en BD -- mismo sintoma reportado
        ("subi el extracto y no aparece"). Se replica el mismo fallback
        amplio que ya usa la capa API.
        """
        try:
            return self.get_empresa_id()
        except Exception:
            logger.warning(
                "[ExtractoBancarioKpisView] get_empresa_id() fallo para user=%s, usando fallback singleton",
                self.request.user.pk,
                exc_info=True,
            )
            from apps.tenant.empresa.models import Empresa

            empresa = Empresa.objects.only("id").first()
            return empresa.id if empresa else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = self._resolver_empresa_id()
        context["kpis"] = (
            ExtractoBancarioKpiSelector.get_kpis_empresa(empresa_id)
            if empresa_id
            else {
                "total": 0,
                "conciliadas": 0,
                "pendientes": 0,
                "pct_conciliado": 0,
                "monto_sin_conciliar": 0,
            }
        )
        return context
