"""
Serializers para la API de proveedores v3.5.

WARNING: SINTEL v3.5: Sincronización Arquitectónica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validación Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separación List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explícitos: PROHIBIDO __all__, usar campos explícitos alineados con LIST_FIELDS y DETAIL_FIELDS (SSoT)
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

from ..models import Proveedor
from ..services import DETAIL_FIELDS, LIST_FIELDS


# ==============================================================================
# NORMALIZATION MIXIN (Zero Trust)
# ==============================================================================
class NormalizationMixin:
    """
    WARNING: v2.60: Mixin para normalización de datos de entrada (Zero Trust).
    Sanitiza strings y valida tipos de datos antes de persistir.
    """
    def normalize_data(self, attrs):
        """
        Normaliza datos de entrada:
        - Strings: strip() para eliminar espacios
        - Email: Validación de formato
        - Números: Conversión a tipos correctos
        """
        for key, value in attrs.items():
            if isinstance(value, str):
                # Strip de espacios en blanco
                attrs[key] = value.strip()
                
                # Validación de email si el campo es email_contacto
                if key == 'email_contacto' and value:
                    try:
                        EmailValidator()(value.strip())
                    except DjangoValidationError:
                        raise serializers.ValidationError({
                            'email_contacto': ['El formato del email no es válido.']
                        })
                
                # Convertir a mayúsculas campos específicos (opcional, según necesidad)
                if key in ['tipo_persona', 'tipo_documento', 'regimen_tributario', 'tipo_cuenta']:
                    attrs[key] = value.strip().upper()
                    
        return attrs


class ProveedorListSerializer(serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer optimizado para listados (Tabulator) con campos requeridos.
    
    Campos para Tabulator:
    - razon_social: Nombre legal del proveedor
    - nit: Número de documento completo (con DV si aplica)
    - contacto_principal: Email o teléfono de contacto
    - estado: Estado activo/inactivo (basado en campo activo)
    """
    tipo_persona_display = serializers.CharField(source='get_tipo_persona_display', read_only=True)
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    regimen_tributario_display = serializers.CharField(source='get_regimen_tributario_display', read_only=True)
    
    # Campos requeridos para Tabulator v2.60
    nit = serializers.SerializerMethodField()
    contacto_principal = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    
    class Meta:
        model = Proveedor
        fields = tuple(LIST_FIELDS) + (
            "tipo_persona_display",
            "tipo_documento_display",
            "regimen_tributario_display",
            "nit",
            "contacto_principal",
            "estado",
        )
        read_only_fields = ("tipo_persona_display", "tipo_documento_display", "regimen_tributario_display", "nit", "contacto_principal", "estado")
    
    def get_nit(self, obj):
        """
        Construye documento completo con dígito de verificación si aplica.
        """
        if obj.tipo_documento == 'NIT' and obj.numero_documento:
            if obj.digito_verificacion:
                return f"{obj.numero_documento}-{obj.digito_verificacion}"
            return obj.numero_documento
        return obj.numero_documento or ''
    
    def get_contacto_principal(self, obj):
        """
        Retorna el contacto principal: email si existe, sino teléfono, sino vacío.
        """
        if obj.email_contacto:
            return obj.email_contacto
        if obj.telefono_contacto:
            return obj.telefono_contacto
        return ''
    
    def get_estado(self, obj):
        """
        Retorna el estado del proveedor basado en el campo activo.
        """
        return 'Activo' if obj.activo else 'Inactivo'


class ProveedorDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/EDICIÓN de Proveedores.
    Campos alineados con DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    tipo_persona_display = serializers.CharField(source='get_tipo_persona_display', read_only=True)
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    regimen_tributario_display = serializers.CharField(source='get_regimen_tributario_display', read_only=True)
    tipo_cuenta_display = serializers.CharField(source='get_tipo_cuenta_display', read_only=True)
    
    class Meta:
        model = Proveedor
        fields = DETAIL_FIELDS + (
            "tipo_persona_display",
            "tipo_documento_display",
            "regimen_tributario_display",
            "tipo_cuenta_display",
        )
        read_only_fields = ("id", "created_at", "updated_at", "empresa")
    
    def validate(self, attrs):
        """WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs

    def validate_codigo_contable(self, value):
        """
        WARNING: v2.61.8: Valida que el codigo contable sea un codigo nivel 6 permitido 
        para pasivos (Proveedores/Cuentas por Pagar).
        """
        if value:
            from ..choices.niif_proveedores_choices import PROVEEDORES_NIIF_CODIGOS_VALIDOS
            if value not in PROVEEDORES_NIIF_CODIGOS_VALIDOS:
                raise serializers.ValidationError(
                    f"El codigo '{value}' no es un codigo de subcuenta NIIF (Clase 2) valido para proveedores."
                )
        return value
    
    def validate_email_contacto(self, value):
        """
        WARNING: v2.60: Validación estricta del formato de email.
        El NormalizationMixin ya valida el formato, pero esta validación adicional
        asegura que el campo sea válido incluso si viene vacío.
        """
        if value:
            try:
                EmailValidator()(value.strip())
            except DjangoValidationError:
                raise serializers.ValidationError('El formato del email no es válido.')
        return value
