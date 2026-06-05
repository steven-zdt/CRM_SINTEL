"""
Management command para migrar retenciones desde Facturas a Contabilidad (v3.7.1).

Uso:
    python manage.py migrate_retenciones                     # Ejecuta migracion
    python manage.py migrate_retenciones --dry-run           # Valida sin commitear
    python manage.py migrate_retenciones --rollback           # Elimina retenciones migradas
    python manage.py migrate_retenciones --empresa-id 1      # Para tenant especifico
"""

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Migra retenciones desde Facturas a Contabilidad (v3.7.1)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Valida sin commitear cambios',
        )
        parser.add_argument(
            '--rollback',
            action='store_true',
            help='Elimina retenciones migradas (usa notas startswith="migrate_v371_from_facturas")',
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='Migra solo para empresa especifica (por defecto: todas)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        rollback = options.get('rollback', False)
        empresa_id = options.get('empresa_id')

        if rollback:
            return self.rollback_migration(empresa_id, dry_run)

        return self.execute_migration(empresa_id, dry_run)

    def execute_migration(self, empresa_id=None, dry_run=False):
        """Ejecuta la migracion de retenciones."""
        from apps.tenant.facturas.models import Factura, ItemFactura
        from apps.tenant.contabilidad.models import Retencion

        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('FASE 4: Migracion de Retenciones Facturas a Contabilidad (v3.7.1)'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nMODO DRY-RUN: Cambios NO se persistiran\n'))

        try:
            with transaction.atomic():
                migrated_count = 0
                skipped_count = 0
                factura_ids = set()
                item_ids = set()

                qs_facturas = Factura.objects.only(
                    'id', 'uuid', 'numero_factura', 'empresa_id',
                    'retefuente', 'reteica', 'reteiva',
                )
                if empresa_id:
                    qs_facturas = qs_facturas.filter(empresa_id=empresa_id)

                self.stdout.write(f'Procesando {qs_facturas.count()} facturas...\n')

                for factura in qs_facturas.iterator(chunk_size=500):
                    tipos_retenciones = []

                    if factura.retefuente and Decimal(str(factura.retefuente)) > Decimal('0'):
                        tipos_retenciones.append({
                            'tipo': 'RETEFUENTE',
                            'monto': Decimal(str(factura.retefuente)),
                        })

                    if factura.reteica and Decimal(str(factura.reteica)) > Decimal('0'):
                        tipos_retenciones.append({
                            'tipo': 'RETEICA',
                            'monto': Decimal(str(factura.reteica)),
                        })

                    if factura.reteiva and Decimal(str(factura.reteiva)) > Decimal('0'):
                        tipos_retenciones.append({
                            'tipo': 'RETEIVA',
                            'monto': Decimal(str(factura.reteiva)),
                        })

                    for ret_data in tipos_retenciones:
                        try:
                            if not dry_run:
                                retencion = Retencion.objects.create(
                                    empresa_id=factura.empresa_id,
                                    tipo=ret_data['tipo'],
                                    porcentaje=Decimal('0'),
                                    base=Decimal('0'),
                                    monto=ret_data['monto'],
                                    documento_origen_app='facturas',
                                    documento_origen_modelo='Factura',
                                    documento_origen_id=factura.id,
                                    reversada=False,
                                    notas=f'migrate_v371_from_facturas; numero={factura.numero_factura}',
                                )
                            migrated_count += 1
                            factura_ids.add(factura.id)

                            self.stdout.write(
                                f'  OK Factura {factura.numero_factura}: {ret_data["tipo"]} = {ret_data["monto"]}'
                            )
                        except Exception as e:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ERROR en Factura {factura.id}: {str(e)[:60]}'
                                )
                            )

                qs_items = ItemFactura.objects.select_related('factura').only(
                    'id', 'empresa_id', 'factura_id', 'factura__empresa_id',
                    'porcentaje_retefuente', 'valor_retefuente',
                    'porcentaje_reteica', 'valor_reteica',
                    'porcentaje_reteiva', 'valor_reteiva',
                )
                if empresa_id:
                    qs_items = qs_items.filter(empresa_id=empresa_id)

                self.stdout.write(f'\nProcesando {qs_items.count()} items...\n')

                for item in qs_items.iterator(chunk_size=500):
                    tipos_retenciones = []

                    if item.valor_retefuente and Decimal(str(item.valor_retefuente)) > Decimal('0'):
                        tipos_retenciones.append({
                            'tipo': 'RETEFUENTE',
                            'monto': Decimal(str(item.valor_retefuente)),
                            'porcentaje': Decimal(str(item.porcentaje_retefuente or 0)),
                        })

                    if item.valor_reteica and Decimal(str(item.valor_reteica)) > Decimal('0'):
                        tipos_retenciones.append({
                            'tipo': 'RETEICA',
                            'monto': Decimal(str(item.valor_reteica)),
                            'porcentaje': Decimal(str(item.porcentaje_reteica or 0)),
                        })

                    if item.valor_reteiva and Decimal(str(item.valor_reteiva)) > Decimal('0'):
                        tipos_retenciones.append({
                            'tipo': 'RETEIVA',
                            'monto': Decimal(str(item.valor_reteiva)),
                            'porcentaje': Decimal(str(item.porcentaje_reteiva or 0)),
                        })

                    for ret_data in tipos_retenciones:
                        try:
                            if not dry_run:
                                retencion = Retencion.objects.create(
                                    empresa_id=item.empresa_id or item.factura.empresa_id,
                                    tipo=ret_data['tipo'],
                                    porcentaje=ret_data['porcentaje'],
                                    base=Decimal('0'),
                                    monto=ret_data['monto'],
                                    documento_origen_app='facturas',
                                    documento_origen_modelo='ItemFactura',
                                    documento_origen_id=item.id,
                                    reversada=False,
                                    notas=f'migrate_v371_from_facturas; item_id={item.id}',
                                )
                            migrated_count += 1
                            item_ids.add(item.id)

                            self.stdout.write(
                                f'  OK Item {item.id}: {ret_data["tipo"]} = {ret_data["monto"]}'
                            )
                        except Exception as e:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ERROR en Item {item.id}: {str(e)[:60]}'
                                )
                            )

                self.stdout.write('\n' + self.style.SUCCESS('=' * 70))
                self.stdout.write(self.style.SUCCESS('OK Migracion completada'))
                self.stdout.write(self.style.SUCCESS(f'  - Retenciones creadas: {migrated_count}'))
                self.stdout.write(self.style.SUCCESS(f'  - Saltadas por error: {skipped_count}'))
                self.stdout.write(self.style.SUCCESS(f'  - Facturas procesadas: {len(factura_ids)}'))
                self.stdout.write(self.style.SUCCESS(f'  - Items procesados: {len(item_ids)}'))

                if dry_run:
                    self.stdout.write(self.style.WARNING('\nDry-run: cambios NO persistidos. Ejecuta sin --dry-run para aplicar.'))
                    raise transaction.TransactionManagementError('Rollback de dry-run')

        except transaction.TransactionManagementError:
            if dry_run:
                self.stdout.write(self.style.SUCCESS('\nOK Validacion exitosa. Cambios reversados (dry-run).'))
            else:
                raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nERROR fatal: {str(e)}'))
            raise CommandError(f'Migracion fallida: {str(e)}')

    def rollback_migration(self, empresa_id=None, dry_run=False):
        """Revierte la migracion (elimina retenciones migradas)."""
        from apps.tenant.contabilidad.models import Retencion

        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('ROLLBACK: Eliminando retenciones migradas'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nMODO DRY-RUN: Cambios NO se persistiran\n'))

        try:
            with transaction.atomic():
                qs = Retencion.objects.filter(
                    notas__startswith='migrate_v371_from_facturas'
                )

                count = qs.count()
                self.stdout.write(f'Se van a eliminar {count} retenciones migradas...\n')

                if not dry_run:
                    for ret in qs.only('id', 'tipo', 'monto', 'documento_origen_id').iterator(chunk_size=500):
                        self.stdout.write(f'  - {ret.tipo} ${ret.monto} (doc: {ret.documento_origen_id})')
                        ret.delete()

                self.stdout.write('\n' + self.style.SUCCESS('=' * 70))
                self.stdout.write(self.style.SUCCESS(f'OK Rollback completado: {count} retenciones eliminadas'))

                if dry_run:
                    self.stdout.write(self.style.WARNING('\nDry-run: cambios NO persistidos. Ejecuta sin --dry-run para aplicar.'))
                    raise transaction.TransactionManagementError('Rollback de dry-run')

        except transaction.TransactionManagementError:
            if dry_run:
                self.stdout.write(self.style.SUCCESS('\nOK Validacion exitosa. Cambios reversados (dry-run).'))
            else:
                raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nERROR en rollback: {str(e)}'))
            raise CommandError(f'Rollback fallido: {str(e)}')
