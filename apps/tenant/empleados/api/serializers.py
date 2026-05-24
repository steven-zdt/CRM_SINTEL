"""
Serializers para Empleados v2.60.

WARNING: SINTEL v2.60: Sincronizacion Arquitectonica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validacion Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separacion List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explicitos: PROHIBIDO __all__, usar campos explicitos alineados con LIST_FIELDS y DETAIL_FIELDS
"""
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

from apps.tenant.api.utils import NormalizationMixin as BaseMixin

class NullableUUIDField(serializers.UUIDField):
    """UUIDField que convierte cadena vacía en None (útil con FormData/HTMX)."""
    def to_internal_value(self, data):
        if data == '' or data is None:
            return None
        return super().to_internal_value(data)

# WARNING: v2.60: Importar campos desde services.py (SSoT)
from apps.tenant.empresa.models import Empresa

from ..choices import AFP_CHOICES, ARL_CHOICES, EPS_CHOICES, RIESGO_ARL_CHOICES
from ..models import Contrato, Devengo, Empleado


# ==============================================================================
# EXTENDED NORMALIZATION MIXIN (Module-specific enhancements)
# ==============================================================================
class NormalizationMixin(BaseMixin):
    """
    WARNING: v2.60: Extiende mixin base con normalizaciones específicas de Empleados.
    """
    def normalize_data(self, attrs):
        """
        Extiende normalize_data canónico con:
        - Capitalización de nombres
        - Validación de email
        - Normalización de decimales (dias_laborados)
        """
        # Llamar al método base para normalización estándar
        attrs = super().normalize_data(attrs)

        for key, value in attrs.items():
            if isinstance(value, str):
                # Capitalizar nombres (primer letra mayuscula, resto minusculas)
                if key in ['primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido', 'cargo']:
                    if value:
                        attrs[key] = value.title()

                # Validar formato de email (redundante con validate_email, pero mantenido para seguridad)
                if key == 'email' and value:
                    try:
                        EmailValidator()(value)
                    except DjangoValidationError:
                        raise serializers.ValidationError({key: ['El formato del email no es válido.']})

            # Normalizar campos decimales (dias_laborados permite decimales 0.1-30)
            if key in ['dias_laborados'] and value is not None:
                try:
                    attrs[key] = Decimal(str(value))
                except (ValueError, InvalidOperation, TypeError):
                    raise serializers.ValidationError({
                        key: [f'El campo {key} debe ser un número válido (permite decimales, ej: 15.5).']
                    })

        return attrs

    def _get_empresa_id(self):
        """Obtiene empresa_id desde contexto con fallback controlado para DEBUG/dev."""
        empresa_id = self.context.get('empresa_id')
        if empresa_id:
            return empresa_id

        empresa = self.context.get('empresa')
        if empresa:
            return empresa.id

        return None

