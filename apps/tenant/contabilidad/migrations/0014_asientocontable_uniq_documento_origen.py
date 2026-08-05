# Generated manually (entorno sin acceso a `manage.py makemigrations`) siguiendo el
# patron de 0013_remove_lineaplantilla_unique_origen_valor.py.
# [PERF-C1] Respaldo de idempotencia a nivel de base de datos para AsientoContable.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contabilidad', '0013_remove_lineaplantilla_unique_origen_valor'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='asientocontable',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('documento_origen_reversado', False),
                    ('documento_origen_id__isnull', False),
                ),
                fields=('empresa', 'documento_origen_app', 'documento_origen_modelo', 'documento_origen_id'),
                name='uniq_asiento_documento_origen_no_reversado',
            ),
        ),
    ]
