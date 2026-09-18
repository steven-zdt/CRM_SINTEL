from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from apps.tenant.bancos.models import (
    CuentaBancaria,
    ExtractoBancario,
    MovimientoBancarioAplicacion,
    TransaccionBancaria,
)
from apps.tenant.empresa.models import Sede

TOLERANCIA_APLICACION = Decimal("0.01")

class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """Field that accepts either UUID (string) or internal PK (integer) for lookups, scoped to the current tenant."""

    def get_queryset(self):
        queryset = super().get_queryset()
        if queryset is None:
            return queryset
        root = getattr(self, "root", None)
        context = getattr(root, "context", {}) if root else {}
        empresa_id = context.get("empresa_id")
        if empresa_id and hasattr(queryset.model, "empresa_id"):
            return queryset.filter(empresa_id=empresa_id)
        return queryset

    def to_internal_value(self, data):
        if data in (None, ""):
            if self.allow_null:
                return None
            self.fail("required")
        data_str = str(data)
        if not data_str.isdigit():
            queryset = self.get_queryset()
            try:
                return queryset.get(uuid=data_str)
            except (TypeError, ValueError, queryset.model.DoesNotExist):
                self.fail("does_not_exist", pk_value=data)
        return super().to_internal_value(data)

class CuentaBancariaSerializer(serializers.ModelSerializer):
    """Serializer for CuentaBancaria."""

    class Meta:
        model = CuentaBancaria
        fields = (
            "id",
            "uuid",
            "nombre",
            "banco",
            "tipo",
            "numero",
            "activo",
        )
        # B-4: 'activo' solo se muta via las acciones dedicadas
        # (activar/desactivar), nunca por el PUT/PATCH generico -- mismo
        # criterio que CO-3 (no bypasear la maquina de estados/flags desde
        # el serializer generico de edicion).
        read_only_fields = ("id", "uuid", "activo")

class ExtractoBancarioListSerializer(serializers.ModelSerializer):
    """Serializer for ExtractoBancario lists with conciliacion summary."""
    cuenta_nombre         = serializers.CharField(source="cuenta.nombre", read_only=True)
    cuenta_numero         = serializers.CharField(source="cuenta.numero", read_only=True)
    cuenta_uuid           = serializers.UUIDField(source="cuenta.uuid", read_only=True)
    total_transacciones   = serializers.IntegerField(read_only=True, default=0)
    tx_conciliadas        = serializers.IntegerField(read_only=True, default=0)
    tx_pendientes         = serializers.SerializerMethodField()
    sede_nombre           = serializers.CharField(source="sede.nombre", read_only=True, allow_null=True)  # BAN-11

    def get_tx_pendientes(self, obj):
        total = getattr(obj, 'total_transacciones', 0) or 0
        conc  = getattr(obj, 'tx_conciliadas', 0) or 0
        return max(total - conc, 0)

    class Meta:
        model = ExtractoBancario
        fields = (
            "id",
            "uuid",
            "cuenta_id",
            "cuenta_uuid",
            "cuenta_nombre",
            "cuenta_numero",
            "mes",
            "anio",
            "archivo_s3",
            "procesado",
            "saldo_inicial",
            "saldo_final",
            "total_transacciones",
            "tx_conciliadas",
            "tx_pendientes",
            "sede_nombre",  # BAN-11
        )
        read_only_fields = fields

class ExtractoBancarioCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an ExtractoBancario."""
    cuenta = UUIDOrPKRelatedField(queryset=CuentaBancaria.objects.none())
    sede = UUIDOrPKRelatedField(
        queryset=Sede.objects.none(), required=False, allow_null=True,
        help_text="UUID de la sede a la que pertenece este extracto (opcional).",
    )  # BAN-11 (DT-SEDE-01)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = self.context.get("empresa_id") or (
            self.context.get("request") and getattr(self.context["request"], "empresa_id", None)
        )
        if empresa_id:
            self.fields["cuenta"].queryset = CuentaBancaria.objects.filter(empresa_id=empresa_id)
            self.fields["sede"].queryset = Sede.objects.filter(empresa_id=empresa_id)

    class Meta:
        model = ExtractoBancario
        fields = (
            "id",
            "uuid",
            "cuenta",
            "mes",
            "anio",
            "archivo_s3",
            "procesado",
            "saldo_inicial",
            "saldo_final",
            "sede",  # BAN-11
        )
        read_only_fields = ("id", "uuid", "procesado")

    def validate_mes(self, value):
        if not (1 <= value <= 12):
            raise serializers.ValidationError("El mes debe estar entre 1 y 12.")
        return value

    def validate_anio(self, value):
        if not (2000 <= value <= 2100):
            raise serializers.ValidationError("El anio debe ser valido (entre 2000 y 2100).")
        return value

    def validate(self, attrs):
        cuenta = attrs.get("cuenta")
        mes = attrs.get("mes")
        anio = attrs.get("anio")
        empresa_id = self.context.get("empresa_id")

        if cuenta and empresa_id and cuenta.empresa_id != empresa_id:
            raise serializers.ValidationError(
                {"cuenta": "La cuenta seleccionada no pertenece a esta empresa."}
            )

        # BAN-11: misma validacion anti-IDOR que gastos.DocumentoSoporte.sede
        # (DT-SEDE-01) -- pertenencia a la empresa + alcance organizacional.
        sede = attrs.get("sede")
        if sede and empresa_id and sede.empresa_id != empresa_id:
            raise serializers.ValidationError(
                {"sede": "La sede seleccionada no pertenece a esta empresa."}
            )
        if sede:
            from apps.tenant.core.services.organizational_scope import sede_esta_en_alcance
            if not sede_esta_en_alcance(sede.id, self.context.get("request")):
                raise serializers.ValidationError(
                    {"sede": "No tiene permiso para asignar esta sede (fuera de su alcance organizacional)."}
                )

        # Check for duplicates on creation
        request = self.context.get("request")
        if request and request.method == "POST":
            if ExtractoBancario.objects.filter(
                empresa_id=empresa_id,
                cuenta=cuenta,
                mes=mes,
                anio=anio
            ).exists():
                raise serializers.ValidationError(
                    "Ya existe un extracto registrado para esta cuenta en el periodo indicado."
                )

        return attrs

class ExtractoBancarioDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ExtractoBancario."""
    cuenta = CuentaBancariaSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    sede_nombre = serializers.CharField(source="sede.nombre", read_only=True, allow_null=True)  # BAN-11

    class Meta:
        model = ExtractoBancario
        fields = (
            "id",
            "uuid",
            "cuenta",
            "mes",
            "anio",
            "archivo_s3",
            "procesado",
            "saldo_inicial",
            "saldo_final",
            "created_at",
            "updated_at",
            "sede_nombre",  # BAN-11
        )
        read_only_fields = fields

class TransaccionBancariaListSerializer(serializers.ModelSerializer):
    """Serializer para listados Tabulator con campos de conciliacion y display."""
    extracto_uuid       = serializers.UUIDField(source="extracto.uuid", read_only=True)
    tipo_movimiento     = serializers.CharField(read_only=True)   # @property: DEBITO | CREDITO
    monto               = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)  # abs(valor)
    factura_info        = serializers.SerializerMethodField(read_only=True)
    proveedor_info      = serializers.SerializerMethodField(read_only=True)
    conciliacion_display = serializers.SerializerMethodField(read_only=True)
    monto_aplicado      = serializers.SerializerMethodField(read_only=True)
    monto_pendiente     = serializers.SerializerMethodField(read_only=True)
    estado_aplicacion   = serializers.SerializerMethodField(read_only=True)

    def _monto_aplicado_total(self, obj):
        # Viene anotado por el selector (Sum) -- evita N+1 en listados.
        return getattr(obj, "monto_aplicado_total", None) or Decimal("0.00")

    def get_monto_aplicado(self, obj):
        return str(self._monto_aplicado_total(obj))

    def get_monto_pendiente(self, obj):
        pendiente = abs(obj.valor) - self._monto_aplicado_total(obj)
        return str(max(pendiente, Decimal("0.00")))

    def get_estado_aplicacion(self, obj):
        aplicado = self._monto_aplicado_total(obj)
        monto = abs(obj.valor)
        if aplicado <= 0:
            return "PENDIENTE"
        if monto - aplicado <= TOLERANCIA_APLICACION:
            return "CONCILIADO"
        return "PARCIAL"

    def get_factura_info(self, obj):
        """Info snapshot de factura (read-only)."""
        if obj.factura_uuid:
            return {'uuid': str(obj.factura_uuid)}
        return None

    def get_proveedor_info(self, obj):
        """Info snapshot de proveedor (read-only)."""
        if obj.proveedor_uuid:
            return {'uuid': str(obj.proveedor_uuid)}
        return None

    def get_conciliacion_display(self, obj):
        partes = []
        if obj.factura_uuid:
            partes.append('Factura')
        if obj.proveedor_uuid:
            partes.append('Proveedor')
        if obj.cliente_uuid:
            partes.append('Cliente')
        if obj.conciliado and partes:
            return 'Vinculado: ' + ' + '.join(partes)
        if obj.conciliado:
            return 'Conciliado'
        return 'No conciliado'

    class Meta:
        model = TransaccionBancaria
        fields = (
            "id", "uuid", "extracto_uuid",
            "fecha", "descripcion", "sucursal", "dcto",
            "valor", "monto", "saldo",
            "tipo_movimiento",
            "factura_uuid", "proveedor_uuid", "cliente_uuid", "conciliado",
            "factura_info", "proveedor_info", "conciliacion_display",
            "notas_conciliacion",
            "monto_aplicado", "monto_pendiente", "estado_aplicacion",
        )
        read_only_fields = fields


