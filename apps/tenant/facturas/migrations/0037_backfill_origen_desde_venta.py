# Facturas Hub FASE 7-8: backfill de datos, no de esquema.
#
# 0036 agrego origen/source_system con default EXTERNO/DESCONOCIDO -- correcto
# para filas nuevas, pero deja mal clasificadas las Factura ya existentes que
# en realidad fueron creadas por Ventas (crear_factura_desde_venta(), nunca
# paso por guardar_desde_dto()). La señal real y verificable es
# Venta.factura_asociada (OneToOneField ya existente, sin ambiguedad) -- se
# usa esa relacion, no una suposicion, para retro-poblar origen=INTERNO en
# esas filas puntuales. Reversible: reversa a EXTERNO/DESCONOCIDO (el default
# de 0036), no borra nada.
from django.db import migrations


def backfill_origen_interno(apps, schema_editor):
    Venta = apps.get_model('tenant_ventas', 'Venta')
    Factura = apps.get_model('facturas', 'Factura')

    factura_ids = list(
        Venta.objects.exclude(factura_asociada=None).values_list('factura_asociada_id', flat=True)
    )
    if factura_ids:
        Factura.objects.filter(id__in=factura_ids).update(origen='INTERNO', source_system='SINTEL')


def revertir_a_default(apps, schema_editor):
    Venta = apps.get_model('tenant_ventas', 'Venta')
    Factura = apps.get_model('facturas', 'Factura')

    factura_ids = list(
        Venta.objects.exclude(factura_asociada=None).values_list('factura_asociada_id', flat=True)
    )
    if factura_ids:
        Factura.objects.filter(id__in=factura_ids).update(origen='EXTERNO', source_system='DESCONOCIDO')


class Migration(migrations.Migration):

    dependencies = [
        ('facturas', '0036_factura_origen_factura_source_system'),
        ('tenant_ventas', '0003_venta_numero_factura_resolucionfacturacion_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_origen_interno, revertir_a_default),
    ]
