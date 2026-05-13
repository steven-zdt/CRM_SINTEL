import os
import django
import uuid
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.public.tenants.models import Client
from apps.tenant.empresa.models import Empresa
from apps.tenant.contabilidad.models import AsientoContable, MovimientoContable, CuentaContable
from django_tenants.utils import tenant_context

def crear_datos():
    client = Client.objects.get(schema_name='home')
    with tenant_context(client):
        print(f"Poblando tenant: {client.schema_name}")
        
        # 0. Asegurar Empresa (Singleton)
        empresa, _ = Empresa.objects.get_or_create(
            defaults={
                'razon_social': 'Empresa Home NIIF',
                'nit': '900123456-1',
                'tipo_contribuyente': 'PERSONA_JURIDICA'
            }
        )
        print(f"Empresa activa: {empresa.razon_social} (ID: {empresa.id})")

        # 1. Asegurar cuentas
        c4, _ = CuentaContable.objects.get_or_create(
            codigo='4135', 
            defaults={'nombre': 'Comercio al por mayor', 'nivel': 4, 'empresa': empresa, 'tipo': 'INGRESO'}
        )
        c5, _ = CuentaContable.objects.get_or_create(
            codigo='5105', 
            defaults={'nombre': 'Gastos de personal', 'nivel': 4, 'empresa': empresa, 'tipo': 'GASTO'}
        )
        c1, _ = CuentaContable.objects.get_or_create(
            codigo='1105', 
            defaults={'nombre': 'Caja General', 'nivel': 4, 'empresa': empresa, 'tipo': 'ACTIVO'}
        )

        # 2. Crear Asiento de Venta (Ingreso)
        asiento_v = AsientoContable.objects.create(
            empresa=empresa,
            numero=f"TEST-V-{uuid.uuid4().hex[:6]}",
            descripcion='Venta de prueba',
            fecha='2024-05-01',
            estado='APROBADO',
            tipo_comprobante='GN',
            debe_total=Decimal('1000000'),
            haber_total=Decimal('1000000')
        )
        MovimientoContable.objects.create(asiento=asiento_v, cuenta=c1, debe=Decimal('1000000'), haber=0, empresa=empresa)
        MovimientoContable.objects.create(asiento=asiento_v, cuenta=c4, debe=0, haber=Decimal('1000000'), empresa=empresa)

        # 3. Crear Asiento de Gasto
        asiento_g = AsientoContable.objects.create(
            empresa=empresa,
            numero=f"TEST-G-{uuid.uuid4().hex[:6]}",
            descripcion='Pago nómina prueba',
            fecha='2024-05-15',
            estado='APROBADO',
            tipo_comprobante='GN',
            debe_total=Decimal('400000'),
            haber_total=Decimal('400000')
        )
        MovimientoContable.objects.create(asiento=asiento_g, cuenta=c5, debe=Decimal('400000'), haber=0, empresa=empresa)
        MovimientoContable.objects.create(asiento=asiento_g, cuenta=c1, debe=0, haber=Decimal('400000'), empresa=empresa)

        print("Datos creados exitosamente.")

if __name__ == "__main__":
    crear_datos()
