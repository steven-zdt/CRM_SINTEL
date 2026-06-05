"""
Business Service para Proyectos v3.5 - Business Logic Layer

WARNING: SINTEL v3.5: Capa de Logica de Negocio y Orquestacion
- SSoT: unica fuente de verdad para reglas de negocio
- Zero Trust: Validacion semantica y de empresa_id
- Resiliencia: Gestion de snapshots desacoplada
"""
from datetime import date
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F, Sum
from rest_framework.exceptions import ValidationError

from apps.tenant.empresa.models import Empresa
from ..models import Proyecto, AsignacionPersonal, ItemPedido, TareaCorta
from .crud_service import save_proyecto, delete_proyecto, save_tarea_corta, delete_tarea_corta

try:
    from apps.tenant.clientes.models import Cliente as _Cliente
except ImportError:
    _Cliente = None

try:
    from apps.tenant.empleados.models import Empleado as _Empleado
except ImportError:
    _Empleado = None

try:
    from apps.tenant.facturas.models import Factura as _Factura
except ImportError:
    _Factura = None

try:
    from apps.tenant.proveedores.models import Proveedor as _Proveedor
except ImportError:
    _Proveedor = None

try:
    from apps.tenant.inventario.models import Servicio as _Servicio
except ImportError:
    _Servicio = None

try:
    from apps.tenant.perfil.models import TenantProfile as _TenantProfile
except ImportError:
    _TenantProfile = None

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
    
    # Actualizacion optimizada via crud_service
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
# GENERACIoN DE CoDIGO uNICO
# ==============================================================================

