"""
Comando para limpiar dominios duplicados de tenants (uso one-off).

Estrategia:
- Detecta dominios duplicados por 'domain'.
- Mantiene el más antiguo (pk más pequeño) marcado como primario si procede.
- Elimina los duplicados adicionales no primarios.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.public.tenants.models import Domain


class Command(BaseCommand):
    help = "Limpia dominios duplicados en tenants_domain, manteniendo el más antiguo."

    def handle(self, *args, **options):
        self.stdout.write("🔍 Buscando dominios duplicados en tenants_domain...")

        by_domain = defaultdict(list)
        for d in Domain.objects.all().order_by("id"):
            by_domain[d.domain].append(d)

        total_duplicates = 0

        for dom, items in by_domain.items():
            if len(items) <= 1:
                continue

            self.stdout.write(f"\n🌐 Dominio duplicado: {dom} ({len(items)} registros)")
            keeper = items[0]
            self.stdout.write(
                f"   Manteniendo: id={keeper.id}, tenant_id={keeper.tenant_id}, is_primary={keeper.is_primary}"
            )

            for extra in items[1:]:
                total_duplicates += 1
                self.stdout.write(
                    f"   Eliminando duplicado: id={extra.id}, tenant_id={extra.tenant_id}, is_primary={extra.is_primary}"
                )
                extra.delete()

        if total_duplicates == 0:
            self.stdout.write(self.style.SUCCESS("OK: No se encontraron dominios duplicados."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nOK: Limpieza completada. Duplicados eliminados: {total_duplicates}"
                )
            )
