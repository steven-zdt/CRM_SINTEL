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

from apps.tenant.contabilidad.models import ReglaContable, TarifaImpuesto, TipoComprobante

Tenant = get_tenant_model()

# ============================================================================
# COMPROBANTES CONTABLES (Plantillas de documentos)
# ============================================================================

COMPROBANTES_DEFECTO = [
    {'codigo': 'CC', 'nombre': 'Comprobante de Contabilidad', 'prefijo': 'CC'},
    {'codigo': 'RC', 'nombre': 'Recibo de Caja', 'prefijo': 'RC'},
    {'codigo': 'CE', 'nombre': 'Comprobante de Egreso', 'prefijo': 'CE'},
    {'codigo': 'FV', 'nombre': 'Factura de Venta', 'prefijo': 'FV'},
    {'codigo': 'DS', 'nombre': 'Documento Soporte', 'prefijo': 'DS'},
    {'codigo': 'NC', 'nombre': 'Nota Crédito', 'prefijo': 'NC'},
    {'codigo': 'ND', 'nombre': 'Nota Débito', 'prefijo': 'ND'},
    {'codigo': 'GN', 'nombre': 'Gasto de Nómina', 'prefijo': 'GN'},
]

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
        'concepto': 'GASTO_GENERAL',
        'cuenta_codigo': '519595',
        'descripcion': 'Otros gastos diversos (General)'
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
        'concepto': 'PASIVO_COMPRA_GASTO',
        'cuenta_codigo': '233595',
        'descripcion': 'Costos y gastos por pagar — Proveedores nacionales'
    },
    # COMPRA INVENTARIO
    {
        'tipo_transaccion': 'COMPRA_INVENTARIO',
        'concepto': 'INVENTARIO_PRODUCTO',
        'cuenta_codigo': '143505',
        'descripcion': 'Inventario de mercancías'
    },
    {
        'tipo_transaccion': 'COMPRA_INVENTARIO',
        'concepto': 'PASIVO_COMPRA_INVENTARIO',
        'cuenta_codigo': '220505',
        'descripcion': 'Proveedores nacionales (Inventario)'
    },
    # INVENTARIO (SALIDA_INVENTARIO_VENTA)
    {
        'tipo_transaccion': 'SALIDA_INVENTARIO_VENTA',
        'concepto': 'COSTO_VENTA_PRODUCTO',
        'cuenta_codigo': '613501',
        'descripcion': 'Costo de ventas y prestación de servicios'
    },
    {
        'tipo_transaccion': 'SALIDA_INVENTARIO_VENTA',
        'concepto': 'INVENTARIO_PRODUCTO',
        'cuenta_codigo': '143505',
        'descripcion': 'Mercancías no fabricadas — Inventario'
    },
    # BAJA INVENTARIO
    {
        'tipo_transaccion': 'BAJA_INVENTARIO',
        'concepto': 'GASTO_DETERIORO_INVENTARIO',
        'cuenta_codigo': '529901',
        'descripcion': 'Gasto por deterioro/pérdida de inventarios'
    },
    {
        'tipo_transaccion': 'BAJA_INVENTARIO',
        'concepto': 'GASTO_CONSUMO_INTERNO',
        'cuenta_codigo': '519595',
        'descripcion': 'Gasto por consumo interno de inventarios'
    },
    {
        'tipo_transaccion': 'BAJA_INVENTARIO',
        'concepto': 'INVENTARIO_PRODUCTO',
        'cuenta_codigo': '143505',
        'descripcion': 'Salida de inventario por baja/consumo'
    },
    # AJUSTE INVENTARIO
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'INVENTARIO_PRODUCTO',
        'cuenta_codigo': '143505',
        'descripcion': 'Entrada/Salida de inventario por ajuste'
    },
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'INGRESO_AJUSTE_INVENTARIO',
        'cuenta_codigo': '425050',
        'descripcion': 'Ingresos por ajustes de inventario (Sobrantes)'
    },
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'COSTO_VENTA_DEVOLUCION',
        'cuenta_codigo': '613501',
        'descripcion': 'Ajuste al costo por devolución'
    },
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'AJUSTE_CONTABLE',
        'cuenta_codigo': '519595',
        'descripcion': 'Ajuste contable genérico'
    },
    # NOTA CREDITO COMPRA (COMPRA_NOTA_CREDITO)
    {
        'tipo_transaccion': 'COMPRA_NOTA_CREDITO',
        'concepto': 'DEVOLUCIONES_COMPRA',
        'cuenta_codigo': '233595',
        'descripcion': 'Devoluciones en compras — ajuste cuentas por pagar'
    },
    {
        'tipo_transaccion': 'COMPRA_NOTA_CREDITO',
        'concepto': 'IVA_DESCONTABLE',
        'cuenta_codigo': '240802',
        'descripcion': 'Ajuste IVA descontable por devolucion en compra'
    },
    {
        'tipo_transaccion': 'COMPRA_NOTA_CREDITO',
        'concepto': 'RETEFUENTE',
        'cuenta_codigo': '236540',
        'descripcion': 'Ajuste retencion fuente por devolucion en compra'
    },
    {
        'tipo_transaccion': 'COMPRA_NOTA_CREDITO',
        'concepto': 'RETEICA',
        'cuenta_codigo': '236805',
        'descripcion': 'Ajuste ReteICA por devolucion en compra'
    },
    {
        'tipo_transaccion': 'COMPRA_NOTA_CREDITO',
        'concepto': 'RETEIVA',
        'cuenta_codigo': '236799',
        'descripcion': 'Ajuste ReteIVA por devolucion en compra'
    },
    {
        'tipo_transaccion': 'COMPRA_NOTA_CREDITO',
        'concepto': 'PASIVO_COMPRA_GASTO',
        'cuenta_codigo': '233595',
        'descripcion': 'Ajuste CxP proveedor por devolucion en compra'
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
        'concepto': 'OTROS_DEVENGOS',
        'cuenta_codigo': '510595',
        'descripcion': 'Otros devengos del empleado'
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
        'descripcion': 'Pension empleado (aporte empleado 4%)'
    },
    {
        'tipo_transaccion': 'NOMINA_LIQUIDACION',
        'concepto': 'PRESTAMOS_EMPLEADO',
        'cuenta_codigo': '259595',
        'descripcion': 'Prestamos y descuentos varios al empleado'
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
    # COSTO DE VENTA (INVENTARIO_COSTO_VENTA)
    {
        'tipo_transaccion': 'INVENTARIO_COSTO_VENTA',
        'concepto': 'COSTO_VENTAS',
        'cuenta_codigo': '613501',
        'descripcion': 'Costo de ventas (mercancías no fabricadas)'
    },
    {
        'tipo_transaccion': 'INVENTARIO_COSTO_VENTA',
        'concepto': 'INVENTARIO_MERCANCIAS',
        'cuenta_codigo': '143505',
        'descripcion': 'Mercancías no fabricadas (salida)'
    },
    # AJUSTE INVENTARIO (AJUSTE_INVENTARIO)
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'GASTO_BAJA_INVENTARIO',
        'cuenta_codigo': '529901',
        'descripcion': 'Gasto por deterioro/pérdida de inventarios'
    },
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'AJUSTE_INVENTARIO_INGRESO',
        'cuenta_codigo': '425050',
        'descripcion': 'Ingresos por ajustes de inventario (Sobrantes)'
    },
    {
        'tipo_transaccion': 'AJUSTE_INVENTARIO',
        'concepto': 'INVENTARIO_MERCANCIAS',
        'cuenta_codigo': '143505',
        'descripcion': 'Mercancías no fabricadas (ajuste)'
    },
    # PAGO NÓMINA (NOMINA_PAGO)
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_SUELDOS',
        'cuenta_codigo': '510506',
        'descripcion': 'Gastos de personal — Sueldos'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_AUXILIO_TRANSPORTE',
        'cuenta_codigo': '510527',
        'descripcion': 'Auxilio de transporte'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_OTROS_DEVENGOS',
        'cuenta_codigo': '510595',
        'descripcion': 'Otros devengos del empleado'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_APORTE_SALUD',
        'cuenta_codigo': '237005',
        'descripcion': 'Salud empleado (aporte empleado 4%)'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_APORTE_PENSION',
        'cuenta_codigo': '237006',
        'descripcion': 'Pension empleado (aporte empleado 4%)'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_PRESTAMOS',
        'cuenta_codigo': '136595',
        'descripcion': 'Recuperación de préstamos a empleados'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'NOMINA_DESCUENTOS',
        'cuenta_codigo': '237095',
        'descripcion': 'Descuentos varios de nómina'
    },
    {
        'tipo_transaccion': 'NOMINA_PAGO',
        'concepto': 'PASIVO_NOMINA_POR_PAGAR',
        'cuenta_codigo': '238030',
        'descripcion': 'Obligaciones laborales por pagar'
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
                # Get the Empresa (SSoT singleton for this tenant)
                from django.apps import apps
                try:
                    Empresa = apps.get_model('empresa', 'Empresa')
                    empresa = Empresa.objects.first()
                    if not empresa:
                         self.stdout.write(self.style.ERROR(f'    [ERROR] No Empresa found for tenant {tenant.nombre}'))
                         continue
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'    [WARNING] Could not retrieve Empresa: {e}')
                    )
                    continue

                # Ensure tables exist (Basic check)
                try:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'contabilidad_reglacontable')"
                        )
                        if not cursor.fetchone()[0]:
                            self.stdout.write(self.style.WARNING('    [WARNING] Accounting tables not found. Run migrate_schemas first.'))
                            continue
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    Warning: Could not check tables: {e}'))

                # Seed TipoComprobante v3.6
                # WARNING: BUGFIX: get_or_create() ejecutaba el INSERT real sin
                # importar --dry-run (el flag solo suprimia el mensaje de exito)
                # -- confirmado en vivo: una corrida "--dry-run" contra el tenant
                # home escribio 62 ReglaContable + 19 TarifaImpuesto reales
                # (auditoria CONT-19, 2026-08-26). En dry_run solo se verifica
                # existencia (.exists()), nunca se llama get_or_create().
                comprobantes_created = 0
                for comp_dict in COMPROBANTES_DEFECTO:
                    try:
                        if dry_run:
                            if not TipoComprobante.objects.filter(empresa=empresa, codigo=comp_dict['codigo']).exists():
                                comprobantes_created += 1
                            continue
                        comp, created = TipoComprobante.objects.get_or_create(
                            empresa=empresa,
                            codigo=comp_dict['codigo'],
                            defaults={
                                'nombre': comp_dict['nombre'],
                                'prefijo': comp_dict['prefijo'],
                                'consecutivo_actual': 1,
                                'activa': True,
                            }
                        )
                        if created:
                            comprobantes_created += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'    [OK] Created voucher type: {comp.codigo} ({comp.nombre})'
                                )
                            )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    Error creating voucher type: {e}'))

                # Seed ReglaContable
                reglas_created = 0
                for regla_dict in REGLAS_DEFECTO:
                    try:
                        if dry_run:
                            if not ReglaContable.objects.filter(
                                tipo_transaccion=regla_dict['tipo_transaccion'], concepto=regla_dict['concepto']
                            ).exists():
                                reglas_created += 1
                            continue
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
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'    [OK] Created rule: {regla.tipo_transaccion} + {regla.concepto} → {regla.cuenta_codigo}'
                                )
                            )
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    Error creating rule: {e}'))

                # Seed TarifaImpuesto
                tarifas_created = 0
                for tarifa_dict in TARIFAS_DEFECTO:
                    try:
                        if dry_run:
                            if not TarifaImpuesto.objects.filter(
                                tipo=tarifa_dict['tipo'],
                                valor_porcentaje=tarifa_dict['valor_porcentaje'],
                                fecha_inicio=tarifa_dict['fecha_inicio'],
                            ).exists():
                                tarifas_created += 1
                            continue
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
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'    [OK] Created rate: {tarifa.tipo} {tarifa.valor_porcentaje}%'
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
                            f'    [SUCCESS] Created {reglas_created} rules + {tarifas_created} rates'
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS('\n[SUCCESS] Seeding complete!')
        )
