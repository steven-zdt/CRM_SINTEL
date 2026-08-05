# [ARQ-A1] Agrega campo uuid a ItemPresupuestoProyecto y TareaDiariaProyecto
# (AGENTS.md §25). Mismo patron de un solo paso que
# apps/tenant/contabilidad/migrations/0012_plantilla_linea_uuid.py: con
# default=uuid.uuid4 (callable) Django genera un valor unico por fila existente.

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_proyectos', '0019_proyecto_sede'),
    ]

    operations = [
        migrations.AddField(
            model_name='itempresupuestoproyecto',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name='tareadiariaproyecto',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
