"""
API Views para activación de cuentas en el esquema público.
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()
logger = logging.getLogger(__name__)


class ActivateAccountAPIView(APIView):
    """
    API endpoint para activación de cuenta mediante token.

    POST /api/public/v1/tenants/activate/
    {
        "token": "...",
        "password": "..."
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Procesa activación de cuenta y establece contraseña.
        """
        try:
            token = request.data.get("token")
            password = request.data.get("password")

            if not token or not password:
                return Response(
                    {"success": False, "error": "Token y contraseña son requeridos"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validar token
            from apps.public.tenants.services.invitations import validate_invitation_token

            token_data = validate_invitation_token(token)

            if not token_data:
                return Response(
                    {"success": False, "error": "Token inválido o expirado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Obtener usuario y establecer contraseña
            user = User.objects.get(id=token_data["user_id"])
            user.set_password(password)
            user.is_active = True
            user.save()

            logger.info(f"Cuenta activada exitosamente para usuario: {user.email}")

            # Obtener tenant para redirección
            from apps.public.tenants.models import Client

            tenant = Client.objects.get(id=token_data["tenant_id"])
            tenant_domain = (
                tenant.domains.only("id", "domain", "is_primary").filter(is_primary=True).first()
            )

            login_url = f"http://{tenant_domain.domain}/" if tenant_domain else "/"

            return Response(
                {
                    "success": True,
                    "message": "Cuenta activada exitosamente",
                    "redirect_url": login_url,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"success": False, "error": "Usuario no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error activando cuenta: {e}", exc_info=True)
            return Response(
                {"success": False, "error": "Error interno del servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CreateTenantOnboardingAPIView(APIView):
    """Endpoint público para crear tenant + admin y devolver un One-Time-Token (OTT).

    POST /api/public/v1/tenants/onboarding/create/
    JSON body:
      - company_name
      - admin_email
      - admin_password
      - schema_name (optional)
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # Evitar SessionAuthentication y CSRF para este endpoint público

    def post(self, request):
        data = request.data or {}
        company_name = data.get("company_name")
        admin_email = data.get("admin_email")
        schema_name = data.get("schema_name")

        if not company_name or not admin_email:
            return Response({"detail": "company_name y admin_email son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.public.tenants.services.onboarding import create_onboarding_ott

            result = create_onboarding_ott(company_name, admin_email, schema_name)
            return Response({"success": True, "redirect_url": result["redirect_url"], "ott": result["ott"]}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error("Error creating onboarding tenant: %s", exc, exc_info=True)
            return Response({"success": False, "detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
