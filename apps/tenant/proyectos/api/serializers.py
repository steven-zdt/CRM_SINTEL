"""
Serializers para Proyectos v3.3 - Alineado con Modelo, Tabulator y Zero Trust (v2.40)

# WARNING: v3.3: Stand-Alone Module (SSoT Strict)
- Serializers alineados con el modelo actual (v3.3)
- Campos optimizados para Tabulator Factory v2.40 (List vs Detail)
- Soporte para snapshots de clientes y responsables
- [SHIELD] Zero Trust: Implementación de NormalizationMixin obligatoria para inputs
"""
from rest_framework import serializers

from apps.tenant.proyectos.models import AsignacionPersonal, ItemPedido, PedidoProyecto, Proyecto, ItemPresupuestoProyecto, TareaDiariaProyecto


# ==============================================================================
# CUSTOM RELATED FIELD (UUID-Safe)
# ==============================================================================
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

        # ⚠️ UUID-Safe: Detectar si es UUID (tiene guiones) o PK entero
        if '-' in data_str and not data_str.isdigit():
            # Es un UUID — buscar por uuid field
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

        # Es un PK entero — usar el método parent
        return super().to_internal_value(data)


class NormalizationMixin:
    """
    Mixin para normalización de datos de entrada (Zero Trust).
    Implementación local para garantizar arquitectura Stand-Alone.
    """
    def normalize_data(self, attrs):
        for key, value in attrs.items():
            if isinstance(value, str):
                attrs[key] = value.strip()
        return attrs

class ProyectoListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado Tabulator v3.3.
    Mínima exposición de datos (Need-to-Know) y sin campos anidados pesados.
    
    # WARNING: Campos alineados con proyectos.page.js:
    - id, codigo, nombre, tipo_servicio_display, estado_display
    - fecha_inicio, fecha_fin_prevista (alias de fecha_fin_estimada)
    """
    tipo_servicio_display = serializers.CharField(source='get_tipo_servicio_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_tarea_display', read_only=True)
    fase_actual_display = serializers.CharField(source='get_fase_actual_display', read_only=True)
    fecha_fin_prevista = serializers.DateField(source='fecha_fin_estimada', read_only=True)
    
    # Snapshots (campos desacoplados)
    cliente_nombre = serializers.CharField(read_only=True)
    responsable_actual_nombre = serializers.CharField(read_only=True)
    proveedor_nombre = serializers.CharField(read_only=True)
    servicio_nombre = serializers.CharField(source='servicio_asociado.nombre', read_only=True, allow_null=True)

    # Campos financieros calculados
    costo_total = serializers.SerializerMethodField()
    utilidad_estimada = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    margen_rentabilidad = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    factura_costo_numero   = serializers.CharField(source='factura_costo.numero',            read_only=True)
    cotizacion_numero      = serializers.CharField(source='factura_costo.cotizacion_numero',  read_only=True)
    cotizacion_uuid        = serializers.UUIDField( source='factura_costo.cotizacion_uuid',    read_only=True)

    class Meta:
        model = Proyecto
        fields = [
            # Campos básicos (Tabulator)
            'id', 'uuid', 'codigo', 'nombre', 'tipo_servicio', 'tipo_servicio_display',
            'fase_actual', 'fase_actual_display', 'estado_tarea', 'estado_display',
            'fecha_inicio', 'fecha_fin_estimada', 'fecha_fin_prevista',

            # Snapshots
            'cliente_id', 'cliente_nombre',
            'responsable_actual_id', 'responsable_actual_nombre',
            'proveedor_id', 'proveedor_nombre',

            # Vínculos
            'factura_costo', 'factura_costo_numero',
            'cotizacion_numero', 'cotizacion_uuid',
            'servicio_asociado_id', 'servicio_nombre',
            
            # Financieros
            'valor_contrato_proyectado',
            'costo_planeado_total', 'utilidad_planeada', 'margen_planeado',
            'costo_mano_obra_real', 'costo_materiales_real',
            'costo_total', 'utilidad_estimada', 'margen_rentabilidad',
            
            # Progreso
            'porcentaje_avance', 'fecha_cierre_real',
            
            # Timestamps
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'costo_mano_obra_real', 'costo_materiales_real',
            'utilidad_estimada', 'margen_rentabilidad',
        ]

    def get_costo_total(self, obj):
        """Calcula el costo total (mano de obra + materiales)."""
        return obj.costo_mano_obra_real + obj.costo_materiales_real


class AsignacionPersonalSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para asignaciones de personal al proyecto.
    [SHIELD] Zero Trust: Aplica normalización de datos en el input.
    """
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = AsignacionPersonal
        fields = [
            'id', 'empleado_id', 'nombre_colaborador', 'rol', 'rol_display',
            'fecha_asignacion', 'fecha_fin_asignacion',
            'horas_totales_registradas', 'costo_hora', 'costo_total_asignacion',
            'activo'
        ]
        read_only_fields = ['id', 'costo_total_asignacion']

    def validate(self, attrs):
        """# WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        
        # Validación de negocio: No permitir asignaciones en proyectos en fase de CIERRE
        proyecto = attrs.get('proyecto') or (self.instance.proyecto if self.instance else None)
        if not proyecto and self.context:
            proyecto = self.context.get('proyecto')
        if not proyecto and self.parent and hasattr(self.parent, 'instance') and self.parent.instance:
            proyecto = self.parent.instance
            
        if proyecto:
            if proyecto.fase_actual == 'CIERRE':
                raise serializers.ValidationError(
                    "No se pueden agregar o modificar asignaciones de personal para proyectos en fase de CIERRE."
                )
        return attrs



class ItemPedidoSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para items de pedido.
    [SHIELD] Zero Trust: Aplica normalización de strings numéricos.
    """
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemPedido
        fields = [
            'id', 'material_ref', 'nombre_material', 'cantidad', 
            'unidad_medida', 'precio_unitario', 'subtotal'
        ]
        read_only_fields = ['id']

    def get_subtotal(self, obj):
        """Calcula el subtotal del item."""
        return obj.cantidad * obj.precio_unitario

    def validate(self, attrs):
        """# WARNING: Zero Trust: Normalización estricta antes de persistir."""
        attrs = self.normalize_data(attrs)
        return attrs


class PedidoProyectoSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para pedidos de recursos del proyecto.
    [SHIELD] Zero Trust: Aplica normalización estricta de inputs.
    """
    items = ItemPedidoSerializer(many=True, read_only=True)
    tipo_recurso_display = serializers.CharField(source='get_tipo_recurso_display', read_only=True)
    fuente_suministro_display = serializers.CharField(source='get_fuente_suministro_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = PedidoProyecto
        fields = [
            'id', 'proyecto', 'tipo_recurso', 'tipo_recurso_display',
            'fuente_suministro', 'fuente_suministro_display',
            'proveedor_id', 'proveedor_nombre',
            'empleado_encargado_nombre',
            'fecha_solicitud', 'estado', 'estado_display',
            'observaciones', 'archivo_adjunto', 'items'
        ]
        read_only_fields = ['id', 'fecha_solicitud']

    def validate(self, attrs):
        """
        # WARNING: Zero Trust: Normalización estricta y validación de reglas de negocio.
        """
        attrs = self.normalize_data(attrs)
        
        # Validación de negocio: No permitir pedidos en proyectos cerrados
        proyecto = attrs.get('proyecto') or (self.instance.proyecto if self.instance else None)
        if not proyecto and self.context:
            proyecto = self.context.get('proyecto')
        if not proyecto and self.parent and hasattr(self.parent, 'instance') and self.parent.instance:
            proyecto = self.parent.instance
            
        if proyecto:
            if proyecto.fase_actual == 'CIERRE':
                raise serializers.ValidationError(
                    "No se pueden generar o modificar pedidos para proyectos en fase de CIERRE."
                )
        return attrs


class ItemPresupuestoSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para ítems de presupuesto planeado (v3.5.2).
    Usado en endpoint independiente /api/v1/proyectos/items-presupuesto/
    y anidado en ProyectoDetailSerializer.

    [SHIELD] Zero Trust: DSV mediante empresa_id en contexto.
    """
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)

    class Meta:
        model = ItemPresupuestoProyecto
        fields = [
            'id', 'proyecto_id', 'empresa_id', 'categoria', 'categoria_display',
            'descripcion', 'cantidad', 'valor_unitario', 'subtotal'
        ]
        read_only_fields = ['id', 'empresa_id', 'subtotal']

    def validate(self, attrs):
        """Zero Trust: Normalización de datos."""
        attrs = self.normalize_data(attrs)
        return attrs


class ProyectoDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer completo para detalle de proyecto v3.3 y operaciones Write.
    
    # WARNING: Incluye todas las relaciones y campos calculados. Excluye datos pesados en listados.
    [SHIELD] Zero Trust: Aplica normalización de datos.
    """
    # Display fields
    tipo_servicio_display = serializers.CharField(source='get_tipo_servicio_display', read_only=True)
    fase_actual_display = serializers.CharField(source='get_fase_actual_display', read_only=True)
    estado_tarea_display = serializers.CharField(source='get_estado_tarea_display', read_only=True)
    
    # Relaciones anidadas
    equipo_trabajo = AsignacionPersonalSerializer(many=True, read_only=True)
    pedidos = PedidoProyectoSerializer(many=True, read_only=True)
    items_presupuesto = ItemPresupuestoSerializer(many=True, read_only=True)

    # Campos calculados
    costo_total = serializers.SerializerMethodField()
    indicadores_financieros = serializers.SerializerMethodField()
    
    # Snapshots (información desacoplada)
    cliente_info = serializers.SerializerMethodField()
    responsables_info = serializers.SerializerMethodField()
    proveedor_info = serializers.SerializerMethodField()
    servicio_nombre = serializers.CharField(source='servicio_asociado.nombre', read_only=True, allow_null=True)
    servicio_asociado_uuid = serializers.CharField(source='servicio_asociado.uuid', read_only=True, allow_null=True)
    servicio_asociado = UUIDOrPKRelatedField(queryset=None, required=False, allow_null=True)
    cotizacion_info = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        exclude = ['empresa']  # SSoT: La empresa se maneja a nivel de viewset/middleware/services
        read_only_fields = [
            'id', 'uuid', 'created_at', 'updated_at',
            'costo_mano_obra_real', 'costo_materiales_real',
            'utilidad_estimada', 'margen_rentabilidad',
            'costo_planeado_total', 'utilidad_planeada', 'margen_planeado',
        ]
        extra_kwargs = {
            # Configuración Write-Only para evitar redundancia en la respuesta JSON
            # (La lectura se realiza vía cliente_info y responsables_info)
            'cliente_id': {'write_only': True},
            'cliente_nombre': {'write_only': True},
            'proveedor_id': {'write_only': True},
            'proveedor_nombre': {'write_only': True},
            'responsable_actual_id': {'write_only': True},
            'responsable_actual_nombre': {'write_only': True},
            'responsable_comercial_id': {'write_only': True},
            'responsable_comercial_nombre': {'write_only': True},
            'responsable_tecnico_id': {'write_only': True},
            'responsable_tecnico_nombre': {'write_only': True},
            'responsable_operativo_id': {'write_only': True},
            'responsable_operativo_nombre': {'write_only': True},
            'responsable_administrativo_id': {'write_only': True},
            'responsable_administrativo_nombre': {'write_only': True},
        }

    def __init__(self, *args, **kwargs):
        """Inicializa y filtra queryset de servicio_asociado por empresa_id."""
        super().__init__(*args, **kwargs)

        # Poblar queryset del campo servicio_asociado
        if 'servicio_asociado' in self.fields:
            try:
                from apps.tenant.inventario.models import Servicio
                empresa_id = self.context.get('empresa_id')
                if empresa_id:
                    self.fields['servicio_asociado'].queryset = Servicio.objects.filter(
                        empresa_id=empresa_id
                    )
                else:
                    self.fields['servicio_asociado'].queryset = Servicio.objects.none()
            except ImportError:
                self.fields['servicio_asociado'].queryset = Servicio.objects.none()

    def get_cotizacion_info(self, obj):
        """Resuelve la cotizacion vinculada via Factura.cotizacion_uuid (Zero-Waste)."""
        if not obj.factura_costo_id:
            return None
        try:
            from apps.tenant.facturas.services.business_service import FacturaInterAppAPI
            return FacturaInterAppAPI.resolve_cotizacion(factura_id=obj.factura_costo_id)
        except Exception:
            return None

    def validate(self, attrs):
        """
        # WARNING: Zero Trust: Limpieza y normalización de todos los datos ingresados.
        Phase-based validation: Only require responsables for their designated phase and later.
        """
        attrs = self.normalize_data(attrs)

        # Get the project's current phase (from instance if updating, from attrs if creating)
        proyecto = self.instance if self.instance else None
        fase_actual = attrs.get('fase_actual') or (proyecto.fase_actual if proyecto else 'BORRADOR')

        # Phase mapping to numeric values
        PHASE_LEVELS = {
            'BORRADOR': 0,
            'INICIO': 1,
            'PLANEACION': 2,
            'EJECUCION': 3,
            'CIERRE': 4,
        }

        current_phase_level = PHASE_LEVELS.get(fase_actual, 0)

        # Convert empty strings to None for responsable fields (avoid "invalid integer" errors)
        responsable_fields = [
            'responsable_comercial_id',
            'responsable_tecnico_id',
            'responsable_operativo_id',
            'responsable_administrativo_id',
        ]

        for field in responsable_fields:
            if field in attrs and attrs[field] == '':
                attrs[field] = None
            # Also handle the corresponding name fields
            name_field = field.replace('_id', '_nombre')
            if name_field in attrs and attrs[name_field] == '':
                attrs[name_field] = None

        # Phase-based validation: require responsables only if fase_actual allows it
        if current_phase_level >= PHASE_LEVELS['INICIO']:
            # Phase 1+: responsable_comercial is optional (form shows it but doesn't force it)
            pass

        if current_phase_level >= PHASE_LEVELS['PLANEACION']:
            # Phase 2+: responsable_tecnico is optional (form shows it but doesn't force it)
            pass

        if current_phase_level >= PHASE_LEVELS['EJECUCION']:
            # Phase 3+: responsable_operativo is optional
            pass

        if current_phase_level >= PHASE_LEVELS['CIERRE']:
            # Phase 4: responsable_administrativo is optional
            pass

        # Note: All responsables are optional by design to allow flexibility.
        # The template controls visibility, but the API accepts any phase configuration.

        return attrs

    def get_costo_total(self, obj):
        """Calcula el costo total del proyecto."""
        return obj.costo_mano_obra_real + obj.costo_materiales_real

    def get_indicadores_financieros(self, obj):
        """
        Indicadores financieros reales y planeados (v3.5.3-fix).

        BASE: valor_contrato_proyectado es la base de todos los calculos.
        REAL:
          utilidad_real   = valor_contrato - (costo_mano_obra_real + costo_materiales_real)
          margen_real %   = utilidad_real / valor_contrato * 100
        PLANEADO:
          utilidad_plan   = valor_contrato - costo_planeado_total
          margen_plan %   = utilidad_plan / valor_contrato * 100
        VARIACION:
          variacion_costo = costo_planeado_total - costo_total_real
          (positivo = bajo presupuesto, negativo = sobre presupuesto)
        """
        valor_contrato   = float(obj.valor_contrato_proyectado or 0)
        costo_mano_obra  = float(obj.costo_mano_obra_real or 0)
        costo_materiales = float(obj.costo_materiales_real or 0)
        costo_total_real = costo_mano_obra + costo_materiales
        costo_plan       = float(obj.costo_planeado_total or 0)

        utilidad_real  = valor_contrato - costo_total_real
        margen_real    = (utilidad_real / valor_contrato * 100) if valor_contrato > 0 else 0

        utilidad_plan  = float(obj.utilidad_planeada or 0)
        margen_plan    = float(obj.margen_planeado or 0)

        # variacion_costo: diferencia presupuesto vs ejecucion
        # positivo = se ejecuto bajo presupuesto, negativo = sobrecosto
        variacion_costo     = costo_plan - costo_total_real
        variacion_costo_pct = (variacion_costo / costo_plan * 100) if costo_plan > 0 else 0

        return {
            "real": {
                "valor_contrato":    float(valor_contrato),
                "costo_mano_obra":   float(costo_mano_obra),
                "costo_materiales":  float(costo_materiales),
                "costo_total":       float(costo_total_real),
                "utilidad_estimada": float(utilidad_real),
                "margen_rentabilidad": round(float(margen_real), 2),
            },
            "planeado": {
                "costo_planeado_total": float(costo_plan),
                "utilidad_planeada":    float(utilidad_plan),
                "margen_planeado":      round(float(margen_plan), 2),
            },
            "variacion": {
                "costo_abs": variacion_costo,
                "costo_pct": round(variacion_costo_pct, 2),
            },
        }

    def get_cliente_info(self, obj):
        """Información del cliente (snapshot)."""
        if obj.cliente_id:
            return {
                "id": obj.cliente_id,
                "nombre": obj.cliente_nombre or "N/A",
            }
        return None

    def get_responsables_info(self, obj):
        """Información de todos los responsables por fase (snapshots)."""
        return {
            "comercial": {
                "id": obj.responsable_comercial_id,
                "nombre": obj.responsable_comercial_nombre or "N/A",
            },
            "tecnico": {
                "id": obj.responsable_tecnico_id,
                "nombre": obj.responsable_tecnico_nombre or "N/A",
            },
            "operativo": {
                "id": obj.responsable_operativo_id,
                "nombre": obj.responsable_operativo_nombre or "N/A",
            },
            "administrativo": {
                "id": obj.responsable_administrativo_id,
                "nombre": obj.responsable_administrativo_nombre or "N/A",
            },
            "actual": {
                "id": obj.responsable_actual_id,
                "nombre": obj.responsable_actual_nombre or "N/A",
            },
        }

    def get_proveedor_info(self, obj):
        """Información del proveedor (snapshot)."""
        if obj.proveedor_id:
            return {
                "id": obj.proveedor_id,
                "nombre": obj.proveedor_nombre or "N/A",
            }
        return None


class TareaDiariaSerializer(NormalizationMixin, serializers.ModelSerializer):
    """
    Serializer para tareas diarias (v3.5.4).
    Usado en endpoint independiente /api/v1/proyectos/tareas-diarias/

    Soporta tareas con período [fecha_inicio, fecha_fin].

    [SHIELD] Zero Trust: DSV mediante empresa_id en contexto.
    Validaciones integradas contra fechas del proyecto y fase CIERRE.
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)

    class Meta:
        model = TareaDiariaProyecto
        fields = [
            'id', 'proyecto_id', 'fecha_inicio', 'fecha_fin', 'titulo', 'descripcion',
            'estado', 'estado_display', 'prioridad', 'prioridad_display',
            'asignado_a', 'notas_progreso', 'created_at'
        ]
        read_only_fields = ['id', 'estado_display', 'prioridad_display', 'created_at']

    def validate(self, attrs):
        """
        Zero Trust: Validación integrada de fechas y fase CIERRE.
        """
        attrs = self.normalize_data(attrs)

        # Obtener proyecto desde datos o desde instancia existente
        proyecto = attrs.get('proyecto') or (self.instance.proyecto if self.instance else None)
        if not proyecto and self.context:
            proyecto = self.context.get('proyecto')

        fecha_inicio = attrs.get('fecha_inicio') or (self.instance.fecha_inicio if self.instance else None)
        fecha_fin = attrs.get('fecha_fin') or (self.instance.fecha_fin if self.instance else None)

        # Validar rango si tenemos proyecto y ambas fechas
        if proyecto and fecha_inicio and fecha_fin:
            if fecha_inicio > fecha_fin:
                raise serializers.ValidationError(
                    "La fecha de inicio no puede ser posterior a la fecha de fin"
                )
            if proyecto.fecha_fin_estimada and fecha_fin > proyecto.fecha_fin_estimada:
                raise serializers.ValidationError(
                    f"La fecha de fin de la tarea no puede ser posterior a la fecha fin del proyecto ({proyecto.fecha_fin_estimada})"
                )

        # Validar que proyecto NO esté en CIERRE
        if proyecto and proyecto.fase_actual == 'CIERRE':
            raise serializers.ValidationError(
                "No se pueden crear, modificar o eliminar tareas en proyectos en fase de CIERRE"
            )

        return attrs
