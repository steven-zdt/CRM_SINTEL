"""
Migración correctiva: Elimina fisicamente las columnas contables de la tabla
tenant_proveedores_proveedor que Django ya habia eliminado del estado del modelo
(0007_remove_proveedor_codigo_contable_and_more) pero que permanecieron en la BD
por una desincronizacion entre el estado Django y la base de datos.

Columnas eliminadas:
  - codigo_contable     (NOT NULL VARCHAR) — causaba error en INSERT
  - cuenta_contable_uuid (NULL UUID)

Principio: AGENTS.md — ninguna app de negocio debe tener referencias contables.
Contabilidad es la unica propietaria del mapeo de cuentas (Pull Model).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tenant_proveedores', '0016_remove_cuentaspagar_uniq_cartera_factura_proveedor_and_more'),
    ]

    operations = [
        # SeparateDatabaseAndState: el estado Django ya esta correcto (0007 lo actualizo).
        # Solo necesitamos ejecutar el DROP COLUMN fisico en la BD.
        migrations.SeparateDatabaseAndState(
            state_operations=[],   # estado Django ya es correcto
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE tenant_proveedores_proveedor
                        DROP COLUMN IF EXISTS codigo_contable;

                        ALTER TABLE tenant_proveedores_proveedor
                        DROP COLUMN IF EXISTS cuenta_contable_uuid;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
