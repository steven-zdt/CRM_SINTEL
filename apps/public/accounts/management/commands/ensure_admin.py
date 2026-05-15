from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/asegura el superusuario de Django Admin de forma idempotente."

    # Username reservado para el superusuario de dev — no colisiona con usuarios de tenant
    DEV_USERNAME = "sintel_dev"
    DEV_EMAIL = "dev@sintel.local"
    DEV_PASSWORD = "admin123"

    def handle(self, *args, **options):
        User = get_user_model()

        try:
            admin = User.objects.get(username=self.DEV_USERNAME)
            created = False
        except User.DoesNotExist:
            admin = User(username=self.DEV_USERNAME, email=self.DEV_EMAIL)
            created = True

        needs_save = created
        if not admin.is_staff:
            admin.is_staff = True
            needs_save = True
        if not admin.is_superuser:
            admin.is_superuser = True
            needs_save = True

        if created:
            admin.set_password(self.DEV_PASSWORD)
            admin.save()
            self.stdout.write(self.style.SUCCESS(
                f"Superusuario de dev creado (user: {self.DEV_USERNAME} / pass: {self.DEV_PASSWORD})"
            ))
        elif needs_save:
            admin.save()
            self.stdout.write(self.style.WARNING(
                f"Superusuario '{self.DEV_USERNAME}' corregido (flags is_staff/is_superuser restaurados)"
            ))
        else:
            self.stdout.write(f"Superusuario '{self.DEV_USERNAME}' ya existe y esta correcto")
