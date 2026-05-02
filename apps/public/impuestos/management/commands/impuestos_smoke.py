"""
Comando de smoke test para OpenSearch.

Verifica que el alias impuestos-docs esté configurado y responda correctamente.
"""

from django.core.management.base import BaseCommand

from apps.public.impuestos.search.client import get_search_client
from apps.public.impuestos.search.schema import INDEX_ALIAS


class Command(BaseCommand):
    help = "Prueba de humo: consulta básica a OpenSearch por el alias impuestos-docs."

    def handle(self, *args, **options):
        """
        Ejecuta una consulta básica (match_all) contra el alias para verificar conectividad.
        """
        try:
            client = get_search_client()

            # Consulta básica: obtener 1 documento para verificar conectividad
            q = {"size": 1, "query": {"match_all": {}}}

            res = client.search(index=INDEX_ALIAS, body=q)
            total = res.get("hits", {}).get("total", {})

            # OpenSearch puede retornar total como int o dict con value
            if isinstance(total, dict):
                total_value = total.get("value", 0)
            else:
                total_value = total or 0

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ OpenSearch OK: alias={INDEX_ALIAS}, total_docs={total_value}"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ OpenSearch FAILED: {str(e)}"))
            raise
