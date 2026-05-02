"""Alter TenantProfile.user to CASCADE and make non-nullable.

This migration sets the relation back to cascade so deleting a global User
removes tenant profiles (prevents orphan tenant rows).
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresa', '0001_initial'),
        ('perfil', '0003_alter_tenantprofile_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenantprofile',
            name='user',
            field=models.OneToOneField(
                to=settings.AUTH_USER_MODEL,
                on_delete=models.CASCADE,
                related_name='tenant_profile',
                verbose_name='Usuario',
                help_text='Usuario global al que pertenece este perfil (reside en esquema public)'
            ),
        ),
    ]
