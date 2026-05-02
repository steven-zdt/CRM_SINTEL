"""
Management command para mostrar el estado del SaaS Maestro.

Muestra conteo de usuarios globales y tenants registrados para confirmar
que el sistema está listo para recibir el primer cliente real.

Uso:
    python manage.py status_public
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.public.tenants.models import Client, Domain, TenantMembership

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Muestra el estado del SaaS Maestro (usuarios globales y tenants registrados)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== ESTADO DEL SAAS MAESTRO SINTEL ==="))

        try:
            # Conteo de usuarios globales
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            staff_users = User.objects.filter(is_staff=True).count()
            superusers = User.objects.filter(is_superuser=True).count()

            self.stdout.write("\n[USUARIOS GLOBALES]")
            self.stdout.write(f"  Total usuarios: {total_users}")
            self.stdout.write(f"  Usuarios activos: {active_users}")
            self.stdout.write(f"  Staff: {staff_users}")
            self.stdout.write(f"  Superusuarios: {superusers}")

            # Conteo de tenants
            total_tenants = Client.objects.count()
            active_tenants = Client.objects.filter(is_active=True).count()
            trial_tenants = Client.objects.filter(on_trial=True).count()
            paid_tenants = Client.objects.filter(on_trial=False).count()

            self.stdout.write("\n[TENANTS REGISTRADOS]")
            self.stdout.write(f"  Total tenants: {total_tenants}")
            self.stdout.write(f"  Tenants activos: {active_tenants}")
            self.stdout.write(f"  En periodo de prueba: {trial_tenants}")
            self.stdout.write(f"  Pagados: {paid_tenants}")

            # Conteo de dominios
            total_domains = Domain.objects.count()
            primary_domains = Domain.objects.filter(is_primary=True).count()

            self.stdout.write("\n[DOMINIOS CONFIGURADOS]")
            self.stdout.write(f"  Total dominios: {total_domains}")
            self.stdout.write(f"  Dominios primarios: {primary_domains}")

            # Conteo de membresías
            total_memberships = TenantMembership.objects.count()
            active_memberships = TenantMembership.objects.filter(is_active=True).count()
            admin_memberships = TenantMembership.objects.filter(rol="ADMIN").count()
            primary_admins = TenantMembership.objects.filter(is_primary_admin=True).count()

            self.stdout.write("\n[MEMBRESIAS DE TENANT]")
            self.stdout.write(f"  Total membresías: {total_memberships}")
            self.stdout.write(f"  Membresías activas: {active_memberships}")
            self.stdout.write(f"  Administradores: {admin_memberships}")
            self.stdout.write(f"  Administradores primarios: {primary_admins}")

            # Verificar tenant público
            public_tenant = Client.objects.filter(schema_name="public").first()
            if public_tenant:
                public_domain = Domain.objects.filter(tenant=public_tenant, is_primary=True).first()
                self.stdout.write("\n[TENANT PUBLICO]")
                self.stdout.write(f"  Schema: {public_tenant.schema_name}")
                self.stdout.write(f"  Nombre: {public_tenant.nombre}")
                self.stdout.write(
                    f"  Dominio primario: {public_domain.domain if public_domain else 'No configurado'}"
                )
                self.stdout.write(
                    f"  Estado: {'Activo' if public_tenant.is_active else 'Inactivo'}"
                )
            else:
                self.stdout.write("\n[TENANT PUBLICO]")
                self.stdout.write(self.style.WARNING("  ADVERTENCIA: Tenant público no encontrado"))
                self.stdout.write("  Ejecute: python manage.py create_public_tenant")

            # Estado general
            self.stdout.write("\n[ESTADO GENERAL]")
            if public_tenant and total_tenants > 0:
                self.stdout.write(
                    self.style.SUCCESS("  SISTEMA LISTO para recibir el primer cliente real")
                )
            elif not public_tenant:
                self.stdout.write(self.style.WARNING("  SISTEMA NO LISTO: Falta tenant público"))
            else:
                self.stdout.write(
                    self.style.WARNING("  SISTEMA PARCIALMENTE LISTO: Sin tenants de cliente")
                )

            self.stdout.write("\n=== FIN DEL REPORTE ===")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error obteniendo estado del sistema: {str(e)}"))
            logger.error(f"Error en status_public: {e}", exc_info=True)
