"""
Comando para corregir todos los tenants existentes agregando el dominio con puerto.

Este comando es útil cuando se actualiza el sistema y los tenants existentes
no tienen el dominio con puerto necesario para desarrollo.
"""
from django.core.management.base import BaseCommand
from apps.public.tenants.models import Client, Domain
from django.conf import settings


class Command(BaseCommand):
    help = 'Agrega dominio con puerto a todos los tenants existentes (solo en desarrollo)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=str,
            default=None,
            help='Puerto a agregar (default: usa APP_PORT de settings)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización incluso si el dominio ya existe'
        )

    def handle(self, *args, **options):
        port = options.get('port') or getattr(settings, 'APP_PORT', '8000')
        force = options.get('force', False)
        
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  Este comando solo debe ejecutarse en desarrollo (DEBUG=True)'
                )
            )
            return
        
        self.stdout.write("=" * 80)
        self.stdout.write("🔧 CORRIGIENDO DOMINIOS DE TENANTS (AGREGANDO PUERTO)")
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        # Obtener todos los tenants (excepto public)
        tenants = Client.objects.exclude(schema_name='public')
        
        if not tenants.exists():
            self.stdout.write(self.style.WARNING("⚠️  No se encontraron tenants privados"))
            return
        
        self.stdout.write(f"📋 Procesando {tenants.count()} tenant(s)...")
        self.stdout.write("")
        
        fixed_count = 0
        skipped_count = 0
        error_count = 0
        
        for tenant in tenants:
            self.stdout.write(f"🔍 Tenant: {tenant.nombre} (schema: {tenant.schema_name})")
            
            # Obtener dominio principal
            primary_domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
            
            if not primary_domain:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ No tiene dominio principal")
                )
                error_count += 1
                continue
            
            domain_name = primary_domain.domain
            domain_with_port = f"{domain_name}:{port}"
            
            # Verificar si ya existe
            existing = Domain.objects.filter(domain=domain_with_port).first()
            
            if existing:
                if existing.tenant == tenant:
                    if force:
                        # Actualizar si se fuerza
                        existing.is_primary = False
                        existing.save()
                        self.stdout.write(
                            self.style.SUCCESS(f"   ✅ Dominio '{domain_with_port}' actualizado")
                        )
                        fixed_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"   ℹ️  Dominio '{domain_with_port}' ya existe (omitiendo)")
                        )
                        skipped_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"   ❌ Dominio '{domain_with_port}' existe pero pertenece a otro tenant"
                        )
                    )
                    error_count += 1
            else:
                # Crear dominio con puerto
                try:
                    Domain.objects.create(
                        domain=domain_with_port,
                        tenant=tenant,
                        is_primary=False
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"   ✅ Dominio '{domain_with_port}' creado")
                    )
                    fixed_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ Error al crear dominio: {e}")
                    )
                    error_count += 1
            
            self.stdout.write("")
        
        # Resumen
        self.stdout.write("=" * 80)
        self.stdout.write("📊 RESUMEN")
        self.stdout.write("=" * 80)
        self.stdout.write(f"✅ Dominios corregidos: {fixed_count}")
        self.stdout.write(f"⏭️  Omitidos (ya existían): {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Errores: {error_count}"))
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"🎉 {fixed_count} tenant(s) corregido(s). Ahora puedes acceder con puerto."
                )
            )
