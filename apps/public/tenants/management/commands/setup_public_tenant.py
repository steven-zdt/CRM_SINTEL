"""
Comando de management para inicializar el tenant público.

Este comando:
1. Ejecuta las migraciones del esquema public (shared)
2. Crea el tenant 'public' si no existe
3. Crea el dominio 'localhost' asociado al tenant público
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_exists

from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = "Inicializa el esquema público y crea el tenant público con dominio localhost"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            default="localhost",
            help="Dominio para el tenant público (default: localhost)",
        )
        parser.add_argument(
            "--skip-migrations",
            action="store_true",
            help="Omitir ejecución de migraciones (solo crear tenant)",
        )

    def handle(self, *args, **options):
        domain_name = options["domain"]
        skip_migrations = options["skip_migrations"]

        self.stdout.write(self.style.SUCCESS("🚀 Iniciando configuración del tenant público..."))

        # 1. Ejecutar migraciones del esquema public (shared)
        if not skip_migrations:
            self.stdout.write("📦 Ejecutando migraciones del esquema public...")
            from django.core.management import call_command

            try:
                call_command("migrate_schemas", "--shared", verbosity=1)
                self.stdout.write(
                    self.style.SUCCESS("OK: Migraciones del esquema public completadas")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR: Error en migraciones: {e}"))
                return
        else:
            self.stdout.write(self.style.WARNING("⏭️  Omitiendo migraciones (--skip-migrations)"))

        # 2. Verificar que el esquema public existe
        if not schema_exists("public"):
            self.stdout.write(
                self.style.ERROR("ERROR: El esquema public no existe. Ejecuta migraciones primero.")
            )
            return

        # 3. Crear o verificar el tenant público
        self.stdout.write("🔍 Verificando tenant público...")
        try:
            # Las apps en SHARED_APPS están automáticamente en el esquema public
            # No necesitamos cambiar el tenant explícitamente
            # Simplemente trabajamos directamente con los modelos

            tenant, created = Client.objects.get_or_create(
                schema_name="public",
                defaults={
                    "nombre": "SINTEL Global",
                    "on_trial": False,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"OK: Tenant público creado: {tenant.nombre}"))
            else:
                self.stdout.write(
                    self.style.WARNING(f"INFO:  Tenant público ya existe: {tenant.nombre}")
                )

            # 3.5. Limpiar dominios no deseados (solo mantener localhost y 127.0.0.1)
            self.stdout.write("🧹 Limpiando dominios no deseados...")
            allowed_domains = ["localhost", "127.0.0.1"]
            existing_domains = Domain.objects.filter(tenant=tenant)
            deleted_count = 0
            for domain in existing_domains:
                if domain.domain not in allowed_domains:
                    domain.delete()
                    deleted_count += 1
                    self.stdout.write(self.style.WARNING(f"🗑️  Dominio eliminado: {domain.domain}"))
            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"OK: {deleted_count} dominio(s) no deseado(s) eliminado(s)")
                )

            # 4. Crear o verificar el dominio
            self.stdout.write(f"🔍 Verificando dominio: {domain_name}...")
            domain, domain_created = Domain.objects.get_or_create(
                domain=domain_name,
                defaults={
                    "tenant": tenant,
                    "is_primary": True,
                },
            )

            if domain_created:
                self.stdout.write(self.style.SUCCESS(f"OK: Dominio creado: {domain.domain}"))
            else:
                if domain.tenant != tenant:
                    domain.tenant = tenant
                    domain.is_primary = True
                    domain.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"OK: Dominio actualizado: {domain.domain}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"INFO:  Dominio ya existe: {domain.domain}")
                    )

            # 5. Crear dominio adicional mínimo: solo 127.0.0.1
            # WARNING: ESTÁNDAR: Solo creamos localhost (principal) y 127.0.0.1 (adicional)
            # No creamos dominios con puerto, sintel.localhost, ni sintel.com
            if domain_name != "127.0.0.1":
                additional_domain_obj, created = Domain.objects.get_or_create(
                    domain="127.0.0.1",
                    defaults={
                        "tenant": tenant,
                        "is_primary": False,
                    },
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS("OK: Dominio adicional creado: 127.0.0.1")
                    )
                elif additional_domain_obj.tenant != tenant:
                    # Actualizar si el dominio estaba asignado a otro tenant
                    additional_domain_obj.tenant = tenant
                    additional_domain_obj.is_primary = False
                    additional_domain_obj.save()
                    self.stdout.write(
                        self.style.SUCCESS("OK: Dominio adicional actualizado: 127.0.0.1")
                    )

            self.stdout.write(
                self.style.SUCCESS("\n🎉 Configuración del tenant público completada exitosamente!")
            )
            self.stdout.write("\n📋 Resumen:")
            self.stdout.write(f"   - Tenant: {tenant.nombre} (schema: {tenant.schema_name})")
            self.stdout.write(
                f"   - Dominios: {', '.join([d.domain for d in Domain.objects.filter(tenant=tenant)])}"
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR: Error al crear tenant público: {e}"))
            import traceback

            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return
