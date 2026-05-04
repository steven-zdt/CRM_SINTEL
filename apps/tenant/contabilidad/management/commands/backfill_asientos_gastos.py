"""
Management command to retroactively materialize AsientoContable for existing Gastos.

Since Fase 1 integration was just implemented, many Gastos created during MVP
don't have corresponding AsientoContable entries. This command finds those orphans
and materializes them via the Contabilizador.

Usage:
    python manage.py backfill_asientos_gastos [--empresa-id 1]
    python manage.py backfill_asientos_gastos --dry-run  # Preview only, no changes

Warning:
    Only processes Gastos whose DocumentoSoporte is activo=True, anulado=False.
    Skips Gastos that already have an AsientoContable (idempotent).
    Handles errors gracefully (logs, continues to next).
"""

import logging

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef

from apps.tenant.contabilidad.integracion.excepciones import (
    AsientoYaExisteError,
    ContabilidadError,
)
from apps.tenant.contabilidad.models import AsientoContable
from apps.tenant.empresa.models import Empresa
from apps.tenant.gastos.models import Gasto
from apps.tenant.contabilidad.services.asientos_service import (
    materializar_asiento_desde_gasto,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Retroactively materialize AsientoContable for existing Gastos (Fase 1 backfill)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=None,
            help='Limit backfill to a specific empresa. If omitted, processes all tenants.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview only; do not create AsientoContable.'
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        dry_run = options.get('dry_run')

        # Filter Empresas
        if empresa_id:
            empresas = Empresa.objects.filter(id=empresa_id)
            if not empresas.exists():
                self.stdout.write(
                    self.style.ERROR(f"Empresa {empresa_id} not found")
                )
                return
        else:
            empresas = Empresa.objects.all()

        self.stdout.write(
            f"Starting backfill for {empresas.count()} empresa(s)... (dry_run={dry_run})"
        )

        stats = {
            'total_gastos': 0,
            'already_have_asiento': 0,
            'skipped_inactivos': 0,
            'materialized': 0,
            'failed': 0,
            'errors': [],
        }

        for empresa in empresas:
            self.stdout.write(f"\n--- Empresa {empresa.id} ({empresa.nombre}) ---")

            # Find Gastos without AsientoContable
            gastos_orfanos = Gasto.objects.filter(
                empresa_id=empresa.id,
                documento_soporte__activo=True,
                documento_soporte__anulado=False,
            ).exclude(
                Exists(
                    AsientoContable.objects.filter(
                        empresa_id=empresa.id,
                        documento_origen_app='tenant_gastos',
                        documento_origen_modelo='DocumentoSoporte',
                        documento_origen_id=OuterRef('documento_soporte_id'),
                        documento_origen_reversado=False,
                    )
                )
            )

            stats['total_gastos'] += gastos_orfanos.count()
            self.stdout.write(f"Found {gastos_orfanos.count()} orphan Gastos")

            for gasto in gastos_orfanos:
                try:
                    if dry_run:
                        self.stdout.write(
                            f"  [DRY-RUN] Would materialize Gasto {gasto.documento_soporte.numero_documento}"
                        )
                    else:
                        asiento = materializar_asiento_desde_gasto(gasto)
                        stats['materialized'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Materialized: {gasto.documento_soporte.numero_documento} → Asiento {asiento.numero}"
                            )
                        )
                except AsientoYaExisteError:
                    # Race condition: another process created it simultaneously
                    stats['already_have_asiento'] += 1
                    self.stdout.write(
                        f"  ⊘ Already exists: {gasto.documento_soporte.numero_documento}"
                    )
                except ContabilidadError as e:
                    stats['failed'] += 1
                    stats['errors'].append(
                        {
                            'gasto': gasto.documento_soporte.numero_documento,
                            'error': f"{type(e).__name__}: {str(e)}"
                        }
                    )
                    logger.error(
                        f"Failed to materialize Gasto {gasto.documento_soporte.numero_documento}: {str(e)}"
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ✗ Failed: {gasto.documento_soporte.numero_documento} — {type(e).__name__}"
                        )
                    )
                except Exception as e:
                    stats['failed'] += 1
                    stats['errors'].append(
                        {
                            'gasto': gasto.documento_soporte.numero_documento,
                            'error': f"Unexpected: {str(e)}"
                        }
                    )
                    logger.exception(
                        f"Unexpected error materializing Gasto {gasto.documento_soporte.numero_documento}"
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ UNEXPECTED ERROR: {gasto.documento_soporte.numero_documento}"
                        )
                    )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("BACKFILL SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total Gastos scanned:          {stats['total_gastos']}")
        self.stdout.write(f"Already have AsientoContable:  {stats['already_have_asiento']}")
        self.stdout.write(f"Skipped (inactive/cancelled):  {stats['skipped_inactivos']}")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully materialized:     {stats['materialized']}")
        )
        self.stdout.write(
            self.style.ERROR(f"Failed:                        {stats['failed']}")
        )

        if stats['errors']:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("ERRORS")
            self.stdout.write("=" * 60)
            for err in stats['errors']:
                self.stdout.write(f"  • {err['gasto']}: {err['error']}")

        if stats['failed'] > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"\n⚠ {stats['failed']} Gastos failed. Review logs for details."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✓ Backfill complete!")
            )
