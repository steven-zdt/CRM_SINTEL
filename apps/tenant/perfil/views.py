"""
Vistas HTML server-rendered (django-tables2 + HTMX) para el listado de
Perfil. Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md).

No reemplaza la API DRF (apps/tenant/perfil/api/viewsets.py), que sigue viva
para crear/editar/eliminar/asignar-rol y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.perfil.api.permissions import get_available_actions
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.perfil.services.selectors import PerfilSelector
from apps.tenant.perfil.tables import PerfilTable

logger = logging.getLogger(__name__)


class PerfilTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_class = PerfilTable
    template_name = "tenant/perfil/partials/tabla_perfiles.html"

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[PerfilTableView] Sin empresa resuelta para user=%s",
                self.request.user.pk,
            )
            return None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return TenantProfile.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return PerfilSelector.get_list(empresa_id=empresa_id, search=search)

    def get_table_kwargs(self):
        kwargs = super().get_table_kwargs()
        requester_perfil = getattr(self.request.user, "tenant_profile", None)
        kwargs["requestor_actions"] = get_available_actions(requester_perfil)
        kwargs["requestor_user_id"] = self.request.user.pk
        return kwargs
