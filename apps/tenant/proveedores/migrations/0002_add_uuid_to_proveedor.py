# Generated manually on 2026-05-11

import uuid
from django.db import migrations, models
from django.contrib.postgres.operations import CreateExtension


def populate_uuid_unique(apps, schema_editor):
    """Populate UUID for existing proveedores using gen_random_uuid."""
    schema_editor.execute("UPDATE tenant_proveedores_proveedor SET uuid = gen_random_uuid() WHERE uuid IS NULL OR uuid = '00000000-0000-0000-0000-000000000000'::uuid;")


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_proveedores', '0001_initial'),
    ]

    operations = [
        # Enable uuid-ossp extension for gen_random_uuid
        CreateExtension('uuid-ossp'),

        # Step 1: Add field as nullable without default
        migrations.AddField(
            model_name='proveedor',
            name='uuid',
            field=models.UUIDField(
                db_index=True,
                null=True,
                blank=True,
                editable=False
            ),
        ),

        # Step 2: Populate UUIDs for existing records using database function
        migrations.RunPython(populate_uuid_unique),

        # Step 3: Make field required and unique
        migrations.AlterField(
            model_name='proveedor',
            name='uuid',
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                unique=True
            ),
        ),
    ]
