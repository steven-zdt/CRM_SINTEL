"""
Serializers para la app tenants.

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""

from rest_framework import serializers

from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.public.tenants.utils import normalize_domain, validate_fqdn
from apps.public.tenants.validators import validate_schema_name
from apps.services.onboarding.empresa_service import build_primary_domain


class DomainSerializer(serializers.ModelSerializer):
    """
    Serializer para Domain.

    WARNING: IMPORTANTE: Implementa normalización automática de dominios.
    Todos los dominios se normalizan a FQDN puro (minúsculas, sin protocolo, sin rutas).
    """

    class Meta:
        model = Domain
        fields = "__all__"

    def validate_domain(self, value: str) -> str:
        """
        Normaliza y valida el dominio conforme a django-tenants.

        WARNING: REGLAS ESTRICTAS (según documentación oficial):
        - Sin protocolo (http://, https://)
        - Sin prefijo www.
        - Sin rutas (/admin/login/)
        - Sin puerto (:8000) - PROHIBIDO según doc oficial
        - FQDN puro en minúsculas (ej: cliente.sintel.net.co)

        Objetivo: Garantizar que Domain.domain siempre contenga un FQDN válido
        y limpio utilizable para enrutamiento django-tenants por hostname.
        """
        if not value:
            raise serializers.ValidationError("El dominio es requerido")

        # WARNING: VALIDACIÓN EXPLÍCITA: Rechazar dominios con puerto (según doc oficial)
        # La doc oficial de django-tenants prohíbe explícitamente puertos en Domain.domain
        if ":" in value:
            raise serializers.ValidationError(
                "Los dominios no pueden incluir puerto (ej: :8000). "
                "Use un FQDN puro sin puerto (ej: cliente.sintel.net.co)."
            )

        # Normalizar dominio (elimina protocolo, www, rutas, puerto)
        normalized = normalize_domain(value)

        if not normalized:
            raise serializers.ValidationError(
                "El dominio no puede estar vacío después de la normalización"
            )

        # Validar que sea un FQDN válido
        if not validate_fqdn(normalized):
            raise serializers.ValidationError(
                f"'{normalized}' no es un FQDN válido. "
                "Debe ser un dominio completo (ej: cliente.sintel.net.co)"
            )

        return normalized


class TenantMembershipSerializer(serializers.ModelSerializer):
    """Serializer para relación usuario-cliente."""

    user = serializers.SerializerMethodField()

    class Meta:
        model = TenantMembership
        fields = "__all__"

    def get_user(self, obj):
        """Incluir información básica del usuario."""
        if obj.user:
            return {"id": obj.user.id, "email": obj.user.email, "username": obj.user.username}
        return None


class OnboardTenantWithOwnerSerializer(serializers.Serializer):
    """
    Serializer para onboarding de tenant con propietario.

    WARNING: CONTRATO ESTABLE: Retorna dict con client_id, domain, membership_id, login_url

    Soporta dos modos:
    1. Usuario existente: admin_user_id (requerido si no se proporciona owner_email)
    2. Usuario nuevo: owner_email (requerido si no se proporciona admin_user_id)

    WARNING: CAMBIO v2.25: dominio_fqdn es OPCIONAL. Si viene vacío o inválido, se autogenera
    como <schema_name>.<TENANT_DOMAIN_BASE> (ej: cliente.sintel.net.co)

    WARNING: CAMBIO v2.29: NO se aceptan campos de password en onboarding.
    El owner se crea con set_unusable_password() y debe activar en /activate?token=...
    """

    nombre = serializers.CharField(required=True, max_length=255)
    schema_name = serializers.CharField(required=True, max_length=63)
    dominio_fqdn = serializers.CharField(required=False, allow_blank=True, max_length=255)
    admin_user_id = serializers.IntegerField(required=False, allow_null=True)
    owner_email = serializers.EmailField(required=False, allow_null=True)
    # WARNING: v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
    # REM ONBOARDING-E2E-03 (docs/e2e/ONBOARDING_E2E_REPORT.md) -- CRITICO:
    # este default era True, contradiciendo directamente el motor real
    # (apps/services/onboarding/empresa_service.py::crear_tenant_con_owner,
    # parametro owner_is_staff: bool = False -- "Owners de tenant no son
    # staff del sistema"). El formulario de consola (/console/tenants/new/)
    # no expone este campo, asi que TODO tenant creado por el flujo normal
    # heredaba is_staff=True para su owner sin que el admin que lo creaba lo
    # supiera -- verificado en vivo: con solo la contrasena establecida via
    # el endpoint legitimo de soporte, el owner podia loguearse en el admin
    # publico y listar TODOS los tenants del sistema (incluyendo clientes
    # reales) via /console/tenants/ y /api/public/v1/tenants/. Alineado con
    # el default correcto del motor.
    owner_is_staff = serializers.BooleanField(required=False, default=False)
    owner_is_active = serializers.BooleanField(required=False, default=True)
    paid_until = serializers.DateField(required=False, allow_null=True)
    on_trial = serializers.BooleanField(required=False, default=True)

    def to_internal_value(self, data):
        """
        Valida campos de password ANTES de que DRF procese los datos.

        WARNING: v2.29: Rechaza explícitamente campos de password en onboarding.
        """
        # WARNING: v2.29: Rechazar explícitamente campos de password
        forbidden_fields = {"password", "password1", "password2", "owner_password"}
        received_fields = set(map(str.lower, data.keys())) if isinstance(data, dict) else set()
        found_forbidden = forbidden_fields & received_fields

        if found_forbidden:
            raise serializers.ValidationError(
                {
                    "detail": f"No se permite establecer contraseña en el onboarding. "
                    f"Campos rechazados: {', '.join(found_forbidden)}. "
                    f"El owner debe activar su cuenta en /activate?token=... para establecer su contraseña."
                }
            )

        # Llamar al método padre para procesamiento normal
        return super().to_internal_value(data)

    def validate_schema_name(self, value: str) -> str:
        """
        Normaliza y valida schema_name.

        Reglas:
        - Máximo 63 caracteres (límite PostgreSQL)
        - Solo letras, números, guiones bajos
        - Sin espacios ni caracteres especiales
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El schema_name es requerido y no puede estar vacío.")

        normalized = value.strip().lower()

        # Validar longitud
        if len(normalized) > 63:
            raise serializers.ValidationError(
                f"El schema_name no puede exceder 63 caracteres (recibido: {len(normalized)})."
            )

        # Validar formato con validador
        try:
            validate_schema_name(normalized)
        except Exception as e:
            raise serializers.ValidationError(str(e)) from e

        return normalized

    def validate_dominio_fqdn(self, value: str) -> str:
        """
        Normaliza y valida dominio_fqdn.

        WARNING: CAMBIO v2.25: Si viene vacío o inválido, se autogenera en validate().
        Aquí solo normalizamos si viene con valor.
        """
        if not value or not value.strip():
            return ""  # Permitir vacío para autogeneración en validate()

        normalized = normalize_domain(value)

        if not validate_fqdn(normalized):
            raise serializers.ValidationError(f"El dominio '{normalized}' no es un FQDN válido")

        return normalized

    def validate(self, data):
        """
        Validación final: autogenerar dominio_fqdn si viene vacío o inválido.

        WARNING: CAMBIO v2.25: Autogeneración de dominio FQDN como <schema>.<TENANT_DOMAIN_BASE>
        """
        # Validación básica (admin_user_id o owner_email)
        admin_user_id = data.get("admin_user_id")
        owner_email = data.get("owner_email")

        if not admin_user_id and not owner_email:
            raise serializers.ValidationError(
                "Se requiere 'admin_user_id' o 'owner_email' para crear un tenant"
            )

        # Autogenerar dominio_fqdn si viene vacío o inválido
        schema_name = data.get("schema_name", "").strip().lower()
        dominio_fqdn = data.get("dominio_fqdn", "").strip()

        if not dominio_fqdn or not validate_fqdn(normalize_domain(dominio_fqdn)):
            # REM ONBOARDING-E2E-01 (docs/e2e/ONBOARDING_E2E_REPORT.md): antes,
            # esta autogeneracion concatenaba f"{schema_name}.{base}" sin sanear
            # guiones bajos -- un schema_name con "_" (formato explicitamente
            # sugerido por el propio campo del formulario, ej. "mi_empresa")
            # producia un FQDN invalido (los guiones bajos no son validos en
            # labels DNS) y el onboarding fallaba con 400 pese a que el dato
            # de entrada era valido segun su propia documentacion. Se reutiliza
            # build_primary_domain() (empresa_service.py), que ya sanea
            # correctamente -- misma logica que el motor de creacion real usa,
            # sin reimplementarla aqui por segunda vez.
            try:
                data["dominio_fqdn"] = build_primary_domain(schema_name, None)
            except Exception as e:
                raise serializers.ValidationError(
                    f"No se pudo autogenerar un dominio valido para el schema '{schema_name}': {e}"
                ) from e

        return data


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer para Client.

    Campos: schema_name, nombre, paid_until.
    Validar schema_name (alphanumeric, lower).
    NO incluir domain ni subdomain como escritura.

    WARNING: OPTIMIZACIÓN: No expone membresías por defecto para API pública.
    Si se necesitan membresías, usar un serializer separado para admin.
    """

    # Relaciones de solo lectura para listado
    domains = DomainSerializer(many=True, read_only=True, source="domains.all")
    # Primary domain (v3.5) — obtener el dominio primario sin query extra
    primary_domain = serializers.SerializerMethodField()
    # WARNING: NOTA: memberships solo se incluye si se necesita (usar related_name correcto)
    # memberships = TenantMembershipSerializer(many=True, read_only=True, source='memberships.all')

    class Meta:
        model = Client
        fields = (
            "id",
            "schema_name",
            "nombre",
            "paid_until",
            "on_trial",
            "created_on",
            "is_active",
            "domains",
            "primary_domain",
        )
        read_only_fields = ("id", "created_on", "domains", "primary_domain")

    def validate_schema_name(self, value: str) -> str:
        """Normaliza y valida schema_name."""
        if not value:
            raise serializers.ValidationError("schema_name es requerido")

        normalized = value.strip().lower()

        try:
            validate_schema_name(normalized)
        except Exception as e:
            raise serializers.ValidationError(str(e)) from e

        return normalized

    def get_primary_domain(self, obj):
        """Retorna el dominio primario del tenant (v3.5)."""
        domain = obj.domains.filter(is_primary=True).first()
        return domain.domain if domain else None
