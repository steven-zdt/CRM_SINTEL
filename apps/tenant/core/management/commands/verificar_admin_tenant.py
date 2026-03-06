"""
Comando para verificar que el admin de tenant NO muestra modelos del esquema público.

Ejecutar:
    docker compose exec web python manage.py verificar_admin_tenant
"""
from django.core.management.base import BaseCommand
from apps.tenant.core.admin import tenant_admin_site
from django.contrib import admin
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura


class Command(BaseCommand):
    help = 'Verifica que el admin de tenant NO muestra modelos del esquema público'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("VERIFICACIÓN DE AISLAMIENTO DEL ADMIN DE TENANT")
        self.stdout.write("=" * 80)

        # 1. Verificar modelos registrados en tenant_admin_site
        self.stdout.write("\n1. MODELOS REGISTRADOS EN tenant_admin_site:")
        self.stdout.write("-" * 80)
        tenant_models = list(tenant_admin_site._registry.keys())
        if tenant_models:
            for model in sorted(tenant_models, key=lambda m: m.__name__):
                self.stdout.write(
                    f"  ✅ {model.__name__:30s} (app: {model._meta.app_label})"
                )
        else:
            self.stdout.write(self.style.WARNING("  ⚠️  No hay modelos registrados"))

        # 2. Verificar que modelos públicos NO están registrados
        self.stdout.write("\n2. VERIFICACIÓN: Modelos del esquema público NO deben estar registrados:")
        self.stdout.write("-" * 80)
        public_models = [
            ('Client', Client),
            ('Domain', Domain),
            ('TenantMembership', TenantMembership),
        ]

        all_ok = True
        for name, model in public_models:
            is_registered = tenant_admin_site.is_registered(model)
            if is_registered:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ VULNERABILIDAD: {name:20s} registrado = {is_registered}")
                )
                all_ok = False
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ OK: {name:20s} NO registrado")
                )

        # 3. Verificar que modelos de tenant SÍ están registrados
        self.stdout.write("\n3. VERIFICACIÓN: Modelos de tenant SÍ deben estar registrados:")
        self.stdout.write("-" * 80)
        tenant_test_models = [
            ('Empresa', Empresa),
            ('Factura', Factura),
        ]

        for name, model in tenant_test_models:
            is_registered = tenant_admin_site.is_registered(model)
            if is_registered:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ OK: {name:20s} registrado")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ FALTA: {name:20s} NO registrado")
                )
                all_ok = False

        # 4. Comparar con admin.site
        self.stdout.write("\n4. COMPARACIÓN: Modelos en admin.site (esquema público):")
        self.stdout.write("-" * 80)
        public_admin_models = [
            m for m in admin.site._registry.keys() 
            if m._meta.app_label in ['tenants', 'accounts']
        ]
        for model in sorted(public_admin_models, key=lambda m: m.__name__)[:10]:
            self.stdout.write(
                f"  - {model.__name__:30s} (app: {model._meta.app_label})"
            )

        # 5. Resumen
        self.stdout.write("\n" + "=" * 80)
        if all_ok:
            self.stdout.write(self.style.SUCCESS("✅ RESULTADO: AISLAMIENTO CORRECTO"))
            self.stdout.write("   - Modelos públicos NO aparecen en tenant_admin_site")
            self.stdout.write("   - Modelos de tenant SÍ aparecen en tenant_admin_site")
        else:
            self.stdout.write(self.style.ERROR("❌ RESULTADO: PROBLEMA DETECTADO"))
            self.stdout.write("   - Hay modelos públicos en tenant_admin_site o faltan modelos de tenant")
        self.stdout.write("=" * 80)
