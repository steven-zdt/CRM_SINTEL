from django.contrib.auth.models import UserManager as DjangoUserManager
from django.utils.text import slugify


class UserManager(DjangoUserManager):
    """
    UserManager personalizado que genera username automáticamente desde el email.

    - create_user / create_superuser aceptan solo email y password.
    - Si no se pasa username, se deriva del local-part del email (antes de @),
      slugificado y en minúsculas.
    - Si hay colisión de username, añade un sufijo incremental: user, user2, user3, ...
    """

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")

        email = self.normalize_email(email)
        # Extraer y eliminar username de extra_fields para no pasarlo dos veces
        username = extra_fields.pop("username", None)

        if not username:
            # Generar username desde el local-part del email
            local_part = email.split("@")[0] if "@" in email else email
            base = slugify(local_part.lower()) if local_part else "user"
            if not base or base.strip() == "":
                base = "user"
            username = base
            Model = self.model
            i = 1
            # Evitar colisiones de username
            while Model.objects.filter(username=username).exists():
                i += 1
                username = f"{base}{i}"

        # Asegurar que username no esté vacío
        if not username or username.strip() == "":
            username = "user"
            Model = self.model
            i = 1
            while Model.objects.filter(username=username).exists():
                i += 1
                username = f"user{i}"

        # Delegar en la implementación de Django, pasando username explícitamente
        return super()._create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email=email, password=password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email=email, password=password, **extra_fields)


