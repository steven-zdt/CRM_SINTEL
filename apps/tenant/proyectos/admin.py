"""
Admin para Proyectos v3.1 - Stand-Alone Data Schema (SSoT Strict)
Alineado con modelo desacoplado (sin ForeignKeys a apps externas)
"""
from django.contrib import admin
from .models import Proyecto, AsignacionPersonal, PedidoProyecto, ItemPedido


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    """
    Admin para Proyectos v3.1 - Stand-Alone Data Schema
    Modelo desacoplado: solo referencias (IDs y snapshots), sin ForeignKeys externas
    """
    list_display = [
        'nombre', 'codigo', 'tipo_servicio', 'fase_actual', 'estado_tarea', 
        'responsable_actual_nombre', 'cliente_nombre', 'fecha_inicio', 'empresa'
    ]
    list_filter = [
        'tipo_servicio', 'fase_actual', 'estado_tarea', 'empresa', 
        'fecha_inicio', 'fecha_cierre_real'
    ]
    search_fields = ['nombre', 'codigo', 'descripcion', 'cliente_nombre', 'responsable_actual_nombre']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('SSoT (Única Dependencia Externa)', {
            'fields': ('empresa',),
            'description': 'Empresa es la única ForeignKey permitida (SSoT estricto)'
        }),
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'tipo_servicio', 'descripcion')
        }),
        ('Relaciones Desacopladas (Loose Coupling)', {
            'fields': (
                ('cliente_id', 'cliente_nombre'),
                'factura_ref',
                'valor_contrato_proyectado'
            ),
            'description': 'Referencias desacopladas: IDs y snapshots (sin ForeignKeys)',
            'classes': ('collapse',)
        }),
        ('Workflow - Responsables por Fase (Snapshots)', {
            'fields': (
                'responsable_comercial_nombre',
                'responsable_tecnico_nombre',
                'responsable_operativo_nombre',
                'responsable_administrativo_nombre',
                ('responsable_actual_id', 'responsable_actual_nombre')
            ),
            'description': 'Snapshots de nombres de responsables (sin ForeignKeys a Empleados)'
        }),
        ('Documentación - Fase Inicio', {
            'fields': ('contrato_archivo', 'acta_inicio_archivo'),
            'classes': ('collapse',)
        }),
        ('Documentación - Fase Planeación', {
            'fields': ('cronograma_archivo', 'fecha_inicio', 'fecha_fin_estimada'),
            'classes': ('collapse',)
        }),
        ('Indicadores Financieros (Calculados)', {
            'fields': (
                'costo_mano_obra_real',
                'costo_materiales_real',
                'utilidad_estimada',
                'margen_rentabilidad'
            ),
            'description': 'Datos calculados y persistidos por el Service Layer',
            'classes': ('collapse',)
        }),
        ('Entregables Finales', {
            'fields': (
                'porcentaje_avance',
                'fecha_cierre_real',
                'acta_entrega_archivo',
                'informe_final_archivo'
            ),
            'classes': ('collapse',)
        }),
        ('Estado del Proyecto', {
            'fields': ('fase_actual', 'estado_tarea')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AsignacionPersonal)
class AsignacionPersonalAdmin(admin.ModelAdmin):
    """
    Admin para Asignación de Personal (Equipo de Trabajo)
    Modelo desacoplado: solo referencia (ID) y snapshot (nombre) del empleado
    """
    list_display = [
        'proyecto', 'nombre_colaborador', 'rol', 'empleado_id',
        'fecha_asignacion', 'horas_totales_registradas', 'costo_total_asignacion', 'activo'
    ]
    list_filter = ['rol', 'activo', 'empresa', 'fecha_asignacion']
    search_fields = ['proyecto__nombre', 'nombre_colaborador', 'empleado_id']
    readonly_fields = ['costo_total_asignacion']
    
    fieldsets = (
        ('SSoT', {
            'fields': ('empresa', 'proyecto')
        }),
        ('Asignación (Desacoplada)', {
            'fields': ('empleado_id', 'nombre_colaborador', 'rol'),
            'description': 'Referencia desacoplada: empleado_id (Integer) y nombre_colaborador (Snapshot)'
        }),
        ('Período', {
            'fields': ('fecha_asignacion', 'fecha_fin_asignacion')
        }),
        ('Datos Financieros', {
            'fields': (
                'horas_totales_registradas',
                'costo_hora',
                'costo_total_asignacion'
            ),
            'description': 'costo_total_asignacion es calculado por el Service Layer'
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )


class ItemPedidoInline(admin.TabularInline):
    """
    Inline para Items de Pedido
    Modelo desacoplado: material_ref (CharField) en lugar de ForeignKey
    """
    model = ItemPedido
    extra = 1
    fields = ['material_ref', 'nombre_material', 'cantidad', 'unidad_medida', 'precio_unitario']


@admin.register(PedidoProyecto)
class PedidoProyectoAdmin(admin.ModelAdmin):
    """
    Admin para Pedidos de Recursos del Proyecto (con Items inline)
    Modelo desacoplado: solo referencias (IDs y nombres) de Proveedores y Empleados
    """
    list_display = [
        'proyecto', 'tipo_recurso', 'fuente_suministro', 'estado', 
        'fecha_solicitud', 'proveedor_nombre', 'empleado_encargado_nombre'
    ]
    list_filter = ['tipo_recurso', 'fuente_suministro', 'estado', 'fecha_solicitud']
    search_fields = ['proyecto__nombre', 'proveedor_nombre', 'empleado_encargado_nombre', 'observaciones']
    readonly_fields = ['fecha_solicitud']
    inlines = [ItemPedidoInline]
    
    fieldsets = (
        ('SSoT', {
            'fields': ('empresa', 'proyecto')
        }),
        ('Solicitud', {
            'fields': ('solicitante', 'tipo_recurso', 'fuente_suministro', 'estado'),
            'description': 'solicitante es AUTH_USER_MODEL (Core Django), no app externa'
        }),
        ('Suministro (Desacoplado)', {
            'fields': (
                ('proveedor_id', 'proveedor_nombre'),
                'empleado_encargado_nombre'
            ),
            'description': 'Referencias desacopladas: IDs y nombres (sin ForeignKeys a Proveedores/Empleados)'
        }),
        ('Detalles', {
            'fields': ('observaciones', 'archivo_adjunto')
        }),
        ('Metadatos', {
            'fields': ('fecha_solicitud',),
            'classes': ('collapse',)
        }),
    )
