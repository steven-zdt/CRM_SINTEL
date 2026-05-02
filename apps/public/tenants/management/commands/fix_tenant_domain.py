"""
Comando para agregar dominio con puerto si es necesario.

En desarrollo, django-tenants puede tener problemas identificando
el tenant cuando se accede con puerto. Este comando agrega el dominio
con puerto como alternativa.
"""

from django.core.management.base import BaseCommand

from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = "Agrega dominio con puerto para desarrollo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema",
            type=str,
            required=True,
            help="Schema name del tenant (ej: ejemplo, cliente)",
        )
        parser.add_argument(
            "--port", type=str, default="8000", help="Puerto a agregar (default: 8000)"
        )

    def handle(self, *args, **options):
        schema_name = options["schema"]
        port = options["port"]

        # Obtener tenant
        tenant = Client.objects.filter(schema_name=schema_name).first()
        if not tenant:
            self.stdout.write(self.style.ERROR(f"ERROR: Tenant '{schema_name}' no encontrado"))
            return

        # Obtener dominio principal
        domain_primary = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        if not domain_primary:
            self.stdout.write(
                self.style.ERROR(f"ERROR: No hay dominio principal para el tenant '{schema_name}'")
            )
            return

        domain_name = domain_primary.domain
        domain_with_port = f"{domain_name}:{port}"

        # Verificar si ya existe
        existing = Domain.objects.filter(domain=domain_with_port).first()
        if existing:
            if existing.tenant == tenant:
                self.stdout.write(
                    self.style.WARNING(
                        f"INFO:  El dominio '{domain_with_port}' ya existe y está correctamente configurado"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: El dominio '{domain_with_port}' existe pero pertenece a otro tenant"
                    )
                )
            return

        # Crear dominio con puerto
        domain_new = Domain.objects.create(domain=domain_with_port, tenant=tenant, is_primary=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: Dominio '{domain_with_port}' creado para el tenant '{schema_name}'"
            )
        )
        self.stdout.write(f"   Ahora puedes acceder a: http://{domain_with_port}/")
