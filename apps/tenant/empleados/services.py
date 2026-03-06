"""
Servicios de dominio para Empleados v2.60.

⚠️ SINTEL v2.60: Sincronización Arquitectónica
- Aislamiento SSoT: Todos los modelos tienen empresa = ForeignKey(Empresa, on_delete=PROTECT) e índice obligatorio
- Campos Explícitos: LIST_FIELDS y DETAIL_FIELDS como tuplas (PROHIBIDO __all__)
- QuerySets Optimizados: qs_list() y qs_detail() usando .only(*FIELDS) y select_related()
- Lógica en Cálculos: Los cálculos económicos se realizan en el backend (Zero Trust)

PRINCIPIOS:
- Lógica de Negocio: Cálculos de nómina, validaciones y gestión de contratos.
- Transaccionalidad: Uso de transaction.atomic para integridad.
- Optimización: QuerySets pre-optimizados (qs_*) para ViewSets.
- Zero Trust: Validación estricta de pertenencia al tenant.
"""

from django.db.models import Sum, Count, Q, Exists, OuterRef, BooleanField
from django.utils import timezone
from decimal import Decimal
from django.apps import apps
from django.db import transaction
from rest_framework.exceptions import ValidationError
import logging
from .models import Empleado, Devengo, Contrato

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. QUERYSETS OPTIMIZADOS (Service Layer Pattern) - v2.60
# ⚠️ SINTEL v2.60: Campos explícitos como tuplas (PROHIBIDO __all__)
# Usados por los ViewSets para evitar N+1 queries y cargar solo lo necesario.
# ==============================================================================

# ⚠️ v2.60: Constantes de campos para LISTAS (SSoT: Single Source of Truth)
# Campos estrictamente necesarios para tablas Tabulator (mínima exposición de datos)
EMPLEADO_LIST_FIELDS = (
    'id', 'tipo_documento', 'numero_documento', 'primer_nombre', 'primer_apellido',
    'segundo_nombre', 'segundo_apellido', 'estado', 'fecha_ingreso', 'empresa_id'
)

CONTRATO_LIST_FIELDS = (
    'id', 'empleado', 'empleado__id', 'empleado__primer_nombre', 'empleado__primer_apellido',
    'tipo', 'fecha_inicio', 'fecha_fin', 'salario_mensual', 'auxilio_transporte',
    'cargo', 'estado', 'activo', 'empresa_id'
)

DEVENGO_LIST_FIELDS = (
    'id', 'empleado', 'empleado__id', 'empleado__primer_nombre', 'empleado__primer_apellido',
    'contrato', 'contrato__id', 'periodo_mes', 'fecha_pago', 'dias_laborados',
    'salario_base', 'auxilio_transporte', 'otros_devengos',
    'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
    'neto_pagar', 'anulado', 'empresa_id'
)

# ⚠️ v2.60: Constantes de campos para DETALLE (campos completos para edición)
# Incluye todos los campos necesarios para formularios de edición
EMPLEADO_DETAIL_FIELDS = (
    'id', 'empresa', 'empresa__id', 'tipo_documento', 'numero_documento',
    'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
    'email', 'telefono', 'eps', 'afp', 'arl', 'nivel_riesgo_arl',
    'estado', 'fecha_ingreso', 'fecha_retiro'
)

CONTRATO_DETAIL_FIELDS = (
    'id', 'empresa', 'empresa__id', 'empleado', 'empleado__id',
    'empleado__primer_nombre', 'empleado__primer_apellido',
    'tipo', 'fecha_inicio', 'fecha_fin', 'salario_mensual', 'auxilio_transporte',
    'prestamos_empresa', 'cargo', 'archivo_pdf', 'estado', 'activo'
)

DEVENGO_DETAIL_FIELDS = (
    'id', 'empresa', 'empresa__id', 'empleado', 'empleado__id',
    'empleado__primer_nombre', 'empleado__primer_apellido',
    'contrato', 'contrato__id', 'periodo_mes', 'fecha_pago', 'dias_laborados',
    'salario_base', 'auxilio_transporte', 'otros_devengos',
    'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
    'observaciones', 'neto_pagar', 'anulado'
)

