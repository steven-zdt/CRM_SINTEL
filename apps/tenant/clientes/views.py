"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de
Clientes. Expansion Fase 5-BIS (ver documentacion/plan_refactorizacion.md).

No reemplaza la API DRF (apps/tenant/clientes/api/viewsets.py), que sigue
viva para crear/editar/eliminar y para consumidores API-first. Reutiliza los
mismos selectors que la API (ClienteSelector) para no duplicar logica.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.clientes.models import Cliente
from apps.tenant.clientes.services.selectors import ClienteSelector
from apps.tenant.clientes.tables import ClienteTable

logger = logging.getLogger(__name__)


class ClienteTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_class = ClienteTable
    template_name = "tenant/clientes/partials/tabla_clientes.html"
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ClienteTableView] Sin empresa resuelta para user=%s",
                self.request.user.pk,
            )
            return None

    def _filtros(self):
        filtro = (self.request.GET.get("filtro") or "").strip()
        filters = {}
        if filtro == "JURIDICA":
            filters["tipo_persona"] = "JURIDICA"
        elif filtro == "NATURAL":
            filters["tipo_persona"] = "NATURAL"
        elif filtro == "RETENEDOR":
            filters["es_retenedor"] = True
        elif filtro == "ACTIVO":
            filters["activo"] = True
        elif filtro == "INACTIVO":
            filters["activo"] = False
        return filters

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Cliente.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ClienteSelector.get_cliente_list(empresa_id, search, self._filtros() or None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = self._resolver_empresa_id()

        # Cartera: una sola query agrupada para los clientes de la PAGINA
        # actual (misma estrategia que ClienteViewSet.list() en la API DRF)
        # -- se calcula despues de super() porque necesita el queryset ya
        # paginado por django-tables2 (context['table'].page).
        table = context["table"]
        cartera_map = {}
        if empresa_id and table.page is not None:
            # table.page.object_list son BoundRow (envoltorio de django-tables2
            # para renderizado), no instancias de Cliente -- el modelo real
            # esta en .record.
            uuids = [row.record.uuid for row in table.page.object_list if row.record.uuid]
            cartera_map = ClienteSelector.get_cartera_resumen(empresa_id, uuids)
        table.cartera_map = cartera_map

        if empresa_id:
            context["kpis"] = ClienteSelector.get_kpis(empresa_id)
        else:
            context["kpis"] = {"total": 0, "activos": 0, "inactivos": 0, "juridicas": 0, "naturales": 0, "retenedores": 0}
        return context