def generar_codigo_proyecto(empresa):
    """
    Genera un codigo unico y predecible. Formato: PRJ-{YYYY}-{seq:04d}.
    El secuenciador basa el siguiente numero en el maximo existente para
    esa empresa+anio, de forma que sea determinista. El UniqueConstraint
    del modelo actua como red de seguridad ante colisiones concurrentes.
    """
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
            if _Cliente is None:
                raise ImportError
            cliente = _Cliente.objects.filter(
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
    Resuelve y asigna al responsable en memoria segun la fase.
    """
    if not fase:
        fase = proyecto.fase_actual
    
    if responsable_id and not responsable_nombre:
        try:
            if _Empleado is None:
                raise ImportError
            empleado = _Empleado.objects.filter(
                id=responsable_id,
                empresa_id=proyecto.empresa_id
            ).only('id', 'primer_nombre', 'primer_apellido').first()
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
    Resuelve el numero de la factura de manera segura y lo asigna en memoria.
    """
    if not factura_id:
        if factura_numero:
            proyecto.factura_costo_numero = factura_numero
        return

    # SINTEL v3.5: Robustez Extrema (ID vs Instancia) - Evita TypeError si Django ya resolvio el FK
    try:
        if _Factura is None:
            raise ImportError
        # Si ya es una instancia (o tiene .id), lo tratamos como tal
        if hasattr(factura_id, 'id'):
            if getattr(factura_id, 'empresa_id', None) != proyecto.empresa_id:
                return
            proyecto.factura_costo = factura_id
            if not factura_numero:
                proyecto.factura_costo_numero = getattr(factura_id, 'numero', '')
        else:
            # Es un ID puro (int/str)
            proyecto.factura_costo_id = factura_id
            if not factura_numero:
                # Usar filter().only() para Zero Waste
                factura = _Factura.objects.filter(
                    id=factura_id,
                    empresa_id=proyecto.empresa_id
                ).only('id', 'numero', 'empresa_id').first()
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
            if _Proveedor is None:
                raise ImportError
            proveedor = _Proveedor.objects.filter(
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

def validar_servicio_asociado_dsv(proyecto, servicio_asociado):
    """
    Validacion DSV (Double Semantic Verification) para servicio_asociado.
    Garantiza que el servicio pertenezca exactamente a la empresa del proyecto.
    Lanza ValidationError si falla la validacion.
    """
    if not servicio_asociado:
        return  # None o no enviado es valido

    try:
        if _Servicio is None:
            raise ImportError

        # Si es instancia, verificar que la empresa coincida
        if hasattr(servicio_asociado, 'empresa_id'):
            if servicio_asociado.empresa_id != proyecto.empresa_id:
                raise ValidationError(
                    f'El servicio seleccionado no pertenece a la empresa actual. '
                    f'Servicio empresa_id: {servicio_asociado.empresa_id}, '
                    f'Proyecto empresa_id: {proyecto.empresa_id}.'
                )
        else:
            # Si es un ID/UUID, consultar la BD con DSV
            lookup = {'empresa_id': proyecto.empresa_id}
            servicio_str = str(servicio_asociado)
            if '-' in servicio_str:
                lookup['uuid'] = servicio_str
            else:
                lookup['id'] = servicio_asociado

            servicio = _Servicio.objects.filter(
                **lookup
            ).only('id', 'empresa_id').first()

            if not servicio:
                raise ValidationError(
                    f'El servicio con ID "{servicio_asociado}" no existe en esta empresa '
                    f'o pertenece a otro tenant.'
                )
    except ImportError:
        # Si inventario no esta disponible, no validar
        pass
    except ValidationError:
        raise  # Re-lanzar ValidationError
    except Exception as e:
        raise ValidationError(f'Error validando servicio_asociado: {str(e)}')

def cambiar_fase_proyecto(proyecto, nueva_fase, responsable_id=None, responsable_nombre=None):
    """
    Valida y cambia la fase del proyecto.
    """
    fases_validas = ['BORRADOR', 'INICIO', 'PLANEACION', 'EJECUCION', 'CIERRE']
    if nueva_fase not in fases_validas:
        raise ValidationError(f'Fase invalida: {nueva_fase}')
    
    proyecto.fase_actual = nueva_fase
    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre, nueva_fase)

# ==============================================================================
# ORQUESTACIoN CRUD (v3.5)
# ==============================================================================

@transaction.atomic
def orchestrate_create_proyecto(empresa, data):
    """
    Orquestador para la creacion de proyectos con logica de negocio.
    """
    if not empresa or not isinstance(empresa, Empresa):
        raise ValidationError({'empresa': 'Empresa invalida o no proporcionada.'})
    
    # WARNING: Generar o validar codigo unico
    codigo = data.get('codigo', None)
    
    # [SHIELD] Normalizar codigo: quitar espacios en blanco
    if codigo:
        codigo = str(codigo).strip()
    
    if not codigo:
        # Si no hay codigo, generar uno automaticamente
        data['codigo'] = generar_codigo_proyecto(empresa)
    else:
        # Validar que el codigo no exista ya
        if Proyecto.objects.filter(empresa=empresa, codigo=codigo).exists():
            raise ValidationError({'codigo': f'El codigo "{codigo}" ya esta registrado para otro proyecto.'})
        data['codigo'] = codigo
    
    cliente_id = data.pop('cliente_id', None)
    cliente_nombre = data.pop('cliente_nombre', None)
    responsable_id = data.pop('responsable_actual_id', None)
    responsable_nombre = data.pop('responsable_actual_nombre', None)
    factura_id = data.pop('factura_costo', None) or data.pop('factura_costo_id', None)
    factura_numero = data.pop('factura_costo_numero', None)
    proveedor_id = data.pop('proveedor_id', None)
    proveedor_nombre = data.pop('proveedor_nombre', None)
    servicio_asociado = data.pop('servicio_asociado', None)

    proyecto = Proyecto(empresa=empresa, **data)
    asignar_snapshot_cliente(proyecto, cliente_id, cliente_nombre)

    if responsable_id or responsable_nombre:
        asignar_snapshot_responsable(proyecto, responsable_id, responsable_nombre)

    if factura_id or factura_numero:
        asignar_snapshot_factura(proyecto, factura_id, factura_numero)

    if proveedor_id or proveedor_nombre:
        asignar_snapshot_proveedor(proyecto, proveedor_id, proveedor_nombre)

    if servicio_asociado:
        validar_servicio_asociado_dsv(proyecto, servicio_asociado)
        proyecto.servicio_asociado = servicio_asociado
        
    proyecto = save_proyecto(proyecto)
    calcular_indicadores_financieros(proyecto)
    return proyecto

@transaction.atomic
def orchestrate_update_proyecto(proyecto, data):
    """
    Orquestador para la actualizacion de proyectos con logica de negocio.
    """
    if not proyecto or not proyecto.empresa:
        raise ValidationError({'proyecto': 'Proyecto invalido o sin empresa asociada.'})
    
    # WARNING: Validar codigo unico si se esta actualizando
    codigo = data.get('codigo', None)
    if codigo is not None:
        codigo = str(codigo).strip()
        if codigo != proyecto.codigo and Proyecto.objects.filter(
            empresa=proyecto.empresa, codigo=codigo
        ).exclude(id=proyecto.id).exists():
            raise ValidationError({'codigo': f'El codigo "{codigo}" ya existe para otro proyecto.'})
        
        # [SHIELD] Asegurar que el codigo vacio se maneje segun la regla de negocio
        if not codigo and not proyecto.codigo:
             # Si no hay codigo previo y se envia vacio, generar uno
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
    servicio_asociado = data.pop('servicio_asociado', None)
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

    if servicio_asociado is not None:
        validar_servicio_asociado_dsv(proyecto, servicio_asociado)
        proyecto.servicio_asociado = servicio_asociado
        
    proyecto = save_proyecto(proyecto)
    calcular_indicadores_financieros(proyecto)
    return proyecto


# ==============================================================================
# TAREAS CORTAS BUSINESS SERVICE (v3.10.0)
# ==============================================================================

class TareasCortasBusinessService:
    """
    Logica de negocio para la gestion de Tareas Cortas v3.10.0.
    Responsable de:
    - Validacion de rango de fechas (coherencia interna).
    - DSV (Double Semantic Verification) para empresa, cliente y empleado.
    """

    @staticmethod
    def _validar_fechas(fecha_inicio, fecha_fin):
        """
        Valida que fecha_inicio <= fecha_fin.
        """
        if fecha_inicio > fecha_fin:
            raise ValidationError(
                f"La fecha de inicio ({fecha_inicio}) no puede ser posterior a la fecha de fin ({fecha_fin})."
            )

    @staticmethod
    def _validar_empresa_dsv(entidad, empresa, nombre='entidad'):
        """
        Valida que una entidad relacionada pertenezca a la misma empresa (DSV).
        """
        if entidad and entidad.empresa_id != empresa.id:
            raise ValidationError(
                f"El {nombre} seleccionado no pertenece a la empresa actual (DSV fallo)."
            )

    @staticmethod
    @transaction.atomic
    def crear_tarea_corta(empresa, empleado, fecha_inicio, fecha_fin, titulo, cliente=None, descripcion='', prioridad='NORMAL', notas_progreso=''):
        """
        Crea una nueva TareaCorta con logica de negocio.
        """
        if not cliente:
            raise ValidationError("La tarea corta requiere un cliente destino.")
        if not empleado:
            raise ValidationError("La tarea corta requiere un empleado asignado.")

        TareasCortasBusinessService._validar_empresa_dsv(cliente, empresa, 'cliente')
        TareasCortasBusinessService._validar_empresa_dsv(empleado, empresa, 'empleado')

        TareasCortasBusinessService._validar_fechas(fecha_inicio, fecha_fin)

        tarea = TareaCorta(
            empresa=empresa,
            cliente=cliente,
            empleado=empleado,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            titulo=titulo,
            descripcion=descripcion,
            prioridad=prioridad,
            notas_progreso=notas_progreso,
            estado='PENDIENTE'
        )

        save_tarea_corta(tarea)
        return tarea

    @staticmethod
    @transaction.atomic
    def actualizar_tarea_corta(tarea_corta, data):
        """
        Actualiza los campos editables de una TareaCorta.
        """
        permitidos = ['fecha_inicio', 'fecha_fin', 'titulo', 'descripcion', 'prioridad', 'notas_progreso', 'cliente', 'empleado']

        if 'cliente' in data:
            cliente = data['cliente']
            if not cliente:
                raise ValidationError("La tarea corta requiere un cliente destino.")
            TareasCortasBusinessService._validar_empresa_dsv(cliente, tarea_corta.empresa, 'cliente')
            tarea_corta.cliente = cliente

        if 'empleado' in data:
            empleado = data['empleado']
            if not empleado:
                raise ValidationError("La tarea corta requiere un empleado asignado.")
            TareasCortasBusinessService._validar_empresa_dsv(empleado, tarea_corta.empresa, 'empleado')
            tarea_corta.empleado = empleado

        for key in permitidos:
            if key in data and key not in ('cliente', 'empleado'):
                setattr(tarea_corta, key, data[key])

        if 'fecha_inicio' in data or 'fecha_fin' in data:
            TareasCortasBusinessService._validar_fechas(
                tarea_corta.fecha_inicio,
                tarea_corta.fecha_fin
            )

        save_tarea_corta(tarea_corta)
        return tarea_corta

    @staticmethod
    @transaction.atomic
    def cambiar_estado_tarea_corta(tarea_corta, nuevo_estado):
        """
        Cambia el estado de una TareaCorta.
        """
        if nuevo_estado not in dict(TareaCorta.Estado.choices):
            raise ValidationError(f"Estado invalido: {nuevo_estado}")

        tarea_corta.estado = nuevo_estado
        save_tarea_corta(tarea_corta)
        return tarea_corta

    @staticmethod
    @transaction.atomic
    def eliminar_tarea_corta(tarea_corta):
        """
        Elimina una TareaCorta.
        """
        delete_tarea_corta(tarea_corta)
        return True
