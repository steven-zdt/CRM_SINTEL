"""
Comando de backfill para calcular naturaleza (VENTA/COMPRA) en facturas existentes.

⚠️ MULTI-TENANT: Usa schema_context y tenant_command/all_tenants_command de django-tenants.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services import _determinar_naturaleza
from apps.tenant.empresa.models import Empresa


class Command(BaseCommand):
    help = "Backfill de naturaleza (VENTA/COMPRA) en facturas con naturaleza NULL"

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema específico (opcional). Si no se proporciona, procesa todos los esquemas.'
        )

    def handle(self, *args, **opts):
        schema_name = opts.get('schema')
        
        if schema_name:
            schemas = [schema_name]
        else:
            # Obtener todos los esquemas de tenant (excluyendo 'public')
            Tenant = get_tenant_model()
            schemas = list(Tenant.objects.exclude(schema_name='public').values_list('schema_name', flat=True))
        
        if not schemas:
            self.stdout.write(self.style.WARNING("No se encontraron esquemas de tenant para procesar."))
            return
        
        total_updated = 0
        
        for schema in schemas:
            with schema_context(schema):
                try:
                    # Obtener empresa del tenant (SSoT)
                    empresa = Empresa.objects.first()
                    empresa_nit = getattr(empresa, "nit", None) if empresa else None
                    
                    if not empresa_nit:
                        self.stdout.write(
                            self.style.WARNING(f"[{schema}] No se encontró empresa. Saltando esquema.")
                        )
                        continue
                    
                    # Buscar facturas con naturaleza NULL
                    facturas_sin_naturaleza = Factura.objects.filter(naturaleza__isnull=True).only("id", "emisor_nit")
                    count = facturas_sin_naturaleza.count()
                    
                    if count == 0:
                        self.stdout.write(
                            self.style.SUCCESS(f"[{schema}] No hay facturas sin naturaleza. Saltando.")
                        )
                        continue
                    
                    updated = 0
                    for factura in facturas_sin_naturaleza:
                        factura.naturaleza = _determinar_naturaleza(factura.emisor_nit, empresa_nit)
                        factura.save(update_fields=["naturaleza"])
                        updated += 1
                    
                    total_updated += updated
                    self.stdout.write(
                        self.style.SUCCESS(f"[{schema}] Naturaleza backfilled: {updated} facturas")
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"[{schema}] Error: {str(e)}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f"\n✅ Total de facturas actualizadas: {total_updated}")
        )