def qs_empleado_list(empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Empleados (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    Anota estados secuenciales (Contrato y Nómina) para lógica de botones en Tabulator.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en documento, nombres, apellidos)
    
    Returns:
        QuerySet: Optimizado con .only(*EMPLEADO_LIST_FIELDS) y anotaciones
    """
    # Subqueries para verificar existencia de registros vinculados (Zero Waste)
    has_contract = Contrato.objects.filter(
        empleado_id=OuterRef('pk'),
        activo=True,
        estado='ACTIVO',
        empresa_id=empresa_id  # ⚠️ v2.60: Zero Trust
    )
    
    has_payroll = Devengo.objects.filter(
        empleado_id=OuterRef('pk'),
        anulado=False,
        empresa_id=empresa_id  # ⚠️ v2.60: Zero Trust
    )

    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: .only(*EMPLEADO_LIST_FIELDS) para cargar solo campos necesarios
    # Anotación de campos booleanos para control de UI en la columna de acciones
    qs = Empleado.objects.filter(empresa_id=empresa_id).annotate(
        tiene_contrato_activo=Exists(has_contract),
        tiene_nominas_registradas=Exists(has_payroll)
    ).only(*EMPLEADO_LIST_FIELDS)
    
    # Aplicar filtro de búsqueda si se proporciona
    if search:
        qs = qs.filter(
            Q(numero_documento__icontains=search) |
            Q(primer_nombre__icontains=search) |
            Q(primer_apellido__icontains=search) |
            Q(segundo_nombre__icontains=search) |
            Q(segundo_apellido__icontains=search)
        )
    
    # ⚠️ v2.40: Ordenamiento explícito para evitar UnorderedObjectListWarning
    return qs.order_by('-fecha_ingreso', 'id')


def qs_empleado_detail(empresa_id, empleado_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Empleado (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        empleado_id: ID del empleado
    
    Returns:
        Empleado: Instancia con todos los campos necesarios para edición
    
    Raises:
        Empleado.DoesNotExist: Si el empleado no existe o no pertenece al tenant
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('empresa') para evitar N+1 queries
    # ⚠️ Performance: .only(*EMPLEADO_DETAIL_FIELDS) para cargar solo campos necesarios
    return Empleado.objects.filter(empresa_id=empresa_id, pk=empleado_id)\
        .select_related('empresa')\
        .only(*EMPLEADO_DETAIL_FIELDS)\
        .get()


def qs_contrato_list(empresa_id, search=None, empleado_id=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Contratos (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en cargo, empleado)
        empleado_id: ID del empleado para filtrar contratos específicos (opcional)
    
    Returns:
        QuerySet: Optimizado con .only(*CONTRATO_LIST_FIELDS) y select_related('empleado')
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('empleado') para evitar N+1 queries
    # ⚠️ Performance: .only(*CONTRATO_LIST_FIELDS) para cargar solo campos necesarios
    qs = Contrato.objects.filter(empresa_id=empresa_id)\
        .select_related('empleado')\
        .only(*CONTRATO_LIST_FIELDS)
    
    if empleado_id:
        qs = qs.filter(empleado_id=empleado_id)
    
    if search:
        qs = qs.filter(
            Q(cargo__icontains=search) |
            Q(empleado__primer_nombre__icontains=search) |
            Q(empleado__primer_apellido__icontains=search)
        )
    
    return qs.order_by('-fecha_inicio', 'id')


def qs_contrato_detail(empresa_id, contrato_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Contrato (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        contrato_id: ID del contrato
    
    Returns:
        Contrato: Instancia con todos los campos necesarios para edición
    
    Raises:
        Contrato.DoesNotExist: Si el contrato no existe o no pertenece al tenant
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('empresa', 'empleado') para evitar N+1 queries
    # ⚠️ Performance: .only(*CONTRATO_DETAIL_FIELDS) para cargar solo campos necesarios
    return Contrato.objects.filter(empresa_id=empresa_id, pk=contrato_id)\
        .select_related('empresa', 'empleado')\
        .only(*CONTRATO_DETAIL_FIELDS)\
        .get()


def qs_devengo_list(empresa_id, search=None, empleado_id=None, periodo_mes=None):
    """
    ⚠️ v2.60: QuerySet optimizado para LISTAR Devengos/Nóminas (tabla Tabulator).
    Campos estrictamente necesarios para listado (mínima exposición de datos).
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en periodo, empleado)
        empleado_id: ID del empleado para filtrar nóminas específicas (opcional)
        periodo_mes: Periodo en formato YYYY-MM para filtrar (opcional)
    
    Returns:
        QuerySet: Optimizado con .only(*DEVENGO_LIST_FIELDS) y select_related('empleado', 'contrato')
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('empleado', 'contrato') para evitar N+1 queries
    # ⚠️ Performance: .only(*DEVENGO_LIST_FIELDS) para cargar solo campos necesarios
    qs = Devengo.objects.filter(empresa_id=empresa_id)\
        .select_related('empleado', 'contrato')\
        .only(*DEVENGO_LIST_FIELDS)
    
    if empleado_id:
        qs = qs.filter(empleado_id=empleado_id)
    
    if periodo_mes:
        qs = qs.filter(periodo_mes=periodo_mes)
    
    if search:
        qs = qs.filter(
            Q(periodo_mes__icontains=search) |
            Q(empleado__primer_nombre__icontains=search) |
            Q(empleado__primer_apellido__icontains=search)
        )
    
    return qs.order_by('-fecha_pago', '-periodo_mes', 'id')


