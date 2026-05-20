import uuid
from django.db import migrations, models


def populate_uuid_documentosoporte(apps, schema_editor):
    schema_editor.execute(
        "UPDATE tenant_gastos_documentosoporte SET uuid = gen_random_uuid() WHERE uuid IS NULL;"
    )


def populate_uuid_resoluciondian(apps, schema_editor):
    schema_editor.execute(
        "UPDATE tenant_gastos_resoluciondian SET uuid = gen_random_uuid() WHERE uuid IS NULL;"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_gastos', '0015_alter_documentosoporte_cuenta_gasto_uuid'),
    ]

    operations = [
        # Step 1: Add fields as nullable (safe for existing rows)
        migrations.AddField(
            model_name='documentosoporte',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name='resoluciondian',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),

        # Step 2: Populate UUIDs for existing records
        migrations.RunPython(populate_uuid_documentosoporte, migrations.RunPython.noop),
        migrations.RunPython(populate_uuid_resoluciondian, migrations.RunPython.noop),

        # Step 3: Make fields required and unique
        migrations.AlterField(
            model_name='documentosoporte',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='resoluciondian',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
