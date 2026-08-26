"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de
Proveedores. Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md).

No reemplaza la API DRF (apps/tenant/proveedores/api/viewsets.py), que sigue
viva para crear/editar/eliminar y para consumidores API-first. Reutiliza los
mismos selectors que la API (ProveedorSelector) para no duplicar logica.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proveedores.services.selectors import CuentasPagarSelector, ProveedorSelector
from apps.tenant.proveedores.tables import CuentasPagarTable, ProveedorTable

logger = logging.getLogger(__name__)


class ProveedorTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_class = ProveedorTable
    template_name = "tenant/proveedores/partials/tabla_proveedores.html"
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ProveedorTableView] Sin empresa resuelta para user=%s",
                self.request.user.pk,
            )
            return None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Proveedor.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ProveedorSelector.get_list(empresa_id, search)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = self._resolver_empresa_id()

        # CuentasPagar: una sola query agrupada para los proveedores de la
        # PAGINA actual (misma estrategia que ProveedorViewSet.list() en la
        # API DRF). table.page.object_list son BoundRow -- el modelo real
        # esta en .record (ver bug encontrado en clientes/views.py).
        table = context["table"]
        cuentas_pagar_map = {}
        if empresa_id and table.page is not None:
            uuids = [row.record.uuid for row in table.page.object_list if row.record.uuid]
            cuentas_pagar_map = ProveedorSelector.get_cuentas_pagar_resumen(empresa_id, uuids)
        table.cuentas_pagar_map = cuentas_pagar_map

        return context


class CuentasPagarTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_class = CuentasPagarTable
    template_name = "tenant/proveedores/partials/tabla_cuentas_pagar.html"
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[CuentasPagarTableView] Sin empresa resuelta para user=%s",
                self.request.user.pk,
            )
            return None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return []
        search = (self.request.GET.get("q") or "").strip() or None
        estado_pago = (self.request.GET.get("estado_pago") or "").strip() or None
        return CuentasPagarSelector.qs_list_unificado(
            empresa_id=empresa_id, estado_pago=estado_pago, search=search,
        )
