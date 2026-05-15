"""
Data migration: Migra retenciones desde Factura/ItemFactura a Retencion (v3.7.1).

Orden garantizado por dependencies:
  facturas.0010 -> contabilidad.0007 -> facturas.0012

empresa_id es obligatorio (SintelTenantBaseModel). Se toma de cada Factura/ItemFactura.
"""

from decimal import Decimal
from django.db import migrations


def migrate_retenciones(apps, schema_editor):
    Factura = apps.get_model('facturas', 'Factura')
    ItemFactura = apps.get_model('facturas', 'ItemFactura')
    Retencion = apps.get_model('contabilidad', 'Retencion')

    migrated = 0

    for factura in Factura.objects.only(
        'id', 'empresa_id', 'numero', 'retefuente', 'reteica', 'reteiva'
    ):
        for tipo, campo in [
            ('RETEFUENTE', factura.retefuente),
            ('RETEICA',    factura.reteica),
            ('RETEIVA',    factura.reteiva),
        ]:
            if not campo:
                continue
            monto = Decimal(str(campo))
            if monto <= Decimal('0'):
                continue
            Retencion.objects.create(
                empresa_id=factura.empresa_id,
                tipo=tipo,
                porcentaje=Decimal('0'),
                base=Decimal('0'),
                monto=monto,
                documento_origen_app='facturas',
                documento_origen_modelo='Factura',
                documento_origen_id=factura.id,
                reversada=False,
                notas=f'migrate_v371_from_facturas; numero={factura.numero}',
            )
            migrated += 1

    for item in ItemFactura.objects.select_related('factura').only(
        'id', 'empresa_id', 'factura_id',
        'porcentaje_retefuente', 'valor_retefuente',
        'porcentaje_reteica',    'valor_reteica',
        'porcentaje_reteiva',    'valor_reteiva',
    ):
        for tipo, valor, pct in [
            ('RETEFUENTE', item.valor_retefuente, item.porcentaje_retefuente),
            ('RETEICA',    item.valor_reteica,    item.porcentaje_reteica),
            ('RETEIVA',    item.valor_reteiva,    item.porcentaje_reteiva),
        ]:
            if not valor:
                continue
            monto = Decimal(str(valor))
            if monto <= Decimal('0'):
                continue
            Retencion.objects.create(
                empresa_id=item.empresa_id,
                tipo=tipo,
                porcentaje=Decimal(str(pct or 0)),
                base=Decimal('0'),
                monto=monto,
                documento_origen_app='facturas',
                documento_origen_modelo='ItemFactura',
                documento_origen_id=item.id,
                reversada=False,
                notas=f'migrate_v371_from_facturas; item_id={item.id}; factura_id={item.factura_id}',
            )
            migrated += 1

    print(f'\n[contabilidad.0007] Retenciones migradas: {migrated}')


def reverse_retenciones(apps, schema_editor):
    Retencion = apps.get_model('contabilidad', 'Retencion')
    deleted, _ = Retencion.objects.filter(
        notas__startswith='migrate_v371_from_facturas'
    ).delete()
    print(f'\n[contabilidad.0007] Rollback: {deleted} retenciones eliminadas')


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0006_add_retenciones_models'),
        ('facturas', '0010_alter_factura_retefuente_alter_factura_reteica_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_retenciones, reverse_retenciones, atomic=False),
    ]
