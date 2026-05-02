"""
Serializers para la app accounts (API-First).

WARNING: IMPORTANTE:
- UserListSerializer: Solo lectura, campos mínimos
- UserCreateSerializer: Creación con password (write_only)
- UserUpdateSerializer: Actualización parcial con password opcional

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer para listado y detalle de usuarios (solo lectura).

    WARNING: SEGURIDAD: No expone password ni información sensible.
    """

    class Meta:
        model = User
        fields = (
            "username",
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "date_joined",
            "telefono",
        )
        read_only_fields = ("id", "email", "date_joined", "username")


class UserCreateSerializer(serializers.Serializer):
    """
    Serializer para crear usuarios (con password y confirmación).

    WARNING: SEGURIDAD:
    - password y password2 son write_only (nunca se expone en respuestas)
    - Valida que las contraseñas coincidan
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    password2 = serializers.CharField(write_only=True, min_length=8, required=True)
    first_name = serializers.CharField(allow_blank=True, required=False, default="")
    last_name = serializers.CharField(allow_blank=True, required=False, default="")
    is_staff = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)
    telefono = serializers.CharField(allow_blank=True, required=False, allow_null=True)

    def validate_email(self, value):
        """Validar que el email no exista."""
        if User.objects.filter(email=value.lower().strip()).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value.lower().strip()

    def validate(self, data):
        """Validar que las contraseñas coincidan."""
        if data.get("password") != data.get("password2"):
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        return data


class UserUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar usuarios (parcial, password opcional).

    WARNING: SEGURIDAD: password es write_only y opcional.
    """

    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    is_staff = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    telefono = serializers.CharField(allow_blank=True, required=False, allow_null=True)
