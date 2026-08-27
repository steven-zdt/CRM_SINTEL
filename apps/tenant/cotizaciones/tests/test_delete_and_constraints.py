"""
Regresiones reales de la auditoria REL Cotizaciones (FASE 2/5, 2026-08-26):

1. DELETE de Cotizacion via API usaba el destroy() por defecto de DRF
   (hard-delete directo, sin ningun chequeo de trazabilidad) -- ahora pasa
   por CotizacionService.eliminar_cotizacion(), que bloquea el borrado si
   existe una Factura vinculada via Factura.cotizacion_uuid.
2. ProductoViewSet/ServicioViewSet/ConfiguracionCotizacionViewSet.destroy()
   llamaban instance.delete() directo, bypaseando el Service Layer -- ahora
   pasan por sus respectivos business_service.eliminar()/eliminar_configuracion().
3. Producto.codigo solo se validaba como unico a nivel de aplicacion (query +
   ValueError, condicion de carrera real) -- ahora hay un UniqueConstraint
   de BD (uniq_producto_codigo_por_empresa) como ultima linea de defensa,
   y el ViewSet devuelve 400 limpio (antes: 500 sin capturar) en cualquiera
   de los dos caminos.
"""
import datetime

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
from apps.tenant.cotizaciones.models import Cotizacion, Producto
from apps.tenant.cotizaciones.services import CotizacionService
from django.contrib.auth import get_user_model


def _crear_cotizacion(empresa, cliente):
    config, _ = ConfiguracionCotizacion.objects.get_or_create(
        empresa=empresa,
        defaults={'dias_validez': 15, 'nombre_configuracion': 'Perfil General', 'es_activo': True},
    )
    return CotizacionService.crear_preforma(empresa, {
        'cliente': cliente.id,
        'fecha_emision': datetime.date(2026, 6, 1),
        'items': [],
    })


def _authed_client(tenant):
    client = APIClient()
    User = get_user_model()
    user = User.objects.filter(email="admin@test.local").first()
    client.force_authenticate(user=user)
    client.credentials(HTTP_HOST=f'{tenant.schema_name}.sintel.net.co')
    return client


@pytest.mark.urls('config.urls_tenant')
@pytest.mark.django_db
def test_eliminar_cotizacion_sin_factura_vinculada_funciona(tenant, factory_empresa, factory_cliente):
    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    client = _authed_client(tenant)

    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(empresa, cliente)

    url = reverse('cotizacion-detail', kwargs={'uuid': cotizacion.uuid})
    response = client.delete(url)
    assert response.status_code == 204, response.content

    with schema_context(tenant.schema_name):
        assert not Cotizacion.objects.filter(uuid=cotizacion.uuid).exists()


@pytest.mark.urls('config.urls_tenant')
@pytest.mark.django_db
def test_eliminar_cotizacion_con_factura_vinculada_se_bloquea(tenant, factory_empresa, factory_cliente):
    from apps.tenant.facturas.models import Factura

    empresa = factory_empresa()
    cliente = factory_cliente(empresa=empresa)
    client = _authed_client(tenant)

    with schema_context(tenant.schema_name):
        cotizacion = _crear_cotizacion(empresa, cliente)
        Factura.objects.create(
            empresa=empresa, numero="FV-DELREL-1", prefijo="FV", consecutivo=1,
            tipo=Factura.TipoFactura.FE, estado=Factura.Estado.ACEPTADA, naturaleza=Factura.Naturaleza.VENTA,
            fecha_emision="2026-06-02T10:00:00Z",
            emisor_nit=empresa.nit, emisor_razon_social=empresa.razon_social,
            receptor_nit=cliente.numero_documento, receptor_razon_social=cliente.razon_social,
            subtotal="100000.00", impuestos="19000.00", total="119000.00",
            cufe="CUFE-DELREL-1", cotizacion_uuid=cotizacion.uuid,
        )

    url = reverse('cotizacion-detail', kwargs={'uuid': cotizacion.uuid})
    response = client.delete(url)
    assert response.status_code == 400, response.content

    with schema_context(tenant.schema_name):
        assert Cotizacion.objects.filter(uuid=cotizacion.uuid).exists()


@pytest.mark.urls('config.urls_tenant')
@pytest.mark.django_db
def test_eliminar_producto_via_api_pasa_por_service_layer(tenant, factory_empresa):
    empresa = factory_empresa()
    client = _authed_client(tenant)

    with schema_context(tenant.schema_name):
        producto = Producto.objects.create(empresa=empresa, nombre="Producto DEL REL", precio_venta="100.00")

    url = reverse('producto-detail', kwargs={'uuid': producto.uuid})
    response = client.delete(url)
    assert response.status_code == 204, response.content

    with schema_context(tenant.schema_name):
        assert not Producto.objects.filter(uuid=producto.uuid).exists()


@pytest.mark.django_db
def test_producto_codigo_duplicado_viola_constraint_de_bd(tenant, factory_empresa):
    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        Producto.objects.create(empresa=empresa, codigo="COD-REL-1", nombre="Producto A", precio_venta="10.00")
        with pytest.raises(IntegrityError):
            Producto.objects.create(empresa=empresa, codigo="COD-REL-1", nombre="Producto B", precio_venta="20.00")


@pytest.mark.django_db
def test_producto_codigo_vacio_no_colisiona_con_constraint(tenant, factory_empresa):
    """codigo blank=True -- multiples productos sin codigo deben poder coexistir
    (la UniqueConstraint excluye codigo vacio explicitamente, ver models.py)."""
    empresa = factory_empresa()
    with schema_context(tenant.schema_name):
        Producto.objects.create(empresa=empresa, codigo="", nombre="Producto Sin Codigo A", precio_venta="10.00")
        Producto.objects.create(empresa=empresa, codigo="", nombre="Producto Sin Codigo B", precio_venta="20.00")
        assert Producto.objects.filter(empresa=empresa, codigo="").count() == 2


@pytest.mark.urls('config.urls_tenant')
@pytest.mark.django_db
def test_crear_producto_codigo_duplicado_devuelve_400_no_500(tenant, factory_empresa):
    empresa = factory_empresa()
    client = _authed_client(tenant)

    with schema_context(tenant.schema_name):
        Producto.objects.create(empresa=empresa, codigo="COD-REL-API", nombre="Producto Original", precio_venta="10.00")

    url = reverse('producto-list')
    response = client.post(url, {"codigo": "COD-REL-API", "nombre": "Producto Duplicado", "precio_venta": "20.00"}, format='json')
    assert response.status_code == 400, response.content
