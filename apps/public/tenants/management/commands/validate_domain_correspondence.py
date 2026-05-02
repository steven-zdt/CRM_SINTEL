"""
Comando de management para validar correspondencia entre dominio en BD y DataTables.

Uso:
    python manage.py validate_domain_correspondence
"""

from django.core.management.base import BaseCommand
from django.db import connection

from apps.public.tenants.api_admin.serializers import TenantListSerializer
from apps.public.tenants.models import Client


class Command(BaseCommand):
    help = "Valida que el dominio mostrado en DataTables corresponde al dominio almacenado en la BD"

    def handle(self, *args, **options):
        # Asegurar que estamos en esquema public
        connection.set_schema_to_public()

        self.stdout.write("=" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                "VALIDACIÓN: Correspondencia entre Dominio en BD y Dominio en DataTables"
            )
        )
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Obtener todos los tenants con sus dominios
        clients = Client.objects.prefetch_related("domains").all()
        serializer = TenantListSerializer()

        errors = []
        warnings = []

        for client in clients:
            self.stdout.write(f"📋 Client ID: {client.id}")
            self.stdout.write(f"   Schema: {client.schema_name}")
            self.stdout.write(f"   Nombre: {client.nombre}")

            # Obtener dominios desde BD
            domains_from_db = list(client.domains.all())
            primary_domains = [d for d in domains_from_db if d.is_primary]

            self.stdout.write(f"   Dominios en BD: {[d.domain for d in domains_from_db]}")
            if primary_domains:
                primary_domain_db = primary_domains[0].domain
                self.stdout.write(
                    self.style.SUCCESS(f"   OK: Dominio Primary en BD: {primary_domain_db}")
                )
            else:
                primary_domain_db = None
                self.stdout.write(self.style.WARNING("   WARNING:  No hay dominio primary en BD"))

            # Obtener dominio desde serializer (como lo hace DataTables)
            serialized_data = serializer.to_representation(client)
            domain_from_serializer = serialized_data[3]  # Columna 3 es el dominio

            self.stdout.write(f"   Dominio en Serializer: {domain_from_serializer}")

            # Validar correspondencia
            if primary_domain_db:
                if domain_from_serializer == primary_domain_db:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "   OK: CORRECTO: El dominio del serializer corresponde al de la BD"
                        )
                    )
                else:
                    error_msg = f"   ERROR: ERROR: El dominio del serializer ('{domain_from_serializer}') NO corresponde al primary de BD ('{primary_domain_db}')"
                    self.stdout.write(self.style.ERROR(error_msg))
                    errors.append(
                        {
                            "client_id": client.id,
                            "schema_name": client.schema_name,
                            "domain_db": primary_domain_db,
                            "domain_serializer": domain_from_serializer,
                        }
                    )
            elif domain_from_serializer == "-":
                self.stdout.write(
                    self.style.SUCCESS(
                        "   OK: CORRECTO: No hay dominio en BD y serializer retorna '-'"
                    )
                )
            else:
                warning_msg = f"   WARNING:  ADVERTENCIA: No hay dominio primary en BD pero serializer retorna '{domain_from_serializer}'"
                self.stdout.write(self.style.WARNING(warning_msg))
                warnings.append(
                    {
                        "client_id": client.id,
                        "schema_name": client.schema_name,
                        "domain_serializer": domain_from_serializer,
                    }
                )

            self.stdout.write("")

        self.stdout.write("=" * 80)
        self.stdout.write("RESUMEN")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total de tenants validados: {clients.count()}")
        self.stdout.write(f"Errores encontrados: {len(errors)}")
        self.stdout.write(f"Advertencias: {len(warnings)}")

        if errors:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("ERROR: ERRORES:"))
            for error in errors:
                self.stdout.write(
                    self.style.ERROR(
                        f"   - Client ID {error['client_id']} ({error['schema_name']}): "
                        f"BD tiene '{error['domain_db']}' pero serializer retorna '{error['domain_serializer']}'"
                    )
                )

        if warnings:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("WARNING:  ADVERTENCIAS:"))
            for warning in warnings:
                self.stdout.write(
                    self.style.WARNING(
                        f"   - Client ID {warning['client_id']} ({warning['schema_name']}): "
                        f"No hay dominio primary en BD pero serializer retorna '{warning['domain_serializer']}'"
                    )
                )

        if not errors and not warnings:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS("OK: TODOS LOS DOMINIOS CORRESPONDEN CORRECTAMENTE")
            )
        else:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("ERROR: SE ENCONTRARON DISCREPANCIAS"))
            raise SystemExit(1)
