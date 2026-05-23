import pytest
import datetime
from decimal import Decimal
from django_tenants.utils import schema_context
from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.cotizaciones.models import Cotizacion

@pytest.mark.django_db
def test_crear_cotizacion_valida(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    
    payload = {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 3, 30),
        'items': [
            {
                'tipo_item': 'PRODUCTO',
                'descripcion': 'Equipo de prueba',
                'cantidad': 2,
                'costo_unitario': 500,
                'porcentaje_utilidad': 10,
                'unidad': 'UND',
                'orden': 1
            }
        ]
    }
    with schema_context(tenant.schema_name):
        # We need to make sure there's a configuration for the company as well
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
        ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={
                'dias_validez': 15,
                'nombre_configuracion': 'Perfil General',
                'es_activo': True
            }
        )
        
        cotizacion = CotizacionService.crear_preforma(empresa, payload)
        assert cotizacion.empresa_id == empresa.id
        assert cotizacion.cliente_id == cliente.id
        assert cotizacion.total_con_impuestos == Decimal("1309.00")
        assert Cotizacion.objects.filter(empresa_id=empresa.id).count() == 1
