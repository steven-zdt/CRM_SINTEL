"""
Management command: garantiza Sede "Principal" + Area "General" para toda
empresa existente que aun no tenga ninguna Sede, Y que cualquier Sede ya
existente sin Area reciba su Area "General" (ver docs/ADR-003-contexto-
organizacional-sede-area.md). Un tenant nuevo ya recibe esto automaticamente
desde el onboarding (apps/services/onboarding/empresa_service.py); este
comando es el backfill de una sola vez para tenants creados antes de ese
cambio o cuya Sede se creo por otra via (ej. CRUD manual).

Idempotente por diseno: reutiliza asegurar_estructura_organizacional_inicial(),
que no hace nada si la empresa ya tiene una Sede CON Area.

[OSF Fase F4] Hallazgo real: la version anterior de este comando tenia su
PROPIO chequeo duplicado "si ya tiene una Sede, se omite" ANTES de siquiera
llamar a asegurar_estructura_organizacional_inicial() - por lo que el fix de
esa funcion (crear el Area faltante en una Sede huerfana) nunca se ejecutaba
para un tenant que ya tuviera Sede sin Area (`shelltest1`, confirmado
empiricamente). Corregido delegando el chequeo de que falta crear
completamente a la funcion idempotente, sin duplicar su logica aqui.

Uso:
    python manage.py backfill_sede_area
    python manage.py backfill_sede_area --tenants=1,2,3
    python manage.py backfill_sede_area --dry-run
"""
import traceback

from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context

Tenant = get_tenant_model()


class Command(BaseCommand):
    help = 'Backfill: crea Sede "Principal"/Area "General" para empresas sin ninguna Sede'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenants',
            type=str,
            default=None,
            help='Comma-separated tenant IDs. Defaults to all tenants.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Solo reporta que empresas carecen de Sede, sin crear nada.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if options['tenants']:
            tenant_ids = [int(t.strip()) for t in options['tenants'].split(',')]
            tenants = Tenant.objects.filter(pk__in=tenant_ids).exclude(schema_name='public')
        else:
            tenants = Tenant.objects.exclude(schema_name='public')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: no se creara ninguna Sede/Area.'))

        totales = {'ya_tenian': 0, 'creadas': 0, 'errores': 0}

        for tenant in tenants:
            self.stdout.write(f'Tenant: {tenant.schema_name} (id={tenant.pk})')
            with schema_context(tenant.schema_name):
                from apps.tenant.empresa.models import Area, Empresa, Sede

                empresa = Empresa.objects.first()
                if not empresa:
                    self.stderr.write(self.style.ERROR(f'  Tenant {tenant.schema_name} no tiene Empresa configurada.'))
                    totales['errores'] += 1
                    continue

                # Estado "correcto" es: existe una Sede (la primera por
                # nombre, que es la que asegurar_estructura_organizacional_inicial
                # usa/crea) Y esa Sede especifica tiene al menos un Area -
                # verificar sobre ESA sede puntual, no "algun Area en toda la
                # empresa" (una empresa con 2 Sedes donde solo 1 tiene Area
                # no debe reportarse como "completa").
                primera_sede = Sede.objects.filter(empresa=empresa).order_by('nombre').first()
                ya_completo = primera_sede is not None and Area.objects.filter(sede=primera_sede).exists()
                if ya_completo:
                    self.stdout.write('  Ya tiene Sede con Area, se omite.')
                    totales['ya_tenian'] += 1
                    continue

                if dry_run:
                    falta = 'Sede "Principal"/Area "General"' if primera_sede is None else 'Area "General" (Sede existente sin ninguna Area)'
                    self.stdout.write(self.style.WARNING(f'  [DRY RUN] crearia {falta}.'))
                    totales['creadas'] += 1
                    continue

                try:
                    from apps.tenant.empresa.services.business_service import (
                        asegurar_estructura_organizacional_inicial,
                    )
                    asegurar_estructura_organizacional_inicial(empresa)
                    self.stdout.write(self.style.SUCCESS('  Sede "Principal"/Area "General" garantizadas.'))
                    totales['creadas'] += 1
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f'  FALLO: {exc}'))
                    self.stderr.write(traceback.format_exc())
                    totales['errores'] += 1

        label = 'DRY RUN — pendientes de crear' if dry_run else 'creadas'
        self.stdout.write(
            self.style.SUCCESS(
                f'\nResumen: {label}={totales["creadas"]} '
                f'ya_tenian={totales["ya_tenian"]} '
                f'errores={totales["errores"]}'
            )
        )
