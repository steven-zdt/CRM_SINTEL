"""
Verifica que exista al menos un superusuario activo en el sistema.

Este comando NO crea usuarios — solo verifica su existencia y alerta si no hay ninguno.
El unico proceso autorizado para crear el superusuario del sistema es:

    python manage.py createsuperuser [--tenant <schema_name>]

Si no hay superusuario, muestra un aviso pero no crea nada automaticamente
(crearlo sin asociar al tenant correcto seria incoherente con la arquitectura).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica que exista al menos un superusuario activo del sistema."

    def handle(self, *args, **options) -> None:
        User = get_user_model()

        admins = User.objects.filter(is_staff=True, is_superuser=True, is_active=True)
        if admins.exists():
            for u in admins:
                self.stdout.write(
                    self.style.SUCCESS(f"Superusuario activo: {u.email} (id={u.id})")
                )
        else:
            self.stdout.write(self.style.ERROR(
                "ALERTA: No hay superusuarios activos en el sistema.\n"
                "Crea uno con:\n"
                "  python manage.py createsuperuser --tenant <schema_name>\n"
                "Donde <schema_name> es el schema_name del tenant al que deseas asociar el admin.\n"
                "Consulta los tenants disponibles con:\n"
                "  python manage.py shell -c \"from apps.public.tenants.models import Client; "
                "[print(c.schema_name) for c in Client.objects.exclude(schema_name='public')]\""
            ))
