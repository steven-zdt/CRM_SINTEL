from django_tenants.utils import schema_context
from apps.tenant.facturas.models import Factura
from apps.tenant.gastos.models import DocumentoSoporte
from apps.tenant.empleados.models import Devengo
from apps.tenant.inventario.models import MovimientoInventario

for schema in ['home', 'cliente']:
    with schema_context(schema):
        print(f"\nSchema: {schema}")
        print(f"Facturas: {Factura.objects.count()}")
        print(f"Gastos: {DocumentoSoporte.objects.count()}")
        print(f"Devengos (Nomina): {Devengo.objects.count()}")
        print(f"Movimientos (Inventario): {MovimientoInventario.objects.count()}")
