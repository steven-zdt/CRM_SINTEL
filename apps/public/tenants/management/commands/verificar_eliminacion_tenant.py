"""
Comando de management para verificar si un tenant ha sido eliminado completamente.

Uso:
    python manage.py verificar_eliminacion_tenant ejemplo
    python manage.py verificar_eliminacion_tenant ejemplo --domain ejemplo.sintel.com
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import schema_exists, get_public_schema_name, schema_context
from apps.public.tenants.models import Client, Domain, TenantMembership


class Command(BaseCommand):
    help = 'Verifica si un tenant ha sido eliminado completamente de la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='Schema name del tenant a verificar (ej: ejemplo, cliente)',
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Dominio del tenant a verificar (ej: ejemplo.sintel.com)',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        domain_name = options.get('domain') or f"{schema_name}.sintel.com"
        
        self.stdout.write(self.style.SUCCESS(f'\n🔍 VERIFICACIÓN: Eliminación del Tenant "{schema_name}"'))
        self.stdout.write('=' * 60)
        
        # 1. Verificar Client
        self.stdout.write(f'\n📋 PASO 1: Verificando Client (schema_name="{schema_name}")...')
        try:
            client = Client.objects.get(schema_name=schema_name)
            self.stdout.write(self.style.ERROR(f'❌ ERROR: El Client "{schema_name}" AÚN EXISTE'))
            self.stdout.write(f'   - ID: {client.pk}')
            self.stdout.write(f'   - Nombre: {client.nombre}')
            self.stdout.write(f'   - Activo: {client.is_active}')
            self.stdout.write(f'   - Creado: {client.created_on}')
            client_exists = True
        except Client.DoesNotExist:
            self.stdout.write(self.style.SUCCESS(f'✅ El Client "{schema_name}" NO existe (eliminado correctamente)'))
            client_exists = False
        
        # 2. Verificar Domain
        self.stdout.write(f'\n📋 PASO 2: Verificando Domain (domain="{domain_name}")...')
        try:
            domain = Domain.objects.get(domain=domain_name)
            self.stdout.write(self.style.ERROR(f'❌ ERROR: El Domain "{domain_name}" AÚN EXISTE'))
            self.stdout.write(f'   - ID: {domain.pk}')
            self.stdout.write(f'   - Tenant: {domain.tenant.schema_name if domain.tenant else "None"}')
            self.stdout.write(f'   - Es principal: {domain.is_primary}')
            domain_exists = True
        except Domain.DoesNotExist:
            self.stdout.write(self.style.SUCCESS(f'✅ El Domain "{domain_name}" NO existe (eliminado correctamente)'))
            domain_exists = False
        
        # 3. Verificar TenantMembership
        self.stdout.write(f'\n📋 PASO 3: Verificando TenantMembership asociadas...')
        if client_exists:
            memberships = TenantMembership.objects.filter(client=client)
            if memberships.exists():
                self.stdout.write(self.style.ERROR(f'❌ ERROR: Existen {memberships.count()} TenantMembership asociadas:'))
                for m in memberships:
                    self.stdout.write(f'   - Usuario: {m.user.email} ({m.user.username}) - Rol: {m.rol}')
                membership_exists = True
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ No hay TenantMembership asociadas al tenant "{schema_name}"'))
                membership_exists = False
        else:
            # Si el client no existe, verificar si hay membresías huérfanas
            memberships = TenantMembership.objects.filter(client__schema_name=schema_name)
            if memberships.exists():
                self.stdout.write(self.style.WARNING(f'⚠️  ADVERTENCIA: Existen {memberships.count()} TenantMembership huérfanas (client eliminado pero membresías quedaron):'))
                for m in memberships:
                    self.stdout.write(f'   - Usuario: {m.user.email} ({m.user.username}) - Rol: {m.rol}')
                membership_exists = True
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ No hay TenantMembership asociadas al tenant "{schema_name}"'))
                membership_exists = False
        
        # 4. Verificar esquema en PostgreSQL
        self.stdout.write(f'\n📋 PASO 4: Verificando esquema en PostgreSQL (schema="{schema_name}")...')
        try:
            schema_exist = schema_exists(schema_name)
            if schema_exist:
                self.stdout.write(self.style.ERROR(f'❌ ERROR: El esquema "{schema_name}" AÚN EXISTE en PostgreSQL'))
                
                # Intentar verificar si hay tablas en el esquema
                try:
                    with schema_context(schema_name):
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                SELECT table_name 
                                FROM information_schema.tables 
                                WHERE table_schema = %s
                                ORDER BY table_name
                            """, [schema_name])
                            tables = cursor.fetchall()
                            
                            if tables:
                                self.stdout.write(self.style.WARNING(f'   ⚠️  El esquema contiene {len(tables)} tablas:'))
                                for table in tables[:10]:  # Mostrar solo las primeras 10
                                    self.stdout.write(f'      - {table[0]}')
                                if len(tables) > 10:
                                    self.stdout.write(f'      ... y {len(tables) - 10} más')
                            else:
                                self.stdout.write(self.style.WARNING(f'   ⚠️  El esquema existe pero está vacío (sin tablas)'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  No se pudo acceder al esquema: {e}'))
                
                schema_exists_flag = True
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ El esquema "{schema_name}" NO existe en PostgreSQL (eliminado correctamente)'))
                schema_exists_flag = False
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Error al verificar el esquema: {e}'))
            schema_exists_flag = None
        
        # 5. Verificar otros dominios relacionados
        self.stdout.write(f'\n📋 PASO 5: Verificando otros dominios relacionados...')
        related_domains = Domain.objects.filter(domain__icontains=f'{schema_name}.')
        if related_domains.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  ADVERTENCIA: Existen {related_domains.count()} dominios relacionados:'))
            for d in related_domains:
                self.stdout.write(f'   - {d.domain} (tenant: {d.tenant.schema_name if d.tenant else "None"})')
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ No hay otros dominios relacionados con "{schema_name}"'))
        
        # Resumen final
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE VERIFICACIÓN'))
        self.stdout.write('=' * 60)
        
        if client_exists or domain_exists or membership_exists or schema_exists_flag:
            self.stdout.write(self.style.ERROR('❌ EL TENANT NO HA SIDO ELIMINADO COMPLETAMENTE'))
            self.stdout.write('\n📋 Estado actual:')
            self.stdout.write(f'   - Client existe: {"SÍ" if client_exists else "NO"}')
            self.stdout.write(f'   - Domain existe: {"SÍ" if domain_exists else "NO"}')
            self.stdout.write(f'   - TenantMembership existen: {"SÍ" if membership_exists else "NO"}')
            self.stdout.write(f'   - Esquema en PostgreSQL existe: {"SÍ" if schema_exists_flag else "NO" if schema_exists_flag is not None else "ERROR"}')
            
            self.stdout.write('\n🔧 COMANDOS PARA ELIMINAR COMPLETAMENTE:')
            self.stdout.write('   python manage.py shell')
            self.stdout.write('   >>> from apps.public.tenants.models import Client, Domain, TenantMembership')
            self.stdout.write('   >>> from django_tenants.utils import schema_context')
            self.stdout.write('   >>> from django.db import connection')
            self.stdout.write('   >>>')
            if client_exists:
                self.stdout.write('   >>> # 1. Eliminar TenantMembership')
                self.stdout.write(f'   >>> client = Client.objects.get(schema_name="{schema_name}")')
                self.stdout.write('   >>> TenantMembership.objects.filter(client=client).delete()')
                self.stdout.write('   >>>')
                self.stdout.write('   >>> # 2. Eliminar Domain')
                self.stdout.write('   >>> Domain.objects.filter(tenant=client).delete()')
                self.stdout.write('   >>>')
                self.stdout.write('   >>> # 3. Eliminar Client (esto puede eliminar el esquema si auto_drop_schema=True)')
                self.stdout.write('   >>> client.delete()')
                self.stdout.write('   >>>')
            if schema_exists_flag:
                self.stdout.write('   >>> # 4. Eliminar esquema manualmente si aún existe')
                self.stdout.write('   >>> with connection.cursor() as cursor:')
                self.stdout.write(f'   ...     cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")')
                self.stdout.write('   >>>')
            self.stdout.write('   >>> # 5. Verificar eliminación')
            self.stdout.write('   >>> from django_tenants.utils import schema_exists')
            self.stdout.write(f'   >>> print(f"Esquema existe: {{schema_exists(\'{schema_name}\')}}")')
        else:
            self.stdout.write(self.style.SUCCESS('✅ EL TENANT HA SIDO ELIMINADO COMPLETAMENTE'))
            self.stdout.write('\n📋 Verificación completa:')
            self.stdout.write('   ✅ Client eliminado')
            self.stdout.write('   ✅ Domain eliminado')
            self.stdout.write('   ✅ TenantMembership eliminadas')
            self.stdout.write('   ✅ Esquema en PostgreSQL eliminado')
        
        self.stdout.write('=' * 60 + '\n')