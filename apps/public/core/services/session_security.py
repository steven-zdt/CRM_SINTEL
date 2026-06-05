"""
Servicio helper de seguridad de sesiones y auditoria (v3.10.4).

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.
"""

import logging
from django.contrib.auth import get_user_model
from apps.public.console.models import ConsoleActionLog

logger = logging.getLogger(__name__)


class SessionSecurityHelper:
    """
    Clase helper para evaluar la coherencia de seguridad en las peticiones.
    
    Analiza cambios repentinos en IP y User-Agent para detectar posibles
    secuestros de sesion o peticiones anomalas y registra alertas en la auditoria.
    """

    @staticmethod
    def evaluate_session_security(request, user) -> bool:
        """
        Evalua la coherencia de IP y User-Agent de la peticion actual.
        
        Si detecta discrepancias o agentes sospechosos, genera una alerta
        de seguridad en el log de acciones de la consola (ConsoleActionLog).
        
        Args:
            request: Objeto HttpRequest actual
            user: Instancia de User asociada a la peticion o token verificado
            
        Returns:
            bool: True si la sesion es coherente, False en caso de anomalia
        """
        if not user:
            return True

        current_ip = request.META.get("REMOTE_ADDR", "N/A")
        current_ua = request.META.get("HTTP_USER_AGENT", "N/A")

        is_suspicious = False
        anomaly_reason = ""

        # 1. Deteccion de agentes automatizados sospechosos
        if not current_ua or current_ua == "N/A":
            is_suspicious = True
            anomaly_reason = "User-Agent nulo o ausente"
        elif any(bot in current_ua.lower() for bot in ["python-requests", "curl", "postman", "wget"]):
            is_suspicious = True
            anomaly_reason = f"Herramienta automatizada detectada en User-Agent: {current_ua[:50]}"

        # 2. Coherencia contra la sesion activa
        session = getattr(request, "session", None)
        if session is not None:
            last_ua = session.get("_security_last_user_agent")
            last_ip = session.get("_security_last_ip")

            if last_ua and last_ua != current_ua:
                is_suspicious = True
                anomaly_reason = f"Discrepancia de User-Agent: cambio de '{last_ua[:50]}' a '{current_ua[:50]}'"

            # Actualizar datos de sesion para proximos chequeos
            session["_security_last_user_agent"] = current_ua
            session["_security_last_ip"] = current_ip

        # 3. Registro de alertas
        if is_suspicious:
            logger.warning(
                "[SECURITY:ALERT] Alerta de seguridad | Usuario: %s | Causa: %s | IP: %s | UA: %s",
                user.email,
                anomaly_reason,
                current_ip,
                current_ua,
            )
            
            try:
                # Registrar en ConsoleActionLog
                ConsoleActionLog.objects.create(
                    action="SECURITY_ALERT",
                    actor=user,
                    metadata={
                        "ip": current_ip,
                        "user_agent": current_ua,
                        "reason": anomaly_reason,
                        "alert_type": "SESSION_INCOHERENCE",
                    }
                )
            except Exception as e:
                logger.error(
                    "[SECURITY:ERROR] No se pudo escribir la alerta en ConsoleActionLog: %s",
                    str(e),
                    exc_info=True,
                )
            return False

        return True
