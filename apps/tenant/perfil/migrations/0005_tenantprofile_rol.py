"""Migration: add rol field to TenantProfile.

[RULE 14] Campo rol sigue la convencion CharField con choices de RolTenant.
Valor por defecto: OPERADOR (rol conservador, no otorga privilegios elevados en
migraciones sobre datos existentes).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perfil', '0004_alter_tenantprofile_user_cascade'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenantprofile',
            name='rol',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrador'),
                    ('OPERADOR', 'Operador'),
                    ('VISOR', 'Visor'),
                ],
                default='OPERADOR',
                db_index=True,
                max_length=20,
                verbose_name='Rol',
                help_text=(
                    'Rol del colaborador en el tenant: '
                    'ADMIN (admin), OPERADOR (puede editar), VISOR (solo lectura).'
                ),
            ),
        ),
    ]
