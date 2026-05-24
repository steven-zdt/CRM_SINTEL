"""
Serializers para la API de proveedores v3.5.

SINTEL v3.5: Sincronización Arquitectónica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validación Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separación List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explícitos: PROHIBIDO __all__, usar campos explícitos alineados con LIST_FIELDS y DETAIL_FIELDS (SSoT)
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

from apps.tenant.api.utils import NormalizationMixin
from ..models import Proveedor
from ..services import DETAIL_FIELDS, LIST_FIELDS


# ==============================================================================
# EXTENDED NORMALIZATION MIXIN (Module-specific enhancements)
# ==============================================================================
class ProveedorNormalizationMixin(NormalizationMixin):
    """
    Extiende NormalizationMixin canónico con métodos específicos de Proveedores.
    """
    def _get_empresa_id(self):
        """Resuelve el ID de empresa de forma segura (Zero Trust)."""
        # 1. Intentar desde contexto (SSoT para ViewSets)
        empresa_id = self.context.get('empresa_id')
        if empresa_id:
            return empresa_id

        # 2. Fallback: Empresa Singleton del Tenant
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()
        if empresa:
            return empresa.id

        raise serializers.ValidationError("No se pudo identificar la configuración de Empresa para este tenant.")


class ProveedorListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listados (Tabulator) con campos requeridos.
    
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


class ProveedorDetailSerializer(ProveedorNormalizationMixin, serializers.ModelSerializer):
    """
    Serializer completo para DETALLE/EDICIÓN de Proveedores.
    Campos alineados con DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    """
    tipo_persona_display = serializers.CharField(source='get_tipo_persona_display', read_only=True)
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    regimen_tributario_display = serializers.CharField(source='get_regimen_tributario_display', read_only=True)
    tipo_cuenta_display = serializers.CharField(source='get_tipo_cuenta_display', read_only=True)
    cuenta_contable_label = serializers.SerializerMethodField()

    class Meta:
        model = Proveedor
        fields = DETAIL_FIELDS + (
            "tipo_persona_display",
            "tipo_documento_display",
            "regimen_tributario_display",
            "tipo_cuenta_display",
            "cuenta_contable_label",
        )
        read_only_fields = ("id", "created_at", "updated_at", "empresa", "cuenta_contable_label")
    
    def validate(self, attrs):
        """Normalización estricta antes de persistir (Zero Trust)."""
        attrs = self.normalize_data(attrs)
        return attrs

    def get_cuenta_contable_label(self, obj):
        """Resuelve el label de la cuenta vía HTTP/Selector (Decoupled)."""
        if not obj.cuenta_contable_uuid:
            return None
        from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
        empresa_id = self._get_empresa_id()
        return CuentaContableSelector.get_label_by_uuid(obj.cuenta_contable_uuid, empresa_id)

    def validate_cuenta_contable_uuid(self, value):
        """Valida existencia y pertenencia al tenant (Zero Trust)."""
        if value:
            from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
            empresa_id = self._get_empresa_id()
            if not CuentaContableSelector.exists_by_uuid(value, empresa_id):
                raise serializers.ValidationError("La cuenta contable no es valida o no pertenece a su empresa.")
        return value

    def validate_codigo_contable(self, value):
        """
        Valida que el codigo contable sea un codigo nivel 6 permitido 
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
        Validación estricta del formato de email.
        El NormalizationMixin ya valida el formato, pero esta validación adicional
        asegura que el campo sea válido incluso si viene vacío.
        """
        if value:
            try:
                EmailValidator()(value.strip())
            except DjangoValidationError:
                raise serializers.ValidationError('El formato del email no es válido.')
        return value
