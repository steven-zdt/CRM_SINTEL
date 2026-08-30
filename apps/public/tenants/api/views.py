"""
API Views para activación de cuentas en el esquema público.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public.tenants.throttling import OnboardingCreateThrottle

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
    """Endpoint público para crear tenant + admin y disparar el enlace de acceso por email.

    POST /api/public/v1/tenants/onboarding/create/
    JSON body:
      - company_name
      - admin_email
      - schema_name (optional)

    REM ONBOARDING-01 (documentacion/AUDITORIA_ONBOARDING_TENANTS_2026-08-30.md
    Hallazgo #1 -- CRITICO): antes de esta correccion, la respuesta 201 incluia
    directamente `ott`/`redirect_url` en el cuerpo JSON, entregados a QUIEN
    HIZO EL POST -- sin verificar que ese llamante controlara `admin_email`.
    Cualquiera podia escribir el email de un tercero y, dentro del TTL de 5
    minutos del OTT, obtener una sesion Django autenticada como owner/ADMIN
    del tenant nuevo, registrado a nombre de ese tercero, antes de que el
    dueno real del correo viera el email de activacion.

    Correccion minima: el OTT/redirect_url ya NO se devuelven en la respuesta
    HTTP. `crear_tenant_con_owner()` (invocado internamente por
    `create_onboarding_ott`) ya encola -- sin cambios, mecanismo preexistente
    y ya probado -- un email de activacion real hacia `admin_email` con un
    token firmado (48h). Ese es ahora el UNICO camino de acceso al tenant
    recien creado: solo quien controla la bandeja de `admin_email` puede
    continuar el flujo.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # Evitar SessionAuthentication y CSRF para este endpoint público
    throttle_classes = [OnboardingCreateThrottle]
    throttle_scope = "tenant_onboarding_create"

    def post(self, request):
        data = request.data or {}
        company_name = data.get("company_name")
        admin_email = data.get("admin_email")
        schema_name = data.get("schema_name")

        if not company_name or not admin_email:
            return Response({"detail": "company_name y admin_email son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.public.tenants.services.onboarding import create_onboarding_ott

            # REM ONBOARDING-01: el resultado (incluyendo ott/redirect_url) se
            # descarta deliberadamente -- no se expone al llamante HTTP. El
            # unico canal de entrega valido es el email de activacion que
            # crear_tenant_con_owner() ya encola hacia admin_email.
            create_onboarding_ott(company_name, admin_email, schema_name)
            return Response(
                {
                    "success": True,
                    "detail": "Hemos iniciado la creacion de tu espacio. Revisa tu correo para continuar.",
                },
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as exc:
            # REM ONBOARDING-06 (Hallazgo #6): validate_schema_name()/
            # validate_fqdn() levantan ValidationError para nombres invalidos
            # (tildes, emoji, caracteres especiales) -- antes caian al
            # except Exception generico y respondian 500. Es un rechazo de
            # validacion legitimo, no un error de servidor.
            logger.info("Onboarding rechazado por validacion: %s", exc)
            detail = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return Response({"success": False, "detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Error creating onboarding tenant: %s", exc, exc_info=True)
            return Response(
                {"success": False, "detail": "Error interno al crear el tenant."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
