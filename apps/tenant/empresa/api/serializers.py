"""
Serializers para la app empresa.

# WARNING: v2.40: Alineado con Tabulator Factory v2.40 y lazy loading.

# WARNING: CONTRATO CANÓNICO (DTO): Este serializer define el contrato estable de datos empresariales.
Todas las TENANT_APPS deben consumir este contrato vía API o servicio provider.

# WARNING: AUTONOMÍA: Esta app es completamente autónoma y no depende de apps/public/impuestos.
Los choices se definen localmente en apps/tenant/empresa/choices/

Referencia: https://www.django-rest-framework.org/api-guide/serializers/
"""
from django.utils import timezone
from django.utils.timesince import timesince
from rest_framework import serializers

from apps.services.security.crypto import encrypt_password
from apps.tenant.api.utils import NormalizationMixin
from apps.tenant.empresa.models import Area, Empresa, MailInboxConfig, Sede


class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """Acepta UUID publico o PK entero — patron SINTEL para FK en formularios (AGENTS.md §27)."""

    def to_internal_value(self, data):
        if data in (None, ''):
            if self.allow_null:
                return None
            self.fail('required')
        data_str = str(data).strip()
        if not data_str.isdigit():
            queryset = self.get_queryset()
            try:
                return queryset.get(uuid=data_str)
            except (TypeError, ValueError, queryset.model.DoesNotExist):
                self.fail('does_not_exist', pk_value=data)
        return super().to_internal_value(data)


class EmpresaListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado Tabulator v2.40.
    
    # WARNING: v2.40: Exposición mínima - Solo campos visibles en la tabla.
    # WARNING: Campos: id, razon_social, nit, dv, direccion, telefono, email_contacto
    # WARNING: NO incluye: logo (binario), website, regimen_tributario, moneda, timestamps
    # WARNING: Alineado con Tabulator Factory (lazy loading, paginación remota)
    """
    class Meta:
        model = Empresa
        fields = (
            'id',
            'razon_social',
            'nit',
            'dv',
            'direccion',
            'ciudad',
            'departamento',
            'telefono',
            'email',
            'activa',
            'regimen_tributario',
            'moneda',
        )
        read_only_fields = fields


class EmpresaHeaderSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para encabezado del Editor de Cotizaciones v2.60.
    
    # WARNING: v2.60: Exposición mínima para encabezado - Solo campos esenciales.
    # WARNING: Campos: id, razon_social, nit, logo (URL absoluta)
    # WARNING: Propósito: Exponer datos básicos de la empresa emisora para el encabezado del Editor de Cotizaciones.
    """
    logo = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = (
            'id',
            'razon_social',
            'nit',
            'logo',
        )
        read_only_fields = fields
    
    def get_logo(self, obj):
        """Retorna URL absoluta del logo si existe."""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class EmpresaDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle (campos extendidos).
    
    # WARNING: Incluye logo, website y otros campos opcionales.
    """
    logo = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = (
            'id',
            'razon_social',
            'nit',
            'dv',
            'direccion',
            'ciudad',
            'departamento',
            'telefono',
            'email',
            'activa',
            'regimen_tributario',
            'logo',
            'website',
            'moneda',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_logo(self, obj):
        """Retorna URL absoluta del logo si existe."""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class EmpresaUpsertSerializer(NormalizationMixin, serializers.ModelSerializer):
    # Only normalize technical fields (nit). Keep `razon_social` case-preserving.
    normalization_fields = ['nit']
    """
    Serializer para create/update (input validation).
    
    # WARNING: Valida singleton: si ya existe una empresa y se intenta crear, retorna 409.
    # WARNING: IMPORTANTE: singleton_key NO debe estar en fields (es editable=False y se establece automáticamente).
    """
    class Meta:
        model = Empresa
        fields = (
            'razon_social',
            'nit',
            'dv',
            'direccion',
            'ciudad',
            'departamento',
            'telefono',
            'email',
            'activa',
            'regimen_tributario',
            'logo',
            'website',
            'moneda',
        )
        read_only_fields = ('dv',)
        # # WARNING: singleton_key NO debe estar en fields (editable=False, se establece automáticamente con default=1)
        extra_kwargs = {
            'razon_social': {'required': True},
            'nit': {'required': True},
            'direccion': {'required': False, 'allow_blank': True},
            'ciudad': {'required': False, 'allow_blank': True},
            'departamento': {'required': False, 'allow_blank': True},
            'telefono': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'activa': {'required': False},
            'regimen_tributario': {'required': False, 'allow_blank': True, 'default': 'NO_RESPONDE'},
            'logo': {'required': False, 'allow_null': True},
            'website': {'required': False, 'allow_blank': True},
            'moneda': {'required': False, 'allow_blank': True, 'default': 'COP'},
        }
    
    def validate_nit(self, value):
        """Valida formato de NIT."""
        if not value:
            raise serializers.ValidationError("El NIT es obligatorio")
        nit_limpio = str(value).replace('-', '').replace(' ', '').strip()
        if not nit_limpio.isdigit():
            raise serializers.ValidationError("El NIT debe contener solo números")
        if len(nit_limpio) < 8 or len(nit_limpio) > 10:
            raise serializers.ValidationError("El NIT debe tener entre 8 y 10 dígitos")
        return nit_limpio
    
    def validate_dv(self, value):
        """Valida formato de DV."""
        if value:
            dv_str = str(value).strip()
            if len(dv_str) > 2:
                raise serializers.ValidationError("El DV debe tener máximo 2 caracteres")
            if not dv_str.isdigit():
                raise serializers.ValidationError("El DV debe ser numérico")
        return value
    
    def validate_email_contacto(self, value):
        """Normaliza email a minúsculas."""
        if value:
            return value.lower().strip()
        return value
    
    def validate(self, attrs):
        """Validación a nivel de objeto: singleton."""
        if self.instance is None:
            # Solo considerar la existencia de la instancia SSoT (singleton_key=1)
            if Empresa.objects.filter(singleton_key=1).exists():
                raise serializers.ValidationError({
                    'non_field_errors': ['Ya existe una Empresa en este tenant. Use PATCH o PUT para actualizar.']
                })
        return attrs


# --- Serializers para configuraciones de buzones de correo (SSoT) ---
import logging

log = logging.getLogger("mailinbox.api")


class MailInboxConfigListSerializer(serializers.ModelSerializer):
    """
    Serializer para LIST (campos operativos mínimos, Tabulator v2.40).
    
    # WARNING: NORMA DE EXPOSICIÓN: Solo campos necesarios para mostrar estado.
    # WARNING: SEGURIDAD: NUNCA expone password, username completo, ni secretos.
    # WARNING: v2.40: Alineado con Tabulator Factory (paginación remota).
    """
    status = serializers.SerializerMethodField()
    last_sync_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MailInboxConfig
        fields = (
            "id",
            "nombre",
            "email_address",
            "provider",
            "protocol",
            "imap_host",
            "imap_port",
            "imap_ssl",
            "is_active",
            "status",
            "last_sync_display",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
    
    def get_status(self, obj):
        """Estado operativo calculado (sin exponer secretos)."""
        if not obj.is_active:
            return "inactive"
        return "active"
    
    def get_last_sync_display(self, obj):
        """Última sincronización formateada."""
        if hasattr(obj, 'updated_at') and obj.updated_at:
            return timesince(obj.updated_at, timezone.now())
        return None


class MailInboxConfigDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para DETAIL (campos extendidos, sin secretos).
    
    # WARNING: SEGURIDAD:
    - password es write_only (nunca se devuelve)
    - username se expone parcialmente (solo dominio si aplica)
    - Cifrado automático de passwords al guardar
    """
    imap_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        help_text="Contraseña o App Password para IMAP (Gmail: requiere App Password si 2FA activo). Solo necesario al crear."
    )
    smtp_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=False,
        help_text="Contraseña o App Password para SMTP (opcional, por defecto usa imap_password)"
    )
    username_display = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = MailInboxConfig
        fields = (
            "id",
            "nombre",
            "email_address",
            "provider",
            "host",
            "port",
            "protocol",
            "ssl",
            "username",
            "password",
            "mailbox",
            "mark_as_seen",
            "move_processed_to",
            "max_attachment_mb",
            "imap_host",
            "imap_port",
            "imap_ssl",
            "imap_starttls",
            "imap_username",
            "imap_password",
            "imap_mailbox",
            "imap_mark_as_seen",
            "imap_move_processed_to",
            "imap_max_attachment_mb",
            "smtp_host",
            "smtp_port",
            "smtp_ssl",
            "smtp_starttls",
            "smtp_username",
            "smtp_password",
            "is_active",
            "username_display",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "username_display", "status")
        extra_kwargs = {
            "password": {"write_only": True},
            "imap_password": {"write_only": True},
            "smtp_password": {"write_only": True},
        }
    
    def get_username_display(self, obj):
        """Muestra username parcialmente (solo dominio si aplica) para no exponer completo."""
        username = obj.imap_username or obj.username or obj.email_address
        if not username:
            return None
        if "@" in username:
            return f"***@{username.split('@')[1]}"
        return f"***{username[-4:]}" if len(username) > 4 else "***"
    
    def get_status(self, obj):
        """Estado operativo calculado."""
        if not obj.is_active:
            return "inactive"
        return "active"
    
    def validate_imap_port(self, value):
        """Valida que el puerto IMAP esté en rango válido."""
        if value and not (1 <= value <= 65535):
            raise serializers.ValidationError("El puerto IMAP debe estar entre 1 y 65535.")
        return value
    
    def validate_smtp_port(self, value):
        """Valida que el puerto SMTP esté en rango válido."""
        if value and not (1 <= value <= 65535):
            raise serializers.ValidationError("El puerto SMTP debe estar entre 1 y 65535.")
        return value
    
    def validate_imap_max_attachment_mb(self, value):
        """Valida que imap_max_attachment_mb esté en rango (1-50)."""
        if value and not (1 <= value <= 50):
            raise serializers.ValidationError("imap_max_attachment_mb debe estar entre 1 y 50 MB.")
        return value
    
    def validate(self, attrs):
        """Validación cruzada: si provider == 'gmail', forzar presets."""
        provider = attrs.get('provider', getattr(self.instance, 'provider', 'custom') if self.instance else 'custom')
        
        is_create = self.instance is None
        if is_create and not attrs.get('imap_password') and not attrs.get('password'):
            raise serializers.ValidationError({
                'imap_password': 'La contraseña IMAP es obligatoria al crear una nueva configuración.'
            })
        
        if provider == 'gmail':
            attrs['imap_host'] = 'imap.gmail.com'
            attrs['imap_port'] = 993
            attrs['imap_ssl'] = True
            attrs['imap_starttls'] = False
            
            if 'smtp_host' not in attrs or not attrs.get('smtp_host'):
                attrs['smtp_host'] = 'smtp.gmail.com'
            if 'smtp_port' not in attrs or not attrs.get('smtp_port'):
                attrs['smtp_port'] = 587
            if 'smtp_starttls' not in attrs:
                attrs['smtp_starttls'] = True
            if 'smtp_ssl' not in attrs:
                attrs['smtp_ssl'] = False
            
            if attrs.get('smtp_port') == 465:
                attrs['smtp_ssl'] = True
                attrs['smtp_starttls'] = False
            elif attrs.get('smtp_port') == 587:
                attrs['smtp_ssl'] = False
                attrs['smtp_starttls'] = True
        
        return attrs
    
    def create(self, validated_data):
        """Crea configuracion cifrando passwords y asignando empresa desde request.user.tenant_profile.empresa (SSoT, anti-IDOR)."""
        request = self.context.get('request')
        empresa = None
        if request and hasattr(request.user, 'tenant_profile') and request.user.tenant_profile:
            empresa = request.user.tenant_profile.empresa
        if not empresa:
            # Fallback: Singleton de Empresa en el tenant actual (django-tenants schema isolation)
            empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise serializers.ValidationError({
                'empresa': 'No se pudo determinar la empresa del usuario autenticado.'
            })
        validated_data['empresa'] = empresa
        if 'imap_password' in validated_data and validated_data['imap_password']:
            try:
                validated_data['imap_password'] = encrypt_password(validated_data['imap_password'])
            except Exception as e:
                log.error(f"Error cifrando imap_password: {e}")
        if 'smtp_password' in validated_data and validated_data.get('smtp_password'):
            try:
                validated_data['smtp_password'] = encrypt_password(validated_data['smtp_password'])
            except Exception as e:
                log.error(f"Error cifrando smtp_password: {e}")
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Actualiza configuración cifrando passwords si se proporcionan."""
        if 'imap_password' in validated_data and validated_data['imap_password']:
            try:
                validated_data['imap_password'] = encrypt_password(validated_data['imap_password'])
            except Exception as e:
                log.error(f"Error cifrando imap_password: {e}")
        
        if 'smtp_password' in validated_data and validated_data.get('smtp_password'):
            try:
                validated_data['smtp_password'] = encrypt_password(validated_data['smtp_password'])
            except Exception as e:
                log.error(f"Error cifrando smtp_password: {e}")
        
        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        """Asegurar que passwords NUNCA se expongan en respuestas."""
        data = super().to_representation(instance)
        for field in ['password', 'imap_password', 'smtp_password']:
            data.pop(field, None)
        return data


class MailInboxConfigTestConnectionSerializer(serializers.Serializer):
    """
    Serializer dedicado para test-connection (no persiste datos).
    
    # WARNING: v2.40: Alineado con arquitectura API-First.
    """
    host = serializers.CharField(
        required=True,
        help_text="Host del servidor IMAP/POP3 (ej: imap.gmail.com)"
    )
    port = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=65535,
        help_text="Puerto del servidor (ej: 993 para IMAPS, 143 para IMAP)"
    )
    protocol = serializers.ChoiceField(
        choices=["imap", "pop3"],
        required=True,
        help_text="Protocolo de correo: 'imap' o 'pop3'"
    )
    username = serializers.CharField(
        required=True,
        help_text="Usuario o email para autenticación"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        trim_whitespace=False,
        help_text="Contraseña o App Password (write_only, nunca se devuelve)"
    )
    use_ssl = serializers.BooleanField(
        required=True,
        help_text="True para IMAPS/POP3S (SSL/TLS), False para IMAP/POP3 sin cifrado"
    )
    use_starttls = serializers.BooleanField(
        required=False,
        default=False,
        help_text="True para usar STARTTLS (solo si use_ssl=False)"
    )
    
    def validate(self, attrs):
        """Validación cruzada: STARTTLS solo si use_ssl=False."""
        use_ssl = attrs.get('use_ssl', False)
        use_starttls = attrs.get('use_starttls', False)
        
        if use_ssl and use_starttls:
            raise serializers.ValidationError({
                'use_starttls': 'STARTTLS no se puede usar junto con SSL. Si use_ssl=True, use_starttls debe ser False.'
            })
        
        return attrs


class SedeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = (
            'id',
            'uuid',
            'nombre',
            'direccion',
            'telefono',
            'encargado_nombre',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class SedeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = (
            'id',
            'uuid',
            'nombre',
            'direccion',
            'telefono',
            'encargado_nombre',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'uuid', 'created_at', 'updated_at')


class SedeUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = (
            'nombre',
            'direccion',
            'telefono',
            'encargado_nombre',
        )
        extra_kwargs = {
            'nombre': {'required': True},
            'direccion': {'required': False, 'allow_blank': True},
            'telefono': {'required': False, 'allow_blank': True},
            'encargado_nombre': {'required': False, 'allow_blank': True},
        }

    def validate_nombre(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre de la sede es obligatorio.")
        return value.strip()


class AreaListSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    sede_uuid = serializers.UUIDField(source='sede.uuid', read_only=True)

    class Meta:
        model = Area
        fields = (
            'id',
            'uuid',
            'sede',
            'sede_uuid',
            'sede_nombre',
            'nombre',
            'codigo_funcionamiento',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AreaDetailSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    sede_uuid = serializers.UUIDField(source='sede.uuid', read_only=True)

    class Meta:
        model = Area
        fields = (
            'id',
            'uuid',
            'sede',
            'sede_uuid',
            'sede_nombre',
            'nombre',
            'codigo_funcionamiento',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'uuid', 'created_at', 'updated_at')


class AreaUpsertSerializer(serializers.ModelSerializer):
    # UUIDOrPKRelatedField acepta UUID (patron SINTEL §27) o PK entero (backward compat)
    sede = UUIDOrPKRelatedField(
        queryset=Sede.objects.none(),
        required=True,
        help_text="UUID de la sede a la que pertenece el area"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = self.context.get('empresa_id')
        if empresa_id:
            self.fields['sede'].queryset = Sede.objects.filter(empresa_id=empresa_id)
        else:
            self.fields['sede'].queryset = Sede.objects.all()

    class Meta:
        model = Area
        fields = (
            'sede',
            'nombre',
            'codigo_funcionamiento',
        )
        extra_kwargs = {
            'nombre': {'required': True},
            'codigo_funcionamiento': {'required': True},
        }

    def validate_nombre(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre del area es obligatorio.")
        return value.strip()

    def validate_codigo_funcionamiento(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("El codigo de funcionamiento es obligatorio.")
        return value.strip()
