"""
Vistas UI para Cotizaciones v2.62.0 - SINTEL FSD
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
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
        context['clientes'] = CotizacionSelector.get_clientes_activos(empresa.id)
        context['configuraciones'] = CotizacionSelector.get_configuraciones_activas(empresa.id)
        return context

class CotizacionEditorTemplateView(CotizacionTemplateView):
    """Vista para editor con UUID."""
    template_name = 'tenant/cotizaciones/editor_cotizacion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uuid = kwargs.get('uuid')
        if uuid:
            empresa = self._resolve_empresa()
            try:
                context['cotizacion'] = CotizacionSelector.get_detail_by_uuid(
                    uuid, empresa.id, sede_ids=self._resolve_sede_ids(),
                ).get()
                context['is_draft'] = False
            except Cotizacion.DoesNotExist:
                raise Http404("Cotizacion no encontrada")
        else:
            context['cotizacion'] = None
            context['is_draft'] = True
        return context

class CotizacionEditorDraftView(CotizacionEditorTemplateView):
    """Vista para editor en modo borrador."""
    template_name = 'tenant/cotizaciones/editor_cotizacion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotizacion'] = None
        context['is_draft'] = True
        return context

class ConfiguracionCrearOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de creacion de plantilla."""
    template_name = 'tenant/cotizaciones/offcanvas_plantilla_crear.html'

class ConfiguracionEditarOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de edicion de plantilla."""
    template_name = 'tenant/cotizaciones/offcanvas_plantilla_editar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_uuid = kwargs.get('uuid')
        if config_uuid:
            empresa = self._resolve_empresa()
            context['configuracion'] = CotizacionSelector.get_configuracion_by_uuid(config_uuid, empresa.id)
            if not context['configuracion']:
                raise Http404("Configuracion no encontrada")
        return context

class ConfiguracionListOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de lista de plantillas."""
    template_name = 'tenant/cotizaciones/offcanvas_list_plantillas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self._resolve_empresa()
        context['plantillas'] = CotizacionSelector.get_configuraciones_lista_completa(empresa.id)
        return context

class ConfiguracionVerOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de detalle de plantilla."""
    template_name = 'tenant/cotizaciones/offcanvas_plantilla_detalle.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_uuid = kwargs.get('uuid')
        if config_uuid:
            empresa = self._resolve_empresa()
            context['configuracion'] = CotizacionSelector.get_configuracion_by_uuid(config_uuid, empresa.id)
            if not context['configuracion']:
                raise Http404("Configuracion no encontrada")
        return context

class CotizacionDetalleOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de detalle de cotizacion."""
    template_name = 'tenant/cotizaciones/offcanvas_detalle_cotizacion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uuid = kwargs.get('uuid')
        if uuid:
            empresa = self._resolve_empresa()
            try:
                context['cotizacion'] = CotizacionSelector.get_detail_by_uuid(
                    uuid, empresa.id, sede_ids=self._resolve_sede_ids(),
                ).get()
            except Cotizacion.DoesNotExist:
                raise Http404("Cotizacion no encontrada")
        return context
