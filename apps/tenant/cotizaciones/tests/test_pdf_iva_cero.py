"""
Regresion (2026-09-12): el PDF de cotizacion recalculaba el IVA de forma
independiente al dominio, usando "cotizacion.iva_porcentaje or 19" en vez
de "or 0" (el default que SI usa CotizacionService.calcular_totales,
business_service.py:251). Una cotizacion explicitamente exenta de IVA
(iva_porcentaje=0) se facturaba al cliente en el PDF con 19% de IVA --
"0 or 19" evalua 19 en Python.

Ver docs/remediation/AUDIT_BASELINE_20260912.md hallazgo Q-1.
"""
import datetime
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.cotizaciones.services.pdf_export_service import CotizacionPDFExportService


def _crear_cotizacion_iva_cero(empresa, cliente):
    from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

    ConfiguracionCotizacion.objects.get_or_create(
        empresa=empresa,
        defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
    )
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'iva_porcentaje': 0,
        'items': [{
            'tipo_item': 'PRODUCTO', 'descripcion': 'Item exento de IVA',
            'cantidad': 1, 'costo_unitario': 1000000, 'porcentaje_utilidad': 0,
            'unidad': 'UND', 'orden': 1,
        }],
    }
    return CotizacionService.crear_preforma(empresa, payload)


@pytest.mark.django_db
def test_pdf_no_aplica_19_por_ciento_cuando_iva_es_cero(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion_iva_cero(empresa, cliente)
        assert cotizacion.iva_porcentaje == Decimal("0.00")

        contexto = CotizacionPDFExportService.preparar_contexto(cotizacion, empresa)

        assert contexto['iva_porcentaje'] == Decimal("0")
        assert contexto['iva_valor'] == Decimal("0")
        # Sin AIU en este caso: total del PDF debe ser exactamente el
        # subtotal, no subtotal*1.19.
        assert contexto['total_neto'] == contexto['subtotal_items']
