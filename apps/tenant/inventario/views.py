"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de
Inventario. Productos, Servicios y Activos Fijos migraron a DataTables --
POST /api/v1/inventario/{productos,servicios,activos}/dt/
(ProductoViewSet.dt()/ServicioViewSet.dt()/ActivoFijoViewSet.dt()) +
DataTables JS, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
(ProductoTable/ProductoTableView y ServicioTable/ServicioTableView
django-tables2 retirados; ActivoFijoTable/ActivoFijoTableView retirados,
sus KPIs -- total/valor libros/por estado -- se extrajeron a
ActivoFijoKpisView, mismo patron ya usado en Ventas/Compras/Gastos/
Proyectos). Categorias sigue en django-tables2/HTMX -- no migrada en esta
pasada. "Movimientos Recientes" (Kardex) tampoco -- ver docstring de
tables.py.

No reemplazan la API DRF (apps/tenant/inventario/api/viewsets.py), que sigue
viva para crear/editar/eliminar/kardex y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Sum
from django.views.generic import TemplateView
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.inventario.models import CategoriaItem
from apps.tenant.inventario.services.selectors import (
    ActivoFijoSelector,
    CategoriaItemSelector,
    ProductoSelector,
)
from apps.tenant.inventario.tables import CategoriaItemTable

logger = logging.getLogger(__name__)


class _InventarioTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[%s] Sin empresa resuelta para user=%s",
                self.__class__.__name__,
                self.request.user.pk,
            )
            return None


class CategoriaItemTableView(_InventarioTableViewBase):
    table_class = CategoriaItemTable
    template_name = "tenant/inventario/partials/tabla_categorias.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return CategoriaItem.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return CategoriaItemSelector.get_list(empresa_id=empresa_id, search=search)


class ProductoKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    template_name = "tenant/inventario/partials/kpis_productos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ProductoKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        if not empresa_id:
            context["kpi_skus"] = 0
            context["kpi_activos"] = 0
            context["kpi_alertas"] = 0
            context["kpi_valor_total"] = 0
            return context

        qs = ProductoSelector.get_list(empresa_id=empresa_id)
        context["kpi_skus"] = qs.count()
        context["kpi_activos"] = qs.filter(activo=True).count()
        context["kpi_alertas"] = qs.filter(stock_actual__lte=F("stock_minimo")).count()
        # stock_actual/costo_promedio ya estan en PRODUCTO_LIST_FIELDS (selectors.py) --
        # NO volver a llamar .only() aqui: un segundo .only() sobre un queryset que ya
        # trae campos de relacion via .only() (categoria__nombre) rompe con
        # "Field Producto.categoria cannot be both deferred and traversed using
        # select_related at the same time" (FieldError real, encontrado en F31.6).
        #
        # REM P3-04 (docs/remediation/REM-P3-04.md): filtrar por activo=True,
        # mismo criterio que InventarioExtractor.extraer_metricas() (dashboard) --
        # antes este KPI sumaba tambien productos inactivos, dando una cifra de
        # "valor de inventario" distinta a la que se muestra en el Dashboard para
        # el mismo concepto de negocio.
        context["kpi_valor_total"] = sum(
            (p.stock_actual or 0) * (p.costo_promedio or 0) for p in qs if p.activo
        )
        return context


class ActivoFijoKpisView(LoginRequiredMixin, SintelDSVMixin, TemplateView):
    """Renderiza los KPIs de Activos Fijos (total/valor libros/por estado)."""

    template_name = "tenant/inventario/partials/kpis_activos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[ActivoFijoKpisView] Sin empresa resuelta para user=%s", self.request.user.pk
            )
            empresa_id = None

        if not empresa_id:
            context["kpi_total"] = 0
            context["kpi_valor_total"] = 0
            context["kpi_por_estado"] = []
            return context

        qs = ActivoFijoSelector.get_list(empresa_id=empresa_id)
        context["kpi_total"] = qs.count()
        context["kpi_valor_total"] = qs.aggregate(t=Sum("costo_adquisicion"))["t"] or 0
        context["kpi_por_estado"] = list(
            qs.values("estado").annotate(cnt=Count("id")).order_by("-cnt")
        )
        return context
