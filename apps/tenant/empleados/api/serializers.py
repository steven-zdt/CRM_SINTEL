"""
Serializers para Empleados v2.60.

⚠️ SINTEL v2.60: Sincronización Arquitectónica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validación Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separación List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explícitos: PROHIBIDO __all__, usar campos explícitos alineados con LIST_FIELDS y DETAIL_FIELDS
"""
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from ..models import Empleado, Contrato, Devengo
from ..choices import EPS_CHOICES, AFP_CHOICES, ARL_CHOICES, RIESGO_ARL_CHOICES
from apps.tenant.empresa.models import Empresa

# ⚠️ v2.60: Importar campos desde services.py (SSoT)
from apps.tenant.empleados.services import (
    EMPLEADO_LIST_FIELDS, EMPLEADO_DETAIL_FIELDS,
    CONTRATO_LIST_FIELDS, CONTRATO_DETAIL_FIELDS,
    DEVENGO_LIST_FIELDS, DEVENGO_DETAIL_FIELDS,
)


# ==============================================================================
# NORMALIZATION MIXIN (Zero Trust)
# ==============================================================================
class NormalizationMixin:
    """
    ⚠️ v2.60: Mixin para normalización de datos de entrada (Zero Trust).
    Sanitiza strings y valida tipos de datos antes de persistir.
    """
    def normalize_data(self, attrs):
        """
        Normaliza datos de entrada:
        - Strings: strip() para eliminar espacios
        - Documentos: upper() para normalizar formato
        - Emails: Validación de formato
        - Nombres: Capitalización apropiada
        - Decimales: Normalizar a Decimal para campos numéricos (dias_laborados, etc.)
        """
        from decimal import Decimal, InvalidOperation
        
        for key, value in attrs.items():
            if isinstance(value, str):
                # Strip espacios
                attrs[key] = value.strip()
                
                # Normalizar documentos y códigos a mayúsculas
                if key in ['numero_documento', 'tipo_documento', 'tipo', 'estado', 'cargo']:
                    attrs[key] = attrs[key].upper()
                
                # Validar formato de email
                if key == 'email' and attrs[key]:
                    try:
                        EmailValidator()(attrs[key])
                    except DjangoValidationError:
                        raise serializers.ValidationError({key: ['El formato del email no es válido.']})
                
                # Capitalizar nombres (primer letra mayúscula, resto minúsculas)
                if key in ['primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido', 'cargo']:
                    if attrs[key]:
                        attrs[key] = attrs[key].title()
            
            # ⚠️ v2.60: Normalizar campos decimales (dias_laborados permite decimales 0.1-30)
            if key in ['dias_laborados'] and value is not None:
                from decimal import Decimal, InvalidOperation
                try:
                    attrs[key] = Decimal(str(value))
                except (ValueError, InvalidOperation, TypeError):
                    raise serializers.ValidationError({
                        key: [f'El campo {key} debe ser un número válido (permite decimales, ej: 15.5).']
                    })
        
        return attrs

