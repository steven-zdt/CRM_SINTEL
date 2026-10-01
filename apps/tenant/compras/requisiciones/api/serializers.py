from rest_framework import serializers

from apps.tenant.clientes.models import Cliente
from apps.tenant.compras.api.serializers import UUIDOrPKRelatedField
from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.compras.requisiciones.models import (
    RequisicionCompra,
    RequisicionCompraItem,
    RequisicionCotizacion,
    RequisicionDocumento,
    RequisicionFactura,
)
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Area
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proyectos.models import Proyecto


class RequisicionCompraItemSerializer(serializers.ModelSerializer):
    # `uuid` opcional en escritura (Fase 6, PLAN_OPTIMIZACION_COMPRAS...):
    # mismo criterio que ItemOrdenCompraSerializer.uuid -- permite a
    # RequisicionCompraCRUDService.actualizar_requisicion() sincronizar
    # items por diferencia en vez de reemplazar toda la coleccion.
    uuid = serializers.UUIDField(required=False)
    cantidad_pendiente = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = RequisicionCompraItem
        fields = (
            "id",
            "uuid",
            "descripcion",
            "item_inventario_uuid",
            "tipo_item",
            "cantidad_solicitada",
            "unidad_medida",
            "valor_unitario_estimado",
            "porcentaje_iva",
            "valor_iva_estimado",
            "subtotal_estimado",
            "total_estimado",
            "cantidad_aprobada",
            "cantidad_ordenada",
            "cantidad_cancelada",
            "cantidad_pendiente",
            "observaciones",
        )
        read_only_fields = (
            "id",
            "valor_iva_estimado",
            "subtotal_estimado",
            "total_estimado",
            "cantidad_aprobada",
            "cantidad_ordenada",
            "cantidad_cancelada",
            "cantidad_pendiente",
        )


class RequisicionDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisicionDocumento
        fields = (
            "id",
            "uuid",
            "tipo",
            "nombre",
            "numero_referencia",
            "documento_uuid",
            "archivo",
            "descripcion",
            "created_at",
        )
        read_only_fields = ("id", "uuid", "created_at")


class RequisicionCotizacionSerializer(serializers.ModelSerializer):
    cotizacion_numero = serializers.CharField(source="cotizacion.numero_cotizacion", read_only=True)
    cotizacion_uuid = serializers.CharField(source="cotizacion.uuid", read_only=True)

    class Meta:
        model = RequisicionCotizacion
        fields = (
            "id",
            "uuid",
            "cotizacion_uuid",
            "cotizacion_numero",
            "tipo_relacion",
            "es_principal",
            "observacion",
            "created_at",
        )
        read_only_fields = fields


class RequisicionFacturaSerializer(serializers.ModelSerializer):
    factura_numero = serializers.CharField(source="factura.numero", read_only=True, default="")
    factura_uuid = serializers.CharField(source="factura.uuid", read_only=True)

    class Meta:
        model = RequisicionFactura
        fields = (
            "id",
            "uuid",
            "factura_uuid",
            "factura_numero",
            "tipo_relacion",
            "es_principal",
            "observacion",
            "created_at",
        )
        read_only_fields = fields


class RequisicionCompraListSerializer(serializers.ModelSerializer):
    solicitante_nombre = serializers.SerializerMethodField()
    responsable_aprobacion_nombre = serializers.SerializerMethodField()
    proyecto_nombre = serializers.CharField(source="proyecto.nombre", read_only=True, default="")
    sede_nombre = serializers.CharField(source="sede.nombre", read_only=True, default="")
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default="")
    cliente_nombre = serializers.CharField(
        source="cliente.razon_social", read_only=True, default=""
    )
    plantilla_nombre = serializers.CharField(source="plantilla.nombre", read_only=True, default="")
    cotizacion_origen_numero = serializers.SerializerMethodField()

    def get_solicitante_nombre(self, obj) -> str:
        return str(obj.solicitante) if obj.solicitante_id else ""

    def get_responsable_aprobacion_nombre(self, obj) -> str:
        return str(obj.responsable_aprobacion) if obj.responsable_aprobacion_id else ""

    def get_cotizacion_origen_numero(self, obj) -> str:
        # Requiere el Prefetch `_cotizacion_origen_list` de
        # RequisicionCompraSelector.get_list() -- si el queryset no lo trae
        # (ej. instancia suelta en un test), cae a una query normal en vez
        # de reventar con AttributeError.
        vinculos = getattr(obj, "_cotizacion_origen_list", None)
        if vinculos is None:
            vinculo = (
                obj.cotizaciones_vinculadas.filter(tipo_relacion="ORIGEN")
                .select_related("cotizacion")
                .first()
            )
            return vinculo.cotizacion.numero_cotizacion if vinculo else ""
        return vinculos[0].cotizacion.numero_cotizacion if vinculos else ""

    class Meta:
        model = RequisicionCompra
        fields = (
            "id",
            "uuid",
            "numero_documento",
            "fecha_solicitud",
            "fecha_necesidad",
            "tipo",
            "prioridad",
            "estado",
            "moneda",
            "subtotal_estimado",
            "impuestos_estimados",
            "total_estimado",
            "solicitante_nombre",
            "responsable_aprobacion_nombre",
            "proyecto_nombre",
            "sede_nombre",
            "area_nombre",
            "cliente_nombre",
            "plantilla_nombre",
            "cotizacion_origen_numero",
        )
        read_only_fields = fields


