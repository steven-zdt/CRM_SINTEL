"""
Tests de Organizational Selectors (Fase 6, proyecto OCF): `context.filter(Model)`
resuelve automaticamente empresa (siempre) y sede/area (segun `alcance`), sin
que el llamador repita `.filter(empresa_id=..., sede_id=...)` por su cuenta.

Usa OrdenCompra (unico SedeAwareModel real, ADR-003) y Proveedor (sin
sede/area, el caso tipico de 16/17 apps - Fase 0) contra datos reales.
"""
from apps.tenant.compras.models import OrdenCompra
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


def _context(empresa_id, alcance="EMPRESA", sede_id=None, area_id=None) -> OrganizationalContext:
    return OrganizationalContext(
        tenant_schema="test", tenant_id=1, empresa_id=empresa_id, sede_id=sede_id, area_id=area_id,
        user_id=1, perfil_id=1, rol="OPERADOR", alcance=alcance, timezone="UTC", configuracion={},
    )


class OrganizationalSelectorTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase6", nit="900000666", direccion="Calle 1",
        )
        self.sede_norte = Sede.objects.create(empresa=self.empresa, nombre="Norte")
        self.sede_sur = Sede.objects.create(empresa=self.empresa, nombre="Sur")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor Selectors", numero_documento="456", tipo_documento="NIT",
        )
        self.orden_norte = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_norte, proveedor=self.proveedor,
            consecutivo=1, fecha="2026-08-01", subtotal=100, impuestos=19, total=119,
        )
        self.orden_sur = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_sur, proveedor=self.proveedor,
            consecutivo=2, fecha="2026-08-02", subtotal=200, impuestos=38, total=238,
        )

    def test_alcance_empresa_returns_orders_from_every_sede(self):
        context = _context(empresa_id=self.empresa.id, alcance="EMPRESA")
        qs = context.filter(OrdenCompra)
        self.assertEqual(set(qs.values_list("id", flat=True)), {self.orden_norte.id, self.orden_sur.id})

    def test_alcance_sede_returns_only_orders_from_active_sede(self):
        context = _context(empresa_id=self.empresa.id, alcance="SEDE", sede_id=self.sede_norte.id)
        qs = context.filter(OrdenCompra)
        self.assertEqual(list(qs.values_list("id", flat=True)), [self.orden_norte.id])

    def test_switching_active_sede_changes_the_filtered_result(self):
        """Prueba que el filtro realmente sigue la sede activa del
        contexto, no una constante - cambiar sede_id cambia el resultado."""
        context_norte = _context(empresa_id=self.empresa.id, alcance="SEDE", sede_id=self.sede_norte.id)
        context_sur = _context(empresa_id=self.empresa.id, alcance="SEDE", sede_id=self.sede_sur.id)
        self.assertEqual(list(context_norte.filter(OrdenCompra).values_list("id", flat=True)), [self.orden_norte.id])
        self.assertEqual(list(context_sur.filter(OrdenCompra).values_list("id", flat=True)), [self.orden_sur.id])

    def test_model_without_sede_field_is_filtered_by_empresa_only(self):
        """Proveedor no tiene sede - alcance=SEDE no debe fallar ni excluir
        nada por un campo que el modelo nunca tuvo."""
        context = _context(empresa_id=self.empresa.id, alcance="SEDE", sede_id=self.sede_norte.id)
        qs = context.filter(Proveedor)
        self.assertEqual(list(qs.values_list("id", flat=True)), [self.proveedor.id])

    def test_result_is_a_real_queryset_chainable_with_only_and_select_related(self):
        """El resultado debe seguir siendo un QuerySet normal, encadenable
        como ya hace cada selector existente - no un tipo especial."""
        context = _context(empresa_id=self.empresa.id, alcance="EMPRESA")
        qs = context.filter(OrdenCompra).select_related("proveedor").only("id", "consecutivo", "empresa_id", "proveedor_id")
        self.assertEqual(qs.count(), 2)
