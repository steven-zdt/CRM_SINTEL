import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresa', '0007_empresa_owner_email'),
        ('tenant_proyectos', '0007_proyecto_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='costo_planeado_total',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Suma de ItemPresupuestoProyecto - Zero Waste cache', max_digits=15),
        ),
        migrations.AddField(
            model_name='proyecto',
            name='margen_planeado',
            field=models.DecimalField(decimal_places=2, default=0, help_text='utilidad_planeada / valor_contrato * 100', max_digits=5),
        ),
        migrations.AddField(
            model_name='proyecto',
            name='utilidad_planeada',
            field=models.DecimalField(decimal_places=2, default=0, help_text='valor_contrato - costo_planeado_total', max_digits=15),
        ),
        migrations.CreateModel(
            name='ItemPresupuestoProyecto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Timestamp auto-asignado al crear el registro.', verbose_name='Creado')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Timestamp auto-actualizado al modificar.', verbose_name='Actualizado')),
                ('categoria', models.CharField(choices=[('MANO_OBRA', 'Mano de Obra'), ('EQUIPOS', 'Equipos'), ('MATERIALES', 'Materiales')], help_text='Mano de Obra, Equipos o Materiales', max_length=20, verbose_name='Categoria')),
                ('descripcion', models.CharField(blank=True, help_text='Ej: Instalacion de cableado, Alquiler de grua, etc.', max_length=300, verbose_name='Descripcion')),
                ('cantidad', models.DecimalField(decimal_places=2, default=1, help_text='Cantidad planeada', max_digits=10, verbose_name='Cantidad')),
                ('valor_unitario', models.DecimalField(decimal_places=2, default=0, help_text='Valor por unidad', max_digits=15, verbose_name='Valor Unitario')),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, help_text='cantidad x valor_unitario (calculado en service layer)', max_digits=15, verbose_name='Subtotal')),
                ('empresa', models.ForeignKey(help_text='DSV: valida que item pertenezca al tenant', on_delete=django.db.models.deletion.PROTECT, related_name='items_presupuesto', to='empresa.empresa', verbose_name='Empresa')),
                ('proyecto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items_presupuesto', to='tenant_proyectos.proyecto', verbose_name='Proyecto')),
            ],
            options={
                'verbose_name': 'Item de Presupuesto',
                'verbose_name_plural': 'items de Presupuesto',
                'ordering': ['categoria', 'id'],
                'indexes': [models.Index(fields=['proyecto'], name='tenant_proy_proyect_b6b6ff_idx'), models.Index(fields=['empresa'], name='tenant_proy_empresa_d84598_idx'), models.Index(fields=['categoria'], name='tenant_proy_categor_8d9cea_idx')],
            },
        ),
    ]
