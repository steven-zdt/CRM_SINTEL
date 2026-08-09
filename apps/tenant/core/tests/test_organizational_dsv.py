"""
Tests de Organizational DSV (Fase 5, proyecto OCF).

Usa OrdenCompra (compras, unico modelo SedeAwareModel real hoy - ADR-003) y
Proveedor (sin sede/area, la mayoria de modelos del proyecto - ver Fase 0)
para probar contra datos reales, no mocks sinteticos.
"""
from apps.tenant.compras.models import OrdenCompra
from apps.tenant.core.services.organizational_context import OrganizationalContext
from apps.tenant.core.services.organizational_dsv import (
    OrganizationalDSVError,
    is_organizationally_consistent,
    verify_organizational_dsv,
)
from apps.tenant.empresa.models import Empresa, Sede
from apps.tenant.proveedores.models import Proveedor
from tests.tenant.base_test import SintelTenantTestCase


def _context(empresa_id, alcance="EMPRESA", sede_id=None) -> OrganizationalContext:
    return OrganizationalContext(
        tenant_schema="test", tenant_id=1, empresa_id=empresa_id, sede_id=sede_id, area_id=None,
        user_id=1, perfil_id=1, rol="OPERADOR", alcance=alcance, timezone="UTC", configuracion={},
    )


class OrganizationalDSVTests(SintelTenantTestCase):
    def setUp(self):
        super().setUp()
        self.empresa = Empresa.objects.first() or Empresa.objects.create(
            razon_social="Empresa Test OCF Fase5", nit="900000444", direccion="Calle 1",
        )
        # Empresa es singleton por schema (UniqueConstraint singleton_key) -
        # no se puede crear una segunda fila en el mismo tenant. Para probar
        # "pertenece a otra empresa" basta un id que no coincida, no hace
        # falta una segunda Empresa real.
        self.otra_empresa_id = self.empresa.id + 999_999
        self.sede_norte = Sede.objects.create(empresa=self.empresa, nombre="Norte")
        self.sede_sur = Sede.objects.create(empresa=self.empresa, nombre="Sur")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, razon_social="Proveedor DSV", numero_documento="123", tipo_documento="NIT",
        )
        self.orden = OrdenCompra.objects.create(
            empresa=self.empresa, sede=self.sede_norte, proveedor=self.proveedor,
            consecutivo=1, fecha="2026-08-01", subtotal=100, impuestos=19, total=119,
        )

    def test_rejects_object_from_another_empresa(self):
        context = _context(empresa_id=self.otra_empresa_id)
        with self.assertRaises(OrganizationalDSVError) as ctx:
            verify_organizational_dsv(self.orden, context)
        self.assertEqual(ctx.exception.field, "empresa")

    def test_alcance_empresa_ignores_sede_entirely(self):
        """alcance=EMPRESA no restringe por sede, sin importar
        sedes_asignadas - mismo comportamiento que HasOrganizationalScope
        (ADR-003)."""
        context = _context(empresa_id=self.empresa.id, alcance="EMPRESA")
        verify_organizational_dsv(self.orden, context, sedes_asignadas=[])  # no lanza

    def test_alcance_sede_rejects_orden_from_unassigned_sede(self):
        context = _context(empresa_id=self.empresa.id, alcance="SEDE")
        with self.assertRaises(OrganizationalDSVError) as ctx:
            verify_organizational_dsv(self.orden, context, sedes_asignadas=[self.sede_sur.id])
        self.assertEqual(ctx.exception.field, "sede")

    def test_alcance_sede_accepts_orden_from_assigned_sede(self):
        context = _context(empresa_id=self.empresa.id, alcance="SEDE")
        verify_organizational_dsv(self.orden, context, sedes_asignadas=[self.sede_norte.id])  # no lanza

    def test_alcance_sede_with_no_sedes_asignadas_is_fail_closed(self):
        context = _context(empresa_id=self.empresa.id, alcance="SEDE")
        with self.assertRaises(OrganizationalDSVError):
            verify_organizational_dsv(self.orden, context, sedes_asignadas=None)

    def test_object_without_sede_field_only_checks_empresa(self):
        """Proveedor no tiene sede_id (Fase 0: 10/17 apps no tienen ningun
        concepto de sede) - alcance=SEDE no debe fallar por falta de un
        atributo que el modelo nunca tuvo."""
        context = _context(empresa_id=self.empresa.id, alcance="SEDE")
        verify_organizational_dsv(self.proveedor, context, sedes_asignadas=[])  # no lanza

    def test_is_organizationally_consistent_boolean_wrapper(self):
        context_ok = _context(empresa_id=self.empresa.id, alcance="SEDE")
        context_bad = _context(empresa_id=self.otra_empresa_id)
        self.assertTrue(
            is_organizationally_consistent(self.orden, context_ok, sedes_asignadas=[self.sede_norte.id])
        )
        self.assertFalse(is_organizationally_consistent(self.orden, context_bad))
