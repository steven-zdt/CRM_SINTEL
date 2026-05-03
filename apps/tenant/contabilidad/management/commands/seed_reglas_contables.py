"""
Management command to seed accounting configuration (ReglaContable and TarifaImpuesto)
for all tenants.

Usage:
    python manage.py seed_reglas_contables
    python manage.py seed_reglas_contables --tenants=1,2,3
    python manage.py seed_reglas_contables --dry-run

v3.0: Fase 0 (Preparación) — Initializes centralized accounting configuration
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model

from apps.tenant.contabilidad.models import ReglaContable, TarifaImpuesto

Tenant = get_tenant_model()

# ============================================================================
# REGLAS CONTABLES (Transaction Type + Economic Concept → PUC Account)
# ============================================================================

REGLAS_DEFECTO = [
    # VENTAS (VENTA_FACTURA)
    {
        'tipo_transaccion': 'VENTA_FACTURA',
        'concepto': 'INGRESO_PRINCIPAL',
        'cuenta_codigo': '413501',
        'descripcion': 'Ingresos por venta de productos/servicios'
    },
    {
        'tipo_transaccion': 'VENTA_FACTURA',
        'concepto': 'IVA_GENERADO',
        'cuenta_codigo': '240801',
        'descripcion': 'IVA generado en venta (19%)'
    },
    {
        'tipo_transaccion': 'VENTA_FACTURA',
        'concepto': 'RETEFUENTE',
        'cuenta_codigo': '235515',
        'descripcion': 'Anticipos de retención en la fuente (retención cliente)'
    },
    {
        'tipo_transaccion': 'VENTA_FACTURA',
        'concepto': 'RETEICA',
        'cuenta_codigo': '235517',
        'descripcion': 'Anticipos de ReteICA (retención cliente)'
    },
    {
        'tipo_transaccion': 'VENTA_FACTURA',
        'concepto': 'RETEIVA',
        'cuenta_codigo': '235525',
        'descripcion': 'Anticipos de ReteIVA (retención cliente)'
    },
    {
        'tipo_transaccion': 'VENTA_FACTURA',
        'concepto': 'CXC',
        'cuenta_codigo': '130505',
        'descripcion': 'Clientes — Cuentas por Cobrar'
    },
    # NOTA CRÉDITO (VENTA_NOTA_CREDITO)
    {
        'tipo_transaccion': 'VENTA_NOTA_CREDITO',
        'concepto': 'DEVOLUCIONES',
        'cuenta_codigo': '417501',
        'descripcion': 'Devoluciones en ventas'
    },
    # COMPRAS (COMPRA_GASTO)
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'GASTO_SERVICIOS',
        'cuenta_codigo': '513501',
        'descripcion': 'Gastos de servicios generales'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'GASTO_ARRIENDO',
        'cuenta_codigo': '512501',
        'descripcion': 'Gastos de arriendo'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'GASTO_UTILES',
        'cuenta_codigo': '511001',
        'descripcion': 'Gastos útiles y materiales'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'IVA_DESCONTABLE',
        'cuenta_codigo': '240802',
        'descripcion': 'IVA descontable en compras'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'RETEFUENTE',
        'cuenta_codigo': '236540',
        'descripcion': 'Retención en la fuente por pagar (retenemos a proveedor)'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'RETEICA',
        'cuenta_codigo': '236805',
        'descripcion': 'Retención ICA por pagar'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'RETEIVA',
        'cuenta_codigo': '236799',
        'descripcion': 'Retención IVA por pagar'
    },
    {
        'tipo_transaccion': 'COMPRA_GASTO',
        'concepto': 'CXP',
        'cuenta_codigo': '233595',
        'descripcion': 'Costos y gastos por pagar — Proveedores nacionales'
    },
    # INVENTARIO (SALIDA_INVENTARIO_VENTA)
    {
        'tipo_transaccion': 'SALIDA_INVENTARIO_VENTA',
        'concepto': 'COSTO_VENTAS',
        'cuenta_codigo': '613501',
        'descripcion': 'Costo de ventas y prestación de servicios'
    },
    {
        'tipo_transaccion': 'SALIDA_INVENTARIO_VENTA',
        'concepto': 'INVENTARIO',
        'cuenta_codigo': '143505',
        'descripcion': 'Mercancías no fabricadas — Inventario'
    },
    # BAJA INVENTARIO
    {
        'tipo_transaccion': 'BAJA_INVENTARIO',
        'concepto': 'PERDIDA_INVENTARIO',
        'cuenta_codigo': '529901',
        'descripcion': 'Pérdida en inventarios'
    },
    # NÓMINA (NOMINA_LIQUIDACION)
    {
        'tipo_transaccion': 'NOMINA_LIQUIDACION',
        'concepto': 'SUELDO',
        'cuenta_codigo': '510506',
        'descripcion': 'Gastos de personal — Sueldos'
    },
    {
        'tipo_transaccion': 'NOMINA_LIQUIDACION',
        'concepto': 'AUXILIO_TRANSPORTE',
        'cuenta_codigo': '510527',
        'descripcion': 'Auxilio de transporte'
    },
    {
        'tipo_transaccion': 'NOMINA_LIQUIDACION',
        'concepto': 'SALUD_EMPLEADO',
        'cuenta_codigo': '237005',
        'descripcion': 'Salud empleado (aporte empleado 4%)'
    },
    {
        'tipo_transaccion': 'NOMINA_LIQUIDACION',
        'concepto': 'PENSION_EMPLEADO',
        'cuenta_codigo': '237006',
        'descripcion': 'Pensión empleado (aporte empleado 4%)'
    },
    {
        'tipo_transaccion': 'NOMINA_LIQUIDACION',
        'concepto': 'SALARIO_POR_PAGAR',
        'cuenta_codigo': '238030',
        'descripcion': 'Salarios por pagar'
    },
    # PROVISIONES NÓMINA (NOMINA_PROVISION)
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'APORTE_PATRONAL',
        'cuenta_codigo': '510568',
        'descripcion': 'Aportes patronales (salud + pensión + ARL + parafiscales)'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'SALUD_PATRONAL',
        'cuenta_codigo': '237007',
        'descripcion': 'Salud patronal (8.5% IBC) — por pagar'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'PENSION_PATRONAL',
        'cuenta_codigo': '237008',
        'descripcion': 'Pensión patronal (12% IBC) — por pagar'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'ARL',
        'cuenta_codigo': '237009',
        'descripcion': 'ARL (seguro ocupacional) — por pagar'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'CAJA_COMPENSACION',
        'cuenta_codigo': '237010',
        'descripcion': 'Caja de Compensación (4%) — por pagar'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'ICBF',
        'cuenta_codigo': '237011',
        'descripcion': 'ICBF (3%) — por pagar'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'SENA',
        'cuenta_codigo': '237012',
        'descripcion': 'SENA (2%) — por pagar'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'CESANTIAS',
        'cuenta_codigo': '251005',
        'descripcion': 'Cesantías por pagar (8.33%)'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'PRIMA_SERVICIOS',
        'cuenta_codigo': '252005',
        'descripcion': 'Prima de servicios por pagar (8.33%)'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'VACACIONES',
        'cuenta_codigo': '252510',
        'descripcion': 'Vacaciones por pagar (4.17%)'
    },
    {
        'tipo_transaccion': 'NOMINA_PROVISION',
        'concepto': 'INTERESES_CESANTIAS',
        'cuenta_codigo': '252005',
        'descripcion': 'Intereses sobre cesantías por pagar (1%)'
    },
]

# ============================================================================
# TARIFAS IMPUESTO (Tax Rates + Exoneration Rules)
# ============================================================================

TARIFAS_DEFECTO = [
    # IVA (2026 standard rates)
    {
        'tipo': 'IVA',
        'valor_porcentaje': Decimal('19.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'IVA general 19%'
    },
    {
        'tipo': 'IVA',
        'valor_porcentaje': Decimal('5.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'IVA reducido 5%'
    },
    # RETEFUENTE
    {
        'tipo': 'RETEFUENTE',
        'valor_porcentaje': Decimal('2.50'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Retefuente compras (2.5% si base ≥ 27 UVT)'
    },
    {
        'tipo': 'RETEFUENTE',
        'valor_porcentaje': Decimal('4.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Retefuente servicios (4% declarantes)'
    },
    {
        'tipo': 'RETEFUENTE',
        'valor_porcentaje': Decimal('11.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Retefuente honorarios personas naturales (11%)'
    },
    # RETEICA
    {
        'tipo': 'RETEICA',
        'valor_porcentaje': Decimal('0.69'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'ReteICA (0.69% estimado — varía por actividad y municipio)'
    },
    # RETEIVA
    {
        'tipo': 'RETEIVA',
        'valor_porcentaje': Decimal('15.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'ReteIVA (15% del IVA si base ≥ 4 UVT)'
    },
    # APORTES NÓMINA EMPLEADO
    {
        'tipo': 'SALUD_EMPLEADO',
        'valor_porcentaje': Decimal('4.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Aporte salud empleado (4% IBC)'
    },
    {
        'tipo': 'PENSION_EMPLEADO',
        'valor_porcentaje': Decimal('4.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Aporte pensión empleado (4% IBC)'
    },
    # APORTES PATRONALES
    {
        'tipo': 'SALUD_PATRONAL',
        'valor_porcentaje': Decimal('8.50'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': True,
        'base_minima_uvt': Decimal('10'),
        'descripcion': 'Aporte salud patronal (8.5%) — exonerado <10 SMMLV (art. 114-1 ET)'
    },
    {
        'tipo': 'PENSION_PATRONAL',
        'valor_porcentaje': Decimal('12.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Aporte pensión patronal (12% IBC)'
    },
    {
        'tipo': 'ARL',
        'valor_porcentaje': Decimal('0.52'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Seguro ARL (0.52% - 6.96% según nivel I-V)'
    },
    {
        'tipo': 'CAJA',
        'valor_porcentaje': Decimal('4.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': True,
        'base_minima_uvt': Decimal('10'),
        'descripcion': 'Caja de Compensación (4%) — exonerado <10 SMMLV (art. 114-1 ET)'
    },
    {
        'tipo': 'ICBF',
        'valor_porcentaje': Decimal('3.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': True,
        'base_minima_uvt': Decimal('10'),
        'descripcion': 'ICBF (3%) — exonerado <10 SMMLV (art. 114-1 ET)'
    },
    {
        'tipo': 'SENA',
        'valor_porcentaje': Decimal('2.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': True,
        'base_minima_uvt': Decimal('10'),
        'descripcion': 'SENA (2%) — exonerado <10 SMMLV (art. 114-1 ET)'
    },
    # PROVISIONES
    {
        'tipo': 'CESANTIAS',
        'valor_porcentaje': Decimal('8.33'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Provisión cesantías (8.33% anual = 0.694% mensual)'
    },
    {
        'tipo': 'INTERESES_CESANTIAS',
        'valor_porcentaje': Decimal('1.00'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Provisión intereses cesantías (1% anual)'
    },
    {
        'tipo': 'PRIMA_SERVICIOS',
        'valor_porcentaje': Decimal('8.33'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Provisión prima servicios (8.33% anual = 0.694% mensual)'
    },
    {
        'tipo': 'VACACIONES',
        'valor_porcentaje': Decimal('4.17'),
        'fecha_inicio': date(2020, 1, 1),
        'fecha_fin': None,
        'exonerado': False,
        'base_minima_uvt': Decimal('0'),
        'descripcion': 'Provisión vacaciones (4.17% anual = 15 días/año)'
    },
]


class Command(BaseCommand):
    help = 'Seed default accounting configuration (ReglaContable and TarifaImpuesto) for all tenants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenants',
            type=str,
            help='Comma-separated tenant IDs to seed (default: all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be seeded without actually doing it'
        )

    def handle(self, *args, **options):
        from django.db import connection
        from django.core.management import call_command

        dry_run = options.get('dry_run', False)
        tenant_ids = None
        if options.get('tenants'):
            tenant_ids = [int(x.strip()) for x in options['tenants'].split(',')]

        # Get tenants to seed
        if tenant_ids:
            tenants = Tenant.objects.filter(id__in=tenant_ids)
        else:
            tenants = Tenant.objects.all()

        if not tenants.exists():
            self.stdout.write(
                self.style.WARNING('No tenants found to seed')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Seeding {tenants.count()} tenant(s)...')
        )

        for tenant in tenants:
            self.stdout.write(f'\n  Processing tenant: {tenant.nombre} (ID={tenant.id})')

            with tenant:
                # Ensure all migrations are applied first
                try:
                    if not dry_run:
                        call_command('migrate', verbosity=0, interactive=False)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'    Warning: Migration failed: {e}')
                    )

                # Get the Empresa (SSoT singleton for this tenant)
                from apps.tenant.empresa.models import Empresa
                try:
                    empresa = Empresa.objects.get()
                except Empresa.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'    ✗ No Empresa found for tenant {tenant.nombre}')
                    )
                    continue
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'    ✗ Could not retrieve Empresa: {e}')
                    )
                    continue

                # Ensure tables exist by running migrations
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'contabilidad_reglacontable')"
                        )
                        tables_exist = cursor.fetchone()[0]

                    if not tables_exist:
                        self.stdout.write(f'    Creating tables for {tenant.nombre}...')
                        if not dry_run:
                            call_command('migrate', 'contabilidad', verbosity=0)
                            self.stdout.write(self.style.SUCCESS('    ✓ Tables created'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    Warning: Could not check/create tables: {e}'))

                # Seed ReglaContable
                reglas_created = 0
                for regla_dict in REGLAS_DEFECTO:
                    try:
                        regla, created = ReglaContable.objects.get_or_create(
                            tipo_transaccion=regla_dict['tipo_transaccion'],
                            concepto=regla_dict['concepto'],
                            defaults={
                                'empresa': empresa,
                                'cuenta_codigo': regla_dict['cuenta_codigo'],
                                'descripcion': regla_dict['descripcion'],
                                'activo': True,
                            }
                        )
                        if created:
                            reglas_created += 1
                            if not dry_run:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'    ✓ Created rule: {regla.tipo_transaccion} + {regla.concepto} → {regla.cuenta_codigo}'
                                    )
                                )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    Error creating rule: {e}'))

                # Seed TarifaImpuesto
                tarifas_created = 0
                for tarifa_dict in TARIFAS_DEFECTO:
                    try:
                        tarifa, created = TarifaImpuesto.objects.get_or_create(
                            tipo=tarifa_dict['tipo'],
                            valor_porcentaje=tarifa_dict['valor_porcentaje'],
                            fecha_inicio=tarifa_dict['fecha_inicio'],
                            defaults={
                                'empresa': empresa,
                                'fecha_fin': tarifa_dict['fecha_fin'],
                                'vigente': True,
                                'exonerado': tarifa_dict['exonerado'],
                                'base_minima_uvt': tarifa_dict['base_minima_uvt'],
                            }
                        )
                        if created:
                            tarifas_created += 1
                            if not dry_run:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'    ✓ Created rate: {tarifa.tipo} {tarifa.valor_porcentaje}%'
                                    )
                                )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    Error creating rate: {e}'))

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'    [DRY-RUN] Would create {reglas_created} rules + {tarifas_created} rates'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'    ✓ Created {reglas_created} rules + {tarifas_created} rates'
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS('\n✓ Seeding complete!')
        )
