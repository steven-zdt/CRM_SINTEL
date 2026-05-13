"""
Selectores de Empleados - Consultas GET optimizadas (read-only).

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene SOLO consultas de lectura optimizadas.
- Todas las funciones son @staticmethod.
- Usa .only() para cargar solo campos necesarios (Zero Waste).
"""
from django.db.models import Exists, OuterRef, Q, Sum, Count
from django.utils import timezone

from apps.tenant.empleados.models import Contrato, Devengo, Empleado


# ==============================================================================
# CONSTANTES SSoT - Campos para consultas optimizadas
# ==============================================================================

# Campos estrictamente necesarios para LISTAS (Tabulator)
EMPLEADO_LIST_FIELDS = (
    'id', 'tipo_documento', 'numero_documento', 'primer_nombre', 'primer_apellido',
    'segundo_nombre', 'segundo_apellido', 'estado', 'fecha_ingreso', 'empresa_id',
    'cuenta_contable_uuid'
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

# Campos completos para DETALLE (formularios de edición)
EMPLEADO_DETAIL_FIELDS = (
    'id', 'empresa', 'empresa__id', 'tipo_documento', 'numero_documento',
    'primer_nombre', 'segundo_nombre', 'primer_apellido', 'segundo_apellido',
    'email', 'telefono', 'eps', 'afp', 'arl', 'nivel_riesgo_arl',
    'estado', 'fecha_ingreso', 'fecha_retiro', 'cuenta_contable_uuid'
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


# ==============================================================================
# SELECTOR CLASSES - Organizadas por modelo
# ==============================================================================

class EmpleadoSelector:
    """Read-only selectors para modelo Empleado."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None):
        """
        QuerySet optimizado para LISTAR Empleados.
        Anota estados secuenciales para lógica de botones UI.
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

        qs = Empleado.objects.filter(empresa_id=empresa_id).annotate(
            tiene_contrato_activo=Exists(has_contract),
            tiene_nominas_registradas=Exists(has_payroll)
        ).only(*EMPLEADO_LIST_FIELDS)

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
    def get_detail(empresa_id: int, empleado_id: int):
        """QuerySet optimizado para DETALLE de Empleado."""
        return Empleado.objects.filter(
            empresa_id=empresa_id, pk=empleado_id
        ).select_related('empresa').only(*EMPLEADO_DETAIL_FIELDS).get()


class ContratoSelector:
    """Read-only selectors para modelo Contrato."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, empleado_id: int = None):
        """QuerySet optimizado para LISTAR Contratos."""
        qs = Contrato.objects.filter(empresa_id=empresa_id).select_related(
            'empleado'
        ).only(*CONTRATO_LIST_FIELDS)

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
    def get_detail(empresa_id: int, contrato_id: int):
        """QuerySet optimizado para DETALLE de Contrato."""
        return Contrato.objects.filter(
            empresa_id=empresa_id, pk=contrato_id
        ).select_related('empresa', 'empleado').only(*CONTRATO_DETAIL_FIELDS).get()


class DevengoSelector:
    """Read-only selectors para modelo Devengo (Nómina)."""

    @staticmethod
    def get_list(empresa_id: int, search: str = None, empleado_id: int = None, periodo_mes: str = None):
        """QuerySet optimizado para LISTAR Devengos/Nóminas."""
        qs = Devengo.objects.filter(empresa_id=empresa_id).select_related(
            'empleado', 'contrato'
        ).only(*DEVENGO_LIST_FIELDS)

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
    def get_detail(empresa_id: int, devengo_id: int):
        """QuerySet optimizado para DETALLE de Devengo."""
        return Devengo.objects.filter(
            empresa_id=empresa_id, pk=devengo_id
        ).select_related('empresa', 'empleado', 'contrato').only(*DEVENGO_DETAIL_FIELDS).get()

    @staticmethod
    def get_historial(empleado_id: int, empresa_id: int, search: str = None):
        """QuerySet optimizado para HISTORIAL de Nóminas de un empleado."""
        qs = Devengo.objects.filter(
            empresa_id=empresa_id,
            empleado_id=empleado_id
        ).select_related('empleado', 'contrato').only(*DEVENGO_LIST_FIELDS)

        if search:
            qs = qs.filter(
                Q(periodo_mes__icontains=search) |
                Q(fecha_pago__icontains=search)
            )

        return qs.order_by('-fecha_pago', '-periodo_mes', 'id')


class NominaSummarySelector:
    """Selector para resúmenes analíticos de nómina."""

    @staticmethod
    def get_summary(empresa_id: int):
        """Calcula analítica para el panel superior (resumen de nómina)."""
        hoy = timezone.now().date()
        mes_actual = hoy.strftime("%Y-%m")

        qs_mes = Devengo.objects.filter(
            empresa_id=empresa_id,
            periodo_mes=mes_actual,
            anulado=False
        )

        from decimal import Decimal
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
