from rest_framework import serializers

from apps.tenant.api.utils import NormalizationMixin
from apps.tenant.clientes.models import Cliente, ContactoCliente, Cartera


class ClienteMiniSerializer(serializers.ModelSerializer):
    """
    Lightweight read-only serializer para uso nested en otros modulos.
    Uso: cotizaciones, proyectos, reportes - donde se necesita info minima del cliente
    sin cargar el serializer completo.
    """
    class Meta:
        model = Cliente
        fields = [
            'id',
            'uuid',
            'numero_documento',
            'razon_social',
            'nombre_comercial',
            'email',
            'telefono',
        ]
        read_only_fields = fields


class ClienteListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listas (Tabulator).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    """
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    tipo_persona_display = serializers.CharField(source='get_tipo_persona_display', read_only=True)
    regimen_tributario_display = serializers.CharField(source='get_regimen_tributario_display', read_only=True)
    encargado = serializers.SerializerMethodField()
    cartera_resumen = serializers.SerializerMethodField()

    def get_encargado(self, obj):
        principal = obj.contactos_prefetched[0] if hasattr(obj, 'contactos_prefetched') and obj.contactos_prefetched else None
        if principal:
            return {'nombre': principal.nombre_completo, 'email': principal.email}
        return None

    def get_cartera_resumen(self, obj):
        """Lee del contexto el dict pre-calculado por el ViewSet (cero queries extra)."""
        cartera_map = self.context.get('cartera_map', {})
        resumen = cartera_map.get(str(obj.uuid))
        if not resumen:
            return {'pendiente_count': 0, 'pendiente_monto': '0', 'cobrada_count': 0, 'total_count': 0}
        return {
            'pendiente_count': resumen['pendiente_count'],
            'pendiente_monto': str(resumen['pendiente_monto']),
            'cobrada_count':   resumen['cobrada_count'],
            'total_count':     resumen['total_count'],
        }

    class Meta:
        model = Cliente
        fields = [
            'id',
            'uuid',
            'tipo_persona', 'tipo_persona_display',
            'tipo_documento', 'tipo_documento_display',
            'numero_documento',
            'razon_social',
            'nombre_comercial',
            'regimen_tributario', 'regimen_tributario_display',
            'es_retenedor',
            'aplica_retefuente', 'retefuente_porcentaje',
            'aplica_reteica', 'reteica_porcentaje',
            'aplica_reteiva', 'reteiva_porcentaje',
            'email',
            'telefono',
            'ciudad',
            'encargado',
            'activo',
            'cartera_resumen',
        ]
        read_only_fields = [
            'id', 'uuid', 'tipo_documento_display', 'tipo_persona_display',
            'regimen_tributario_display', 'encargado', 'cartera_resumen',
        ]


class ContactoClienteSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para Contactos de Cliente (CRUD independiente).
    Campo id explicito y forzado para preservarlo en actualizaciones anidadas.
    Integracion con NormalizationMixin para Zero Trust.
    """
    # cliente es opcional en el serializer para soportar el patron de creacion anidada inicial.
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.only('id', 'empresa_id'),
        required=False,
        allow_null=True,
    )
    cliente_uuid = serializers.UUIDField(source='cliente.uuid', read_only=True)
    cliente_nombre = serializers.SerializerMethodField(read_only=True)
    cliente_documento = serializers.SerializerMethodField(read_only=True)
    
    def get_cliente_nombre(self, obj):
        return obj.cliente.razon_social if obj.cliente else None

    def get_cliente_documento(self, obj):
        return obj.cliente.numero_documento if obj.cliente else None

    class Meta:
        model = ContactoCliente
        fields = [
            'id',
            'uuid',
            'cliente',
            'cliente_uuid',
            'nombre_completo',
            'cargo',
            'email',
            'telefono',
            'activo',
            'is_principal',
            'es_representante_legal',
            'cliente_nombre',
            'cliente_documento',
        ]

    def validate(self, attrs):
        attrs = self.normalize_data(attrs)
        if attrs.get('email'):
            attrs['email'] = attrs['email'].strip().lower()
        if attrs.get('nombre_completo'):
            attrs['nombre_completo'] = attrs['nombre_completo'].strip()

        empresa_id = self.context.get('empresa_id')
        cliente = attrs.get('cliente') or (self.instance.cliente if self.instance else None)

        # Validar que el cliente pertenece a esta empresa.
        if cliente and empresa_id and cliente.empresa_id != empresa_id:
            raise serializers.ValidationError({
                'cliente': ['El cliente especificado no pertenece a esta empresa.']
            })

        # Validar unico (cliente, email) para notificar el error de forma temprana.
        email = attrs.get('email')
        if email and cliente and self.instance:
            existing = ContactoCliente.objects.filter(
                cliente_id=cliente.id,
                empresa_id=empresa_id or cliente.empresa_id,
                email=email,
            ).exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    'email': ['Ya existe un contacto con este email para este cliente.']
                })

        return attrs


class ClienteDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer completo para detalle/edicion de Clientes.
    Contactos se gestionan de forma independiente via ContactoClienteViewSet.
    """

    class Meta:
        model = Cliente
        fields = [
            'id',
            'uuid',
            'tipo_persona',
            'tipo_documento',
            'numero_documento',
            'razon_social',
            'nombre_comercial',
            'regimen_tributario',
            'es_retenedor',
            'aplica_retefuente',
            'retefuente_porcentaje',
            'aplica_reteica',
            'reteica_porcentaje',
            'aplica_reteiva',
            'reteiva_porcentaje',
            'email',
            'telefono',
            'direccion',
            'ciudad',
            'activo',
            'observaciones',
        ]
        read_only_fields = ['id', 'uuid']

    def validate(self, attrs):
        """
        Validacion completa (Zero Trust) — FASE 4 anti-duplicidad.
        1. Normalizar strings, numeros, booleanos.
        2. Normalizar documento (sin guiones/espacios/DV) para comparacion exacta.
        3. Validar unicidad (empresa, tipo_documento, numero_documento):
           - CREATE (instance=None): rechaza si el documento ya existe.
           - UPDATE (instance!=None): rechaza si existe en OTRO registro (exclude pk actual).
        """
        attrs = self.normalize_data(attrs)

        empresa_id       = self.context.get('empresa_id')
        numero_documento = attrs.get('numero_documento')
        tipo_documento   = attrs.get('tipo_documento')

        if numero_documento and tipo_documento and empresa_id:
            num_norm = self.normalize_document_number(numero_documento)
            attrs['numero_documento'] = num_norm

            qs = Cliente.objects.filter(
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
                        f"Ya existe un Cliente registrado con el documento "
                        f"{tipo_documento} {num_norm} en su organización."
                    ]
                })
        
        if 'nombre_comercial' in attrs and attrs['nombre_comercial']:
            attrs['nombre_comercial'] = attrs['nombre_comercial'].strip()
        
        if 'telefono' in attrs and attrs['telefono']:
            attrs['telefono'] = self.normalize_phone(attrs['telefono'])

        return attrs


class CarteraListSerializer(serializers.ModelSerializer):
    """Serializer representation for accounts receivable list."""

    cliente_nombre = serializers.CharField(source="cliente.razon_social", read_only=True)
    cliente_documento = serializers.CharField(source="cliente.numero_documento", read_only=True)
    cliente_uuid = serializers.UUIDField(source="cliente.uuid", read_only=True)
    estado_pago_display = serializers.CharField(source="get_estado_pago_display", read_only=True)
    saldo = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = Cartera
        fields = [
            "id",
            "uuid",
            "cliente",
            "cliente_uuid",
            "cliente_nombre",
            "cliente_documento",
            "numero_factura",
            "factura_uuid",
            "fecha_emision",
            "fecha_vencimiento",
            "valor_total",
            "valor_pagado",
            "saldo",
            "estado_pago",
            "estado_pago_display",
            "observaciones",
        ]
        read_only_fields = fields


class CarteraDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para crear/actualizar Cartera (cuentas por cobrar).
    - saldo y estado_pago son read-only (calculados por models.Cartera.save())
    - cliente_uuid resuelve el FK via DSV en el ViewSet
    - factura_uuid es referencia débil (Bounded Context §18)
    """
    cliente_nombre    = serializers.CharField(source="cliente.razon_social", read_only=True)
    cliente_uuid_out  = serializers.UUIDField(source="cliente.uuid",         read_only=True)
    estado_pago_display = serializers.CharField(source="get_estado_pago_display", read_only=True)
    saldo = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model  = Cartera
        fields = [
            "id", "uuid",
            "cliente",          # FK (write: PK interno — resuelto por ViewSet via DSV)
            "cliente_uuid_out", # UUID público del cliente (read-only)
            "cliente_nombre",   # read-only snapshot
            "numero_factura",
            "factura_uuid",
            "fecha_emision",
            "fecha_vencimiento",
            "valor_total",
            "valor_pagado",
            "saldo",            # calculado en save()
            "estado_pago",      # calculado en save()
            "estado_pago_display",
            "observaciones",
        ]
        read_only_fields = [
            "id", "uuid", "saldo", "estado_pago", "estado_pago_display",
            "cliente_uuid_out", "cliente_nombre",
        ]

    def validate(self, attrs):
        """Validaciones de negocio para creación/edición de Cartera."""
        valor_total  = attrs.get("valor_total")
        valor_pagado = attrs.get("valor_pagado", 0)
        if valor_total is not None and valor_total <= 0:
            raise serializers.ValidationError({"valor_total": "El valor total debe ser mayor a cero."})
        if valor_pagado is not None and valor_pagado < 0:
            raise serializers.ValidationError({"valor_pagado": "El valor pagado no puede ser negativo."})
        if valor_total and valor_pagado and valor_pagado > valor_total:
            raise serializers.ValidationError({"valor_pagado": "El valor pagado no puede superar el valor total."})
        fecha_emision    = attrs.get("fecha_emision")
        fecha_vencimiento = attrs.get("fecha_vencimiento")
        if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
            raise serializers.ValidationError({"fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la de emisión."})
        return attrs


