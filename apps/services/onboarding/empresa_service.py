import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, ProgrammingError, connection, transaction
from django.utils.text import slugify
from django_tenants.utils import schema_context, schema_exists

from apps.public.accounts.api.services.user_service import create_user_service
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.utils import normalize_domain, validate_fqdn, validate_schema_name

User = get_user_model()
logger = logging.getLogger(__name__)
"""
Servicio de onboarding para creación automática de empresas (tenants).

Este servicio centraliza el proceso de creación de tenants de forma segura,
reproducible y coherente, siguiendo el principio de Service Layer Pattern.

Uso:
    from apps.services.onboarding.empresa_service import crear_empresa, crear_tenant
    
    empresa = crear_empresa(
        nombre="Mi Empresa S.A.",
        dominio="mi-empresa.localhost",
        email_admin="admin@mi-empresa.com"
    )
    
    # O con usuario existente:
    client, domain, login_url = crear_tenant(
        nombre="Acme SAS",
        dominio="acme.localhost",
        admin_user_id=1
    )
"""
def _build_primary_domain(schema_name: str, dominio_fqdn: str | None = None) -> str:
    """
    Construye el dominio primario FQDN para un tenant.
    
    WARNING: CAMBIO v2.25: Autogeneración de dominio como <schema>.<TENANT_DOMAIN_BASE>
    si dominio_fqdn viene vacío, inválido o sin TLD.
    
    Args:
        schema_name: Nombre del schema del tenant (ej: "cliente")
        dominio_fqdn: Dominio proporcionado (opcional, puede ser None o vacío)
    
    Returns:
        str: Dominio FQDN normalizado y validado (ej: "cliente.sintel.com")
    
    Raises:
        ValidationError: Si el dominio autogenerado no es válido
    """
    from django.conf import settings
    
    base = getattr(settings, 'TENANT_DOMAIN_BASE', 'sintel.com')
    
    # Si no viene dominio o está vacío, autogenerar.
    # Sanitizar schema_name para uso en labels DNS (no se permiten underscores u otros caracteres).
    if not dominio_fqdn or not dominio_fqdn.strip():
        import re

        sanitized = re.sub(r'[^a-z0-9-]', '-', schema_name.lower())
        sanitized = sanitized.strip('-') or schema_name.lower()
        dominio_fqdn = f"{sanitized}.{base}"
    else:
        # Normalizar primero para verificar si tiene TLD
        normalized = normalize_domain(dominio_fqdn)
        # Si no es un FQDN válido o no tiene TLD (no termina con el base), autogenerar
        if not validate_fqdn(normalized) or not normalized.endswith(f".{base}"):
            import re

            sanitized = re.sub(r'[^a-z0-9-]', '-', schema_name.lower())
            sanitized = sanitized.strip('-') or schema_name.lower()
            dominio_fqdn = f"{sanitized}.{base}"
    
    # Normalizar (sin protocolo/www/puerto/rutas)
    fqdn = normalize_domain(dominio_fqdn)
    
    # Validar FQDN
    if not validate_fqdn(fqdn):
        raise ValidationError(
            f"El dominio '{fqdn}' no es un FQDN válido. "
            f"Se esperaba un formato como '{schema_name}.{base}'"
        )
    
    return fqdn


def _build_login_url(domain: str) -> str:
    """
    Construye login_url con puerto en DEV si APP_PORT está configurado.
    
    WARNING: v2.30: API-First - La raíz del tenant redirige según autenticación.
    - Usuario autenticado → /dashboard/
    - Usuario anónimo → /api/v1/landing/info/ (información pública)
    
    WARNING: v2.30: El login se maneja mediante POST /api/v1/core/auth/login/ (Core API)
    
    WARNING: v2.30: Hardening - Incluye puerto en DEV cuando APP_PORT está configurado.
    - Domain.domain SIEMPRE es FQDN puro (sin puerto), tal como dicta la normalización.
    - En DEV, si APP_PORT=8000, se agrega :8000 a la URL.
    - En PROD, se omite puerto (80/443 implícitos).
    """
    from django.conf import settings

    fqdn = normalize_domain(domain)
    if not fqdn:
        raise ValidationError("Dominio inválido para construir login_url")

    if not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False):
        protocol = "https"
    else:
        protocol = "http"

    # WARNING: v2.30: Incluir puerto en DEV si APP_PORT está configurado
    app_port = getattr(settings, 'APP_PORT', None)
    if settings.DEBUG and app_port and str(app_port) not in ('80', '443'):
        domain_with_port = f"{fqdn}:{app_port}"
    else:
        domain_with_port = fqdn

    # WARNING: v2.30: Apuntar al shell de login (ahora en Core via urls_tenant)
    return f"{protocol}://{domain_with_port}/login/"


