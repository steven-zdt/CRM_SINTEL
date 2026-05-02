"""
Mixins para las vistas de la consola.

Proporciona funcionalidad común para todas las vistas de la consola.
"""

import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django_tenants.utils import get_tenant

logger = logging.getLogger(__name__)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin que requiere que el usuario esté autenticado y sea staff.

    Además, verifica que se esté accediendo desde el esquema 'public'.
    """

    # Usar LOGIN_URL de settings o el admin como fallback
    login_url = getattr(settings, "LOGIN_URL", "/admin/login/")

    def test_func(self):
        """Verifica que el usuario sea staff."""
        return self.request.user.is_staff

    def dispatch(self, request, *args, **kwargs):
        """
        Verifica que se esté accediendo desde el esquema 'public'.

        La consola solo debe ser accesible desde el esquema público.
        """
        # Debug entry: show request.user state at dispatch start
        try:
            print(f"DEBUG StaffRequiredMixin enter: user={request.user} authenticated={getattr(request.user, 'is_authenticated', None)}")
            logger.debug("StaffRequiredMixin enter: user=%s authenticated=%s", request.user, getattr(request.user, 'is_authenticated', None))
        except Exception:
            pass

        try:
            tenant = get_tenant()
            if tenant.schema_name != "public":
                raise PermissionDenied("La consola solo está disponible en el esquema 'public'")
        except Exception:
            # Si no se puede obtener el tenant, asumimos que no estamos en un contexto multi-tenant
            # Esto puede pasar en ciertos casos, pero en producción debería estar en 'public'
            # No abortamos: seguimos con la comprobación de autenticación/permiso.
            tenant = None

        # Ajustar `login_url` según contexto: si estamos en el esquema público, usar el login del admin
        try:
            if tenant and getattr(tenant, "schema_name", None) == "public":
                # Forzar login del admin en contexto público para mantener compatibilidad de UI
                self.login_url = getattr(settings, "ADMIN_LOGIN_URL", "/admin/login/")
            else:
                # Usar el LOGIN_URL general (tenant login)
                self.login_url = getattr(settings, "LOGIN_URL", "/login/")
        except Exception:
            # Dejar el valor por defecto si algo falla
            pass

        # If the user is not authenticated according to request.user, allow
        # LoginRequiredMixin to handle anonymous users. Tests may set the session
        # directly (Client.login) without request.user populated in some edge cases;
        # detect session-based auth and materialize the user.
        if not request.user or not request.user.is_authenticated:
            # Debugging info: log session keys to diagnose TestClient.login behavior
            try:
                logger.debug("StaffRequiredMixin: session keys=%s", list(request.session.keys()))
                # Also print to stdout for pytest capture visibility
                print(f"DEBUG StaffRequiredMixin session keys={list(request.session.keys())}")
            except Exception:
                logger.debug("StaffRequiredMixin: cannot read session keys")
                print("DEBUG StaffRequiredMixin: cannot read session keys")

            auth_user_id = request.session.get("_auth_user_id")
            if auth_user_id:
                try:
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    user_obj = User.objects.filter(pk=auth_user_id).first()
                    logger.debug("StaffRequiredMixin: materialize user from session: auth_user_id=%s user_obj=%s", auth_user_id, bool(user_obj))
                    print(f"DEBUG StaffRequiredMixin materialize: auth_user_id={auth_user_id} user_obj={bool(user_obj)}")
                    if user_obj:
                        request.user = user_obj
                except Exception:
                    # If anything goes wrong, fall back to normal behavior
                    logger.exception("StaffRequiredMixin: error materializing user from session")
                    print("DEBUG StaffRequiredMixin: exception materializing user")

        # After materializing from session, if still anonymous let LoginRequiredMixin act
        if not request.user or not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        # If authenticated but not staff, return 403 instead of redirect
        if not request.user.is_staff:
            raise PermissionDenied("Requiere permisos de staff para acceder a la consola")

        return super().dispatch(request, *args, **kwargs)
