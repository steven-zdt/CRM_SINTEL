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
from apps.tenant.empresa.models import Empresa
from ..models import Proveedor, CuentasPagar
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
    cuentas_pagar_resumen = serializers.SerializerMethodField()

    class Meta:
        model = Proveedor
        fields = tuple(LIST_FIELDS) + (
            "tipo_persona_display",
            "tipo_documento_display",
            "regimen_tributario_display",
            "nit",
            "contacto_principal",
            "estado",
            "cuentas_pagar_resumen",
        )
        read_only_fields = (
            "tipo_persona_display", "tipo_documento_display",
            "regimen_tributario_display", "nit", "contacto_principal",
            "estado", "cuentas_pagar_resumen",
        )
    
    def get_nit(self, obj):
        """
        Construye documento completo con digito de verificacion si aplica.
        """
        if obj.tipo_documento == 'NIT' and obj.numero_documento:
            if obj.digito_verificacion:
                return f"{obj.numero_documento}-{obj.digito_verificacion}"
            return obj.numero_documento
        return obj.numero_documento or ''
    
    def get_contacto_principal(self, obj):
        """
        Retorna el contacto principal: email si existe, sino telefono, sino vacio.
        """
        if obj.email_contacto:
            return obj.email_contacto
        if obj.telefono_contacto:
            return obj.telefono_contacto
        return ''
    
    def get_estado(self, obj):
        return 'Activo' if obj.activo else 'Inactivo'

    def get_cuentas_pagar_resumen(self, obj):
        """
        Lee del contexto el dict pre-calculado por el ViewSet (cero queries extra).
        Estructura: {pendiente_count, pendiente_monto, pagada_count, total_count}
        """
        cuentas_pagar_map = self.context.get('cuentas_pagar_map', {})
        resumen = cuentas_pagar_map.get(str(obj.uuid))
        if not resumen:
            return {'pendiente_count': 0, 'pendiente_monto': '0', 'pagada_count': 0, 'total_count': 0}
        return {
            'pendiente_count': resumen['pendiente_count'],
            'pendiente_monto': str(resumen['pendiente_monto']),
            'pagada_count':    resumen['pagada_count'],
            'total_count':     resumen['total_count'],
        }


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
        """
        Normalización estricta + anti-duplicidad (FASE 4 / Zero Trust).
        - Normaliza todos los campos de entrada.
        - Valida unicidad (empresa, tipo_documento, numero_documento):
          CREATE (instance=None) → rechaza si el documento ya existe.
          UPDATE (instance!=None) → rechaza si existe en OTRO registro.
        """
        attrs = self.normalize_data(attrs)

        empresa_id       = self.context.get('empresa_id')
        numero_documento = attrs.get('numero_documento')
        tipo_documento   = attrs.get('tipo_documento')

        if numero_documento and tipo_documento and empresa_id:
            # Normalizar (idéntico a ProveedorBusinessService.normalize_document_number)
            import re
            num_norm = re.sub(r"[\s\.\-]", "", str(numero_documento)).upper()
            attrs['numero_documento'] = num_norm

            qs = Proveedor.objects.filter(
                empresa_id=empresa_id,
                tipo_documento=tipo_documento,
                numero_documento=num_norm,
            )
            if self.instance is not None:
                # UPDATE: excluir el registro actual para no colisionar consigo mismo
                qs = qs.exclude(pk=self.instance.pk)

            if qs.only("id").exists():
                raise serializers.ValidationError({
                    "numero_documento": [
                        f"Ya existe un Proveedor registrado con el documento "
                        f"{tipo_documento} {num_norm} en su organización."
                    ]
                })

        return attrs

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


# ==============================================================================
# FacturaCxPListSerializer — lee Factura COMPRA y la presenta como CxP
# Fuente de verdad para el listado de Cuentas por Pagar (Bounded Context §18)
# ==============================================================================

