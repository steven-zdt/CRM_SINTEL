# Generated migration for Devengo horas extras y recargos

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_empleados', '0004_remove_empleado_cuenta_contable_uuid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='devengo',
            name='horas_extras_diurnas',
            field=models.DecimalField(decimal_places=2, default=0, help_text='H.E. diurnas Lun-Sab 6am-9pm (+25%)', max_digits=6),
        ),
        migrations.AddField(
            model_name='devengo',
            name='horas_extras_nocturnas',
            field=models.DecimalField(decimal_places=2, default=0, help_text='H.E. nocturnas 9pm-6am (+75%)', max_digits=6),
        ),
        migrations.AddField(
            model_name='devengo',
            name='recargo_nocturno_horas',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Horas nocturnas ordinarias (+35%)', max_digits=6),
        ),
        migrations.AddField(
            model_name='devengo',
            name='recargo_festivo_horas',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Horas dominicales/festivas (+75%)', max_digits=6),
        ),
        migrations.AddField(
            model_name='devengo',
            name='valor_horas_extras',
            field=models.DecimalField(decimal_places=2, default=0, editable=False, help_text='Valor calculado de H.E. y recargos en COP', max_digits=12),
        ),
    ]
