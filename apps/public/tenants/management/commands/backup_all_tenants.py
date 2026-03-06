"""
Comando de management para realizar backups de todos los tenants.

Este comando itera sobre todos los tenants y crea backups de cada uno.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.public.tenants.models import Client


class Command(BaseCommand):
    help = 'Realiza backups de todos los tenants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directorio donde guardar los backups (default: backups)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['plain', 'custom', 'directory', 'tar'],
            default='custom',
            help='Formato del backup (default: custom)',
        )
        parser.add_argument(
            '--skip-public',
            action='store_true',
            help='Omitir el esquema public en los backups',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        format_type = options['format']
        skip_public = options['skip_public']

        # Obtener todos los tenants
        tenants = Client.objects.all()
        total = tenants.count()

        self.stdout.write(self.style.SUCCESS(f'🔄 Iniciando backups de {total} tenants...'))

        success_count = 0
        error_count = 0

        for tenant in tenants:
            # Omitir public si se solicita
            if skip_public and tenant.schema_name == 'public':
                self.stdout.write(self.style.WARNING(f'⏭️  Omitiendo tenant public'))
                continue

            self.stdout.write(f'\n📦 Procesando: {tenant.nombre} ({tenant.schema_name})')

            try:
                call_command(
                    'backup_tenant',
                    tenant.schema_name,
                    output_dir=output_dir,
                    format=format_type,
                    verbosity=0
                )
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Backup completado: {tenant.nombre}'))
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'❌ Error en backup de {tenant.nombre}: {str(e)}'))

        # Resumen
        self.stdout.write(self.style.SUCCESS(f'\n📊 Resumen:'))
        self.stdout.write(f'   ✅ Exitosos: {success_count}')
        self.stdout.write(f'   ❌ Errores: {error_count}')
        self.stdout.write(f'   📁 Directorio: {output_dir}')
