import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django_tenants.utils import schema_exists

from .models import Client, Domain, TenantMembership
from .validators import validate_schema_name

logger = logging.getLogger(__name__)
User = get_user_model()


def generar_schema_name(nombre: str) -> str:
    """
    Genera un schema_name válido a partir del nombre de la empresa.

    - Minúsculas
    - Sin espacios ni caracteres especiales
    - Solo letras minúsculas, números y guiones bajos (underscores)
    - Longitud máxima 63
    - Evita 'public'
    - Garantiza unicidad frente a Client.schema_name
    """
    import re

    if not nombre:
        raise ValidationError("El nombre de la empresa es requerido para generar el schema_name")

    slug = nombre.lower()
    # Normalizar caracteres acentuados
    import unicodedata

    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode("ascii")
    # Remover caracteres especiales, mantener solo letras, números y espacios
    slug = re.sub(r"[^\w\s]", "", slug)
    # Reemplazar espacios y guiones con guiones bajos
    slug = re.sub(r"[-\s]+", "_", slug).strip("_") or "empresa"

    if slug == "public":
        slug = "empresa_public"

    if len(slug) > 63:
        slug = slug[:63]

    original_slug = slug
    counter = 1
    while Client.objects.filter(schema_name=slug).exists():
        slug = f"{original_slug}_{counter}"
        if len(slug) > 63:
            slug = f"{original_slug[:60]}_{counter}"
        counter += 1

    return slug


@transaction.atomic
def crear_tenant_con_owner(
    nombre: str,
    admin_user_id: int,
    schema_name: str | None = None,
    paid_until: str | None = None,
    on_trial: bool = True,
) -> tuple[Client, Domain, TenantMembership, str]:
    """
    Crea un tenant completo en el esquema público y asigna un owner (primary admin).

    Flujo:
    1. Genera/valida schema_name (sin puntos, único).
    2. Verifica que el usuario admin exista y esté activo.
    3. Crea Client (TenantMixin) → señal post_save crea Domain principal.
    4. Ejecuta migrate_schemas SOLO para ese schema.
    5. Crea TenantMembership con rol ADMIN + is_primary_admin=True.
    6. Verifica integridad final (schema existe, dominio principal único).
    7. Construye login_url estándar (API-First, apunta a /login/).

    Todo el proceso es atómico: si falla algo, no quedan tenants huérfanos.
    """
    if not nombre or not nombre.strip():
        raise ValidationError("El nombre de la empresa es requerido")

    # 1. schema_name
    if not schema_name:
        schema_name = generar_schema_name(nombre)

    schema_normalized = schema_name.strip().lower()
    validate_schema_name(schema_normalized)

    if "." in schema_normalized:
        raise ValidationError(
            f"El schema_name '{schema_normalized}' no puede contener puntos. "
            f"Los subdominios se construyen automáticamente como: "
            f"{{schema_name}}.{settings.TENANT_DOMAIN_BASE}"
        )

    if Client.objects.filter(schema_name=schema_normalized).exists():
        raise ValidationError(f"El schema_name '{schema_normalized}' ya existe")

    # 2. Usuario admin
    try:
        admin_user = User.objects.get(pk=admin_user_id, is_active=True)
    except User.DoesNotExist:
        raise ValidationError(
            f"El usuario con ID {admin_user_id} no existe o no está activo. "
            f"No se puede crear un tenant sin un administrador válido."
        )

    # 3–5 dentro de try para log enriquecido
    try:
        logger.info("🚀 Creando tenant '%s' (schema=%s)", nombre, schema_normalized)

        # 3. Client (auto_create_schema=True crea el schema físico)
        client = Client.objects.create(
            schema_name=schema_normalized,
            nombre=nombre.strip(),
            paid_until=paid_until,
            on_trial=on_trial,
            is_active=True,
        )

        # 4. Crear dominio principal manualmente (las señales están desactivadas)
        expected_domain = f"{schema_normalized}.{settings.TENANT_DOMAIN_BASE}"
        domain, created = Domain.objects.get_or_create(
            tenant=client, domain=expected_domain, defaults={"is_primary": True}
        )

        if not domain.is_primary:
            domain.is_primary = True
            domain.save()

        logger.info(f"OK: Dominio creado: {domain.domain} (is_primary={domain.is_primary})")

        # 5. Migraciones del schema del tenant
        logger.info("🛠 Aplicando migraciones a schema '%s'…", schema_normalized)
        call_command(
            "migrate_schemas", "--schema", schema_normalized, "--fake-initial", verbosity=0
        )

        # 6. TenantMembership (owner)
        membership = TenantMembership.objects.create(
            client=client,
            user=admin_user,
            rol="ADMIN",
            is_primary_admin=True,
            is_active=True,
        )

    except Exception as exc:
        logger.error(
            "ERROR: ROLLBACK creando tenant '%s' (schema=%s): %s",
            nombre,
            schema_normalized,
            exc,
            exc_info=True,
        )
        raise

    # 7. Validaciones finales
    if not client.is_active:
        raise ValidationError(
            f"El tenant '{schema_normalized}' fue creado pero no está activo (is_active=False). "
            f"Esto no debería ocurrir."
        )

    if not schema_exists(schema_normalized):
        raise ValidationError(
            f"El schema PostgreSQL '{schema_normalized}' no existe después de crear el tenant. "
            f"Revisa auto_create_schema=True en el modelo Client."
        )

    primary_domains = Domain.objects.filter(tenant=client, is_primary=True)
    if primary_domains.count() != 1:
        raise ValidationError(
            f"El tenant '{schema_normalized}' debe tener exactamente un dominio principal. "
            f"Encontrados: {primary_domains.count()}"
        )

    # 8. Construir login_url estándar (API-First login)
    tenant_domain = domain.domain
    if not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False):
        protocol = "https"
    else:
        protocol = "http"

    login_url = f"{protocol}://{tenant_domain}/login/"

    logger.info(
        "OK: Tenant creado: %s (%s) -> %s",
        client.nombre,
        client.schema_name,
        login_url,
    )

    return client, domain, membership, login_url
