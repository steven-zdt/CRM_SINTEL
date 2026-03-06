"""
Vistas core para el esquema público.

Lógica de redirección inteligente para el dominio público (sintel.com).
"""
from django.shortcuts import redirect
from django.views.generic import View
from django.urls import reverse


class PublicIndexView(View):
    """
    Vista índice para el dominio público (sintel.com).
    
    Lógica de redirección:
    - Si el usuario está autenticado y es staff: redirige a la consola de gestión
    - Si el usuario está autenticado pero no es staff: redirige a lista de tenants del usuario
    - Si es usuario anónimo: redirige al login del admin
    """
    
    def get(self, request, *args, **kwargs):
        # Si el usuario ya está logueado en el público
        if request.user.is_authenticated:
            # Si es staff o superuser, redirige a la consola de gestión
            if request.user.is_staff or request.user.is_superuser:
                return redirect(reverse('console:dashboard'))
            
            # Si es usuario normal, redirige al login (no tiene acceso a consola)
            # TODO: Implementar vista de selección de tenant para usuarios normales
            return redirect(reverse('admin:login'))
        
        # Si es usuario anónimo en dominio público, redirige al login
        return redirect(reverse('admin:login'))
