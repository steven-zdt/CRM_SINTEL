from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Crea/asegura el superusuario 'admin' de forma idempotente."

    def handle(self, *args, **options):
        User = get_user_model()

        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "is_superuser": True,
                "is_staff": True,
                "email": "admin@example.com",
            },
        )

        if created:
            admin.set_password("admin123")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Superusuario 'admin' creado"))
        else:
            self.stdout.write("Superusuario 'admin' ya existe")

