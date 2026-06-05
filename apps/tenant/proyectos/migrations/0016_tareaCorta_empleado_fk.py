# Migration 0016: TareaCorta - Remove proyecto/operador, add empleado FK
# v3.10.0 - Uses IF EXISTS SQL for idempotent multi-tenant execution.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresa', '0009_sedes_areas_explicit_fk'),
        ('tenant_empleados', '0008_foto_empleado'),
        ('tenant_proyectos', '0015_tareacorta'),
    ]

    operations = [
        # Use RunSQL with IF EXISTS to handle tenants that may be in different states.
        migrations.RunSQL(
            sql="""
                ALTER TABLE tenant_proyectos_tareacorta
                    DROP CONSTRAINT IF EXISTS unique_tarea_corta_por_proyecto_fecha_inicio_titulo;
                DROP INDEX IF EXISTS tenant_proy_proyect_9b170d_idx;
                DROP INDEX IF EXISTS tenant_proy_emplead_idx;
                DROP INDEX IF EXISTS tenant_proy_emplead_4d5513_idx;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Remove operador if it exists
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name='tenant_proyectos_tareacorta' AND column_name='operador_id'
                    ) THEN
                        ALTER TABLE tenant_proyectos_tareacorta DROP COLUMN operador_id;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Remove proyecto if it exists
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name='tenant_proyectos_tareacorta' AND column_name='proyecto_id'
                    ) THEN
                        ALTER TABLE tenant_proyectos_tareacorta DROP COLUMN proyecto_id;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Add empleado_id FK if it does not already exist
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name='tenant_proyectos_tareacorta' AND column_name='empleado_id'
                    ) THEN
                        ALTER TABLE tenant_proyectos_tareacorta
                            ADD COLUMN empleado_id bigint NULL
                            REFERENCES tenant_empleados_empleado(id)
                            DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Re-create index and constraint (idempotent)
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS tenant_proy_emplead_4d5513_idx
                    ON tenant_proyectos_tareacorta (empleado_id, fecha_inicio);

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'unique_tarea_corta_por_empleado_fecha_inicio_titulo'
                    ) THEN
                        ALTER TABLE tenant_proyectos_tareacorta
                            ADD CONSTRAINT unique_tarea_corta_por_empleado_fecha_inicio_titulo
                            UNIQUE (empleado_id, fecha_inicio, titulo);
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Tell Django ORM the new state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(
                    model_name='tareacorta',
                    name='unique_tarea_corta_por_proyecto_fecha_inicio_titulo',
                ),
                migrations.RemoveIndex(
                    model_name='tareacorta',
                    name='tenant_proy_proyect_9b170d_idx',
                ),
                migrations.RemoveField(
                    model_name='tareacorta',
                    name='operador',
                ),
                migrations.RemoveField(
                    model_name='tareacorta',
                    name='proyecto',
                ),
                migrations.AddField(
                    model_name='tareacorta',
                    name='empleado',
                    field=models.ForeignKey(
                        blank=True,
                        help_text='Empleado asignado a la tarea corta',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='tareas_cortas',
                        to='tenant_empleados.empleado',
                        verbose_name='Empleado',
                    ),
                ),
                migrations.AddIndex(
                    model_name='tareacorta',
                    index=models.Index(
                        fields=['empleado', 'fecha_inicio'],
                        name='tenant_proy_emplead_4d5513_idx',
                    ),
                ),
                migrations.AddConstraint(
                    model_name='tareacorta',
                    constraint=models.UniqueConstraint(
                        fields=('empleado', 'fecha_inicio', 'titulo'),
                        name='unique_tarea_corta_por_empleado_fecha_inicio_titulo',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
