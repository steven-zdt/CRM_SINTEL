"""
Management command para poblar CatalogoMaestroNIIF con datos del catálogo oficial.

WARNING: v2.61: Carga inicial del catálogo maestro NIIF Colombia
WARNING: Uso: python manage.py poblar_catalogo_niif
WARNING: Idempotente: No duplica registros si ya existen
"""
from django.core.management.base import BaseCommand

from apps.tenant.contabilidad.choices.choices import CATALOGO_NIIF_COLOMBIA
from apps.tenant.contabilidad.models import CatalogoMaestroNIIF


class Command(BaseCommand):
    help = 'Pobla el catálogo maestro NIIF con datos del archivo choices.py'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la recreación del catálogo (elimina y recrea)',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)

        if force:
            self.stdout.write(self.style.WARNING('WARNING: Modo FORCE: Eliminando catálogo existente...'))
            deleted_count = CatalogoMaestroNIIF.objects.all().delete()[0]
            self.stdout.write(self.style.SUCCESS(f'OK: {deleted_count} registros eliminados'))

        self.stdout.write(self.style.MIGRATE_HEADING('INFO: Poblando catálogo maestro NIIF...'))
        
        created_count = 0
        skipped_count = 0
        error_count = 0

        for codigo, nombre, nivel, naturaleza in CATALOGO_NIIF_COLOMBIA:
            try:
                cuenta, created = CatalogoMaestroNIIF.objects.get_or_create(codigo=codigo)
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'OK: Creada: {codigo} - {nombre} (Nivel {nivel}, {naturaleza})')
                    )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⏭️  Ya existe: {codigo} - {nombre}')
                    )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'ERROR: Error en {codigo}: {str(e)}')
                )

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('📊 Resumen:'))
        self.stdout.write(self.style.SUCCESS(f'  OK: Creadas: {created_count}'))
        self.stdout.write(self.style.WARNING(f'  ⏭️  Omitidas: {skipped_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  ERROR: Errores: {error_count}'))
        
        total = CatalogoMaestroNIIF.objects.count()
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'🎉 Total de cuentas en catálogo: {total}')
        )
