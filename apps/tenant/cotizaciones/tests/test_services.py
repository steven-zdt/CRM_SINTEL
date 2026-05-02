import pytest
from apps.tenant.cotizaciones.services import CotizacionService
from apps.tenant.cotizaciones.models import Cotizacion
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_crear_cotizacion_valida(factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    payload = {
        'cliente_id': cliente.id,
        'total': 1000,
        'fecha': '2026-03-30',
        'empresa_id': empresa.id
    }
    cotizacion = CotizacionService.crear_preforma(empresa.id, payload)
    assert cotizacion.empresa_id == empresa.id
    assert cotizacion.total == 1000
    assert cotizacion.cliente_id == cliente.id
    assert Cotizacion.objects.filter(empresa_id=empresa.id).count() == 1
