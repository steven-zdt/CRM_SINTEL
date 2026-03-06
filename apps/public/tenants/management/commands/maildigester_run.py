"""
Management command para disparar la tarea de ingesta de correo manualmente.

Útil para operación local/DEV y debugging.

⚠️ En producción, la activación vendrá desde Core API o Celery Beat por tenant.
⚠️ Mantén credenciales por tenant fuera de settings.py (SSoT/Config por tenant).
"""
from django.core.management.base import BaseCommand, CommandError
from apps.services.maildigester.tasks import fetch_and_process_billing_mail
from apps.services.maildigester.schemas import MailboxConfigDTO


class Command(BaseCommand):
    help = "Dispara la tarea de ingesta de correo para un tenant específico por schema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            type=str,
            required=True,
            help="Nombre del esquema del tenant (ej: tenant_acme)"
        )
        parser.add_argument(
            "--host",
            type=str,
            required=True,
            help="Servidor de correo (ej: imap.gmail.com)"
        )
        parser.add_argument(
            "--port",
            type=int,
            default=993,
            help="Puerto del servidor (default: 993 para IMAP SSL)"
        )
        parser.add_argument(
            "--protocol",
            type=str,
            choices=["imap", "pop3"],
            default="imap",
            help="Protocolo de correo (default: imap)"
        )
        parser.add_argument(
            "--ssl",
            action="store_true",
            default=True,
            help="Usar SSL/TLS (default: True)"
        )
        parser.add_argument(
            "--no-ssl",
            dest="ssl",
            action="store_false",
            help="No usar SSL/TLS"
        )
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help="Usuario del buzón de correo"
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Contraseña del buzón de correo"
        )
        parser.add_argument(
            "--mailbox",
            type=str,
            default="INBOX",
            help="Carpeta del buzón a procesar (default: INBOX)"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Número máximo de mensajes a procesar (default: 50)"
        )
        parser.add_argument(
            "--naturaleza",
            type=str,
            choices=["VENTA", "COMPRA"],
            default="VENTA",
            help="Naturaleza de las facturas (default: VENTA)"
        )
        parser.add_argument(
            "--max-attachment-mb",
            type=int,
            default=50,
            help="Límite máximo de tamaño de adjuntos en MB (default: 50)"
        )

    def handle(self, *args, **opts):
        """
        Ejecuta el comando.
        
        Encola la tarea Celery y muestra el ID de la tarea.
        """
        schema = opts["schema"]
        
        # Construir configuración del buzón
        mailbox_config: MailboxConfigDTO = {
            "host": opts["host"],
            "port": opts["port"],
            "protocol": opts["protocol"],
            "ssl": opts["ssl"],
            "username": opts["username"],
            "password": opts["password"],
            "mailbox": opts["mailbox"],
            "max_attachment_mb": opts["max_attachment_mb"],
        }
        
        # Encolar tarea
        try:
            result = fetch_and_process_billing_mail.delay(
                tenant_schema=schema,
                mailbox_config=mailbox_config,
                limit_messages=opts["limit"],
                naturaleza=opts["naturaleza"]
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Tarea encolada exitosamente:\n"
                    f"   - Task ID: {result.id}\n"
                    f"   - Tenant: {schema}\n"
                    f"   - Buzón: {opts['host']}:{opts['port']}\n"
                    f"   - Límite: {opts['limit']} mensajes\n"
                    f"   - Naturaleza: {opts['naturaleza']}"
                )
            )
            
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Nota: La tarea se ejecutará de forma asíncrona.\n"
                    "   Para ver el resultado, consulta los logs de Celery o el estado de la tarea."
                )
            )
        
        except Exception as e:
            raise CommandError(f"Error al encolar la tarea: {e}")
