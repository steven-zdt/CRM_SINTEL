from django.contrib.auth import get_user_model, authenticate
from django.db import connection
from django.conf import settings
from django_tenants.utils import get_public_schema_name
from rest_framework import serializers


User = get_user_model()


class TenantPublicInfoSerializer(serializers.Serializer):
    """
    Información pública básica del tenant actual.
    Se alimenta desde request.tenant (esquema actual).
    
    ⚠️ POLÍTICA DE BRANDING: Incluye información de branding desde Empresa.
    No se permiten hardcodes de marca.
    """

    name = serializers.CharField(source="nombre")
    nombre = serializers.CharField()  # Campo sin source redundante (nombre del campo = nombre del atributo)
    schema_name = serializers.CharField()
    is_active = serializers.BooleanField()
    domain = serializers.SerializerMethodField()
    branding = serializers.SerializerMethodField()

    def get_domain(self, obj):
        """
        Devuelve el dominio principal registrado para este tenant (en esquema public).
        """
        from apps.tenant.core.services.membership import get_primary_domain
        return get_primary_domain(obj)
    
    def get_branding(self, obj):
        """
        Obtiene información de branding desde Empresa (modelo del tenant).
        
        ⚠️ POLÍTICA: Todo branding viene de la BD, no de constantes.
        
        Returns:
            Dict con nombre, logo_url, website, moneda
        """
        request = self.context.get('request')
        if not request:
            return {
                'nombre': getattr(obj, 'nombre', 'Sistema de Gestión'),
                'logo_url': None,
                'website': None,
                'moneda': 'COP',
            }
        
        # Usar el módulo de branding centralizado
        from apps.tenant.core.branding import get_tenant_branding
        return get_tenant_branding(request)


