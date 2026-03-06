"""
Management command para prueba de humo de configuración de email.

Ejecuta un envío mínimo con fail_silently=False y registra el resultado.
Útil para aislar si el fallo es de configuración SMTP vs. lógica de negocio.

Uso:
    python manage.py test_email test@example.com
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Prueba de humo de configuración de email (envío mínimo con logging detallado)'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            type=str,
            help='Email del destinatario para la prueba'
        )
        parser.add_argument(
            '--subject',
            type=str,
            default='[TEST] Prueba de configuración de email - SINTEL',
            help='Asunto del email de prueba'
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        subject = options['subject']
        
        # Mostrar configuración actual
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('CONFIGURACIÓN DE EMAIL ACTUAL'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        email_config = {
            'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'NOT SET'),
            'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'NOT SET'),
            'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'NOT SET'),
            'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', 'NOT SET'),
            'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', 'NOT SET'),
            'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', 'NOT SET'),
            'EMAIL_HOST_PASSWORD': '***' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NOT SET',
            'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET'),
            'SERVER_EMAIL': getattr(settings, 'SERVER_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')),
            'EMAIL_TIMEOUT': getattr(settings, 'EMAIL_TIMEOUT', 'NOT SET'),
        }
        
        for key, value in email_config.items():
            self.stdout.write(f'  {key}: {value}')
        
        # Validar consistencia puerto/protocolo
        port = getattr(settings, 'EMAIL_PORT', None)
        use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        
        if port and isinstance(port, int):
            if port == 587 and not use_tls:
                self.stdout.write(self.style.WARNING(
                    '⚠️  ADVERTENCIA: Puerto 587 normalmente requiere EMAIL_USE_TLS=True'
                ))
            elif port == 465 and not use_ssl:
                self.stdout.write(self.style.WARNING(
                    '⚠️  ADVERTENCIA: Puerto 465 normalmente requiere EMAIL_USE_SSL=True'
                ))
            elif use_tls and use_ssl:
                self.stdout.write(self.style.ERROR(
                    '❌ ERROR: EMAIL_USE_TLS y EMAIL_USE_SSL no pueden estar ambos en True'
                ))
        
        self.stdout.write(self.style.WARNING('=' * 80))
        
        # Preparar mensaje de prueba
        message = f"""
Este es un email de prueba de configuración SMTP.

Configuración utilizada:
- Backend: {email_config['EMAIL_BACKEND']}
- Host: {email_config['EMAIL_HOST']}
- Port: {email_config['EMAIL_PORT']}
- TLS: {email_config['EMAIL_USE_TLS']}
- SSL: {email_config['EMAIL_USE_SSL']}
- From: {email_config['DEFAULT_FROM_EMAIL']}
- To: {recipient}

Si recibes este email, la configuración SMTP está funcionando correctamente.
"""
        
        html_message = f"""
<html>
<body>
<h2>Prueba de Configuración SMTP</h2>
<p>Este es un email de prueba de configuración SMTP.</p>
<ul>
<li><strong>Backend:</strong> {email_config['EMAIL_BACKEND']}</li>
<li><strong>Host:</strong> {email_config['EMAIL_HOST']}</li>
<li><strong>Port:</strong> {email_config['EMAIL_PORT']}</li>
<li><strong>TLS:</strong> {email_config['EMAIL_USE_TLS']}</li>
<li><strong>SSL:</strong> {email_config['EMAIL_USE_SSL']}</li>
<li><strong>From:</strong> {email_config['DEFAULT_FROM_EMAIL']}</li>
<li><strong>To:</strong> {recipient}</li>
</ul>
<p>Si recibes este email, la configuración SMTP está funcionando correctamente.</p>
</body>
</html>
"""
        
        # Intentar envío
        self.stdout.write(self.style.WARNING('\n📧 Intentando envío de email de prueba...'))
        self.stdout.write(f'  From: {email_config["DEFAULT_FROM_EMAIL"]}')
        self.stdout.write(f'  To: {recipient}')
        self.stdout.write(f'  Subject: {subject}')
        self.stdout.write(f'  Backend: {email_config["EMAIL_BACKEND"]}')
        
        try:
            # ⚠️ IMPORTANTE: fail_silently=False para capturar excepciones
            result = send_mail(
                subject=subject,
                message=message,
                from_email=email_config['DEFAULT_FROM_EMAIL'],
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,  # Forzar excepciones para diagnóstico
            )
            
            self.stdout.write(self.style.SUCCESS('\n✅ Email enviado exitosamente!'))
            self.stdout.write(f'  Resultado: {result}')
            self.stdout.write(f'  Si el backend es "console", revisa la salida del terminal.')
            self.stdout.write(f'  Si el backend es "smtp", verifica la bandeja de entrada de {recipient}')
            
            # Logging adicional
            logger.info(
                "✅ Prueba de email EXITOSA: from=%s, to=%s, subject='%s', backend=%s, host=%s, port=%s",
                email_config['DEFAULT_FROM_EMAIL'],
                recipient,
                subject,
                email_config['EMAIL_BACKEND'],
                email_config['EMAIL_HOST'],
                email_config['EMAIL_PORT']
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ ERROR enviando email: {str(e)}'))
            self.stdout.write(self.style.ERROR(f'  Tipo de error: {type(e).__name__}'))
            
            # Logging detallado del error
            logger.error(
                "❌ Prueba de email FALLIDA: from=%s, to=%s, subject='%s', backend=%s, host=%s, port=%s, error=%s",
                email_config['DEFAULT_FROM_EMAIL'],
                recipient,
                subject,
                email_config['EMAIL_BACKEND'],
                email_config['EMAIL_HOST'],
                email_config['EMAIL_PORT'],
                str(e),
                exc_info=True
            )
            
            # Sugerencias según el tipo de error
            error_str = str(e).lower()
            if 'authentication' in error_str or 'login' in error_str:
                self.stdout.write(self.style.WARNING(
                    '\n💡 SUGERENCIA: Error de autenticación. Verifica:'
                    '\n   - EMAIL_HOST_USER y EMAIL_HOST_PASSWORD'
                    '\n   - Si usas Gmail, necesitas una "App Password" (no tu contraseña normal)'
                ))
            elif 'connection' in error_str or 'timeout' in error_str:
                self.stdout.write(self.style.WARNING(
                    '\n💡 SUGERENCIA: Error de conexión. Verifica:'
                    '\n   - EMAIL_HOST y EMAIL_PORT'
                    '\n   - Firewall/red permite conexión al puerto SMTP'
                    '\n   - EMAIL_USE_TLS/EMAIL_USE_SSL según el puerto'
                ))
            elif 'ssl' in error_str or 'tls' in error_str:
                self.stdout.write(self.style.WARNING(
                    '\n💡 SUGERENCIA: Error SSL/TLS. Verifica:'
                    '\n   - EMAIL_USE_TLS=True para puerto 587'
                    '\n   - EMAIL_USE_SSL=True para puerto 465'
                    '\n   - No ambos en True simultáneamente'
                ))
            
            raise CommandError(f'Fallo en envío de email: {str(e)}')
