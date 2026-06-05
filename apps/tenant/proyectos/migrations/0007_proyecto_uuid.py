# ARCHIVO: apps/tenant/proyectos/migrations/0007_proyecto_uuid.py
"""
Migracion M-001 Roadmap M3 - UUID lookup field para Proyecto.
Patron 3-fases (safe migration):
  1. AddField nullable
  2. RunPython - popula filas existentes
  3. AlterField - aplica unique + db_index
"""
import uuid as uuid_lib

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Proyecto = apps.get_model('tenant_proyectos', 'Proyecto')
    for proyecto in Proyecto.objects.filter(uuid__isnull=True).iterator():
        proyecto.uuid = uuid_lib.uuid4()
        proyecto.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_proyectos', '0006_alter_itempedido_options_and_more'),
    ]

    operations = [
        # Fase 1: Agregar campo nullable (no bloquea tabla en produccion)
        migrations.AddField(
            model_name='proyecto',
            name='uuid',
            field=models.UUIDField(null=True, blank=True, editable=False),
        ),
        # Fase 2: Poblar filas existentes con UUIDs unicos
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        # Fase 3: Aplicar constraint unique + db_index
        migrations.AlterField(
            model_name='proyecto',
            name='uuid',
            field=models.UUIDField(
                default=uuid_lib.uuid4,
                unique=True,
                editable=False,
                db_index=True,
            ),
        ),
    ]
