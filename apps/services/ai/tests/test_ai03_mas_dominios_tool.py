"""
Fase AI-03 (continuacion): tests reales para 6 tools nuevas
(buscar_proveedor, consultar_venta, consultar_compra,
consultar_cotizacion, consultar_gasto, consultar_proyecto), mismo
patron que test_buscar_cliente_tool.py / test_buscar_producto_tool.py.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.services.ai.engine import run_tool
from apps.tenant.clientes.models import Cliente
from apps.tenant.compras.models import OrdenCompra
from apps.tenant.cotizaciones.models import Cotizacion
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.facturas.models import Factura
from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.ventas.models import Venta
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


class BuscarProveedorToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA PROV TEST S.A.S.", nit="900666777", direccion="Calle Prov",
        )
        self.user = User.objects.create_user(email="prov_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800111222", razon_social="Proveedor Real Uno",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_proveedor_encuentra_proveedor_real(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_proveedor", request, search="Real Uno")

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["razon_social"] == "Proveedor Real Uno"

    def test_buscar_proveedor_bloqueado_sin_ai_enabled(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_proveedor", request)

        assert result.status == "PERMISSION_DENIED"


class ConsultarVentaToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA VENTAS TEST S.A.S.", nit="900777888", direccion="Calle V",
        )
        self.user = User.objects.create_user(email="venta_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900222333", razon_social="Cliente De La Venta",
        )
        Venta.objects.create(
            empresa=self.empresa, cliente=self.cliente, fecha_emision="2026-06-01",
            numero_factura="VENTA-AI-TEST", subtotal="500.00", total_neto="500.00",
            estado="BORRADOR",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_consultar_venta_incluye_nombre_de_cliente(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("consultar_venta", request)

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["cliente"] == "Cliente De La Venta"
        assert result.data[0]["numero_factura"] == "VENTA-AI-TEST"

    @override_settings(**AI_FLAGS_ON)
    def test_consultar_venta_filtra_por_estado(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("consultar_venta", request, estado="APROBADA")

        assert result.status == "OK"
        assert result.data == []


class ConsultarCompraToolTests(SintelTenantTestCase):
    """Cubre el manejo real de alcance organizacional (sede) -- no solo empresa_id."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA COMPRAS TEST S.A.S.", nit="900888999", direccion="Calle C",
        )
        self.sede_a = Sede.objects.create(empresa=self.empresa, nombre="Sede A")
        self.sede_b = Sede.objects.create(empresa=self.empresa, nombre="Sede B")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800333444", razon_social="Proveedor De La Compra",
        )
        OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_a, proveedor=self.proveedor,
            consecutivo=1, fecha="2026-06-01",
        )
        OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_b, proveedor=self.proveedor,
            consecutivo=2, fecha="2026-06-02",
        )

        self.user_empresa = User.objects.create_user(email="oc_empresa@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user_empresa, empresa=self.empresa, alcance="EMPRESA")

        self.user_sede_a = User.objects.create_user(email="oc_sede_a@test.local", password="testpass123")
        profile_sede_a = TenantProfile.objects.create(
            user=self.user_sede_a, empresa=self.empresa, alcance="SEDE",
        )
        profile_sede_a.sedes_asignadas.set([self.sede_a])

    @override_settings(**AI_FLAGS_ON)
    def test_alcance_empresa_ve_todas_las_sedes(self):
        request = _FakeRequest(user=self.user_empresa, tenant=self.tenant)

        result = run_tool("consultar_compra", request)

        assert result.status == "OK"
        assert {o["sede"] for o in result.data} == {"Sede A", "Sede B"}

    @override_settings(**AI_FLAGS_ON)
    def test_alcance_sede_solo_ve_su_propia_sede(self):
        """Regla 4/DSV: un usuario con alcance SEDE nunca debe ver otra sede."""
        request = _FakeRequest(user=self.user_sede_a, tenant=self.tenant)

        result = run_tool("consultar_compra", request)

        assert result.status == "OK"
        assert {o["sede"] for o in result.data} == {"Sede A"}
        assert "Sede B" not in {o["sede"] for o in result.data}


class ConsultarCotizacionToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA COTIZ TEST S.A.S.", nit="900999000", direccion="Calle Q",
        )
        self.user = User.objects.create_user(email="cotiz_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900333444", razon_social="Cliente De La Cotizacion",
        )
        Cotizacion.objects.create(
            empresa=self.empresa, cliente=self.cliente, numero_cotizacion="COT-AI-TEST",
            fecha_vencimiento=datetime.date(2026, 12, 31), estado="BORRADOR",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_consultar_cotizacion_incluye_nombre_de_cliente(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("consultar_cotizacion", request)

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["cliente"] == "Cliente De La Cotizacion"
        assert result.data[0]["numero_cotizacion"] == "COT-AI-TEST"


class ConsultarGastoToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA GASTOS TEST S.A.S.", nit="900111333", direccion="Calle G",
        )
        self.user = User.objects.create_user(email="gasto_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800555666", razon_social="Proveedor Del Gasto",
        )
        self.resolucion = ResolucionDIAN.objects.create(
            empresa=self.empresa, numero_resolucion="RES-AI-TEST", prefijo="DS",
            rango_desde=1, rango_hasta=1000,
            fecha_resolucion=datetime.date(2026, 1, 1), fecha_fin=datetime.date(2027, 1, 1),
        )
        DocumentoSoporte.objects.create(
            empresa=self.empresa, resolucion_dian=self.resolucion, proveedor=self.proveedor,
            consecutivo=1, fecha=datetime.date(2026, 6, 1),
            descripcion="Gasto de prueba AI", subtotal="100.00", total="100.00",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_consultar_gasto_incluye_proveedor(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("consultar_gasto", request)

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["proveedor"] == "Proveedor Del Gasto"
        assert result.data[0]["descripcion"] == "Gasto de prueba AI"


class ConsultarProyectoToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA PROYECTOS TEST S.A.S.", nit="900222444", direccion="Calle P",
        )
        self.user = User.objects.create_user(email="proy_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Proyecto.objects.create(
            empresa=self.empresa, nombre="Proyecto De Prueba AI", codigo="PRY-AI-TEST",
            cliente_nombre="Cliente Snapshot", fase_actual="EJECUCION",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_consultar_proyecto_encuentra_proyecto_real(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("consultar_proyecto", request)

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["nombre"] == "Proyecto De Prueba AI"
        assert result.data[0]["cliente"] == "Cliente Snapshot"


class ConsultarFacturaToolTests(SintelTenantTestCase):
    """consultar_factura es READ-only por diseno (FASE 21) -- estos tests
    solo verifican lectura, nunca ejercitan escritura via esta tool."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA FACTURAS TEST S.A.S.", nit="900444555", direccion="Calle F",
        )
        self.user = User.objects.create_user(email="fact_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Factura.objects.create(
            empresa=self.empresa, numero="FE-AI-TEST-001", consecutivo=1,
            naturaleza="VENTA", fecha_emision="2026-06-01T00:00:00Z",
            emisor_nit="900444555", emisor_razon_social="EMPRESA FACTURAS TEST S.A.S.",
            receptor_nit="900333444", receptor_razon_social="Cliente Receptor AI",
            total="238.00",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_consultar_factura_encuentra_factura_real(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("consultar_factura", request, search="AI-TEST")

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["numero"] == "FE-AI-TEST-001"
        assert result.data[0]["receptor_razon_social"] == "Cliente Receptor AI"

    def test_consultar_factura_no_expone_metodos_de_escritura(self):
        """La tool nunca debe registrar kind distinto de READ."""
        from apps.services.ai.tools import get_tool

        tool = get_tool("consultar_factura")

        assert tool.kind.value == "READ"
