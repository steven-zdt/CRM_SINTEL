"""
Comando de auditoría: Lista facturas cuya naturaleza no coincide con la comparación (emisor vs Empresa.nit).

Uso:
    python manage.py all_tenants_command audit_naturaleza_mismatches
    python manage.py tenant_command audit_naturaleza_mismatches --schema=tenant1
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services import _norm_nit


class Command(BaseCommand):
    help = "Lista facturas cuya naturaleza no coincide con la comparación (emisor vs Empresa.nit)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema específico (opcional, si no se proporciona, se procesan todos)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Límite de facturas a mostrar por tenant (default: 50)'
        )

    def handle(self, *args, **options):
        schema_name = options.get('schema')
        limit = options.get('limit', 50)
        
        if schema_name:
            schemas = [schema_name]
        else:
            schemas = list(get_tenant_model().objects.values_list('schema_name', flat=True))
        
        total_mismatches = 0
        
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
                
                en = _norm_nit(empresa_nit)
                wrong = []
                
                for f in Factura.objects.only("id", "numero", "emisor_nit", "naturaleza").iterator():
                    emisor_norm = _norm_nit(f.emisor_nit)
                    match = bool(emisor_norm and en and emisor_norm == en)
                    expected = "VENTA" if match else "COMPRA"
                    
                    if f.naturaleza != expected:
                        wrong.append({
                            "id": f.id,
                            "numero": f.numero,
                            "naturaleza_actual": f.naturaleza,
                            "naturaleza_esperada": expected,
                            "emisor_nit": f.emisor_nit,
                            "empresa_nit": empresa_nit,
                            "match": match,
                        })
                
                if wrong:
                    self.stdout.write(
                        self.style.ERROR(f"[{schema}] Mismatches: {len(wrong)}")
                    )
                    for item in wrong[:limit]:
                        self.stdout.write(
                            f"  ID={item['id']} Numero={item['numero']} "
                            f"Actual={item['naturaleza_actual']} Esperada={item['naturaleza_esperada']} "
                            f"Emisor={item['emisor_nit']} Empresa={item['empresa_nit']}"
                        )
                    if len(wrong) > limit:
                        self.stdout.write(
                            f"  ... y {len(wrong) - limit} más"
                        )
                    total_mismatches += len(wrong)
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"[{schema}] OK (0 mismatches)")
                    )
        
        if total_mismatches > 0:
            self.stdout.write(
                self.style.ERROR(f"\nTotal de mismatches encontrados: {total_mismatches}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Todos los tenants están correctos (0 mismatches)")
            )
