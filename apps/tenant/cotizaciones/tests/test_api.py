import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django_tenants.utils import schema_context
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
from django.contrib.auth import get_user_model

@pytest.mark.urls('config.urls_tenant')
@pytest.mark.django_db
def test_api_crear_cotizacion(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    client = APIClient()
    
    with schema_context(tenant.schema_name):
        cliente.activo = True
        cliente.save()

        # Create active config
        config, _ = ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={
                'dias_validez': 15,
                'nombre_configuracion': 'Perfil General',
                'es_activo': True
            }
        )

        User = get_user_model()
        user = User.objects.filter(email="admin@test.local").first()
        client.force_authenticate(user=user)

        payload = {
            'cliente': cliente.id,
            'configuracion': config.id,
            'tipo_cotizacion': 'PRODUCTO',
            'items': [
                {
                    'tipo_item': 'PRODUCTO',
                    'descripcion': 'Equipo de prueba',
                    'cantidad': '2.00',
                    'costo_unitario': '500.00',
                    'porcentaje_utilidad': '10.00',
                    'unidad': 'UND',
                    'orden': 1
                }
            ]
        }
        client.credentials(HTTP_HOST=f'{tenant.schema_name}.sintel.net.co')
        url = reverse('cotizacion-list')
        response = client.post(url, payload, format='json')
        assert response.status_code in (200, 201), response.content
        assert Cotizacion.objects.filter(empresa_id=empresa.id).count() == 1


@pytest.mark.urls('config.urls_tenant')
@pytest.mark.django_db
def test_api_listar_configuracion_cotizacion(tenant, factory_empresa):
    """Regression: ConfiguracionCotizacionViewSet must resolve get_empresa_id
    (requires SintelDSVMixin) instead of 500ing on every request."""
    empresa = factory_empresa()
    client = APIClient()

    with schema_context(tenant.schema_name):
        ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={
                'dias_validez': 15,
                'nombre_configuracion': 'Perfil General',
                'es_activo': True
            }
        )

        User = get_user_model()
        user = User.objects.filter(email="admin@test.local").first()
        client.force_authenticate(user=user)

        client.credentials(HTTP_HOST=f'{tenant.schema_name}.sintel.net.co')
        url = reverse('configuracion-cotizacion-list')
        response = client.get(url)
        assert response.status_code == 200, response.content
