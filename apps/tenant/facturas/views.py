"""
Vista HTML server-rendered (django-tables2 + HTMX) para el listado de Facturas.

Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md) del piloto ya aplicado en
`gastos`. Una sola vista parametrizada por `naturaleza` (VENTA/COMPRA) alimenta
las 2 pestañas del template `list_factura.html`. No reemplaza la API DRF
(`apps/tenant/facturas/api/viewsets.py`), que sigue viva para consumidores
API-first y para el resto de acciones (crear, editar, gestor-offcanvas, etc.).
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.selectors import FacturaSelectors
from apps.tenant.facturas.tables import FacturaTable

logger = logging.getLogger(__name__)

# (valor, etiqueta, clase-bootstrap, icono) — mismo set de filtros rapidos que
# tenian los botones data-filtro-venta-pago/data-filtro-compra-pago en JS.
FILTROS_PAGO = [
    ("", "Todas", "btn-outline-dark", "bi-list"),
    ("NO_PAGADA", "Pendientes", "btn-outline-danger", "bi-exclamation-circle"),
    ("PAGO_PARCIAL", "Parcial", "btn-outline-warning", "bi-clock-history"),
    ("PAGADA", "Pagadas", "btn-outline-success", "bi-check2-all"),
]


class FacturaTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    model = Factura
    table_class = FacturaTable
    template_name = "tenant/facturas/partials/tabla_facturas.html"
    table_pagination = {"per_page": 20}

    def get_naturaleza(self):
        nat = (self.kwargs.get("naturaleza") or "venta").upper()
        return nat if nat in (Factura.Naturaleza.VENTA, Factura.Naturaleza.COMPRA) else Factura.Naturaleza.VENTA

    def get_queryset(self):
        self._empresa_id = None
        try:
            self._empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning("[FacturaTableView] Sin empresa resuelta para user=%s", self.request.user.pk)
            return Factura.objects.none()

        search = (self.request.GET.get("q") or "").strip() or None
        qs = FacturaSelectors.qs_list(empresa_id=self._empresa_id, search=search).filter(
            naturaleza=self.get_naturaleza()
        )
        estado_pago = self.request.GET.get("estado_pago") or ""
        if estado_pago:
            qs = qs.filter(estado_pago=estado_pago)
        return qs

    def get_table_kwargs(self):
        kwargs = super().get_table_kwargs()
        naturaleza = self.get_naturaleza()
        kwargs["naturaleza"] = naturaleza
        if naturaleza == Factura.Naturaleza.COMPRA:
            kwargs["exclude"] = ("cotizacion_numero",)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        naturaleza = self.get_naturaleza()
        estado_actual = self.request.GET.get("estado_pago") or ""
        context["tabla_url"] = reverse("facturas:tabla", kwargs={"naturaleza": naturaleza.lower()})
        context["filtros_pago"] = [
            {"valor": v, "etiqueta": e, "clase": c, "icono": i, "activo": v == estado_actual}
            for v, e, c, i in FILTROS_PAGO
        ]
        return context
