import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.tenant.cotizaciones.models import Cotizacion

@pytest.mark.django_db
def test_api_crear_cotizacion(factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    client = APIClient()
    # Simular autenticación y contexto de empresa
    client.force_authenticate(user=empresa.usuario_set.first())
    payload = {
        'cliente_id': cliente.id,
        'total': 1500,
        'fecha': '2026-03-30',
        'empresa_id': empresa.id
    }
    url = reverse('cotizaciones-list')
    response = client.post(url, payload, format='json')
    assert response.status_code in (200, 201)
    assert Cotizacion.objects.filter(empresa_id=empresa.id, total=1500).exists()
