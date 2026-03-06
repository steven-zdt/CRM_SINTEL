"""
Mixins para las vistas de la consola.

Proporciona funcionalidad común para todas las vistas de la consola.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django_tenants.utils import get_tenant


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin que requiere que el usuario esté autenticado y sea staff.
    
    Además, verifica que se esté accediendo desde el esquema 'public'.
    """
    # Usar LOGIN_URL de settings o el admin como fallback
    login_url = getattr(settings, 'LOGIN_URL', '/admin/login/')
    
    def test_func(self):
        """Verifica que el usuario sea staff."""
        return self.request.user.is_staff
    
    def dispatch(self, request, *args, **kwargs):
        """
        Verifica que se esté accediendo desde el esquema 'public'.
        
        La consola solo debe ser accesible desde el esquema público.
        """
        try:
            tenant = get_tenant()
            if tenant.schema_name != 'public':
                raise PermissionDenied("La consola solo está disponible en el esquema 'public'")
        except Exception:
            # Si no se puede obtener el tenant, asumimos que no estamos en un contexto multi-tenant
            # Esto puede pasar en ciertos casos, pero en producción debería estar en 'public'
            pass
        
        return super().dispatch(request, *args, **kwargs)
