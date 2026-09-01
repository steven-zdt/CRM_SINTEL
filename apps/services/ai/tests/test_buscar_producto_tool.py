"""
Fase AI-03.2: test de integracion real (DB) de `buscar_producto`,
mismo patron que test_buscar_cliente_tool.py.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.services.ai.engine import run_tool
from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import Producto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase

User = get_user_model()

AI_FLAGS_ON = {"AI_ENABLED": True, "AI_READ_ENABLED": True}


class _FakeRequest:
    def __init__(self, user, tenant=None):
        self.user = user
        self.tenant = tenant


class BuscarProductoToolTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.create(
            razon_social="EMPRESA PRODUCTOS TEST S.A.S.", nit="900555666", direccion="Calle P",
        )
        self.user = User.objects.create_user(email="prod_user@test.local", password="testpass123")
        TenantProfile.objects.create(user=self.user, empresa=self.empresa)

        Producto.objects.create(
            empresa=self.empresa, codigo="PROD-001", nombre="Cable UTP",
            stock_actual="150.000", precio_venta="25000.00",
        )
        Producto.objects.create(
            empresa=self.empresa, codigo="PROD-002", nombre="Switch 8 puertos",
            stock_actual="5.000", precio_venta="180000.00",
        )

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_producto_devuelve_stock_real(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_producto", request, search="Cable")

        assert result.status == "OK"
        assert len(result.data) == 1
        assert result.data[0]["codigo"] == "PROD-001"
        assert result.data[0]["stock_actual"] == "150.000"

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_producto_sin_filtro_devuelve_todos(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_producto", request)

        assert result.status == "OK"
        assert {p["codigo"] for p in result.data} == {"PROD-001", "PROD-002"}

    @override_settings(**AI_FLAGS_ON)
    def test_buscar_producto_limit_invalido(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_producto", request, limit=0)

        assert result.status == "VALIDATION_ERROR"

    def test_buscar_producto_bloqueado_sin_ai_enabled(self):
        request = _FakeRequest(user=self.user, tenant=self.tenant)

        result = run_tool("buscar_producto", request)

        assert result.status == "PERMISSION_DENIED"
