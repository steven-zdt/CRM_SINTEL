"""
Selectors de Empleados - Consultas GET optimizadas (read-only).

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO consultas de lectura optimizadas.
- Todas las funciones son @staticmethod.
- Usa .only() para cargar solo campos necesarios (Zero Waste).
"""
from datetime import date
from decimal import Decimal

from django.db.models import Count, Exists, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.tenant.empleados.models import Contrato, Devengo, Empleado


# ==============================================================================
# CONSTANTES SSoT - Campos para consultas optimizadas
# ==============================================================================

# Campos estrictamente necesarios para LISTAS (Tabulator)
EMPLEADO_LIST_FIELDS = (
    'id', 'uuid', 'tipo_documento', 'numero_documento', 'primer_nombre', 'primer_apellido',
    'segundo_nombre', 'segundo_apellido', 'estado', 'fecha_ingreso', 'empresa_id', 'foto',
    'email', 'telefono', 'sede', 'area', 'resolucion_dian',
)

_SEDE_AREA_TRAVERSALS = (
    'sede__id', 'sede__uuid', 'sede__nombre',
    'area__id', 'area__uuid', 'area__nombre',
)

CONTRATO_LIST_FIELDS = (
    'id', 'uuid', 'empleado',
    'tipo', 'fecha_inicio', 'fecha_fin', 'salario_mensual', 'auxilio_transporte',
    'cargo', 'estado', 'activo', 'empresa_id', 'horas_semanales',
)

_CONTRATO_LIST_EMPLEADO_TRAVERSALS = (
    'empleado__id', 'empleado__uuid',
    'empleado__primer_nombre', 'empleado__primer_apellido',
)

DEVENGO_LIST_FIELDS = (
    'id', 'uuid', 'empresa_id',
    # Empleado (cross-model via select_related)
    'empleado',
    # Contrato (cross-model via select_related)
    'contrato',
    # Nómina — período y fechas
    'periodo_mes', 'fecha_inicio', 'fecha_fin', 'fecha_pago', 'dias_laborados',
    # Devengos
    'salario_base', 'auxilio_transporte', 'otros_devengos',
    'horas_extras_diurnas', 'horas_extras_nocturnas', 'recargo_nocturno_horas', 'recargo_festivo_horas', 'valor_horas_extras',
    # Deducciones
    'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
    # Totales y estado
    'neto_pagar', 'anulado',
)

_DEVENGO_LIST_TRAVERSALS = (
    'empleado__id', 'empleado__uuid',
    'empleado__tipo_documento', 'empleado__numero_documento',
    'empleado__primer_nombre', 'empleado__primer_apellido',
    'contrato__id', 'contrato__uuid', 'contrato__tipo', 'contrato__cargo', 'contrato__salario_mensual',
)

# Campos completos para DETALLE (formularios de edicion)
EMPLEADO_DETAIL_FIELDS = (
    'id', 'uuid', 'empresa', 'tipo_documento', 'numero_documento',
    'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
    'email', 'telefono', 'eps', 'afp', 'arl', 'nivel_riesgo_arl',
    'estado', 'fecha_ingreso', 'fecha_retiro', 'foto',
    'sede', 'area', 'resolucion_dian',
)

_EMPLEADO_DETAIL_TRAVERSALS = (
    'empresa__id',
    'sede__id', 'sede__uuid', 'sede__nombre',
    'area__id', 'area__uuid', 'area__nombre',
    'resolucion_dian__id', 'resolucion_dian__uuid',
    'resolucion_dian__numero_resolucion', 'resolucion_dian__prefijo', 'resolucion_dian__vigente',
)

CONTRATO_DETAIL_FIELDS = (
    'id', 'uuid', 'empresa', 'empleado',
    'tipo', 'fecha_inicio', 'fecha_fin', 'salario_mensual', 'auxilio_transporte',
    'prestamos_empresa', 'cargo', 'archivo_pdf', 'estado', 'activo', 'horas_semanales',
)

_CONTRATO_DETAIL_TRAVERSALS = (
    'empresa__id', 'empleado__id', 'empleado__uuid',
    'empleado__primer_nombre', 'empleado__primer_apellido',
)