class EmpleadoListSerializer(serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer optimizado para LISTAS (Tabulator Factory).
    Solo incluye campos estrictamente necesarios para la tabla del frontend.
    Campos alineados con EMPLEADO_LIST_FIELDS de services.py.
    Fase 2: Expone indicadores de estado para habilitar acciones secuenciales.
    """
    nombre_completo = serializers.ReadOnlyField()
    tipo_doc_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    # Indicadores de estado procedentes de anotaciones en services.py
    # Determinan la visibilidad de botones: Crear Contrato -> Registrar Nómina -> Historial
    tiene_contrato_activo = serializers.BooleanField(read_only=True)
    tiene_nominas_registradas = serializers.BooleanField(read_only=True)

    class Meta:
        model = Empleado
        fields = (
            'id', 'tipo_documento', 'tipo_doc_display', 'numero_documento', 
            'nombre_completo', 'estado', 'estado_display', 'fecha_ingreso',
            'tiene_contrato_activo', 'tiene_nominas_registradas'
        )
        read_only_fields = ['id', 'nombre_completo', 'tipo_doc_display', 'estado_display', 
                           'tiene_contrato_activo', 'tiene_nominas_registradas']

class ContratoNestedSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    ⚠️ v2.60: Serializer para gestión de contratos vinculados a empleados.
    Campos alineados con CONTRATO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    
    ⚠️ v2.95: La creación se maneja en perform_create del ViewSet usando service layer.
    Este serializer solo valida y serializa datos.
    """
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    
    # ⚠️ v2.60: Campo empleado - puede venir como ID (string) desde FormData
    empleado = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all(),
        required=True,
        help_text="ID del empleado (puede venir como string desde FormData)"
    )
    
    # ⚠️ v2.95: Campos opcionales con valores por defecto (valores en COP)
    auxilio_transporte = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Auxilio de transporte en COP")
    prestamos_empresa = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Préstamos de la empresa en COP")
    fecha_fin = serializers.DateField(required=False, allow_null=True)
    archivo_pdf = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Contrato
        fields = (
            'id', 'empleado', 'empleado_nombre', 'tipo', 'tipo_display', 
            'fecha_inicio', 'fecha_fin', 'salario_mensual', 'auxilio_transporte', 
            'prestamos_empresa', 'cargo', 'archivo_pdf', 'estado', 'estado_display', 'activo'
        )
        read_only_fields = ('estado_display', 'activo', 'empleado_nombre')  # ⚠️ v2.95: activo se sincroniza con estado
    
    def validate(self, attrs):
        """
        ⚠️ v2.60: Zero Trust - Normalización estricta y validación antes de persistir.
        """
        attrs = self.normalize_data(attrs)
        
        # Validar que fecha_fin sea posterior a fecha_inicio si ambas están presentes
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de inicio.'
            })
        
        return attrs
    
    def validate_empleado(self, value):
        """⚠️ v2.60: Validación estricta - Asegurar que el empleado pertenezca al tenant actual."""
        if value is None:
            return value
        
        # Obtener empresa del contexto (debe estar disponible en el ViewSet)
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise serializers.ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        if not Empleado.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise serializers.ValidationError(f"El empleado con ID {value.id} no pertenece a este tenant.")
        
        return value
    
    # ⚠️ v2.95: NO implementar create() aquí - se maneja en perform_create del ViewSet
    # El ViewSet usa gestionar_contrato_service para crear el contrato
    
    def update(self, instance, validated_data):
        """
        ⚠️ v2.40: Solo permitir edición si el contrato está ACTIVO.
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
    ⚠️ v2.60: Serializer de Nómina vinculado a Contrato.
    Campos alineados con DEVENGO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    
    ⚠️ Zero Trust: Los valores calculados (salario_base, auxilio_transporte, salud_empleado, 
    pension_empleado, neto_pagar) son READ_ONLY. El backend los calcula en perform_create usando
    la capa de servicio (calcular_liquidacion_nomina). El frontend NUNCA debe enviar estos valores.
    
    v2.40: Los valores proporcionales se calculan desde la lógica de servicio.
    ⚠️ v2.95: Todos los valores monetarios están en COP (Pesos Colombianos).
    """
    # ⚠️ v2.60: Campos requeridos
    periodo_mes = serializers.CharField(required=True, help_text="Periodo en formato YYYY-MM (ej: 2024-01)")
    fecha_pago = serializers.DateField(required=True)
    dias_laborados = serializers.DecimalField(max_digits=5, decimal_places=2, required=True, help_text="Días laborados (0.5-30, permite decimales)")
    empleado = serializers.PrimaryKeyRelatedField(queryset=Empleado.objects.all(), required=True, help_text="ID del empleado")
    contrato = serializers.PrimaryKeyRelatedField(queryset=Contrato.objects.all(), required=True, help_text="ID del contrato activo")
    
    # ⚠️ v2.60: Campos calculados - READ_ONLY (Zero Trust: el backend los calcula, nunca confiar en el frontend)
    salario_base = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Salario base proporcional en COP (calculado automáticamente)")
    auxilio_transporte = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Auxilio de transporte proporcional en COP (calculado automáticamente)")
    salud_empleado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Deducción de salud (4%) en COP (calculado automáticamente)")
    pension_empleado = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Deducción de pensión (4%) en COP (calculado automáticamente)")
    neto_pagar = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, help_text="Neto a pagar en COP (calculado automáticamente)")
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    
    # ⚠️ v2.95: Campos opcionales con valores por defecto
    prestamos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Préstamos descontados en COP")
    descuentos_operativos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Descuentos operativos en COP")
    otros_devengos = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0, help_text="Otros devengos en COP")
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
    def __init__(self, *args, **kwargs):
        """⚠️ v2.60: Inicializar querysets dinámicamente para validación Zero Trust."""
        super().__init__(*args, **kwargs)
        # Obtener empresa del contexto o request
        empresa = Empresa.objects.only('id').first()
        if empresa:
            # Filtrar querysets por empresa (Zero Trust) - Actualizar después de la inicialización
            if 'empleado' in self.fields:
                self.fields['empleado'].queryset = Empleado.objects.filter(empresa_id=empresa.id)
            if 'contrato' in self.fields:
                self.fields['contrato'].queryset = Contrato.objects.filter(empresa_id=empresa.id)

    class Meta:
        model = Devengo
        fields = (
            'id', 'empleado', 'contrato', 'empleado_nombre', 'periodo_mes', 
            'fecha_pago', 'dias_laborados', 'salario_base', 'auxilio_transporte', 
            'otros_devengos', 'salud_empleado', 'pension_empleado',
            'prestamos', 'descuentos_operativos', 'observaciones',
            'neto_pagar', 'anulado'
        )
        read_only_fields = ('salario_base', 'auxilio_transporte', 'salud_empleado', 'pension_empleado', 'neto_pagar', 'anulado', 'empleado_nombre')
    
    def validate(self, attrs):
        """
        ⚠️ v2.60: Zero Trust - Normalización estricta antes de persistir.
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
                    'dias_laborados': ['Los días laborados deben estar entre 0.5 y 30.']
                })
        
        return attrs
    
    def validate_empleado(self, value):
        """⚠️ v2.60: Validación estricta - Asegurar que el empleado pertenezca al tenant actual."""
        if value is None:
            return value
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise serializers.ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        if not Empleado.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise serializers.ValidationError(f"El empleado con ID {value.id} no pertenece a este tenant.")
        
        return value
    
    def validate_contrato(self, value):
        """⚠️ v2.60: Validación estricta - Asegurar que el contrato pertenezca al tenant actual y al empleado."""
        if value is None:
            return value
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise serializers.ValidationError("No se encontró configuración de Empresa para este tenant.")
        
        if not Contrato.objects.filter(pk=value.id, empresa_id=empresa.id).exists():
            raise serializers.ValidationError(f"El contrato con ID {value.id} no pertenece a este tenant.")
        
        # Validar que el contrato pertenezca al empleado (si está en el contexto)
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
    ⚠️ v2.60: Serializer completo para DETALLE/EDICIÓN de Empleados.
    Campos alineados con EMPLEADO_DETAIL_FIELDS de services.py.
    Aplica NormalizationMixin para sanitizar datos de entrada.
    
    ⚠️ v2.95: Incluye campos de seguridad social (EPS, AFP, ARL).
    """
    contratos = ContratoNestedSerializer(many=True, read_only=True)
    nombre_completo = serializers.ReadOnlyField()
    
    # Campos opcionales
    segundo_nombre = serializers.CharField(required=False, allow_blank=True, allow_null=False)
    segundo_apellido = serializers.CharField(required=False, allow_blank=True, allow_null=False)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=False)
    fecha_retiro = serializers.DateField(required=False, allow_null=True)
    
    # ⚠️ v2.95: Campos de seguridad social
    eps = serializers.ChoiceField(choices=EPS_CHOICES, required=True)
    afp = serializers.ChoiceField(choices=AFP_CHOICES, required=True)
    arl = serializers.ChoiceField(choices=ARL_CHOICES, required=True)
    nivel_riesgo_arl = serializers.ChoiceField(
        choices=RIESGO_ARL_CHOICES,
        required=False,
        default='I'
    )
    
    # ⚠️ v2.60: Empresa es read_only pero se asigna en perform_create
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Empleado
        fields = (
            'id', 'empresa', 'tipo_documento', 'numero_documento',
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'email', 'telefono', 
            'eps', 'afp', 'arl', 'nivel_riesgo_arl',  # ⚠️ v2.95: Seguridad Social
            'estado', 'fecha_ingreso', 'fecha_retiro',
            'nombre_completo', 'contratos'
        )
        read_only_fields = ('empresa', 'nombre_completo', 'contratos')
    
    def validate(self, attrs):
        """
        ⚠️ v2.60: Zero Trust - Normalización estricta antes de persistir.
        """
        # Remover empresa si viene en los datos (debe ser asignada por perform_create)
        attrs.pop('empresa', None)
        attrs = self.normalize_data(attrs)
        return attrs
    
    def validate_email(self, value):
        """⚠️ v2.60: Validación estricta de formato de email."""
        if value:
            try:
                EmailValidator()(value.strip())
            except DjangoValidationError:
                raise serializers.ValidationError('El formato del email no es válido.')
        return value