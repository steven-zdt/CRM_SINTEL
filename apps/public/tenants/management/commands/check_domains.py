"""
Comando de management para verificar dominios registrados en la base de datos.
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Domain


class Command(BaseCommand):
    help = "Verifica los dominios registrados en la base de datos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            help="Verificar un dominio específico (ej: ejemplo.sintel.net.co)",
        )

    def handle(self, *args, **options):
        domain_to_check = options.get("domain")

        self.stdout.write(self.style.HTTP_INFO("=" * 80))
        self.stdout.write(self.style.HTTP_INFO("VERIFICACIÓN DE DOMINIOS REGISTRADOS"))
        self.stdout.write(self.style.HTTP_INFO("=" * 80))

        with schema_context(get_public_schema_name()):
            domains = Domain.objects.select_related("tenant").all()

            self.stdout.write(f"\nTotal de dominios registrados: {domains.count()}\n")

            if domains.exists():
                self.stdout.write(self.style.HTTP_INFO("DOMINIOS:"))
                self.stdout.write("-" * 80)
                for d in domains:
                    status = "OK:" if d.tenant.is_active else "⏸️"
                    self.stdout.write(
                        f"{status} ID: {d.id:3d} | Domain: {d.domain:30s} | "
                        f"Tenant: {d.tenant.schema_name:20s} | Primary: {d.is_primary} | "
                        f"Active: {d.tenant.is_active}"
                    )
                self.stdout.write("-" * 80)

                # Verificar dominio específico si se proporciona
                if domain_to_check:
                    domain_obj = Domain.objects.filter(domain=domain_to_check).first()
                    if domain_obj:
                        self.stdout.write(
                            self.style.SUCCESS(f"\nOK: '{domain_to_check}' está registrado:")
                        )
                        self.stdout.write(f"   - ID: {domain_obj.id}")
                        self.stdout.write(
                            f"   - Tenant: {domain_obj.tenant.schema_name} ({domain_obj.tenant.nombre})"
                        )
                        self.stdout.write(f"   - Primary: {domain_obj.is_primary}")
                        self.stdout.write(f"   - Is Active: {domain_obj.tenant.is_active}")
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"\nERROR: '{domain_to_check}' NO está registrado en la base de datos"
                            )
                        )
                        self.stdout.write(
                            self.style.WARNING("   Necesitas crear un tenant con este dominio")
                        )
            else:
                self.stdout.write(
                    self.style.WARNING("WARNING:  No hay dominios registrados en la base de datos")
                )

        self.stdout.write("\n" + "=" * 80)
