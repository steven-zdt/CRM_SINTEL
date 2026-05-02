"""
Vistas UI para Cotizaciones v2.60.

# WARNING: API-First: Solo renderizan HTML (UI Shells), sin lógica de negocio.
Toda la lógica está en apps/tenant/cotizaciones/api/viewsets.py y serializers.py.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import TemplateView

from apps.tenant.clientes.models import Cliente
from apps.tenant.empresa.models import Empresa

from .configuracion.models import ConfiguracionCotizacion
from .models import Cotizacion


class CotizacionTemplateView(LoginRequiredMixin, TemplateView):
    """Vista base para templates (solo renderiza HTML)."""
    def _resolve_empresa(self):
        empresa = getattr(self.request, 'empresa', None)
        if empresa:
            return empresa

        tenant = getattr(self.request, 'tenant', None)
        empresa = getattr(tenant, 'empresa', None)
        if empresa:
            return empresa

        return Empresa.objects.only('id').first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self._resolve_empresa()
        context['clientes'] = Cliente.objects.filter(empresa_id=empresa.id, activo=True).only('id', 'razon_social').order_by('razon_social')[:100] if empresa else []
        context['configuraciones'] = ConfiguracionCotizacion.objects.filter(empresa_id=empresa.id, es_activo=True).only('id', 'nombre_configuracion').order_by('nombre_configuracion') if empresa else []
        return context


class CotizacionEditorTemplateView(CotizacionTemplateView):
    """Vista para editor con UUID."""
    template_name = 'cotizaciones/offcanvas_editar_cotizacion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uuid = kwargs.get('uuid')
        if uuid:
            try:
                empresa = self._resolve_empresa()
                cotizacion_qs = Cotizacion.objects.select_related('cliente', 'configuracion')
                if empresa:
                    cotizacion_qs = cotizacion_qs.filter(empresa_id=empresa.id)
                context['cotizacion'] = cotizacion_qs.get(uuid=uuid)
                context['is_draft'] = False
            except Cotizacion.DoesNotExist:
                raise Http404("Cotización no encontrada")
        else:
            context['cotizacion'] = None
            context['is_draft'] = True
        return context


class CotizacionEditorDraftView(CotizacionEditorTemplateView):
    """Vista para editor en modo borrador."""
    template_name = 'cotizaciones/offcanvas_crear_cotizacion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotizacion'] = None
        context['is_draft'] = True
        return context


class ConfiguracionCrearOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de creación de plantilla."""
    template_name = 'cotizaciones/offcanvas_plantilla_crear.html'


class ConfiguracionEditarOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de edición de plantilla."""
    template_name = 'cotizaciones/offcanvas_plantilla_editar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_id = kwargs.get('id')
        if config_id:
            try:
                empresa = self._resolve_empresa()
                configuracion_qs = ConfiguracionCotizacion.objects.all()
                if empresa:
                    configuracion_qs = configuracion_qs.filter(empresa_id=empresa.id)
                context['configuracion'] = configuracion_qs.get(id=config_id)
            except ConfiguracionCotizacion.DoesNotExist:
                raise Http404("Configuración no encontrada")
        return context


class ConfiguracionListOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de lista de plantillas."""
    template_name = 'cotizaciones/offcanvas_list_plantillas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self._resolve_empresa()
        context['plantillas'] = ConfiguracionCotizacion.objects.filter(empresa_id=empresa.id).only(
            'id', 'nombre_configuracion', 'es_activo', 'dias_validez', 'prefijo_secuencia', 'sufijo_secuencia', 'ultimo_numero'
        ).order_by('-es_activo', 'nombre_configuracion') if empresa else []
        return context


class ConfiguracionVerOffcanvasView(CotizacionTemplateView):
    """Vista para offcanvas de detalle de plantilla."""
    template_name = 'cotizaciones/offcanvas_plantilla_detalle.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config_id = kwargs.get('id')
        if config_id:
            try:
                empresa = self._resolve_empresa()
                configuracion_qs = ConfiguracionCotizacion.objects.all()
                if empresa:
                    configuracion_qs = configuracion_qs.filter(empresa_id=empresa.id)
                context['configuracion'] = configuracion_qs.get(id=config_id)
            except ConfiguracionCotizacion.DoesNotExist:
                raise Http404("Configuración no encontrada")
        return context
