"""
Comando de management para corregir dominios en desarrollo.

WARNING: CRÍTICO: Este comando asegura que todos los tenants tengan dominios con puerto
en modo DEBUG=True, lo cual es necesario para que django-tenants resuelva correctamente
el tenant cuando se accede con puerto explícito (ej: http://cliente.localhost:8000/).

Problema que resuelve:
- En desarrollo, django-tenants busca el dominio SIN puerto en la BD
- Pero el navegador envía el hostname CON puerto (ej: cliente.localhost:8000)
- Si no existe el dominio con puerto, django-tenants no resuelve el tenant
- Resultado: Redirección al esquema público (/admin/login/)

Solución:
- Este comando crea automáticamente dominios con puerto para todos los tenants
- Solo se ejecuta si DEBUG=True
- Los dominios con puerto se crean como is_primary=False (alias)
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = "Crea dominios con puerto para todos los tenants en modo desarrollo (DEBUG=True)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forzar recreación de dominios con puerto incluso si ya existen",
        )
        parser.add_argument(
            "--port",
            type=str,
            default=None,
            help="Puerto específico a usar (default: APP_PORT de settings o 8000)",
        )

    def handle(self, *args, **options):
        # Verificar que estamos en modo desarrollo
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING:  Este comando solo se ejecuta en modo DEBUG=True. "
                    "En producción, los dominios no deben incluir puerto."
                )
            )
            return

        # Obtener puerto
        port = options.get("port") or getattr(settings, "APP_PORT", "8000")

        # Validar que el puerto no sea 80 o 443 (puertos estándar HTTP/HTTPS)
        if port in ("80", "443"):
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING:  Puerto {port} es un puerto estándar (HTTP/HTTPS). "
                    f"No se crearán dominios con puerto explícito."
                )
            )
            return

        force = options.get("force", False)

        self.stdout.write(
            self.style.SUCCESS(
                f"🚀 Iniciando corrección de dominios en desarrollo (puerto: {port})..."
            )
        )

        # Cambiar al esquema public para consultar Client y Domain
        public_schema = get_public_schema_name()

        with schema_context(public_schema):
            # Obtener todos los tenants (excepto public)
            tenants = Client.objects.exclude(schema_name="public")

            if not tenants.exists():
                self.stdout.write(
                    self.style.WARNING("WARNING:  No se encontraron tenants para procesar.")
                )
                return

            total_tenants = tenants.count()
            created_count = 0
            skipped_count = 0
            error_count = 0

            for tenant in tenants:
                try:
                    # Obtener el dominio principal (sin puerto)
                    primary_domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()

                    if not primary_domain:
                        self.stdout.write(
                            self.style.WARNING(
                                f'WARNING:  Tenant "{tenant.schema_name}" no tiene dominio principal. '
                                f"Saltando..."
                            )
                        )
                        skipped_count += 1
                        continue

                    domain_base = primary_domain.domain
                    domain_with_port = f"{domain_base}:{port}"

                    # Verificar si ya existe el dominio con puerto
                    existing_domain = Domain.objects.filter(
                        tenant=tenant, domain=domain_with_port
                    ).first()

                    if existing_domain and not force:
                        self.stdout.write(
                            f'  ✓ Tenant "{tenant.schema_name}": Dominio "{domain_with_port}" ya existe. '
                            f"Usa --force para recrearlo."
                        )
                        skipped_count += 1
                        continue

                    # Si existe y force=True, eliminarlo primero
                    if existing_domain and force:
                        existing_domain.delete()
                        self.stdout.write(
                            f'  🔄 Tenant "{tenant.schema_name}": Dominio "{domain_with_port}" eliminado (--force).'
                        )

                    # Crear dominio con puerto (is_primary=False, es un alias)
                    Domain.objects.create(
                        domain=domain_with_port,
                        tenant=tenant,
                        is_primary=False,  # El dominio principal sigue siendo el sin puerto
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  OK: Tenant "{tenant.schema_name}": Dominio "{domain_with_port}" creado.'
                        )
                    )
                    created_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ERROR: Error procesando tenant "{tenant.schema_name}": {e}'
                        )
                    )
                    error_count += 1

            # Resumen
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write(self.style.SUCCESS("📊 RESUMEN DE CORRECCIÓN DE DOMINIOS"))
            self.stdout.write(self.style.SUCCESS("=" * 70))
            self.stdout.write(f"  Total de tenants procesados: {total_tenants}")
            self.stdout.write(self.style.SUCCESS(f"  OK: Dominios creados: {created_count}"))
            self.stdout.write(self.style.WARNING(f"  ⏭️  Dominios omitidos: {skipped_count}"))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f"  ERROR: Errores: {error_count}"))
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "OK: Corrección de dominios completada. "
                    "Los tenants ahora deberían resolverse correctamente con puerto."
                )
            )
