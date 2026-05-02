"""
Vistas UI para partials de empresa (sin datos, solo estructura HTML).

# WARNING: API-First: Estas vistas solo retornan HTML estructural.
Los datos se cargan vía JavaScript desde las APIs JSON de la app.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.tenant.api.permissions import IsTenantMember


class EmpresaCardPartialView(LoginRequiredMixin, TemplateView):
    """
    Vista que retorna el partial HTML de la tarjeta de empresa.
    
    # WARNING: API-First: No pasa datos al template.
    El JavaScript (empresa.ui.js) carga los datos desde /api/v1/empresas/mi-empresa/
    
    Endpoint: GET /ui/empresa/partials/card/
    """
    template_name = 'tenant/core/partials/empresa/card.html'
    permission_classes = [IsTenantMember]
    
    def get_context_data(self, **kwargs):
        """
        Contexto mínimo (sin datos de empresa).
        
        # WARNING: API-First: El template obtiene datos vía JavaScript.
        """
        context = super().get_context_data(**kwargs)
        return context
