import uuid
from django.db import migrations, models
from django.contrib.postgres.operations import CreateExtension


def populate_uuid_empleado(apps, schema_editor):
    schema_editor.execute(
        "UPDATE tenant_empleados_empleado SET uuid = gen_random_uuid() WHERE uuid IS NULL OR uuid = '00000000-0000-0000-0000-000000000000'::uuid;"
    )


def populate_uuid_contrato(apps, schema_editor):
    schema_editor.execute(
        "UPDATE tenant_empleados_contrato SET uuid = gen_random_uuid() WHERE uuid IS NULL OR uuid = '00000000-0000-0000-0000-000000000000'::uuid;"
    )


def populate_uuid_devengo(apps, schema_editor):
    schema_editor.execute(
        "UPDATE tenant_empleados_devengo SET uuid = gen_random_uuid() WHERE uuid IS NULL OR uuid = '00000000-0000-0000-0000-000000000000'::uuid;"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_empleados', '0001_initial'),
    ]

    operations = [
        CreateExtension('uuid-ossp'),

        # Empleado: Step 1 nullable
        migrations.AddField(
            model_name='empleado',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),
        # Contrato: Step 1 nullable
        migrations.AddField(
            model_name='contrato',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),
        # Devengo: Step 1 nullable
        migrations.AddField(
            model_name='devengo',
            name='uuid',
            field=models.UUIDField(db_index=True, null=True, blank=True, editable=False),
        ),

        # Step 2: Populate with gen_random_uuid()
        migrations.RunPython(populate_uuid_empleado, migrations.RunPython.noop),
        migrations.RunPython(populate_uuid_contrato, migrations.RunPython.noop),
        migrations.RunPython(populate_uuid_devengo, migrations.RunPython.noop),

        # Step 3: Make unique + default
        migrations.AlterField(
            model_name='empleado',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='contrato',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='devengo',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
