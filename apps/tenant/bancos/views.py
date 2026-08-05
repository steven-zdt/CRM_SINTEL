"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de
Bancos. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplazan la API DRF (apps/tenant/bancos/api/viewsets.py), que sigue
viva para crear/editar/procesar/eliminar y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.bancos.services.selectors import CuentaBancariaSelector, ExtractoBancarioSelector
from apps.tenant.bancos.tables import CuentaBancariaTable, ExtractoBancarioTable

logger = logging.getLogger(__name__)


class _BancosTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[%s] Sin empresa resuelta para user=%s",
                self.__class__.__name__, self.request.user.pk,
            )
            return None


class CuentaBancariaTableView(_BancosTableViewBase):
    table_class = CuentaBancariaTable
    template_name = "tenant/bancos/partials/tabla_cuentas.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return CuentaBancaria.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return CuentaBancariaSelector.get_list(empresa_id=empresa_id, search=search)


class ExtractoBancarioTableView(_BancosTableViewBase):
    table_class = ExtractoBancarioTable
    template_name = "tenant/bancos/partials/tabla_extractos.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return ExtractoBancario.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ExtractoBancarioSelector.get_list(empresa_id=empresa_id, search=search)
