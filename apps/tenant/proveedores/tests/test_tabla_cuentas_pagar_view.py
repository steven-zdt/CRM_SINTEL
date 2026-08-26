"""
Test de la tabla server-rendered de Cuentas por Pagar (Fase 5-BIS,
django-tables2 + HTMX).

Verifica:
1. La vista responde 200 tras login por sesion.
2. Las facturas de compra (Factura.naturaleza=COMPRA) se renderizan como
   filas de Cuentas por Pagar, con el mismo mapeo de campos que
   FacturaCxPListSerializer (fuente de verdad, api/serializers.py).
3. El filtro ?estado_pago= y la busqueda ?q= funcionan.

Nota: esta migracion corrigio de paso dos bugs funcionales pre-existentes:
- La grilla Tabulator (`cuentas_pagar_list.js`) nunca se inicializaba: su
  `init()` no era llamado desde ninguna parte (el handler `shown.bs.tab` en
  proveedores_main.js solo hacia un console.log).
- El input de busqueda (#search-cuentas-pagar) enviaba `?search=` a la API,
  pero `CuentasPagarViewSet.list()` nunca leia ese parametro -- se agrego
  soporte real de busqueda en CuentasPagarSelector.qs_list_facturas_compra()
  y en el ViewSet.
"""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

from apps.public.tenants.models import TenantMembership
from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import CuentasPagar, Proveedor

User = get_user_model()


@pytest.fixture
def _admin_con_cxp(tenant):
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        proveedor = Proveedor.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800555666", razon_social="Proveedor CxP SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )
        Factura.objects.create(
            empresa=empresa, numero="FCOMPRA-001",
            emisor_nit=proveedor.numero_documento, emisor_razon_social=proveedor.razon_social,
            receptor_nit=empresa.nit, receptor_razon_social=empresa.razon_social,
            naturaleza=Factura.Naturaleza.COMPRA, proveedor_uuid=proveedor.uuid,
            subtotal=100000, impuestos=19000, total=119000,
            estado_pago=Factura.EstadoPago.NO_PAGADA,
        )
        Factura.objects.create(
            empresa=empresa, numero="FCOMPRA-002",
            emisor_nit=proveedor.numero_documento, emisor_razon_social=proveedor.razon_social,
            receptor_nit=empresa.nit, receptor_razon_social=empresa.razon_social,
            naturaleza=Factura.Naturaleza.COMPRA, proveedor_uuid=proveedor.uuid,
            subtotal=50000, impuestos=9500, total=59500,
            estado_pago=Factura.EstadoPago.PAGADA,
        )

        admin_user = User.objects.create(username="admin_cxp", email="admin_cxp@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_cuentas_pagar_render(client, tenant, _admin_con_cxp):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_cxp)

    r = client.get("/ui/proveedores/cuentas-pagar/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200, f"Status inesperado: {r.status_code}: {r.content[:500]}"
    html = r.content.decode("utf-8")
    assert "FCOMPRA-001" in html
    assert "FCOMPRA-002" in html
    assert "Proveedor CxP SAS" in html
    assert "Sin Pago" in html
    assert "Pagada" in html


@pytest.mark.django_db
def test_tabla_cuentas_pagar_filtro_estado(client, tenant, _admin_con_cxp):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_cxp)

    r = client.get(
        "/ui/proveedores/cuentas-pagar/tabla/?estado_pago=PAGADA",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "FCOMPRA-002" in html
    assert "FCOMPRA-001" not in html


@pytest.mark.django_db
def test_tabla_cuentas_pagar_busqueda(client, tenant, _admin_con_cxp):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_cxp)

    r = client.get(
        "/ui/proveedores/cuentas-pagar/tabla/?q=FCOMPRA-001",
        HTTP_HOST=f"{tenant.schema_name}.sintel.net.co",
    )

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "FCOMPRA-001" in html
    assert "FCOMPRA-002" not in html


@pytest.fixture
def _admin_con_cxp_sin_factura(tenant):
    """
    Hallazgo real (2026-08-26): CuentasPagar sin factura_uuid (generadas al
    aprobar una Orden de Compra, o creadas a mano) eran invisibles en esta
    tabla porque solo leia Factura.naturaleza='COMPRA'. Este fixture no crea
    ninguna Factura -- solo un CuentasPagar suelto, como quedaria una compra
    real sin factura electronica.
    """
    with schema_context(tenant.schema_name):
        empresa = Empresa.objects.only('id').first()
        proveedor = Proveedor.objects.create(
            empresa=empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800777888", razon_social="Proveedor Sin Factura SAS",
            regimen_tributario="ORDINARIO", activo=True,
        )
        CuentasPagar.objects.create(
            empresa=empresa, proveedor=proveedor, numero_factura="OC-SIN-FACTURA-1",
            fecha_emision="2026-06-01", fecha_vencimiento="2026-07-01",
            valor_total=Decimal("11900.00"),
        )

        admin_user = User.objects.create(username="admin_cxp_sf", email="admin_cxp_sf@example.com")
        TenantProfile.objects.create(user=admin_user, empresa=empresa, rol="ADMIN")

    TenantMembership.objects.create(client=tenant, user=admin_user, is_active=True, rol="ADMIN")
    return admin_user


@pytest.mark.django_db
def test_tabla_cuentas_pagar_incluye_cxp_sin_factura(client, tenant, _admin_con_cxp_sin_factura):
    with schema_context(tenant.schema_name):
        client.force_login(_admin_con_cxp_sin_factura)

    r = client.get("/ui/proveedores/cuentas-pagar/tabla/", HTTP_HOST=f"{tenant.schema_name}.sintel.net.co")

    assert r.status_code == 200
    html = r.content.decode("utf-8")
    assert "OC-SIN-FACTURA-1" in html
    assert "Proveedor Sin Factura SAS" in html
    assert "Sin Pago" in html
