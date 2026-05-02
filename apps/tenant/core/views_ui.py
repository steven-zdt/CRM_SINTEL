"""
Vistas UI para el workspace compositor (core).

# WARNING: API-First: Esta vista solo renderiza el template workspace.html.
Los partials se cargan lazy vía HTMX y sus datos se obtienen vía JavaScript.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class WorkspaceView(LoginRequiredMixin, TemplateView):
    """
    Vista del workspace compositor.
    
    # WARNING: v2.30: API-First - Solo renderiza el template, sin lógica de negocio.
    El JS consume APIs REST directamente.
    
    # WARNING: SEGURIDAD: LoginRequiredMixin garantiza autenticación.
    El middleware require_tenant_membership valida membresía en rutas privadas.
    
    # WARNING: CSRF: ensure_csrf_cookie garantiza que la cookie csrftoken esté disponible
    para las llamadas PATCH/POST con SessionAuthentication (mismo origen).
    
    Endpoint: GET /workspace/
    """
    template_name = 'tenant/core/workspace.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Dispatch estándar - el middleware require_tenant_membership valida membresía.
        
        # WARNING: v2.30: LoginRequiredMixin garantiza autenticación.
        El middleware require_tenant_membership valida TenantMembership activa
        para rutas privadas como /workspace/.
        """
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """
        Contexto mínimo (sin datos).
        
        # WARNING: API-First: El template carga datos desde APIs REST vía JavaScript.
        """
        context = super().get_context_data(**kwargs)
        # Agregar STATIC_VERSION para cache-busting (si no está en settings)
        from django.conf import settings
        context['STATIC_VERSION'] = getattr(settings, 'STATIC_VERSION', '0')
        return context
