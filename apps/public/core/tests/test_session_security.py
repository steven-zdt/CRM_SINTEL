"""
Tests para SessionSecurityHelper y LoggedTokenVerifyView de la aplicacion core.

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from apps.public.console.models import ConsoleActionLog
from apps.public.core.services.session_security import SessionSecurityHelper


class SessionSecurityTestCase(TestCase):
    """
    Suite de pruebas para validar la evaluacion de seguridad de sesion.
    """

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        
        User = get_user_model()
        self.user = User.objects.create_user(
            username="security_test_user",
            email="security@sintel.net.co",
            password="securepassword123",
        )

    def test_clean_session_is_considered_secure(self):
        """
        Una peticion con User-Agent comun es coherente y no genera alertas.
        """
        request = self.factory.post(
            "/api/token/verify/",
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            REMOTE_ADDR="192.168.1.50",
        )
        
        # Inyectar una sesion simulada en el request
        session = {}
        request.session = session
        
        result = SessionSecurityHelper.evaluate_session_security(request, self.user)
        
        self.assertTrue(result)
        self.assertEqual(ConsoleActionLog.objects.filter(action="SECURITY_ALERT").count(), 0)
        self.assertEqual(session.get("_security_last_user_agent"), "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    def test_suspicious_user_agent_generates_alert(self):
        """
        Peticiones con agentes sospechosos (python-requests) generan una alerta en ConsoleActionLog.
        """
        request = self.factory.post(
            "/api/token/verify/",
            HTTP_USER_AGENT="python-requests/2.28.1",
            REMOTE_ADDR="192.168.1.100",
        )
        request.session = {}
        
        result = SessionSecurityHelper.evaluate_session_security(request, self.user)
        
        self.assertFalse(result)
        
        # Verificar que se creo la alerta en la base de datos
        alerts = ConsoleActionLog.objects.filter(action="SECURITY_ALERT", actor=self.user)
        self.assertEqual(alerts.count(), 1)
        
        alert = alerts.first()
        self.assertEqual(alert.metadata["reason"], "Herramienta automatizada detectada en User-Agent: python-requests/2.28.1")
        self.assertEqual(alert.metadata["ip"], "192.168.1.100")
        self.assertEqual(alert.metadata["user_agent"], "python-requests/2.28.1")

    def test_user_agent_change_in_session_generates_alert(self):
        """
        Un cambio repentino de User-Agent en la misma sesion genera una alerta.
        """
        request1 = self.factory.post(
            "/api/token/verify/",
            HTTP_USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            REMOTE_ADDR="192.168.1.50",
        )
        session = {}
        request1.session = session
        
        # Primera peticion (limpia)
        result1 = SessionSecurityHelper.evaluate_session_security(request1, self.user)
        self.assertTrue(result1)
        
        # Segunda peticion con User-Agent modificado
        request2 = self.factory.post(
            "/api/token/verify/",
            HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            REMOTE_ADDR="192.168.1.50",
        )
        request2.session = session
        
        result2 = SessionSecurityHelper.evaluate_session_security(request2, self.user)
        self.assertFalse(result2)
        
        # Verificar que se creo la alerta
        alerts = ConsoleActionLog.objects.filter(action="SECURITY_ALERT")
        self.assertEqual(alerts.count(), 1)
