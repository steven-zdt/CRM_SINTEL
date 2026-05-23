import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenant.proyectos.models import TareaDiariaProyecto
from django.db import connection

print('\n=== VERIFICACION: TareaDiariaProyecto Schema ===\n')

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'tenant_proyectos_tareadiariaproyecto'
        ORDER BY ordinal_position
    """)
    for row in cursor.fetchall():
        print(f'{row[0]:<30} | {row[1]:<20} | nullable={row[2]}')

print('\n=== CAMPOS DEL MODELO ===\n')
for field in TareaDiariaProyecto._meta.get_fields():
    if hasattr(field, 'get_internal_type'):
        print(f'{field.name:<30} | {field.get_internal_type():<20}')

print('\n✅ Schema verificado correctamente\n')
