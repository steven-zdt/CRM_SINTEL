"""
Comando para corregir historial de migraciones inconsistente.
Útil cuando se cambia AUTH_USER_MODEL después de aplicar migraciones.

Uso:
    python manage.py fix_migration_history
    python manage.py fix_migration_history --fake-accounts
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Corrige el historial de migraciones inconsistente (especialmente cuando se cambia AUTH_USER_MODEL)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fake-accounts',
            action='store_true',
            help='Marcar migraciones de accounts como aplicadas (fake) si las tablas ya existen',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='⚠️ PELIGROSO: Eliminar todo el historial de migraciones (solo para desarrollo)',
        )

    def handle(self, *args, **options):
        fake_accounts = options.get('fake_accounts', False)
        reset = options.get('reset', False)

        if reset:
            self.stdout.write(self.style.WARNING('⚠️  RESETEANDO HISTORIAL DE MIGRACIONES...'))
            
            # En modo no interactivo (Docker), proceder automáticamente
            # En modo interactivo, pedir confirmación
            import sys
            if sys.stdin.isatty():
                confirm = input('¿Estás seguro? Esto eliminará todo el historial. Escribe "yes" para continuar: ')
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.ERROR('Operación cancelada.'))
                    return
            else:
                self.stdout.write(self.style.WARNING('Modo no interactivo: procediendo automáticamente...'))

            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations;")
            self.stdout.write(self.style.SUCCESS('✅ Historial de migraciones eliminado.'))
            self.stdout.write(self.style.WARNING('Ahora ejecuta: python manage.py migrate_schemas --shared --fake-initial'))
            return

        if fake_accounts:
            self.stdout.write('🔍 Verificando tablas de accounts...')
            
            # Verificar si la tabla accounts_user existe
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'accounts_user'
                    );
                """)
                table_exists = cursor.fetchone()[0]

                if table_exists:
                    self.stdout.write(self.style.SUCCESS('✅ Tabla accounts_user existe.'))
                    
                    # Verificar si la migración ya está registrada
                    cursor.execute("""
                        SELECT COUNT(*) FROM django_migrations 
                        WHERE app = 'accounts' AND name = '0001_initial';
                    """)
                    migration_exists = cursor.fetchone()[0] > 0

                    if not migration_exists:
                        self.stdout.write('📝 Marcando migración accounts.0001_initial como aplicada (fake)...')
                        recorder = MigrationRecorder(connection)
                        recorder.record_applied('accounts', '0001_initial')
                        self.stdout.write(self.style.SUCCESS('✅ Migración accounts.0001_initial marcada como aplicada.'))
                    else:
                        self.stdout.write(self.style.WARNING('ℹ️  La migración accounts.0001_initial ya está registrada.'))
                else:
                    self.stdout.write(self.style.ERROR('❌ La tabla accounts_user no existe. Ejecuta migraciones primero.'))
                    raise CommandError('Tabla accounts_user no existe. Ejecuta: python manage.py migrate_schemas --shared')
        else:
            self.stdout.write(self.style.WARNING('💡 Opciones disponibles:'))
            self.stdout.write('  --fake-accounts: Marcar migraciones de accounts como aplicadas si las tablas existen')
            self.stdout.write('  --reset: ⚠️  Eliminar todo el historial de migraciones (solo desarrollo)')
            self.stdout.write('')
            self.stdout.write('Ejemplo: python manage.py fix_migration_history --fake-accounts')
