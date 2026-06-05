"""
Migración: Retencion — unificación de naturaleza (v3.16.1)

Reemplaza los dos BooleanFields mutuamente excluyentes:
  - aplicada_por_cliente  (VENTA)
  - aplicada_por_proveedor (COMPRA)

Por un único CharField:
  - naturaleza = 'VENTA' | 'COMPRA'

Elimina también fecha_creacion (duplicado de SintelTenantBaseModel.created_at).
"""
from django.db import migrations, models


def booleans_a_naturaleza(apps, schema_editor):
    Retencion = apps.get_model('contabilidad', 'Retencion')
    # aplicada_por_proveedor=True indica contexto COMPRA
    Retencion.objects.filter(aplicada_por_proveedor=True).update(naturaleza='COMPRA')
    # Todo lo demás queda como VENTA (valor por defecto ya aplicado en AddField)


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0008_impuestodocumento_plantillacontable'),
    ]

    operations = [
        # 1. Agregar naturaleza con default VENTA
        migrations.AddField(
            model_name='retencion',
            name='naturaleza',
            field=models.CharField(
                choices=[('VENTA', 'Venta'), ('COMPRA', 'Compra')],
                default='VENTA',
                max_length=10,
                verbose_name='Naturaleza',
                help_text='VENTA: retencion requerida por el cliente. COMPRA: retenida al proveedor.',
            ),
        ),
        # 2. Data migration: convertir booleans legacy a naturaleza
        migrations.RunPython(booleans_a_naturaleza, migrations.RunPython.noop),
        # 3. Eliminar campos legacy
        migrations.RemoveField(model_name='retencion', name='aplicada_por_cliente'),
        migrations.RemoveField(model_name='retencion', name='aplicada_por_proveedor'),
        migrations.RemoveField(model_name='retencion', name='fecha_creacion'),
        # 4. Agregar índice en naturaleza
        migrations.AddIndex(
            model_name='retencion',
            index=models.Index(fields=['naturaleza'], name='retencion_naturaleza_idx'),
        ),
        # 5. Actualizar ordering en Meta (cosmético para estado_migraciones)
        migrations.AlterModelOptions(
            name='retencion',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Retenci\xf3n',
                'verbose_name_plural': 'Retenciones',
            },
        ),
    ]