class EmpleadoListSerializer(serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con EMPLEADO_LIST_FIELDS de services.py.
    Fase 2: Expone indicadores de estado para habilitar acciones secuenciales.
    """
    nombre_completo = serializers.ReadOnlyField()
    tipo_doc_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    # Foto de perfil — URL relativa para el avatar en Tabulator
    foto_url = serializers.SerializerMethodField()

    # Indicadores de estado procedentes de anotaciones en services.py
    # Determinan la visibilidad de botones: Crear Contrato -> Registrar Nomina -> Historial
    tiene_contrato_activo = serializers.BooleanField(read_only=True)
    tiene_nominas_registradas = serializers.BooleanField(read_only=True)
    contrato_activo_uuid = serializers.UUIDField(read_only=True, allow_null=True)

    def get_foto_url(self, obj):
        if not obj.foto:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.foto.url) if request else obj.foto.url

    class Meta:
        model = Empleado
        fields = (
            'id', 'uuid', 'tipo_documento', 'tipo_doc_display', 'numero_documento',
            'primer_nombre', 'primer_apellido', 'nombre_completo',
            'estado', 'estado_display', 'fecha_ingreso',
            'foto_url',
            'tiene_contrato_activo', 'tiene_nominas_registradas', 'contrato_activo_uuid'
        )
        read_only_fields = ['id', 'uuid', 'nombre_completo', 'tipo_doc_display', 'estado_display',
                           'foto_url',
                           'tiene_contrato_activo', 'tiene_nominas_registradas', 'contrato_activo_uuid']

class ContratoNestedSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer para gestion de contratos vinculados a empleados.
    Campos alineados con CONTRATO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    
    WARNING: v2.95: La creacion se maneja en perform_create del ViewSet usando service layer.
    Este serializer solo valida y serializa datos.
    """
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    
    # WARNING: v2.60: Campo empleado - puede venir como ID (string) desde FormData
    empleado = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.none(),
        required=True,
        help_text="ID del empleado (puede venir como string desde FormData)"
    )
    
    # WARNING: v2.95: Campos opcionales con valores por defecto (valores en COP)
    auxilio_transporte = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Auxilio de transporte en COP")
    prestamos_empresa = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Prestamos de la empresa en COP")
    fecha_fin = serializers.DateField(required=False, allow_null=True)
    archivo_pdf = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Contrato
        fields = (
            'id', 'uuid', 'empleado', 'empleado_nombre', 'tipo', 'tipo_display',
            'fecha_inicio', 'fecha_fin', 'salario_mensual', 'auxilio_transporte', 
            'prestamos_empresa', 'cargo', 'archivo_pdf', 'estado', 'estado_display', 'activo',
            'horas_semanales',
        )
        read_only_fields = ('id', 'uuid', 'estado_display', 'activo', 'empleado_nombre')

    def __init__(self, *args, **kwargs):
        """Inicializa querysets filtrados por tenant."""
        super().__init__(*args, **kwargs)
        empresa_id = self._get_empresa_id()
        if empresa_id and 'empleado' in self.fields:
            self.fields['empleado'].queryset = Empleado.objects.filter(
                empresa_id=empresa_id
            ).only('id', 'uuid', 'empresa_id', 'primer_nombre', 'primer_apellido')
    
    def validate(self, attrs):
        """
        WARNING: v2.60: Zero Trust - Normalizacion estricta y validacion antes de persistir.
        """
        attrs = self.normalize_data(attrs)
        
        # WARNING: v2.60: Validar un solo contrato ACTIVO por empleado (DB constraint)
        if attrs.get('estado') == 'ACTIVO':
            empleado = attrs.get('empleado')
            if empleado:
                qs = Contrato.objects.filter(
                    empleado=empleado,
                    estado='ACTIVO',
                    empresa_id=empleado.empresa_id,
                ).only('id')
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError({
                        'estado': 'Este empleado ya tiene un contrato ACTIVO. Debe finalizarlo antes de crear uno nuevo.'
                    })
        
        return attrs
    
    def validate_empleado(self, value):
        """WARNING: v2.60: Validacion estricta - Asegurar que el empleado pertenezca al tenant actual."""
        if value is None:
            return value
        
        empresa_id = self._get_empresa_id()
        if not empresa_id:
            raise serializers.ValidationError("No se encontro configuracion de Empresa para este tenant.")
        
        if value.empresa_id != empresa_id:
            raise serializers.ValidationError(f"El empleado con ID {value.id} no pertenece a este tenant.")
        
        return value
    
    # WARNING: v2.95: NO implementar create() aqui - se maneja en perform_create del ViewSet
    # El ViewSet usa gestionar_contrato_service para crear el contrato
    
    def update(self, instance, validated_data):
        """
        WARNING: v2.40: Solo permitir edicion si el contrato esta ACTIVO.
        """
        nuevo_estado = validated_data.get('estado', instance.estado)
        
        if instance.estado != 'ACTIVO' and nuevo_estado != 'ACTIVO':
            campos_editables = {'estado'}
            campos_modificados = set(validated_data.keys()) - campos_editables
            if campos_modificados:
                raise serializers.ValidationError({
                    'estado': f'No se puede editar un contrato {instance.estado.lower()}. Solo se puede cambiar su estado.'
                })
        
        if 'estado' in validated_data:
            validated_data['activo'] = (validated_data['estado'] == 'ACTIVO')
        
        return super().update(instance, validated_data)

class DevengoSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer de Nomina vinculado a Contrato.
    Campos alineados con DEVENGO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    
    WARNING: Zero Trust: Los valores calculados (salario_base, auxilio_transporte, salud_empleado, 
    pension_empleado, neto_pagar) son READ_ONLY. El backend los calcula en perform_create usando
    la capa de servicio (calcular_liquidacion_nomina). El frontend NUNCA debe enviar estos valores.
    
    v2.40: Los valores proporcionales se calculan desde la logica de servicio.
    WARNING: v2.95: Todos los valores monetarios estan en COP (Pesos Colombianos).
    """
    # WARNING: v2.60: Campos requeridos
    # required=False: puede derivarse automaticamente de fecha_inicio en el viewset
    periodo_mes = serializers.CharField(required=False, allow_blank=True, help_text="Periodo YYYY-MM — se deriva de fecha_inicio si no se envia")
    fecha_pago = serializers.DateField(required=True)
    dias_laborados = serializers.DecimalField(max_digits=5, decimal_places=2, required=True, help_text="Dias laborados (0.5-30, permite decimales)")
    empleado = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.none(),
        required=True,
        help_text="ID del empleado"
    )
    contrato = serializers.PrimaryKeyRelatedField(
        queryset=Contrato.objects.none(),
        required=True,
        help_text="ID del contrato activo"
    )
    
    # WARNING: v2.60: Campos calculados - READ_ONLY
    salario_base        = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    auxilio_transporte  = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    salud_empleado      = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    pension_empleado    = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    neto_pagar          = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    # Campos de presentación (read-only, cross-model via select_related)
    empleado_uuid       = serializers.UUIDField(source='empleado.uuid',              read_only=True)
    empleado_nombre     = serializers.CharField(source='empleado.nombre_completo',   read_only=True)
    empleado_documento  = serializers.CharField(source='empleado.numero_documento',  read_only=True)
    contrato_tipo         = serializers.CharField(source='contrato.tipo',              read_only=True)
    contrato_tipo_display = serializers.CharField(source='contrato.get_tipo_display', read_only=True)
    contrato_cargo        = serializers.CharField(source='contrato.cargo',             read_only=True)

    # Mapeo contable — SSoT en Devengo (Pull Model Contabilidad)
    # NullableUUIDField: acepta cadena vacía de FormData/HTMX y la convierte en None
    cuenta_contable_uuid = NullableUUIDField(required=False, allow_null=True)
    
    # WARNING: v2.95: Campos opcionales con valores por defecto
    prestamos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Prestamos descontados en COP")
    descuentos_operativos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Descuentos operativos en COP")
    otros_devengos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Otros devengos en COP")
    observaciones = serializers.CharField(required=False, allow_blank=True)
    fecha_inicio  = serializers.DateField(required=False, allow_null=True)
    fecha_fin     = serializers.DateField(required=False, allow_null=True)

    # Horas extras y recargos (Decreto 2663/1950 - normativa colombiana)
    horas_extras_diurnas   = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0)
    horas_extras_nocturnas = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0)
    recargo_nocturno_horas = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0)
    recargo_festivo_horas  = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, default=0)
    valor_horas_extras     = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    def __init__(self, *args, **kwargs):
        """WARNING: v2.60: Inicializar querysets dinamicamente para validacion Zero Trust."""
        super().__init__(*args, **kwargs)
        empresa_id = self._get_empresa_id()
        if empresa_id:
            # Filtrar querysets por empresa (Zero Trust) - Actualizar despues de la inicializacion
            if 'empleado' in self.fields:
                self.fields['empleado'].queryset = Empleado.objects.filter(
                    empresa_id=empresa_id
                ).only('id', 'uuid', 'empresa_id', 'estado', 'primer_nombre', 'primer_apellido')
            if 'contrato' in self.fields:
                # Solo contratos ACTIVOS son válidos para registrar nómina.
                # Esto rechaza el FK antes de llegar a validate_contrato.
                self.fields['contrato'].queryset = Contrato.objects.filter(
                    empresa_id=empresa_id,
                    estado='ACTIVO',
                    activo=True,
                ).select_related('empleado').only(
                    'id', 'uuid', 'empresa_id', 'empleado_id', 'empleado__id',
                    'estado', 'activo', 'salario_mensual', 'auxilio_transporte',
                    'prestamos_empresa', 'tipo', 'horas_semanales',
                )

    class Meta:
        model = Devengo
        fields = (
            # Identificación
            'id', 'uuid',
            # Relaciones
            'empleado', 'contrato',
            # Info presentación (read-only)
            'empleado_uuid', 'empleado_nombre', 'empleado_documento',
            'contrato_tipo', 'contrato_tipo_display', 'contrato_cargo',
            # Período
            'periodo_mes', 'fecha_pago', 'dias_laborados',
            # Devengos
            'salario_base', 'auxilio_transporte', 'otros_devengos',
            # Horas extras y recargos
            'horas_extras_diurnas', 'horas_extras_nocturnas', 'recargo_nocturno_horas', 'recargo_festivo_horas', 'valor_horas_extras',
            # Deducciones
            'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
            # Totales y estado
            'observaciones', 'neto_pagar', 'anulado',
            # Rango de fechas del período
            'fecha_inicio', 'fecha_fin',
            # Mapeo contable
            'cuenta_contable_uuid',
        )
        read_only_fields = (
            'id', 'uuid',
            'salario_base', 'auxilio_transporte', 'salud_empleado', 'pension_empleado', 'neto_pagar',
            'valor_horas_extras',
            'anulado',
            'empleado_uuid', 'empleado_nombre', 'empleado_documento',
            'contrato_tipo', 'contrato_tipo_display', 'contrato_cargo',
        )
    
    def validate(self, attrs):
        """
        WARNING: v2.60: Zero Trust - Normalizacion estricta antes de persistir.
        """
        attrs = self.normalize_data(attrs)
        
        # Validar formato de periodo_mes (YYYY-MM)
        periodo_mes = attrs.get('periodo_mes')
        if periodo_mes:
            import re
            if not re.match(r'^\d{4}-\d{2}$', periodo_mes):
                raise serializers.ValidationError({
                    'periodo_mes': ['El periodo debe tener el formato YYYY-MM (ej: 2024-01).']
                })
        
        # Validar rango de dias_laborados (0.5 - 30)
        dias_laborados = attrs.get('dias_laborados')
        if dias_laborados is not None:
            from decimal import Decimal
            if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('30'):
                raise serializers.ValidationError({
                    'dias_laborados': ['Los dias laborados deben estar entre 0.5 y 30.']
                })

        # WARNING: v2.60: Validar unicidad (empleado, periodo_mes, fecha_pago)
        # Evita duplicados en la misma tanda de pago
        empleado = attrs.get('empleado')
        periodo = attrs.get('periodo_mes')
        fecha = attrs.get('fecha_pago')
        if empleado and periodo and fecha:
            qs = Devengo.objects.filter(
                empleado=empleado, 
                periodo_mes=periodo, 
                fecha_pago=fecha,
                anulado=False,
                empresa_id=empleado.empresa_id,
            ).only('id')
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'fecha_pago': f'Ya existe una nomina registrada para este empleado en el periodo {periodo} con fecha {fecha}.'
                })
        
        return attrs
    
    def validate_empleado(self, value):
        """Valida tenant y que el empleado tenga contrato activo antes de registrar nomina."""
        if value is None:
            return value

        empresa_id = self._get_empresa_id()
        if not empresa_id:
            raise serializers.ValidationError("No se encontro configuracion de Empresa para este tenant.")

        if value.empresa_id != empresa_id:
            raise serializers.ValidationError(f"El empleado con ID {value.id} no pertenece a este tenant.")

        # Garantia: no se puede registrar nomina a un empleado sin contrato activo.
        # Espejo de la logica del selector get_disponibles_para_periodo en el frontend.
        tiene_contrato = Contrato.objects.filter(
            empresa_id=empresa_id,
            empleado_id=value.id,
            estado='ACTIVO',
            activo=True,
        ).only('id').exists()
        if not tiene_contrato:
            raise serializers.ValidationError(
                'El empleado no tiene un contrato activo. '
                'Cree un contrato antes de registrar nomina.'
            )

        return value

    def validate_contrato(self, value):
        """Valida tenant, estado activo y vinculacion contrato-empleado."""
        if value is None:
            return value

        empresa_id = self._get_empresa_id()
        if not empresa_id:
            raise serializers.ValidationError("No se encontro configuracion de Empresa para este tenant.")

        if value.empresa_id != empresa_id:
            raise serializers.ValidationError(f"El contrato con ID {value.id} no pertenece a este tenant.")

        # El queryset ya filtra estado='ACTIVO', pero la validacion explicita garantiza
        # que tampoco llegue un contrato inactivo por bypass directo del API.
        if value.estado != 'ACTIVO' or not value.activo:
            raise serializers.ValidationError(
                f'El contrato seleccionado no esta activo (estado: {value.estado}). '
                f'Solo se puede registrar nomina con un contrato ACTIVO.'
            )

        # Validar que el contrato pertenezca al empleado enviado en el mismo payload.
        empleado = self.initial_data.get('empleado') if hasattr(self, 'initial_data') else None
        if empleado:
            if isinstance(empleado, int):
                empleado_id = empleado
            elif hasattr(empleado, 'id'):
                empleado_id = empleado.id
            else:
                empleado_id = None

            if empleado_id and value.empleado_id != empleado_id:
                raise serializers.ValidationError("El contrato seleccionado no pertenece al empleado especificado.")

        return value

class EmpleadoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    WARNING: v2.60: Serializer completo para DETALLE/EDICION de Empleados.
    Campos alineados con EMPLEADO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.

    WARNING: v2.95: Incluye campos de seguridad social (EPS, AFP, ARL).
    """
    contratos = ContratoNestedSerializer(many=True, read_only=True)
    nombre_completo = serializers.ReadOnlyField()

    # Foto de perfil — ImageField writable + URL read-only
    foto = serializers.ImageField(required=False, allow_null=True, use_url=True)
    foto_url = serializers.SerializerMethodField()

    def get_foto_url(self, obj):
        if not obj.foto:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.foto.url) if request else obj.foto.url

    # Campos opcionales
    segundo_nombre = serializers.CharField(required=False, allow_blank=True, allow_null=False)
    segundo_apellido = serializers.CharField(required=False, allow_blank=True, allow_null=False)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=False)
    fecha_retiro = serializers.DateField(required=False, allow_null=True)

    # WARNING: v2.95: Campos de seguridad social
    eps = serializers.ChoiceField(choices=EPS_CHOICES, required=True)
    afp = serializers.ChoiceField(choices=AFP_CHOICES, required=True)
    arl = serializers.ChoiceField(choices=ARL_CHOICES, required=True)
    nivel_riesgo_arl = serializers.ChoiceField(
        choices=RIESGO_ARL_CHOICES,
        required=False,
        default='I'
    )

    # WARNING: v2.60: Empresa es read_only pero se asigna en perform_create
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Empleado
        fields = (
            'id', 'uuid', 'empresa', 'tipo_documento', 'numero_documento',
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'email', 'telefono',
            'eps', 'afp', 'arl', 'nivel_riesgo_arl',
            'estado', 'fecha_ingreso', 'fecha_retiro',
            'foto', 'foto_url',
            'nombre_completo', 'contratos',
        )
        read_only_fields = ('id', 'uuid', 'empresa', 'nombre_completo', 'contratos', 'foto_url')

    def validate(self, attrs):
        """Zero Trust — normaliza y verifica unicidad antes de persistir."""
        attrs.pop('empresa', None)
        attrs = self.normalize_data(attrs)

        # Usar empresa_id desde context (nunca None si usuario autenticado)
        # _get_empresa_id() busca 'empresa_id' y luego 'empresa' en el context,
        # evitando el fallo silencioso cuando context['empresa'] es None.
        empresa_id = self._get_empresa_id()
        tipo = attrs.get('tipo_documento')
        numero = attrs.get('numero_documento')

        if tipo and numero and empresa_id:
            qs = (
                Empleado.objects
                .filter(empresa_id=empresa_id, tipo_documento=tipo, numero_documento=numero)
                .only('id', 'primer_nombre', 'primer_apellido', 'estado')
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            conflicting = qs.first()
            if conflicting:
                nombre = f'{conflicting.primer_nombre} {conflicting.primer_apellido}'.strip()
                estado = conflicting.estado
                if estado == 'RETIRADO':
                    msg = (
                        f'El documento {tipo} {numero} pertenece a {nombre} (RETIRADO). '
                        f'Reactive ese empleado en lugar de crear uno nuevo.'
                    )
                else:
                    msg = f'El documento {tipo} {numero} ya esta registrado para {nombre}.'
                raise serializers.ValidationError({'numero_documento': msg})

        return attrs
    
    def validate_email(self, value):
        """WARNING: v2.60: Validacion estricta de formato de email."""
        if value:
            try:
                EmailValidator()(value.strip())
            except DjangoValidationError:
                raise serializers.ValidationError('El formato del email no es valido.')
        return value
