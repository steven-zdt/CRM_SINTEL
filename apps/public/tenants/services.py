import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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


def crear_tenant_con_owner(
    nombre: str,
    admin_user_id: int,
    schema_name: str | None = None,
    paid_until: str | None = None,
    on_trial: bool = True,
) -> tuple[Client, Domain, TenantMembership, str]:
    """
    Crea un tenant completo en el esquema publico y asigna un owner (primary admin).

    Separacion intencional de DDL y DML para compatibilidad con PostgreSQL:
    -----------------------------------------------------------------------
    PostgreSQL trata CREATE SCHEMA como DDL transaccional, pero django-tenants
    emite ese DDL en Client.save() via auto_create_schema=True. Envolver esa
    operacion en transaction.atomic() global causa que cualquier excepcion
    posterior intente revertir el CREATE SCHEMA junto con DML, generando
    estados inconsistentes cuando el schema fue creado pero la transaccion
    hace rollback (el schema queda huerfano o la FK queda rota).

    Solucion adoptada (two-phase commit pattern):
      FASE 1 — DDL (sin transaction.atomic): Client.objects.create() deja que
               TenantMixin cree el schema PostgreSQL de forma irrevocable.
      FASE 2 — DML (transaction.atomic): Domain + TenantMembership se crean
               atomicamente DESPUES de confirmar que el schema existe.

    Flujo:
    1. Genera/valida schema_name (sin puntos, unico).
    2. Verifica que el usuario admin exista y este activo.
    3. FASE 1 — Crea Client (TenantMixin crea el schema PostgreSQL via DDL).
    4. FASE 2 — Crea Domain y TenantMembership en transaction.atomic() separada.
    5. Verifica integridad final (schema existe, dominio primario unico).
    6. Construye login_url estandar (apunta a /login/).
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
            f"Los subdominios se construyen automaticamente como: "
            f"{{schema_name}}.{settings.TENANT_DOMAIN_BASE}"
        )

    if Client.objects.filter(schema_name=schema_normalized).exists():
        raise ValidationError(f"El schema_name '{schema_normalized}' ya existe")

    # 2. Usuario admin
    try:
        admin_user = User.objects.get(pk=admin_user_id, is_active=True)
    except User.DoesNotExist:
        raise ValidationError(
            f"El usuario con ID {admin_user_id} no existe o no esta activo. "
            f"No se puede crear un tenant sin un administrador valido."
        )

    logger.info("Creando tenant '%s' (schema=%s)", nombre, schema_normalized)

    # FASE 1 — DDL: Client.save() emite CREATE SCHEMA via TenantMixin.
    # No se envuelve en transaction.atomic() para evitar conflictos DDL/DML.
    # Si falla aqui, no hay datos parciales que revertir.
    client = Client.objects.create(
        schema_name=schema_normalized,
        nombre=nombre.strip(),
        paid_until=paid_until,
        on_trial=on_trial,
        is_active=True,
    )
    logger.info("Tenant schema creado: %s", schema_normalized)

    # FASE 2 — DML: Domain + TenantMembership en bloque atomico.
    # Solo se ejecuta una vez confirmado que el schema PostgreSQL existe.
    try:
        with transaction.atomic():
            expected_domain = f"{schema_normalized}.{settings.TENANT_DOMAIN_BASE}"
            domain, _ = Domain.objects.get_or_create(
                tenant=client,
                domain=expected_domain,
                defaults={"is_primary": True},
            )
            if not domain.is_primary:
                domain.is_primary = True
                domain.save(update_fields=["is_primary"])

            logger.info("Dominio registrado: %s (is_primary=%s)", domain.domain, domain.is_primary)

            membership = TenantMembership.objects.create(
                client=client,
                user=admin_user,
                rol="ADMIN",
                is_primary_admin=True,
                is_active=True,
            )
    except Exception as exc:
        logger.error(
            "FASE 2 fallida para tenant '%s' (schema=%s): %s",
            nombre,
            schema_normalized,
            exc,
            exc_info=True,
        )
        raise

    # 5. Validaciones finales
    if not schema_exists(schema_normalized):
        raise ValidationError(
            f"El schema PostgreSQL '{schema_normalized}' no existe despues de crear el tenant. "
            f"Revisa auto_create_schema=True en el modelo Client."
        )

    primary_domains = Domain.objects.filter(tenant=client, is_primary=True)
    if primary_domains.count() != 1:
        raise ValidationError(
            f"El tenant '{schema_normalized}' debe tener exactamente un dominio primario. "
            f"Encontrados: {primary_domains.count()}"
        )

    # 6. Construir login_url
    tenant_domain = domain.domain
    protocol = "https" if (not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False)) else "http"
    login_url = f"{protocol}://{tenant_domain}/login/"

    logger.info("Tenant creado: %s (%s) -> %s", client.nombre, client.schema_name, login_url)

    return client, domain, membership, login_url