class FacturaCxPListSerializer(serializers.Serializer):
    """
    Serializer de solo lectura que adapta Factura(naturaleza=COMPRA) → formato CxP.

    Mapeos:
      Factura.numero            → numero_factura
      Factura.emisor_razon_social → proveedor_nombre  (en COMPRA el emisor es el proveedor)
      Factura.total             → valor_total
      Factura.total (si pendiente) o 0 → saldo
      Factura.payment_due_date  → fecha_vencimiento
      Factura.estado_pago (mapped) → estado_pago (SIN_PAGO | PARCIAL | PAGADA)
      Factura.uuid              → uuid
    """
    uuid             = serializers.UUIDField(read_only=True)
    numero_factura   = serializers.CharField(source='numero', read_only=True)
    proveedor_nombre = serializers.CharField(source='emisor_razon_social', read_only=True)
    proveedor_nit    = serializers.CharField(source='emisor_nit', read_only=True)
    valor_total      = serializers.DecimalField(source='total', max_digits=15, decimal_places=2, read_only=True)
    saldo            = serializers.SerializerMethodField()
    fecha_vencimiento = serializers.DateField(source='payment_due_date', read_only=True)
    fecha_emision    = serializers.DateTimeField(read_only=True)
    estado_pago      = serializers.SerializerMethodField()
    estado_pago_display = serializers.SerializerMethodField()
    factura_uuid     = serializers.UUIDField(source='uuid', read_only=True)

    def get_estado_pago(self, obj):
        """Traduce estado Factura → estado CxP para el JS."""
        mapa = {
            'NO_PAGADA':    'SIN_PAGO',
            'PAGO_PARCIAL': 'PARCIAL',
            'PAGADA':       'PAGADA',
        }
        return mapa.get(obj.estado_pago, 'SIN_PAGO')

    def get_estado_pago_display(self, obj):
        mapa = {
            'NO_PAGADA':    'Sin pago',
            'PAGO_PARCIAL': 'Pago parcial',
            'PAGADA':       'Pagada',
        }
        return mapa.get(obj.estado_pago, 'Sin pago')

    def get_saldo(self, obj):
        """Saldo = total si no pagada/parcial, 0 si pagada."""
        from decimal import Decimal
        if obj.estado_pago == 'PAGADA':
            return str(Decimal('0.00'))
        return str(obj.total or Decimal('0.00'))


# ==============================================================================
# CuentasPagar Serializers — modelo unificado de cuentas por pagar
# ==============================================================================

class CuentasPagarListSerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para listados de CuentasPagar.
    Optimizado para tablas de resumen.
    """
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True)
    estado_pago_display = serializers.CharField(source='get_estado_pago_display', read_only=True)

    class Meta:
        model = CuentasPagar
        fields = (
            "uuid",
            "proveedor_id",
            "proveedor_nombre",
            "numero_factura",
            "fecha_vencimiento",
            "valor_total",
            "saldo",
            "estado_pago",
            "estado_pago_display",
            "created_at",
        )
        read_only_fields = fields


class CuentasPagarDetailSerializer(ProveedorNormalizationMixin, serializers.ModelSerializer):
    """
    Serializer de detalle para Cuentas por Pagar. Permite creacion y edicion controlada.
    Los campos 'saldo' y 'estado_pago' son estrictamente de solo lectura
    ya que se calculan a nivel de modelo en el metodo save().
    """
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True)
    estado_pago_display = serializers.CharField(source='get_estado_pago_display', read_only=True)

    class Meta:
        model = CuentasPagar
        fields = (
            "uuid",
            "proveedor",
            "proveedor_nombre",
            "numero_factura",
            "fecha_emision",
            "fecha_vencimiento",
            "valor_total",
            "valor_pagado",
            "saldo",
            "estado_pago",
            "estado_pago_display",
            "observaciones",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "uuid", 
            "saldo", 
            "estado_pago", 
            "estado_pago_display", 
            "created_at", 
            "updated_at"
        )

    def validate(self, attrs):
        """Aplica NormalizationMixin y valida coherencia de fechas."""
        attrs = self.normalize_data(attrs)
        
        fecha_emision = attrs.get('fecha_emision') or (self.instance.fecha_emision if self.instance else None)
        fecha_vencimiento = attrs.get('fecha_vencimiento') or (self.instance.fecha_vencimiento if self.instance else None)

        if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
            raise serializers.ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emision."
            })
            
        return attrs


class CuentasPagarAbonoSerializer(serializers.Serializer):
    """
    Serializer de entrada para la accion de registrar un pago o abono
    a una factura especifica en las Cuentas por Pagar.
    """
    monto = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=0.01,
        help_text="Monto a abonar a la factura"
    )
    observaciones = serializers.CharField(
        required=False, 
        allow_blank=True, 
        default=""
    )