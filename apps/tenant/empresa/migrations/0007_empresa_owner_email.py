# Generated migration - add owner_email to Empresa
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresa', '0006_alter_empresa_empresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='owner_email',
            field=models.EmailField(
                blank=True,
                default='',
                db_index=True,
                verbose_name='Email del Propietario',
                help_text=(
                    'Email del admin primario del tenant. Poblado durante el '
                    'onboarding para Auto-Admin Elevation. No exponer en la UI de clientes.'
                ),
            ),
        ),
    ]
