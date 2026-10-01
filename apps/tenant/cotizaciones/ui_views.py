"""
Vistas UI para Cotizaciones v2.62.0 - SINTEL FSD
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import Http404
from django.utils import timezone
from django.views.generic import TemplateView

from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.core.services.organizational_scope import (
    OrganizationalScope,
    OrganizationalScopeError,
)

from .models import Cotizacion
from .services import CotizacionSelector


class CotizacionTemplateView(LoginRequiredMixin, TemplateView):
    """Vista base para templates (solo renderiza HTML)."""

    def _resolve_empresa(self):
        empresa = resolve_tenant_empresa(self.request)
        if not empresa:
            raise PermissionDenied("No se pudo determinar la empresa activa.")
        return empresa

    def _resolve_sede_ids(self):
        """[OSF Fase F13] mismo criterio de degradacion NULL-safe de F7/F11."""
        try:
            return OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self._resolve_empresa()
        # Uso de Selectors para carga optimizada
        context["clientes"] = CotizacionSelector.get_clientes_activos(empresa.id)
        context["configuraciones"] = CotizacionSelector.get_configuraciones_activas(empresa.id)
        return context


class CotizacionKpisView(LoginRequiredMixin, TemplateView):
    """
    KPIs del listado principal de Cotizaciones (Total/Borrador/Enviada/
    Aceptada/Vencidas/Monto), extraidos al migrar la grilla a DataTables --
    antes se computaban 100% client-side en cotizaciones.table.js sobre
    TODAS las filas ya cargadas por Tabulator (dataLoaded/dataFiltered);
    con paginacion server-side eso ya no es posible, mismo patron ya usado
    en Ventas/Compras/Gastos/Proyectos/Inventario.
    """

    template_name = "tenant/cotizaciones/partials/kpis_cotizaciones.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = resolve_tenant_empresa(self.request)
        if not empresa:
            context.update(
                {
                    "kpi_total": 0,
                    "kpi_borrador": 0,
                    "kpi_enviada": 0,
                    "kpi_aceptada": 0,
                    "kpi_vencidas": 0,
                    "kpi_monto": 0,
                }
            )
            return context

        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        qs = CotizacionSelector.get_list(empresa.id, sede_ids=sede_ids)
        hoy = timezone.localdate()
        context["kpi_total"] = qs.count()
        context["kpi_borrador"] = qs.filter(estado="BORRADOR").count()
        context["kpi_enviada"] = qs.filter(estado="ENVIADA").count()
        # Hallazgo real (2026-09-25): filtraba por 'ACEPTADA', el nombre
        # de estado anterior al rename de COTIZACIONES-02 (ACEPTADA ->
        # APROBADA) -- este KPI mostraba 0 siempre, silenciosamente, desde
        # ese rename (ningun registro real tiene ya 'ACEPTADA').
        context["kpi_aceptada"] = qs.filter(estado="APROBADA").count()
        context["kpi_vencidas"] = qs.filter(
            estado__in=["BORRADOR", "ENVIADA"],
            fecha_vencimiento__lt=hoy,
        ).count()
        context["kpi_monto"] = qs.aggregate(t=Sum("total_con_impuestos"))["t"] or 0
        return context


class CotizacionEditorTemplateView(CotizacionTemplateView):
    """Vista para editor con UUID."""

    template_name = "tenant/cotizaciones/editor_cotizacion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uuid = kwargs.get("uuid")
        if uuid:
            empresa = self._resolve_empresa()
            try:
                context["cotizacion"] = CotizacionSelector.get_detail_by_uuid(
                    uuid,
                    empresa.id,
                    sede_ids=self._resolve_sede_ids(),
                ).get()
                context["is_draft"] = False
            except Cotizacion.DoesNotExist:
                raise Http404("Cotizacion no encontrada") from None
        else:
            context["cotizacion"] = None
            context["is_draft"] = True
        return context


class CotizacionEditorDraftView(CotizacionEditorTemplateView):
    """Vista para editor en modo borrador."""

    template_name = "tenant/cotizaciones/editor_cotizacion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cotizacion"] = None
        context["is_draft"] = True
        return context


class ConfiguracionCrearOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de creacion de plantilla."""

    template_name = "tenant/cotizaciones/offcanvas_plantilla_crear.html"


class ConfiguracionEditarOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de edicion de plantilla."""

    template_name = "tenant/cotizaciones/offcanvas_plantilla_editar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_uuid = kwargs.get("uuid")
        if config_uuid:
            empresa = self._resolve_empresa()
            context["configuracion"] = CotizacionSelector.get_configuracion_by_uuid(
                config_uuid, empresa.id
            )
            if not context["configuracion"]:
                raise Http404("Configuracion no encontrada")
        return context


class ConfiguracionListOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de lista de plantillas."""

    template_name = "tenant/cotizaciones/offcanvas_list_plantillas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self._resolve_empresa()
        context["plantillas"] = CotizacionSelector.get_configuraciones_lista_completa(empresa.id)
        return context


class ConfiguracionVerOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de detalle de plantilla."""

    template_name = "tenant/cotizaciones/offcanvas_plantilla_detalle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_uuid = kwargs.get("uuid")
        if config_uuid:
            empresa = self._resolve_empresa()
            context["configuracion"] = CotizacionSelector.get_configuracion_by_uuid(
                config_uuid, empresa.id
            )
            if not context["configuracion"]:
                raise Http404("Configuracion no encontrada")
        return context


class CotizacionDetalleOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de detalle de cotizacion."""

    template_name = "tenant/cotizaciones/offcanvas_detalle_cotizacion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uuid = kwargs.get("uuid")
        if uuid:
            empresa = self._resolve_empresa()
            try:
                context["cotizacion"] = CotizacionSelector.get_detail_by_uuid(
                    uuid,
                    empresa.id,
                    sede_ids=self._resolve_sede_ids(),
                ).get()
            except Cotizacion.DoesNotExist:
                raise Http404("Cotizacion no encontrada") from None
        return context
