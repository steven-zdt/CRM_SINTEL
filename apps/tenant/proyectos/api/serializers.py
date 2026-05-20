"""
Serializers para Proyectos v3.3 - Alineado con Modelo, Tabulator y Zero Trust (v2.40)

# WARNING: v3.3: Stand-Alone Module (SSoT Strict)
- Serializers alineados con el modelo actual (v3.3)
- Campos optimizados para Tabulator Factory v2.40 (List vs Detail)
- Soporte para snapshots de clientes y responsables
- [SHIELD] Zero Trust: Implementación de NormalizationMixin obligatoria para inputs
"""
from rest_framework import serializers

from apps.tenant.proyectos.models import AsignacionPersonal, ItemPedido, PedidoProyecto, Proyecto


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
    
    # Campos financieros calculados
    costo_total = serializers.SerializerMethodField()
    utilidad_estimada = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    margen_rentabilidad = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    factura_costo_numero = serializers.CharField(source='factura_costo.numero', read_only=True)

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
            
            # Financieros
            'valor_contrato_proyectado', 'costo_mano_obra_real', 'costo_materiales_real',
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
    
    # Vínculos cross-app
    factura_costo_numero = serializers.CharField(source='factura_costo.numero', read_only=True)
    
    # Relaciones anidadas
    equipo_trabajo = AsignacionPersonalSerializer(many=True, read_only=True)
    pedidos = PedidoProyectoSerializer(many=True, read_only=True)
    
    # Campos calculados
    costo_total = serializers.SerializerMethodField()
    indicadores_financieros = serializers.SerializerMethodField()
    
    # Snapshots (información desacoplada)
    cliente_info = serializers.SerializerMethodField()
    responsables_info = serializers.SerializerMethodField()
    proveedor_info = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        exclude = ['empresa']  # SSoT: La empresa se maneja a nivel de viewset/middleware/services
        read_only_fields = [
            'id', 'uuid', 'created_at', 'updated_at',
            'costo_mano_obra_real', 'costo_materiales_real',
            'utilidad_estimada', 'margen_rentabilidad',
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

    def validate(self, attrs):
        """# WARNING: Zero Trust: Limpieza y normalización de todos los datos ingresados."""
        attrs = self.normalize_data(attrs)
        
        # Validación de negocio: Bloquear edición de costos y datos críticos en fase de CIERRE
        if self.instance and self.instance.fase_actual == 'CIERRE':
            # Campos permitidos para carga de actas/informes o finalización
            allowed_fields = {'acta_entrega_archivo', 'informe_final_archivo', 'fecha_cierre_real', 'porcentaje_avance', 'estado_tarea'}
            disallowed_changes = []
            for key, val in attrs.items():
                if key not in allowed_fields:
                    current_val = getattr(self.instance, key)
                    # Si es FK, comparar el ID
                    if hasattr(current_val, 'id') and hasattr(val, 'id'):
                        if current_val.id != val.id:
                            disallowed_changes.append(key)
                    elif current_val != val:
                        disallowed_changes.append(key)
            if disallowed_changes:
                raise serializers.ValidationError(
                    "No se pueden modificar costos ni datos críticos de un proyecto en fase de CIERRE."
                )
        return attrs

    def get_costo_total(self, obj):
        """Calcula el costo total del proyecto."""
        return obj.costo_mano_obra_real + obj.costo_materiales_real

    def get_indicadores_financieros(self, obj):
        """
        Calcula indicadores financieros del proyecto.
        """
        costo_total = obj.costo_mano_obra_real + obj.costo_materiales_real
        valor_contrato = obj.valor_contrato_proyectado
        
        return {
            "valor_contrato": float(valor_contrato),
            "costo_total": float(costo_total),
            "utilidad_estimada": float(obj.utilidad_estimada),
            "margen_rentabilidad": float(obj.margen_rentabilidad),
            "variacion_costo": float(valor_contrato - costo_total) if valor_contrato > 0 else 0,
            "indice_rentabilidad": float(obj.utilidad_estimada / valor_contrato * 100) if valor_contrato > 0 else 0,
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
