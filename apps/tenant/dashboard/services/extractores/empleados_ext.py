"""
Extractor de Empleados para Dashboard v3.9.5 — datos reales.
Pull Model: usa NominaSummarySelector + EmpleadoSelector, no importa models.py.
"""
from decimal import Decimal

from apps.tenant.dashboard.services.dtos import WidgetEmpleadosDTO

_ZERO = Decimal('0.00')


class EmpleadosExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetEmpleadosDTO:
        try:
            from apps.tenant.empleados.services.selectors import (
                NominaSummarySelector,
                EmpleadoSelector,
            )

            summary = NominaSummarySelector.get_summary(empresa_id)

            total_empleados = summary.get('total_empleados', 0)
            empleados_activos = summary.get('empleados_activos', 0)
            empleados_pagados = summary.get('empleados_pagados', 0)
            total_nomina_mes = Decimal(str(summary.get('total_nomina_mes', '0') or '0'))

            # Empleados activos sin nómina registrada este mes
            nominas_pendientes = max(0, empleados_activos - empleados_pagados)

            return WidgetEmpleadosDTO(
                total_empleados=total_empleados,
                empleados_activos=empleados_activos,
                nominas_pendientes=nominas_pendientes,
                **{'total_nómina_mes': total_nomina_mes},
            )

        except Exception:
            return WidgetEmpleadosDTO(0, 0, 0, _ZERO)
