"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de
Inventario. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplazan la API DRF (apps/tenant/inventario/api/viewsets.py), que sigue
viva para crear/editar/eliminar/kardex y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q, Sum
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.inventario.models import ActivoFijo, CategoriaItem, Producto, Servicio
from apps.tenant.inventario.services.selectors import (
    ActivoFijoSelector,
    CategoriaItemSelector,
    ProductoSelector,
    ServicioSelector,
)
from apps.tenant.inventario.tables import ActivoFijoTable, CategoriaItemTable, ProductoTable, ServicioTable

logger = logging.getLogger(__name__)


class _InventarioTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
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


class CategoriaItemTableView(_InventarioTableViewBase):
    table_class = CategoriaItemTable
    template_name = "tenant/inventario/partials/tabla_categorias.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return CategoriaItem.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return CategoriaItemSelector.get_list(empresa_id=empresa_id, search=search)


class ProductoTableView(_InventarioTableViewBase):
    table_class = ProductoTable
    template_name = "tenant/inventario/partials/tabla_productos.html"
    table_pagination = {"per_page": 15}

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Producto.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ProductoSelector.get_list(empresa_id=empresa_id, search=search)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.object_list
        if isinstance(qs, list):
            context["kpi_skus"] = 0
            context["kpi_activos"] = 0
            context["kpi_alertas"] = 0
            context["kpi_valor_total"] = 0
        else:
            context["kpi_skus"] = qs.count()
            context["kpi_activos"] = qs.filter(activo=True).count()
            context["kpi_alertas"] = qs.filter(stock_actual__lte=F("stock_minimo")).count()
            # stock_actual/costo_promedio ya estan en PRODUCTO_LIST_FIELDS (selectors.py) --
            # NO volver a llamar .only() aqui: un segundo .only() sobre un queryset que ya
            # trae campos de relacion via .only() (categoria__nombre) rompe con
            # "Field Producto.categoria cannot be both deferred and traversed using
            # select_related at the same time" (FieldError real, encontrado en F31.6).
            context["kpi_valor_total"] = sum(
                (p.stock_actual or 0) * (p.costo_promedio or 0) for p in qs
            )
        return context


class ServicioTableView(_InventarioTableViewBase):
    table_class = ServicioTable
    template_name = "tenant/inventario/partials/tabla_servicios.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Servicio.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ServicioSelector.get_list(empresa_id=empresa_id, search=search)


class ActivoFijoTableView(_InventarioTableViewBase):
    table_class = ActivoFijoTable
    template_name = "tenant/inventario/partials/tabla_activos.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return ActivoFijo.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ActivoFijoSelector.get_list(empresa_id=empresa_id, search=search)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.object_list
        context["kpi_total"] = qs.count()
        context["kpi_valor_total"] = qs.aggregate(t=Sum("costo_adquisicion"))["t"] or 0
        context["kpi_por_estado"] = list(
            qs.values("estado").annotate(cnt=Count("id")).order_by("-cnt")
        )
        return context
