"""Alter ConsoleActionLog.actor and target_user to CASCADE.

Generated to ensure console logs are removed when their referenced User is deleted.
"""

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("console", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="consoleactionlog",
            name="actor",
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL,
                on_delete=models.CASCADE,
                null=True,
                related_name="console_actions",
                verbose_name="Actor",
            ),
        ),
        migrations.AlterField(
            model_name="consoleactionlog",
            name="target_user",
            field=models.ForeignKey(
                blank=True,
                to=settings.AUTH_USER_MODEL,
                on_delete=models.CASCADE,
                null=True,
                related_name="console_action_targets",
                verbose_name="Usuario objetivo",
            ),
        ),
    ]
