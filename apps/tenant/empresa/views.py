"""
Vistas HTML server-rendered (django-tables2 + HTMX) para Empresa: Sede y
Area. Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md).

No reemplazan la API DRF (apps/tenant/empresa/api/viewsets.py), que sigue
viva para crear/editar/eliminar y para consumidores API-first. Reutilizan
los mismos selectors que la API (SedeSelector/AreaSelector) para no
duplicar logica.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.empresa.models import Area, Empresa, MailInboxConfig, Sede
from apps.tenant.empresa.services.selectors import (
    AreaSelector, EmpresaSelector, MailInboxConfigSelector, SedeSelector,
)
from apps.tenant.empresa.tables import AreaTable, EmpresaTable, MailInboxConfigTable, SedeTable

logger = logging.getLogger(__name__)


class _EmpresaTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
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


class SedeTableView(_EmpresaTableViewBase):
    table_class = SedeTable
    template_name = "tenant/empresa/partials/tabla_sedes.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Sede.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return SedeSelector.get_list(empresa_id, search)


class AreaTableView(_EmpresaTableViewBase):
    table_class = AreaTable
    template_name = "tenant/empresa/partials/tabla_areas.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Area.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return AreaSelector.get_list(empresa_id, search)


class EmpresaTableView(_EmpresaTableViewBase):
    table_class = EmpresaTable
    template_name = "tenant/empresa/partials/tabla_empresa.html"

    def get_queryset(self):
        search = (self.request.GET.get("q") or "").strip() or None
        return EmpresaSelector.get_list(search)


class MailInboxConfigTableView(_EmpresaTableViewBase):
    table_class = MailInboxConfigTable
    template_name = "tenant/empresa/partials/tabla_mailinboxconfig.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return MailInboxConfig.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return MailInboxConfigSelector.get_list(empresa_id, search)
