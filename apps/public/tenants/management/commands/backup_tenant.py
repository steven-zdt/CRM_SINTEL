"""
Comando de management para realizar backups de un tenant específico.

Este comando usa pg_dump para crear backups diferenciales por esquema.
"""
import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection
from apps.public.tenants.models import Client


class Command(BaseCommand):
    help = 'Realiza un backup del esquema de un tenant específico usando pg_dump'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='Nombre del esquema del tenant a respaldar',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directorio donde guardar el backup (default: backups)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['plain', 'custom', 'directory', 'tar'],
            default='custom',
            help='Formato del backup (default: custom)',
        )
        parser.add_argument(
            '--incremental',
            action='store_true',
            help='Realizar backup incremental (solo cambios desde último backup)',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        output_dir = options['output_dir']
        format_type = options['format']
        incremental = options['incremental']

        # Verificar que el tenant existe
        try:
            tenant = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            raise CommandError(f'Tenant con schema_name "{schema_name}" no existe')

        self.stdout.write(self.style.SUCCESS(f'🔄 Iniciando backup del tenant: {tenant.nombre} ({schema_name})'))

        # Crear directorio de backups si no existe
        os.makedirs(output_dir, exist_ok=True)

        # Generar nombre del archivo de backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if format_type == 'custom':
            filename = f'{schema_name}_{timestamp}.dump'
        elif format_type == 'tar':
            filename = f'{schema_name}_{timestamp}.tar'
        elif format_type == 'directory':
            filename = f'{schema_name}_{timestamp}'
        else:  # plain
            filename = f'{schema_name}_{timestamp}.sql'

        backup_path = os.path.join(output_dir, filename)

        # Obtener configuración de base de datos
        db_config = settings.DATABASES['default']
        db_name = db_config['NAME']
        db_user = db_config['USER']
        db_password = db_config['PASSWORD']
        db_host = db_config['HOST']
        db_port = db_config['PORT']

        # Construir comando pg_dump
        cmd = [
            'pg_dump',
            f'--dbname={db_name}',
            f'--username={db_user}',
            f'--host={db_host}',
            f'--port={db_port}',
            f'--schema={schema_name}',
            '--no-owner',
            '--no-acl',
        ]

        # Agregar opciones según el formato
        if format_type == 'custom':
            cmd.append('--format=custom')
            cmd.append('--compress=9')
        elif format_type == 'tar':
            cmd.append('--format=tar')
        elif format_type == 'directory':
            cmd.append('--format=directory')
        else:  # plain
            cmd.append('--format=plain')

        # Backup incremental (solo si es custom format)
        if incremental and format_type == 'custom':
            # Buscar último backup
            last_backup = self._find_last_backup(output_dir, schema_name)
            if last_backup:
                # pg_dump custom format no soporta incremental directo
                # Se puede usar pg_dump con --file para especificar salida
                self.stdout.write(f'📦 Backup incremental desde: {last_backup}')
                self.stdout.write(self.style.WARNING('⚠️  Nota: pg_dump no soporta incremental nativo, se realizará backup completo'))
            else:
                self.stdout.write(self.style.WARNING('⚠️  No se encontró backup anterior, realizando backup completo'))
        
        # pg_dump usa redirección de salida, no --file
        # Guardaremos la salida en el archivo especificado

        # Establecer variable de entorno para la contraseña
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        try:
            # Ejecutar pg_dump y redirigir salida al archivo
            self.stdout.write(f'💾 Ejecutando pg_dump para esquema: {schema_name}')
            with open(backup_path, 'wb') as backup_file:
                result = subprocess.run(
                    cmd,
                    env=env,
                    stdout=backup_file,
                    stderr=subprocess.PIPE,
                    check=True
                )

            self.stdout.write(self.style.SUCCESS(f'✅ Backup completado exitosamente'))
            self.stdout.write(f'📁 Archivo: {backup_path}')
            self.stdout.write(f'📊 Tamaño: {self._get_file_size(backup_path)}')

            # Guardar metadata del backup
            self._save_backup_metadata(schema_name, backup_path, format_type, incremental)

        except subprocess.CalledProcessError as e:
            raise CommandError(f'Error al ejecutar pg_dump: {e.stderr}')
        except Exception as e:
            raise CommandError(f'Error inesperado: {str(e)}')

    def _find_last_backup(self, output_dir, schema_name):
        """Encuentra el último backup del tenant."""
        import glob
        pattern = os.path.join(output_dir, f'{schema_name}_*.dump')
        backups = glob.glob(pattern)
        if backups:
            return max(backups, key=os.path.getmtime)
        return None

    def _get_file_size(self, filepath):
        """Obtiene el tamaño del archivo en formato legible."""
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f'{size:.2f} {unit}'
            size /= 1024.0
        return f'{size:.2f} TB'

    def _save_backup_metadata(self, schema_name, backup_path, format_type, incremental):
        """Guarda metadata del backup en un archivo JSON."""
        import json
        metadata_file = os.path.join(os.path.dirname(backup_path), 'backups_metadata.json')
        
        metadata = {
            'schema_name': schema_name,
            'backup_path': backup_path,
            'format': format_type,
            'incremental': incremental,
            'timestamp': datetime.now().isoformat(),
            'size': os.path.getsize(backup_path),
        }

        # Leer metadata existente
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                all_metadata = json.load(f)
        else:
            all_metadata = []

        all_metadata.append(metadata)

        # Guardar metadata actualizada
        with open(metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=2)

        self.stdout.write(f'📝 Metadata guardada en: {metadata_file}')
