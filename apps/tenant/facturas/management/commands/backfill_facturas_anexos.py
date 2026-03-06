"""
Comando de backfill: crea FacturaAnexos desde columnas antiguas.

⚠️ FASE 5: Backfill tenant-aware de anexos.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model


class Command(BaseCommand):
    help = "Backfill de anexos desde columnas antiguas a FacturaAnexos (tenant-aware)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Esquema específico a procesar (si no se especifica, procesa todos)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        from apps.tenant.facturas.models import Factura, FacturaAnexos
        
        schema_name = options.get('schema')
        dry_run = options.get('dry_run', False)
        
        if schema_name:
            schemas = [schema_name]
        else:
            # Procesar todos los tenants
            schemas = get_tenant_model().objects.values_list("schema_name", flat=True)
        
        total_created = 0
        
        for schema in schemas:
            with schema_context(schema):
                created = 0
                
                for factura in Factura.objects.all():
                    # Recoger potenciales columnas antiguas
                    ubl = (
                        getattr(factura, 'xml_content', None) or
                        getattr(factura, 'xml_ubl', None) or
                        getattr(factura, 'xml_raw', None) or
                        getattr(factura, 'attached_document_xml', None)
                    )
                    
                    app = (
                        getattr(factura, 'dian_response_xml', None) or
                        getattr(factura, 'application_response_xml', None) or
                        getattr(factura, 'app_response_xml', None)
                    )
                    
                    # Si no hay valores, saltar
                    if not ubl and not app:
                        continue
                    
                    # Verificar si ya existe anexo
                    if FacturaAnexos.objects.filter(factura=factura).exists():
                        continue
                    
                    if not dry_run:
                        FacturaAnexos.objects.create(
                            factura=factura,
                            ubl_xml=ubl,
                            application_response_xml=app
                        )
                    
                    created += 1
                
                action = "SIMULADO" if dry_run else "CREADOS"
                self.stdout.write(self.style.SUCCESS(
                    f"[{schema}] anexos {action.lower()}={created}"
                ))
                
                total_created += created
        
        # Resumen global
        action = "SIMULADOS" if dry_run else "CREADOS"
        self.stdout.write(self.style.SUCCESS(
            f"\n=== RESUMEN GLOBAL ===\n"
            f"Total anexos {action.lower()}: {total_created}"
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  DRY-RUN: No se realizaron cambios. Ejecuta sin --dry-run para aplicar."
            ))
