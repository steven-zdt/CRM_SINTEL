from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import ProgrammingError, connection


class Command(BaseCommand):
    help = "Delete a user row by id using raw SQL to avoid ORM cascade touching tenant tables."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int, help="ID of the user to delete")

    def handle(self, *args, **options):
        uid = options["user_id"]
        User = get_user_model()
        table = User._meta.db_table
        # 1) Remove rows in public tables that reference the user
        public_cleanup_sqls = [
            ("DELETE FROM tenants_tenantmembership WHERE user_id = %s", [uid]),
            ("DELETE FROM token_blacklist_outstandingtoken WHERE user_id = %s", [uid]),
            ("DELETE FROM console_consoleactionlog WHERE user_id = %s", [uid]),
            ("DELETE FROM django_admin_log WHERE user_id = %s", [uid]),
        ]

        with connection.cursor() as cur:
            for sql, params in public_cleanup_sqls:
                try:
                    cur.execute(sql, params)
                    self.stdout.write(self.style.NOTICE(f"EXECUTED: {sql} -> {cur.rowcount}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"FAILED: {sql} -> {e}"))

            # token_blacklist has chained relations: blacklistedtoken -> outstandingtoken -> user
            try:
                cur.execute(
                    "DELETE FROM token_blacklist_blacklistedtoken WHERE token_id IN (SELECT id FROM token_blacklist_outstandingtoken WHERE user_id = %s)",
                    [uid],
                )
                self.stdout.write(self.style.NOTICE(f"DELETED blacklistedtoken -> {cur.rowcount}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"FAILED deleting blacklistedtoken: {e}"))

            try:
                cur.execute(
                    "DELETE FROM token_blacklist_outstandingtoken WHERE user_id = %s", [uid]
                )
                self.stdout.write(self.style.NOTICE(f"DELETED outstandingtoken -> {cur.rowcount}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"FAILED deleting outstandingtoken: {e}"))

            # 2) Attempt to nullify tenant profiles in each tenant schema
            try:
                from apps.public.tenants.models import Client

                schemas = [c["schema_name"] for c in Client.objects.values("schema_name")]
            except Exception:
                schemas = []

            for schema in schemas:
                try:
                    cur.execute(f'SET search_path TO "{schema}"')
                    # Cascade-delete tenant profile rows referencing the user in this schema
                    cur.execute("DELETE FROM perfil_tenantprofile WHERE user_id = %s", [uid])
                except ProgrammingError:
                    # table may not exist in this schema; ignore
                    pass
                except Exception:
                    pass

            # 3) Finally attempt to delete the user row from the public user table
            try:
                cur.execute(f'DELETE FROM "{table}" WHERE id = %s', [uid])
                self.stdout.write(self.style.SUCCESS(f"RAW_DELETED {uid}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"RAW_DELETE_ERROR: {e}"))
                raise
