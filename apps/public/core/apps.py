"""
AppConfig para la app core pública.

⚠️ SERVER GUARD: Este AppConfig contiene lógica de validación que se ejecuta
al arrancar la aplicación. Debe ser cuidadoso para no bloquear comandos de
mantenimiento como makemigrations, migrate, etc.
"""
import sys
from django.apps import AppConfig
from django.db import connection


class CoreConfig(AppConfig):
    """
    Configuración de la app core pública.
    
    ⚠️ SERVER GUARD: Contiene validaciones que se ejecutan al arrancar.
    Estas validaciones deben OMITIRSE durante comandos de mantenimiento.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.public.core'
    label = 'public_core'  # ⚠️ CRÍTICO: Label único para evitar conflicto con apps.tenant.core
    verbose_name = 'Core (Público)'

    def ready(self):
        """
        Se ejecuta cuando todas las apps están listas.
        
        ⚠️ CRÍTICO: NO ejecutar validaciones durante comandos de mantenimiento.
        - makemigrations: No hay tablas aún, fallaría
        - migrate/migrate_schemas: Están creando las tablas
        - collectstatic: No necesita BD
        
        ⚠️ REGLA DE ORO: Solo ejecutar validaciones cuando el servidor está corriendo.
        """
        # ⚠️ GUARDA CRÍTICA: Omitir validaciones durante comandos de mantenimiento
        # Estos comandos NO deben ejecutar lógica que requiera BD
        maintenance_commands = {
            'makemigrations',
            'migrate',
            'migrate_schemas',
            'collectstatic',
            'shell',
            'check',
            'test',
            'flush',
            'loaddata',
            'dumpdata',
        }
        
        # Verificar si estamos ejecutando un comando de mantenimiento
        # sys.argv[1] es el comando (ej: 'makemigrations', 'migrate', etc.)
        if len(sys.argv) > 1 and sys.argv[1] in maintenance_commands:
            # Comando de mantenimiento: NO ejecutar validaciones
            return
        
        # Si llegamos aquí, estamos en modo servidor (runserver, gunicorn, etc.)
        # Aquí SÍ podemos ejecutar validaciones, pero con cuidado
        # Por ahora, no ejecutamos validaciones automáticas para evitar problemas
        # Las validaciones deben estar en comandos de management explícitos
        pass
