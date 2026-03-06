from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    help = "Imprime los nombres de URL y sus patrones registrados."

    def handle(self, *args, **options):
        resolver = get_resolver()
        for name, patterns in resolver.reverse_dict.items():
            if not isinstance(name, str):
                continue
            try:
                for possibility in patterns[0]:
                    pattern = possibility[1]
                    self.stdout.write(f"{name} -> /{pattern}")
            except Exception:
                self.stdout.write(f"{name} -> (pattern no legible)")

