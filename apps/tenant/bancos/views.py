"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de
Bancos. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplazan la API DRF (apps/tenant/bancos/api/viewsets.py), que sigue
viva para crear/editar/procesar/eliminar y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.bancos.models import CuentaBancaria, ExtractoBancario
from apps.tenant.bancos.services.selectors import CuentaBancariaSelector, ExtractoBancarioSelector
from apps.tenant.bancos.tables import CuentaBancariaTable, ExtractoBancarioTable

logger = logging.getLogger(__name__)


class _BancosTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        """
        BUG (2026-09-12, hallazgo B-1): solo atrapaba DRFValidationError,
        a diferencia del path de creacion (BaseServiceMixin._get_empresa_id_seguro(),
        apps/tenant/api/mixins.py) que atrapa cualquier excepcion y cae al
        singleton Empresa del schema del tenant. Si la resolucion fallaba
        por otro motivo en el GET que repuebla el panel (ej. justo despues
        de subir un extracto), esta tabla server-rendered caia
        silenciosamente a queryset vacio aunque la fila existiera en BD --
        mismo sintoma reportado ("subi el extracto y no aparece"). Se
        replica el mismo fallback amplio que ya usa la capa API.
        """
        try:
            return self.get_empresa_id()
        except Exception:
            logger.warning(
                "[%s] get_empresa_id() fallo para user=%s, usando fallback singleton",
                self.__class__.__name__, self.request.user.pk, exc_info=True,
            )
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.only('id').first()
            return empresa.id if empresa else None


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
