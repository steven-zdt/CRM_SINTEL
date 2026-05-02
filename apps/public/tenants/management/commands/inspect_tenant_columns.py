"""
Comando de management para inspeccionar columnas de tablas en un schema de tenant.

WARNING: v2.30: Útil para diagnosticar problemas de migraciones en multi-tenant.

Uso:
    python manage.py inspect_tenant_columns <schema_name> [--table <table_name>]
    python manage.py inspect_tenant_columns cliente --table facturas_factura
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_exists

from apps.public.tenants.models import Client


class Command(BaseCommand):
    help = "Inspecciona columnas de tablas en un schema de tenant"

    def add_arguments(self, parser):
        parser.add_argument(
            "schema_name",
            type=str,
            help="Schema name del tenant a inspeccionar",
        )
        parser.add_argument(
            "--table",
            type=str,
            dest="table_name",
            help="Nombre de la tabla a inspeccionar (default: todas las tablas del tenant)",
        )

    def handle(self, *args, **options):
        schema_name = options["schema_name"]
        table_name = options.get("table_name")

        # Verificar que el schema existe
        if not schema_exists(schema_name):
            raise CommandError(f"El schema '{schema_name}' no existe.")

        # Verificar que es un tenant válido (no public)
        public_schema = get_public_schema_name()
        if schema_name == public_schema:
            raise CommandError(
                f"Este comando es para schemas de tenant, no para '{public_schema}'."
            )

        # Verificar que existe el Client
        try:
            client = Client.objects.get(schema_name=schema_name)
            self.stdout.write(
                self.style.SUCCESS(f"OK: Tenant encontrado: {client.nombre} ({schema_name})")
            )
        except Client.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING:  Schema '{schema_name}' existe pero no hay Client asociado."
                )
            )

        # Cambiar al schema del tenant
        connection.set_schema_to_public()
        connection.set_schema(schema_name)

        try:
            with connection.cursor() as cursor:
                if table_name:
                    # Inspeccionar una tabla específica
                    cursor.execute(
                        """
                        SELECT 
                            column_name,
                            data_type,
                            character_maximum_length,
                            is_nullable,
                            column_default
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = %s
                        ORDER BY ordinal_position;
                    """,
                        [table_name],
                    )

                    columns = cursor.fetchall()
                    if not columns:
                        self.stdout.write(
                            self.style.WARNING(
                                f"WARNING:  La tabla '{table_name}' no existe en el schema '{schema_name}'."
                            )
                        )
                        return

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\n📋 Columnas de '{table_name}' en schema '{schema_name}':\n"
                        )
                    )
                    self.stdout.write(
                        f"{'Columna':<30} {'Tipo':<20} {'Longitud':<10} {'Nullable':<10} {'Default':<20}"
                    )
                    self.stdout.write("-" * 90)

                    for col in columns:
                        col_name, data_type, max_length, is_nullable, col_default = col
                        max_len_str = str(max_length) if max_length else "-"
                        nullable_str = "YES" if is_nullable == "YES" else "NO"
                        default_str = str(col_default) if col_default else "-"
                        self.stdout.write(
                            f"{col_name:<30} {data_type:<20} {max_len_str:<10} {nullable_str:<10} {default_str:<20}"
                        )
                else:
                    # Listar todas las tablas y sus columnas
                    cursor.execute("""
                        SELECT 
                            table_name,
                            COUNT(*) as column_count
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                        GROUP BY table_name
                        ORDER BY table_name;
                    """)

                    tables = cursor.fetchall()
                    if not tables:
                        self.stdout.write(
                            self.style.WARNING(
                                f"WARNING:  No hay tablas en el schema '{schema_name}'."
                            )
                        )
                        return

                    self.stdout.write(
                        self.style.SUCCESS(f"\n📋 Tablas en schema '{schema_name}':\n")
                    )
                    self.stdout.write(f"{'Tabla':<40} {'Columnas':<10}")
                    self.stdout.write("-" * 50)

                    for table, col_count in tables:
                        self.stdout.write(f"{table:<40} {col_count:<10}")

                    # Mostrar columnas de facturas_factura si existe
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_schema = current_schema()
                              AND table_name = 'facturas_factura'
                        );
                    """)

                    if cursor.fetchone()[0]:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"\n📋 Columnas de 'facturas_factura' en schema '{schema_name}':\n"
                            )
                        )
                        cursor.execute("""
                            SELECT 
                                column_name,
                                data_type,
                                character_maximum_length,
                                is_nullable,
                                column_default
                            FROM information_schema.columns
                            WHERE table_schema = current_schema()
                              AND table_name = 'facturas_factura'
                            ORDER BY ordinal_position;
                        """)

                        columns = cursor.fetchall()
                        self.stdout.write(
                            f"{'Columna':<30} {'Tipo':<20} {'Longitud':<10} {'Nullable':<10} {'Default':<20}"
                        )
                        self.stdout.write("-" * 90)

                        for col in columns:
                            col_name, data_type, max_length, is_nullable, col_default = col
                            max_len_str = str(max_length) if max_length else "-"
                            nullable_str = "YES" if is_nullable == "YES" else "NO"
                            default_str = str(col_default) if col_default else "-"
                            self.stdout.write(
                                f"{col_name:<30} {data_type:<20} {max_len_str:<10} {nullable_str:<10} {default_str:<20}"
                            )
        finally:
            # Restaurar schema público
            connection.set_schema_to_public()