def generar_schema_name(nombre: str) -> str:
    """
    Genera un schema_name válido a partir del nombre de la empresa.

    - Basado en slugify(nombre)
    - Sustituye guiones por guiones bajos
    """
    return slugify(nombre).replace("-", "_")


def _table_exists(schema: str, table: str) -> bool:
    """
    Verifica si una tabla existe en el schema del tenant.
    
    Consulta el catálogo de PostgreSQL para verificar existencia de la tabla.
    """
    with connection.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
        """, [schema, table])
        return cur.fetchone() is not None


def _ensure_schema_ready(client: Client, required_tables: list[str] = None):
    """
    Verifica que el schema del tenant tenga las tablas requeridas.
    Si faltan, intenta forzar migración del schema del tenant.
    
    WARNING: v2.30: Hardening - Reforzado para asegurar migraciones antes del seed.
    La doc de django-tenants indica que con auto_create_schema=True
    se ejecuta migrate_schemas al save(), pero esta verificación asegura que
    estén aplicadas antes de seedear (evita errores en escenarios de timing).
    
    WARNING: DEFENSIVO: Ejecuta migrate_schemas --tenant para el schema específico.
    """
    if not required_tables:
        return
    
    missing = [t for t in required_tables if not _table_exists(client.schema_name, t)]
    if missing:
        # Forzar migraciones del schema del tenant (defensivo)
        logger.info(
            f"WARNING: Tablas faltantes en schema '{client.schema_name}': {missing}. "
            f"Forzando migraciones del tenant..."
        )
        try:
            # WARNING: v2.30: Usar --schema y --fake-initial para migrar el schema específico
            call_command(
                "migrate_schemas",
                "--schema", client.schema_name,
                "--fake-initial",
                interactive=False,
                verbosity=1,  # WARNING: v2.30: Aumentar verbosidad para debugging
            )
            # Verificar nuevamente después de migrar
            still_missing = [t for t in missing if not _table_exists(client.schema_name, t)]
            if still_missing:
                logger.warning(
                    f"WARNING: Tablas aún faltantes después de migrar schema '{client.schema_name}': {still_missing}. "
                    f"Seed de perfil se omitirá."
                )
            else:
                logger.info(
                    f"OK: Migraciones aplicadas exitosamente. Tablas creadas en schema '{client.schema_name}'."
                )
        except Exception as e:
            logger.error(
                f"ERROR: Error ejecutando migrate_schemas para schema '{client.schema_name}': {e}. "
                f"Seed de perfil se omitirá.",
                exc_info=True
            )


@transaction.atomic
def crear_tenant_con_owner(
    *,
    nombre: str,
    schema_name: str,
    dominio_fqdn: str | None = None,  # WARNING: v2.25: Opcional, se autogenera si no viene
    owner_email: str | None = None,
    # WARNING: v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
    admin_user_id: int | None = None,
    owner_is_staff: bool = True,
    owner_is_active: bool = True,
    paid_until: str | None = None,
    on_trial: bool = True,
) -> dict[str, Any]:
    """
    Onboarding atómico de tenant con propietario (idempotente y resiliente).
    
    WARNING: CONTRATO ESTABLE: Siempre retorna dict {"client_id", "domain", "membership_id", "login_url"}
    Aunque el seed de perfil falle, el onboarding SIEMPRE retorna login_url si User, Client, Domain y Membership se crearon.
    
    Orden de ejecución (con guardas):
    1. User en public → set_password() (hash seguro), idempotente por email
    2. Client.save() con auto_create_schema=True (crea esquema + migra TENANT_APPS automáticamente)
    3. Domain sin puerto ni www (normalizado)
    4. TenantMembership (OWNER) en public
    5. Seed dentro de schema_context(schema), solo si existe la(s) tabla(s) (ej. perfil_tenantprofile)
       - Si no existen, log de "seed omitido" y continuar (no romper el onboarding)
    
    WARNING: CONFORME A DOCUMENTACIÓN OFICIAL DE DJANGO-TENANTS:
    - Usuario global en public (AUTH_USER_MODEL) - NO en el schema del tenant
    - Client con auto_create_schema=True (crea esquema automáticamente al save())
    - Domain con FQDN limpio (sin puerto, sin www) - según doc oficial
    - TenantMembership (rol=ADMIN, is_primary_admin=True) en public
    - Seed opcional dentro del tenant usando schema_context (solo si tabla existe)
    
    Referencias:
    - django-tenants: https://django-tenants.readthedocs.io/en/latest/use.html
    - auto_create_schema: https://django-tenants.readthedocs.io/en/latest/use.html#creating-tenants
    - schema_context: https://django-tenants.readthedocs.io/en/latest/use.html#schema-context
    
    Args:
        nombre: Nombre de la empresa (requerido)
        schema_name: Schema name (requerido)
        dominio_fqdn: Dominio FQDN sin puerto/www (opcional, se autogenera como <schema>.<TENANT_DOMAIN_BASE>)
        owner_email: Email del propietario (requerido si no se proporciona admin_user_id)
        # WARNING: v2.29: owner_password ELIMINADO - El owner se crea con set_unusable_password() y debe activar en /activate?token=...
        admin_user_id: ID del usuario admin existente (alternativa a owner_email)
        owner_is_staff: Si el propietario es staff (default: True)
        owner_is_active: Si el propietario está activo (default: True)
        paid_until: Fecha de pago hasta (opcional)
        on_trial: Si está en período de prueba (default: True)
    
    Returns:
        Dict estable: {
            "client_id": int,
            "domain": str,
            "membership_id": int,
            "login_url": str
        }
    
    Raises:
        ValidationError: Si los datos son inválidos o el dominio ya existe
        ValueError: Si email o password están vacíos o faltan parámetros requeridos
    """
    if not nombre or not nombre.strip():
        raise ValidationError("El nombre de la empresa es requerido")
    
    # 1) Resolver usuario admin (crear si no existe, o usar existente)
    # WARNING: GUARDA: User en public (AUTH_USER_MODEL), idempotente por email
    # WARNING: CAMBIO v2.24: Owner se crea con set_unusable_password() y se invita por email
    user = None
    if admin_user_id is not None:
        # Usuario existente por ID
        try:
            user = User.objects.get(pk=admin_user_id, is_active=True)
            logger.info("Usuario existente (ID %s): %s", admin_user_id, user.email)
        except User.DoesNotExist:
            raise ValidationError(
                f"El usuario con ID {admin_user_id} no existe o no está activo. "
                f"No se puede crear un tenant sin un administrador válido."
            )
    elif owner_email:
        # WARNING: CAMBIO v2.24: Crear/obtener usuario SIN contraseña usable (se activará en el subdominio)
        email = (owner_email or "").strip().lower()
        if not email:
            raise ValueError("Email del propietario es obligatorio.")
        
        # Primero intentar obtener usuario existente
        user = User.objects.only("id", "email", "is_active", "password").filter(email=email).first()
        
        if user:
            # Usuario existente: si ya tiene password usable, mantenerlo
            # Si no tiene password usable, se generará nueva invitación
            if user.has_usable_password():
                logger.info("Usuario existente con password usable: %s", email)
            else:
                logger.info("Usuario existente sin password usable: %s (se generará nueva invitación)", email)
        else:
            # Crear nuevo usuario SIN password usable (se activará en el subdominio)
            try:
                from apps.public.accounts.api.services.user_service import (
                    _generate_unique_username,
                    _user_has_field,
                )
                
                # Preparar kwargs para crear usuario
                user_kwargs = {
                    "email": email,
                    "first_name": "",
                    "last_name": "",
                    "is_staff": owner_is_staff,
                    "is_active": owner_is_active,
                }
                
                # Si existe el campo username, generarlo de forma única
                if _user_has_field("username"):
                    user_kwargs["username"] = _generate_unique_username(email)
                
                # Crear usuario
                user = User(**user_kwargs)
                user.set_unusable_password()  # WARNING: CRÍTICO: Sin password usable (se activará en subdominio)
                # WARNING: CRÍTICO: Guardar primero sin update_fields para crear el PK, luego actualizar si es necesario
                user.save()  # Crear usuario con PK
                
                logger.info("Usuario creado en public: %s (username=%s, password unusable - se activará en subdominio)", email, getattr(user, 'username', 'N/A'))
            except IntegrityError as e:
                # Si hay conflicto de unicidad (email o username), intentar obtener el usuario existente
                logger.warning("Conflicto de unicidad al crear usuario %s, intentando obtener existente...", email)
                user = User.objects.only("id", "email", "is_active", "password").filter(email=email).first()
                if not user:
                    raise ValueError(f"No se pudo crear ni obtener el usuario {email}: {str(e)}") from e
                logger.info("Usuario obtenido después de conflicto: %s", email)
    else:
        raise ValueError("Se requiere 'admin_user_id' o 'owner_email' para crear un tenant")
    
    # 2) Validar schema_name
    raw_schema = schema_name.strip().lower()
    validate_schema_name(raw_schema)
    logger.info("Iniciando onboarding para tenant: schema='%s', nombre='%s'", raw_schema, nombre.strip())
    
    # 3) Client: auto_create_schema=True debe estar en el modelo; al save() ejecuta migrate_schemas (doc)
    # WARNING: GUARDA: Client.save() con auto_create_schema=True crea esquema + migra TENANT_APPS automáticamente
    client = Client(
        schema_name=raw_schema,
        nombre=nombre.strip(),
        paid_until=paid_until,
        on_trial=on_trial,
        is_active=True,
    )
    client.save()  # django-tenants ejecuta migrate_schemas automáticamente aquí
    logger.info("Client creado: schema='%s', id=%s (esquema PostgreSQL creado y migrado)", raw_schema, client.id)
    
    # 4) Domain (dominio primario FQDN)
    # WARNING: CAMBIO v2.25: Autogeneración de dominio como <schema>.<TENANT_DOMAIN_BASE>
    # si dominio_fqdn viene vacío o inválido
    primary_fqdn = _build_primary_domain(client.schema_name, dominio_fqdn)
    
    try:
        domain, created = Domain.objects.get_or_create(
            domain=primary_fqdn,
            defaults={"tenant": client, "is_primary": True},
        )
        if not created and domain.tenant_id != client.id:
            raise ValidationError(f"El dominio '{primary_fqdn}' ya está asociado a otro tenant.")
        logger.info(
            "Domain creado: '%s' (is_primary=True, autogenerado: %s)",
            primary_fqdn,
            "sí" if not dominio_fqdn or not dominio_fqdn.strip() else "no"
        )
    except IntegrityError:
        # Read-back para condiciones de carrera
        domain = Domain.objects.get(domain=primary_fqdn)
        if domain.tenant_id != client.id:
            raise ValidationError(f"El dominio '{primary_fqdn}' ya está asociado a otro tenant.")
        logger.info("Domain existente: '%s' (idempotente)", primary_fqdn)
    
    # 5) Membership (propietario) en public
    # WARNING: GUARDA: TenantMembership (OWNER) en public, no en el schema del tenant
    membership, created = TenantMembership.objects.get_or_create(
        client=client,
        user=user,
        defaults={"rol": "ADMIN", "is_primary_admin": True, "is_active": True},
    )
    if created:
        logger.info("TenantMembership creado: user=%s, client=%s, rol=ADMIN, is_primary_admin=True", user.email, raw_schema)
    else:
        logger.info("TenantMembership existente: user=%s, client=%s (idempotente)", user.email, raw_schema)
    
    # 6) (Opcional) Seed de perfil, sólo si la tabla existe en el schema del tenant
    # CRÍTICO: El seed es OPCIONAL y NUNCA debe romper el onboarding
    # Aseguramos antes que migraciones estén aplicadas (defensivo)
    # Si la tabla no existe o hay errores, omitimos el seed sin afectar el resultado
    try:
        # Indica el nombre real de tu tabla: <app_label>_<model> en minúsculas
        required_tables = ["perfil_tenantprofile", "empresa_empresa"]  # ajusta si tu app/model difiere
        
        # Verificar y forzar migraciones si faltan tablas
        _ensure_schema_ready(client, required_tables)
        
        # Verificar que las tablas existen después de forzar migraciones
        if _table_exists(client.schema_name, "perfil_tenantprofile") and _table_exists(client.schema_name, "empresa_empresa"):
            with schema_context(client.schema_name):  # ejecutar dentro del schema del tenant
                # 1. CRÍTICO: Crear instancia de Empresa ANTES del TenantProfile
                from apps.tenant.empresa.models import Empresa
                empresa, empresa_created = Empresa.objects.get_or_create(
                    singleton_key=1,
                    defaults={
                        "razon_social": nombre.strip(),
                        "nit": "000000000",  # NIT temporal, debe configurarse después
                        "direccion": "Dirección por configurar",
                        "telefono": "000-000-0000",
                        "email_contacto": user.email,
                        "owner_email": user.email,  # Auto-Admin Elevation: denormalizacion del owner
                    }
                )
                if empresa_created:
                    logger.info(f"Empresa SINTEL_EMPRESA_ROOT creada para tenant {raw_schema}: {empresa.razon_social}")
                else:
                    logger.info(f"Empresa existente para tenant {raw_schema}: {empresa.razon_social}")
                
                # 2. Crear TenantProfile con empresa explícita
                # LOOKUP incluye empresa para respetar unique_together=(user, empresa)
                from apps.tenant.perfil.models import TenantProfile
                TenantProfile.objects.get_or_create(
                    user=user,
                    empresa=empresa,
                    defaults={
                        "cargo": "Administrador Principal",
                        "departamento": "Gerencia",
                        "rol": "ADMIN",  # Auto-Admin: owner siempre es ADMIN
                        "configuracion": {"theme": "light", "notifications": True},
                    },
                )
            logger.info(f"Perfil creado para usuario {user.email} en tenant {raw_schema}")
        else:
            # Mensaje de log estándar (formato recomendado)
            logger.warning(
                "Tabla 'perfil_tenantprofile' no existe en schema '%s'. "
                "Seed de perfil omitido. Onboarding continúa normalmente.",
                raw_schema
            )
    except ProgrammingError as e:
        # Si el app no está en TENANT_APPS o hay desfase de migraciones, no bloqueamos el onboarding
        logger.warning(
            f"No se pudo crear perfil para tenant '{raw_schema}': {e}. "
            f"Onboarding continúa sin perfil."
        )
    except Exception as ex:
        logger.error(
            f"Error creando/actualizando TenantProfile para tenant '{raw_schema}': {ex}",
            exc_info=True,
        )
        # CRITICO: Si hay error en seed de empresa/perfil, abortar onboarding completo
        # para evitar falsos positivos (envio de invitacion sin empresa creada)
        logger.error(
            f"Error critico creando empresa/perfil para tenant '{raw_schema}': {ex}. "
            f"Abortando onboarding para evitar inconsistencias.",
            exc_info=True,
        )
        raise
    
    # 7) Generar token de invitación y enviar email (solo si owner_email fue proporcionado)
    # CAMBIO v2.24: Owner se invita por email con token de activación
    activation_url = None
    if owner_email and not admin_user_id:
        logger.info(
            "Iniciando proceso de invitación por email: user=%s, tenant=%s",
            user.email, raw_schema
        )
        try:
            from django.conf import settings

            from apps.public.tenants.services.invitations import (
                build_activation_url,
                generate_invitation_token,
                send_invitation_email,
            )
            
            logger.info("Generando token de invitación para user_id=%s, tenant_id=%s", user.id, client.id)
            
            # Generar token de invitación (TTL: 24 horas)
            token = generate_invitation_token(
                user_id=user.id,
                tenant_id=client.id,
                ttl_hours=24,
            )
            logger.info("Token de invitación generado (TTL: 24 horas)")
            
            # Construir URL de activación en el subdominio del tenant
            logger.info("Construyendo URL de activación para dominio: %s", domain.domain)
            activation_url = build_activation_url(domain.domain, token)
            logger.info("URL de activación construida: %s", activation_url)
            
            # Enviar email de invitación
            logger.info("Invocando send_invitation_email para user=%s", user.email)
            email_sent = send_invitation_email(user, client, activation_url)
            
            if email_sent:
                logger.info(
                    "PROCESO DE INVITACIÓN COMPLETADO: user=%s, tenant=%s, activation_url=%s",
                    user.email, raw_schema, activation_url
                )
            else:
                logger.warning(
                    "Invitación generada pero email NO enviado: user=%s, tenant=%s, activation_url=%s",
                    user.email, raw_schema, activation_url
                )
                
        except Exception as e:
            # No abortar onboarding si falla el envío de email
            logger.error(
                "ERROR en proceso de invitación para tenant '%s': %s. "
                "Onboarding continúa normalmente.",
                raw_schema, str(e),
                exc_info=True  # Stacktrace completo
            )
            # En desarrollo, construir URL aunque no se envíe email
            try:
                from django.conf import settings
                if settings.DEBUG:
                    logger.info("Modo desarrollo: construyendo URL de activación sin email")
                    from apps.public.tenants.services.invitations import (
                        build_activation_url,
                        generate_invitation_token,
                    )
                    token = generate_invitation_token(user_id=user.id, tenant_id=client.id)
                    activation_url = build_activation_url(domain.domain, token)
                    logger.info("URL de activación construida (modo desarrollo): %s", activation_url)
            except Exception as fallback_error:
                logger.error(
                    "Error incluso en fallback de desarrollo: %s",
                    str(fallback_error),
                    exc_info=True
                )
    
    # 8) Construir login_url sin puerto (para compatibilidad con consola)
    login_url = _build_login_url(domain.domain)
    
    # WARNING: CONTRATO ESTABLE: Siempre retornar dict con estos campos, incluso si el seed falló
    result = {
        "client_id": client.id,
        "domain": domain.domain,
        "membership_id": membership.id,
        "login_url": login_url,
    }
    
    # WARNING: CAMBIO v2.24: Incluir activation_url si se generó
    if activation_url:
        result["activation_url"] = activation_url
    
    logger.info(
        "ONBOARDING COMPLETADO: tenant='%s' (schema='%s'), domain='%s', login_url='%s'%s",
        nombre.strip(), raw_schema, domain.domain, login_url,
        f", activation_url='{activation_url}'" if activation_url else ""
    )
    
    return result


@transaction.atomic
def onboard_tenant(
    nombre: str,
    schema_name: str | None = None,
    admin_user_id: int | None = None,
    dominio: str | None = None,
    paid_until: str | None = None,
    on_trial: bool = True,
) -> tuple[Client, Domain, str]:
    """
    Servicio de alto nivel e idempotente para onboarding de tenants.

    Reglas clave:
    - Idempotente frente a recargas/autoreloader:
      - Client se obtiene via get_or_create(schema_name=...).
      - Domain se obtiene via get_or_create(domain=FQDN normalizado).
      - Membership/Profile se crean via get_or_create.
    - Sin signals: NO depende de post_save para crear Domain.
    - Dominios SIEMPRE sin puerto (normalize_domain).
    - Manejo explícito de IntegrityError + read-back para evitar transacciones abortadas.
    """
    from django.conf import settings

    if not nombre or not nombre.strip():
        raise ValidationError("El nombre de la empresa es requerido")

    # 1) Resolver schema_name y validarlo
    raw_schema = schema_name or generar_schema_name(nombre)
    raw_schema = raw_schema.strip().lower()
    validate_schema_name(raw_schema)

    # 2) Resolver usuario admin si se proporcionó
    admin_user = None
    if admin_user_id is not None:
        try:
            admin_user = User.objects.get(pk=admin_user_id, is_active=True)
        except User.DoesNotExist:
            raise ValidationError(
                f"El usuario con ID {admin_user_id} no existe o no está activo. "
                f"No se puede crear un tenant sin un administrador válido."
            )

    # 3) Client idempotente
    client, _ = Client.objects.get_or_create(
        schema_name=raw_schema,
        defaults={
            "nombre": nombre.strip(),
            "paid_until": paid_until,
            "on_trial": on_trial,
            "is_active": True,
        },
    )

    # 4) Dominio idempotente
    base_domain = dominio or f"{raw_schema}.{getattr(settings, 'TENANT_DOMAIN_BASE', 'localhost')}"
    fqdn = normalize_domain(base_domain)
    if not fqdn:
        raise ValidationError("Dominio normalizado vacío o inválido")

    try:
        domain, created = Domain.objects.get_or_create(
            domain=fqdn,
            defaults={"tenant": client, "is_primary": True},
        )
        if not created and domain.tenant_id != client.id:
            # El dominio existe pero pertenece a otro tenant
            raise ValidationError(f"El dominio '{fqdn}' ya está asociado a otro tenant.")
    except IntegrityError:
        # Read-back para condiciones de carrera / autoreloads concurrentes
        domain = Domain.objects.get(domain=fqdn)
        if domain.tenant_id != client.id:
            raise ValidationError(f"El dominio '{fqdn}' ya está asociado a otro tenant.")

    # 5) Membership idempotente (si hay admin)
    if admin_user is not None:
        TenantMembership.objects.update_or_create(
            client=client,
            user=admin_user,
            defaults={
                "rol": "ADMIN",
                "is_primary_admin": True,
                "is_active": True,
            },
        )

    # 6) Seed opcional dentro del schema del tenant (usando schema_context según doc oficial)
    if admin_user is not None:
        try:
            # Seed de perfil para admin_user (si existe la tabla)
            required_tables = ["perfil_tenantprofile"]
            _ensure_schema_ready(client, required_tables)
            
            if _table_exists(client.schema_name, "perfil_tenantprofile"):
                with schema_context(client.schema_name):
                    from apps.tenant.perfil.models import TenantProfile

                    # Obtener empresa singleton para FK obligatoria
                    profile_empresa = None
                    try:
                        from apps.tenant.empresa.models import Empresa
                        profile_empresa = Empresa.objects.only('id').first()
                    except Exception:
                        pass

                    profile_defaults = {
                        "cargo": "Administrador Principal",
                        "departamento": "Gerencia",
                        "rol": "ADMIN",  # Auto-Admin: owner siempre es ADMIN
                        "configuracion": {"theme": "light", "notifications": True},
                    }
                    if profile_empresa:
                        profile_defaults["empresa"] = profile_empresa

                    TenantProfile.objects.get_or_create(
                        user=admin_user,
                        defaults=profile_defaults,
                    )
                logger.info(f"Perfil creado para admin_user {admin_user.email} en tenant {raw_schema}")
            else:
                logger.warning(
                    "Tabla 'perfil_tenantprofile' no existe en schema '%s'. "
                    "Seed de perfil omitido para admin_user.",
                    raw_schema
                )
        except Exception as ex:
            logger.error(
                "Error creando/actualizando TenantProfile para tenant '%s': %s",
                client.schema_name,
                ex,
                exc_info=True,
            )
            # No abortamos el onboarding completo por fallo en perfil

    # 7) Construir login_url sin puerto
    login_url = _build_login_url(domain.domain)

    return client, domain, login_url


@transaction.atomic
def crear_tenant(
    nombre: str,
    admin_user_id: int,
    schema_name: str | None = None,
    paid_until: str | None = None,
    on_trial: bool = True,
) -> tuple[Client, Domain, str]:
    """
    Wrapper histórico para compatibilidad. Delegado a onboard_tenant().
    """
    return onboard_tenant(
        nombre=nombre,
        schema_name=schema_name,
        admin_user_id=admin_user_id,
        dominio=None,
        paid_until=paid_until,
        on_trial=on_trial,
    )


def crear_empresa(
    nombre: str,
    email_admin: str,
    poblar_datos_iniciales: bool = False,
    schema_name: str | None = None,
    **kwargs
) -> dict[str, Any]:
    """
    Crea una nueva empresa (tenant) con su dominio y usuario administrador.
    
    WARNING: v2.17: Estandarización de subdominios
    - El dominio se construye automáticamente como: {schema_name}.{TENANT_DOMAIN_BASE}
    - Ya no se acepta el parámetro 'dominio' - todos los tenants usan subdominios
    - La señal post_save crea automáticamente el dominio principal
    
    Flujo estándar de alta de empresa:
    1. Genera schema_name desde el nombre (si no se proporciona)
    2. Crea instancia de Client (genera esquema automáticamente, señal crea dominio como subdominio)
    3. Ejecuta migraciones del tenant
    4. Opcionalmente crea usuario administrador
    5. Opcionalmente pobla datos iniciales
    
    Args:
        nombre: Nombre de la empresa
        email_admin: Email del administrador de la empresa
        poblar_datos_iniciales: Si True, pobla catálogo DIAN en el tenant (opcional)
        schema_name: Schema name (opcional, se genera desde nombre si no se proporciona)
        **kwargs: Argumentos adicionales para Client (paid_until, on_trial, etc.)
        
    Returns:
        Dict con información de la empresa creada:
        {
            'client': Client,
            'domain': Domain,
            'user': User (opcional),
            'schema_name': str
        }
        
    Raises:
        ValidationError: Si los datos son inválidos o el dominio ya existe
    """

    # Validaciones
    if not nombre or not nombre.strip():
        raise ValidationError("El nombre de la empresa es requerido")
    
    if not email_admin or not email_admin.strip():
        raise ValidationError("El email del administrador es requerido")
    
    # Generar schema_name si no se proporciona
    if not schema_name:
        schema_name = generar_schema_name(nombre)

    # 1. Crear/obtener usuario admin global usando el Service Layer
    # WARNING: CRÍTICO: Usar create_user_service para generar username único y hashear password
    user = User.objects.only("id", "email", "is_active", "password", "username").filter(email=email_admin).first()
    if not user:
        # Generar password temporal si no se proporciona (el usuario deberá cambiarlo en el primer login)
        from django.contrib.auth.models import User as BaseUser
        temp_password = BaseUser.objects.make_random_password()
        
        try:
            user = create_user_service(
                email=email_admin,
                password=temp_password,  # Password temporal, el usuario deberá cambiarlo
                is_staff=True,
                is_active=True,
            )
            user_created = True
            logger.info("OK: Usuario admin creado en public: %s (username=%s, password temporal)", email_admin, user.username)
        except IntegrityError as e:
            # Si hay conflicto de unicidad, intentar obtener el usuario existente
            logger.warning("WARNING:  Conflicto de unicidad al crear usuario %s, intentando obtener existente...", email_admin)
            user = User.objects.only("id", "email", "is_active", "password", "username").filter(email=email_admin).first()
            if not user:
                raise ValueError(f"No se pudo crear ni obtener el usuario {email_admin}: {str(e)}") from e
            logger.info("OK: Usuario obtenido después de conflicto: %s", email_admin)
            user_created = False

    # 2. Crear tenant + dominio + membership owner usando el servicio central
    client, domain, login_url = crear_tenant(
        nombre=nombre,
        admin_user_id=user.id,
        schema_name=schema_name,
        paid_until=kwargs.get("paid_until"),
        on_trial=kwargs.get("on_trial", True),
    )

    # 3.b) Si el usuario fue creado en este flujo (password temporal), generar token
    # de activación e intentar enviar email de invitación. No abortar onboarding si falla.
    try:
        if 'user_created' in locals() and user_created:
            from apps.public.tenants.services.invitations import (
                build_activation_url,
                generate_invitation_token,
                send_invitation_email,
            )
            logger.info("Generando token de invitación para nuevo admin user_id=%s, tenant_id=%s", user.id, client.id)
            token = generate_invitation_token(user_id=user.id, tenant_id=client.id)
            activation_url = build_activation_url(domain.domain, token)
            logger.info("Invocando send_invitation_email para nuevo admin %s", user.email)
            sent = send_invitation_email(user, client, activation_url)
            if sent:
                logger.info("Email de activación enviado para user=%s tenant=%s", user.email, client.schema_name)
                # Incluir activation_url en el return payload
                return_payload = {
                    'client': client,
                    'domain': domain,
                    'user': user,
                    'schema_name': schema_name,
                    'activation_url': activation_url,
                }
                return return_payload
            else:
                logger.warning("No se pudo enviar email de activación para user=%s", user.email)
    except Exception as e:
        logger.error("ERROR enviando invitación para nuevo admin %s en tenant %s: %s", user.email, schema_name, str(e), exc_info=True)

    # 3. (Opcional) Poblar datos iniciales en el schema del tenant
    if poblar_datos_iniciales:
        # El catálogo DIAN está en SHARED_APPS, por lo que ya está disponible.
        # Si en el futuro necesitas datos específicos por tenant, este es el lugar.
        pass

    return {
        'client': client,
        'domain': domain,
        'user': user,
        'schema_name': schema_name,
    }


def verificar_empresa(schema_name: str) -> bool:
    """
    Verifica que una empresa (tenant) existe y está correctamente configurada.
    
    Args:
        schema_name: Nombre del esquema del tenant
        
    Returns:
        True si la empresa existe y está configurada correctamente
    """
    try:
        client = Client.objects.get(schema_name=schema_name)
        domain = Domain.objects.only("id", "domain", "is_primary", "tenant_id").filter(tenant=client, is_primary=True).first()
        schema_exists_check = schema_exists(schema_name)
        
        return client is not None and domain is not None and schema_exists_check
    except Client.DoesNotExist:
        return False
