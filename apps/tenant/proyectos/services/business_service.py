"""
Business Service para Proyectos v3.5 - Business Logic Layer

WARNING: SINTEL v3.5: Capa de Lógica de Negocio y Orquestación
- SSoT: Única fuente de verdad para reglas de negocio
- Zero Trust: Validación semántica y de empresa_id
- Resiliencia: Gestión de snapshots desacoplada
"""
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F, Sum
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from ..models import Proyecto, AsignacionPersonal, ItemPedido
from .crud_service import save_proyecto, delete_proyecto

# ==============================================================================
# INDICADORES FINANCIEROS (P&L)
# ==============================================================================

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
    
    # Actualización optimizada vía crud_service
    proyecto.costo_mano_obra_real = costo_mano_obra
    proyecto.costo_materiales_real = costo_materiales
    proyecto.utilidad_estimada = utilidad_estimada
    proyecto.margen_rentabilidad = margen_rentabilidad
    
    save_proyecto(proyecto, update_fields=[
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

# ==============================================================================
# GENERACIÓN DE CÓDIGO ÚNICO
# ==============================================================================

def generar_codigo_proyecto(empresa):
    """
    Genera un código único de proyecto para la empresa.
    Formato: PRJ-{timestamp}-{random_4digitos}-{secuencia}
    """
    import time
    import random
    
    # Generar base del código con timestamp y random de 4 dígitos
    timestamp = int(time.time())
    random_suffix = random.randint(1000, 9999)
    attempt = 0
    max_attempts = 10
    
    # Verificar unicidad y regenerar si existe
    from ..models import Proyecto
    while attempt < max_attempts:
        codigo = f"PRJ-{timestamp}-{random_suffix}"
        if not Proyecto.objects.filter(empresa=empresa, codigo=codigo).exists():
            return codigo
        # Si existe, generar nuevo random y actualizar timestamp
        random_suffix = random.randint(1000, 9999)
        timestamp = int(time.time())
        attempt += 1
    
    # Si no encontramos código único en 10 intentos, usar timestamp + microsegundos
    import datetime
    now = datetime.datetime.now()
    codigo = f"PRJ-{now.strftime('%Y%m%d%H%M%S%f')}"
    return codigo


# ==============================================================================
# SNAPSHOTS Y DESACOPLAMIENTO (Zero-Coupling)
# ==============================================================================

def asignar_snapshot_cliente(proyecto, cliente_id=None, cliente_nombre=None):
    """
    Resuelve el nombre del cliente de manera segura y lo asigna en memoria.
    """
    if cliente_id:
        proyecto.cliente_id = cliente_id
        if not cliente_nombre:
            try:
                from apps.tenant.clientes.models import Cliente
                cliente = Cliente.objects.filter(id=cliente_id).first()
                if cliente:
                    proyecto.cliente_nombre = getattr(cliente, 'razon_social', str(cliente))
            except ImportError:
                pass
    elif cliente_nombre:
        proyecto.cliente_nombre = cliente_nombre

def asignar_snapshot_responsable(proyecto, responsable_id=None, responsable_nombre=None, fase=None):
    """
    Resuelve y asigna al responsable en memoria según la fase.
    """
    if not fase:
        fase = proyecto.fase_actual
    
    if responsable_id and not responsable_nombre:
        try:
            from apps.tenant.empleados.models import Empleado
            empleado = Empleado.objects.filter(id=responsable_id).first()
            if empleado:
                responsable_nombre = getattr(empleado, 'nombre_completo', str(empleado))
        except ImportError:
            pass
            
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
    Valida y cambia la fase del proyecto.
    """
    fases_validas = ['BORRADOR', 'INICIO', 'PLANEACION', 'EJECUCION', 'CIERRE']
    if nueva_fase not in fases_validas:
        raise ValidationError(f'Fase inválida: {nueva_fase}')
    
    proyecto.fase_actual = nueva_fase
    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre, nueva_fase)

# ==============================================================================
# ORQUESTACIÓN CRUD (v3.5)
# ==============================================================================

@transaction.atomic
def orchestrate_create_proyecto(empresa, data):
    """
    Orquestador para la creación de proyectos con lógica de negocio.
    """
    if not empresa or not isinstance(empresa, Empresa):
        raise ValidationError({'empresa': 'Empresa inválida o no proporcionada.'})
    
    # ⚠️ Generar o validar código único
    codigo = data.get('codigo', None)
    # Limpiar código vacío o solo espacios
    if codigo:
        codigo = str(codigo).strip()
    if not codigo:
        data['codigo'] = generar_codigo_proyecto(empresa)
    else:
        # Validar que el código no exista ya - si existe, generar uno nuevo automáticamente
        from ..models import Proyecto
        if Proyecto.objects.filter(empresa=empresa, codigo=codigo).exists():
            # ⚠️ Auto-generar código en lugar de fallar (mejor UX)
            data['codigo'] = generar_codigo_proyecto(empresa)
        else:
            data['codigo'] = codigo
    
    cliente_id = data.pop('cliente_id', None)
    cliente_nombre = data.pop('cliente_nombre', None)
    responsable_id = data.pop('responsable_actual_id', None)
    responsable_nombre = data.pop('responsable_actual_nombre', None)
    
    proyecto = Proyecto(empresa=empresa, **data)
    asignar_snapshot_cliente(proyecto, cliente_id, cliente_nombre)
    
    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre)
        
    proyecto = save_proyecto(proyecto)
    calcular_indicadores_financieros(proyecto)
    return proyecto

@transaction.atomic
def orchestrate_update_proyecto(proyecto, data):
    """
    Orquestador para la actualización de proyectos con lógica de negocio.
    """
    if not proyecto or not proyecto.empresa:
        raise ValidationError({'proyecto': 'Proyecto inválido o sin empresa asociada.'})
    
    # ⚠️ Validar código único si se está actualizando
    codigo = data.get('codigo', None)
    if codigo:
        codigo = str(codigo).strip()
        from ..models import Proyecto
        # Solo validar si el código cambió y ya existe en OTRO proyecto
        if codigo != proyecto.codigo and Proyecto.objects.filter(
            empresa=proyecto.empresa, codigo=codigo
        ).exclude(id=proyecto.id).exists():
            raise ValidationError({'codigo': f'El código "{codigo}" ya existe para otro proyecto.'})
        data['codigo'] = codigo
    
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
        
    proyecto = save_proyecto(proyecto)
    calcular_indicadores_financieros(proyecto)
    return proyecto
