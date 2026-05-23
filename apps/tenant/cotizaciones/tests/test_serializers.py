import pytest
from decimal import Decimal
from django_tenants.utils import schema_context
from apps.tenant.cotizaciones.api.serializers import CotizacionSerializer
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

@pytest.mark.django_db
def test_cotizacion_serializer_valid(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    
    with schema_context(tenant.schema_name):
        cliente.activo = True
        cliente.save()

        config, _ = ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={
                'dias_validez': 15,
                'nombre_configuracion': 'Perfil General',
                'es_activo': True
            }
        )

        data = {
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
        
        serializer = CotizacionSerializer(data=data, context={'empresa': empresa})
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_cotizacion_serializer_valid_uuid(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    
    with schema_context(tenant.schema_name):
        cliente.activo = True
        cliente.save()

        config, _ = ConfiguracionCotizacion.objects.get_or_create(
            empresa=empresa,
            defaults={
                'dias_validez': 15,
                'nombre_configuracion': 'Perfil General',
                'es_activo': True
            }
        )

        data = {
            'cliente': str(cliente.uuid),
            'configuracion': str(config.uuid),
            'tipo_cotizacion': 'PRODUCTO',
            'items': [
                {
                    'tipo_item': 'PRODUCTO',
                    'descripcion': 'Equipo de prueba con UUID',
                    'cantidad': '1.00',
                    'costo_unitario': '1000.00',
                    'porcentaje_utilidad': '20.00',
                    'unidad': 'UND',
                    'orden': 1
                }
            ]
        }
        
        serializer = CotizacionSerializer(data=data, context={'empresa': empresa})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data['cliente'] == cliente
        assert serializer.validated_data['configuracion'] == config


