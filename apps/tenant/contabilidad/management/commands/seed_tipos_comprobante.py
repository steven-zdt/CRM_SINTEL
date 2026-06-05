"""
Crea los tipos de comprobante contable estándar Colombia (Decreto 2650 / NIIF PYMES).

Idempotente: usa get_or_create por (empresa, codigo). Seguro de re-ejecutar.

Uso:
    python manage.py seed_tipos_comprobante
    python manage.py seed_tipos_comprobante --tenants=1,2
    python manage.py seed_tipos_comprobante --dry-run
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model

Tenant = get_tenant_model()

# ---------------------------------------------------------------------------
# Tipos de comprobante estándar — Normativa colombiana Decreto 2650 / NIIF PYMES
# codigo : sigla del comprobante (max 10 chars, unique por empresa)
# nombre : nombre descriptivo
# prefijo: prefijo para el consecutivo (ej: FVE-00001, CE-00001)
# ---------------------------------------------------------------------------
TIPOS_COMPROBANTE = [
    # ── Facturas y Documentos de Venta ──────────────────────────────────────
    {
        'codigo': 'FVE',
        'nombre': 'Factura de Venta Electronica',
        'prefijo': 'FVE-',
        'descripcion': 'Factura electronica de venta de bienes y/o servicios (DIAN)',
    },
    {
        'codigo': 'FVC',
        'nombre': 'Factura de Venta Contado',
        'prefijo': 'FVC-',
        'descripcion': 'Factura de venta de contado (bienes y servicios)',
    },
    {
        'codigo': 'FCC',
        'nombre': 'Factura de Compra',
        'prefijo': 'FCC-',
        'descripcion': 'Factura de compra de bienes y/o servicios a proveedores',
    },
    # ── Notas ────────────────────────────────────────────────────────────────
    {
        'codigo': 'NC',
        'nombre': 'Nota Credito',
        'prefijo': 'NC-',
        'descripcion': 'Nota credito: ajuste o devolucion a favor del cliente',
    },
    {
        'codigo': 'ND',
        'nombre': 'Nota Debito',
        'prefijo': 'ND-',
        'descripcion': 'Nota debito: cargo adicional al cliente',
    },
    # ── Comprobantes de Pago y Caja ──────────────────────────────────────────
    {
        'codigo': 'CE',
        'nombre': 'Comprobante de Egreso',
        'prefijo': 'CE-',
        'descripcion': 'Soporte de pagos realizados (proveedores, gastos, nomina)',
    },
    {
        'codigo': 'RC',
        'nombre': 'Recibo de Caja',
        'prefijo': 'RC-',
        'descripcion': 'Soporte de ingresos de efectivo recibidos de clientes',
    },
    {
        'codigo': 'CC',
        'nombre': 'Comprobante de Consignacion',
        'prefijo': 'CC-',
        'descripcion': 'Soporte de consignacion bancaria',
    },
    # ── Comprobantes de Diario y Ajuste ──────────────────────────────────────
    {
        'codigo': 'CD',
        'nombre': 'Comprobante de Diario',
        'prefijo': 'CD-',
        'descripcion': 'Asiento de diario general (reclasificaciones, ajustes varios)',
    },
    {
        'codigo': 'CA',
        'nombre': 'Comprobante de Ajuste',
        'prefijo': 'CA-',
        'descripcion': 'Ajuste contable (correcciones, diferencias cambiarias)',
    },
    {
        'codigo': 'CJ',
        'nombre': 'Comprobante de Cierre',
        'prefijo': 'CJ-',
        'descripcion': 'Asiento de cierre de periodo o ejercicio contable',
    },
    # ── Nomina y Prestaciones ─────────────────────────────────────────────────
    {
        'codigo': 'CN',
        'nombre': 'Comprobante de Nomina',
        'prefijo': 'CN-',
        'descripcion': 'Liquidacion de nomina mensual (salarios, prestaciones, aportes)',
    },
    {
        'codigo': 'CP',
        'nombre': 'Comprobante de Prestaciones',
        'prefijo': 'CP-',
        'descripcion': 'Liquidacion de prestaciones sociales (cesantias, prima, vacaciones)',
    },
    # ── Inventario y Activos ──────────────────────────────────────────────────
    {
        'codigo': 'CI',
        'nombre': 'Comprobante de Inventario',
        'prefijo': 'CI-',
        'descripcion': 'Movimientos de inventario (entradas, salidas, ajustes de kardex)',
    },
    {
        'codigo': 'DA',
        'nombre': 'Comprobante de Depreciacion',
        'prefijo': 'DA-',
        'descripcion': 'Depreciacion mensual de activos fijos y amortizaciones',
    },
    # ── Documentos Soporte (Compras sin Factura) ──────────────────────────────
    {
        'codigo': 'DS',
        'nombre': 'Documento Soporte',
        'prefijo': 'DS-',
        'descripcion': 'Documento soporte en adquisiciones a no obligados a facturar (Art 771-2 ET)',
    },
    # ── Otros ─────────────────────────────────────────────────────────────────
    {
        'codigo': 'GN',
        'nombre': 'Nota General',
        'prefijo': 'GN-',
        'descripcion': 'Nota o anotacion contable de proposito general',
    },
    {
        'codigo': 'TR',
        'nombre': 'Traslado entre Cuentas',
        'prefijo': 'TR-',
        'descripcion': 'Traslado de saldos entre cuentas del mismo nivel',
    },
]


class Command(BaseCommand):
    help = 'Crear tipos de comprobante contable estandar Colombia para todos los tenants activos'

    def add_arguments(self, parser):
        parser.add_argument('--tenants', type=str,
            help='IDs de tenants separados por coma (default: todos los activos)')
        parser.add_argument('--dry-run', action='store_true',
            help='Mostrar que se crearia sin persistir')

    def handle(self, *args, **options):
        from django.db import connection

        dry_run = options.get('dry_run', False)

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

        self.stdout.write(self.style.SUCCESS(
            f'Tipos de Comprobante — {tenants.count()} tenant(s) | '
            f'{len(TIPOS_COMPROBANTE)} tipos a verificar'
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
                            "WHERE table_name='contabilidad_tipocomprobante')"
                        )
                        if not cur.fetchone()[0]:
                            self.stdout.write(self.style.WARNING(
                                '    Tabla no existe — ejecutar migrate_schemas primero'))
                            continue
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f'    No se pudo verificar tabla: {exc}'))
                    continue

                from apps.tenant.contabilidad.models import TipoComprobante

                creados = existentes = errores = 0

                for t in TIPOS_COMPROBANTE:
                    try:
                        if dry_run:
                            existe = TipoComprobante.objects.filter(
                                empresa=empresa, codigo=t['codigo']
                            ).exists()
                            if existe:
                                existentes += 1
                                self.stdout.write(
                                    f'    [EXISTE]  {t["codigo"]:6s}  {t["nombre"]}'
                                )
                            else:
                                creados += 1
                                self.stdout.write(
                                    f'    [CREAR]   {t["codigo"]:6s}  {t["nombre"]}  '
                                    f'(prefijo: {t["prefijo"]})'
                                )
                        else:
                            _, created = TipoComprobante.objects.get_or_create(
                                empresa=empresa,
                                codigo=t['codigo'],
                                defaults={
                                    'nombre':             t['nombre'],
                                    'prefijo':            t.get('prefijo', ''),
                                    'consecutivo_actual': 1,
                                    'activa':             True,
                                },
                            )
                            if created:
                                creados += 1
                                self.stdout.write(
                                    f'    [CREADO]  {t["codigo"]:6s}  {t["nombre"]}  '
                                    f'(prefijo: {t["prefijo"]})'
                                )
                            else:
                                existentes += 1
                    except Exception as exc:
                        errores += 1
                        self.stdout.write(
                            self.style.ERROR(f'    [ERROR] {t["codigo"]}: {exc}')
                        )

                fn  = self.style.WARNING if dry_run else self.style.SUCCESS
                msg = (
                    f'    [DRY-RUN] Crearia {creados} | Ya existen {existentes} | Errores {errores}'
                    if dry_run else
                    f'    [OK] Creados: {creados} | Ya existian: {existentes} | Errores: {errores}'
                )
                self.stdout.write(fn(msg))

        self.stdout.write(self.style.SUCCESS('\n[DONE] Tipos de comprobante completado.'))
