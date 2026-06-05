"""
Crea periodos contables mensuales para un año dado.

Idempotente: usa get_or_create por (empresa, periodo). Seguro de re-ejecutar.

Uso:
    python manage.py seed_periodos_contables
    python manage.py seed_periodos_contables --year=2026
    python manage.py seed_periodos_contables --year=2025 --tenants=1,2
    python manage.py seed_periodos_contables --year=2024,2025,2026
    python manage.py seed_periodos_contables --dry-run
"""
import calendar
from datetime import date

from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model

Tenant = get_tenant_model()

MESES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


class Command(BaseCommand):
    help = 'Crear periodos contables mensuales (ABIERTO) para todos los tenants activos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=str,
            default=str(date.today().year),
            help='Año(s) separados por coma (default: año actual). Ej: --year=2025,2026',
        )
        parser.add_argument(
            '--tenants',
            type=str,
            help='IDs de tenants separados por coma (default: todos los activos)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar que se crearia sin persistir',
        )

    def handle(self, *args, **options):
        from django.db import connection

        dry_run = options.get('dry_run', False)

        # Parsear año(s)
        years = [int(y.strip()) for y in options['year'].split(',')]

        # Seleccionar tenants
        tenant_ids = None
        if options.get('tenants'):
            tenant_ids = [int(x.strip()) for x in options['tenants'].split(',')]
        tenants = (
            Tenant.objects.filter(id__in=tenant_ids)
            if tenant_ids
            else Tenant.objects.exclude(schema_name='public').filter(is_active=True)
        )

        if not tenants.exists():
            self.stdout.write(self.style.WARNING('No se encontraron tenants activos.'))
            return

        total = len(years) * 12
        self.stdout.write(self.style.SUCCESS(
            f'Periodos Contables — {tenants.count()} tenant(s) | '
            f'{len(years)} año(s): {", ".join(str(y) for y in years)} | '
            f'{total} periodos a verificar por tenant'
        ))

        for tenant in tenants:
            self.stdout.write(f'\n  Tenant: {tenant.nombre} (schema={tenant.schema_name})')

            with tenant:
                from django.apps import apps as django_apps
                try:
                    Empresa = django_apps.get_model('empresa', 'Empresa')
                    empresa = Empresa.objects.first()
                    if not empresa:
                        self.stdout.write(self.style.ERROR('    Sin Empresa configurada — omitir'))
                        continue
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'    [WARN] {exc}'))
                    continue

                try:
                    with connection.cursor() as cur:
                        cur.execute(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                            "WHERE table_name='contabilidad_periodocontable')"
                        )
                        if not cur.fetchone()[0]:
                            self.stdout.write(self.style.WARNING(
                                '    Tabla no existe — ejecutar migrate_schemas primero'))
                            continue
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'    No se pudo verificar tabla: {exc}'))
                    continue

                from apps.tenant.contabilidad.models import PeriodoContable

                creados = existentes = errores = 0

                for year in years:
                    for mes in range(1, 13):
                        periodo_str = f'{year}-{mes:02d}'
                        ultimo_dia = calendar.monthrange(year, mes)[1]
                        f_inicio = date(year, mes, 1)
                        f_fin    = date(year, mes, ultimo_dia)
                        nombre   = f'{MESES[mes - 1]} {year}'

                        try:
                            if dry_run:
                                existe = PeriodoContable.objects.filter(
                                    empresa=empresa, periodo=periodo_str
                                ).exists()
                                if existe:
                                    existentes += 1
                                    self.stdout.write(
                                        f'    [DRY-EXIST] {periodo_str}  {nombre}'
                                    )
                                else:
                                    creados += 1
                                    self.stdout.write(
                                        f'    [DRY-CREAR] {periodo_str}  {nombre}  '
                                        f'({f_inicio} → {f_fin})'
                                    )
                            else:
                                _, created = PeriodoContable.objects.get_or_create(
                                    empresa=empresa,
                                    periodo=periodo_str,
                                    defaults={
                                        'fecha_inicio': f_inicio,
                                        'fecha_fin':    f_fin,
                                        'estado':       'ABIERTO',
                                    },
                                )
                                if created:
                                    creados += 1
                                    self.stdout.write(
                                        f'    [CREADO]  {periodo_str}  {nombre}  '
                                        f'({f_inicio} → {f_fin})'
                                    )
                                else:
                                    existentes += 1
                        except Exception as exc:
                            errores += 1
                            self.stdout.write(
                                self.style.ERROR(f'    [ERROR] {periodo_str}: {exc}')
                            )

                fn  = self.style.WARNING if dry_run else self.style.SUCCESS
                msg = (
                    f'    [DRY-RUN] Crearia {creados} | Ya existen {existentes} | Errores {errores}'
                    if dry_run else
                    f'    [OK] Creados: {creados} | Ya existian: {existentes} | Errores: {errores}'
                )
                self.stdout.write(fn(msg))

        self.stdout.write(self.style.SUCCESS('\n[DONE] Periodos contables completado.'))
