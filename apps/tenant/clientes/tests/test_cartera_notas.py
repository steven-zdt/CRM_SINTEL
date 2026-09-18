"""
Tests de CarteraNota (mision "Clientes + Cartera" seccion 29-30, 2026-09-11):
historial de anotaciones de seguimiento sobre una obligacion de Cartera,
append-only, independiente del campo `observaciones` legado.
"""
from decimal import Decimal

import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cartera, CarteraNota, Cliente
from apps.tenant.clientes.services.business_service import CarteraBusinessService
from apps.tenant.empresa.models import Empresa


def _crear_cartera(empresa):
    cliente = Cliente.objects.create(
        empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
        numero_documento="900333444", razon_social="Cliente Notas Cartera",
        regimen_tributario="ORDINARIO", activo=True,
    )
    return Cartera.objects.create(
        empresa=empresa, cliente=cliente, numero_factura="FE-NOTA-1",
        fecha_emision="2026-06-01", fecha_vencimiento="2026-07-01",
        valor_total=Decimal("1000000.00"),
    )


@pytest.mark.django_db
def test_agregar_nota_service(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cartera = _crear_cartera(empresa)

        nota = CarteraBusinessService.agregar_nota(
            empresa_id=empresa.id, cartera_uuid=cartera.uuid,
            texto="Cliente informa que paga el viernes.", tipo="PROMESA_PAGO",
        )
        assert nota.id
        assert nota.texto == "Cliente informa que paga el viernes."
        assert nota.tipo == "PROMESA_PAGO"
        assert CarteraNota.objects.filter(cartera=cartera).count() == 1


@pytest.mark.django_db
def test_agregar_nota_texto_vacio_falla(tenant):
    from rest_framework.exceptions import ValidationError
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cartera = _crear_cartera(empresa)

        with pytest.raises(ValidationError):
            CarteraBusinessService.agregar_nota(
                empresa_id=empresa.id, cartera_uuid=cartera.uuid, texto="   ",
            )


@pytest.mark.django_db
def test_api_notas_get_y_post(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cartera = _crear_cartera(empresa)
        cartera_uuid = cartera.uuid

    # GET inicial: vacio
    resp = client.get(
        f"/api/v1/clientes/cartera/{cartera_uuid}/notas/",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200
    assert resp.json() == []

    # POST agrega una nota y retorna el historial actualizado
    resp2 = client.post(
        f"/api/v1/clientes/cartera/{cartera_uuid}/notas/",
        data={"texto": "Abono realizado por consignacion.", "tipo": "SEGUIMIENTO"},
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp2.status_code == 201, resp2.content
    data = resp2.json()
    assert len(data) == 1
    assert data[0]["texto"] == "Abono realizado por consignacion."
    assert data[0]["tipo_display"] == "Seguimiento"

    # GET posterior refleja la nota persistida
    resp3 = client.get(
        f"/api/v1/clientes/cartera/{cartera_uuid}/notas/",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp3.status_code == 200
    assert len(resp3.json()) == 1


@pytest.mark.django_db
def test_api_notas_texto_vacio_400(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.first()
        cartera = _crear_cartera(empresa)
        cartera_uuid = cartera.uuid

    resp = client.post(
        f"/api/v1/clientes/cartera/{cartera_uuid}/notas/",
        data={"texto": ""},
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 400