def qs_historial_list(empleado_id, empresa_id, search=None):
    """
    ⚠️ v2.60: QuerySet optimizado para HISTORIAL de Nóminas de un empleado específico.
    Campos estrictamente necesarios para listado en el historial (mínima exposición de datos).
    
    Args:
        empleado_id: ID del empleado (requerido - Zero Trust)
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        search: Término de búsqueda opcional (busca en periodo)
    
    Returns:
        QuerySet: Optimizado con .only(*DEVENGO_LIST_FIELDS) y select_related('empleado', 'contrato')
        Ordenado por fecha de pago descendente (más reciente primero)
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id y empleado_id (SSoT)
    # ⚠️ Performance: select_related('empleado', 'contrato') para evitar N+1 queries
    # ⚠️ Performance: .only(*DEVENGO_LIST_FIELDS) para cargar solo campos necesarios
    qs = Devengo.objects.filter(
        empresa_id=empresa_id,
        empleado_id=empleado_id
    ).select_related('empleado', 'contrato').only(*DEVENGO_LIST_FIELDS)
    
    if search:
        qs = qs.filter(
            Q(periodo_mes__icontains=search) |
            Q(fecha_pago__icontains=search)
        )
    
    # Ordenar por fecha de pago descendente (más reciente primero)
    return qs.order_by('-fecha_pago', '-periodo_mes', 'id')


def qs_devengo_detail(empresa_id, devengo_id):
    """
    ⚠️ v2.60: QuerySet optimizado para DETALLE de Devengo/Nómina (formulario de edición).
    Campos completos necesarios para edición.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        devengo_id: ID del devengo
    
    Returns:
        Devengo: Instancia con todos los campos necesarios para edición
    
    Raises:
        Devengo.DoesNotExist: Si el devengo no existe o no pertenece al tenant
    """
    # ⚠️ Zero Trust: Filtrar por empresa_id (SSoT)
    # ⚠️ Performance: select_related('empresa', 'empleado', 'contrato') para evitar N+1 queries
    # ⚠️ Performance: .only(*DEVENGO_DETAIL_FIELDS) para cargar solo campos necesarios
    return Devengo.objects.filter(empresa_id=empresa_id, pk=devengo_id)\
        .select_related('empresa', 'empleado', 'contrato')\
        .only(*DEVENGO_DETAIL_FIELDS)\
        .get()

def get_nomina_summary(empresa_id):
    """
    ⚠️ v2.60: Calcula analítica para el panel superior.
    Usa empresa_id para Zero Trust.
    
    Args:
        empresa_id: ID de la empresa (SSoT - Zero Trust)
    
    Returns:
        dict: Resumen de nómina del mes actual
    """
    hoy = timezone.now().date()
    mes_actual = hoy.strftime("%Y-%m")
    
    # ⚠️ v2.60: Zero Trust - Filtrar por empresa_id directamente
    # Excluir devengos anulados para mantener integridad contable
    qs_mes = Devengo.objects.filter(
        empresa_id=empresa_id,  # ⚠️ v2.60: Zero Trust
        periodo_mes=mes_actual,
        anulado=False
    )
    
    totales = qs_mes.aggregate(
        total_neto=Sum('neto_pagar') or Decimal('0.00'),
        count_pagos=Count('id')
    )
    
    activos = Empleado.objects.filter(empresa_id=empresa_id, estado='ACTIVO').count()
    
    return {
        "total_nomina_mes": str(totales['total_neto']),
        "empleados_pagados": totales['count_pagos'],
        "empleados_activos": activos
    }

@transaction.atomic
def gestionar_contrato_service(empleado, data, contrato_existente=None):
    """
    Fase 2: Crea o actualiza el contrato de un empleado.
    Al activarse, habilitará el botón 'Registrar Nómina' en Tabulator.
    
    ⚠️ v2.60: El modelo Contrato tiene campo empresa (SSoT).
    La empresa se sincroniza desde empleado.empresa en el método save() del modelo.
    
    Args:
        empleado: Instancia de Empleado
        data: Diccionario con los datos del contrato
        contrato_existente: Instancia de Contrato existente (opcional, para actualizaciones)
    
    Returns:
        Contrato: Instancia creada o actualizada
    """
    # ⚠️ v2.60: SSoT - Asignar empresa desde empleado si no viene en data
    if 'empresa' not in data:
        data['empresa'] = empleado.empresa
    
    # ⚠️ Sincronizar el campo legacy 'activo' con el nuevo 'estado'
    if 'estado' in data:
        data['activo'] = (data['estado'] == 'ACTIVO')
    
    # Determinar cuál será el estado final del contrato
    estado_final = data.get('estado', contrato_existente.estado if contrato_existente else 'ACTIVO')
    
    # SSoT: Desactivar contratos previos para garantizar un único contrato activo
    # Solo lo hacemos si el contrato que estamos procesando va a quedar ACTIVO
    if estado_final == 'ACTIVO':
        qs_previos = Contrato.objects.filter(
            empleado=empleado, 
            estado='ACTIVO',
            empresa_id=empleado.empresa_id  # ⚠️ v2.60: Zero Trust
        )
        
        # Si es una actualización, excluimos el contrato actual de la desactivación masiva
        if contrato_existente:
            qs_previos = qs_previos.exclude(pk=contrato_existente.pk)
            
        qs_previos.update(
            activo=False, 
            estado='INACTIVO'
        )
    
    # Flujo de Actualización
    if contrato_existente:
        for key, value in data.items():
            setattr(contrato_existente, key, value)
        contrato_existente.save()
        return contrato_existente
        
    # Flujo de Creación
    else:
        if 'estado' not in data:
            data['estado'] = 'ACTIVO'
        if 'activo' not in data:
            data['activo'] = True
            
        return Contrato.objects.create(
            empleado=empleado,
            **data
        )

@transaction.atomic
def registrar_devengo_nomina_service(empleado, data):
    """
    Fase 3: Registra un pago de nómina.
    Requiere validación de contrato previo para habilitar el historial.
    
    ⚠️ v2.60: El modelo Devengo tiene campo empresa (SSoT).
    La empresa se sincroniza desde empleado.empresa en el método save() del modelo.
    """
    # ⚠️ v2.60: SSoT - Asignar empresa desde empleado si no viene en data
    if 'empresa' not in data:
        data['empresa'] = empleado.empresa
    
    # Validación de seguridad: No pagar sin contrato activo
    if not empleado.contratos.filter(
        activo=True, 
        estado='ACTIVO',
        empresa_id=empleado.empresa_id  # ⚠️ v2.60: Zero Trust
    ).exists():
        raise ValidationError("No se puede registrar nómina: El empleado no tiene un contrato activo.")
    
    return Devengo.objects.create(
        empleado=empleado,
        **data,
        anulado=False
    )

def anular_devengo_service(devengo_id, empresa_id):
    """
    ⚠️ v2.60: Lógica de inmutabilidad: Marca un desprendible como anulado.
    Usa empresa_id para Zero Trust.
    
    Args:
        devengo_id: ID del devengo a anular
        empresa_id: ID de la empresa (SSoT - Zero Trust)
    
    Returns:
        Devengo: Instancia anulada
    
    Raises:
        Devengo.DoesNotExist: Si el devengo no existe o no pertenece al tenant
        ValueError: Si el devengo ya está anulado
    """
    with transaction.atomic():
        devengo = Devengo.objects.select_for_update().get(
            id=devengo_id, 
            empresa_id=empresa_id  # ⚠️ v2.60: Zero Trust
        )
        
        if devengo.anulado:
            raise ValueError("El desprendible ya está anulado.")
        
        devengo.anulado = True
        devengo.save(update_fields=['anulado'])
        
        return devengo

def validar_limite_dias_mes(empleado_id, periodo_mes, nuevos_dias, empresa_id, devengo_id_excluir=None):
    """
    ⚠️ v2.60: Zero Trust - Valida que la suma de todos los pagos del mes no exceda 31 días.
    
    Args:
        empleado_id: ID del empleado
        periodo_mes: Periodo en formato YYYY-MM
        nuevos_dias: Días laborados del nuevo registro (Decimal)
        empresa_id: ID de la empresa (SSoT - Zero Trust)
        devengo_id_excluir: ID del devengo a excluir de la suma (para actualizaciones)
    
    Returns:
        dict: {
            'total_dias': Decimal,  # Total de días ya registrados
            'nuevos_dias': Decimal,  # Días del nuevo registro
            'total_final': Decimal,  # Suma total
            'excede_limite': bool   # True si excede 31 días
        }
    
    Raises:
        ValidationError: Si el total excede 31 días
    """
    from decimal import Decimal
    
    try:
        nuevos_dias = Decimal(str(nuevos_dias))
    except (ValueError, TypeError):
        raise ValidationError("Los días laborados deben ser un número válido")
    
    # Sumar días laborados de todas las nóminas del mes (no anuladas, excluyendo la actual si es update)
    qs = Devengo.objects.filter(
        empleado_id=empleado_id,
        periodo_mes=periodo_mes,
        anulado=False,
        empresa_id=empresa_id
    )
    
    if devengo_id_excluir:
        qs = qs.exclude(pk=devengo_id_excluir)
    
    total_dias = qs.aggregate(total=Sum('dias_laborados'))['total'] or Decimal('0')
    total_final = total_dias + nuevos_dias
    
    if total_final > Decimal('31'):
        raise ValidationError(
            f"El total de días pagados en {periodo_mes} excedería el límite legal (31 días). "
            f"Ya se han registrado {total_dias} días. Con {nuevos_dias} días adicionales, "
            f"el total sería {total_final} días."
        )
    
    return {
        'total_dias': total_dias,
        'nuevos_dias': nuevos_dias,
        'total_final': total_final,
        'excede_limite': False
    }

def eliminar_empleado_retirado(empleado):
    """
    ⚠️ v2.40: Eliminación en cascada de empleado RETIRADO y todas sus dependencias.
    Elimina físicamente nóminas y contratos para liberar FK protegidas.
    """
    # ⚠️ v2.40: Validación estricta - Solo permitir eliminación si está RETIRADO
    if empleado.estado != 'RETIRADO':
        raise ValidationError(
            f'Solo se pueden eliminar empleados con estado RETIRADO. Estado actual: {empleado.estado}'
        )
    
    with transaction.atomic():
        contratos_count = empleado.contratos.count()
        devengos_count = empleado.nominas.count()
        
        # Eliminar todas las nóminas (Devengo) asociadas
        if devengos_count > 0:
            empleado.nominas.all().delete()
        
        # Eliminar todos los contratos asociados
        if contratos_count > 0:
            empleado.contratos.all().delete()
        
        # Finalmente, eliminar el empleado
        empleado.delete()
        
        return {
            'contratos_eliminados': contratos_count,
            'devengos_eliminados': devengos_count,
            'empleado_eliminado': True
        }

def cancelar_contratos_activos_al_retirar(empleado):
    """
    ⚠️ v2.40: Cancela contratos activos cuando un empleado pasa a estado RETIRADO.
    """
    with transaction.atomic():
        contratos_activos = empleado.contratos.filter(estado='ACTIVO')
        count = contratos_activos.count()
        
        if count > 0:
            hoy = timezone.now().date()
            contratos_activos.update(
                estado='INACTIVO',
                activo=False,
                fecha_fin=hoy
            )
        
        return count

def calcular_nomina_colombia(contrato, dias_laborados, horas_trabajadas=None, otros_devengos=0, prestamos=0, descuentos_operativos=0, empresa_id=None):
    """
    ⚠️ v2.60: Función única fuente de verdad para cálculo de nómina colombiana.
    Cumple con normativa laboral colombiana (Ley 2101 de 2021 - 46 horas semanales).
    Base de cálculo: 30 días mensuales.
    
    Args:
        contrato: Instancia de Contrato (debe estar ACTIVO)
        dias_laborados: Días trabajados (0.5-30, permite decimales)
        horas_trabajadas: Horas trabajadas (opcional, para cálculo por horas)
        otros_devengos: Otros devengos adicionales en COP (default: 0)
        prestamos: Préstamos descontados en COP (default: 0)
        descuentos_operativos: Descuentos operativos en COP (default: 0)
        empresa_id: ID de la empresa para validación Zero Trust (opcional pero recomendado)
    
    Returns:
        dict: Diccionario con todos los valores calculados en COP
        
    Reglas de Cálculo (Normativa Colombiana):
    1. Jornada Laboral: 46 horas semanales (Ley 2101 de 2021)
       - Horas mensuales: 46 * 4.33 = 199.18 horas/mes (redondeado a 200 horas)
       - Valor hora = Salario Mensual / 200
    
    2. Salario Proporcional:
       - Por días: (Salario Base / 30) * dias_laborados
       - Por horas: Valor hora * horas_trabajadas (si se proporciona)
    
    3. Auxilio de Transporte:
       - Valor legal vigente (obtener de configuración o contrato)
       - Proporcional: (Auxilio / 30) * dias_laborados
       - Solo aplica si NO es Prestación de Servicios
    
    4. IBC (Ingreso Base de Cotización):
       - IBC = Salario Proporcional (NO incluye auxilio de transporte)
       - Base para calcular Salud (4%) y Pensión (4%)
    
    5. Deducciones de Ley:
       - Salud: 4% sobre IBC
       - Pensión: 4% sobre IBC
       - Solo aplica si es contrato laboral (FIJO, INDEF, OBRA)
       - NO aplica para PRESTACION
    
    6. Neto a Pagar:
       - Neto = (Salario + Auxilio + Otros Devengos) - (Salud + Pensión + Préstamos + Descuentos)
    
    Raises:
        ValueError: Si el contrato no está ACTIVO o los días/horas son inválidos
        ValidationError: Si el contrato no pertenece a la empresa especificada (Zero Trust)
    """
    return calcular_liquidacion_nomina(contrato, dias_laborados, horas_trabajadas, otros_devengos, prestamos, descuentos_operativos, empresa_id)


def calcular_liquidacion_nomina(contrato, dias_laborados, horas_trabajadas=None, otros_devengos=0, prestamos=0, descuentos_operativos=0, empresa_id=None):
    """
    ⚠️ v2.60: Función única fuente de verdad para cálculo de liquidación de nómina.
    Cumple con normativa laboral colombiana (Ley 2101 de 2021 - 46 horas semanales).
    
    Args:
        contrato: Instancia de Contrato (debe estar ACTIVO)
        dias_laborados: Días trabajados (0.5-30, permite decimales)
        horas_trabajadas: Horas trabajadas (opcional, para cálculo por horas)
        otros_devengos: Otros devengos adicionales en COP (default: 0)
        prestamos: Préstamos descontados en COP (default: 0)
        descuentos_operativos: Descuentos operativos en COP (default: 0)
        empresa_id: ID de la empresa para validación Zero Trust (opcional pero recomendado)
    
    Returns:
        dict: Diccionario con todos los valores calculados en COP
        
    Reglas de Cálculo (Normativa Colombiana):
    1. Jornada Laboral: 46 horas semanales (Ley 2101 de 2021)
       - Horas mensuales: 46 * 4.33 = 199.18 horas/mes (redondeado a 200 horas)
       - Valor hora = Salario Mensual / 200
    
    2. Salario Proporcional:
       - Por días: (Salario Base / 30) * dias_laborados
       - Por horas: Valor hora * horas_trabajadas (si se proporciona)
    
    3. Auxilio de Transporte:
       - Valor legal vigente (obtener de configuración o contrato)
       - Proporcional: (Auxilio / 30) * dias_laborados
       - Solo aplica si NO es Prestación de Servicios
    
    4. IBC (Ingreso Base de Cotización):
       - IBC = Salario Proporcional (NO incluye auxilio de transporte)
       - Base para calcular Salud (4%) y Pensión (4%)
    
    5. Deducciones de Ley:
       - Salud: 4% sobre IBC
       - Pensión: 4% sobre IBC
       - Solo aplica si es contrato laboral (FIJO, INDEF, OBRA)
       - NO aplica para PRESTACION
    
    6. Neto a Pagar:
       - Neto = (Salario + Auxilio + Otros Devengos) - (Salud + Pensión + Préstamos + Descuentos)
    
    Raises:
        ValueError: Si el contrato no está ACTIVO o los días/horas son inválidos
        ValidationError: Si el contrato no pertenece a la empresa especificada (Zero Trust)
    """
    from apps.tenant.empleados.models import Contrato
    from rest_framework.exceptions import ValidationError
    
    # ⚠️ Zero Trust: Validar que el contrato pertenezca a la empresa especificada
    if empresa_id is not None:
        if contrato.empresa_id != empresa_id:
            raise ValidationError({
                'contrato': f'El contrato no pertenece a la empresa especificada (empresa_id: {empresa_id}).'
            })
    
    # ⚠️ Validación: Contrato debe estar ACTIVO
    if contrato.estado != 'ACTIVO' or not contrato.activo:
        raise ValueError("No se puede calcular nómina para un contrato inactivo")
    
    # ⚠️ Validación: Días laborados (0.5-30) - Normalizar a Decimal
    try:
        dias_laborados = Decimal(str(dias_laborados))
    except (ValueError, TypeError):
        raise ValueError("Los días laborados deben ser un número válido")
    
    if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('30'):
        raise ValueError("Los días laborados deben estar entre 0.5 y 30")
    
    # ⚠️ Ley 2101 de 2021: 46 horas semanales = 200 horas mensuales (46 * 4.33 ≈ 200)
    HORAS_MENSUALES = Decimal('200')  # Jornada de 46 horas semanales
    DIAS_MENSUALES = Decimal('30')   # Mes estándar de 30 días
    
    # 1. CÁLCULO DE SALARIO BASE PROPORCIONAL
    salario_mensual = Decimal(str(contrato.salario_mensual))
    
    if horas_trabajadas is not None and horas_trabajadas > 0:
        # Cálculo por horas (Ley 2101: 200 horas mensuales)
        valor_hora = salario_mensual / HORAS_MENSUALES
        salario_base = valor_hora * Decimal(str(horas_trabajadas))
    else:
        # Cálculo por días (proporcional a 30 días)
        factor = Decimal(str(dias_laborados)) / DIAS_MENSUALES
        salario_base = salario_mensual * factor
    
    # 2. CÁLCULO DE AUXILIO DE TRANSPORTE PROPORCIONAL
    auxilio_transporte = Decimal('0')
    if contrato.tipo != 'PRESTACION':
        # Solo aplica para contratos laborales
        auxilio_mensual = Decimal(str(contrato.auxilio_transporte or 0))
        if auxilio_mensual > 0:
            factor = Decimal(str(dias_laborados)) / DIAS_MENSUALES
            auxilio_transporte = auxilio_mensual * factor
    
    # 3. CÁLCULO DE IBC (Ingreso Base de Cotización)
    # ⚠️ CRÍTICO: IBC = SOLO Salario Base (NO incluye auxilio de transporte)
    ibc = salario_base
    
    # 4. DEDUCCIONES DE LEY (Salud y Pensión - 4% cada una)
    salud_empleado = Decimal('0')
    pension_empleado = Decimal('0')
    
    # Solo aplica para contratos laborales (NO para Prestación de Servicios)
    if contrato.tipo in ['FIJO', 'INDEF', 'OBRA']:
        salud_empleado = ibc * Decimal('0.04')  # 4% sobre IBC
        pension_empleado = ibc * Decimal('0.04')  # 4% sobre IBC
    
    # 5. CÁLCULO DE NETO A PAGAR
    # Devengos = Salario + Auxilio + Otros Devengos
    devengos = salario_base + auxilio_transporte + Decimal(str(otros_devengos))
    
    # Deducciones = Salud + Pensión + Préstamos + Descuentos Operativos
    deducciones = salud_empleado + pension_empleado + Decimal(str(prestamos)) + Decimal(str(descuentos_operativos))
    
    # Neto = Devengos - Deducciones
    neto_pagar = devengos - deducciones
    
    # Validar que el neto no sea negativo (advertencia, no error)
    if neto_pagar < 0:
        logger.warning(f"[calcular_liquidacion_nomina] Neto a pagar negativo: {neto_pagar} para contrato {contrato.id}")
    
    return {
        "salario_base": str(salario_base.quantize(Decimal('0.01'))),
        "auxilio_transporte": str(auxilio_transporte.quantize(Decimal('0.01'))),
        "ibc": str(ibc.quantize(Decimal('0.01'))),  # ⚠️ IBC para referencia
        "salud_empleado": str(salud_empleado.quantize(Decimal('0.01'))),
        "pension_empleado": str(pension_empleado.quantize(Decimal('0.01'))),
        "neto_pagar": str(neto_pagar.quantize(Decimal('0.01')))
    }


def calcular_devengo_proporcional(contrato, dias_laborados, otros_devengos=0, prestamos=0, descuentos_operativos=0):
    """
    ⚠️ DEPRECATED v2.60: Usar calcular_liquidacion_nomina() en su lugar.
    Mantenido para compatibilidad hacia atrás.
    """
    resultado = calcular_liquidacion_nomina(
        contrato=contrato,
        dias_laborados=dias_laborados,
        otros_devengos=otros_devengos,
        prestamos=prestamos,
        descuentos_operativos=descuentos_operativos
    )
    # Mapear nombres de campos para compatibilidad
    return {
        "salario_proporcional": resultado["salario_base"],
        "auxilio_proporcional": resultado["auxilio_transporte"],
        "salud_empleado": resultado["salud_empleado"],
        "pension_empleado": resultado["pension_empleado"],
        "neto_pagar": resultado["neto_pagar"]
    }

    # apps/tenant/empleados/services.py

def calcular_nomina_dinamica(contrato, dias_laborados, horas_extras=0, otros_devengos=0):
    """
    Cálculo SSoT v2.95: Soporta días (0.5), horas y turnos.
    Ajustado a Ley 2101 (44 horas semanales en 2026).
    """
    # 1. Base por Horas (220 horas mensuales para jornada de 44h)
    # Valor hora = salario / 220
    valor_hora = Decimal(contrato.salario_mensual) / Decimal(220)
    
    # 2. Cálculo de Salario Base Proporcional
    # Si se ingresa 0.5 días, equivale a 4 horas (o media jornada)
    total_horas = Decimal(dias_laborados) * Decimal(8)
    salario_base = valor_hora * total_horas
    
    # 3. Auxilio de Transporte (Solo si no es Prestación de Servicios)
    auxilio = Decimal(0)
    if contrato.tipo != 'PRESTACION':
        # Proporcional a días laborados
        auxilio = (Decimal(contrato.auxilio_transporte) / 30) * Decimal(dias_laborados)
    
    # 4. Deducciones de Ley (Salud y Pensión 4% c/u)
    # ⚠️ REGLA: 0% si es PRESTACION, 4% si es Laboral
    salud = pension = Decimal(0)
    if contrato.tipo in ['FIJO', 'INDEF', 'OBRA']:
        salud = salario_base * Decimal('0.04')
        pension = salario_base * Decimal('0.04')
        
    neto = (salario_base + auxilio + Decimal(otros_devengos)) - (salud + pension)
    
    return {
        "salario_base": str(salario_base.quantize(Decimal('0.01'))),
        "salud_empleado": str(salud.quantize(Decimal('0.01'))),
        "pension_empleado": str(pension.quantize(Decimal('0.01'))),
        "neto_pagar": str(neto.quantize(Decimal('0.01')))
    }