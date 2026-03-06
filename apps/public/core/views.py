"""
Vistas core para el esquema público.

Landing page y redirección inteligente para el dominio público (sintel.com).
"""
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.urls import reverse


class PublicIndexView(TemplateView):
    """
    Vista índice para el dominio público (sintel.com).
    
    Renderiza la landing page profesional para usuarios anónimos.
    Si el usuario está autenticado y es staff, redirige a la consola de gestión.
    
    Template: public/core/index.html
    """
    template_name = 'public/core/index.html'
    
    def dispatch(self, request, *args, **kwargs):
        """
        Redirección inteligente para usuarios autenticados.
        Solo usuarios anónimos ven la landing page.
        """
        # Si el usuario ya está logueado en el público
        if request.user.is_authenticated:
            # Si es staff o superuser, redirige a la consola de gestión
            if request.user.is_staff or request.user.is_superuser:
                return redirect(reverse('console:dashboard'))
            
            # Si es usuario normal, redirige al login (no tiene acceso a consola)
            # TODO: Implementar vista de selección de tenant para usuarios normales
            return redirect(reverse('admin:login'))
        
        # Usuario anónimo: mostrar landing page
        return super().dispatch(request, *args, **kwargs)
