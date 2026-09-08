"""Enciende/apaga buscar_conocimiento para un tenant (rollout AI-VECTOR-11).

Palanca operativa del rollout gate por gate (piloto -> 2 tenants -> 25% ->
50% -> 100%): el flag global `AI_RETRIEVAL_ENABLED` sigue siendo el kill
switch de todo el entorno; este comando controla el flag por tenant
(`AIKnowledgeSettings.retrieval_enabled`) que decide a cuales tenants ya
llego el rollout.

Uso:
    python manage.py ai_knowledge_toggle_retrieval home --enable
    python manage.py ai_knowledge_toggle_retrieval home --disable
"""

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = "Enciende/apaga buscar_conocimiento (Vector Store) para un tenant."

    def add_arguments(self, parser):
        parser.add_argument("schema", type=str, help="schema_name del tenant.")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--enable", action="store_true", help="Habilitar retrieval.")
        group.add_argument("--disable", action="store_true", help="Deshabilitar retrieval.")

    def handle(self, *args, **options):
        schema_name = options["schema"]
        enabled = bool(options["enable"])

        with schema_context(schema_name):
            from apps.tenant.ai_knowledge.services import AIKnowledgeCRUDService
            from apps.tenant.empresa.models import Empresa

            empresa = Empresa.objects.only("id", "razon_social").first()
            if empresa is None:
                raise CommandError(f"schema '{schema_name}' sin Empresa.")

            AIKnowledgeCRUDService.set_retrieval_enabled(empresa=empresa, enabled=enabled)

        estado = "HABILITADO" if enabled else "DESHABILITADO"
        self.stdout.write(
            self.style.SUCCESS(f"buscar_conocimiento {estado} para schema='{schema_name}'")
        )
