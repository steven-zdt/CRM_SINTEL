"""
Fase AI-04 (Validation Engine): tests reales para las 6 tools
`validar_*` del primer lote (clientes, proveedores, inventario,
compras, cotizaciones, gastos). Cada tool envuelve el Serializer DRF
real de escritura de su dominio (`is_valid()`, nunca `.save()`) -- ver
apps/services/ai/tools/_validation.py.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.services.ai.engine import run_tool
from apps.tenant.clientes.models import Cliente
from apps.tenant.compras.models import PlantillaOrdenCompra
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import CategoriaItem
from apps.tenant.perfil.models import TenantProfile
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()

AI_VALIDATE_FLAGS_ON = {"AI_ENABLED": True, "AI_VALIDATE_ENABLED": True}


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


class ValidarClienteToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI04 CLIENTES S.A.S.", nit="900111001", direccion="Calle AI04-1",
        )
        self.user = User.objects.create_user(email="ai04_cliente@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900222001", razon_social="Cliente Ya Existente", regimen_tributario="ORDINARIO",
        )

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_datos_validos(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {
            "tipo_persona": "JURIDICA", "tipo_documento": "NIT", "numero_documento": "900333002",
            "razon_social": "Cliente Nuevo AI04", "regimen_tributario": "ORDINARIO",
        }

        result = run_tool("validar_cliente", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is True
        assert result.data["warnings"] == []
        assert result.data["missing_data"] == []

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_falta_razon_social(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {"tipo_persona": "JURIDICA", "tipo_documento": "NIT", "numero_documento": "900444003", "regimen_tributario": "ORDINARIO"}

        result = run_tool("validar_cliente", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert "razon_social" in result.data["missing_data"]

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_documento_duplicado_es_invalido(self):
        """Reutiliza la misma regla anti-duplicidad (FASE 4) del formulario real."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {
            "tipo_persona": "JURIDICA", "tipo_documento": "NIT", "numero_documento": "900222001",
            "razon_social": "Otro Nombre", "regimen_tributario": "ORDINARIO",
        }

        result = run_tool("validar_cliente", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert any("numero_documento" in w for w in result.data["warnings"])


class ValidarProveedorToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI04 PROVEEDORES S.A.S.", nit="900111002", direccion="Calle AI04-2",
        )
        self.user = User.objects.create_user(email="ai04_proveedor@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_datos_validos(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {"tipo_persona": "JURIDICA", "tipo_documento": "NIT", "numero_documento": "800555004", "razon_social": "Proveedor Nuevo AI04"}

        result = run_tool("validar_proveedor", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is True

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_falta_numero_documento(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {"razon_social": "Proveedor Sin Documento"}

        result = run_tool("validar_proveedor", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert "numero_documento" in result.data["missing_data"]


class ValidarProductoToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI04 PRODUCTOS S.A.S.", nit="900111003", direccion="Calle AI04-3",
        )
        self.user = User.objects.create_user(email="ai04_producto@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.categoria_servicio = CategoriaItem.objects.create(
            empresa=self.empresa, nombre="Categoria De Servicios AI04", aplicacion=CategoriaItem.Aplicacion.SERVICIO,
        )

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_datos_minimos_validos(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("validar_producto", request, data={"codigo": "AI04-PROD-1", "nombre": "Producto AI04"})

        assert result.status == "OK"
        assert result.data["valid"] is True

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_falta_nombre(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("validar_producto", request, data={"codigo": "AI04-PROD-2"})

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert "nombre" in result.data["missing_data"]

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_categoria_no_aplicable_a_productos(self):
        """Reutiliza validate_categoria() real -- una categoria SOLO_SERVICIOS no es valida para un producto."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {"codigo": "AI04-PROD-3", "nombre": "Producto Con Categoria Invalida", "categoria": self.categoria_servicio.id}

        result = run_tool("validar_producto", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert any("categoria" in w for w in result.data["warnings"])


class ValidarCompraToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI04 COMPRAS S.A.S.", nit="900111004", direccion="Calle AI04-4",
        )
        self.user = User.objects.create_user(email="ai04_compra@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800666005", razon_social="Proveedor Para Compra AI04",
        )
        self.plantilla = PlantillaOrdenCompra.objects.create(
            empresa=self.empresa, nombre="Plantilla AI04", rango_desde=1, rango_hasta=1000,
        )

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_datos_vacios_reportan_campos_faltantes(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("validar_compra", request, data={})

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert "plantilla" in result.data["missing_data"]
        assert "proveedor" in result.data["missing_data"]

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_fecha_entrega_anterior_a_fecha_es_invalida(self):
        """Reutiliza la regla real de OrdenCompraCreateUpdateSerializer.validate()."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {
            "plantilla": self.plantilla.id,
            "proveedor": self.proveedor.id,
            "fecha": "2026-06-10",
            "fecha_entrega": "2026-06-01",
            "items": [
                {"descripcion": "Item AI04", "cantidad": "1.00", "valor_unitario": "100.00", "porcentaje_iva": "19.00"},
            ],
        }

        result = run_tool("validar_compra", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert any("fecha_entrega" in w for w in result.data["warnings"])


class ValidarCotizacionToolTests(SintelTenantTestCase):
    """CotizacionSerializer requiere `context['empresa']` (instancia real,
    no empresa_id) -- ver la nota en cotizaciones_tools.py."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI04 COTIZ S.A.S.", nit="900111005", direccion="Calle AI04-5",
        )
        self.user = User.objects.create_user(email="ai04_cotiz@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="900888005", razon_social="Cliente Para Cotizacion AI04", regimen_tributario="ORDINARIO",
        )
        self.configuracion = ConfiguracionCotizacion.objects.create(
            empresa=self.empresa, nombre_configuracion="Configuracion AI04",
        )

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_datos_validos(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)
        data = {"cliente": self.cliente.id, "configuracion": self.configuracion.id}

        result = run_tool("validar_cotizacion", request, data=data)

        assert result.status == "OK"
        assert result.data["valid"] is True

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_datos_vacios_reportan_cliente_y_configuracion_faltantes(self):
        """Hallazgo real (corrige una hipotesis inicial equivocada): aunque
        Cotizacion.cliente/configuracion permiten NULL a nivel de modelo
        (blank=True, null=True), CotizacionSerializer los declara
        explicitamente SIN required=False -- DRF los trata como
        requeridos porque son campos declarados a mano, no
        auto-generados desde el modelo."""
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("validar_cotizacion", request, data={})

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert "cliente" in result.data["missing_data"]
        assert "configuracion" in result.data["missing_data"]

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_sede_inexistente_es_invalida(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool(
            "validar_cotizacion", request,
            data={"sede": "00000000-0000-0000-0000-000000000000"},
        )

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert any("sede" in w for w in result.data["warnings"])


class ValidarGastoToolTests(SintelTenantTestCase):
    """GastoDetailSerializer tiene subtotal/total/resolucion_dian como
    read_only -- solo proveedor es realmente requerido via este
    serializer (ver la nota en gastos_tools.py)."""

    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA AI04 GASTOS S.A.S.", nit="900111006", direccion="Calle AI04-6",
        )
        self.user = User.objects.create_user(email="ai04_gasto@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, tipo_persona="JURIDICA", tipo_documento="NIT",
            numero_documento="800777006", razon_social="Proveedor Para Gasto AI04",
        )

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_con_proveedor_es_valido(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("validar_gasto", request, data={"proveedor": self.proveedor.id})

        assert result.status == "OK"
        assert result.data["valid"] is True

    @override_settings(**AI_VALIDATE_FLAGS_ON)
    def test_falta_proveedor(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("validar_gasto", request, data={})

        assert result.status == "OK"
        assert result.data["valid"] is False
        assert "proveedor" in result.data["missing_data"]
