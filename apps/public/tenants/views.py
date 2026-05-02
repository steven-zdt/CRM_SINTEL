"""
Vistas para el módulo tenants del esquema público.
Landing page, selección de tenants y activación de cuentas.
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

User = get_user_model()
logger = logging.getLogger(__name__)


class LandingPageView(TemplateView):
    """
    Vista de landing page para el sitio público.

    Renderiza la página principal con información del producto,
    botones de login y acceso al workspace.

    Regla de Oro: 100% agnóstica de modelos de tenant,
    solo usa datos del esquema public.
    """

    template_name = "public/landing.html"

    def dispatch(self, request, *args, **kwargs):
        """
        Redirección inteligente para usuarios autenticados.
        """
        # Si el usuario está autenticado y es staff, redirige a consola
        if request.user.is_authenticated and request.user.is_staff:
            return redirect(reverse("console:dashboard"))

        # Usuario anónimo o normal: mostrar landing page
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "SINTEL - Sistema Integral de Gestión Empresarial",
                "show_login_button": not self.request.user.is_authenticated,
                "show_workspace_button": self.request.user.is_authenticated,
            }
        )
        return context


class TenantSelectView(LoginRequiredMixin, TemplateView):
    """
    Vista para selección de tenant por parte de usuarios autenticados.

    Muestra los tenants disponibles para el usuario actual.
    """

    template_name = "public/tenant_select.html"
    login_url = "/admin/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener tenants disponibles para el usuario
        # Solo mostrar tenants activos donde el usuario tiene membresía
        available_tenants = []

        if self.request.user.is_authenticated:
            from .models import TenantMembership

            memberships = TenantMembership.objects.filter(
                user=self.request.user, is_active=True, client__is_active=True
            ).select_related("client")

            for membership in memberships:
                available_tenants.append(
                    {
                        "name": membership.client.nombre,
                        "schema": membership.client.schema_name,
                        "role": membership.get_rol_display(),
                        "is_primary_admin": membership.is_primary_admin,
                        "domain": membership.client.domains.filter(is_primary=True).first(),
                    }
                )

        context.update(
            {
                "available_tenants": available_tenants,
                "user_email": self.request.user.email,
            }
        )
        return context


@method_decorator(csrf_exempt, name="dispatch")
class ActivateAccountView(View):
    """
    Vista para activación de cuenta de usuario mediante token.

    GET: Renderiza formulario de activación con token
    POST: Procesa activación y establece contraseña
    """

    def get(self, request):
        """
        Renderiza formulario de activación de cuenta.
        Responde tanto a GET /activate/ como a GET /api/public/v1/tenants/activate/
        """
        token = request.GET.get("token")
        if not token:
            # Si es una petición AJAX, devolver JSON
            if request.headers.get("Accept") == "application/json":
                return JsonResponse(
                    {"success": False, "error": "Token de activación requerido"}, status=400
                )

            return render(
                request,
                "public/activate_password.html",
                {"error": "Token de activación requerido", "token": None},
            )

        # Validar token básico (sin establecer contraseña aún)
        try:
            from apps.public.tenants.services.invitations import validate_invitation_token

            token_data = validate_invitation_token(token)

            if not token_data:
                # Si es una petición AJAX, devolver JSON
                if request.headers.get("Accept") == "application/json":
                    return JsonResponse(
                        {"success": False, "error": "Token inválido o expirado"}, status=400
                    )

                return render(
                    request,
                    "public/activate_password.html",
                    {"error": "Token inválido o expirado", "token": None},
                )

            # Obtener usuario para mostrar email
            user = User.objects.get(id=token_data["user_id"])

            # Si es una petición AJAX, devolver JSON con datos del usuario
            if request.headers.get("Accept") == "application/json":
                return JsonResponse(
                    {"success": True, "user_email": user.email, "token_valid": True}
                )

            return render(
                request,
                "public/activate_password.html",
                {"token": token, "user_email": user.email, "error": None},
            )

        except Exception as e:
            logger.error(f"Error validando token de activación: {e}", exc_info=True)

            # Si es una petición AJAX, devolver JSON
            if request.headers.get("Accept") == "application/json":
                return JsonResponse(
                    {"success": False, "error": "Error validando token de activación"}, status=500
                )

            return render(
                request,
                "public/activate_password.html",
                {"error": "Error validando token de activación", "token": None},
            )

    def post(self, request):
        """
        Procesa activación de cuenta y establece contraseña.
        """
        import json

        try:
            # Parsear JSON del request
            data = json.loads(request.body)
            token = data.get("token")
            password = data.get("password")

            if not token or not password:
                return JsonResponse(
                    {"success": False, "error": "Token y contraseña son requeridos"}, status=400
                )

            # Validar token
            from apps.public.tenants.services.invitations import validate_invitation_token

            token_data = validate_invitation_token(token)

            if not token_data:
                return JsonResponse(
                    {"success": False, "error": "Token inválido o expirado"}, status=400
                )

            # Obtener usuario y establecer contraseña
            user = User.objects.get(id=token_data["user_id"])
            user.set_password(password)
            user.is_active = True
            user.save()

            # [AUDIT] Registrar activación
            try:
                from apps.public.console.models import ConsoleActionLog
                ConsoleActionLog.objects.create(
                    action="USER_ACTIVATE",
                    actor=user,
                    target_user=user,
                    metadata={"method": "token_activation", "tenant_id": token_data["tenant_id"]}
                )
            except Exception as audit_err:
                logger.error(f"[AUDIT] Error registrando activación: {audit_err}")

            logger.info(f"Cuenta activada exitosamente para usuario: {user.email}")

            # Obtener tenant para redirección
            from apps.public.tenants.models import Client

            try:
                tenant = Client.objects.get(id=token_data["tenant_id"])
                tenant_domain = (
                    tenant.domains.only("id", "domain", "is_primary").filter(is_primary=True).first()
                )
                
                # [DEBUG] Incluir puerto en desarrollo si es necesario
                from django.conf import settings
                app_port = getattr(settings, "APP_PORT", "8000")
                domain = tenant_domain.domain if tenant_domain else "localhost"
                
                if settings.DEBUG and app_port and str(app_port) not in ("80", "443"):
                    login_url = f"http://{domain}:{app_port}/"
                else:
                    login_url = f"http://{domain}/"
                    
            except Client.DoesNotExist:
                logger.warning(f"[WARNING] Tenant {token_data['tenant_id']} no encontrado tras activación. Usando fallback.")
                login_url = "/"

            return JsonResponse(
                {
                    "success": True,
                    "message": "Cuenta activada exitosamente",
                    "redirect_url": login_url,
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Formato JSON inválido"}, status=400)
        except User.DoesNotExist:
            logger.error(f"[ERROR] Intento de activación para usuario inexistente {token_data.get('user_id')}")
            return JsonResponse({"success": False, "error": "Usuario no encontrado"}, status=404)
        except Exception as e:
            logger.error(f"Error activando cuenta: {e}", exc_info=True)
            return JsonResponse(
                {"success": False, "error": "Error interno del servidor"}, status=500
            )
