from django.apps import AppConfig


class DbExtensionsConfig(AppConfig):
    """App minima, sin modelos, cuyo unico proposito es alojar migraciones
    de objetos a nivel de base de datos (extensiones de PostgreSQL) que deben
    aplicarse una sola vez via `migrate_schemas --shared`.

    Vive fuera de `apps/public/` a proposito: `apps/public/` esta restringido
    (AGENTS.md, requiere RFC + needs-admin-approval) y una extension de BD no
    es logica de negocio del esquema publico. Se registra solo en SHARED_APPS
    -- NUNCA en TENANT_APPS -- porque las extensiones de PostgreSQL son
    database-wide, no schema-scoped.

    Introducida en AI-VECTOR-02 (docs/ai/AI_VECTOR_POC_EXECUTION.md).
    """

    name = "apps.db_extensions"
    verbose_name = "DB Extensions (PostgreSQL)"
