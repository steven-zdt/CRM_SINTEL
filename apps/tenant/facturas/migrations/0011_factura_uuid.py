"""
Migration: Agrega campo uuid a Factura (v3.7.1).

3 pasos para garantizar UUIDs unicos en filas existentes:
  1. AddField null=True sin default (columna vacia)
  2. RunPython genera un uuid4 distinto por cada fila
  3. AlterField aplica unique + NOT NULL
"""

import uuid as uuid_module
from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    """Asigna un UUID unico a cada Factura existente."""
    Factura = apps.get_model('facturas', 'Factura')
    for factura in Factura.objects.filter(uuid__isnull=True).iterator():
        factura.uuid = uuid_module.uuid4()
        factura.save(update_fields=['uuid'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('facturas', '0010_alter_factura_retefuente_alter_factura_reteica_and_more'),
    ]

    operations = [
        # Paso 1: columna nullable SIN default → PostgreSQL no asigna ningún valor
        migrations.AddField(
            model_name='factura',
            name='uuid',
            field=models.UUIDField(null=True, editable=False),
        ),
        # Paso 2: Python genera uuid4() individual por cada fila
        migrations.RunPython(populate_uuids, noop),
        # Paso 3: ya todos tienen UUID único → aplicar unique + NOT NULL
        migrations.AlterField(
            model_name='factura',
            name='uuid',
            field=models.UUIDField(
                default=uuid_module.uuid4,
                editable=False,
                unique=True,
                verbose_name='UUID',
                help_text='Identificador unico universal (usado en API URLs)',
            ),
        ),
    ]
