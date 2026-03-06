"""
Comando para re-indexar todas las NormasTributaria en OpenSearch.

Útil para reindexar desde cero o actualizar el índice después de cambios en el schema.
"""
from django.core.management.base import BaseCommand
from apps.public.impuestos.search.indexer import bulk_index_normas


class Command(BaseCommand):
    help = "Indexa (o re-indexa) todas las NormasTributaria al alias actual (impuestos-docs)."
    
    def handle(self, *args, **options):
        """
        Ejecuta bulk index de todas las normas tributarias.
        """
        self.stdout.write("Iniciando indexación de normas tributarias...")
        
        try:
            stats = bulk_index_normas()
            
            ok_count = stats.get("ok", 0)
            fail_count = stats.get("fail", 0)
            
            if fail_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Indexación completada con errores: OK={ok_count}, FAIL={fail_count}"
                    )
                )
                if stats.get("failed_items"):
                    self.stdout.write(
                        self.style.ERROR(f"Items fallidos: {len(stats['failed_items'])}")
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Indexación completada: OK={ok_count}, FAIL={fail_count}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error en indexación: {str(e)}")
            )
            raise
