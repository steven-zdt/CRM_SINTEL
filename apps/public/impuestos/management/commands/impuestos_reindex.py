"""
Comando de gestión para crear índices versionados y hacer switch del alias.

Ejemplo de uso:
    python manage.py impuestos_reindex --version 1
    python manage.py impuestos_reindex --version 2
"""

from django.core.management.base import BaseCommand

from apps.public.impuestos.search.client import get_search_client
from apps.public.impuestos.search.schema import INDEX_ALIAS, MAPPINGS, index_name


class Command(BaseCommand):
    help = "Crea un índice versionado y hace switch del alias impuestos-docs (blue/green)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--version",
            type=int,
            required=True,
            help="Número de versión (v{N})",
        )

    def handle(self, *args, **options):
        client = get_search_client()
        v = options["version"]
        idx = index_name(v)

        # 1) Crear índice versión
        if client.indices.exists(idx):
            self.stdout.write(self.style.WARNING(f"{idx} ya existe"))
        else:
            client.indices.create(index=idx, body=MAPPINGS)
            self.stdout.write(self.style.SUCCESS(f"Creado índice {idx}"))

        # 2) Reindexar desde alias actual (si existe) -> opcional para clonado
        # TODO: Implementar reindexación si es necesario

        # 3) Cambiar alias (desapuntar viejos y apuntar al nuevo)
        actions = []

        # Si el alias existe, obtener índices actuales y removerlos
        if client.indices.exists_alias(name=INDEX_ALIAS):
            current_indices = list(client.indices.get_alias(name=INDEX_ALIAS).keys())
            for old_idx in current_indices:
                actions.append({"remove": {"index": old_idx, "alias": INDEX_ALIAS}})

        # Agregar nuevo índice al alias
        actions.append({"add": {"index": idx, "alias": INDEX_ALIAS}})

        if actions:
            client.indices.update_aliases({"actions": actions})
            self.stdout.write(self.style.SUCCESS(f"Alias {INDEX_ALIAS} -> {idx}"))

        self.stdout.write(self.style.SUCCESS(f"Índice {idx} configurado y alias actualizado"))
