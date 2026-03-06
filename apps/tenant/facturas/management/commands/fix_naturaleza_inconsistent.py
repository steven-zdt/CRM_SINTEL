"""
Comando de corrección: Corrige naturaleza para todas las facturas recalculando contra Empresa.nit.

⚠️ ADVERTENCIA: Este comando modifica datos en producción. Ejecutar con precaución.

Uso:
    python manage.py all_tenants_command fix_naturaleza_inconsistent
    python manage.py tenant_command fix_naturaleza_inconsistent --schema=tenant1
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model
from django.db import transaction
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services import _determinar_naturaleza


class Command(BaseCommand):
    help = "Corrige naturaleza para todas las facturas recalculando contra Empresa.nit"

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema específico (opcional, si no se proporciona, se procesan todos)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se corregiría sin hacer cambios'
        )

    def handle(self, *args, **options):
        schema_name = options.get('schema')
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  MODO DRY-RUN: No se realizarán cambios")
            )
        
        if schema_name:
            schemas = [schema_name]
        else:
            schemas = list(get_tenant_model().objects.values_list('schema_name', flat=True))
        
        total_fixed = 0
        
        for schema in schemas:
            with schema_context(schema):
                emp = Empresa.objects.first()
                if not emp:
                    self.stdout.write(
                        self.style.WARNING(f"[{schema}] Sin Empresa configurada")
                    )
                    continue
                
                empresa_nit = getattr(emp, "nit", None)
                if not empresa_nit:
                    self.stdout.write(
                        self.style.WARNING(f"[{schema}] Empresa sin NIT")
                    )
                    continue
                
                fixed = 0
                
                with transaction.atomic():
                    for f in Factura.objects.all().only("id", "emisor_nit", "naturaleza").iterator():
                        expected = _determinar_naturaleza(f.emisor_nit, empresa_nit)
                        
                        if f.naturaleza != expected:
                            if not dry_run:
                                f.naturaleza = expected
                                f.save(update_fields=["naturaleza"])
                            fixed += 1
                            self.stdout.write(
                                f"  [{schema}] Factura ID={f.id} "
                                f"Actual={f.naturaleza} → Esperada={expected}"
                            )
                
                if fixed > 0:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f"[{schema}] Se corregirían {fixed} facturas")
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"[{schema}] Corregidas {fixed} facturas")
                        )
                    total_fixed += fixed
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"[{schema}] OK (0 correcciones necesarias)")
                    )
        
        if total_fixed > 0:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"\n⚠️  Total de facturas a corregir: {total_fixed}")
                    self.stdout.write(
                        self.style.WARNING("Ejecuta sin --dry-run para aplicar cambios")
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"\n✅ Total de facturas corregidas: {total_fixed}")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Todas las facturas están correctas (0 correcciones)")
            )
