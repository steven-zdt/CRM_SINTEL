"""
Management command para resetear un owner a contraseña no usable y generar token de activación.

⚠️ v2.30: API-First - Este comando facilita pruebas del flujo de activación.

Uso:
    python manage.py owner_activation_reset_and_token \
        --email owner@cliente.com \
        --tenant-domain cliente.sintel.com \
        --ttl-minutes 60

O por schema:
    python manage.py owner_activation_reset_and_token \
        --email owner@cliente.com \
        --schema cliente \
        --ttl-minutes 60
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, get_public_schema_name
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.services.invitations import generate_invitation_token, build_activation_url

User = get_user_model()


class Command(BaseCommand):
    help = 'Resetea un owner a contraseña no usable y genera token de activación (v2.30 API-First)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Email del owner a resetear'
        )
        parser.add_argument(
            '--tenant-domain',
            type=str,
            help='Dominio del tenant (ej: cliente.sintel.com)'
        )
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema name del tenant (ej: cliente)'
        )
        parser.add_argument(
            '--ttl-minutes',
            type=int,
            default=60,
            help='TTL del token en minutos (default: 60)'
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        tenant_domain = options.get('tenant_domain')
        schema_name = options.get('schema')
        ttl_minutes = options['ttl_minutes']

        # Validar que se proporcione domain o schema
        if not tenant_domain and not schema_name:
            raise CommandError('Debe proporcionar --tenant-domain o --schema')

        # Resolver tenant
        with schema_context(get_public_schema_name()):
            tenant = None
            
            if tenant_domain:
                # Buscar por dominio
                domain_obj = Domain.objects.filter(domain=tenant_domain, is_primary=True).first()
                if not domain_obj:
                    raise CommandError(f'No se encontró tenant con dominio: {tenant_domain}')
                tenant = domain_obj.tenant
            else:
                # Buscar por schema
                tenant = Client.objects.filter(schema_name=schema_name).first()
                if not tenant:
                    raise CommandError(f'No se encontró tenant con schema: {schema_name}')
            
            # Obtener dominio primario si no se proporcionó
            if not tenant_domain:
                domain_obj = Domain.objects.filter(tenant=tenant, is_primary=True).first()
                if not domain_obj:
                    raise CommandError(f'Tenant {tenant.schema_name} no tiene dominio primario')
                tenant_domain = domain_obj.domain

            # Buscar usuario
            user = User.objects.filter(email=email).first()
            if not user:
                raise CommandError(f'No se encontró usuario con email: {email}')

            # Verificar membresía
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True
            ).first()
            
            if not membership:
                raise CommandError(
                    f'El usuario {email} no tiene membresía activa en el tenant {tenant.schema_name}'
                )

            # Resetear a contraseña no usable
            user.set_unusable_password()
            user.save(update_fields=['password'])
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Usuario {email} reseteado a contraseña no usable'
                )
            )

            # Generar token de activación
            ttl_hours = ttl_minutes / 60.0
            token = generate_invitation_token(
                user_id=user.id,
                tenant_id=tenant.id,
                ttl_hours=ttl_hours
            )

            # Construir URL de activación
            activation_url = build_activation_url(tenant_domain, token)

            # Imprimir información
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS('TOKEN DE ACTIVACIÓN GENERADO'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            self.stdout.write(f'Usuario: {email}')
            self.stdout.write(f'Tenant: {tenant.nombre} ({tenant.schema_name})')
            self.stdout.write(f'Dominio: {tenant_domain}')
            self.stdout.write(f'TTL: {ttl_minutes} minutos ({ttl_hours:.2f} horas)')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Token:'))
            self.stdout.write(f'  {token}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('URL de activación (API-First v2.30):'))
            self.stdout.write(f'  {activation_url}')
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ Listo para pruebas'))
            self.stdout.write('')
            self.stdout.write('Pruebas sugeridas:')
            self.stdout.write(f'  1. GET {activation_url}')
            self.stdout.write(f'     → Debe retornar 200 con información del usuario/tenant')
            self.stdout.write(f'  2. POST {activation_url}')
            self.stdout.write(f'     → Con password1 y password2 para activar')
            self.stdout.write('')
