"""
Migration: Mark retention fields as deprecated (v3.7.1).

v3.7.1: Retenciones movidas a Contabilidad app. Los campos en Facturas
se marcan como deprecated con:
- null=True, blank=True, editable=False
- @property en modelo para backward compat (lee desde Retencion model)

Esta migración prepara los datos para la completa eliminación en v3.8+.
"""

from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('facturas', '0008_add_reteiva_fields'),
    ]

    operations = [
        # Factura: Deprecate retefuente
        migrations.AlterField(
            model_name='factura',
            name='retefuente',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='Retención en la Fuente [DEPRECATED v3.7.1]',
                help_text='[DEPRECATED v3.7.1] Leer desde Contabilidad.Retencion. Campo mantenido solo para backward compatibility.'
            ),
        ),
        # Factura: Deprecate reteica
        migrations.AlterField(
            model_name='factura',
            name='reteica',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='ReteICA [DEPRECATED v3.7.1]',
                help_text='[DEPRECATED v3.7.1] Leer desde Contabilidad.Retencion. Campo mantenido solo para backward compatibility.'
            ),
        ),
        # Factura: Deprecate reteiva
        migrations.AlterField(
            model_name='factura',
            name='reteiva',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='ReteIVA [DEPRECATED v3.7.1]',
                help_text='[DEPRECATED v3.7.1] Leer desde Contabilidad.Retencion. Campo mantenido solo para backward compatibility.'
            ),
        ),
        # ItemFactura: Deprecate porcentaje_retefuente
        migrations.AlterField(
            model_name='itemfactura',
            name='porcentaje_retefuente',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='% Retención Fuente [DEPRECATED v3.7.1]',
            ),
        ),
        # ItemFactura: Deprecate valor_retefuente
        migrations.AlterField(
            model_name='itemfactura',
            name='valor_retefuente',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='Valor Retención Fuente [DEPRECATED v3.7.1]',
            ),
        ),
        # ItemFactura: Deprecate porcentaje_reteiva
        migrations.AlterField(
            model_name='itemfactura',
            name='porcentaje_reteiva',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='% ReteIVA [DEPRECATED v3.7.1]',
            ),
        ),
        # ItemFactura: Deprecate valor_reteiva
        migrations.AlterField(
            model_name='itemfactura',
            name='valor_reteiva',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='Valor ReteIVA [DEPRECATED v3.7.1]',
            ),
        ),
        # ItemFactura: Deprecate porcentaje_reteica
        migrations.AlterField(
            model_name='itemfactura',
            name='porcentaje_reteica',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=5,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='% ReteICA [DEPRECATED v3.7.1]',
            ),
        ),
        # ItemFactura: Deprecate valor_reteica
        migrations.AlterField(
            model_name='itemfactura',
            name='valor_reteica',
            field=models.DecimalField(
                blank=True,
                default=Decimal('0.00'),
                decimal_places=2,
                editable=False,
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                verbose_name='Valor ReteICA [DEPRECATED v3.7.1]',
            ),
        ),
    ]
