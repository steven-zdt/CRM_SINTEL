"""
Serializers para la app de perfil.

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from rest_framework import serializers
from apps.tenant.perfil.models import TenantProfile
from django.contrib.auth import get_user_model

User = get_user_model()


class UserNestedSerializer(serializers.ModelSerializer):
    """
    Serializer anidado para datos básicos del User global.
    
    ⚠️ IMPORTANTE: Este serializer solo expone datos básicos del User
    para mostrar en el frontend. NO permite modificar el User desde aquí.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name']


class TenantProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo TenantProfile.
    
    ⚠️ v2.30: Contrato canónico para consumo desde workspace.html
    - django-tenants maneja automáticamente el aislamiento por esquema
    - Incluye datos básicos del User global como campos de solo lectura
    - El campo `configuracion` es un JSONField para almacenar preferencias de UI
    - `avatar_url` retorna URL absoluta si existe avatar
    """
    # Campos anidados del User global (solo lectura)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_full_name = serializers.SerializerMethodField()
    
    # Avatar URL (read-only, retorna URL absoluta)
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TenantProfile
        fields = [
            'id',
            'user_id',
            'user_email',
            'user_username',
            'user_first_name',
            'user_last_name',
            'user_full_name',  # ⚠️ v2.30: Campo esperado por workspace.html
            'cargo',
            'departamento',
            'telefono_corporativo',
            'avatar',
            'avatar_url',  # ⚠️ v2.30: URL absoluta del avatar
            'configuracion',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'user_email', 'user_username', 
                          'user_first_name', 'user_last_name', 'user_full_name',
                          'avatar_url', 'created_at', 'updated_at']
        extra_kwargs = {
            'avatar': {
                'required': False,
                'allow_null': True,
            },
            'configuracion': {
                'required': False,
                'allow_null': True,
            }
        }
    
    def get_user_full_name(self, obj):
        """
        Retorna el nombre completo del usuario (first_name + last_name).
        
        ⚠️ v2.30: Campo esperado por workspace.html
        """
        parts = [obj.user.first_name, obj.user.last_name]
        return ' '.join(filter(None, parts)) or obj.user.email
    
    def get_avatar_url(self, obj):
        """
        Retorna la URL absoluta del avatar si existe.
        
        ⚠️ v2.30: Campo esperado por workspace.html
        """
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def validate_configuracion(self, value):
        """
        Validar y normalizar configuracion.
        
        ⚠️ v2.30: Normaliza null a {} para evitar errores 400.
        - Si value is None: convierte a {} (reset seguro)
        - Valida que el tipo final sea dict (no string/array/number)
        
        El campo configuracion debe ser un diccionario JSON válido.
        """
        # Normalizar None a {} (reset seguro)
        if value is None:
            return {}
        
        # Validar que sea un diccionario
        if not isinstance(value, dict):
            raise serializers.ValidationError("La configuración debe ser un objeto JSON válido.")
        
        return value


class TenantProfileMeUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualización parcial del perfil (endpoint /me/).
    
    ⚠️ v2.30: Serializer específico para PATCH /api/v1/perfil/perfiles/me/
    - Solo incluye campos editables: cargo, departamento, telefono_corporativo, configuracion
    - Todos los campos son opcionales (partial=True)
    - Valida que configuracion sea dict
    - Normaliza strings vacíos a None para campos opcionales
    """
    class Meta:
        model = TenantProfile
        fields = ['cargo', 'departamento', 'telefono_corporativo', 'configuracion']
        extra_kwargs = {
            'cargo': {
                'required': False,
                'allow_blank': True,
                'allow_null': True,
            },
            'departamento': {
                'required': False,
                'allow_blank': True,
                'allow_null': True,
            },
            'telefono_corporativo': {
                'required': False,
                'allow_blank': True,
                'allow_null': True,
            },
            'configuracion': {
                'required': False,
                'allow_null': True,
            }
        }
    
    def validate_cargo(self, value):
        """Normalizar string vacío a None."""
        if value is not None and value.strip() == '':
            return None
        return value
    
    def validate_departamento(self, value):
        """Normalizar string vacío a None."""
        if value is not None and value.strip() == '':
            return None
        return value
    
    def validate_telefono_corporativo(self, value):
        """Normalizar string vacío a None."""
        if value is not None and value.strip() == '':
            return None
        return value
    
    def validate_configuracion(self, value):
        """
        Validar y normalizar configuracion.
        
        ⚠️ v2.30: Normaliza null a {} para evitar errores 400.
        - Si value is None: convierte a {} (reset seguro)
        - Valida que el tipo final sea dict (no string/array/number)
        """
        # Normalizar None a {} (reset seguro)
        if value is None:
            return {}
        
        # Validar que sea un diccionario
        if not isinstance(value, dict):
            raise serializers.ValidationError("La configuración debe ser un objeto JSON válido.")
        
        return value
