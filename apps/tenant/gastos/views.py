"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de gastos.

Piloto de reemplazo de Tabulator (PLAN_UNICO_CORRECCIONES.md, Fase 5-BIS).
No reemplazan la API DRF (apps/tenant/gastos/api/viewsets.py) — esta vive en
paralelo para clientes API-first / tests de IDOR ya existentes. Estas vistas
solo alimentan los contenedores #gastos-panel / #resoluciones-panel del
template gastos_list.html via hx-get.

Aislamiento multi-tenant: reutiliza SintelDSVMixin.get_empresa_id() (misma
fuente de verdad que BaseTenantViewSet) y los selectors ya existentes con
.only()/filter(empresa_id=...), en vez de reimplementar la resolucion de
empresa o el filtrado por tenant.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services.selectors import DocumentoSelector, ResolucionSelector
from apps.tenant.gastos.tables import DocumentoSoporteTable, ResolucionDIANTable

logger = logging.getLogger(__name__)


class DocumentoSoporteTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    """Renderiza la tabla de Documentos Soporte (pestaña "Gastos")."""

    model = DocumentoSoporte
    table_class = DocumentoSoporteTable
    template_name = "tenant/gastos/partials/tabla_gastos.html"
    table_pagination = {"per_page": 20}

    def get_queryset(self):
        self._empresa_id = None
        try:
            self._empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning("[DocumentoSoporteTableView] Sin empresa resuelta para user=%s", self.request.user.pk)
            return DocumentoSoporte.objects.none()

        search = (self.request.GET.get("q") or "").strip() or None
        return DocumentoSelector.get_list(empresa_id=self._empresa_id, search=search)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa_id = getattr(self, "_empresa_id", None)
        if empresa_id:
            total = self.object_list.count()
            anulados = self.object_list.filter(anulado=True).count()
            context["resumen"] = DocumentoSelector.get_summary(empresa_id)
            context["total_documentos"] = total
            context["total_anulados"] = anulados
            context["total_activos"] = total - anulados
        else:
            context["resumen"] = None
            context["total_documentos"] = 0
            context["total_anulados"] = 0
            context["total_activos"] = 0
        return context


class ResolucionDIANTableView(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    """Renderiza la tabla de Resoluciones DIAN (pestaña "Resoluciones DIAN")."""

    model = ResolucionDIAN
    table_class = ResolucionDIANTable
    template_name = "tenant/gastos/partials/tabla_resoluciones.html"
    table_pagination = {"per_page": 20}

    def get_queryset(self):
        try:
            empresa_id = self.get_empresa_id()
        except DRFValidationError:
            logger.warning("[ResolucionDIANTableView] Sin empresa resuelta para user=%s", self.request.user.pk)
            return ResolucionDIAN.objects.none()

        search = (self.request.GET.get("q") or "").strip() or None
        return ResolucionSelector.get_list(empresa_id=empresa_id, search=search)
