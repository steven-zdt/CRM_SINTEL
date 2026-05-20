import uuid as uuid_module

from django.db import migrations, models


def _populate_uuids(apps, schema_editor):
    schema_editor.execute(
        "UPDATE tenant_cotizaciones_producto SET uuid = gen_random_uuid() WHERE uuid IS NULL;"
    )
    schema_editor.execute(
        "UPDATE tenant_cotizaciones_servicio SET uuid = gen_random_uuid() WHERE uuid IS NULL;"
    )
    schema_editor.execute(
        "UPDATE tenant_cotizaciones_item SET uuid = gen_random_uuid() WHERE uuid IS NULL;"
    )
    schema_editor.execute(
        "UPDATE tenant_cotizaciones_configuracion SET uuid = gen_random_uuid() WHERE uuid IS NULL;"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_cotizaciones', '0003_cotizacion_dias_configuracion_and_more'),
    ]

    operations = [
        # Phase 1: Add nullable uuid fields (no unique constraint yet)
        migrations.AddField(
            model_name='producto',
            name='uuid',
            field=models.UUIDField(editable=False, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='servicio',
            name='uuid',
            field=models.UUIDField(editable=False, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='cotizacionitem',
            name='uuid',
            field=models.UUIDField(editable=False, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='configuracioncotizacion',
            name='uuid',
            field=models.UUIDField(editable=False, null=True, blank=True),
        ),
        # Phase 2: Populate all NULL uuids using PostgreSQL native gen_random_uuid()
        migrations.RunPython(_populate_uuids, migrations.RunPython.noop),
        # Phase 3: Make unique + db_index
        migrations.AlterField(
            model_name='producto',
            name='uuid',
            field=models.UUIDField(default=uuid_module.uuid4, db_index=True, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='servicio',
            name='uuid',
            field=models.UUIDField(default=uuid_module.uuid4, db_index=True, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='cotizacionitem',
            name='uuid',
            field=models.UUIDField(default=uuid_module.uuid4, db_index=True, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='configuracioncotizacion',
            name='uuid',
            field=models.UUIDField(default=uuid_module.uuid4, db_index=True, editable=False, unique=True),
        ),
    ]