DEVENGO_DETAIL_FIELDS = (
    'id', 'uuid', 'empresa',
    # Empleado
    'empleado',
    # Contrato
    'contrato',
    # Nómina
    'periodo_mes', 'fecha_inicio', 'fecha_fin', 'fecha_pago', 'dias_laborados',
    # Devengos
    'salario_base', 'auxilio_transporte', 'otros_devengos',
    'horas_extras_diurnas', 'horas_extras_nocturnas', 'recargo_nocturno_horas', 'recargo_festivo_horas', 'valor_horas_extras',
    # Deducciones
    'salud_empleado', 'pension_empleado', 'prestamos', 'descuentos_operativos',
    # Totales, notas y estado
    'observaciones', 'neto_pagar', 'anulado',
)

_DEVENGO_DETAIL_TRAVERSALS = (
    'empresa__id',
    'empleado__id', 'empleado__uuid',
    'empleado__tipo_documento', 'empleado__numero_documento',
    'empleado__primer_nombre', 'empleado__primer_apellido',
    'contrato__id', 'contrato__uuid', 'contrato__tipo', 'contrato__salario_mensual',
)


# ==============================================================================
# SELECTOR CLASSES - Organizadas por modelo
# ==============================================================================

class EmpleadoSelector:
    """Read-only selectors para modelo Empleado."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, sede_ids=None, area_ids=None):
        """
        QuerySet optimizado para LISTAR Empleados.
        Anota estados secuenciales para logica de botones UI.

        [OSF Fase F7] `sede_ids`/`area_ids=None` (default) no restringe -
        comportamiento identico al de antes de esta fase. El 100% de los
        Empleado reales tiene sede=NULL/area=NULL hoy (verificado
        empiricamente) - un registro sin sede/area queda visible para todos
        los alcances (filtro NULL-safe), para no ocultar datos existentes.
        """
        has_contract = Contrato.objects.filter(
            empleado_id=OuterRef('pk'),
            activo=True,
            estado='ACTIVO',
            empresa_id=empresa_id
        )

        has_payroll = Devengo.objects.filter(
            empleado_id=OuterRef('pk'),
            anulado=False,
            empresa_id=empresa_id
        )

        contrato_activo_uuid = Subquery(
            Contrato.objects.filter(
                empleado_id=OuterRef('pk'),
                activo=True,
                estado='ACTIVO',
                empresa_id=empresa_id,
            ).values('uuid')[:1]
        )

        cargo = Subquery(
            Contrato.objects.filter(
                empleado_id=OuterRef('pk'),
                activo=True,
                estado='ACTIVO',
                empresa_id=empresa_id,
            ).values('cargo')[:1]
        )

        qs = Empleado.objects.filter(empresa_id=empresa_id).annotate(
            tiene_contrato_activo=Exists(has_contract),
            tiene_nominas_registradas=Exists(has_payroll),
            contrato_activo_uuid=contrato_activo_uuid,
            cargo=cargo,
        ).select_related('sede', 'area').only(*EMPLEADO_LIST_FIELDS, *_SEDE_AREA_TRAVERSALS)

        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        if area_ids is not None:
            qs = qs.filter(Q(area_id__isnull=True) | Q(area_id__in=area_ids))

        if search:
            qs = qs.filter(
                Q(numero_documento__icontains=search) |
                Q(primer_nombre__icontains=search) |
                Q(primer_apellido__icontains=search) |
                Q(segundo_nombre__icontains=search) |
                Q(segundo_apellido__icontains=search)
            )

        return qs.order_by('-fecha_ingreso', 'id')

    @staticmethod
    def get_detail(empresa_id: int, empleado_uuid, sede_ids=None, area_ids=None):
        """QuerySet optimizado para DETALLE de Empleado.

        [OSF Fase F13] `sede_ids`/`area_ids=None` (default) no restringen -
        mismo criterio NULL-safe de F7 (get_list). Antes de esta fase,
        `EmpleadoViewSet.get_object()` (retrieve/update/partial_update/
        destroy, via get_qs_detail() generico) solo filtraba por empresa_id -
        mismo gap que F11/F13(gastos/cotizaciones/inventario/proyectos)
        encontraron y corrigieron.
        """
        qs = Empleado.objects.filter(
            empresa_id=empresa_id, uuid=empleado_uuid
        ).select_related('empresa', 'sede', 'area').only(*EMPLEADO_DETAIL_FIELDS, *_EMPLEADO_DETAIL_TRAVERSALS)
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        if area_ids is not None:
            qs = qs.filter(Q(area_id__isnull=True) | Q(area_id__in=area_ids))
        return qs.get()

    @staticmethod
    def get_by_id(empresa_id: int, empleado_id: int):
        """Obtiene un empleado por PK interno solo para payloads validados."""
        return Empleado.objects.filter(
            empresa_id=empresa_id, pk=empleado_id
        ).only('id', 'uuid', 'empresa_id', 'estado').get()

    @staticmethod
    def get_empleados_activos(empresa_id: int):
        """Retorna todos los empleados activos."""
        return Empleado.objects.filter(
            empresa_id=empresa_id,
            estado='ACTIVO'
        ).only('id', 'uuid', 'numero_documento', 'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido')

    @staticmethod
    def get_empleados_sin_contrato(empresa_id: int):
        """Retorna empleados activos que NO tienen un contrato vigente."""
        has_contract = Contrato.objects.filter(
            empleado_id=OuterRef('pk'),
            activo=True,
            estado='ACTIVO',
            empresa_id=empresa_id
        )
        return Empleado.objects.filter(
            empresa_id=empresa_id,
            estado='ACTIVO'
        ).annotate(
            tiene_contrato_activo=Exists(has_contract)
        ).filter(
            tiene_contrato_activo=False
        ).only('id', 'uuid', 'numero_documento', 'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido')

    @classmethod
    def get_disponibles_para_periodo(cls, empresa_id: int, fecha_inicio, fecha_fin):
        """
        Retorna los empleados de la empresa con contrato activo que NO
        tienen nominas registradas (no anuladas) solapadas con el rango dado.
        """
        if isinstance(fecha_inicio, str):
            fecha_inicio = date.fromisoformat(fecha_inicio)
        if isinstance(fecha_fin, str):
            fecha_fin = date.fromisoformat(fecha_fin)

        start_month = fecha_inicio.strftime('%Y-%m')
        end_month = fecha_fin.strftime('%Y-%m')

        solapados = Devengo.objects.filter(
            empresa_id=empresa_id,
            anulado=False
        ).filter(
            Q(fecha_inicio__lte=fecha_fin, fecha_fin__gte=fecha_inicio) |
            Q(
                Q(fecha_inicio__isnull=True) | Q(fecha_fin__isnull=True),
                periodo_mes__gte=start_month,
                periodo_mes__lte=end_month
            )
        ).values_list('empleado_id', flat=True)

        has_contract = Contrato.objects.filter(
            empleado_id=OuterRef('pk'),
            activo=True,
            estado='ACTIVO',
            empresa_id=empresa_id
        )

        return Empleado.objects.filter(
            empresa_id=empresa_id,
            estado='ACTIVO'
        ).annotate(
            tiene_contrato_activo=Exists(has_contract)
        ).filter(
            tiene_contrato_activo=True
        ).exclude(
            id__in=solapados
        ).only('id', 'uuid', 'primer_nombre', 'primer_apellido', 'numero_documento')


class ContratoSelector:
    """Read-only selectors para modelo Contrato."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, empleado_id: int = None):
        """QuerySet optimizado para LISTAR Contratos."""
        qs = Contrato.objects.filter(empresa_id=empresa_id).select_related(
            'empleado'
        ).only(*CONTRATO_LIST_FIELDS, *_CONTRATO_LIST_EMPLEADO_TRAVERSALS)

        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)

        if search:
            qs = qs.filter(
                Q(cargo__icontains=search) |
                Q(empleado__primer_nombre__icontains=search) |
                Q(empleado__primer_apellido__icontains=search)
            )

        return qs.order_by('-fecha_inicio', 'id')

    @staticmethod
    def get_detail(empresa_id: int, contrato_uuid):
        """QuerySet optimizado para DETALLE de Contrato."""
        return Contrato.objects.filter(
            empresa_id=empresa_id, uuid=contrato_uuid
        ).select_related('empresa', 'empleado').only(*CONTRATO_DETAIL_FIELDS, *_CONTRATO_DETAIL_TRAVERSALS).get()

    @staticmethod
    def get_by_id(empresa_id: int, contrato_id: int):
        """Obtiene un contrato por PK interno solo para payloads validados."""
        return Contrato.objects.filter(
            empresa_id=empresa_id, pk=contrato_id
        ).select_related('empleado').only(*CONTRATO_DETAIL_FIELDS, *_CONTRATO_DETAIL_TRAVERSALS).get()

    @staticmethod
    def get_activo_for_empleado(empresa_id: int, empleado_id: int):
        """Retorna el contrato activo del empleado dentro del tenant."""
        return Contrato.objects.filter(
            empresa_id=empresa_id,
            empleado_id=empleado_id,
            estado='ACTIVO',
            activo=True,
        ).select_related('empleado').only(*CONTRATO_DETAIL_FIELDS, *_CONTRATO_DETAIL_TRAVERSALS).first()


