"""
Comando de auditoría: Lista tenants sin Empresa o sin NIT.

Uso:
    python manage.py all_tenants_command audit_empresa_nit
    python manage.py tenant_command audit_empresa_nit --schema=tenant1
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context

from apps.tenant.empresa.models import Empresa


class Command(BaseCommand):
    help = "Lista tenants sin Empresa o sin NIT"

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema específico (opcional, si no se proporciona, se procesan todos)'
        )

    def handle(self, *args, **options):
        schema_name = options.get('schema')
        
        if schema_name:
            schemas = [schema_name]
        else:
            schemas = list(get_tenant_model().objects.values_list('schema_name', flat=True))
        
        total_sin_empresa = 0
        total_sin_nit = 0
        total_ok = 0
        
        for schema in schemas:
            with schema_context(schema):
                empresa = Empresa.objects.only("id", "nit", "razon_social").first()
                
                if not empresa:
                    self.stdout.write(
                        self.style.ERROR(f"[{schema}] SIN Empresa")
                    )
                    total_sin_empresa += 1
                elif not empresa.nit:
                    self.stdout.write(
                        self.style.ERROR(f"[{schema}] Empresa SIN NIT (razon_social: {empresa.razon_social})")
                    )
                    total_sin_nit += 1
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"[{schema}] OK: NIT={empresa.nit}")
                    )
                    total_ok += 1
        
        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"Total tenants: {len(schemas)}")
        self.stdout.write(f"  [OK] OK: {total_ok}")
        self.stdout.write(f"  [ERROR] Sin Empresa: {total_sin_empresa}")
        self.stdout.write(f"  # WARNING:  Sin NIT: {total_sin_nit}")
        
        if total_sin_empresa > 0 or total_sin_nit > 0:
            self.stdout.write(
                self.style.WARNING("\n# WARNING:  Hay tenants sin Empresa o sin NIT. Configure antes de importar facturas.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n[OK] Todos los tenants tienen Empresa con NIT configurado.")
            )
