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
        """Renderiza el formulario de activacion con codigo numerico."""
        return render(request, "public/activate_password.html", {"error": None, "user_email": ""})

    def post(self, request):
        """Procesa activacion: valida email + codigo de 6 digitos + establece contrasena."""
        import json
        import os
        from django.conf import settings

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Formato JSON invalido"}, status=400)

        email = (data.get("email") or "").strip().lower()
        code = (data.get("code") or "").strip()
        password = data.get("password") or ""

        if not email or not code or not password:
            return JsonResponse({"success": False, "error": "Email, codigo y contrasena son obligatorios"}, status=400)

        if len(code) != 8:
            return JsonResponse({"success": False, "error": "El codigo debe tener exactamente 8 caracteres"}, status=400)

        # Validar codigo en Redis (uso unico — lo elimina al consumir)
        from apps.public.tenants.services.invitations import validate_activation_code
        payload = validate_activation_code(code)

        if not payload:
            return JsonResponse({"success": False, "error": "Codigo invalido o expirado"}, status=400)

        # Verificar que el email coincide con el usuario del payload
        try:
            user = User.objects.get(pk=payload["user_id"])
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "Usuario no encontrado"}, status=404)

        if user.email.lower() != email:
            return JsonResponse({"success": False, "error": "El email no coincide con el codigo de activacion"}, status=400)

        # Establecer contrasena y activar
        user.set_password(password)
        user.is_active = True
        user.save()

        # Audit
        try:
            from apps.public.console.models import ConsoleActionLog
            ConsoleActionLog.objects.create(
                action="USER_ACTIVATE",
                actor=user,
                target_user=user,
                metadata={"method": "code_activation", "tenant_id": payload.get("tenant_id")},
            )
        except Exception as audit_err:
            logger.warning("[AUDIT] Error registrando activacion: %s", audit_err)

        logger.info("Cuenta activada via codigo para usuario: %s", user.email)

        # Construir redirect_url al tenant
        from apps.public.tenants.models import Client
        login_url = "/"
        try:
            tenant = Client.objects.get(pk=payload["tenant_id"])
            tenant_domain = tenant.domains.filter(is_primary=True).only("domain").first()
            domain = tenant_domain.domain if tenant_domain else None
            if domain:
                activation_base = os.getenv("ACTIVATION_BASE_URL", "").strip().rstrip("/")
                if activation_base:
                    login_url = f"{activation_base}/console/"
                else:
                    protocol = getattr(settings, "SITE_PROTOCOL", "http").lower()
                    login_url = f"{protocol}://{domain}/login/"
        except Client.DoesNotExist:
            logger.warning("Tenant id=%s no encontrado tras activacion", payload.get("tenant_id"))

        return JsonResponse({"success": True, "message": "Cuenta activada exitosamente", "redirect_url": login_url})
