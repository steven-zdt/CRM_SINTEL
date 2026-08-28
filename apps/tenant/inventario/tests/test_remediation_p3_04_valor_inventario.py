"""
REM P3-04 (docs/remediation/REM-P3-04.md): "Valor de inventario" tenia 2
formulas divergentes -- InventarioExtractor (dashboard) filtraba
activo=True, ProductoTableView (vista propia de Inventario) no. Se unifico
al mismo criterio (activo=True) en ambos lugares.
"""
from decimal import Decimal

from django.urls import reverse

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import Producto
from apps.tenant.perfil.models import TenantProfile
from tests.tenant.base_test import SintelTenantTestCase


class ValorInventarioP3_04Tests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa P3-04", nit="900000800", direccion="Calle 1",
        )
        TenantProfile.objects.create(
            user=self.user, empresa=self.empresa, rol="ADMIN", alcance="EMPRESA",
        )

    def test_kpi_valor_total_excluye_productos_inactivos(self):
        Producto.objects.create(
            empresa=self.empresa, codigo="P304-ACTIVO", nombre="Producto Activo",
            stock_actual=Decimal("10"), costo_promedio=Decimal("100.00"), activo=True,
        )
        Producto.objects.create(
            empresa=self.empresa, codigo="P304-INACTIVO", nombre="Producto Inactivo",
            stock_actual=Decimal("50"), costo_promedio=Decimal("1000.00"), activo=False,
        )

        response = self.client.get(reverse("inventario:producto-tabla"))

        self.assertEqual(response.status_code, 200)
        # Solo el producto activo (10 * 100 = 1000) debe contarse -- el
        # inactivo (50 * 1000 = 50000) debe quedar fuera.
        self.assertEqual(response.context["kpi_valor_total"], Decimal("1000.00"))
