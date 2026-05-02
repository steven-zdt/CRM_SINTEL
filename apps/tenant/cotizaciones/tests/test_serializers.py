import pytest
from apps.tenant.cotizaciones.api.serializers import CotizacionSerializer
from apps.tenant.cotizaciones.models import Cotizacion

@pytest.mark.django_db
def test_cotizacion_serializer_valid(factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    data = {
        'cliente_id': cliente.id,
        'total': 2000,
        'fecha': '2026-03-30',
        'empresa_id': empresa.id
    }
    serializer = CotizacionSerializer(data=data, context={'empresa': empresa})
    assert serializer.is_valid(), serializer.errors
    cotizacion = serializer.save()
    assert cotizacion.empresa_id == empresa.id
    assert cotizacion.total == 2000
    assert cotizacion.cliente_id == cliente.id
