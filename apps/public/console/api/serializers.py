"""
Serializers mínimos para la API de consola.

Solo expone campos necesarios para la UI, evitando información sensible.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.public.tenants.models import Client, Domain

User = get_user_model()


class TenantListSerializer(serializers.ModelSerializer):
    """Serializer para listado de tenants en DataTables."""

    primary_domain = serializers.CharField(read_only=True, allow_null=True)
    # Annotated by TenantsDataTableView — no extra query per row
    owner_email = serializers.CharField(read_only=True, allow_null=True)
    owner_activated = serializers.SerializerMethodField()

    def get_owner_activated(self, obj):
        """True si el owner ya tiene contrasena usable (no empieza con '!')."""
        pw = getattr(obj, "owner_password", None)
        if pw is None:
            return None
        return not pw.startswith("!")

    class Meta:
        model = Client
        fields = (
            "id",
            "nombre",
            "schema_name",
            "is_active",
            "on_trial",
            "paid_until",
            "created_on",
            "primary_domain",
            "owner_email",
            "owner_activated",
        )


class TenantDomainSerializer(serializers.ModelSerializer):
    """Serializer mínimo para dominios de tenants."""

    class Meta:
        model = Domain
        fields = ("id", "domain", "is_primary")


class UserTenantMembershipSerializer(serializers.Serializer):
    """Miniatura de la membresia de un usuario en un tenant."""
    tenant_id = serializers.IntegerField(source="client.id")
    nombre = serializers.CharField(source="client.nombre")
    schema_name = serializers.CharField(source="client.schema_name")
    primary_domain = serializers.SerializerMethodField()
    rol = serializers.CharField()
    is_primary_admin = serializers.BooleanField()
    is_active = serializers.BooleanField()

    def get_primary_domain(self, obj):
        domain = getattr(obj, "_primary_domain", None)
        return domain


class ConsoleUserListSerializer(serializers.ModelSerializer):
    """
    Serializer para listado de usuarios globales con sus tenants asignados.
    Solo se usa para usuarios visibles en la consola (system admins + tenant owners).
    """

    tenants = serializers.SerializerMethodField()
    tipo_usuario = serializers.SerializerMethodField()

    def get_tenants(self, obj):
        from django.conf import settings
        domain_base = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")
        protocol = getattr(settings, "SITE_PROTOCOL", "https")

        memberships = getattr(obj, "_tenant_memberships", None)
        if memberships is None:
            return []
        result = []
        for m in memberships:
            schema = m.client.schema_name if m.client else ""
            domain_url = f"{protocol}://{schema}.{domain_base}" if schema else ""
            result.append({
                "tenant_id": m.client_id,
                "nombre": m.client.nombre if m.client else "",
                "schema_name": schema,
                "domain_url": domain_url,
                "rol": m.rol,
                "is_primary_admin": m.is_primary_admin,
                "is_active": m.is_active,
            })
        return result

    def get_tipo_usuario(self, obj):
        """
        Clasifica el usuario segun su rol en el sistema:
          SYSTEM_ADMIN  → is_staff=True AND is_superuser=True
          TENANT_OWNER  → tiene TenantMembership.is_primary_admin=True
          UNKNOWN       → no deberia aparecer en la consola (filtrado incompleto)
        """
        if getattr(obj, "is_superuser", False) and getattr(obj, "is_staff", False):
            return "SYSTEM_ADMIN"
        memberships = getattr(obj, "_tenant_memberships", None) or []
        if any(m.is_primary_admin for m in memberships):
            return "TENANT_OWNER"
        return "UNKNOWN"

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "telefono",
            "tenants",
            "tipo_usuario",
        )


class ConsoleUserDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para CRUD de usuarios en la consola."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "telefono",
            "password",
        )
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "last_login": {"read_only": True},
            "date_joined": {"read_only": True},
            "id": {"read_only": True},
        }

    def create(self, validated_data):
        """Crear usuario con contraseña hasheada."""
        password = validated_data.pop("password", None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        """Actualizar usuario, hasheando contraseña si se proporciona."""
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
