"""
Management command para crear el tenant público obligatorio.
Sin este registro, django-tenants no puede servir el esquema public.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = "Crea el tenant público obligatorio para django-tenants"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            default="localhost",
            help="Dominio para el tenant público (default: localhost)",
        )

    def handle(self, *args, **options):
        domain_name = options["domain"]

        self.stdout.write("Creando tenant público obligatorio...")

        try:
            with transaction.atomic():
                # 1. Crear o obtener el tenant público
                public_tenant, created = Client.objects.get_or_create(
                    schema_name="public",
                    defaults={
                        "nombre": "Sitio Público SINTEL",
                        "paid_until": None,
                        "on_trial": False,
                        "is_active": True,
                    },
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Tenant público creado: {public_tenant.schema_name}")
                    )
                else:
                    self.stdout.write(f"Tenant público ya existe: {public_tenant.schema_name}")

                # 2. Crear o obtener el dominio asociado
                domain, domain_created = Domain.objects.get_or_create(
                    domain=domain_name,
                    defaults={
                        "tenant": public_tenant,
                        "is_primary": True,
                    },
                )

                if domain_created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Dominio creado: {domain.domain} -> {public_tenant.schema_name}"
                        )
                    )
                else:
                    # Actualizar tenant si el dominio ya existe
                    if domain.tenant != public_tenant:
                        domain.tenant = public_tenant
                        domain.save()
                        self.stdout.write(
                            f"Dominio actualizado: {domain.domain} -> {public_tenant.schema_name}"
                        )
                    else:
                        self.stdout.write(f"Dominio ya existe: {domain.domain}")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Tenant público configurado correctamente!\n"
                        f"Schema: {public_tenant.schema_name}\n"
                        f"Dominio: {domain.domain}\n"
                        f"Estado: {'Activo' if public_tenant.is_active else 'Inactivo'}\n"
                        f"Acceso: http://{domain.domain}/"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creando tenant público: {str(e)}"))
            raise
