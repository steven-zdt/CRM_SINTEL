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
    Genera un codigo unico y predecible. Formato: PRJ-{YYYY}-{seq:04d}.
    El secuenciador basa el siguiente numero en el maximo existente para
    esa empresa+anio, de forma que sea determinista. El UniqueConstraint
    del modelo actua como red de seguridad ante colisiones concurrentes.
    """
    from datetime import date

    year = date.today().year
    prefix = f'PRJ-{year}-'

    codigos = Proyecto.objects.filter(
        empresa=empresa,
        codigo__startswith=prefix
    ).values_list('codigo', flat=True)

    numeros = []
    for c in codigos:
        sufijo = c[len(prefix):]
        if sufijo.isdigit():
            numeros.append(int(sufijo))

    seq = max(numeros) + 1 if numeros else 1
    return f'{prefix}{seq:04d}'


# ==============================================================================
# SNAPSHOTS Y DESACOPLAMIENTO (Zero-Coupling)
# ==============================================================================

def asignar_snapshot_cliente(proyecto, cliente_id=None, cliente_nombre=None):
    """
    Resuelve el nombre del cliente con DSV (empresa_id) y lo asigna en memoria.
    """
    if cliente_id:
        try:
            from apps.tenant.clientes.models import Cliente
            cliente = Cliente.objects.filter(
                id=cliente_id, empresa_id=proyecto.empresa_id
            ).only('razon_social').first()
            if not cliente:
                return
            proyecto.cliente_id = cliente_id
            proyecto.cliente_nombre = cliente_nombre or cliente.razon_social
        except ImportError:
            proyecto.cliente_id = cliente_id
            if cliente_nombre:
                proyecto.cliente_nombre = cliente_nombre
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

def asignar_snapshot_factura(proyecto, factura_id=None, factura_numero=None):
    """
    Resuelve el número de la factura de manera segura y lo asigna en memoria.
    """
    if not factura_id:
        if factura_numero:
            proyecto.factura_costo_numero = factura_numero
        return

    # SINTEL v3.5: Robustez Extrema (ID vs Instancia) - Evita TypeError si Django ya resolvió el FK
    try:
        from apps.tenant.facturas.models import Factura
        
        # Si ya es una instancia (o tiene .id), lo tratamos como tal
        if hasattr(factura_id, 'id'):
            proyecto.factura_costo = factura_id
            if not factura_numero:
                proyecto.factura_costo_numero = getattr(factura_id, 'numero', '')
        else:
            # Es un ID puro (int/str)
            proyecto.factura_costo_id = factura_id
            if not factura_numero:
                # Usar filter().only() para Zero Waste
                factura = Factura.objects.filter(id=factura_id).only('numero').first()
                if factura:
                    proyecto.factura_costo_numero = factura.numero
    except (ImportError, ValueError, TypeError, Exception):
        # Fallback silencioso si no se puede resolver la factura
        if factura_numero:
            proyecto.factura_costo_numero = factura_numero

def asignar_snapshot_proveedor(proyecto, proveedor_id=None, proveedor_nombre=None):
    """
    Resuelve el nombre del proveedor con DSV (empresa_id) y lo asigna en memoria.
    """
    if proveedor_id:
        try:
            from apps.tenant.proveedores.models import Proveedor
            proveedor = Proveedor.objects.filter(
                id=proveedor_id, empresa_id=proyecto.empresa_id
            ).only('razon_social').first()
            if not proveedor:
                return
            proyecto.proveedor_id = proveedor_id
            proyecto.proveedor_nombre = proveedor_nombre or proveedor.razon_social
        except ImportError:
            proyecto.proveedor_id = proveedor_id
            if proveedor_nombre:
                proyecto.proveedor_nombre = proveedor_nombre
    elif proveedor_nombre:
        proyecto.proveedor_nombre = proveedor_nombre

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
    
    # [SHIELD] Normalizar código: quitar espacios en blanco
    if codigo:
        codigo = str(codigo).strip()
    
    if not codigo:
        # Si no hay código, generar uno automáticamente
        data['codigo'] = generar_codigo_proyecto(empresa)
    else:
        # Validar que el código no exista ya
        if Proyecto.objects.filter(empresa=empresa, codigo=codigo).exists():
            raise ValidationError({'codigo': f'El código "{codigo}" ya está registrado para otro proyecto.'})
        data['codigo'] = codigo
    
    cliente_id = data.pop('cliente_id', None)
    cliente_nombre = data.pop('cliente_nombre', None)
    responsable_id = data.pop('responsable_actual_id', None)
    responsable_nombre = data.pop('responsable_actual_nombre', None)
    factura_id = data.pop('factura_costo', None) or data.pop('factura_costo_id', None)
    factura_numero = data.pop('factura_costo_numero', None)
    proveedor_id = data.pop('proveedor_id', None)
    proveedor_nombre = data.pop('proveedor_nombre', None)
    
    proyecto = Proyecto(empresa=empresa, **data)
    asignar_snapshot_cliente(proyecto, cliente_id, cliente_nombre)
    
    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre)

    if factura_id or factura_numero:
        asignar_snapshot_factura(proyecto, factura_id, factura_numero)

    if proveedor_id or proveedor_nombre:
        asignar_snapshot_proveedor(proyecto, proveedor_id, proveedor_nombre)
        
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
    if codigo is not None:
        codigo = str(codigo).strip()
        if codigo != proyecto.codigo and Proyecto.objects.filter(
            empresa=proyecto.empresa, codigo=codigo
        ).exclude(id=proyecto.id).exists():
            raise ValidationError({'codigo': f'El código "{codigo}" ya existe para otro proyecto.'})
        
        # [SHIELD] Asegurar que el código vacío se maneje según la regla de negocio
        if not codigo and not proyecto.codigo:
             # Si no hay código previo y se envía vacío, generar uno
             data['codigo'] = generar_codigo_proyecto(proyecto.empresa)
        else:
             data['codigo'] = codigo
    
    cliente_id = data.pop('cliente_id', None)
    cliente_nombre = data.pop('cliente_nombre', None)
    responsable_id = data.pop('responsable_actual_id', None)
    responsable_nombre = data.pop('responsable_actual_nombre', None)
    factura_id = data.pop('factura_costo', None) or data.pop('factura_costo_id', None)
    factura_numero = data.pop('factura_costo_numero', None)
    proveedor_id = data.pop('proveedor_id', None)
    proveedor_nombre = data.pop('proveedor_nombre', None)
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
        
    if factura_id is not None or factura_numero:
        asignar_snapshot_factura(proyecto, factura_id, factura_numero)
        
    if proveedor_id is not None or proveedor_nombre:
        asignar_snapshot_proveedor(proyecto, proveedor_id, proveedor_nombre)
        
    proyecto = save_proyecto(proyecto)
    calcular_indicadores_financieros(proyecto)
    return proyecto
