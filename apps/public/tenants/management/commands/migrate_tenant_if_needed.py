"""
Comando para aplicar migraciones (TENANT_APPS) a un tenant específico o a todos.

WARNING: v2.30: Comando operativo para garantizar migraciones de tenants.
Útil en post-deploy, soporte y CI/CD.

Uso:
    # Migrar un tenant específico
    python manage.py migrate_tenant_if_needed --schema=tenant_abc

    # Migrar todos los tenants
    python manage.py migrate_tenant_if_needed --all-tenants
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.public.tenants.models import Client


class Command(BaseCommand):
    help = (
        "Aplica migraciones (TENANT_APPS) a un tenant específico o a todos, de forma idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--schema", type=str, help="Nombre del schema del tenant.")
        parser.add_argument("--all-tenants", action="store_true", help="Migrar todos los tenants.")

    def handle(self, *args, **options):
        schema = options.get("schema")
        all_tenants = options.get("all_tenants")

        if not schema and not all_tenants:
            raise CommandError("Especifique --schema=<name> o --all-tenants")

        if all_tenants:
            self.stdout.write("🔄 Aplicando migraciones a todos los tenants...")
            try:
                call_command("migrate_schemas", "--tenant", "--fake-initial", verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS("OK: Migraciones aplicadas a todos los tenants.")
                )
            except Exception as e:
                raise CommandError(f"Error aplicando migraciones a todos los tenants: {e}")
        else:
            # Validar que el schema existe
            public_schema = get_public_schema_name()
            current_schema = connection.schema_name

            try:
                # Cambiar al esquema public para consultar Client
                connection.set_schema_to_public()
                client = Client.objects.filter(schema_name=schema).first()

                if not client:
                    raise CommandError(
                        f"ERROR: No se encontró un tenant con schema '{schema}'. "
                        f"Verifica que el tenant exista en la tabla public.tenants_client."
                    )

                self.stdout.write(f"🔄 Aplicando migraciones al tenant '{schema}'...")
                call_command("migrate_schemas", "--schema", schema, "--fake-initial", verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS(f"OK: Migraciones aplicadas al tenant '{schema}'.")
                )

            except Exception as e:
                raise CommandError(f"Error aplicando migraciones al tenant '{schema}': {e}")

            finally:
                # Restaurar el esquema original
                if current_schema and current_schema != public_schema:
                    connection.set_schema(current_schema)
                else:
                    connection.set_schema_to_public()
