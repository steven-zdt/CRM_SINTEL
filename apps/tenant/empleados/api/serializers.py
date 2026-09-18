"""
Serializers para Empleados v2.60.

WARNING: SINTEL v2.60: Sincronizacion Arquitectonica
- NormalizationMixin: Todos los serializadores heredan de este Mixin para sanitizar strings y validar tipos
- Validacion Estricta: validate_<field> para asegurar que ForeignKeys pertenezcan al tenant actual
- Separacion List/Detail: ListSerializer para tablas, DetailSerializer para formularios
- Campos Explicitos: PROHIBIDO __all__, usar campos explicitos alineados con LIST_FIELDS y DETAIL_FIELDS
"""
import re
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

from apps.tenant.api.utils import NormalizationMixin as BaseMixin
from apps.tenant.empleados.models import Contrato, Devengo, Empleado, ResolucionDIAN, LiquidacionPrestacion, PeriodoNomina

class NullableUUIDField(serializers.UUIDField):
    """UUIDField que convierte cadena vacia en None (util con FormData/HTMX)."""
    def to_internal_value(self, data):
        if data == '' or data is None:
            return None
        return super().to_internal_value(data)

class UUIDOrPKRelatedField(serializers.PrimaryKeyRelatedField):
    """Campo relacionado que acepta UUID publico o PK interno en formularios legacy."""

    def get_queryset(self):
        queryset = super().get_queryset()
        if queryset is None:
            return queryset
        root = getattr(self, 'root', None)
        context = getattr(root, 'context', {}) if root else {}
        empresa_id = context.get('empresa_id')
        if empresa_id and hasattr(queryset.model, 'empresa_id'):
            queryset = queryset.filter(empresa_id=empresa_id)
        return queryset

    def to_internal_value(self, data):
        if data in (None, ''):
            if self.allow_null:
                return None
            self.fail('required')

        data_str = str(data).strip()

        # WARNING: UUID-Safe: Detectar si es UUID (tiene guiones) o PK entero
        if '-' in data_str and not data_str.isdigit():
            # Es un UUID - buscar por uuid field
            queryset = self.get_queryset()
            try:
                obj = queryset.get(uuid=data_str)
                return obj
            except Exception as e:
                # Manejar tanto DoesNotExist como otros errores
                import sys
                print(
                    f"[DEBUG] UUID lookup failed: uuid='{data_str}', error={type(e).__name__}: {e}",
                    file=sys.stderr
                )
                self.fail('does_not_exist', pk_value=data)

        # Es un PK entero - usar el metodo parent
        return super().to_internal_value(data)

# WARNING: v2.60: Importar campos desde services.py (SSoT)
from apps.tenant.empresa.models import Area, Empresa, Sede

