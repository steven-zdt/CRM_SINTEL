"""
Vistas API personalizadas para endpoints comunes (v3.10.4).

Incluye wrappers con logging para endpoints de autenticacion.

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.
"""

import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

logger = logging.getLogger(__name__)


class SafeTokenRefreshView(TokenRefreshView):
    """
    Wrapper de TokenRefreshView que convierte User.DoesNotExist en 401.

    simplejwt no captura DoesNotExist cuando el usuario referenciado
    en el refresh token fue eliminado — genera 500 en lugar de 401.
    Este wrapper lo convierte en una respuesta 401 limpia para que
    el cliente sepa que debe volver a autenticarse.
    """

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except (ObjectDoesNotExist, Exception) as exc:
            if isinstance(exc, (TokenError, InvalidToken)):
                raise
            # User eliminado o no encontrado — token ya no es valido
            if "DoesNotExist" in type(exc).__name__ or "User matching query" in str(exc):
                logger.warning(
                    "TokenRefresh 401: usuario del token no existe (posiblemente eliminado) | IP=%s",
                    request.META.get("REMOTE_ADDR", "?"),
                )
                return Response(
                    {"detail": "Token inválido: el usuario asociado ya no existe. Vuelve a iniciar sesión."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            raise


class LoggedTokenVerifyView(TokenVerifyView):
    """
    Wrapper de TokenVerifyView con logging para diagnostico de 401.

    Registra:
    - Token ausente
    - Token malformado
    - Token expirado
    - Token con clave o algoritmo incorrectos
    - Evaluacion de seguridad de sesion si el token es valido
    """

    def post(self, request, *args, **kwargs):
        """
        Verifica token JWT, evalua coherencia de sesion y registra diagnosticos.
        """
        token = request.data.get("token") or request.headers.get("Authorization", "").replace(
            "Bearer ", ""
        )

        if not token:
            logger.warning(
                "TokenVerify 401 - Token ausente | IP: %s, User-Agent: %s",
                request.META.get("REMOTE_ADDR", "N/A"),
                request.META.get("HTTP_USER_AGENT", "N/A"),
            )
        else:
            logger.debug(
                "TokenVerify - Verificando token (primeros 10 chars: %s...) | IP: %s",
                token[:10] if len(token) > 10 else token,
                request.META.get("REMOTE_ADDR", "N/A"),
            )

        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                logger.debug("TokenVerify 200 - Token valido")
                
                # Evaluar coherencia y seguridad de la sesion
                try:
                    from rest_framework_simplejwt.tokens import UntypedToken
                    from django.contrib.auth import get_user_model
                    from apps.public.core.services.session_security import SessionSecurityHelper

                    token_obj = UntypedToken(token)
                    user_id = token_obj.get("user_id")
                    User = get_user_model()
                    user = User.objects.filter(pk=user_id).first()
                    
                    if user:
                        SessionSecurityHelper.evaluate_session_security(request, user)
                except Exception as ex:
                    logger.error(
                        "Error al evaluar seguridad de sesion en LoggedTokenVerifyView: %s",
                        str(ex),
                        exc_info=True,
                    )
            return response
        except Exception as e:
            # Capturar excepciones de verificacion (token invalido, expirado, etc.)
            logger.warning(
                "TokenVerify 401 - Error de verificacion: %s | Token (primeros 10 chars): %s | IP: %s",
                str(e),
                token[:10] if token and len(token) > 10 else "N/A",
                request.META.get("REMOTE_ADDR", "N/A"),
            )
            # Re-lanzar para que DRF maneje la respuesta 401
            raise
