"""
Comando para exportar normas tributarias a JSON.

Útil para backups rápidos o migración de datos.
No sustituye a snapshots nativos de OpenSearch, pero sirve como "export" inmediato.
"""

import json
import sys

from django.core.management.base import BaseCommand

from apps.public.impuestos.models import NormaTributaria


class Command(BaseCommand):
    help = "Exporta normas tributarias a JSON por stdout (para backups rápidos)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=0, help="Límite de registros a exportar (0 = todos)"
        )

    def handle(self, *args, **options):
        """
        Exporta normas a JSON en formato estándar.
        """
        limit = options["limit"]

        # Obtener QuerySet con campos relevantes
        qs = NormaTributaria.objects.all().values(
            "id",
            "articulo",
            "impuesto",
            "tema",
            "vigencia_desde",
            "vigencia_hasta",
            "texto_plano",
            "referencias",
            "documento_fuente_id",
        )

        # Aplicar límite si se especifica
        if limit > 0:
            qs = qs[:limit]
            self.stdout.write(f"Exportando {limit} registros...")
        else:
            count = qs.count()
            self.stdout.write(f"Exportando {count} registros...")

        # Serializar fechas a strings ISO
        def serialize_date(obj):
            """Helper para serializar fechas."""
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        # Convertir QuerySet a lista y serializar
        data = list(qs)

        # Serializar fechas manualmente
        for item in data:
            if item.get("vigencia_desde"):
                item["vigencia_desde"] = (
                    item["vigencia_desde"].isoformat()
                    if hasattr(item["vigencia_desde"], "isoformat")
                    else str(item["vigencia_desde"])
                )
            if item.get("vigencia_hasta"):
                item["vigencia_hasta"] = (
                    item["vigencia_hasta"].isoformat()
                    if hasattr(item["vigencia_hasta"], "isoformat")
                    else str(item["vigencia_hasta"])
                )

        # Escribir a stdout como JSON
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2, default=serialize_date)

        self.stderr.write(f"\n✓ Exportación completada: {len(data)} registros", ending="")
