from django.db import migrations
from django_tenants.utils import get_public_schema_name


def _create_vector_extension(apps, schema_editor):
    """Crea la extension `vector` una sola vez, en el schema `public`.

    django-tenants registra las migraciones de SHARED_APPS en el
    `django_migrations` de TODOS los schemas (mismo patron que `auth`,
    `impuestos`, etc.), pero una operacion que no es de modelo -- como
    `CREATE EXTENSION` -- se ejecutaria de verdad una vez por schema.
    Con `IF NOT EXISTS` seria inofensivo (la extension es database-wide,
    `pg_extension` nunca pasaria de 1 fila), pero la auditoria lo marca
    como senal de diseno incorrecto. El guard por schema lo evita: en
    cualquier schema != public la migracion queda como no-op registrado.
    """
    if schema_editor.connection.schema_name != get_public_schema_name():
        return
    schema_editor.execute('CREATE EXTENSION IF NOT EXISTS "vector"')


def _drop_vector_extension(apps, schema_editor):
    """Reverse: solo dropea la extension desde `public`.

    Sin este guard, `migrate_schemas ... db_extensions zero` haria que el
    PRIMER tenant en revertir ejecutara `DROP EXTENSION vector` y matara la
    extension database-wide mientras los demas schemas siguen creyendola
    aplicada. Falla -- correctamente -- si existe alguna columna `vector`
    dependiente.
    """
    if schema_editor.connection.schema_name != get_public_schema_name():
        return
    schema_editor.execute('DROP EXTENSION IF EXISTS "vector"')


class Migration(migrations.Migration):
    """AI-VECTOR-02: instala pgvector una sola vez a nivel de base de datos.

    Se aplica via `migrate_schemas --shared` (SHARED_APPS). El tipo `vector`
    queda visible desde cualquier schema de tenant porque django-tenants
    mantiene `public` en el search_path (`<tenant>, public`).

    NO crea ninguna tabla vectorial -- esas viven en la app TENANT_APPS
    `apps.tenant.ai_knowledge` (AI-VECTOR-03), aplicadas con
    `migrate_schemas --tenant`.
    """

    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(_create_vector_extension, _drop_vector_extension),
    ]