class RequisicionCompraDetailSerializer(serializers.ModelSerializer):
    items = RequisicionCompraItemSerializer(many=True, read_only=True)
    documentos = RequisicionDocumentoSerializer(many=True, read_only=True)
    cotizaciones_vinculadas = RequisicionCotizacionSerializer(many=True, read_only=True)
    facturas_vinculadas = RequisicionFacturaSerializer(many=True, read_only=True)
    ordenes_compra_uuids = serializers.SerializerMethodField()
    solicitante_nombre = serializers.SerializerMethodField()
    responsable_aprobacion_nombre = serializers.SerializerMethodField()
    proyecto_nombre = serializers.CharField(source="proyecto.nombre", read_only=True, default="")
    sede_nombre = serializers.CharField(source="sede.nombre", read_only=True, default="")
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default="")
    cliente_nombre = serializers.CharField(
        source="cliente.razon_social", read_only=True, default=""
    )
    plantilla_nombre = serializers.CharField(source="plantilla.nombre", read_only=True, default="")

    def get_solicitante_nombre(self, obj) -> str:
        return str(obj.solicitante) if obj.solicitante_id else ""

    def get_responsable_aprobacion_nombre(self, obj) -> str:
        return str(obj.responsable_aprobacion) if obj.responsable_aprobacion_id else ""

    def get_ordenes_compra_uuids(self, obj) -> list:
        return [
            str(v.orden_compra.uuid)
            for v in obj.ordenes_compra_vinculadas.select_related("orden_compra").all()
        ]

    class Meta:
        model = RequisicionCompra
        fields = (
            "id",
            "uuid",
            "numero_documento",
            "fecha_solicitud",
            "fecha_necesidad",
            "tipo",
            "prioridad",
            "estado",
            "justificacion",
            "observaciones",
            "moneda",
            "subtotal_estimado",
            "impuestos_estimados",
            "total_estimado",
            "solicitante_nombre",
            "responsable_aprobacion_nombre",
            "proyecto",
            "proyecto_nombre",
            "sede_nombre",
            "area_nombre",
            "cliente",
            "cliente_nombre",
            "plantilla",
            "plantilla_nombre",
            "items",
            "documentos",
            "cotizaciones_vinculadas",
            "facturas_vinculadas",
            "ordenes_compra_uuids",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RequisicionCompraCreateUpdateSerializer(serializers.ModelSerializer):
    proyecto = UUIDOrPKRelatedField(
        queryset=Proyecto.objects.all(), required=False, allow_null=True
    )
    area = UUIDOrPKRelatedField(queryset=Area.objects.all(), required=False, allow_null=True)
    responsable_aprobacion = UUIDOrPKRelatedField(
        queryset=TenantProfile.objects.all(), required=False, allow_null=True
    )
    # Cotizaciones -- PLAN_NUEVA_REQUISICION_FORMULARIO.md #1: revierte la
    # decision del 2026-09-26 ("cotizacion de origen obligatoria, FK unico")
    # a 0..N, ninguna obligatoria. Mismo patron que
    # OrdenCompraCreateUpdateSerializer.requisiciones (compras/api/
    # serializers.py:219-221) pero `required=False` (0 es valido). La
    # primera que el BusinessService vincule con exito se marca
    # internamente tipo_relacion='ORIGEN' (compatibilidad con el snapshot
    # de Aprobaciones y `cotizacion_origen_numero`, fuera de alcance de este
    # plan) -- invisible para el usuario, que ve todas por igual.
    cotizaciones = UUIDOrPKRelatedField(
        queryset=Cotizacion.objects.all(),
        many=True,
        required=False,
        default=list,
    )
    # Plantilla y Cliente -- OBLIGATORIOS al crear (fase previa de esta
    # sesion). En `update` el ViewSet siempre usa `partial=True`, asi que
    # DRF no los exige al editar. `plantilla` nunca se reemplaza via PATCH
    # (ya determino el numero_documento); `cliente` si se puede reemplazar
    # en BORRADOR (ver business_service.actualizar_requisicion), pero nunca
    # vaciar -- validado en el Service Layer, no aqui.
    plantilla = UUIDOrPKRelatedField(
        queryset=PlantillaOrdenCompra.objects.all(), required=True, allow_null=False
    )
    cliente = UUIDOrPKRelatedField(queryset=Cliente.objects.all(), required=True, allow_null=False)
    # Documento #6: pasa de default silencioso (_hoy() en el modelo) a
    # campo explicito y obligatorio del formulario -- se declara explicito
    # porque el modelo tiene `default=_hoy`, que DRF interpretaria como
    # `required=False` si se dejara implicito.
    fecha_solicitud = serializers.DateField(required=True)
    items = RequisicionCompraItemSerializer(many=True, required=True)

    class Meta:
        model = RequisicionCompra
        fields = (
            "fecha_solicitud",
            "fecha_necesidad",
            "tipo",
            "prioridad",
            "justificacion",
            "observaciones",
            "proyecto",
            "area",
            "responsable_aprobacion",
            "moneda",
            "items",
            "cotizaciones",
            "plantilla",
            "cliente",
        )
        # 'estado' nunca escribible via CRUD generico -- unica via son las
        # acciones explicitas (enviar-aprobacion/aprobar/rechazar/cancelar),
        # mismo criterio que corrigio CO-3 en OrdenCompra.

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "Debe proporcionar al menos un item para la requisicion."
            )
        return value
