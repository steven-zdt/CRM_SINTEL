"""
Comando de management para auditar un tenant y verificar asociaciones de usuarios.

Uso:
    python manage.py auditar_tenant ejemplo
    python manage.py auditar_tenant ejemplo --email admin@ejemplo.com
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client, Domain, TenantMembership
from django_tenants.utils import schema_context

User = get_user_model()


class Command(BaseCommand):
    help = 'Audita un tenant y verifica la asociación de usuarios'

    def add_arguments(self, parser):
        parser.add_argument(
            'schema_name',
            type=str,
            help='Schema name del tenant a auditar (ej: ejemplo, cliente)',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email del usuario a verificar (ej: admin@ejemplo.com)',
        )

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        email_usuario = options.get('email')
        
        self.stdout.write(self.style.SUCCESS(f'\n🔍 AUDITORÍA: Tenant "{schema_name}"'))
        self.stdout.write('=' * 60)
        
        # 1. Verificar tenant
        self.stdout.write(f'\n📋 PASO 1: Verificando tenant "{schema_name}"...')
        try:
            tenant = Client.objects.get(schema_name=schema_name)
            self.stdout.write(self.style.SUCCESS(f'✅ Tenant encontrado:'))
            self.stdout.write(f'   - Schema: {tenant.schema_name}')
            self.stdout.write(f'   - Nombre: {tenant.nombre}')
            self.stdout.write(f'   - Activo: {tenant.is_active}')
            self.stdout.write(f'   - En prueba: {tenant.on_trial}')
        except Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ ERROR: El tenant "{schema_name}" NO existe'))
            return
        
        # 2. Verificar dominio
        self.stdout.write(f'\n📋 PASO 2: Verificando dominio...')
        dominios = Domain.objects.filter(tenant=tenant)
        dominio_principal = dominios.filter(is_primary=True).first()
        
        if dominio_principal:
            self.stdout.write(self.style.SUCCESS(f'✅ Dominio principal encontrado:'))
            self.stdout.write(f'   - Dominio: {dominio_principal.domain}')
            self.stdout.write(f'   - Es principal: {dominio_principal.is_primary}')
            self.stdout.write(f'   - URL esperada: http://{dominio_principal.domain}:8000/')
        else:
            self.stdout.write(self.style.ERROR(f'❌ ERROR: No se encontró dominio principal'))
            return
        
        if dominios.count() > 1:
            self.stdout.write(f'\n   Otros dominios asociados:')
            for d in dominios.exclude(pk=dominio_principal.pk):
                self.stdout.write(f'   - {d.domain} (principal: {d.is_primary})')
        
        # 3. Verificar usuario si se proporciona email
        if email_usuario:
            self.stdout.write(f'\n📋 PASO 3: Verificando usuario "{email_usuario}"...')
            try:
                usuario = User.objects.get(email=email_usuario)
                self.stdout.write(self.style.SUCCESS(f'✅ Usuario encontrado:'))
                self.stdout.write(f'   - ID: {usuario.id}')
                self.stdout.write(f'   - Username: {usuario.username}')
                self.stdout.write(f'   - Email: {usuario.email}')
                self.stdout.write(f'   - Activo: {usuario.is_active}')
                self.stdout.write(f'   - Staff: {usuario.is_staff}')
                self.stdout.write(f'   - Superuser: {usuario.is_superuser}')
                self.stdout.write(f'   - Tiene contraseña: {usuario.has_usable_password()}')
                
                # 4. Verificar TenantMembership
                self.stdout.write(f'\n📋 PASO 4: Verificando TenantMembership...')
                try:
                    membership = TenantMembership.objects.get(
                        client=tenant,
                        user=usuario
                    )
                    self.stdout.write(self.style.SUCCESS(f'✅ Membresía encontrada:'))
                    self.stdout.write(f'   - Rol: {membership.rol}')
                    self.stdout.write(f'   - Es admin principal: {membership.is_primary_admin}')
                    if hasattr(membership, 'is_active'):
                        self.stdout.write(f'   - Activa: {membership.is_active}')
                except TenantMembership.DoesNotExist:
                    self.stdout.write(self.style.ERROR(
                        f'❌ ERROR: NO existe TenantMembership entre el usuario y el tenant'
                    ))
                    self.stdout.write(f'\n💡 SOLUCIÓN: Crear la membresía con:')
                    self.stdout.write(f'   python manage.py shell')
                    self.stdout.write(f'   >>> from apps.public.tenants.models import Client, TenantMembership')
                    self.stdout.write(f'   >>> from django.contrib.auth import get_user_model')
                    self.stdout.write(f'   >>> User = get_user_model()')
                    self.stdout.write(f'   >>> tenant = Client.objects.get(schema_name="{schema_name}")')
                    self.stdout.write(f'   >>> usuario = User.objects.get(email="{email_usuario}")')
                    self.stdout.write(f'   >>> TenantMembership.objects.create(')
                    self.stdout.write(f'   ...     client=tenant,')
                    self.stdout.write(f'   ...     user=usuario,')
                    self.stdout.write(f'   ...     rol="ADMIN",')
                    self.stdout.write(f'   ...     is_primary_admin=True')
                    self.stdout.write(f'   ... )')
                    return
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ ERROR: El usuario "{email_usuario}" NO existe'))
                self.stdout.write(f'\n   Usuarios similares encontrados:')
                usuarios_similares = User.objects.filter(email__icontains='admin')
                if usuarios_similares.exists():
                    for u in usuarios_similares[:5]:
                        self.stdout.write(f'   - {u.email} (username: {u.username})')
                return
        
        # 5. Verificar todas las membresías del tenant
        self.stdout.write(f'\n📋 PASO 5: Verificando todas las membresías del tenant...')
        todas_membresias = TenantMembership.objects.filter(client=tenant)
        self.stdout.write(f'   Total de membresías: {todas_membresias.count()}')
        if todas_membresias.exists():
            for m in todas_membresias:
                admin_mark = ' (ADMIN)' if m.is_primary_admin else ''
                self.stdout.write(f'   - {m.user.email} ({m.user.username}) - Rol: {m.rol}{admin_mark}')
        else:
            self.stdout.write(self.style.WARNING(f'   ⚠️  No hay membresías asociadas a este tenant'))
        
        # 6. Verificar acceso al esquema
        self.stdout.write(f'\n📋 PASO 6: Verificando acceso al esquema...')
        try:
            with schema_context(schema_name):
                from django.db import connection
                current_schema = connection.schema_name
                self.stdout.write(self.style.SUCCESS(f'   ✅ Esquema accesible: {current_schema}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ ERROR al acceder al esquema: {e}'))
            return
        
        # 7. Resumen
        self.stdout.write(f'\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE AUDITORÍA'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'✅ Tenant "{schema_name}": EXISTE')
        self.stdout.write(f'✅ Dominio "{dominio_principal.domain}": EXISTE')
        if email_usuario:
            self.stdout.write(f'✅ Usuario "{email_usuario}": EXISTE')
            self.stdout.write(f'✅ TenantMembership: EXISTE')
        self.stdout.write(f'✅ Esquema accesible: SÍ')
        
        self.stdout.write(f'\n💡 RECOMENDACIONES:')
        self.stdout.write(f'   1. Verificar que la contraseña del usuario sea correcta')
        self.stdout.write(f'   2. Verificar que el usuario tenga permisos de staff si es necesario')
        self.stdout.write(f'   3. Verificar que el tenant esté activo (is_active=True)')
        self.stdout.write(f'   4. Verificar la configuración de CSRF y CORS para el dominio')
        
        self.stdout.write(f'\n🔧 COMANDOS ÚTILES:')
        self.stdout.write(f'   # Cambiar contraseña del usuario:')
        self.stdout.write(f'   python manage.py shell')
        self.stdout.write(f'   >>> from django.contrib.auth import get_user_model')
        self.stdout.write(f'   >>> User = get_user_model()')
        self.stdout.write(f'   >>> u = User.objects.get(email="{email_usuario if email_usuario else "admin@ejemplo.com"}")')
        self.stdout.write(f'   >>> u.set_password("nueva_contraseña")')
        self.stdout.write(f'   >>> u.save()')