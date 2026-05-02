"""
Serializers mínimos para la API de consola.

Solo expone campos necesarios para la UI, evitando información sensible.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.public.tenants.models import Client, Domain

User = get_user_model()


class TenantListSerializer(serializers.ModelSerializer):
    """Serializer mínimo para listado de tenants en DataTables."""

    primary_domain = serializers.CharField(read_only=True, allow_null=True)

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
        )


class TenantDomainSerializer(serializers.ModelSerializer):
    """Serializer mínimo para dominios de tenants."""

    class Meta:
        model = Domain
        fields = ("id", "domain", "is_primary")


class ConsoleUserListSerializer(serializers.ModelSerializer):
    """Serializer mínimo para listado de usuarios globales en la consola."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "date_joined",
            "telefono",
        )
