# Migration 0017: TareaCorta - add Cliente FK and tenant-safe constraint.
# Uses IF EXISTS SQL for idempotent multi-tenant execution.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("empresa", "0009_sedes_areas_explicit_fk"),
        ("tenant_clientes", "0006_alter_cliente_aplica_retefuente_and_more"),
        ("tenant_empleados", "0008_foto_empleado"),
        ("tenant_proyectos", "0016_tareaCorta_empleado_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE tenant_proyectos_tareacorta
                    DROP CONSTRAINT IF EXISTS unique_tarea_corta_por_empleado_fecha_inicio_titulo;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name='tenant_proyectos_tareacorta'
                          AND column_name='cliente_id'
                    ) THEN
                        ALTER TABLE tenant_proyectos_tareacorta
                            ADD COLUMN cliente_id bigint NULL
                            REFERENCES tenant_clientes_cliente(id)
                            DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS tenant_proy_cliente_6f7149_idx
                    ON tenant_proyectos_tareacorta (cliente_id, fecha_inicio);

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'unique_tarea_corta_por_cliente_empleado_fecha_titulo'
                          AND conrelid = 'tenant_proyectos_tareacorta'::regclass
                    ) THEN
                        ALTER TABLE tenant_proyectos_tareacorta
                            ADD CONSTRAINT unique_tarea_corta_por_cliente_empleado_fecha_titulo
                            UNIQUE (cliente_id, empleado_id, fecha_inicio, titulo);
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="tareacorta",
                    name="unique_tarea_corta_por_empleado_fecha_inicio_titulo",
                ),
                migrations.AddField(
                    model_name="tareacorta",
                    name="cliente",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Cliente destino de la tarea corta",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tareas_cortas",
                        to="tenant_clientes.cliente",
                        verbose_name="Cliente",
                    ),
                ),
                migrations.AddIndex(
                    model_name="tareacorta",
                    index=models.Index(
                        fields=["cliente", "fecha_inicio"],
                        name="tenant_proy_cliente_6f7149_idx",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="tareacorta",
                    constraint=models.UniqueConstraint(
                        fields=("cliente", "empleado", "fecha_inicio", "titulo"),
                        name="unique_tarea_corta_por_cliente_empleado_fecha_titulo",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
