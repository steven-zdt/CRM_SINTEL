# Generated migration for cotizacion_numero snapshot field (v3.10.1)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturas', '0018_factura_cotizacion_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='factura',
            name='cotizacion_numero',
            field=models.CharField(
                blank=True,
                help_text='Numero de la cotizacion vinculada (snapshot para Zero Waste queries)',
                max_length=100,
                null=True
            ),
        ),
    ]