class FacturaCxCListSerializer(serializers.Serializer):
    """
    Read-only: mapea Factura.VENTA a los campos de display de la pestana Cartera.
    Patron Pull Model Bounded Context (AGENTS.md §18) — sin FK directa.

    Auditoria "Clientes + Cartera" (2026-09-11): antes, valor_pagado/saldo
    se INFERIAN del enum Factura.estado_pago (3 estados) — una factura
    PAGO_PARCIAL siempre mostraba valor_pagado=0/saldo=total, IGNORANDO el
    monto real de los abonos ya registrados en `Cartera` (fuente de verdad
    real de los abonos, ver CarteraBusinessService.registrar_abono()). Ahora
    el ViewSet arma un `cartera_map` (bulk, sin N+1) via
    CarteraSelector.get_cartera_map_by_factura_uuids() y lo pasa en
    `context` -- si existe una Cartera real para esta factura, sus
    valor_pagado/saldo/estado_pago mandan; si no existe (factura nunca
    tocada por Cartera), se mantiene el fallback anterior basado en el
    enum. Ver DEUDA documentada en AUDITORIA_FLUJO_CLIENTES.md sobre la
    reconciliacion pendiente con Bancos (tercera fuente de pagos, fuera de
    alcance de este fix puntual).
    """
    uuid            = serializers.UUIDField()
    numero_factura  = serializers.CharField(source='numero')
    cliente_nombre  = serializers.CharField(source='receptor_razon_social')
    cliente_documento = serializers.CharField(source='receptor_nit')
    cliente_uuid    = serializers.UUIDField(allow_null=True)
    fecha_emision   = serializers.DateTimeField()
    fecha_vencimiento = serializers.DateField(source='payment_due_date', allow_null=True)
    valor_total     = serializers.DecimalField(source='total', max_digits=15, decimal_places=2)
    valor_pagado    = serializers.SerializerMethodField()
    saldo           = serializers.SerializerMethodField()
    estado_pago     = serializers.SerializerMethodField()
    estado_pago_display = serializers.SerializerMethodField()

    _ESTADO_MAP = {'NO_PAGADA': 'SIN_PAGO', 'PAGO_PARCIAL': 'PARCIAL', 'PAGADA': 'PAGADA'}
    _DISPLAY_MAP = {'NO_PAGADA': 'Sin Pago', 'PAGO_PARCIAL': 'Pago Parcial', 'PAGADA': 'Pagada'}
    _CARTERA_DISPLAY_MAP = {'SIN_PAGO': 'Sin Pago', 'PARCIAL': 'Pago Parcial', 'PAGADA': 'Pagada'}

    def _cartera(self, obj):
        return (self.context.get('cartera_map') or {}).get(str(obj.uuid))

    def get_estado_pago(self, obj):
        cartera = self._cartera(obj)
        if cartera:
            return cartera['estado_pago']
        return self._ESTADO_MAP.get(obj.estado_pago, 'SIN_PAGO')

    def get_estado_pago_display(self, obj):
        cartera = self._cartera(obj)
        if cartera:
            return self._CARTERA_DISPLAY_MAP.get(cartera['estado_pago'], cartera['estado_pago'])
        return self._DISPLAY_MAP.get(obj.estado_pago, obj.estado_pago)

    def get_valor_pagado(self, obj):
        cartera = self._cartera(obj)
        if cartera:
            return str(cartera['valor_pagado'])
        return str(obj.total) if obj.estado_pago == 'PAGADA' else '0.00'

    def get_saldo(self, obj):
        cartera = self._cartera(obj)
        if cartera:
            return str(cartera['saldo'])
        return '0.00' if obj.estado_pago == 'PAGADA' else str(obj.total)


class CarteraAbonoSerializer(serializers.Serializer):
    """Serializer for registering a payment/abono on cartera."""

    monto = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0.01)


class CarteraNotaInputSerializer(serializers.Serializer):
    """Input para registrar una nueva CarteraNota."""

    texto = serializers.CharField(max_length=4000)
    tipo = serializers.ChoiceField(
        choices=["SEGUIMIENTO", "PROMESA_PAGO", "DISPUTA", "OTRO"],
        default="SEGUIMIENTO", required=False,
    )


class CarteraNotaSerializer(serializers.Serializer):
    """Read-only: historial de notas de una obligacion de Cartera."""

    uuid = serializers.UUIDField()
    tipo = serializers.CharField()
    tipo_display = serializers.SerializerMethodField()
    texto = serializers.CharField()
    created_at = serializers.DateTimeField()
    usuario_nombre = serializers.SerializerMethodField()

    _TIPO_DISPLAY = {
        "SEGUIMIENTO": "Seguimiento", "PROMESA_PAGO": "Promesa de pago",
        "DISPUTA": "Disputa/Reclamo", "OTRO": "Otro",
    }

    def get_tipo_display(self, obj):
        return self._TIPO_DISPLAY.get(obj.tipo, obj.tipo)

    def get_usuario_nombre(self, obj):
        if not obj.usuario or not obj.usuario.user:
            return None
        nombre = f"{obj.usuario.user.first_name} {obj.usuario.user.last_name}".strip()
        return nombre or obj.usuario.user.email
