"""
Migration 0010 - Motor de Plantillas Contables (Fase 3)

Cambios:
1. PlantillaContable: hace nullable los campos legacy (regla, cuenta_debe_codigo,
   cuenta_credito_codigo) para coexistir con el modo Motor.
2. PlantillaContable: agrega campos nombre y tipo_transaccion para el Motor Fase 3.
3. PlantillaContable: actualiza constraint unique_regla_activo para excluir filas
   con regla=NULL (evita conflictos con las nuevas filas del motor).
4. PlantillaContable: agrega constraint unique_tipo_transaccion_activo (1 plantilla
   activa por tipo de documento VENTA/COMPRA/GASTO/NOMINA).
5. LineaPlantilla: nuevo modelo que define las lineas de partida doble.
"""
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contabilidad", "0009_retencion_naturaleza"),
        ("empresa", "0009_sedes_areas_explicit_fk"),
    ]

    operations = [
        # --- PlantillaContable: hacer campos legacy nullable ---
        migrations.AlterField(
            model_name="plantillacontable",
            name="regla",
            field=models.ForeignKey(
                blank=True,
                help_text="Regla contable asociada (modo resolver legacy)",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="plantillas",
                to="contabilidad.reglacontable",
                verbose_name="Regla Contable",
            ),
        ),
        migrations.AlterField(
            model_name="plantillacontable",
            name="cuenta_debe_codigo",
            field=models.CharField(
                blank=True,
                help_text="Codigo PUC para el DEBE (modo resolver legacy)",
                max_length=20,
                null=True,
                verbose_name="Codigo Cuenta Debito",
            ),
        ),
        migrations.AlterField(
            model_name="plantillacontable",
            name="cuenta_credito_codigo",
            field=models.CharField(
                blank=True,
                help_text="Codigo PUC para el HABER (modo resolver legacy)",
                max_length=20,
                null=True,
                verbose_name="Codigo Cuenta Credito",
            ),
        ),

        # --- PlantillaContable: nuevos campos Motor Fase 3 ---
        migrations.AddField(
            model_name="plantillacontable",
            name="nombre",
            field=models.CharField(
                blank=True,
                help_text="Nombre descriptivo (ej: Venta Facturas Electronicas)",
                max_length=100,
                null=True,
                verbose_name="Nombre",
            ),
        ),
        migrations.AddField(
            model_name="plantillacontable",
            name="tipo_transaccion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("VENTA", "Venta"),
                    ("COMPRA", "Compra"),
                    ("GASTO", "Gasto"),
                    ("NOMINA", "Nomina"),
                ],
                help_text="Tipo de documento que usa esta plantilla: VENTA, COMPRA, GASTO o NOMINA",
                max_length=20,
                null=True,
                verbose_name="Tipo de Transaccion",
            ),
        ),

        # --- PlantillaContable: actualizar constraints ---
        # Eliminar constraint original (condicion no incluia regla__isnull=False)
        migrations.RemoveConstraint(
            model_name="plantillacontable",
            name="plantillacontable_unique_regla_activo",
        ),
        # Recrear con condicion regla IS NOT NULL (no colisiona con filas del motor)
        migrations.AddConstraint(
            model_name="plantillacontable",
            constraint=models.UniqueConstraint(
                condition=models.Q(activo=True) & models.Q(regla__isnull=False),
                fields=("empresa", "regla"),
                name="plantillacontable_unique_regla_activo",
            ),
        ),
        # Nuevo: 1 sola plantilla activa por tipo_transaccion por empresa
        migrations.AddConstraint(
            model_name="plantillacontable",
            constraint=models.UniqueConstraint(
                condition=models.Q(activo=True) & models.Q(tipo_transaccion__isnull=False),
                fields=("empresa", "tipo_transaccion"),
                name="plantillacontable_unique_tipo_transaccion_activo",
            ),
        ),

        # --- LineaPlantilla: nuevo modelo ---
        migrations.CreateModel(
            name="LineaPlantilla",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp auto-asignado al crear el registro.",
                        verbose_name="Creado",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp auto-actualizado al modificar.",
                        verbose_name="Actualizado",
                    ),
                ),
                (
                    "naturaleza",
                    models.CharField(
                        choices=[("DEBE", "Debe"), ("HABER", "Haber")],
                        help_text="DEBE o HABER",
                        max_length=5,
                        verbose_name="Naturaleza",
                    ),
                ),
                (
                    "origen_valor",
                    models.CharField(
                        choices=[
                            ("SALDO_BASE", "Saldo Base / Subtotal"),
                            ("IVA_GENERADO", "IVA Generado"),
                            ("IVA_DESCONTABLE", "IVA Descontable"),
                            ("RETEFUENTE", "Retencion en la Fuente"),
                            ("RETEICA", "Retencion ICA"),
                            ("RETEIVA", "Retencion IVA"),
                            ("TOTAL_DOCUMENTO", "Total Neto del Documento"),
                        ],
                        help_text="Componente economico del documento que alimenta esta cuenta",
                        max_length=30,
                        verbose_name="Origen del Valor",
                    ),
                ),
                (
                    "porcentaje_aplicar",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("100.00"),
                        help_text="100 = valor completo, 50 = la mitad del componente",
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                        verbose_name="Porcentaje a Aplicar",
                    ),
                ),
                (
                    "orden",
                    models.PositiveSmallIntegerField(
                        default=1,
                        help_text="Orden de aparicion en el asiento generado",
                        verbose_name="Orden",
                    ),
                ),
                (
                    "descripcion",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Descripcion que aparece en el MovimientoContable",
                        max_length=200,
                        verbose_name="Descripcion",
                    ),
                ),
                (
                    "cuenta_contable",
                    models.ForeignKey(
                        help_text="Cuenta PUC nivel 6 para este movimiento",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="contabilidad.cuentacontable",
                        verbose_name="Cuenta Contable",
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        help_text="Empresa propietaria (SSoT por tenant). Requerido.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_related",
                        to="empresa.empresa",
                        verbose_name="Empresa",
                    ),
                ),
                (
                    "plantilla",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="contabilidad.plantillacontable",
                        verbose_name="Plantilla Contable",
                    ),
                ),
            ],
            options={
                "verbose_name": "Linea de Plantilla",
                "verbose_name_plural": "Lineas de Plantilla",
                "ordering": ["plantilla", "orden"],
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["empresa"], name="contabilida_empresa_lp001_idx"
                    ),
                    models.Index(
                        fields=["empresa", "-created_at"],
                        name="contabilida_empresa_lp002_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("empresa", "plantilla", "origen_valor"),
                        name="lineaplantilla_unique_plantilla_origen_valor",
                    )
                ],
            },
        ),
    ]
