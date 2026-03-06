"""
Comando de management para crear una nueva empresa (tenant).

Este comando utiliza el servicio de onboarding para crear empresas de forma
segura y reproducible.

⚠️ v2.17: Estandarización de subdominios
- El dominio se construye automáticamente como: {schema_name}.{TENANT_DOMAIN_BASE}
- Ya no se requiere el parámetro 'dominio'

Uso:
    python manage.py crear_empresa "Mi Empresa S.A." "admin@mi-empresa.com"
    python manage.py crear_empresa "Mi Empresa S.A." "admin@mi-empresa.com" --poblar-datos
"""
from django.core.management.base import BaseCommand, CommandError
from apps.services.onboarding.empresa_service import crear_empresa


class Command(BaseCommand):
    help = 'Crea una nueva empresa (tenant) con subdominio automático y usuario administrador'

    def add_arguments(self, parser):
        parser.add_argument(
            'nombre',
            type=str,
            help='Nombre de la empresa',
        )
        parser.add_argument(
            'email_admin',
            type=str,
            help='Email del administrador de la empresa',
        )
        parser.add_argument(
            '--schema-name',
            type=str,
            dest='schema_name',
            help='Schema name (opcional, se genera desde nombre si no se proporciona)',
        )
        parser.add_argument(
            '--poblar-datos',
            action='store_true',
            help='Poblar datos iniciales en el tenant (opcional)',
        )
        parser.add_argument(
            '--on-trial',
            action='store_true',
            default=True,
            help='Marcar empresa como en período de prueba (default: True)',
        )
        parser.add_argument(
            '--no-trial',
            action='store_false',
            dest='on_trial',
            help='Marcar empresa como fuera del período de prueba',
        )

    def handle(self, *args, **options):
        nombre = options['nombre']
        email_admin = options['email_admin']
        schema_name = options.get('schema_name')
        poblar_datos = options.get('poblar_datos', False)
        on_trial = options.get('on_trial', True)

        self.stdout.write(self.style.SUCCESS(f'🚀 Creando empresa: {nombre}'))
        self.stdout.write('=' * 60)
        
        # ⚠️ v2.17: Informar sobre subdominio automático
        from django.conf import settings
        if schema_name:
            dominio_esperado = f"{schema_name}.{settings.TENANT_DOMAIN_BASE}"
        else:
            # El schema_name se generará desde el nombre
            from apps.services.onboarding.empresa_service import generar_schema_name
            schema_generado = generar_schema_name(nombre)
            dominio_esperado = f"{schema_generado}.{settings.TENANT_DOMAIN_BASE}"
        
        self.stdout.write(f'📌 El dominio se creará automáticamente como: {dominio_esperado}')

        try:
            # ⚠️ v2.17: Usar el servicio de onboarding sin parámetro dominio
            resultado = crear_empresa(
                nombre=nombre,
                email_admin=email_admin,
                schema_name=schema_name,
                poblar_datos_iniciales=poblar_datos,
                on_trial=on_trial,
            )

            client = resultado['client']
            domain = resultado['domain']
            user = resultado['user']
            schema_name = resultado['schema_name']

            self.stdout.write(self.style.SUCCESS('\n✅ Empresa creada exitosamente!'))
            self.stdout.write(f'\n📋 Resumen:')
            self.stdout.write(f'   - Nombre: {client.nombre}')
            self.stdout.write(f'   - Schema: {schema_name}')
            self.stdout.write(f'   - Dominio: {domain.domain} (principal: {domain.is_primary})')
            self.stdout.write(f'   - En prueba: {client.on_trial}')
            
            if user:
                self.stdout.write(f'   - Usuario admin: {user.email}')
            else:
                self.stdout.write(self.style.WARNING('   - Usuario admin: No creado (ya existe o error)'))

            self.stdout.write(f'\n🌐 Acceso:')
            self.stdout.write(f'   http://{domain.domain}/admin/')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error al crear empresa: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            raise CommandError(f'Error al crear empresa: {e}')
