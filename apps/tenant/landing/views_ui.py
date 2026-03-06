"""
Vistas UI para partials de landing (sin datos, solo estructura HTML).

⚠️ API-First: Estas vistas solo retornan HTML estructural.
Los datos se cargan vía JavaScript desde las APIs JSON de la app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.tenant.api.permissions import IsTenantMember


class LandingHeaderPartialView(LoginRequiredMixin, TemplateView):
    """
    Vista que retorna el partial HTML del encabezado de landing.
    
    ⚠️ API-First: No pasa datos al template.
    El JavaScript (landing.ui.js en Core) carga los datos desde /api/v1/landing/info/
    
    Endpoint: GET /ui/landing/partials/header/
    """
    template_name = 'tenant/landing/partials/header.html'
    permission_classes = [IsTenantMember]
    
    def get_context_data(self, **kwargs):
        """
        Contexto mínimo (sin datos de landing).
        
        ⚠️ API-First: El template obtiene datos vía JavaScript.
        """
        context = super().get_context_data(**kwargs)
        return context


class LandingAuthPartialView(LoginRequiredMixin, TemplateView):
    """
    Vista que retorna el partial HTML de autenticación de landing.
    
    ⚠️ API-First: No pasa datos al template.
    El JavaScript (landing.ui.js en Core) maneja login y activación vía APIs.
    
    Endpoint: GET /ui/landing/partials/auth/
    """
    template_name = 'tenant/landing/partials/auth.html'
    permission_classes = [IsTenantMember]
    
    def get_context_data(self, **kwargs):
        """
        Contexto mínimo (sin datos).
        
        ⚠️ API-First: El template obtiene datos vía JavaScript.
        """
        context = super().get_context_data(**kwargs)
        return context


class LandingInfoPartialView(LoginRequiredMixin, TemplateView):
    """
    Vista que retorna el partial HTML de información de landing.
    
    ⚠️ API-First: No pasa datos al template.
    El JavaScript (landing.ui.js en Core) carga los datos desde /api/v1/landing/info/
    
    Endpoint: GET /ui/landing/partials/info/
    """
    template_name = 'tenant/landing/partials/info.html'
    permission_classes = [IsTenantMember]
    
    def get_context_data(self, **kwargs):
        """
        Contexto mínimo (sin datos).
        
        ⚠️ API-First: El template obtiene datos vía JavaScript.
        """
        context = super().get_context_data(**kwargs)
        return context