from ..choices import AFP_CHOICES, ARL_CHOICES, EPS_CHOICES, MOTIVO_RETIRO_CHOICES, RIESGO_ARL_CHOICES
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

    # Sede and Area display fields (FASE 2: API & Serializacion)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, allow_null=True)

    # Foto de perfil — URL relativa para el avatar en Tabulator
    foto_url = serializers.SerializerMethodField()

    # Indicadores de estado procedentes de anotaciones en services.py
    # Determinan la visibilidad de botones: Crear Contrato -> Registrar Nomina -> Historial
    tiene_contrato_activo = serializers.BooleanField(read_only=True)
    tiene_nominas_registradas = serializers.BooleanField(read_only=True)
    contrato_activo_uuid = serializers.UUIDField(read_only=True, allow_null=True)
    cargo = serializers.CharField(read_only=True, allow_null=True)

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
            'tiene_contrato_activo', 'tiene_nominas_registradas', 'contrato_activo_uuid',
            'email', 'telefono', 'cargo',
            'sede_nombre', 'area_nombre'
        )
        read_only_fields = ['id', 'uuid', 'nombre_completo', 'tipo_doc_display', 'estado_display',
                           'foto_url',
                           'tiene_contrato_activo', 'tiene_nominas_registradas', 'contrato_activo_uuid',
                           'email', 'telefono', 'cargo', 'sede_nombre', 'area_nombre']

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
    
    # WARNING: v2.60: Campo empleado - puede venir como ID o UUID desde FormData
    empleado = UUIDOrPKRelatedField(
        queryset=Empleado.objects.none(),
        required=True,
        help_text="ID o UUID del empleado (puede venir como string/UUID desde FormData)"
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
    dias_laborados = serializers.DecimalField(max_digits=5, decimal_places=2, required=True, help_text="Dias laborados (0.5-31, permite decimales)")
    empleado = UUIDOrPKRelatedField(
        queryset=Empleado.objects.none(),
        required=True,
        help_text="ID o UUID del empleado"
    )
    contrato = UUIDOrPKRelatedField(
        queryset=Contrato.objects.none(),
        required=True,
        help_text="ID o UUID del contrato activo"
    )
    # mision auditoria nomina "correccion arquitectonica" (2026-09-10): antes
    # de este campo, la UNICA forma de vincular un Devengo a un PeriodoNomina
    # era preliquidar_periodo() (forzaba dias_laborados=30 para TODOS). Este
    # campo habilita la liquidacion INDIVIDUAL dentro de un periodo -- cada
    # empleado con sus propios dias_laborados (8, 15, 5...), el periodo es
    # solo el contenedor administrativo, nunca determina los dias.
    periodo = UUIDOrPKRelatedField(
        queryset=PeriodoNomina.objects.none(),
        required=False,
        allow_null=True,
        help_text="UUID del PeriodoNomina al que pertenece esta liquidacion (opcional)"
    )
    periodo_info = serializers.SerializerMethodField()

    def get_periodo_info(self, obj):
        p = obj.periodo
        if not p:
            return None
        return {'uuid': str(p.uuid), 'periodo_mes': p.periodo_mes, 'estado': p.estado}

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
            if 'periodo' in self.fields:
                self.fields['periodo'].queryset = PeriodoNomina.objects.filter(
                    empresa_id=empresa_id,
                ).only('id', 'uuid', 'empresa_id', 'estado', 'periodo_mes')

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
            'periodo_mes', 'periodo', 'periodo_info', 'fecha_pago', 'dias_laborados',
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
        )
        read_only_fields = (
            'id', 'uuid',
            'salario_base', 'auxilio_transporte', 'salud_empleado', 'pension_empleado', 'neto_pagar',
            'valor_horas_extras',
            'anulado',
            'empleado_uuid', 'empleado_nombre', 'empleado_documento',
            'contrato_tipo', 'contrato_tipo_display', 'contrato_cargo',
            'periodo_info',
        )
        # WARNING: mision PERIODOS-NOMINA-01 (2026-09-11): DRF auto-genera un
        # validador desde CADA UniqueConstraint de Devengo.Meta.constraints, y
        # al hacerlo fuerza required=True sobre TODOS sus campos -- incluido
        # 'periodo', que es legitimamente opcional (nullable, flujo historico
        # sin periodo). El nuevo UniqueConstraint uniq_nomina_activo_per_empleado_periodo
        # (agregado para integridad a nivel de DB) rompio la creacion clasica
        # sin periodo con 400 "periodo: Este campo es requerido" pese a su
        # required=False explicito arriba. Se desactiva la auto-generacion:
        # validate() ya implementa manualmente AMBAS reglas de duplicado
        # (periodo FK L428-447, periodo_mes+fecha_pago L465-483) -- los
        # UniqueConstraint de DB quedan como ultima linea de defensa (race
        # conditions/escritura directa), no como fuente de validadores DRF.
        validators = []

    def validate(self, attrs):
        """
        WARNING: v2.60: Zero Trust - Normalizacion estricta antes de persistir.
        """
        attrs = self.normalize_data(attrs)

        # mision auditoria nomina "correccion arquitectonica" (2026-09-10):
        # liquidacion individual dentro de un periodo. El periodo es SOLO el
        # contenedor administrativo -- nunca fuerza dias_laborados (ver
        # dias_laborados arriba, validado independientemente 0.5-31).
        periodo = attrs.get('periodo')
        if periodo:
            empresa_id = self._get_empresa_id()
            if empresa_id and periodo.empresa_id != empresa_id:
                raise serializers.ValidationError({'periodo': 'El periodo no pertenece a esta empresa.'})
            if periodo.estado not in ('ABIERTO', 'PRELIQUIDADO'):
                raise serializers.ValidationError({
                    'periodo': f'No se pueden registrar liquidaciones en un periodo en estado {periodo.estado}.'
                })
            empleado_periodo = attrs.get('empleado')
            if empleado_periodo:
                qs_dup = Devengo.objects.filter(
                    empleado=empleado_periodo, periodo=periodo, anulado=False,
                ).only('id')
                if self.instance:
                    qs_dup = qs_dup.exclude(pk=self.instance.pk)
                if qs_dup.exists():
                    raise serializers.ValidationError({
                        'periodo': 'Este empleado ya tiene una liquidacion registrada en este periodo. Anulela primero para volver a liquidar.'
                    })

        # Validar formato de periodo_mes (YYYY-MM)
        periodo_mes = attrs.get('periodo_mes')
        if periodo_mes:
            if not re.match(r'^\d{4}-\d{2}$', periodo_mes):
                raise serializers.ValidationError({
                    'periodo_mes': ['El periodo debe tener el formato YYYY-MM (ej: 2024-01).']
                })
        
        # Validar rango de dias_laborados (0.5 - 31, Colombia admite meses de 31 dias)
        dias_laborados = attrs.get('dias_laborados')
        if dias_laborados is not None:
            if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('31'):
                raise serializers.ValidationError({
                    'dias_laborados': ['Los dias laborados deben estar entre 0.5 y 31.']
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
            empleado_id = None
            if isinstance(empleado, int):
                empleado_id = empleado
            elif isinstance(empleado, str) and empleado.isdigit():
                empleado_id = int(empleado)
            elif hasattr(empleado, 'id'):
                empleado_id = empleado.id
            elif isinstance(empleado, str):
                # Buscar por UUID si se envio como UUID
                empleado_id = Empleado.objects.filter(
                    empresa_id=empresa_id,
                    uuid=empleado
                ).values_list('id', flat=True).first()

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

    # Sede and Area fields (Fase 2: API & Serializacion)
    sede = UUIDOrPKRelatedField(
        queryset=Sede.objects.none(),
        required=False,
        allow_null=True,
        help_text="ID o UUID de la sede"
    )

    # Resolucion DIAN — Nomina Electronica (DSPNE)
    resolucion_dian = UUIDOrPKRelatedField(
        queryset=ResolucionDIAN.objects.none(),
        required=False,
        allow_null=True,
        help_text="UUID de la ResolucionDIAN asignada para DSPNE de este empleado"
    )
    resolucion_dian_info = serializers.SerializerMethodField()

    def get_resolucion_dian_info(self, obj):
        r = obj.resolucion_dian
        if not r:
            return None
        return {
            'uuid':              str(r.uuid),
            'numero_resolucion': r.numero_resolucion,
            'prefijo':           r.prefijo,
            'vigente':           r.vigente,
            'consecutivo':       r.consecutivo,
            'rango_hasta':       r.rango_hasta,
        }
    area = UUIDOrPKRelatedField(
        queryset=Area.objects.none(),
        required=False,
        allow_null=True,
        help_text="ID o UUID del area"
    )
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, allow_null=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, allow_null=True)

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
    motivo_retiro = serializers.ChoiceField(choices=MOTIVO_RETIRO_CHOICES, required=False, allow_null=True, allow_blank=True)

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

    def __init__(self, *args, **kwargs):
        """WARNING: v2.60: Inicializar querysets dinamicamente para validacion Zero Trust."""
        super().__init__(*args, **kwargs)
        empresa_id = self._get_empresa_id()
        if empresa_id:
            # Filtrar querysets por empresa (Zero Trust)
            if 'sede' in self.fields:
                self.fields['sede'].queryset = Sede.objects.filter(
                    empresa_id=empresa_id
                ).only('id', 'uuid', 'nombre', 'empresa_id')
            if 'area' in self.fields:
                self.fields['area'].queryset = Area.objects.filter(
                    empresa_id=empresa_id
                ).select_related('sede').only('id', 'uuid', 'nombre', 'sede_id', 'sede__id', 'sede__uuid', 'empresa_id')
            if 'resolucion_dian' in self.fields:
                self.fields['resolucion_dian'].queryset = ResolucionDIAN.objects.filter(
                    empresa_id=empresa_id
                ).only('id', 'uuid', 'numero_resolucion', 'prefijo', 'vigente',
                       'consecutivo', 'rango_hasta', 'empresa_id')

    class Meta:
        model = Empleado
        fields = (
            'id', 'uuid', 'empresa', 'tipo_documento', 'numero_documento',
            'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
            'email', 'telefono',
            'eps', 'afp', 'arl', 'nivel_riesgo_arl',
            'estado', 'fecha_ingreso', 'fecha_retiro', 'motivo_retiro',
            'foto', 'foto_url',
            'nombre_completo', 'contratos',
            'sede', 'area', 'sede_nombre', 'area_nombre',
            'resolucion_dian', 'resolucion_dian_info',
        )
        read_only_fields = ('id', 'uuid', 'empresa', 'nombre_completo', 'contratos',
                            'foto_url', 'sede_nombre', 'area_nombre', 'resolucion_dian_info')

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

        # DSV (Double Semantic Verification) para Sede y Area
        sede = attrs.get('sede')
        area = attrs.get('area')

        if sede and sede.empresa_id != empresa_id:
            raise serializers.ValidationError({'sede': 'La sede seleccionada no pertenece a esta empresa.'})

        if area:
            if area.empresa_id != empresa_id:
                raise serializers.ValidationError({'area': 'El area seleccionada no pertenece a esta empresa.'})
            if not sede:
                raise serializers.ValidationError({'sede': 'Debe seleccionar una sede si selecciona un area.'})
            if area.sede_id != sede.id:
                raise serializers.ValidationError({'area': 'El area seleccionada no pertenece a la sede seleccionada.'})

        # [OSF Fase F8] anti-IDOR ya verificaba "pertenece a la empresa" -
        # esto agrega "esta dentro del alcance organizacional del usuario".
        from apps.tenant.core.services.organizational_scope import (
            area_esta_en_alcance,
            sede_esta_en_alcance,
        )
        request = self.context.get('request')
        if sede and not sede_esta_en_alcance(sede.id, request):
            raise serializers.ValidationError(
                {'sede': 'No tiene permiso para asignar esta sede (fuera de su alcance organizacional).'}
            )
        if area and not area_esta_en_alcance(area.id, request):
            raise serializers.ValidationError(
                {'area': 'No tiene permiso para asignar esta area (fuera de su alcance organizacional).'}
            )

        # mision auditoria nomina FASE 22 (2026-09-10): retirar un empleado
        # exige motivo_retiro + fecha_retiro -- ya no basta con estado=RETIRADO
        # (ver EmpleadoBusinessService.retirar_empleado(), unica fuente de
        # verdad de esta regla; se repite aqui para dar el error en el punto
        # mas temprano posible, no para duplicar la logica de negocio).
        estado_actual = self.instance.estado if self.instance else None
        if attrs.get('estado') == 'RETIRADO' and estado_actual != 'RETIRADO':
            if not attrs.get('motivo_retiro'):
                raise serializers.ValidationError(
                    {'motivo_retiro': 'Motivo de retiro requerido para retirar un empleado.'}
                )
            if not attrs.get('fecha_retiro'):
                raise serializers.ValidationError(
                    {'fecha_retiro': 'Fecha de retiro requerida para retirar un empleado.'}
                )

        return attrs
    
    def validate_email(self, value):
        """WARNING: v2.60: Validacion estricta de formato de email."""
        if value:
            try:
                EmailValidator()(value.strip())
            except DjangoValidationError:
                raise serializers.ValidationError('El formato del email no es valido.')
        return value


class ResolucionDIANSerializer(BaseMixin, serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = ResolucionDIAN
        fields = [
            'id', 'uuid', 'prefijo', 'rango_desde', 'rango_hasta', 'consecutivo',
            'numero_resolucion', 'fecha_resolucion', 'fecha_inicio', 'fecha_fin',
            'vigente', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uuid', 'consecutivo', 'created_at', 'updated_at']

    def validate(self, attrs):
        rango_desde = attrs.get('rango_desde')
        rango_hasta = attrs.get('rango_hasta')
        if rango_desde is not None and rango_hasta is not None:
            if rango_desde > rango_hasta:
                raise serializers.ValidationError({
                    'rango_desde': 'El rango desde no puede ser mayor al rango hasta.'
                })
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        if fecha_inicio is not None and fecha_fin is not None:
            if fecha_inicio > fecha_fin:
                raise serializers.ValidationError({
                    'fecha_inicio': 'La fecha de inicio no puede ser posterior a la fecha de fin.'
                })
        return attrs


class LiquidacionPrestacionSerializer(BaseMixin, serializers.ModelSerializer):
    uuid = serializers.UUIDField(read_only=True)
    empleado_id = serializers.PrimaryKeyRelatedField(
        source='empleado',
        queryset=Empleado.objects.all(),
        required=True
    )
    contrato_id = serializers.PrimaryKeyRelatedField(
        source='contrato',
        queryset=Contrato.objects.all(),
        required=True
    )
    tipo_display = serializers.CharField(source='get_tipo_liquidacion_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    contrato_cargo = serializers.CharField(source='contrato.cargo', read_only=True)
    
    class Meta:
        model = LiquidacionPrestacion
        fields = [
            'id', 'uuid', 'empleado_id', 'contrato_id', 'tipo_liquidacion', 'tipo_display',
            'fecha_corte', 'dias_base_calculo', 'base_salarial', 'valor_total',
            'estado', 'estado_display', 'empleado_nombre', 'contrato_cargo',
            'desglose_conceptos', 'observaciones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at', 'estado']

    def validate(self, attrs):
        empresa_id = self.context.get('empresa_id')
        empleado = attrs.get('empleado')
        contrato = attrs.get('contrato')
        
        if empleado and empleado.empresa_id != empresa_id:
            raise serializers.ValidationError({'empleado_id': 'El empleado no pertenece a la empresa actual.'})
            
        if contrato and contrato.empresa_id != empresa_id:
            raise serializers.ValidationError({'contrato_id': 'El contrato no pertenece a la empresa actual.'})
            
        return attrs



class PeriodoNominaSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para PeriodoNomina (mision nomina 2026-08-21). Solo expone
    los campos que el modelo realmente tiene (FASE 2 de la mision: "no
    agregar campos especulativos") -- estado y campos de auditoria son
    read_only, se cambian exclusivamente via las acciones dedicadas del
    ViewSet (preliquidar/aprobar/marcar-pagado/etc.), nunca por PATCH directo.
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    creado_por_nombre = serializers.SerializerMethodField()
    aprobado_por_nombre = serializers.SerializerMethodField()
    pagado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = PeriodoNomina
        fields = [
            'id', 'uuid', 'periodo_mes', 'fecha_inicio', 'fecha_fin', 'fecha_pago',
            'estado', 'estado_display',
            'creado_por_nombre', 'aprobado_por_nombre', 'pagado_por_nombre',
            'fecha_aprobacion', 'fecha_pago_real', 'observaciones',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'uuid', 'estado', 'created_at', 'updated_at',
            'fecha_aprobacion', 'fecha_pago_real',
        ]

    def _nombre_perfil(self, perfil):
        if not perfil:
            return None
        nombre = f"{perfil.user.first_name} {perfil.user.last_name}".strip() if perfil.user else ''
        return nombre or (perfil.user.email if perfil.user else None)

    def get_creado_por_nombre(self, obj):
        return self._nombre_perfil(obj.creado_por)

    def get_aprobado_por_nombre(self, obj):
        return self._nombre_perfil(obj.aprobado_por)

    def get_pagado_por_nombre(self, obj):
        return self._nombre_perfil(obj.pagado_por)

    def validate_periodo_mes(self, value):
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', value or ''):
            raise serializers.ValidationError('Formato invalido, use YYYY-MM.')
        return value

    def validate(self, attrs):
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError({'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'})
        return attrs
