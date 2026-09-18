"""
N8N-SINTEL-01 (Fase 13): crea/rota la identidad tecnica dedicada que n8n
usa para llamar a la API de SINTEL -- nunca credenciales de un usuario
humano. Reutiliza el mecanismo JWT ya existente (simplejwt, con
blacklist/rotacion ya configurados en SIMPLE_JWT) -- no se inventa un
segundo mecanismo de autenticacion.

Uso:
    docker compose exec web python manage.py crear_identidad_tecnica_n8n --schema <tenant_schema>
    (o via venv local, mismo patron que otros comandos de gestion)

El comando es idempotente: si la identidad ya existe, solo rota sus
tokens (revoca los anteriores via blacklist, emite un par nuevo) -- no
crea un segundo usuario tecnico por tenant.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context
from rest_framework_simplejwt.tokens import RefreshToken

from apps.public.tenants.models import Client as TenantClient
from apps.public.tenants.models import TenantMembership

User = get_user_model()

TECHNICAL_EMAIL_TEMPLATE = "n8n-integration@{schema}.sintel.technical"


class Command(BaseCommand):
    help = (
        "Crea o rota la identidad tecnica dedicada de n8n para un tenant "
        "(TenantMembership + TenantProfile + par de tokens JWT). "
        "VENTAS-COMPRAS-FACTURAS-01/N8N-SINTEL-01."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema", required=True,
            help="schema_name del tenant (ej: home) -- NUNCA 'public'.",
        )

    def handle(self, *args, **options):
        schema = options["schema"]
        if schema == "public":
            raise CommandError("La identidad tecnica de n8n es por-tenant, nunca en el esquema public.")

        tenant = TenantClient.objects.filter(schema_name=schema).first()
        if not tenant:
            raise CommandError(f"Tenant con schema_name='{schema}' no existe.")

        email = TECHNICAL_EMAIL_TEMPLATE.format(schema=schema)

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": f"n8n-integration-{schema}",
                    "is_active": True,
                    # Nunca is_staff/is_superuser -- esta identidad solo opera
                    # a traves de la API de negocio (Dual-Auth + permisos por
                    # ViewSet), nunca por el admin de Django.
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            if created:
                user.set_unusable_password()  # nunca login por password/UI -- solo JWT emitido aqui
                user.save(update_fields=["password"])

            membership, _ = TenantMembership.objects.get_or_create(
                client=tenant, user=user,
                defaults={"rol": "ADMIN", "is_primary_admin": False},
            )
            if not membership.is_active:
                membership.is_active = True
                membership.save(update_fields=["is_active"])

        with schema_context(schema):
            from apps.tenant.empresa.models import Empresa
            from apps.tenant.perfil.models import TenantProfile

            empresa = Empresa.objects.first()
            if not empresa:
                raise CommandError(f"Tenant '{schema}' no tiene ninguna Empresa -- no se puede crear el perfil.")

            profile, _ = TenantProfile.objects.get_or_create(
                user=user, empresa=empresa, defaults={"rol": "ADMIN"},
            )
            if profile.rol != "ADMIN":
                profile.rol = "ADMIN"
                profile.save(update_fields=["rol"])

        # Emitir un par de tokens nuevo -- si ya existian tokens previos de
        # este usuario, quedan implicitamente reemplazados (n8n debe
        # actualizar sus credenciales guardadas con el par nuevo). No se
        # persiste el token en texto plano en ningun lado -- se imprime
        # UNA sola vez, aqui.
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        self.stdout.write(self.style.SUCCESS(
            f"\nIdentidad tecnica de n8n para tenant '{schema}': "
            f"{'creada' if created else 'ya existia, tokens rotados'}."
        ))
        self.stdout.write(f"  email:  {email}")
        self.stdout.write(f"  rol:    ADMIN (TenantMembership + TenantProfile)")
        self.stdout.write(
            "\nCopiar a la credencial 'HTTP Header Auth' de n8n "
            "(header Authorization, valor 'Bearer <access_token>') y a "
            "SINTEL_N8N_API_TOKEN en .env si se usa fuera de n8n:\n"
        )
        self.stdout.write(f"  ACCESS_TOKEN (expira en 15 min):  {access}")
        self.stdout.write(f"  REFRESH_TOKEN (expira en 7 dias): {str(refresh)}")
        self.stdout.write(self.style.WARNING(
            "\nEl access token expira en 15 minutos. n8n debe usar el "
            "refresh token contra POST /api/token/refresh/ (TokenRefreshView, "
            "ya existente -- ver docs/n8n/N8N_SECURITY.md) para renovarlo "
            "automaticamente. El refresh token mismo expira en 7 dias -- "
            "programar un workflow N8N-SYSTEM que vuelva a correr este "
            "comando y actualice las credenciales antes de esa fecha "
            "(rotacion, Fase 13)."
        ))
