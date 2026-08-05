# [ARQ-A1] Agrega campo uuid a ConfiguracionRetenciones (AGENTS.md §25).
# Mismo patron de un solo paso ya usado en 0012_plantilla_linea_uuid.py: con
# default=uuid.uuid4 (callable) Django genera un valor unico por fila existente,
# no aplica un unico valor estatico a todas -- no requiere el patron de 3 fases.

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0014_asientocontable_uniq_documento_origen'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionretenciones',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID'),
        ),
    ]