class DevengoSelector:
    """Read-only selectors para modelo Devengo (Nomina)."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, empleado_id: int = None, periodo_mes: str = None):
        """QuerySet optimizado para LISTAR Devengos/Nominas."""
        qs = Devengo.objects.filter(empresa_id=empresa_id).select_related(
            'empleado', 'contrato'
        ).only(*DEVENGO_LIST_FIELDS, *_DEVENGO_LIST_TRAVERSALS)

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

    @staticmethod
    def get_detail(empresa_id: int, devengo_uuid):
        """QuerySet optimizado para DETALLE de Devengo."""
        return Devengo.objects.filter(
            empresa_id=empresa_id, uuid=devengo_uuid
        ).select_related('empresa', 'empleado', 'contrato').only(*DEVENGO_DETAIL_FIELDS, *_DEVENGO_DETAIL_TRAVERSALS).get()

    @staticmethod
    def get_historial(empleado_id: int, empresa_id: int, search: str = None):
        """QuerySet optimizado para HISTORIAL de Nominas de un empleado."""
        qs = Devengo.objects.filter(
            empresa_id=empresa_id,
            empleado_id=empleado_id
        ).select_related('empleado', 'contrato').only(*DEVENGO_LIST_FIELDS, *_DEVENGO_LIST_TRAVERSALS)

        if search:
            qs = qs.filter(
                Q(periodo_mes__icontains=search) |
                Q(fecha_pago__icontains=search)
            )

        return qs.order_by('-fecha_pago', '-periodo_mes', 'id')

    @staticmethod
    def exists_for_periodo(empresa_id: int, empleado_id: int, periodo_mes: str) -> bool:
        """Indica si ya hay nomina vigente para un empleado y periodo."""
        return Devengo.objects.filter(
            empresa_id=empresa_id,
            empleado_id=empleado_id,
            periodo_mes=periodo_mes,
            anulado=False,
        ).only('id').exists()

    @staticmethod
    def get_ultima_for_empleado(empresa_id: int, empleado_id: int):
        """Retorna la ultima nomina vigente del empleado dentro del tenant."""
        return Devengo.objects.filter(
            empresa_id=empresa_id,
            empleado_id=empleado_id,
            anulado=False,
        ).select_related('empleado', 'contrato').only(*DEVENGO_LIST_FIELDS, *_DEVENGO_LIST_TRAVERSALS).order_by(
            '-fecha_pago', '-periodo_mes'
        ).first()


class NominaSummarySelector:
    """Selector para resumenes analiticos de nomina."""

    @staticmethod
    def get_summary(empresa_id: int):
        """Calcula analitica para el panel superior (resumen de nomina)."""
        hoy = timezone.now().date()
        mes_actual = hoy.strftime("%Y-%m")

        qs_mes = Devengo.objects.filter(
            empresa_id=empresa_id,
            periodo_mes=mes_actual,
            anulado=False
        ).only('id', 'neto_pagar')

        totales = qs_mes.aggregate(
            total_neto=Coalesce(Sum('neto_pagar'), Decimal('0.00')),
            count_pagos=Count('id')
        )

        qs_emp = Empleado.objects.filter(empresa_id=empresa_id).only('id', 'estado')
        activos = qs_emp.filter(estado='ACTIVO').count()
        retirados = qs_emp.filter(estado='RETIRADO').count()
        total = qs_emp.count()

        return {
            "total_empleados": total,
            "empleados_activos": activos,
            "empleados_retirados": retirados,
            "total_nomina_mes": str(totales['total_neto']),
            "empleados_pagados": totales['count_pagos'],
        }


# Compatibilidad legacy - tuplas de campos por modelo
LIST_FIELDS = {
    'empleado': EMPLEADO_LIST_FIELDS,
    'contrato': CONTRATO_LIST_FIELDS,
    'devengo': DEVENGO_LIST_FIELDS,
}

DETAIL_FIELDS = {
    'empleado': EMPLEADO_DETAIL_FIELDS,
    'contrato': CONTRATO_DETAIL_FIELDS,
    'devengo': DEVENGO_DETAIL_FIELDS,
}

