"""
Extractor de Proveedores para Dashboard - Pull Model.
Usa ProveedorSelector y CuentasPagarSelector, no importa models.py directamente.
"""
from decimal import Decimal
from apps.tenant.dashboard.services.dtos import WidgetProveedoresDTO


class ProveedoresExtractor:

    @staticmethod
    def extraer_metricas(empresa_id: int) -> WidgetProveedoresDTO:
        try:
            from apps.tenant.proveedores.services.selectors import ProveedorSelector, CuentasPagarSelector

            # total_provedores
            proveedores_qs = ProveedorSelector.get_list(empresa_id).filter(activo=True)
            total_provedores = proveedores_qs.count()

            # Resumen de cartera por pagar
            resumen = CuentasPagarSelector.resumen_por_empresa(empresa_id)
            cartera_pendiente = resumen.get('deuda_total_pendiente', Decimal('0.00'))
            total_pagado = resumen.get('total_pagado_historico', Decimal('0.00'))

            # total_gastos es el total facturado por proveedores (saldo pendiente + valor pagado)
            total_gastos = cartera_pendiente + total_pagado

            return WidgetProveedoresDTO(
                total_provedores=total_provedores,
                total_gastos=total_gastos.quantize(Decimal('0.01')),
                cartera_pendiente=cartera_pendiente.quantize(Decimal('0.01')),
            )

        except Exception:
            return WidgetProveedoresDTO(0, Decimal('0.00'), Decimal('0.00'))
