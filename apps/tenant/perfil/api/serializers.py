"""
Serializers para la app de perfil.

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.tenant.perfil.api.permissions import get_available_actions, get_permissions_context
from apps.tenant.perfil.models import TenantProfile, RolTenant, Departamento

User = get_user_model()


class UserNestedSerializer(serializers.ModelSerializer):
    """
    Serializer anidado para datos básicos del User global.
    
    WARNING: IMPORTANTE: Este serializer solo expone datos básicos del User
    para mostrar en el frontend. NO permite modificar el User desde aquí.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name']


class TenantProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo TenantProfile.
    
    WARNING: v2.30: Contrato canónico para consumo desde workspace.html
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

    # Acciones disponibles para el usuario que realiza la peticion (basado en su rol)
    available_actions = serializers.SerializerMethodField()

    # Contexto de permisos UI: habilita/deshabilita modulos de configuracion en frontend
    permissions_context = serializers.SerializerMethodField()

    # Departamento UUID / Nombre integration
    departamento_uuid = serializers.SlugRelatedField(
        queryset=Departamento.objects.all(),
        slug_field='uuid',
        source='departamento',
        required=False,
        allow_null=True
    )
    departamento_nombre = serializers.CharField(source='departamento.nombre', read_only=True)

    # Sedes and Areas integration via UUID lists and details
    sedes_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    areas_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    sedes_detalles = serializers.SerializerMethodField(read_only=True)
    areas_detalles = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TenantProfile
        fields = [
            'id',
            'user_id',
            'user_email',
            'user_username',
            'user_first_name',
            'user_last_name',
            'user_full_name',
            'cargo',
            'departamento',
            'departamento_uuid',
            'departamento_nombre',
            'telefono_corporativo',
            'avatar',
            'avatar_url',
            'configuracion',
            'rol',
            'sedes_uuids',
            'areas_uuids',
            'sedes_detalles',
            'areas_detalles',
            'available_actions',
            'permissions_context',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'user_email', 'user_username',
                          'user_first_name', 'user_last_name', 'user_full_name',
                          'avatar_url', 'available_actions', 'permissions_context',
                          'departamento_nombre', 'sedes_detalles', 'areas_detalles',
                          'created_at', 'updated_at',
                          'rol']  # [RULE 15] rol solo modificable via assign_rol endpoint
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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['sedes_uuids'] = [str(s.uuid) for s in instance.sedes_asignadas.all()]
        ret['areas_uuids'] = [str(a.uuid) for a in instance.areas_asignadas.all()]
        return ret

    def get_sedes_detalles(self, obj):
        return [
            {"uuid": str(s.uuid), "nombre": s.nombre}
            for s in obj.sedes_asignadas.all()
        ]

    def get_areas_detalles(self, obj):
        return [
            {
                "uuid": str(a.uuid),
                "nombre": a.nombre,
                "sede_uuid": str(a.sede.uuid) if a.sede else None,
                "sede_nombre": a.sede.nombre if a.sede else None
            }
            for a in obj.areas_asignadas.all()
        ]
    
    def get_user_full_name(self, obj):
        """
        Retorna el nombre completo del usuario (first_name + last_name).
        
        WARNING: v2.30: Campo esperado por workspace.html
        """
        parts = [obj.user.first_name, obj.user.last_name]
        return ' '.join(filter(None, parts)) or obj.user.email
    
    def get_avatar_url(self, obj):
        """
        Retorna la URL absoluta del avatar si existe.
        """
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_available_actions(self, obj):
        """[RULE 12] Retorna la lista de acciones permitidas para el solicitante.

        Usa el rol del perfil del usuario que realiza la peticion (no el objeto
        serializado) para determinar que botones/acciones debe mostrar la UI.
        Retorna [] si el request no contiene un usuario autenticado con perfil.
        """
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return []
        requester_perfil = getattr(request.user, 'tenant_profile', None)
        if not requester_perfil:
            return []
        return get_available_actions(requester_perfil)

    def get_permissions_context(self, obj):
        """[AUTO-ADMIN] Devuelve el contexto de permisos del solicitante para la UI.

        Calcula is_owner via TenantMembership.is_primary_admin (DSV: schema activo).
        El resultado habilita/deshabilita modulos de configuracion en el frontend
        (Tabulator actionsFormatter, botones de accion, settings panel).
        """
        request = self.context.get('request')
        if not request or not getattr(request, 'user', None):
            return {}
        requester_perfil = getattr(request.user, 'tenant_profile', None)
        if not requester_perfil:
            return {}
        return get_permissions_context(requester_perfil, user=request.user)

    def validate_configuracion(self, value):
        """
        Validar y normalizar configuracion.
        
        WARNING: v2.30: Normaliza null a {} para evitar errores 400.
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
    
    WARNING: v2.30: Serializer específico para PATCH /api/v1/perfil/perfiles/me/
    - Solo incluye campos editables: cargo, departamento, departamento_uuid, telefono_corporativo, configuracion
    - Todos los campos son opcionales (partial=True)
    - Valida que configuracion sea dict
    - Normaliza strings vacíos a None para campos opcionales
    """
    departamento_uuid = serializers.SlugRelatedField(
        queryset=Departamento.objects.all(),
        slug_field='uuid',
        source='departamento',
        required=False,
        allow_null=True
    )

    class Meta:
        model = TenantProfile
        fields = ['cargo', 'departamento', 'departamento_uuid', 'telefono_corporativo', 'configuracion']
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
        """
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("La configuracion debe ser un objeto JSON valido.")
        return value


class TenantProfileRolSerializer(serializers.Serializer):
    """[RULE 5] Serializer para el endpoint assign_rol.

    Valida que el valor de 'rol' sea uno de los choices definidos en RolTenant.
    Solo expone el campo 'rol' para minimizar la superficie de escritura.
    """
    rol = serializers.ChoiceField(
        choices=RolTenant.choices,
        help_text="Rol a asignar: 'ADMIN', 'OPERADOR' o 'VISOR'.",
    )


class DepartamentoListSerializer(serializers.ModelSerializer):
    """
    Serializer para listado de Departamento.
    """
    class Meta:
        model = Departamento
        fields = ['uuid', 'nombre', 'descripcion', 'activo', 'created_at', 'updated_at']
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class DepartamentoDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle de Departamento.
    """
    class Meta:
        model = Departamento
        fields = ['uuid', 'nombre', 'descripcion', 'activo', 'created_at', 'updated_at']
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class PerfilCreateSerializer(serializers.Serializer):
    """
    Serializer para creacion/invitacion de un nuevo colaborador (TenantProfile + User).
    """
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    rol = serializers.ChoiceField(choices=RolTenant.choices, default=RolTenant.OPERADOR)
    cargo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    telefono_corporativo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    departamento_uuid = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sedes_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    areas_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )

