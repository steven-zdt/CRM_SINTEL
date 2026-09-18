"""
Tests de la regla de Representante Legal (mision "Clientes + Cartera",
2026-09-11, secciones 7-10 y 59): un Cliente JURIDICA debe tener al menos
un ContactoCliente marcado como representante legal; NATURAL no lo
requiere. La regla se valida en Backend (ClienteBusinessService.
validar_representante_legal()), nunca solo en el formulario.

`validar_representante=True` solo se activa desde el formulario real
(ClienteViewSet) -- los flujos de resolucion automatica desde documentos
externos (factura XML) siguen sin exigirla, ver docstring de
registrar_cliente_completo().
"""
import pytest
from django_tenants.utils import schema_context

from apps.tenant.clientes.models import Cliente, ContactoCliente
from apps.tenant.empresa.models import Empresa


def _post_cliente(client, tenant, payload):
    return client.post(
        "/api/v1/clientes/",
        data=payload,
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )


def _base_payload(numero_documento, tipo_persona, contactos=None):
    payload = {
        "tipo_persona": tipo_persona,
        "tipo_documento": "NIT" if tipo_persona == "JURIDICA" else "CC",
        "numero_documento": numero_documento,
        "razon_social": "Cliente Representante Test",
        "regimen_tributario": "ORDINARIO",
        "activo": True,
    }
    if contactos is not None:
        payload["contactos"] = contactos
    return payload


@pytest.mark.django_db
def test_crear_cliente_natural_sin_representante_funciona(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    resp = _post_cliente(client, tenant, _base_payload("800300001", "NATURAL"))
    assert resp.status_code in (200, 201), resp.content


@pytest.mark.django_db
def test_crear_cliente_juridica_sin_representante_falla(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    resp = _post_cliente(client, tenant, _base_payload("800300002", "JURIDICA"))
    assert resp.status_code == 400, resp.content
    assert "representante_legal" in resp.json()

    with schema_context(tenant.schema_name):
        assert not Cliente.objects.filter(numero_documento="800300002").exists()


@pytest.mark.django_db
def test_crear_cliente_juridica_con_representante_funciona(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    contactos = [{
        "nombre_completo": "Juan Representante",
        "email": "juan.representante@example.com",
        "es_representante_legal": True,
    }]
    resp = _post_cliente(client, tenant, _base_payload("800300003", "JURIDICA", contactos))
    assert resp.status_code == 201, resp.content

    with schema_context(tenant.schema_name):
        cliente = Cliente.objects.get(numero_documento="800300003")
        assert ContactoCliente.objects.filter(
            cliente=cliente, es_representante_legal=True
        ).exists()


@pytest.mark.django_db
def test_actualizar_cliente_juridica_quitando_representante_falla(client, admin_user, tenant):
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)

    contactos = [{
        "nombre_completo": "Juan Representante",
        "email": "juan.representante2@example.com",
        "es_representante_legal": True,
    }]
    resp = _post_cliente(client, tenant, _base_payload("800300004", "JURIDICA", contactos))
    assert resp.status_code == 201, resp.content
    cliente_uuid = resp.json()["uuid"]

    with schema_context(tenant.schema_name):
        contacto_id = ContactoCliente.objects.get(
            cliente__uuid=cliente_uuid, email="juan.representante2@example.com",
        ).id

    # PATCH tocando contactos: quita la marca de representante legal. Envia
    # el `id` del contacto existente para que sincronizar_contactos() lo
    # trate como UPDATE (sin id, se interpretaria como un contacto NUEVO
    # con el mismo email -> violaria uniq_contacto_cliente_email).
    resp2 = client.patch(
        f"/api/v1/clientes/{cliente_uuid}/",
        data={"contactos": [{
            "id": contacto_id,
            "nombre_completo": "Juan Representante",
            "email": "juan.representante2@example.com",
            "es_representante_legal": False,
        }]},
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp2.status_code == 400, resp2.content
    assert "representante_legal" in resp2.json()


@pytest.mark.django_db
def test_actualizar_cliente_juridica_sin_tocar_contactos_no_falla(client, admin_user, tenant):
    """
    Un PATCH que no envia 'contactos' (ej. solo cambia telefono) no debe
    romper clientes JURIDICA historicos que nunca tuvieron esta regla --
    la validacion solo corre al crear o cuando la peticion toca contactos
    explicitamente (ver docstring de registrar_cliente_completo()).
    """
    with schema_context(tenant.schema_name):
        client.force_login(admin_user)
        empresa = Empresa.objects.first()
        cliente_historico = Cliente.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800300005", razon_social="Historico Sin Representante",
            regimen_tributario="ORDINARIO", activo=True,
        )
        cliente_uuid = str(cliente_historico.uuid)

    resp = client.patch(
        f"/api/v1/clientes/{cliente_uuid}/",
        data={"telefono": "3009998888"},
        content_type="application/json",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )
    assert resp.status_code == 200, resp.content