class TransaccionBancariaDetailSerializer(serializers.ModelSerializer):
    """Serializer de detalle con relacion extracto completa."""
    extracto        = ExtractoBancarioDetailSerializer(read_only=True)
    tipo_movimiento = serializers.CharField(read_only=True)
    monto           = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    created_at      = serializers.DateTimeField(read_only=True)
    updated_at      = serializers.DateTimeField(read_only=True)
    monto_aplicado    = serializers.SerializerMethodField(read_only=True)
    monto_pendiente   = serializers.SerializerMethodField(read_only=True)
    estado_aplicacion = serializers.SerializerMethodField(read_only=True)

    def _monto_aplicado_total(self, obj):
        total = obj.aplicaciones.aggregate(total=Sum("monto_aplicado"))["total"]
        return total or Decimal("0.00")

    def get_monto_aplicado(self, obj):
        return str(self._monto_aplicado_total(obj))

    def get_monto_pendiente(self, obj):
        pendiente = abs(obj.valor) - self._monto_aplicado_total(obj)
        return str(max(pendiente, Decimal("0.00")))

    def get_estado_aplicacion(self, obj):
        aplicado = self._monto_aplicado_total(obj)
        monto = abs(obj.valor)
        if aplicado <= 0:
            return "PENDIENTE"
        if monto - aplicado <= TOLERANCIA_APLICACION:
            return "CONCILIADO"
        return "PARCIAL"

    class Meta:
        model = TransaccionBancaria
        fields = (
            "id", "uuid", "extracto",
            "fecha", "descripcion", "sucursal", "dcto",
            "valor", "monto", "saldo",
            "tipo_movimiento",
            "factura_uuid", "proveedor_uuid", "cliente_uuid", "conciliado",
            "created_at", "updated_at",
            "notas_conciliacion",
            "monto_aplicado", "monto_pendiente", "estado_aplicacion",
        )
        read_only_fields = fields


class TransaccionBancariaConciliarSerializer(serializers.ModelSerializer):
    """PATCH parcial para vincular transaccion con factura, proveedor, cliente y notas."""

    class Meta:
        model = TransaccionBancaria
        fields = ("factura_uuid", "proveedor_uuid", "cliente_uuid", "conciliado", "notas_conciliacion")

    def validate(self, attrs):
        factura_uuid   = attrs.get("factura_uuid",   self.instance.factura_uuid   if self.instance else None)
        proveedor_uuid = attrs.get("proveedor_uuid", self.instance.proveedor_uuid if self.instance else None)
        cliente_uuid   = attrs.get("cliente_uuid",   self.instance.cliente_uuid   if self.instance else None)
        if factura_uuid or proveedor_uuid or cliente_uuid:
            attrs.setdefault("conciliado", True)
        return attrs


class MovimientoBancarioAplicacionSerializer(serializers.ModelSerializer):
    """Serializer de lectura/creacion para aplicaciones multiples (Fase 5/17)."""
    transaccion_uuid = serializers.UUIDField(source="transaccion.uuid", read_only=True)
    tipo_referencia_display = serializers.CharField(source="get_tipo_referencia_display", read_only=True)
    # Opcional: el frontend no siempre la envia (el flujo tipico es "aplicar
    # hoy") -- crud_service.crear_aplicacion() la completa con la fecha
    # actual cuando no se especifica.
    fecha_aplicacion = serializers.DateField(required=False)

    class Meta:
        model = MovimientoBancarioAplicacion
        fields = (
            "id", "uuid", "transaccion_uuid",
            "tipo_referencia", "tipo_referencia_display", "referencia_uuid",
            "tercero_tipo", "tercero_uuid",
            "monto_aplicado", "fecha_aplicacion", "notas",
            "origen_matching", "confianza",
            "created_at",
        )
        read_only_fields = ("id", "uuid", "transaccion_uuid", "tipo_referencia_display", "created_at")

    def validate_monto_aplicado(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto aplicado debe ser mayor a 0.")
        return value


class MovimientoBancarioSugerenciaSerializer(serializers.Serializer):
    """Serializer de solo-lectura para los candidatos que produce
    BankTransactionMatchingService (Fase 8). No es un ModelSerializer --
    los candidatos son dicts, nunca se persisten desde aqui."""
    tipo = serializers.CharField()
    uuid = serializers.CharField()
    descripcion = serializers.CharField()
    monto = serializers.CharField(allow_null=True)
    score = serializers.FloatField()
    reason = serializers.ListField(child=serializers.CharField())
