"""
Comando de auditoría: verifica estado de anexos en facturas.

⚠️ FASE 5: Auditoría tenant-aware de anexos.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model


class Command(BaseCommand):
    help = "Audita anexos: facturas con/sin anexo y columnas antiguas (si existen)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Esquema específico a auditar (si no se especifica, audita todos)',
        )

    def handle(self, *args, **options):
        from apps.tenant.facturas.models import Factura, FacturaAnexos
        
        schema_name = options.get('schema')
        
        if schema_name:
            schemas = [schema_name]
        else:
            # Auditar todos los tenants
            schemas = get_tenant_model().objects.values_list("schema_name", flat=True)
        
        total_facturas = 0
        total_con_anexo = 0
        total_con_columnas_antiguas = 0
        
        for schema in schemas:
            with schema_context(schema):
                facturas_count = Factura.objects.count()
                anexos_count = FacturaAnexos.objects.count()
                
                # Detectar columnas antiguas si existieran
                old_cols = []
                field_candidates = [
                    'xml_content', 'xml_ubl', 'xml_raw',
                    'dian_response_xml', 'application_response_xml', 'app_response_xml',
                    'attached_document_xml'
                ]
                
                for field_name in field_candidates:
                    try:
                        Factura._meta.get_field(field_name)
                        old_cols.append(field_name)
                    except Exception:
                        pass
                
                # Contar facturas con columnas antiguas pobladas
                facturas_con_antiguas = 0
                if old_cols:
                    from django.db.models import Q
                    q = Q()
                    for col in old_cols:
                        q |= Q(**{f"{col}__isnull": False}) & ~Q(**{col: ""})
                    facturas_con_antiguas = Factura.objects.filter(q).count()
                
                msg = (
                    f"[{schema}] "
                    f"total_facturas={facturas_count} "
                    f"con_anexo={anexos_count} "
                    f"old_cols={','.join(old_cols) or '-'} "
                    f"con_old_cols={facturas_con_antiguas}"
                )
                self.stdout.write(self.style.SUCCESS(msg))
                
                total_facturas += facturas_count
                total_con_anexo += anexos_count
                total_con_columnas_antiguas += facturas_con_antiguas
        
        # Resumen global
        self.stdout.write(self.style.SUCCESS(
            f"\n=== RESUMEN GLOBAL ===\n"
            f"Total facturas: {total_facturas}\n"
            f"Total con anexo: {total_con_anexo}\n"
            f"Total con columnas antiguas: {total_con_columnas_antiguas}\n"
            f"Pendientes de migración: {total_con_columnas_antiguas - total_con_anexo}"
        ))
