"""
Vistas API personalizadas para endpoints comunes.

Incluye wrappers con logging para endpoints de autenticación.
"""

import logging

from rest_framework_simplejwt.views import TokenVerifyView

logger = logging.getLogger(__name__)


class LoggedTokenVerifyView(TokenVerifyView):
    """
    Wrapper de TokenVerifyView con logging para diagnóstico de 401.

    Registra:
    - Token ausente
    - Token malformado
    - Token expirado
    - Token con clave/algoritmo incorrectos
    """

    def post(self, request, *args, **kwargs):
        """
        Verifica token JWT y registra errores para diagnóstico.
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
                logger.debug("TokenVerify 200 - Token válido")
            return response
        except Exception as e:
            # Capturar excepciones de verificación (token inválido, expirado, etc.)
            logger.warning(
                "TokenVerify 401 - Error de verificación: %s | Token (primeros 10 chars): %s | IP: %s",
                str(e),
                token[:10] if token and len(token) > 10 else "N/A",
                request.META.get("REMOTE_ADDR", "N/A"),
            )
            # Re-lanzar para que DRF maneje la respuesta 401
            raise
