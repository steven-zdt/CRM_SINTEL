"""
Serializers para Empleados v2.60.

WARNING: SINTEL v2.60: Sincronizacion Arquitectonica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validacion Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separacion List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explicitos: PROHIBIDO __all__, usar campos explicitos alineados con LIST_FIELDS y DETAIL_FIELDS
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

# WARNING: v2.60: Importar campos desde services.py (SSoT)
from apps.tenant.empresa.models import Empresa

from ..choices import AFP_CHOICES, ARL_CHOICES, EPS_CHOICES, RIESGO_ARL_CHOICES
from ..models import Contrato, Devengo, Empleado


# ==============================================================================
# NORMALIZATION MIXIN (Zero Trust)
# ==============================================================================
class NormalizationMixin:
    """
    WARNING: v2.60: Mixin para normalizacion de datos de entrada (Zero Trust).
    Sanitiza strings y valida tipos de datos antes de persistir.
    """
    def normalize_data(self, attrs):
        """
        Normaliza datos de entrada:
        - Strings: strip() para eliminar espacios
        - Documentos: upper() para normalizar formato
        - Emails: Validacion de formato
        - Nombres: Capitalizacion apropiada
        - Decimales: Normalizar a Decimal para campos numericos (dias_laborados, etc.)
        """
        from decimal import Decimal, InvalidOperation
        
        for key, value in attrs.items():
            if isinstance(value, str):
                # Strip espacios
                attrs[key] = value.strip()
                
                # Normalizar documentos y codigos a mayusculas
                if key in ['numero_documento', 'tipo_documento', 'tipo', 'estado', 'cargo']:
                    attrs[key] = attrs[key].upper()
                
                # Validar formato de email
                if key == 'email' and attrs[key]:
                    try:
                        EmailValidator()(attrs[key])
                    except DjangoValidationError:
                        raise serializers.ValidationError({key: ['El formato del email no es valido.']})
                
                # Capitalizar nombres (primer letra mayuscula, resto minusculas)
                if key in ['primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido', 'cargo']:
                    if attrs[key]:
                        attrs[key] = attrs[key].title()
            
            # WARNING: v2.60: Normalizar campos decimales (dias_laborados permite decimales 0.1-30)
            if key in ['dias_laborados'] and value is not None:
                from decimal import Decimal, InvalidOperation
                try:
                    attrs[key] = Decimal(str(value))
                except (ValueError, InvalidOperation, TypeError):
                    raise serializers.ValidationError({
                        key: [f'El campo {key} debe ser un numero valido (permite decimales, ej: 15.5).']
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

        empresa = Empresa.objects.only('id').first()
        return empresa.id if empresa else None

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
    
    # Indicadores de estado procedentes de anotaciones en services.py
    # Determinan la visibilidad de botones: Crear Contrato -> Registrar Nomina -> Historial
    tiene_contrato_activo = serializers.BooleanField(read_only=True)
    tiene_nominas_registradas = serializers.BooleanField(read_only=True)

    class Meta:
        model = Empleado
        fields = (
            'id', 'uuid', 'tipo_documento', 'tipo_doc_display', 'numero_documento',
            'primer_nombre', 'primer_apellido', 'nombre_completo', 
            'estado', 'estado_display', 'fecha_ingreso',
            'tiene_contrato_activo', 'tiene_nominas_registradas'
        )
        read_only_fields = ['id', 'uuid', 'nombre_completo', 'tipo_doc_display', 'estado_display',
                           'tiene_contrato_activo', 'tiene_nominas_registradas']

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
            'prestamos_empresa', 'cargo', 'archivo_pdf', 'estado', 'estado_display', 'activo'
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
    periodo_mes = serializers.CharField(required=True, help_text="Periodo en formato YYYY-MM (ej: 2024-01)")
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
    
    # WARNING: v2.60: Campos calculados - READ_ONLY (Zero Trust: el backend los calcula, nunca confiar en el frontend)
    salario_base = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Salario base proporcional en COP (calculado automaticamente)")
    auxilio_transporte = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Auxilio de transporte proporcional en COP (calculado automaticamente)")
    salud_empleado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Deduccion de salud (4%) en COP (calculado automaticamente)")
    pension_empleado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Deduccion de pension (4%) en COP (calculado automaticamente)")
    neto_pagar = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Neto a pagar en COP (calculado automaticamente)")
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    
    # WARNING: v2.95: Campos opcionales con valores por defecto
    prestamos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Prestamos descontados en COP")
    descuentos_operativos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Descuentos operativos en COP")
    otros_devengos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Otros devengos en COP")
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
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
                self.fields['contrato'].queryset = Contrato.objects.filter(
                    empresa_id=empresa_id
                ).select_related('empleado').only(
                    'id', 'uuid', 'empresa_id', 'empleado_id', 'empleado__id',
                    'estado', 'activo', 'salario_mensual', 'auxilio_transporte',
                    'prestamos_empresa', 'tipo',
                )

    class Meta:
        model = Devengo
        fields = (
            'id', 'uuid', 'empleado', 'contrato', 'empleado_nombre', 'periodo_mes',
            'fecha_pago', 'dias_laborados', 'salario_base', 'auxilio_transporte', 
            'otros_devengos', 'salud_empleado', 'pension_empleado',
            'prestamos', 'descuentos_operativos', 'observaciones',
            'neto_pagar', 'anulado'
        )
        read_only_fields = (
            'id', 'uuid', 'salario_base', 'auxilio_transporte', 'salud_empleado',
            'pension_empleado', 'neto_pagar', 'anulado', 'empleado_nombre'
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
        """WARNING: v2.60: Validacion estricta - Asegurar que el empleado pertenezca al tenant actual."""
        if value is None:
            return value
        
        empresa_id = self._get_empresa_id()
        if not empresa_id:
            raise serializers.ValidationError("No se encontro configuracion de Empresa para este tenant.")
        
        if value.empresa_id != empresa_id:
            raise serializers.ValidationError(f"El empleado con ID {value.id} no pertenece a este tenant.")
        
        return value
    
    def validate_contrato(self, value):
        """WARNING: v2.60: Validacion estricta - Asegurar que el contrato pertenezca al tenant actual y al empleado."""
        if value is None:
            return value
        
        empresa_id = self._get_empresa_id()
        if not empresa_id:
            raise serializers.ValidationError("No se encontro configuracion de Empresa para este tenant.")
        
        if value.empresa_id != empresa_id:
            raise serializers.ValidationError(f"El contrato con ID {value.id} no pertenece a este tenant.")
        
        # Validar que el contrato pertenezca al empleado (si esta en el contexto)
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
    
    # WARNING: v3.5: Integracion Contable
    cuenta_contable_uuid = serializers.UUIDField(required=False, allow_null=True)

    # WARNING: v2.60: Empresa es read_only pero se asigna en perform_create
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)

    # WARNING: v3.5: Integracion Contable - 18: label dinamico para UI (Pull Model)
    cuenta_contable_label = serializers.SerializerMethodField()

    class Meta:
        model = Empleado
        fields = (
            'id', 'uuid', 'empresa', 'tipo_documento', 'numero_documento',
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'email', 'telefono',
            'eps', 'afp', 'arl', 'nivel_riesgo_arl',  # WARNING: v2.95: Seguridad Social
            'estado', 'fecha_ingreso', 'fecha_retiro',
            'nombre_completo', 'contratos',
            'cuenta_contable_uuid', 'cuenta_contable_label'  # WARNING: v3.5: Integracion Contable - 18
        )
        read_only_fields = ('id', 'uuid', 'empresa', 'nombre_completo', 'contratos', 'cuenta_contable_label')

    def get_cuenta_contable_label(self, obj):
        """
        Retorna el UUID contable pasivo sin acoplar empleados a contabilidad.
        """
        if isinstance(obj, dict):
            cuenta_uuid = obj.get('cuenta_contable_uuid')
        else:
            cuenta_uuid = obj.cuenta_contable_uuid

        if not cuenta_uuid:
            return None

        return str(cuenta_uuid)

    def validate_cuenta_contable_uuid(self, value):
        """
        Acepta UUID contable como dato pasivo para el Pull Model.
        """
        return value

    def validate(self, attrs):
        """
        WARNING: v2.60: Zero Trust - Normalizacion estricta antes de persistir.
        """
        # Remover empresa si viene en los datos (debe ser asignada por perform_create)
        attrs.pop('empresa', None)
        attrs = self.normalize_data(attrs)
        
        # WARNING: v2.60: Validacion de unicidad preventiva (empresa, tipo, numero)
        # Evita IntegrityError 500 y proporciona feedback 400 limpio
        empresa = self.context.get('empresa')
        tipo = attrs.get('tipo_documento')
        numero = attrs.get('numero_documento')
        
        if tipo and numero and empresa:
            qs = Empleado.objects.filter(
                empresa_id=empresa.id,
                tipo_documento=tipo,
                numero_documento=numero
            ).only('id')
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise serializers.ValidationError({
                    'numero_documento': f'Ya existe un empleado con {tipo} {numero} en esta empresa.'
                })
                
        return attrs
    
    def validate_email(self, value):
        """WARNING: v2.60: Validacion estricta de formato de email."""
        if value:
            try:
                EmailValidator()(value.strip())
            except DjangoValidationError:
                raise serializers.ValidationError('El formato del email no es valido.')
        return value
