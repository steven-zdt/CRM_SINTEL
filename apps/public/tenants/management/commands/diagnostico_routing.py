"""
Comando de diagnóstico para verificar el routing de tenants.

Verifica si django-tenants puede identificar correctamente un tenant
cuando se accede con puerto en el dominio.
"""
from django.core.management.base import BaseCommand
from apps.public.tenants.models import Client, Domain
from django_tenants.utils import get_tenant_model


class Command(BaseCommand):
    help = 'Diagnostica problemas de routing de tenants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            required=True,
            help='Schema name del tenant a verificar (ej: ejemplo, cliente)'
        )

    def handle(self, *args, **options):
        schema_name = options['schema']
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"Diagnóstico de routing para tenant: {schema_name}")
        self.stdout.write("=" * 60)
        
        # 1. Verificar tenant
        self.stdout.write("\n1. Verificando tenant...")
        tenant = Client.objects.filter(schema_name=schema_name).first()
        if tenant:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Tenant encontrado: {tenant.nombre} (schema: {tenant.schema_name})"
            ))
            self.stdout.write(f"   - Activo: {tenant.is_active}")
            self.stdout.write(f"   - En prueba: {tenant.on_trial}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Tenant '{schema_name}' NO encontrado"))
            return
        
        # 2. Verificar dominios
        self.stdout.write("\n2. Verificando dominios...")
        domains = Domain.objects.filter(tenant=tenant)
        domain_list = [d.domain for d in domains]
        self.stdout.write(f"   Dominios encontrados: {domain_list}")
        
        if not domain_list:
            self.stdout.write(self.style.ERROR("❌ No hay dominios configurados para este tenant"))
            return
        
        # 3. Simular matching de django-tenants
        self.stdout.write("\n3. Simulando matching de django-tenants...")
        DomainModel = Domain  # Usar el modelo Domain directamente
        
        # Probar diferentes variantes del hostname
        hostnames_to_test = [
            f'{domain_list[0]}:8000',
            domain_list[0],
            f'{domain_list[0].upper()}:8000',
            domain_list[0].upper(),
        ]
        
        for hostname in hostnames_to_test:
            # django-tenants normalmente hace split(':')[0] para extraer el hostname
            hostname_clean = hostname.split(':')[0].lower()
            self.stdout.write(f"\n   Probando: {hostname}")
            self.stdout.write(f"   Hostname limpio: {hostname_clean}")
            
            # Buscar dominio exacto
            domain_exact = DomainModel.objects.filter(domain=hostname).first()
            if domain_exact:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Dominio encontrado (exacto): {domain_exact.domain}"
                ))
                continue
            
            # Buscar dominio sin puerto
            domain_clean = DomainModel.objects.filter(domain=hostname_clean).first()
            if domain_clean:
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ Dominio encontrado (sin puerto): {domain_clean.domain}"
                ))
                self.stdout.write(self.style.WARNING(
                    "   ⚠️  django-tenants debería usar este dominio automáticamente"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Dominio NO encontrado"))
        
        # 4. Recomendación
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("4. Recomendación:")
        self.stdout.write("   django-tenants debería extraer automáticamente el hostname")
        self.stdout.write("   sin puerto del HTTP_HOST. Si el problema persiste:")
        self.stdout.write("   1. Verifica que el middleware TenantMainMiddleware esté activo")
        self.stdout.write("   2. Verifica que ALLOWED_HOSTS incluya el dominio")
        self.stdout.write("   3. Verifica los logs del servidor para ver qué hostname recibe")
