"""
Comando de management para restaurar un backup de tenant.

Este comando usa pg_restore para restaurar backups de esquemas.
"""

import os
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.public.tenants.models import Client


class Command(BaseCommand):
    help = "Restaura un backup de un tenant específico usando pg_restore"

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            type=str,
            help="Ruta al archivo de backup a restaurar",
        )
        parser.add_argument(
            "--schema-name",
            type=str,
            help="Nombre del esquema donde restaurar (default: extraído del nombre del archivo)",
        )
        parser.add_argument(
            "--create-schema",
            action="store_true",
            help="Crear el esquema si no existe",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Limpiar objetos existentes antes de restaurar",
        )

    def handle(self, *args, **options):
        backup_file = options["backup_file"]
        schema_name = options.get("schema_name")
        create_schema = options["create_schema"]
        clean = options["clean"]

        # Verificar que el archivo existe
        if not os.path.exists(backup_file):
            raise CommandError(f"Archivo de backup no encontrado: {backup_file}")

        # Extraer schema_name del nombre del archivo si no se proporciona
        if not schema_name:
            filename = os.path.basename(backup_file)
            # Formato esperado: schema_name_timestamp.dump
            schema_name = filename.split("_")[0]

        self.stdout.write(
            self.style.SUCCESS(f"🔄 Iniciando restauración del tenant: {schema_name}")
        )

        # Verificar que el tenant existe (o crearlo si se solicita)
        try:
            tenant = Client.objects.get(schema_name=schema_name)
            self.stdout.write(f"OK: Tenant encontrado: {tenant.nombre}")
        except Client.DoesNotExist:
            if create_schema:
                self.stdout.write(
                    self.style.WARNING("WARNING:  Tenant no existe, se creará el esquema")
                )
            else:
                raise CommandError(
                    f'Tenant con schema_name "{schema_name}" no existe. Use --create-schema para crearlo.'
                )

        # Obtener configuración de base de datos
        db_config = settings.DATABASES["default"]
        db_name = db_config["NAME"]
        db_user = db_config["USER"]
        db_password = db_config["PASSWORD"]
        db_host = db_config["HOST"]
        db_port = db_config["PORT"]

        # Determinar formato del backup
        backup_format = self._detect_backup_format(backup_file)

        # Construir comando pg_restore
        if backup_format == "custom" or backup_format == "tar" or backup_format == "directory":
            cmd = ["pg_restore"]
        else:  # plain SQL
            cmd = ["psql"]

        cmd.extend(
            [
                f"--dbname={db_name}",
                f"--username={db_user}",
                f"--host={db_host}",
                f"--port={db_port}",
            ]
        )

        if backup_format != "plain":
            cmd.extend(
                [
                    f"--schema={schema_name}",
                    "--no-owner",
                    "--no-acl",
                ]
            )

            if clean:
                cmd.append("--clean")

            cmd.append(backup_file)
        else:
            # Para SQL plain, usar psql directamente
            cmd.extend(
                [
                    "--set",
                    f"search_path={schema_name}",
                ]
            )

        # Establecer variable de entorno para la contraseña
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        try:
            # Ejecutar restauración
            self.stdout.write(f"💾 Ejecutando restauración para esquema: {schema_name}")

            if backup_format == "plain":
                # Para SQL plain, leer el archivo y ejecutarlo con psql
                with open(backup_file, encoding="utf-8") as f:
                    sql_content = f.read()
                    # Agregar comando para establecer search_path
                    sql_content = f"SET search_path TO {schema_name};\n" + sql_content

                    result = subprocess.run(
                        cmd, env=env, input=sql_content, capture_output=True, text=True, check=True
                    )
            else:
                # Para otros formatos, usar pg_restore
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

            self.stdout.write(self.style.SUCCESS("OK: Restauración completada exitosamente"))

        except subprocess.CalledProcessError as e:
            raise CommandError(f"Error al ejecutar restauración: {e.stderr}")
        except Exception as e:
            raise CommandError(f"Error inesperado: {str(e)}")

    def _detect_backup_format(self, backup_file):
        """Detecta el formato del backup basado en la extensión."""
        ext = os.path.splitext(backup_file)[1].lower()
        if ext == ".dump":
            return "custom"
        elif ext == ".tar":
            return "tar"
        elif ext == ".sql":
            return "plain"
        elif os.path.isdir(backup_file):
            return "directory"
        else:
            # Intentar detectar por contenido
            with open(backup_file, "rb") as f:
                header = f.read(5)
                if header.startswith(b"PGDMP"):
                    return "custom"
                elif header.startswith(b"BEGIN"):
                    return "plain"
            return "custom"  # Default