class TenantLoginSerializer(serializers.Serializer):
    """
    Serializer para login de tenant (API-First).

    Valida credenciales y membresía activa en el tenant actual.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        """
        Valida credenciales y membresía en el tenant actual.
        """
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError({
                'email': ['Email es requerido.'] if not email else None,
                'password': ['Contraseña es requerida.'] if not password else None,
            })

        # Normalizar email
        email = email.lower().strip() if email else None

        # Autenticar usuario (busca en esquema public)
        # El backend TenantAwareBackend soporta email como username si el modelo User lo permite
        # Si el modelo User usa email como USERNAME_FIELD, authenticate(username=email) funcionará
        # Si no, necesitamos buscar el usuario por email primero
        request = self.context.get('request')
        
        # Intentar autenticar directamente con email
        user = authenticate(request=request, username=email, password=password)
        
        # Si falla, intentar buscar usuario por email y autenticar con username
        if not user:
            current_schema = connection.schema_name
            try:
                connection.set_schema_to_public()
                # Buscar usuario por email
                try:
                    user_by_email = User.objects.get(email=email, is_active=True)
                    # Intentar autenticar con el username real del usuario
                    user = authenticate(request=request, username=user_by_email.username, password=password)
                except User.DoesNotExist:
                    user = None
            finally:
                connection.set_schema(current_schema)

        if not user:
            raise serializers.ValidationError({
                'non_field_errors': ['Credenciales inválidas.']
            })

        if not user.is_active:
            raise serializers.ValidationError({
                'non_field_errors': ['Usuario inactivo.']
            })

        # Validar membresía en el tenant actual
        tenant = getattr(request, 'tenant', None) if request else None
        if not tenant:
            raise serializers.ValidationError({
                'non_field_errors': ['No se pudo determinar el tenant actual.']
            })

        # Verificar membresia via Core Membership Bridge (REGLA 2)
        from apps.tenant.core.services.membership import check_membership
        membership = check_membership(user, tenant)
        if not membership:
            # Log de intento de acceso sin membresía
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "TenantLoginSerializer: Usuario sin membresía en tenant: user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
            raise serializers.ValidationError({
                'non_field_errors': ['No tienes acceso a este tenant. Por favor, contacta al administrador.']
            })

        attrs['user'] = user
        attrs['tenant'] = tenant
        return attrs


class TenantLandingSerializer(serializers.Serializer):
    """
    Serializer para información pública del tenant en la landing page.

    Serializa el objeto request.tenant (inyectado por TenantMainMiddleware)
    y construye URLs dinámicas según el entorno (desarrollo/producción).

    ⚠️ IMPORTANTE: django-tenants inyecta el tenant en request.tenant
    después del middleware, así que este serializer debe usarse en un
    ViewSet que tenga acceso a request.
    """
    nombre = serializers.CharField(
        read_only=True,
        help_text="Nombre del tenant (empresa). Campo 'nombre' del modelo Client."
    )
    schema_name = serializers.CharField(
        read_only=True,
        help_text="Nombre del esquema del tenant"
    )
    domain_url = serializers.SerializerMethodField(
        help_text="URL base del dominio del tenant"
    )
    login_url = serializers.SerializerMethodField(
        help_text="URL de login del tenant"
    )
    dashboard_url = serializers.SerializerMethodField(
        help_text="URL del dashboard del tenant"
    )
    
    class Meta:
        fields = ['nombre', 'schema_name', 'domain_url', 'login_url', 'dashboard_url']
    
    def get_domain_url(self, obj):
        """
        Construye la URL base del dominio del tenant.
        
        En desarrollo y producción: http://{domain} o https://{domain} (puerto 80/443 implícito)
        """
        # Obtener el dominio primario del tenant
        domain = None
        if hasattr(obj, 'domains'):
            primary_domain = obj.domains.filter(is_primary=True).first()
            if primary_domain:
                domain = primary_domain.domain
        
        if not domain:
            # Fallback: usar schema_name + TENANT_DOMAIN_BASE
            domain = f"{obj.schema_name}.{settings.TENANT_DOMAIN_BASE}"
        
        # Construir URL (puerto 80/443 implícito)
        if not settings.DEBUG and getattr(settings, 'SECURE_SSL_REDIRECT', False):
            protocol = "https"
        else:
            protocol = "http"
        return f"{protocol}://{domain}"
    
    def get_login_url(self, obj):
        """
        Construye la URL de login del tenant.
        
        ⚠️ v2.30: API-First - Retorna la raíz del tenant (/)
        El frontend maneja el login desde allí usando POST /api/v1/core/auth/login/ (Core API v2.30)
        """
        domain_url = self.get_domain_url(obj)
        return f"{domain_url}/"  # v2.30: Raíz del tenant (frontend maneja login)
    
    def get_dashboard_url(self, obj):
        """
        Construye la URL del dashboard del tenant.
        
        En desarrollo y producción: http://{domain}/dashboard/ o https://{domain}/dashboard/ (puerto 80/443 implícito)
        """
        domain_url = self.get_domain_url(obj)
        return f"{domain_url}/dashboard/"


class OwnerActivationSerializer(serializers.Serializer):
    """
    Serializer para activación de owner (API-First).
    
    ⚠️ v2.30: Una sola activación - solo establece contraseña si el usuario NO tiene una usable.
    El ViewSet LandingViewSet.activate valida esto antes de llamar al serializer.
    
    Campos:
    - password1: Nueva contraseña (mínimo 8 caracteres)
    - password2: Confirmación de contraseña (debe coincidir con password1)
    
    Validaciones:
    - Token válido y no expirado
    - Usuario existe y está activo
    - Tenant coincide con el token
    - Membresía activa en el tenant
    - password1 y password2 coinciden
    - password1 mínimo 8 caracteres
    """
    
    password1 = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Nueva contraseña (mínimo 8 caracteres)"
    )
    password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Confirmación de contraseña (debe coincidir con password1)"
    )
    
    def validate(self, attrs):
        """
        Valida token, usuario, tenant y membresía, luego procesa la activación.
        
        ⚠️ v2.30: Establece la contraseña del owner (solo si no tiene una usable).
        El ViewSet LandingViewSet.activate valida que el usuario no tenga contraseña usable
        antes de llamar a este serializer.
        """
        # 1. Validar coincidencia de contraseñas
        password1 = attrs.get('password1')
        password2 = attrs.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise serializers.ValidationError({
                "password2": ["Las contraseñas no coinciden."]
            })
        
        # 2. Obtener token y request del contexto
        request = self.context.get('request')
        token = self.context.get('token')
        
        if not request or not token:
            raise serializers.ValidationError("Request o token no proporcionado en el contexto.")
        
        # 3. Validar token
        from apps.tenant.core.services.membership import verify_invitation
        payload = verify_invitation(token)
        
        if not payload:
            raise serializers.ValidationError("Token de activación inválido o expirado.")
        
        # 4. Obtener usuario
        try:
            user = User.objects.get(pk=payload['user_id'], is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado o inactivo.")
        
        # 5. Obtener tenant
        tenant = getattr(request, 'tenant', None)
        if not tenant or tenant.id != payload['tenant_id']:
            raise serializers.ValidationError("El token no corresponde al tenant actual.")
        
        # 6. Validar membresia activa via Core Membership Bridge (REGLA 2)
        from apps.tenant.core.services.membership import check_membership

        membership = check_membership(user, tenant)
        
        if not membership:
            raise serializers.ValidationError("No tienes acceso a este tenant.")
        
        # 7. Establecer password (v2.30: solo si no tiene una usable - validado por la vista)
        password = attrs['password1']
        user.set_password(password)
        user.save(update_fields=['password'])
        
        # 8. Agregar usuario y tenant a validated_data para usar en la vista
        attrs['user'] = user
        attrs['tenant'] = tenant
        
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer para solicitar reset de contraseña (API-First).
    
    ⚠️ v2.30: API-First - Solo valida email y genera token Django estándar.
    No requiere autenticación.
    
    Campos:
    - email: Email del usuario que solicita el reset
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Email del usuario que solicita el reset de contraseña"
    )
    
    def validate_email(self, value):
        """
        Valida que el email exista y tenga membresía activa en el tenant actual.
        """
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            raise serializers.ValidationError("No se pudo determinar el tenant actual.")
        
        # Buscar usuario en esquema public
        current_schema = connection.schema_name
        try:
            connection.set_schema_to_public()
            
            # Buscar usuario por email
            try:
                user = User.objects.get(email=value.lower().strip(), is_active=True)
            except User.DoesNotExist:
                # No revelar si el email existe o no (seguridad)
                return value
            
            # Verificar membresía activa en el tenant
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True,
            ).first()
            
            if not membership:
                # No revelar si el email existe o no (seguridad)
                return value
            
            # Verificar que el usuario tenga contraseña usable (no es activación)
            if not user.has_usable_password():
                raise serializers.ValidationError(
                    "Este usuario aún no ha activado su cuenta. Usa el enlace de activación."
                )
            
        finally:
            connection.set_schema(current_schema)
        
        return value


class PasswordResetValidateSerializer(serializers.Serializer):
    """
    Serializer para validar token de reset de contraseña (API-First).
    
    ⚠️ v2.30: API-First - Valida uidb64 y token Django estándar.
    No requiere autenticación.
    
    Campos:
    - uidb64 o uid: User ID codificado en base64 URL-safe (acepta ambos nombres)
    - token: Token de reset generado por PasswordResetTokenGenerator
    """
    
    uidb64 = serializers.CharField(
        required=False,
        help_text="User ID codificado en base64 URL-safe (alias: uid)"
    )
    uid = serializers.CharField(
        required=False,
        help_text="User ID codificado en base64 URL-safe (alias de uidb64)"
    )
    token = serializers.CharField(
        required=True,
        help_text="Token de reset generado por PasswordResetTokenGenerator"
    )
    
    def validate(self, attrs):
        """
        Valida que el uidb64/uid y token sean válidos.
        """
        # Unificar parámetros: aceptar uid o uidb64 (ambos son equivalentes)
        uidb64 = attrs.get('uidb64') or attrs.get('uid')
        token = attrs.get('token')
        
        if not uidb64:
            raise serializers.ValidationError({
                'uidb64': ['Este campo es requerido (también acepta "uid").']
            })
        
        # Decodificar uidb64
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Token de reset inválido o expirado.")
        
        # Validar token con PasswordResetTokenGenerator
        from django.contrib.auth.tokens import default_token_generator
        
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError("Token de reset inválido o expirado.")
        
        # Verificar membresía en el tenant actual
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            raise serializers.ValidationError("No se pudo determinar el tenant actual.")
        
        current_schema = connection.schema_name
        try:
            connection.set_schema_to_public()
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True,
            ).first()
        finally:
            connection.set_schema(current_schema)
        
        if not membership:
            raise serializers.ValidationError("Token de reset inválido o expirado.")
        
        attrs['user'] = user
        attrs['tenant'] = tenant
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer para confirmar reset de contraseña (API-First).
    
    ⚠️ v2.30: API-First - Establece nueva contraseña y redirige a /login/.
    No hace auto-login (seguridad).
    
    Campos:
    - uidb64 o uid: User ID codificado en base64 URL-safe (acepta ambos nombres)
    - token: Token de reset generado por PasswordResetTokenGenerator
    - password1: Nueva contraseña (mínimo 8 caracteres)
    - password2: Confirmación de contraseña (debe coincidir con password1)
    """
    
    uidb64 = serializers.CharField(
        required=False,
        help_text="User ID codificado en base64 URL-safe (alias: uid)"
    )
    uid = serializers.CharField(
        required=False,
        help_text="User ID codificado en base64 URL-safe (alias de uidb64)"
    )
    token = serializers.CharField(
        required=True,
        help_text="Token de reset generado por PasswordResetTokenGenerator"
    )
    password1 = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Nueva contraseña (mínimo 8 caracteres)"
    )
    password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Confirmación de contraseña (debe coincidir con password1)"
    )
    
    def validate(self, attrs):
        """
        Valida token, contraseñas y establece nueva contraseña.
        """
        # 1. Validar coincidencia de contraseñas
        password1 = attrs.get('password1')
        password2 = attrs.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise serializers.ValidationError({
                "password2": ["Las contraseñas no coinciden."]
            })
        
        # 2. Validar uidb64/uid y token (reutilizar lógica de validate)
        # Unificar parámetros: aceptar uid o uidb64
        uidb64_value = attrs.get('uidb64') or attrs.get('uid')
        if not uidb64_value:
            raise serializers.ValidationError({
                'uidb64': ['Este campo es requerido (también acepta "uid").']
            })
        
        validate_serializer = PasswordResetValidateSerializer(
            data={
                'uidb64': uidb64_value,
                'token': attrs.get('token'),
            },
            context=self.context
        )
        validate_serializer.is_valid(raise_exception=True)
        
        user = validate_serializer.validated_data['user']
        tenant = validate_serializer.validated_data['tenant']
        
        # 3. Establecer nueva contraseña
        password = attrs['password1']
        
        # ⚠️ IMPORTANTE: set_password y save explícito
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(
            "PasswordResetConfirmSerializer: Estableciendo nueva contraseña para user=%s, tenant=%s",
            user.email, tenant.schema_name
        )
        
        user.set_password(password)
        # Guardar explícitamente el campo password para asegurar persistencia
        user.save(update_fields=['password'])
        
        # Verificar que el password quedó usable
        user.refresh_from_db()
        if not user.has_usable_password():
            logger.error(
                "PasswordResetConfirmSerializer: Password NO usable después de set_password: user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
            raise serializers.ValidationError({
                'non_field_errors': ['Error al establecer la nueva contraseña. Por favor, intenta nuevamente.']
            })
        
        logger.info(
            "PasswordResetConfirmSerializer: Password establecido exitosamente (usable confirmado): user=%s, tenant=%s",
            user.email, tenant.schema_name
        )
        
        # 4. Agregar usuario y tenant a validated_data
        attrs['user'] = user
        attrs['tenant'] = tenant
        
        return attrs
