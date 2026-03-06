"""
Vistas UI para Cotizaciones v2.60.

⚠️ API-First: Solo renderizan HTML (UI Shells), sin lógica de negocio.
Toda la lógica está en apps/tenant/cotizaciones/api/viewsets.py y serializers.py.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import Http404

from .models import Cotizacion
from apps.tenant.empresa.models import Empresa
from apps.tenant.clientes.models import Cliente
from .configuracion.models import ConfiguracionCotizacion


class CotizacionTemplateView(LoginRequiredMixin, TemplateView):
    """Vista base para templates (solo renderiza HTML)."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = Empresa.objects.first()
        context['clientes'] = Cliente.objects.filter(activo=True).order_by('razon_social')[:100] if empresa else []
        context['configuraciones'] = ConfiguracionCotizacion.objects.filter(es_activo=True).order_by('nombre_configuracion') if empresa else []
        return context


class CotizacionEditorTemplateView(CotizacionTemplateView):
    """Vista para editor con UUID."""
    template_name = 'tenant/core/partials/cotizaciones/editor_cotizacion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uuid = kwargs.get('uuid')
        if uuid:
            try:
                context['cotizacion'] = Cotizacion.objects.select_related('cliente', 'configuracion').get(uuid=uuid)
                context['is_draft'] = False
            except Cotizacion.DoesNotExist:
                raise Http404("Cotización no encontrada")
        else:
            context['cotizacion'] = None
            context['is_draft'] = True
        return context


class CotizacionEditorDraftView(CotizacionEditorTemplateView):
    """Vista para editor en modo borrador."""
    template_name = 'tenant/core/partials/cotizaciones/editor_cotizacion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotizacion'] = None
        context['is_draft'] = True
        return context


class ConfiguracionCrearOffcanvasView(LoginRequiredMixin, TemplateView):
    """Vista para offcanvas de creación de plantilla."""
    template_name = 'tenant/core/partials/cotizaciones/offcanvas_plantilla_crear.html'


class ConfiguracionEditarOffcanvasView(LoginRequiredMixin, TemplateView):
    """Vista para offcanvas de edición de plantilla."""
    template_name = 'tenant/core/partials/cotizaciones/offcanvas_plantilla_editar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_id = kwargs.get('id')
        if config_id:
            try:
                context['configuracion'] = ConfiguracionCotizacion.objects.get(id=config_id)
            except ConfiguracionCotizacion.DoesNotExist:
                raise Http404("Configuración no encontrada")
        return context


class ConfiguracionListOffcanvasView(LoginRequiredMixin, TemplateView):
    """Vista para offcanvas de lista de plantillas."""
    template_name = 'tenant/core/partials/cotizaciones/offcanvas_list_plantillas.html'


class ConfiguracionVerOffcanvasView(LoginRequiredMixin, TemplateView):
    """Vista para offcanvas de ver detalles de plantilla (solo lectura)."""
    template_name = 'tenant/core/partials/cotizaciones/offcanvas_ver_detalle.html'
