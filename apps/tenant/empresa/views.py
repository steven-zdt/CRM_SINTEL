"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de
Sedes. Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md).

No reemplaza la API DRF (apps/tenant/empresa/api/viewsets.py), que sigue
viva para crear/editar/eliminar y para consumidores API-first. Reutiliza el
mismo selector que la API (SedeSelector) para no duplicar logica.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.empresa.models import Sede
from apps.tenant.empresa.services.selectors import SedeSelector
from apps.tenant.empresa.tables import SedeTable

logger = logging.getLogger(__name__)


class SedeTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_class = SedeTable
    template_name = "tenant/empresa/partials/tabla_sedes.html"
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[SedeTableView] Sin empresa resuelta para user=%s",
                self.request.user.pk,
            )
            return None

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Sede.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return SedeSelector.get_list(empresa_id, search)
