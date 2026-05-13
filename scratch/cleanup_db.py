import os
import django
from django.conf import settings
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def cleanup_test_db():
    print("Intentando limpiar base de datos de test...")
    with connection.cursor() as cursor:
        try:
            # En Windows/Postgres, a veces hay que forzar la desconexión
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'test_sintel' AND pid <> pg_backend_pid();")
            print("Conexiones a 'test_sintel' terminadas.")
        except Exception as e:
            print(f"No se pudo terminar conexiones: {e}")

if __name__ == "__main__":
    cleanup_test_db()
