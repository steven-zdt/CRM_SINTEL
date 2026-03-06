"""
Comando de management para auditar todos los tenants y verificar que:
1. Tienen dominio activo
2. El dominio principal existe (is_primary=True)
3. El tenant está activo (is_active=True)
4. El esquema PostgreSQL existe
5. El acceso web funciona (simulación HTTP)
"""
from django.core.management.base import BaseCommand
from django.test import Client as TestClient
from django.db import connection
from django_tenants.utils import schema_exists, get_public_schema_name
from django.conf import settings

from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = 'Audita todos los tenants y verifica que tienen dominio activo y acceso web funcionando.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Auditar solo un tenant específico por schema_name',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Intentar corregir problemas encontrados automáticamente',
        )
        parser.add_argument(
            '--test-web',
            action='store_true',
            help='Probar acceso web real (simula petición HTTP)',
        )

    def handle(self, *args, **options):
        schema_filter = options.get('schema')
        fix_issues = options.get('fix', False)
        test_web = options.get('test_web', False)

        self.stdout.write("=" * 80)
        self.stdout.write("🔍 AUDITORÍA DE DOMINIOS Y ACCESO WEB DE TENANTS")
        self.stdout.write("=" * 80)
        self.stdout.write("")

        # Obtener tenants a auditar
        if schema_filter:
            try:
                tenants = [Client.objects.get(schema_name=schema_filter)]
            except Client.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"❌ Tenant '{schema_filter}' no encontrado.")
                )
                return
        else:
            tenants = Client.objects.all().order_by('schema_name')

        if not tenants:
            self.stdout.write(self.style.WARNING("⚠️  No se encontraron tenants para auditar."))
            return

        # Estadísticas
        total_tenants = len(tenants)
        tenants_ok = 0
        tenants_with_issues = 0
        issues_found = []

        public_schema = get_public_schema_name()

        for tenant in tenants:
            self.stdout.write("")
            self.stdout.write("-" * 80)
            self.stdout.write(f"📋 Tenant: {tenant.nombre} (schema: {tenant.schema_name})")
            self.stdout.write("-" * 80)

            tenant_issues = []
            tenant_fixed = False

            # 1. Verificar que el tenant esté activo
            if not tenant.is_active:
                issue = "❌ Tenant INACTIVO (is_active=False)"
                tenant_issues.append(issue)
                self.stdout.write(self.style.ERROR(issue))
                if fix_issues and tenant.schema_name != public_schema:
                    tenant.is_active = True
                    tenant.save()
                    tenant_fixed = True
                    self.stdout.write(self.style.SUCCESS("   ✅ Corregido: Tenant activado"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Tenant activo"))

            # 2. Verificar que existe el esquema PostgreSQL
            if not schema_exists(tenant.schema_name):
                issue = f"❌ Esquema PostgreSQL '{tenant.schema_name}' NO existe"
                tenant_issues.append(issue)
                self.stdout.write(self.style.ERROR(issue))
                # No se puede corregir automáticamente (requiere migraciones)
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ Esquema PostgreSQL '{tenant.schema_name}' existe"))

            # 3. Verificar dominios
            domains = Domain.objects.filter(tenant=tenant)
            primary_domain = domains.filter(is_primary=True).first()

            if not domains.exists():
                issue = "❌ NO tiene dominios asociados"
                tenant_issues.append(issue)
                self.stdout.write(self.style.ERROR(issue))
                
                if fix_issues:
                    # Intentar crear dominio principal
                    domain_name = f"{tenant.schema_name}.{settings.TENANT_DOMAIN_BASE}"
                    try:
                        Domain.objects.create(
                            domain=domain_name,
                            tenant=tenant,
                            is_primary=True
                        )
                        tenant_fixed = True
                        self.stdout.write(
                            self.style.SUCCESS(f"   ✅ Corregido: Dominio '{domain_name}' creado")
                        )
                        primary_domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"   ❌ Error al crear dominio: {e}")
                        )
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ Tiene {domains.count()} dominio(s)"))

            # 4. Verificar dominio principal
            if not primary_domain:
                issue = "❌ NO tiene dominio principal (is_primary=True)"
                tenant_issues.append(issue)
                self.stdout.write(self.style.ERROR(issue))
                
                if fix_issues:
                    # Marcar el primer dominio como principal
                    first_domain = domains.first()
                    if first_domain:
                        # Desmarcar otros como principales
                        Domain.objects.filter(tenant=tenant).update(is_primary=False)
                        first_domain.is_primary = True
                        first_domain.save()
                        tenant_fixed = True
                        self.stdout.write(
                            self.style.SUCCESS(f"   ✅ Corregido: '{first_domain.domain}' marcado como principal")
                        )
                        primary_domain = first_domain
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Dominio principal: {primary_domain.domain}")
                )

            # 5. Verificar formato del dominio (debe ser subdominio)
            if primary_domain:
                expected_domain = f"{tenant.schema_name}.{settings.TENANT_DOMAIN_BASE}"
                if primary_domain.domain != expected_domain:
                    issue = f"⚠️  Dominio '{primary_domain.domain}' no coincide con formato esperado '{expected_domain}'"
                    tenant_issues.append(issue)
                    self.stdout.write(self.style.WARNING(issue))
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Formato de dominio correcto: {expected_domain}")
                    )

            # 6. Probar acceso web (simulación HTTP)
            if test_web and primary_domain:
                try:
                    # Simular petición HTTP al dominio del tenant
                    test_client = TestClient()
                    response = test_client.get('/', HTTP_HOST=primary_domain.domain, follow=False)
                    
                    # Verificar que la respuesta no sea 404 (tenant no encontrado)
                    if response.status_code == 404:
                        issue = f"❌ Acceso web falla: HTTP 404 (tenant no encontrado por django-tenants)"
                        tenant_issues.append(issue)
                        self.stdout.write(self.style.ERROR(issue))
                    elif response.status_code in [200, 302, 301]:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✅ Acceso web funciona: HTTP {response.status_code}"
                            )
                        )
                    else:
                        issue = f"⚠️  Acceso web retorna: HTTP {response.status_code}"
                        tenant_issues.append(issue)
                        self.stdout.write(self.style.WARNING(issue))
                except Exception as e:
                    issue = f"❌ Error al probar acceso web: {e}"
                    tenant_issues.append(issue)
                    self.stdout.write(self.style.ERROR(issue))

            # Resumen del tenant
            if tenant_issues:
                tenants_with_issues += 1
                issues_found.extend([(tenant.schema_name, issue) for issue in tenant_issues])
                if not tenant_fixed:
                    self.stdout.write("")
                    self.stdout.write(self.style.ERROR("❌ TENANT CON PROBLEMAS"))
            else:
                tenants_ok += 1
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("✅ TENANT OK"))

        # Resumen final
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("📊 RESUMEN DE AUDITORÍA")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total de tenants auditados: {total_tenants}")
        self.stdout.write(
            self.style.SUCCESS(f"✅ Tenants OK: {tenants_ok}")
        )
        self.stdout.write(
            self.style.ERROR(f"❌ Tenants con problemas: {tenants_with_issues}")
        )

        if issues_found:
            self.stdout.write("")
            self.stdout.write("🔍 PROBLEMAS ENCONTRADOS:")
            for schema, issue in issues_found:
                self.stdout.write(f"   [{schema}] {issue}")
            
            if not fix_issues:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        "💡 Ejecuta con --fix para intentar corregir problemas automáticamente"
                    )
                )

        self.stdout.write("")
        self.stdout.write("=" * 80)
