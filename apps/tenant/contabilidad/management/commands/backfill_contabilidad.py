"""
Management command to backfill accounting journal entries from all source apps.

Orchestrates all extractors (Gastos, Facturas, Inventario, Nomina) for one or all tenants.
Safe to re-run: idempotent by design (skips already-journalized documents).

Usage:
    python manage.py backfill_contabilidad
    python manage.py backfill_contabilidad --tenants=1,2,3
    python manage.py backfill_contabilidad --extractores=gastos,facturas
    python manage.py backfill_contabilidad --dry-run
"""
import traceback

from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context

from apps.tenant.contabilidad.integracion.extractores import (
    ExtractorGastos,
    ExtractorFacturas,
    ExtractorInventario,
    ExtractorNomina,
)

Tenant = get_tenant_model()

EXTRACTORES_DISPONIBLES = {
    'gastos': ExtractorGastos,
    'facturas': ExtractorFacturas,
    'inventario': ExtractorInventario,
    'nomina': ExtractorNomina,
}


class Command(BaseCommand):
    help = 'Backfill contabilidad: genera asientos desde Gastos, Facturas, Inventario y Nomina'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenants',
            type=str,
            default=None,
            help='Comma-separated tenant IDs. Defaults to all tenants.',
        )
        parser.add_argument(
            '--extractores',
            type=str,
            default=None,
            help=f'Comma-separated extractor names: {", ".join(EXTRACTORES_DISPONIBLES)}. Defaults to all.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Preview counts without persisting entries.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if options['tenants']:
            tenant_ids = [int(t.strip()) for t in options['tenants'].split(',')]
            tenants = Tenant.objects.filter(pk__in=tenant_ids).exclude(schema_name='public')
        else:
            tenants = Tenant.objects.exclude(schema_name='public')

        if options['extractores']:
            nombres = [n.strip() for n in options['extractores'].split(',')]
            extractores_seleccionados = {
                k: v for k, v in EXTRACTORES_DISPONIBLES.items() if k in nombres
            }
            if not extractores_seleccionados:
                self.stderr.write(f'Extractores invalidos. Disponibles: {", ".join(EXTRACTORES_DISPONIBLES)}')
                return
        else:
            extractores_seleccionados = EXTRACTORES_DISPONIBLES

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: no se persistiran asientos.'))

        totales = {'contabilizados': 0, 'omitidos': 0, 'errores': 0}

        for tenant in tenants:
            self.stdout.write(f'\nTenant: {tenant.schema_name} (id={tenant.pk})')
            with schema_context(tenant.schema_name):
                # [ARCHITECTURE] Obtener la empresa del tenant (SSoT)
                from apps.tenant.empresa.models import Empresa
                empresa = Empresa.objects.first()
                if not empresa:
                    self.stderr.write(self.style.ERROR(f'  Tenant {tenant.schema_name} no tiene Empresa configurada.'))
                    continue
                
                empresa_id = empresa.id
                for nombre, ClaseExtractor in extractores_seleccionados.items():
                    self.stdout.write(f'  [{nombre}] extrayendo pendientes...')
                    try:
                        extractor = ClaseExtractor(empresa_id)
                        pendientes = extractor.extraer_pendientes()
                        self.stdout.write(f'  [{nombre}] {len(pendientes)} pendientes encontrados')

                        if dry_run:
                            totales['contabilizados'] += len(pendientes)
                            continue

                        resultado = extractor.contabilizar_pendientes()
                        totales['contabilizados'] += resultado['contabilizados']
                        totales['omitidos'] += resultado['omitidos']
                        totales['errores'] += len(resultado['errores'])

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [{nombre}] contabilizados={resultado["contabilizados"]} '
                                f'omitidos={resultado["omitidos"]} '
                                f'errores={len(resultado["errores"])}'
                            )
                        )

                        for err in resultado['errores']:
                            self.stderr.write(f'    ERROR {err["ref"]}: {err["error"]}')

                    except Exception as exc:
                        self.stderr.write(
                            self.style.ERROR(f'  [{nombre}] FALLO: {exc}')
                        )
                        self.stderr.write(traceback.format_exc())

        label = 'DRY RUN — pendientes' if dry_run else 'contabilizados'
        self.stdout.write(
            self.style.SUCCESS(
                f'\nResumen: {label}={totales["contabilizados"]} '
                f'omitidos={totales["omitidos"]} '
                f'errores={totales["errores"]}'
            )
        )
