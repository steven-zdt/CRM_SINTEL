from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturas', '0024_add_idx_empresa_cliente_uuid'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='factura',
            index=models.Index(fields=['empresa_id', 'proveedor_uuid'], name='idx_fact_empresa_prov_uuid'),
        ),
    ]
