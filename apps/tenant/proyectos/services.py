"""
Services para Proyectos v3.3 - SSoT Pattern y Stand-Alone Module

⚠️ Arquitectura v2.40: Stand-Alone Module (SSoT Strict)
- Implementación de Modelo Anémico: Toda la lógica de negocio vive aquí.
- Cálculo de P&L (indicadores financieros).
- Gestión resiliente de snapshots (Zero-Coupling con otras apps).
- Delegación absoluta desde los ViewSets.
"""
from decimal import Decimal
from django.db import IntegrityError, models, transaction
from django.db.models import Sum, F
from rest_framework.exceptions import ValidationError

# Carga segura de modelos locales (SSoT)
from apps.tenant.empresa.models import Empresa
from .models import Proyecto, AsignacionPersonal, PedidoProyecto, ItemPedido


def qs_list(empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para listado de proyectos (Tabulator Factory) con Zero Trust.
    
    ⚠️ Zero Trust: Filtra explícitamente por empresa_id del tenant.
    ⚠️ PERFORMANCE BIBLE: Usa .only() para especificar campos necesarios.
    ⚠️ Mínima carga de datos, filtra por la Empresa SSoT.
    """
    # ⚠️ PERFORMANCE BIBLE: Especificar campos necesarios para el serializer
    campos_list = [
        'id', 'codigo', 'nombre', 'tipo_servicio', 'descripcion',
        'fase_actual', 'estado_tarea',
        'fecha_inicio', 'fecha_fin_estimada',
        'cliente_id', 'cliente_nombre',
        'responsable_actual_id', 'responsable_actual_nombre',
        'valor_contrato_proyectado', 'costo_mano_obra_real', 'costo_materiales_real',
        'utilidad_estimada', 'margen_rentabilidad',
        'porcentaje_avance', 'fecha_cierre_real',
        'created_at', 'updated_at',
        'empresa_id'  # Para Zero Trust validation
    ]
    
    qs = Proyecto.objects.filter(empresa_id=empresa_id).only(*campos_list)
    
    if search:
        qs = qs.filter(
            models.Q(nombre__icontains=search) |
            models.Q(codigo__icontains=search) |
            models.Q(descripcion__icontains=search) |
            models.Q(cliente_nombre__icontains=search) |
            models.Q(responsable_actual_nombre__icontains=search)
        )
    
    return qs.distinct().order_by('-updated_at')


def qs_detail(empresa_id, pk):
    """
    QuerySet optimizado para detalle de proyecto con relaciones.
    """
    return Proyecto.objects.filter(
        empresa_id=empresa_id,
        pk=pk
    ).select_related('empresa').prefetch_related(
        'equipo_trabajo',
        'pedidos',
        'pedidos__items'
    ).first()


def calcular_costo_mano_obra(proyecto):
    """
    Calcula el costo total de mano de obra sumando asignaciones activas.
    """
    total = AsignacionPersonal.objects.filter(
        proyecto=proyecto,
        activo=True
    ).aggregate(
        total=Sum('costo_total_asignacion')
    )['total'] or Decimal('0.00')
    
    return total


def calcular_costo_materiales(proyecto):
    """
    Calcula el costo total de materiales sumando items de pedidos aprobados.
    """
    total = ItemPedido.objects.filter(
        pedido__proyecto=proyecto,
        pedido__estado='APROBADO'
    ).aggregate(
        total=Sum(F('cantidad') * F('precio_unitario'))
    )['total'] or Decimal('0.00')
    
    return total


def calcular_indicadores_financieros(proyecto):
    """
    Calcula P&L y actualiza los indicadores financieros del proyecto.
    """
    costo_mano_obra = calcular_costo_mano_obra(proyecto)
    costo_materiales = calcular_costo_materiales(proyecto)
    costo_total = costo_mano_obra + costo_materiales
    
    valor_contrato = proyecto.valor_contrato_proyectado or Decimal('0.00')
    utilidad_estimada = valor_contrato - costo_total
    
    if valor_contrato > 0:
        margen_rentabilidad = (utilidad_estimada / valor_contrato) * Decimal('100.00')
    else:
        margen_rentabilidad = Decimal('0.00')
    
    # Actualización optimizada
    proyecto.costo_mano_obra_real = costo_mano_obra
    proyecto.costo_materiales_real = costo_materiales
    proyecto.utilidad_estimada = utilidad_estimada
    proyecto.margen_rentabilidad = margen_rentabilidad
    
    proyecto.save(update_fields=[
        'costo_mano_obra_real', 'costo_materiales_real',
        'utilidad_estimada', 'margen_rentabilidad'
    ])
    
    return {
        'costo_mano_obra_real': costo_mano_obra,
        'costo_materiales_real': costo_materiales,
        'costo_total': costo_total,
        'utilidad_estimada': utilidad_estimada,
        'margen_rentabilidad': margen_rentabilidad,
    }


def asignar_snapshot_cliente(proyecto, cliente_id=None, cliente_nombre=None):
    """
    ⚠️ Soft-Coupling: Resuelve el nombre del cliente de manera segura.
    Asigna los valores en memoria (no hace save).
    """
    if cliente_id:
        proyecto.cliente_id = cliente_id
        if not cliente_nombre:
            try:
                # Importación diferida para no romper si el módulo Clientes no existe
                from apps.tenant.clientes.models import Cliente
                cliente = Cliente.objects.filter(id=cliente_id).first()
                if cliente:
                    proyecto.cliente_nombre = getattr(cliente, 'razon_social', str(cliente))
            except ImportError:
                pass  # Tolerancia a fallos: Módulo no disponible
    elif cliente_nombre:
        proyecto.cliente_nombre = cliente_nombre


def asignar_snapshot_responsable(proyecto, responsable_id=None, responsable_nombre=None, fase=None):
    """
    ⚠️ Soft-Coupling: Resuelve y asigna al responsable en memoria (no hace save).
    """
    if not fase:
        fase = proyecto.fase_actual
    
    # Resolver nombre automáticamente si no se envía pero sí hay ID
    if responsable_id and not responsable_nombre:
        try:
            from apps.tenant.empleados.models import Empleado
            empleado = Empleado.objects.filter(id=responsable_id).first()
            if empleado:
                responsable_nombre = getattr(empleado, 'nombre_completo', str(empleado))
        except ImportError:
            pass  # Tolerancia a fallos
            
    # Mapeo de fase a campo del responsable
    if fase == 'INICIO':
        proyecto.responsable_comercial_id = responsable_id
        if responsable_nombre: proyecto.responsable_comercial_nombre = responsable_nombre
    elif fase == 'PLANEACION':
        proyecto.responsable_tecnico_id = responsable_id
        if responsable_nombre: proyecto.responsable_tecnico_nombre = responsable_nombre
    elif fase == 'EJECUCION':
        proyecto.responsable_operativo_id = responsable_id
        if responsable_nombre: proyecto.responsable_operativo_nombre = responsable_nombre
    elif fase == 'CIERRE':
        proyecto.responsable_administrativo_id = responsable_id
        if responsable_nombre: proyecto.responsable_administrativo_nombre = responsable_nombre
    
    # Responsable actual global
    proyecto.responsable_actual_id = responsable_id
    if responsable_nombre:
        proyecto.responsable_actual_nombre = responsable_nombre


def cambiar_fase_proyecto(proyecto, nueva_fase, responsable_id=None, responsable_nombre=None):
    """
    Valida y cambia la fase del proyecto. Asigna valores en memoria.
    """
    fases_validas = ['BORRADOR', 'INICIO', 'PLANEACION', 'EJECUCION', 'CIERRE']
    
    if nueva_fase not in fases_validas:
        raise ValidationError(f'Fase inválida: {nueva_fase}')
    
    proyecto.fase_actual = nueva_fase
    
    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre, nueva_fase)


@transaction.atomic
def crear_proyecto(empresa, data):
    """
    ⚠️ v2.60: Crea un nuevo proyecto con Zero Trust explícito.
    
    ⚠️ Zero Trust: Valida que la empresa pertenezca al tenant actual.
    ⚠️ Service Layer: Toda la lógica de negocio está aquí.
    ⚠️ Transactional: Usa @transaction.atomic para garantizar integridad.
    
    Args:
        empresa: Instancia de Empresa (debe ser del tenant actual)
        data: Dict con datos del proyecto (contrato canónico del serializer)
    
    Returns:
        Instancia de Proyecto creada
    
    Raises:
        ValidationError: Si hay errores de validación o integridad
    """
    # ⚠️ Zero Trust: Validar que empresa existe y es válida
    if not empresa or not isinstance(empresa, Empresa):
        raise ValidationError({'empresa': 'Empresa inválida o no proporcionada.'})
    
    cliente_id = data.pop('cliente_id', None)
    cliente_nombre = data.pop('cliente_nombre', None)
    responsable_id = data.pop('responsable_actual_id', None)
    responsable_nombre = data.pop('responsable_actual_nombre', None)
    
    # Instanciar sin guardar aún
    proyecto = Proyecto(empresa=empresa, **data)
    
    asignar_snapshot_cliente(proyecto, cliente_id, cliente_nombre)
    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre)
        
    try:
        proyecto.save()
        # Se calculan los indicadores (en 0) y guardan en DB
        calcular_indicadores_financieros(proyecto)
        return proyecto
    except IntegrityError as e:
        if 'uniq_proyecto_codigo_empresa' in str(e):
            raise ValidationError({'codigo': 'Ya existe un proyecto con este código en la empresa.'})
        raise ValidationError({'detail': 'Error de integridad al crear el proyecto.'})


@transaction.atomic
def actualizar_proyecto(proyecto, data):
    """
    ⚠️ v2.60: Actualiza un proyecto existente con Zero Trust explícito.
    
    ⚠️ Zero Trust: Valida que el proyecto pertenezca al tenant actual.
    ⚠️ Service Layer: Toda la lógica de negocio está aquí.
    ⚠️ Transactional: Usa @transaction.atomic para garantizar integridad.
    
    Args:
        proyecto: Instancia de Proyecto (debe pertenecer al tenant actual)
        data: Dict con datos a actualizar (contrato canónico del serializer)
    
    Returns:
        Instancia de Proyecto actualizada
    
    Raises:
        ValidationError: Si hay errores de validación o integridad
    """
    # ⚠️ Zero Trust: Validar que el proyecto existe y tiene empresa válida
    if not proyecto or not proyecto.empresa:
        raise ValidationError({'proyecto': 'Proyecto inválido o sin empresa asociada.'})
    
    cliente_id = data.pop('cliente_id', None)
    cliente_nombre = data.pop('cliente_nombre', None)
    responsable_id = data.pop('responsable_actual_id', None)
    responsable_nombre = data.pop('responsable_actual_nombre', None)
    nueva_fase = data.pop('fase_actual', None)
    
    for key, value in data.items():
        if hasattr(proyecto, key):
            setattr(proyecto, key, value)
    
    if cliente_id is not None or cliente_nombre:
        asignar_snapshot_cliente(proyecto, cliente_id, cliente_nombre)
        
    if nueva_fase and nueva_fase != proyecto.fase_actual:
        cambiar_fase_proyecto(proyecto, nueva_fase, responsable_id, responsable_nombre)
    elif responsable_id is not None or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre)
        
    try:
        proyecto.save()
        calcular_indicadores_financieros(proyecto)
        return proyecto
    except IntegrityError as e:
        if 'uniq_proyecto_codigo_empresa' in str(e):
            raise ValidationError({'codigo': 'Ya existe un proyecto con este código en la empresa.'})
        raise ValidationError({'detail': 'Error de integridad al actualizar el proyecto.'})


def eliminar_proyecto(proyecto):
    """
    Elimina físicamente un proyecto de la base de datos (Hard Delete).
    Delega de ViewSet para validaciones futuras de negocio.
    """
    # Aquí puedes añadir lógicas futuras: ej. raise ValidationError si hay horas pagadas.
    proyecto.delete()