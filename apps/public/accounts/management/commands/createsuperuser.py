"""
Override de createsuperuser: crea el superusuario del sistema y lo asocia
directamente a un tenant privado como administrador primario.

Flujo:
  1. Solicita email, password (igual que el comando Django nativo)
  2. Pregunta a qué tenant privado asociar al nuevo superusuario
  3. Crea/actualiza TenantMembership con is_primary_admin=True

Reglas:
  - El superusuario tiene is_staff=True + is_superuser=True (acceso a /admin/ y /console/)
  - El tenant owner (sin superuser) es un usuario distinto creado en el onboarding
  - Este comando es el UNICO proceso autorizado para crear administradores del sistema
  - No crear admins via ensure_admin ni manualmente con is_staff=True en onboarding
"""
from django.contrib.auth.management.commands.createsuperuser import (
    Command as BaseCreateSuperuserCommand,
)
from django.core.management.base import CommandError


class Command(BaseCreateSuperuserCommand):
    help = "Crea el superusuario del sistema y lo asocia a un tenant privado."

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--tenant",
            dest="tenant_schema",
            default=None,
            help="schema_name del tenant privado al que asociar al superusuario (ej: <schema_name>). "
                 "Consulta los disponibles con: python manage.py shell -c "
                 "\"from apps.public.tenants.models import Client; "
                 "[print(c.schema_name) for c in Client.objects.exclude(schema_name='public')]\"",
        )

    def handle(self, *args, **options) -> None:
        # 1. Crear el superusuario con el flujo nativo de Django
        super().handle(*args, **options)

        # 2. Obtener el usuario recién creado
        from django.contrib.auth import get_user_model
        User = get_user_model()

        username = options.get(self.UserModel.USERNAME_FIELD)
        if not username:
            # En modo interactivo el username puede estar en stdin — recuperar el último creado
            user = User.objects.filter(is_superuser=True, is_staff=True).order_by("-date_joined").first()
        else:
            user = User.objects.filter(**{self.UserModel.USERNAME_FIELD: username}).first()

        if not user:
            self.stdout.write(self.style.WARNING("No se pudo recuperar el usuario creado para asociar al tenant."))
            return

        # 3. Determinar el tenant a asociar
        tenant_schema = options.get("tenant_schema")
        if not tenant_schema and not options.get("no_input"):
            tenant_schema = self._ask_tenant()

        if not tenant_schema:
            self.stdout.write(self.style.WARNING(
                f"Superusuario '{user.email}' creado sin asociacion a tenant. "
                f"Usa: python manage.py createsuperuser --tenant <schema_name>"
            ))
            return

        # 4. Crear TenantMembership
        self._associate_tenant(user, tenant_schema)

    def _ask_tenant(self) -> str | None:
        """Pregunta interactivamente qué tenant asociar."""
        from apps.public.tenants.models import Client
        tenants = list(
            Client.objects.exclude(schema_name="public")
            .filter(is_active=True)
            .values_list("schema_name", "nombre")
            .order_by("schema_name")
        )
        if not tenants:
            self.stdout.write(self.style.WARNING("No hay tenants privados activos. Omitiendo asociacion."))
            return None

        self.stdout.write("\nTenants privados disponibles:")
        for i, (schema, nombre) in enumerate(tenants, 1):
            self.stdout.write(f"  {i}. {schema} ({nombre})")
        self.stdout.write("  0. Omitir (no asociar)")

        while True:
            raw = input("Selecciona el numero del tenant (0 para omitir): ").strip()
            if raw == "0":
                return None
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(tenants):
                    return tenants[idx][0]
            except ValueError:
                pass
            self.stdout.write("Seleccion invalida. Intenta nuevamente.")

    def _associate_tenant(self, user, tenant_schema: str) -> None:
        """Crea o actualiza TenantMembership para el superusuario en el tenant indicado."""
        from apps.public.tenants.models import Client, TenantMembership

        try:
            tenant = Client.objects.get(schema_name=tenant_schema, is_active=True)
        except Client.DoesNotExist:
            raise CommandError(f"Tenant '{tenant_schema}' no encontrado o inactivo.")

        # Quitar is_primary_admin anterior en ese tenant (si existe)
        TenantMembership.objects.filter(
            client=tenant, is_primary_admin=True
        ).exclude(user=user).update(is_primary_admin=False)

        membership, created = TenantMembership.objects.update_or_create(
            client=tenant,
            user=user,
            defaults={
                "rol": "ADMIN",
                "is_primary_admin": True,
                "is_active": True,
            },
        )

        action = "creada" if created else "actualizada"
        self.stdout.write(self.style.SUCCESS(
            f"TenantMembership {action}: {user.email} → {tenant.nombre} ({tenant_schema}) "
            f"[Administrador Primario]"
        ))
